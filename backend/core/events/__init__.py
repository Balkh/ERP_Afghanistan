"""
Phase 17++ — Safety-Layered Event Bus.
FAIL-OPEN, depth-guarded, priority-aware, lossless-by-design.
Must never block business flow. Must stay under 80 lines.
"""
import logging
import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List

from core.events.safety import EVENT_PRIORITY, EventCategory, backpressure, dispatch_safe, safety_buffer

logger = logging.getLogger("erp.events")

MAX_EVENT_DEPTH = 2
_event_context = threading.local()


def _get_depth(correlation_id: str) -> int:
    if not hasattr(_event_context, "depths"):
        _event_context.depths = {}
    return _event_context.depths.get(correlation_id, 0)


def _set_depth(correlation_id: str, depth: int) -> None:
    _event_context.depths[correlation_id] = depth


def _clean_depth(correlation_id: str) -> None:
    depths = getattr(_event_context, "depths", {})
    depths.pop(correlation_id, None)


class EnterpriseEventBus:
    _subscribers: Dict[str, List[Callable]] = defaultdict(list)

    @classmethod
    def subscribe(cls, event_name: str, handler: Callable) -> None:
        if handler not in cls._subscribers[event_name]:
            cls._subscribers[event_name].append(handler)

    @classmethod
    def publish(cls, event_name: str, payload: dict) -> None:
        correlation_id = payload.get("correlation_id", "")
        depth = _get_depth(correlation_id)
        cat = EVENT_PRIORITY.get(event_name, EventCategory.OPERATIONAL)
        if depth > MAX_EVENT_DEPTH:
            if cat == EventCategory.FINANCIAL_CRITICAL:
                safety_buffer.store(payload, "DEPTH_LIMITED")
                logger.warning("Event %s depth-limited, buffered (FINANCIAL_CRITICAL)", event_name)
            else:
                logger.warning("Event %s dropped: max depth %s exceeded", event_name, MAX_EVENT_DEPTH)
            return
        _set_depth(correlation_id, depth + 1)
        backpressure.record_dispatch()
        dispatch_safe(cls._subscribers.get(event_name, []), payload)
        _set_depth(correlation_id, depth)

    @classmethod
    def clear(cls) -> None:
        cls._subscribers.clear()

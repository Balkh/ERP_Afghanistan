import uuid
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.sandbox.models import EventPriority, SandboxEvent

logger = logging.getLogger(__name__)


class EventBus:
    _instance = None
    _initialized = False

    def __init__(self):
        if not EventBus._initialized:
            self._queues: Dict[str, deque] = {
                p.value: deque()
                for p in EventPriority
            }
            self._subscribers: Dict[str, List[Callable]] = {}
            self._processed_count: int = 0
            self._max_queue: int = 10000
            EventBus._initialized = True

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "",
    ) -> str:
        event_id = str(uuid.uuid4())
        event = SandboxEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload or {},
            priority=priority,
            source=source,
        )
        q = self._queues[priority.value]
        if len(q) >= self._max_queue:
            q.popleft()
        q.append(event)
        logger.debug(
            f"[SANDBOX] Event published: {event_type} "
            f"(id={event_id[:8]}, priority={priority.value})"
        )
        return event_id

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def process_next(self) -> Optional[SandboxEvent]:
        for p in [EventPriority.CRITICAL, EventPriority.HIGH,
                  EventPriority.NORMAL, EventPriority.LOW]:
            q = self._queues[p.value]
            if q:
                event = q.popleft()
                event.processed = True
                self._processed_count += 1
                handlers = self._subscribers.get(event.event_type, [])
                results = []
                for handler in handlers:
                    try:
                        result = handler(event)
                        results.append(result)
                    except Exception as e:
                        logger.error(
                            f"[SANDBOX] Handler error for {event.event_type}: {e}"
                        )
                event.result = {"handler_results": results} if results else None
                return event
        return None

    def process_all(self, max_events: int = 0) -> int:
        count = 0
        while True:
            if max_events and count >= max_events:
                break
            event = self.process_next()
            if event is None:
                break
            count += 1
        return count

    def get_queue_length(self) -> int:
        return sum(len(q) for q in self._queues.values())

    def get_queue_stats(self) -> Dict[str, int]:
        return {p.value: len(self._queues[p.value]) for p in EventPriority}

    def clear(self):
        for q in self._queues.values():
            q.clear()
        self._processed_count = 0

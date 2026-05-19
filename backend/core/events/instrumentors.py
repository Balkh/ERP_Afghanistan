"""
Phase 17++ — Safety-layered event publish surface.
Single entry point. Builds deterministic envelope. NEVER raises.
"""
import logging
from typing import Any, Dict, Optional

from core.events import EnterpriseEventBus, _clean_depth
from core.events.safety import EVENT_PRIORITY, EventCategory, build_envelope, safety_buffer

logger = logging.getLogger("erp.events.instrumentors")


def publish_event(
    event_name: str,
    payload: Dict[str, Any],
    actor_id: Optional[str] = None,
    company_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """
    Publish a deterministic event envelope. NEVER raises.
    Financial-critical events are buffered (not dropped) on depth limit.
    Payload must be flat metadata only — no ORM objects, no binary.
    """
    cat = EVENT_PRIORITY.get(event_name, EventCategory.OPERATIONAL)
    envelope = build_envelope(event_name, payload, cat, actor_id, company_id, correlation_id, depth=0)
    try:
        EnterpriseEventBus.publish(event_name, envelope)
    except Exception:
        logger.exception("Event dispatch failed for %s (fail-open)", event_name)
        if cat == EventCategory.FINANCIAL_CRITICAL:
            safety_buffer.store(envelope, "FAILED_HANDLER")
    finally:
        _clean_depth(envelope["correlation_id"])

"""
Governance Events — Phase 4.

Structured governance events with noise control.
Prevents duplicate logs, repetitive warnings, telemetry spam, and recursive logging.
"""
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("erp.governance.events")

EVENTS_VERSION = "1.0.0"


class EventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class GovernanceEvent:
    event_id: str
    event_type: str
    severity: EventSeverity
    message: str
    policy_id: str = ""
    invariant_id: str = ""
    enforcement_result: str = ""
    latency_ms: float = 0.0
    correlation_id: str = ""
    details: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class EventDeduplicator:
    """Prevents duplicate event emissions within a dedup window.

    Thread-safe. Uses bounded memory via LRU-like structure.
    """

    def __init__(self, window_seconds: float = 300.0, max_entries: int = 500):
        self._window = window_seconds
        self._max = max_entries
        self._seen: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_duplicate(self, event: GovernanceEvent) -> bool:
        """Check if an event is a duplicate within the dedup window."""
        key = f"{event.event_type}:{event.message[:100]}"
        now = time.time()
        with self._lock:
            last_seen = self._seen.get(key)
            if last_seen and (now - last_seen) < self._window:
                return True
            self._seen[key] = now
            if len(self._seen) > self._max:
                oldest = min(self._seen.keys(), key=lambda k: self._seen[k])
                del self._seen[oldest]
            return False


class EventBus:
    """Lightweight governance event bus.

    Collects structured governance events for observability.
    NOT a replacement for the enterprise event bus — this is
    governance-specific instrumentation only.
    """

    def __init__(self, max_events: int = 500):
        self._events: deque = deque(maxlen=max_events)
        self._dedup = EventDeduplicator()
        self._lock = threading.Lock()
        self._handlers: Dict[str, List[callable]] = {}
        self._last_cleanup = time.time()

    def emit(self, event: GovernanceEvent) -> None:
        """Emit a governance event. Deduplicates by type+message within window."""
        if self._dedup.is_duplicate(event):
            return

        with self._lock:
            self._events.append(event)

        profile = _get_env_profile()

        log_map = {
            EventSeverity.CRITICAL: logger.critical,
            EventSeverity.ERROR: logger.error,
            EventSeverity.WARNING: logger.warning,
            EventSeverity.INFO: logger.info,
            EventSeverity.DEBUG: logger.debug,
        }

        should_log = (
            profile == "production" and event.severity in (
                EventSeverity.ERROR, EventSeverity.CRITICAL, EventSeverity.WARNING,
            )
        ) or (profile != "production" and event.severity != EventSeverity.DEBUG)

        if should_log:
            log_fn = log_map.get(event.severity, logger.info)
            log_fn(
                "[%s] %s (policy=%s, corr=%s, latency=%.1fms)",
                event.event_type, event.message,
                event.policy_id, event.correlation_id[:8] if event.correlation_id else "",
                event.latency_ms,
            )

        self._notify_handlers(event)

    def get_recent(self, limit: int = 50) -> List[GovernanceEvent]:
        with self._lock:
            return list(self._events)[-limit:]

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def subscribe(self, event_type: str, handler: callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def _notify_handlers(self, event: GovernanceEvent) -> None:
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Governance event handler error: %s", e)

    def summary(self) -> dict:
        """Return summary of recent events."""
        with self._lock:
            total = len(self._events)
            counts = {}
            for e in self._events:
                counts[e.event_type] = counts.get(e.event_type, 0) + 1
            return {
                "total_events": total,
                "capacity": self._events.maxlen,
                "by_type": counts,
                "dedup_window_seconds": self._dedup._window,
            }


# Singleton
_instance = None
_lock = threading.Lock()


def get_event_bus() -> EventBus:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = EventBus()
    return _instance


def _get_env_profile() -> str:
    try:
        from django.conf import settings
        debug = getattr(settings, "DEBUG", True)
        import os
        env = os.environ.get("ENV", "").lower()
        if env == "production":
            return "production"
        if env == "staging":
            return "staging"
        if env in ("qa", "testing"):
            return "qa"
        return "development"
    except Exception:
        return "development"

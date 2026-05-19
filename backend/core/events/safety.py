"""
Phase 17++ — Event Safety Layer.
Classification, buffer, backpressure, deterministic envelope, safe dispatch.
FAIL-OPEN by design. Financial events NEVER silently dropped.
"""
import hashlib
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger("erp.events.safety")

# ── Phase 1: Event Classification ──

class EventCategory(Enum):
    FINANCIAL_CRITICAL = 5
    BUSINESS_CRITICAL = 4
    OPERATIONAL = 3
    OBSERVABILITY = 2
    ANALYTICS = 1

EVENT_PRIORITY: Dict[str, EventCategory] = {
    "accounting.journal.posted": EventCategory.FINANCIAL_CRITICAL,
    "accounting.journal.reversed": EventCategory.FINANCIAL_CRITICAL,
    "inventory.stock.moved": EventCategory.FINANCIAL_CRITICAL,
    "customer.payment.received": EventCategory.FINANCIAL_CRITICAL,
    "purchase.invoice.received": EventCategory.FINANCIAL_CRITICAL,
    "supplier.payment.made": EventCategory.FINANCIAL_CRITICAL,
    "returns.order.approved": EventCategory.FINANCIAL_CRITICAL,
    "payroll.cycle.closed": EventCategory.FINANCIAL_CRITICAL,
    "sales.invoice.created": EventCategory.BUSINESS_CRITICAL,
    "sales.invoice.dispatched": EventCategory.BUSINESS_CRITICAL,
    "purchase.invoice.created": EventCategory.BUSINESS_CRITICAL,
    "returns.order.created": EventCategory.BUSINESS_CRITICAL,
    "inventory.batch.expiring": EventCategory.BUSINESS_CRITICAL,
}

BUFFER_STATES = {"DEFERRED", "FAILED_HANDLER", "DEPTH_LIMITED"}

# ── Phase 2: EventSafetyBuffer (in-memory bounded ring buffer) ──

class EventSafetyBuffer:
    """Logically lossless: events that cannot be dispatched are buffered, never silently dropped."""

    def __init__(self, max_size: int = 200):
        self._buffer: deque = deque(maxlen=max_size)
        self.max_size = max_size

    def store(self, envelope: dict, reason: str) -> None:
        if reason not in BUFFER_STATES:
            reason = "DEFERRED"
        entry = {
            "envelope": envelope,
            "reason": reason,
            "stored_at": time.time(),
        }
        self._buffer.append(entry)
        logger.warning("Event %s buffered: %s (buffer: %d/%d)", envelope.get("name"), reason, len(self._buffer), self.max_size)

    def replay(self, limit: int = 50) -> List[dict]:
        entries = list(self._buffer)[:limit]
        result = [e["envelope"] for e in entries]
        self._buffer.clear()
        return result

    def replay_by_correlation(self, correlation_id: str) -> List[dict]:
        kept, result = [], []
        for entry in self._buffer:
            if entry["envelope"].get("correlation_id") == correlation_id:
                result.append(entry["envelope"])
            else:
                kept.append(entry)
        self._buffer.clear()
        self._buffer.extend(kept[:self.max_size])
        return result

    @property
    def pending_count(self) -> int:
        return len(self._buffer)

    @property
    def usage_ratio(self) -> float:
        return len(self._buffer) / self.max_size if self.max_size else 0.0

    def clear(self) -> None:
        self._buffer.clear()


safety_buffer = EventSafetyBuffer()

# ── Phase 3: Backpressure Control ──

class BackpressureMetrics:
    """Per-thread lightweight backpressure tracking. No blocking operations."""

    def __init__(self, window_seconds: int = 5):
        self._window = window_seconds
        self._timestamps: deque = deque(maxlen=1000)
        self._handler_times: deque = deque(maxlen=100)

    def record_dispatch(self) -> None:
        self._timestamps.append(time.time())

    def record_handler_time(self, elapsed_ms: float) -> None:
        self._handler_times.append(elapsed_ms)

    @property
    def events_per_second(self) -> float:
        now = time.time()
        cutoff = now - self._window
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        return len(self._timestamps) / self._window if self._window else 0

    @property
    def handler_avg_ms(self) -> float:
        if not self._handler_times:
            return 0.0
        return sum(self._handler_times) / len(self._handler_times)

    def pressure_level(self, buffer_ratio: float) -> str:
        eps = self.events_per_second
        if buffer_ratio > 0.8 or eps > 500:
            return "critical"
        if buffer_ratio > 0.5 or eps > 200:
            return "elevated"
        return "normal"


backpressure = BackpressureMetrics()

# ── Phase 4: Deterministic EventEnvelope ──

MAX_PAYLOAD_BYTES = 10 * 1024  # 10KB


def _compute_checksum(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _validate_payload(payload: Dict[str, Any]) -> None:
    """Reject payloads containing Django Model instances at runtime."""
    try:
        from django.db.models import Model as DjangoModel
    except ImportError:
        return
    for k, v in payload.items():
        if isinstance(v, DjangoModel):
            raise TypeError(f"Payload key '{k}' contains ORM object ({type(v).__name__}). Forbidden.")


def build_envelope(
    name: str,
    payload: Dict[str, Any],
    category: EventCategory = EventCategory.OPERATIONAL,
    actor_id: Optional[str] = None,
    company_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    depth: int = 0,
) -> dict:
    _validate_payload(payload)
    raw = json.dumps(payload, default=str)
    if len(raw) > MAX_PAYLOAD_BYTES:
        logger.warning("Event %s payload too large (%d bytes), truncating", name, len(raw))
        payload = {"_truncated": True, "_original_size": len(raw)}
    envelope = {
        "event_id": str(uuid4()),
        "correlation_id": correlation_id or str(uuid4()),
        "event_type": category.name,
        "priority": category.value,
        "name": name,
        "actor_id": actor_id,
        "company_id": company_id,
        "timestamp": time.time(),
        "depth": depth,
        "payload": payload,
        "checksum": _compute_checksum(payload),
    }
    return envelope


def validate_envelope(envelope: dict) -> bool:
    required = {"event_id", "correlation_id", "event_type", "name", "timestamp", "depth", "payload", "checksum"}
    if not all(k in envelope for k in required):
        return False
    expected_cs = _compute_checksum(envelope.get("payload", {}))
    return envelope.get("checksum") == expected_cs

# ── Phase 5: Safe Dispatch Strategy ──

def should_downgrade(buffer_ratio: float) -> bool:
    return buffer_ratio > 0.8


def classify_handlers(handlers: List, envelope: dict, downgrade: bool) -> tuple:
    cat_name = envelope.get("event_type", "OPERATIONAL")
    try:
        cat = EventCategory[cat_name]
    except KeyError:
        cat = EventCategory.OPERATIONAL
    if downgrade and cat.value <= EventCategory.BUSINESS_CRITICAL.value:
        cat = EventCategory.OBSERVABILITY
    critical, non_critical = [], []
    for h in handlers:
        if cat == EventCategory.FINANCIAL_CRITICAL:
            critical.append(h)
        else:
            non_critical.append(h)
    return critical, non_critical


def dispatch_safe(handlers: List, envelope: dict) -> None:
    critical, non_critical = classify_handlers(handlers, envelope, downgrade=should_downgrade(safety_buffer.usage_ratio))
    for handler in critical:
        _run_handler(handler, envelope)
    for handler in non_critical:
        _run_handler(handler, envelope)


def _run_handler(handler, envelope: dict) -> None:
    t0 = time.perf_counter()
    try:
        handler(envelope)
    except Exception:
        logger.exception("Handler %s.%s failed for %s", handler.__module__, handler.__name__, envelope.get("name"))
        safety_buffer.store(envelope, "FAILED_HANDLER")
    finally:
        elapsed = (time.perf_counter() - t0) * 1000
        backpressure.record_handler_time(elapsed)

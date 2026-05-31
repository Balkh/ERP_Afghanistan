"""
Governance Self-Health — Phase 5.

Governance kernel self-monitoring:
- Recursion depth tracking
- Queue backlog detection
- Handler failure monitoring
- Event amplification detection
- Listener leak detection
- Safe degradation
- Memory safety
"""
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from core.governance.kernel import GovernanceKernel, PriorityTier

logger = logging.getLogger("erp.governance.self_health")

SELF_HEALTH_VERSION = "1.0.0"

_MAX_RECURSION_DEPTH = 10
_MAX_EVENTS_PER_SECOND = 100
_MAX_LISTENER_COUNT = 50


@dataclass
class SelfHealthReport:
    healthy: bool
    recursion_depth: int
    queue_backlog: int
    handler_failures: int
    events_per_second: float
    listener_count: int
    memory_usage: dict
    degraded_tiers: List[str]
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class GovernanceHealthMonitor:
    """Monitors governance kernel health and triggers failsafe modes.

    Thread-safe. No blocking operations. Pure observation with
    self-correction triggers.
    """

    def __init__(self, kernel: GovernanceKernel):
        self._kernel = kernel
        self._lock = threading.Lock()
        self._recursion_depth: int = 0
        self._handler_failures: int = 0
        self._event_timestamps: deque = deque(maxlen=200)
        self._listener_registry: Dict[str, int] = defaultdict(int)
        self._backlog_estimate: int = 0
        self._failsafe_triggered: bool = False
        self._last_check: float = time.time()

    def enter_enforcement(self) -> bool:
        """Track enforcement recursion depth. Returns False if too deep."""
        with self._lock:
            self._recursion_depth += 1
            if self._recursion_depth > _MAX_RECURSION_DEPTH:
                logger.warning(
                    "Recursion depth %d exceeded max %d — possible governance loop",
                    self._recursion_depth, _MAX_RECURSION_DEPTH,
                )
                return False
            return True

    def leave_enforcement(self) -> None:
        with self._lock:
            self._recursion_depth = max(0, self._recursion_depth - 1)

    def record_event(self) -> None:
        now = time.time()
        with self._lock:
            self._event_timestamps.append(now)

    def record_handler_failure(self) -> None:
        with self._lock:
            self._handler_failures += 1

    def register_listener(self, name: str) -> bool:
        """Register a governance listener. Returns False if at capacity."""
        with self._lock:
            current = sum(self._listener_registry.values())
            if current >= _MAX_LISTENER_COUNT:
                logger.warning("Listener limit reached (%d)", _MAX_LISTENER_COUNT)
                return False
            self._listener_registry[name] += 1
            return True

    def unregister_listener(self, name: str) -> None:
        with self._lock:
            if name in self._listener_registry:
                self._listener_registry[name] -= 1
                if self._listener_registry[name] <= 0:
                    del self._listener_registry[name]

    def tick_backlog(self, delta: int = 1) -> None:
        with self._lock:
            self._backlog_estimate += delta

    def pop_backlog(self, delta: int = 1) -> None:
        with self._lock:
            self._backlog_estimate = max(0, self._backlog_estimate - delta)

    def check(self) -> SelfHealthReport:
        """Run self-health check and trigger failsafe if necessary."""
        now = time.time()
        interval = now - self._last_check

        with self._lock:
            rd = self._recursion_depth
            hf = self._handler_failures
            backlog = self._backlog_estimate
            listeners = sum(self._listener_registry.values())

            recent_events = [t for t in self._event_timestamps
                             if t > now - 1.0]
            eps = len(recent_events) / max(interval, 0.1)

            memory = {
                "recursion_depth": rd,
                "handler_failures": hf,
                "listener_count": listeners,
                "events_per_second": round(eps, 1),
                "event_buffer_used": len(self._event_timestamps),
                "event_buffer_capacity": self._event_timestamps.maxlen,
            }

        warnings = []
        degraded = []

        if rd > 5:
            warnings.append(f"High recursion depth: {rd}")
        if eps > _MAX_EVENTS_PER_SECOND:
            warnings.append(f"Event rate {eps:.0f}/s exceeds limit {_MAX_EVENTS_PER_SECOND}/s")
        if backlog > 20:
            warnings.append(f"Queue backlog: {backlog}")
        if hf > 5:
            warnings.append(f"Handler failures: {hf}")
        if listeners > _MAX_LISTENER_COUNT * 0.8:
            warnings.append(f"Listener count high: {listeners}/{_MAX_LISTENER_COUNT}")

        if not self._failsafe_triggered and (
            eps > _MAX_EVENTS_PER_SECOND * 2 or
            rd > _MAX_RECURSION_DEPTH
        ):
            logger.warning("Governance health degraded — enabling failsafe")
            self._kernel.enable_failsafe()
            self._failsafe_triggered = True
            degraded.append("low_priority")

        if eps > _MAX_EVENTS_PER_SECOND:
            degraded.append("event_driven")

        healthy = len(warnings) == 0

        self._last_check = now

        return SelfHealthReport(
            healthy=healthy,
            recursion_depth=rd,
            queue_backlog=backlog,
            handler_failures=hf,
            events_per_second=round(eps, 1),
            listener_count=listeners,
            memory_usage=memory,
            degraded_tiers=degraded,
            warnings=warnings,
        )

    def reset(self) -> None:
        with self._lock:
            self._recursion_depth = 0
            self._handler_failures = 0
            self._event_timestamps.clear()
            self._listener_registry.clear()
            self._backlog_estimate = 0
            self._failsafe_triggered = False

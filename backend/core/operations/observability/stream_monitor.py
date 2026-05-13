"""
Phase 5B.4 — Real-Time Stream Monitor.

Read-only event stream monitoring with descriptive metrics.
NO alerting with priority/urgency bias. All outputs are informational only.

Capabilities:
- Event throughput metrics (events/sec)
- Domain-level event segmentation
- Source type distribution
- Lag monitoring (descriptive only)
- Stream health status
"""
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Deque

from core.operations.truth.models import Domain, SourceType, Event
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.observability.models import (
    StreamMetrics, StreamHealth,
)

logger = logging.getLogger('erp.observability.stream')

STREAM_MONITOR_VERSION = "1.0.0"
METRICS_WINDOW_SECONDS = 60


class RealTimeStreamMonitor:
    """Read-only stream monitor with descriptive metrics.

    All outputs are:
    - Informational only
    - Non-actionable
    - Deterministic
    - Never amplified or prioritized
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._lock = Lock()
        self._event_timestamps: Deque[float] = deque(maxlen=10000)
        self._domain_counts: Dict[str, int] = defaultdict(int)
        self._source_counts: Dict[str, int] = defaultdict(int)
        self._last_event_time: float = 0.0
        self._total_observed: int = 0

    def observe_event(self, event: Event) -> None:
        """Record an event observation (read-only subscription).

        NEVER modifies the event or store.
        """
        with self._lock:
            now = time.time()
            self._event_timestamps.append(now)
            self._domain_counts[event.domain.value] += 1
            self._source_counts[event.source_type.value] += 1
            self._last_event_time = now
            self._total_observed += 1

    def get_metrics(self) -> StreamMetrics:
        """Get current stream metrics.

        Deterministic — same observation window → same metrics.
        """
        with self._lock:
            now = time.time()
            cutoff = now - METRICS_WINDOW_SECONDS
            recent = [t for t in self._event_timestamps if t >= cutoff]

            eps = len(recent) / METRICS_WINDOW_SECONDS if recent else 0.0

            lag = 0
            all_events = self._store.get_all()
            if all_events:
                try:
                    last_ts = all_events[-1].timestamp
                    if last_ts.endswith("Z"):
                        last_ts = last_ts[:-1]
                    last_dt = datetime.fromisoformat(last_ts)
                    now_dt = datetime.utcnow()
                    lag = int((now_dt - last_dt).total_seconds())
                    if lag < 0:
                        lag = 0
                except (ValueError, TypeError):
                    lag = 0

            health = StreamHealth.HEALTHY
            if lag > 300:
                health = StreamHealth.STALLED
            elif lag > 60:
                health = StreamHealth.LAGGING

            return StreamMetrics(
                total_events_received=self._total_observed,
                events_per_second=round(eps, 2),
                events_by_domain=dict(self._domain_counts),
                events_by_source=dict(self._source_counts),
                last_event_timestamp=all_events[-1].timestamp if all_events else "",
                health=health,
                lag_seconds=lag,
            )

    def get_domain_throughput(self, domain: Domain) -> Dict[str, Any]:
        """Get throughput metrics for a specific domain.

        Informational only — never influences behavior.
        """
        with self._lock:
            now = time.time()
            cutoff = now - METRICS_WINDOW_SECONDS
            domain_events = [
                t for t in self._event_timestamps
                if t >= cutoff
            ]
            return {
                "domain": domain.value,
                "events_in_window": len(domain_events),
                "total_observed": self._domain_counts.get(domain.value, 0),
                "window_seconds": METRICS_WINDOW_SECONDS,
                "sampled_at": datetime.utcnow().isoformat() + "Z",
            }

    def get_store_summary(self) -> Dict[str, Any]:
        """Read-only summary of store state."""
        all_events = self._store.get_all()
        return {
            "total_events_stored": len(all_events),
            "events_by_domain": self._store.count_by_domain(),
            "events_by_source": self._store.count_by_source(),
            "observed_events": self._total_observed,
            "stream_health": self.get_metrics().health.value,
        }

    def reset(self) -> None:
        """Reset monitor state. For testing only."""
        with self._lock:
            self._event_timestamps.clear()
            self._domain_counts.clear()
            self._source_counts.clear()
            self._last_event_time = 0.0
            self._total_observed = 0

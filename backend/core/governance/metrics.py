"""
Governance Metrics — Phase 4.

Tracks enforcement latency, denial counts, invariant failures,
readiness degradation, and policy conflicts.
Noise-controlled: no duplicate metrics, bounded memory.
"""
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

METRICS_VERSION = "1.0.0"


@dataclass
class MetricPoint:
    value: float
    timestamp: float = field(default_factory=time.time)


class GovernanceMetrics:
    """Lightweight governance metrics tracker.

    Bounded memory — retains only recent data points.
    Thread-safe for concurrent enforcement.
    """

    def __init__(self, max_points_per_metric: int = 100):
        self._max = max_points_per_metric
        self._lock = threading.Lock()
        self._latency: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_points_per_metric)
        )
        self._denials: Dict[str, int] = defaultdict(int)
        self._invariant_failures: Dict[str, int] = defaultdict(int)
        self._readiness_scores: deque = deque(maxlen=50)
        self._enforcement_count: int = 0
        self._error_count: int = 0
        self._start_time: float = time.time()

    def record_enforcement(
        self,
        policy_id: str,
        allowed: bool,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self._enforcement_count += 1
            self._latency[policy_id].append(MetricPoint(latency_ms))
            if not allowed:
                self._denials[policy_id] += 1

    def record_error(self) -> None:
        with self._lock:
            self._error_count += 1

    def record_invariant_failure(self, invariant_id: str) -> None:
        with self._lock:
            self._invariant_failures[invariant_id] += 1

    def record_readiness(self, passed: int, total: int) -> None:
        score = (passed / total * 100) if total > 0 else 0
        with self._lock:
            self._readiness_scores.append(MetricPoint(score))

    def get_latency_stats(self, policy_id: str) -> dict:
        with self._lock:
            points = list(self._latency.get(policy_id, []))
        if not points:
            return {"avg": 0, "max": 0, "min": 0, "count": 0}
        values = [p.value for p in points]
        return {
            "avg": round(sum(values) / len(values), 2),
            "max": round(max(values), 2),
            "min": round(min(values), 2),
            "count": len(values),
            "p95": _percentile(values, 95),
        }

    def snapshot(self) -> dict:
        """Return current metrics snapshot."""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                "uptime_seconds": round(uptime, 1),
                "total_enforcements": self._enforcement_count,
                "total_errors": self._error_count,
                "denials_by_policy": dict(self._denials),
                "invariant_failures": dict(self._invariant_failures),
                "readiness_checkpoints": len(self._readiness_scores),
            }

    def reset(self) -> None:
        with self._lock:
            self._latency.clear()
            self._denials.clear()
            self._invariant_failures.clear()
            self._readiness_scores.clear()
            self._enforcement_count = 0
            self._error_count = 0
            self._start_time = time.time()


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(sorted_v):
        return sorted_v[-1]
    return sorted_v[f] + (k - f) * (sorted_v[c] - sorted_v[f])


# Singleton
_instance = None
_lock = threading.Lock()


def get_metrics() -> GovernanceMetrics:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GovernanceMetrics()
    return _instance

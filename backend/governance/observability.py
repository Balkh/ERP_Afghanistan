"""
Section 10 — Governance Observability & Metrics.
Lightweight metrics collection for governance operations.
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class MetricPoint:
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: float


class GovernanceMetricsCollector:

    def __init__(self, max_points: int = 1000):
        self._points: List[MetricPoint] = []
        self._max_points = max_points

    def record(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        if len(self._points) >= self._max_points:
            self._points.pop(0)
        self._points.append(MetricPoint(name, value, labels or {}, time.time()))

    def get_stats(self, name: str, window_seconds: float = 300) -> Dict:
        now = time.time()
        filtered = [p for p in self._points if p.name == name and (now - p.timestamp) < window_seconds]
        if not filtered:
            return {"name": name, "count": 0, "avg": 0, "min": 0, "max": 0}
        values = [p.value for p in filtered]
        return {
            "name": name,
            "count": len(values),
            "avg": round(sum(values) / len(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
        }

    def snapshot(self) -> Dict[str, Dict]:
        names = set(p.name for p in self._points)
        return {name: self.get_stats(name, 3600) for name in names}

    def governance_score(self) -> float:
        """Aggregate governance health score based on recent metrics."""
        gate_results = self.get_stats("gate.passed", 86400)
        total_gates = gate_results["count"]
        if total_gates == 0:
            return 100.0
        # Score = percentage of gates that passed
        passed = gate_results["max"]  # max=1 if any passed, avg better
        return round((gate_results["avg"] / 1.0) * 100, 1) if gate_results["count"] > 0 else 100.0


GOVERNANCE_METRICS = GovernanceMetricsCollector()


def record_gate_result(gate_name: str, passed: bool) -> None:
    GOVERNANCE_METRICS.record("gate.passed", 1.0 if passed else 0.0, {"gate": gate_name})
    GOVERNANCE_METRICS.record(f"gate.{gate_name}.passed", 1.0 if passed else 0.0)


def record_validation_duration(name: str, duration_ms: float) -> None:
    GOVERNANCE_METRICS.record("validation.duration_ms", duration_ms, {"name": name})


def get_health_snapshot() -> Dict:
    return GOVERNANCE_METRICS.snapshot()

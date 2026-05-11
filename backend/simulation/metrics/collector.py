import logging
import time
from collections import defaultdict, deque
from threading import RLock
from typing import Any, Dict, List


logger = logging.getLogger('erp.simulation.metrics')


class SimulationMetricsCollector:
    """
    Bounded-memory metrics collector for simulation infrastructure.
    Tracks operations, latency, successes, failures, rollbacks.
    No unbounded growth. Safe concurrent access.
    """

    def __init__(self, max_metric_history: int = 5000):
        self._lock = RLock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._max_history = max_metric_history
        self._timeline: deque = deque(maxlen=max_metric_history)

    def increment(self, metric_name: str, value: int = 1):
        with self._lock:
            self._counters[metric_name] += value

    def record_latency(self, operation: str, seconds: float):
        with self._lock:
            self._latencies[operation].append(seconds)

    def record_timeline(self, metric_name: str, value: Any):
        with self._lock:
            self._timeline.append((metric_name, value))

    def get_counter(self, metric_name: str) -> int:
        with self._lock:
            return self._counters.get(metric_name, 0)

    def get_latency_stats(self, operation: str) -> Dict[str, float]:
        with self._lock:
            vals = self._latencies.get(operation, [])
            if not vals:
                return {'count': 0, 'min': 0.0, 'max': 0.0,
                        'avg': 0.0, 'sum': 0.0}
            vals_list = list(vals)
            return {
                'count': len(vals_list),
                'min': min(vals_list),
                'max': max(vals_list),
                'avg': sum(vals_list) / len(vals_list),
                'sum': sum(vals_list),
            }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            latencies_summary = {}
            for op in self._latencies:
                latencies_summary[op] = self.get_latency_stats(op)
            return {
                'counters': dict(self._counters),
                'latencies': latencies_summary,
                'timeline_count': len(self._timeline),
            }

    def reset(self):
        with self._lock:
            self._counters.clear()
            self._latencies.clear()
            self._timeline.clear()

    @property
    def total_operations(self) -> int:
        with self._lock:
            return sum(self._counters.values())

    @property
    def counters(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

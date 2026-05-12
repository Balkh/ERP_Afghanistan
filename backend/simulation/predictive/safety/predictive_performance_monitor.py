import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.safety.performance')


class PredictivePerformanceMonitor:
    def __init__(self, max_records: int = 200):
        self._max_records = max_records
        self._latency_records: deque = deque(maxlen=max_records)
        self._operation_counts: Dict[str, int] = {}

    def measure(self, operation_name: str) -> 'TimingContext':
        return TimingContext(self, operation_name)

    def record_latency(self, operation: str, latency_ms: float):
        self._latency_records.append({
            'operation': operation,
            'latency_ms': round(latency_ms, 2),
        })
        self._operation_counts[operation] = self._operation_counts.get(operation, 0) + 1

    def get_average_latency(self, operation: str) -> float:
        relevant = [r for r in self._latency_records if r['operation'] == operation]
        if not relevant:
            return 0.0
        return sum(r['latency_ms'] for r in relevant) / len(relevant)

    def get_total_latency(self, operation: str) -> float:
        relevant = [r for r in self._latency_records if r['operation'] == operation]
        return sum(r['latency_ms'] for r in relevant)

    def get_operation_count(self, operation: str) -> int:
        return self._operation_counts.get(operation, 0)

    def get_all_metrics(self) -> Dict[str, Any]:
        return {
            'total_operations': sum(self._operation_counts.values()),
            'unique_operations': len(self._operation_counts),
            'total_records': len(self._latency_records),
            'operations': dict(self._operation_counts),
            'avg_latencies': {
                op: self.get_average_latency(op)
                for op in self._operation_counts
            },
        }

    @property
    def record_count(self) -> int:
        return len(self._latency_records)

    def clear(self):
        self._latency_records.clear()
        self._operation_counts.clear()


class TimingContext:
    def __init__(self, monitor: PredictivePerformanceMonitor, operation: str):
        self._monitor = monitor
        self._operation = operation
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start is not None:
            elapsed = (time.time() - self._start) * 1000
            self._monitor.record_latency(self._operation, elapsed)

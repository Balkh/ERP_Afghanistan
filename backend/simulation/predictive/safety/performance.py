import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.safety.performance')


class PredictivePerformanceMonitor:
    def __init__(self, max_samples: int = 100):
        self._max_samples = max_samples
        self._forecast_latencies: deque = deque(maxlen=max_samples)
        self._scoring_latencies: deque = deque(maxlen=max_samples)
        self._warning_latencies: deque = deque(maxlen=max_samples)
        self._trend_latencies: deque = deque(maxlen=max_samples)

    def record_forecast_latency(self, latency_ms: float):
        self._forecast_latencies.append(latency_ms)

    def record_scoring_latency(self, latency_ms: float):
        self._scoring_latencies.append(latency_ms)

    def record_warning_latency(self, latency_ms: float):
        self._warning_latencies.append(latency_ms)

    def record_trend_latency(self, latency_ms: float):
        self._trend_latencies.append(latency_ms)

    def measure_call(self, category: str, fn, *args, **kwargs):
        start = time.monotonic()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = (time.monotonic() - start) * 1000
            if category == 'forecast':
                self.record_forecast_latency(elapsed)
            elif category == 'scoring':
                self.record_scoring_latency(elapsed)
            elif category == 'warning':
                self.record_warning_latency(elapsed)
            elif category == 'trend':
                self.record_trend_latency(elapsed)

    def get_latency_report(self) -> Dict[str, Dict[str, float]]:
        return {
            'forecast': self._summarize(self._forecast_latencies),
            'scoring': self._summarize(self._scoring_latencies),
            'warning_generation': self._summarize(self._warning_latencies),
            'trend_analysis': self._summarize(self._trend_latencies),
        }

    def _summarize(self, samples: deque) -> Dict[str, float]:
        if not samples:
            return {'avg_ms': 0.0, 'max_ms': 0.0, 'min_ms': 0.0, 'samples': 0}
        vals = list(samples)
        return {
            'avg_ms': round(sum(vals) / len(vals), 2),
            'max_ms': round(max(vals), 2),
            'min_ms': round(min(vals), 2),
            'samples': len(vals),
        }

    def clear(self):
        self._forecast_latencies.clear()
        self._scoring_latencies.clear()
        self._warning_latencies.clear()
        self._trend_latencies.clear()

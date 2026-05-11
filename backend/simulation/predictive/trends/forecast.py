import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.trends.forecast')


FORECAST_WINDOWS = {
    'short_term': 5,
    'medium_term': 20,
    'long_term': 50,
}


class DriftForecastWindow:
    def __init__(self, max_history: int = 500):
        self._max_history = max_history
        self._history: deque = deque(maxlen=max_history)

    def record(self, tick: int, mismatch_count: int,
               severity_map: Dict[str, int],
               module_map: Dict[str, int]):
        self._history.append({
            'tick': tick,
            'mismatch_count': mismatch_count,
            'severity_map': dict(severity_map),
            'module_map': dict(module_map),
        })

    def forecast(self) -> Dict[str, Any]:
        samples = list(self._history)
        if len(samples) < 2:
            return {
                'short_term': None, 'medium_term': None, 'long_term': None,
                'predicted_drift_density': 0.0,
                'probable_escalation_regions': [],
                'sample_size': len(samples),
            }
        base = samples[-1]['mismatch_count']
        rate = self._estimate_rate(samples)
        windows = {}
        for name, ticks in FORECAST_WINDOWS.items():
            predicted = base + (rate * ticks)
            windows[name] = max(0, round(predicted, 2))
        escalation = self._predict_escalation_regions(samples)
        return {
            'short_term': windows['short_term'],
            'medium_term': windows['medium_term'],
            'long_term': windows['long_term'],
            'predicted_drift_density': windows['medium_term'],
            'probable_escalation_regions': escalation,
            'sample_size': len(samples),
        }

    def _estimate_rate(self, samples: List[Dict]) -> float:
        if len(samples) < 2:
            return 0.0
        mid = len(samples) // 2
        first = samples[:mid]
        second = samples[mid:]
        first_avg = sum(s['mismatch_count'] for s in first) / max(len(first), 1)
        second_avg = sum(s['mismatch_count'] for s in second) / max(len(second), 1)
        return second_avg - first_avg

    def _predict_escalation_regions(self, samples: List[Dict]) -> List[str]:
        recent = samples[-10:] if len(samples) >= 10 else samples
        module_scores: Dict[str, float] = {}
        for s in recent:
            for module, count in s['module_map'].items():
                module_scores[module] = module_scores.get(module, 0) + count
        threshold = (sum(module_scores.values()) / max(len(module_scores), 1)) * 1.5 if module_scores else 0
        return sorted([m for m, c in module_scores.items() if c >= threshold])

    @property
    def record_count(self) -> int:
        return len(self._history)

    def clear(self):
        self._history.clear()

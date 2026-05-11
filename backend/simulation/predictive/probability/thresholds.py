import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('erp.simulation.predictive.probability.thresholds')


class ProbabilityThresholdManager:
    def __init__(self):
        self._thresholds: Dict[str, float] = {
            'warning': 25.0,
            'escalation': 50.0,
            'critical': 75.0,
        }

    def get_threshold(self, level: str) -> float:
        return self._thresholds.get(level, 100.0)

    def set_threshold(self, level: str, value: float):
        if level not in self._thresholds:
            raise ValueError(f"Unknown threshold level: {level}")
        self._thresholds[level] = max(0.0, min(100.0, value))

    def classify(self, value: float) -> str:
        if value >= self._thresholds['critical']:
            return 'critical'
        if value >= self._thresholds['escalation']:
            return 'escalation'
        if value >= self._thresholds['warning']:
            return 'warning'
        return 'normal'

    def get_all_thresholds(self) -> Dict[str, float]:
        return dict(self._thresholds)

    @property
    def threshold_count(self) -> int:
        return len(self._thresholds)

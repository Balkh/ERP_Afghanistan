import logging
from typing import Any, Dict, Optional

from simulation.predictive.models import WarningSeverity

logger = logging.getLogger('erp.simulation.predictive.probability.thresholds')

DEFAULT_THRESHOLDS: Dict[str, float] = {
    'warning': 25.0,
    'escalation': 50.0,
    'critical': 75.0,
}


class ProbabilityThresholdManager:
    def __init__(self):
        self._thresholds: Dict[str, float] = dict(DEFAULT_THRESHOLDS)

    def get_threshold(self, name: str) -> float:
        return self._thresholds.get(name, 50.0)

    def set_threshold(self, name: str, value: float):
        clamped = min(max(value, 0.0), 100.0)
        self._thresholds[name] = clamped

    def classify_probability(self, probability: float) -> WarningSeverity:
        if probability >= self._thresholds.get('critical', 75.0):
            return WarningSeverity.CRITICAL
        if probability >= self._thresholds.get('escalation', 50.0):
            return WarningSeverity.HIGH
        if probability >= self._thresholds.get('warning', 25.0):
            return WarningSeverity.MEDIUM
        return WarningSeverity.LOW

    def is_warning(self, probability: float) -> bool:
        return probability >= self._thresholds.get('warning', 25.0)

    def is_escalation(self, probability: float) -> bool:
        return probability >= self._thresholds.get('escalation', 50.0)

    def is_critical(self, probability: float) -> bool:
        return probability >= self._thresholds.get('critical', 75.0)

    def get_all_thresholds(self) -> Dict[str, float]:
        return dict(self._thresholds)

    def reset_to_defaults(self):
        self._thresholds.clear()
        self._thresholds.update(DEFAULT_THRESHOLDS)

    def clear(self):
        self._thresholds.clear()
        self._thresholds.update(DEFAULT_THRESHOLDS)

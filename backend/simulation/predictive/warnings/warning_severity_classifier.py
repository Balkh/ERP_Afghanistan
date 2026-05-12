import logging
from typing import Any, Dict, Optional

from simulation.predictive.models import WarningSeverity

logger = logging.getLogger('erp.simulation.predictive.warnings.severity')

SEVERITY_LEVELS = {
    WarningSeverity.INFO: 0,
    WarningSeverity.LOW: 1,
    WarningSeverity.MEDIUM: 2,
    WarningSeverity.HIGH: 3,
    WarningSeverity.CRITICAL: 4,
}


class WarningSeverityClassifier:
    def __init__(self):
        self._classification_counts: Dict[str, int] = {}

    def classify(self, probability: float, trend_direction: str,
                 module_count: int, chain_complexity: int) -> WarningSeverity:
        if probability >= 75 or trend_direction == 'critical' or module_count >= 4:
            return WarningSeverity.CRITICAL
        if probability >= 50 or trend_direction == 'worsening' or module_count >= 3:
            return WarningSeverity.HIGH
        if probability >= 25 or chain_complexity >= 3:
            return WarningSeverity.MEDIUM
        if probability >= 10:
            return WarningSeverity.LOW
        return WarningSeverity.INFO

    def get_numeric_level(self, severity: WarningSeverity) -> int:
        return SEVERITY_LEVELS.get(severity, 0)

    def is_at_least(self, severity: WarningSeverity,
                    minimum: WarningSeverity) -> bool:
        return self.get_numeric_level(severity) >= self.get_numeric_level(minimum)

    def clear(self):
        self._classification_counts.clear()

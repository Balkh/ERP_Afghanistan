import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('erp.simulation.predictive.warnings.classifier')


WARNING_LEVELS = ['info', 'low', 'medium', 'high', 'critical']


class WarningSeverityClassifier:
    def classify(self, score: float, probability: float,
                 escalation: bool = False) -> str:
        if escalation or probability >= 75 or score >= 80:
            return 'critical'
        if probability >= 50 or score >= 60:
            return 'high'
        if probability >= 25 or score >= 40:
            return 'medium'
        if probability >= 10 or score >= 20:
            return 'low'
        return 'info'

    def get_level_value(self, level: str) -> int:
        mapping = {'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        return mapping.get(level, 0)

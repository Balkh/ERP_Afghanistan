"""Severity classification for recovery incidents."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import IntegritySeverity


class SeverityClassifier:
    def __init__(self, max_history: int = 200):
        self._classification_history: deque = deque(maxlen=max_history)

    def classify(self, risk_score: float, has_conflicts: bool = False,
                 has_irreversible: bool = False, containment_active: bool = False,
                 workflows_affected: int = 0) -> Dict[str, Any]:
        if has_irreversible or has_conflicts or risk_score >= 80:
            severity = IntegritySeverity.CRITICAL
        elif risk_score >= 55 or workflows_affected >= 5:
            severity = IntegritySeverity.HIGH
        elif risk_score >= 30 or workflows_affected >= 3:
            severity = IntegritySeverity.MEDIUM
        elif risk_score >= 10:
            severity = IntegritySeverity.LOW
        else:
            severity = IntegritySeverity.INFO
        self._classification_history.append({
            'risk_score': risk_score, 'severity': severity.value,
        })
        return {'severity': severity.value, 'risk_score': risk_score,
                'containment_active': containment_active,
                'workflows_affected': workflows_affected}

    def get_classification_count(self) -> int:
        return len(self._classification_history)

    def clear(self):
        self._classification_history.clear()

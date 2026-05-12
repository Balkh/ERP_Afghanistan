from collections import deque
from typing import Any, Dict, List, Optional
from simulation.control_center.models import (
    OperationalState, IntelligenceSeverity, OperationalPriority,
)


class IntelligenceStateClassifier:
    def __init__(self, max_history: int = 200):
        self._classification_history: deque = deque(maxlen=max_history)

    def classify(self, severity_score: float, critical_count: int,
                 incident_count: int, active_signals: int,
                 source_count: int) -> Dict[str, Any]:
        state = self._determine_state(severity_score, critical_count)
        severity = self._determine_severity(severity_score)
        priority = self._determine_priority(severity_score, critical_count, incident_count)
        cascading = self._detect_cascading(critical_count, incident_count, active_signals)
        self._classification_history.append({
            'state': state.value, 'severity': severity.value,
            'priority': priority.value, 'cascading': cascading,
        })
        return {
            'operational_state': state.value,
            'severity': severity.value,
            'priority': priority.value,
            'cascading_risk': cascading,
            'classification': f"{state.value}_{severity.value}",
        }

    def _determine_state(self, score: float,
                         critical_count: int) -> OperationalState:
        if critical_count > 5:
            return OperationalState.EMERGENCY
        if score >= 0.7:
            return OperationalState.CRITICAL
        if score >= 0.4:
            return OperationalState.DEGRADED
        if critical_count > 0:
            return OperationalState.DEGRADED
        return OperationalState.NORMAL

    def _determine_severity(self, score: float) -> IntelligenceSeverity:
        if score >= 0.8:
            return IntelligenceSeverity.CRITICAL
        if score >= 0.5:
            return IntelligenceSeverity.HIGH
        if score >= 0.3:
            return IntelligenceSeverity.MEDIUM
        if score > 0:
            return IntelligenceSeverity.LOW
        return IntelligenceSeverity.INFO

    def _determine_priority(self, score: float, critical_count: int,
                            incident_count: int) -> OperationalPriority:
        if critical_count > 5:
            return OperationalPriority.CRITICAL
        if score >= 0.7 or critical_count > 2:
            return OperationalPriority.HIGH
        if score >= 0.4 or incident_count > 3:
            return OperationalPriority.MEDIUM
        if score > 0 or incident_count > 0:
            return OperationalPriority.LOW
        return OperationalPriority.LOWEST

    def _detect_cascading(self, critical_count: int, incident_count: int,
                          active_signals: int) -> bool:
        return critical_count > 3 and incident_count > 2 and active_signals > 20

    def clear(self):
        self._classification_history.clear()

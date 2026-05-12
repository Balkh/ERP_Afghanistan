"""Stateless incident classification from signals and records."""
from typing import Any, Dict, List

from simulation.control_center.models import (
    IncidentRecord,
    IncidentStatus,
    IntelligenceSeverity,
    OperationalPriority,
    OperationalSignal,
    SignalType,
)


class IncidentClassifier:
    """Stateless classifier for signals and incident records."""

    SEVERITY_TO_PRIORITY = {
        IntelligenceSeverity.CRITICAL: OperationalPriority.CRITICAL,
        IntelligenceSeverity.HIGH: OperationalPriority.HIGH,
        IntelligenceSeverity.MEDIUM: OperationalPriority.MEDIUM,
        IntelligenceSeverity.LOW: OperationalPriority.LOW,
        IntelligenceSeverity.INFO: OperationalPriority.LOWEST,
    }

    STALE_THRESHOLD_TICKS = 50

    def classify_signal(self, signal: OperationalSignal) -> Dict[str, Any]:
        severity = signal.severity
        priority = self.SEVERITY_TO_PRIORITY.get(
            severity, OperationalPriority.LOWEST
        )
        return {
            "incident_type": f"{signal.signal_type.value}_incident",
            "severity": severity,
            "priority": priority,
            "requires_escalation": severity
            in (IntelligenceSeverity.CRITICAL, IntelligenceSeverity.HIGH),
        }

    def classify_incident(self, record: IncidentRecord) -> Dict[str, Any]:
        is_stale = (
            record.status == IncidentStatus.OPEN
            and record.tick_detected > 0
            and record.occurrence_count >= self.STALE_THRESHOLD_TICKS
        )

        if record.severity == IntelligenceSeverity.CRITICAL:
            recommended = "immediate investigation and escalation"
        elif record.severity == IntelligenceSeverity.HIGH:
            recommended = "prioritize investigation within next cycle"
        elif record.severity == IntelligenceSeverity.MEDIUM:
            recommended = "schedule investigation during normal cycle"
        elif record.severity == IntelligenceSeverity.LOW:
            recommended = "monitor and close if no further activity"
        else:
            recommended = "review and close"

        return {
            "classification": f"{record.signal_type.value}_incident",
            "severity_label": record.severity.value,
            "is_stale": is_stale,
            "recommended_action": recommended,
        }

    def batch_classify(
        self, signals: List[OperationalSignal]
    ) -> List[Dict[str, Any]]:
        return [self.classify_signal(s) for s in signals]

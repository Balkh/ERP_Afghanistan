"""Escalation engine with bounded history and level evaluation."""
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List

from simulation.control_center.models import (
    EscalationLevel,
    IncidentRecord,
    IntelligenceSeverity,
    OperationalPriority,
)


@dataclass
class EscalationRecord:
    incident_id: str
    level: EscalationLevel
    reason: str
    tick: int = 0


_LEVEL_ORDER = [
    EscalationLevel.NONE,
    EscalationLevel.OBSERVE,
    EscalationLevel.WARN,
    EscalationLevel.ESCALATE,
    EscalationLevel.EMERGENCY,
]

_LEVEL_MAP = {lvl: idx for idx, lvl in enumerate(_LEVEL_ORDER)}

_ACTIVE_COUNT_BUMP_THRESHOLD = 10


def _bump_level(level: EscalationLevel) -> EscalationLevel:
    idx = _LEVEL_MAP.get(level, 0)
    if idx < len(_LEVEL_ORDER) - 1:
        return _LEVEL_ORDER[idx + 1]
    return level


class EscalationEngine:
    """Evaluates and records incident escalation levels."""

    def __init__(self, max_escalations: int = 200):
        self.max_escalations = max(max_escalations, 1)
        self._history: deque = deque(maxlen=self.max_escalations)

    def evaluate_escalation(
        self,
        incident: IncidentRecord,
        tick: int,
        active_incident_count: int,
    ) -> Dict[str, Any]:
        severity = incident.severity
        ticks_open = tick - incident.tick_detected

        if severity == IntelligenceSeverity.CRITICAL and ticks_open > 10:
            level = EscalationLevel.EMERGENCY
        elif severity == IntelligenceSeverity.HIGH and ticks_open > 20:
            level = EscalationLevel.ESCALATE
        elif severity == IntelligenceSeverity.MEDIUM and ticks_open > 30:
            level = EscalationLevel.WARN
        elif severity == IntelligenceSeverity.LOW and ticks_open > 50:
            level = EscalationLevel.OBSERVE
        else:
            level = EscalationLevel.NONE

        if active_incident_count > _ACTIVE_COUNT_BUMP_THRESHOLD:
            level = _bump_level(level)

        reason = (
            f"Severity={severity.value}, ticks_open={ticks_open}, "
            f"active_incidents={active_incident_count}"
        )

        priority = self._level_to_priority(level)

        return {
            "escalation_level": level,
            "reason": reason,
            "priority": priority,
        }

    def record_escalation(
        self,
        incident_id: str,
        level: EscalationLevel,
        reason: str,
    ) -> Dict[str, Any]:
        record = EscalationRecord(
            incident_id=incident_id, level=level, reason=reason
        )
        self._history.append(record)
        return {
            "incident_id": incident_id,
            "level": level,
            "reason": reason,
        }

    def get_escalation_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "incident_id": r.incident_id,
                "level": r.level,
                "reason": r.reason,
            }
            for r in self._history
        ]

    def get_escalation_count(self) -> int:
        return len(self._history)

    def clear(self) -> None:
        self._history.clear()

    @staticmethod
    def _level_to_priority(level: EscalationLevel) -> OperationalPriority:
        mapping = {
            EscalationLevel.EMERGENCY: OperationalPriority.CRITICAL,
            EscalationLevel.ESCALATE: OperationalPriority.HIGH,
            EscalationLevel.WARN: OperationalPriority.MEDIUM,
            EscalationLevel.OBSERVE: OperationalPriority.LOW,
            EscalationLevel.NONE: OperationalPriority.LOWEST,
        }
        return mapping.get(level, OperationalPriority.LOWEST)

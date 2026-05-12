"""Incident status lifecycle with bounded transition history."""
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List

from simulation.control_center.models import IncidentRecord, IncidentStatus


@dataclass
class StatusTransition:
    old_status: IncidentStatus
    new_status: IncidentStatus
    tick: int
    incident_id: str


_VALID_TRANSITIONS: Dict[IncidentStatus, List[IncidentStatus]] = {
    IncidentStatus.OPEN: [
        IncidentStatus.ACKNOWLEDGED,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CLOSED,
    ],
    IncidentStatus.ACKNOWLEDGED: [
        IncidentStatus.INVESTIGATING,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ],
    IncidentStatus.INVESTIGATING: [
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ],
    IncidentStatus.RESOLVED: [
        IncidentStatus.CLOSED,
        IncidentStatus.REOPENED,
    ],
    IncidentStatus.CLOSED: [
        IncidentStatus.REOPENED,
    ],
    IncidentStatus.REOPENED: [
        IncidentStatus.ACKNOWLEDGED,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CLOSED,
    ],
}

_TERMINAL_STATUSES = frozenset({IncidentStatus.CLOSED})


class IncidentLifecycle:
    """Manages incident status transitions with validation and history."""

    def __init__(self, max_history: int = 500):
        self.max_history = max(max_history, 1)
        self._history: deque = deque(maxlen=self.max_history)

    def transition(
        self,
        incident: IncidentRecord,
        new_status: IncidentStatus,
        tick: int,
    ) -> Dict[str, Any]:
        old_status = incident.status
        valid = self.get_valid_transitions(old_status)
        transition_valid = new_status in valid
        if transition_valid:
            incident.status = new_status
        self._history.append(
            StatusTransition(
                old_status=old_status,
                new_status=new_status,
                tick=tick,
                incident_id=incident.incident_id,
            )
        )
        return {
            "success": transition_valid,
            "old_status": old_status,
            "new_status": new_status,
            "transition_valid": transition_valid,
        }

    def get_valid_transitions(
        self, current_status: IncidentStatus
    ) -> List[IncidentStatus]:
        return list(_VALID_TRANSITIONS.get(current_status, []))

    def is_terminal(self, status: IncidentStatus) -> bool:
        return status in _TERMINAL_STATUSES

    def get_transition_count(self) -> int:
        return len(self._history)

    def clear(self) -> None:
        self._history.clear()

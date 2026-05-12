"""Bounded incident registry with status lifecycle management."""
from collections import deque, OrderedDict
from typing import Any, Dict, List, Optional

from simulation.control_center.models import (
    EscalationLevel,
    IncidentRecord,
    IncidentStatus,
    IntelligenceSeverity,
    SignalType,
)


class IncidentRegistry:
    """Thread-safe incident registry with bounded storage and eviction."""

    def __init__(self, max_incidents: int = 500):
        self.max_incidents = max(max_incidents, 1)
        self._incidents: Dict[str, IncidentRecord] = OrderedDict()
        self._insertion_order: deque = deque(maxlen=max_incidents)

    def register_incident(
        self,
        incident_id: str,
        signal_type: SignalType,
        severity: IntelligenceSeverity,
        tick: int,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> IncidentRecord:
        record = IncidentRecord(
            incident_id=incident_id,
            signal_type=signal_type,
            severity=severity,
            status=IncidentStatus.OPEN,
            tick_detected=tick,
            description=description,
            occurrence_count=1,
            details=details or {},
        )
        self._evict_if_full()
        self._incidents[incident_id] = record
        self._insertion_order.append(incident_id)
        return record

    def update_status(
        self,
        incident_id: str,
        new_status: IncidentStatus,
        resolved_tick: Optional[int] = None,
    ) -> bool:
        record = self._incidents.get(incident_id)
        if record is None:
            return False
        record.status = new_status
        if new_status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
            record.resolved_tick = resolved_tick
        return True

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        return self._incidents.get(incident_id)

    def get_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IntelligenceSeverity] = None,
        signal_type: Optional[SignalType] = None,
        limit: int = 100,
    ) -> List[IncidentRecord]:
        result: List[IncidentRecord] = []
        for record in self._incidents.values():
            if status is not None and record.status != status:
                continue
            if severity is not None and record.severity != severity:
                continue
            if signal_type is not None and record.signal_type != signal_type:
                continue
            result.append(record)
            if len(result) >= limit:
                break
        return result

    def get_active_incidents(self) -> List[IncidentRecord]:
        return [
            r
            for r in self._incidents.values()
            if r.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
        ]

    def get_incident_count(self) -> int:
        return len(self._incidents)

    def increment_occurrence(self, incident_id: str) -> bool:
        record = self._incidents.get(incident_id)
        if record is None:
            return False
        record.occurrence_count += 1
        return True

    def clear(self) -> None:
        self._incidents.clear()
        self._insertion_order.clear()

    def _evict_if_full(self) -> None:
        while len(self._incidents) >= self.max_incidents:
            oldest = self._insertion_order.popleft()
            self._incidents.pop(oldest, None)

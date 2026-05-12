"""Quarantine management for contained workflows."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import QuarantineRecord, IntegritySeverity, ContainmentStatus


class QuarantineManager:
    def __init__(self, max_history: int = 200):
        self._quarantined: Dict[str, QuarantineRecord] = {}
        self._quarantine_history: deque = deque(maxlen=max_history)

    def quarantine(self, workflow_id: str, workflow_type: str,
                   tick: int, reason: str,
                   severity: IntegritySeverity = IntegritySeverity.MEDIUM,
                   evidence: Optional[List[str]] = None,
                   expiry_tick: Optional[int] = None) -> Dict[str, Any]:
        if workflow_id in self._quarantined:
            return {'quarantined': False, 'reason': 'Already quarantined', 'workflow_id': workflow_id}
        record = QuarantineRecord(
            workflow_id=workflow_id, workflow_type=workflow_type,
            quarantined_at_tick=tick, reason=reason,
            severity=severity, evidence=evidence or [],
            expiry_tick=expiry_tick,
        )
        self._quarantined[workflow_id] = record
        self._quarantine_history.append({
            'workflow_id': workflow_id, 'action': 'quarantine',
            'tick': tick, 'severity': severity.value,
        })
        return {'quarantined': True, 'workflow_id': workflow_id,
                'severity': severity.value, 'reason': reason}

    def release_from_quarantine(self, workflow_id: str, tick: int) -> Dict[str, Any]:
        if workflow_id not in self._quarantined:
            return {'released': False, 'reason': 'Not quarantined', 'workflow_id': workflow_id}
        self._quarantine_history.append({
            'workflow_id': workflow_id, 'action': 'release', 'tick': tick,
        })
        del self._quarantined[workflow_id]
        return {'released': True, 'workflow_id': workflow_id}

    def get_active_quarantine_count(self) -> int:
        return len(self._quarantined)

    def list_quarantined(self) -> List[Dict[str, Any]]:
        return [{'workflow_id': r.workflow_id, 'workflow_type': r.workflow_type,
                 'severity': r.severity.value, 'reason': r.reason,
                 'quarantined_at': r.quarantined_at_tick}
                for r in self._quarantined.values()]

    def clear(self):
        self._quarantined.clear()
        self._quarantine_history.clear()

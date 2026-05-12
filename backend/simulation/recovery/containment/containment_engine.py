"""Containment engine - orchestrates isolation + quarantine + rules."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.containment.containment_rules import ContainmentRules
from simulation.recovery.containment.workflow_isolator import WorkflowIsolator
from simulation.recovery.containment.quarantine_manager import QuarantineManager
from simulation.recovery.models import ContainmentResult, ContainmentStatus


class ContainmentEngine:
    def __init__(self, max_history: int = 500):
        self._rules = ContainmentRules()
        self._isolator = WorkflowIsolator()
        self._quarantine = QuarantineManager()
        self._containment_history: deque = deque(maxlen=max_history)
        self._containment_count: int = 0

    @property
    def rules(self) -> ContainmentRules:
        return self._rules

    @property
    def isolator(self) -> WorkflowIsolator:
        return self._isolator

    @property
    def quarantine(self) -> QuarantineManager:
        return self._quarantine

    def evaluate_and_contain(self, workflow_id: str, workflow_type: str,
                             tick: int, contexts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        rule_results = self._rules.evaluate_multi(contexts)
        triggered = [r for r in rule_results if r.get('triggered')]
        if not triggered:
            return {'contained': False, 'reason': 'No rules triggered', 'triggered_count': 0}
        self._containment_count += 1
        containment_id = f"cnt_{self._containment_count}_{tick}"
        isolated = []
        quarantined = []
        blocking = False
        for result in triggered:
            if result.get('auto_isolate'):
                iso = self._isolator.isolate_workflow(
                    workflow_id, workflow_type, tick, result.get('message', ''))
                if iso.get('isolated'):
                    isolated.append(workflow_id)
                    blocking = True
            if result.get('auto_quarantine'):
                q = self._quarantine.quarantine(
                    workflow_id, workflow_type, tick, result.get('message', ''),
                    expiry_tick=result.get('quarantine_duration'),
                )
                if q.get('quarantined'):
                    quarantined.append(workflow_id)
        record = ContainmentResult(
            contained=True, containment_id=containment_id,
            status=ContainmentStatus.QUARANTINED if quarantined else ContainmentStatus.ISOLATED,
            isolated_workflows=isolated, quarantined_workflows=quarantined,
            blocking=blocking, message=f"{len(triggered)} rule(s) triggered",
        )
        self._containment_history.append({
            'containment_id': containment_id, 'workflow_id': workflow_id,
            'tick': tick, 'triggered_rules': len(triggered),
            'blocking': blocking,
        })
        return {
            'contained': True, 'containment_id': containment_id,
            'status': record.status.value, 'isolated': isolated,
            'quarantined': quarantined, 'blocking': blocking,
            'triggered_count': len(triggered),
            'message': record.message,
        }

    def release_workflow(self, workflow_id: str, tick: int) -> Dict[str, Any]:
        isolated_result = self._isolator.release_workflow(workflow_id, tick)
        quarantined_result = self._quarantine.release_from_quarantine(workflow_id, tick)
        return {
            'isolated_released': isolated_result.get('released', False),
            'quarantined_released': quarantined_result.get('released', False),
            'workflow_id': workflow_id,
        }

    def get_containment_report(self) -> Dict[str, Any]:
        return {
            'isolated_count': self._isolator.get_isolated_count(),
            'quarantined_count': self._quarantine.get_active_quarantine_count(),
            'total_containments': self._containment_count,
            'isolated': self._isolator.list_isolated(),
            'quarantined': self._quarantine.list_quarantined(),
        }

    def clear(self):
        self._isolator.clear()
        self._quarantine.clear()
        self._containment_history.clear()
        self._containment_count = 0

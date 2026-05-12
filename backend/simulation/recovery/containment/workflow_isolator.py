"""Workflow isolation - prevents failure propagation."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import ContainmentStatus, ContainmentRecord


class WorkflowIsolator:
    def __init__(self, max_history: int = 200):
        self._isolated: Dict[str, ContainmentRecord] = {}
        self._isolation_history: deque = deque(maxlen=max_history)

    def isolate_workflow(self, workflow_id: str, workflow_type: str,
                         tick: int, reason: str,
                         affected_components: Optional[List[str]] = None) -> Dict[str, Any]:
        if workflow_id in self._isolated:
            return {'isolated': False, 'reason': 'Already isolated', 'workflow_id': workflow_id}
        record = ContainmentRecord(
            workflow_id=workflow_id, workflow_type=workflow_type,
            status=ContainmentStatus.ISOLATED, isolation_tick=tick,
            reason=reason, affected_components=affected_components or [],
        )
        self._isolated[workflow_id] = record
        self._isolation_history.append({
            'workflow_id': workflow_id, 'action': 'isolate',
            'tick': tick, 'reason': reason,
        })
        return {'isolated': True, 'workflow_id': workflow_id, 'status': 'isolated',
                'reason': reason}

    def release_workflow(self, workflow_id: str, tick: int) -> Dict[str, Any]:
        if workflow_id not in self._isolated:
            return {'released': False, 'reason': 'Not isolated', 'workflow_id': workflow_id}
        self._isolated[workflow_id].status = ContainmentStatus.RELEASED
        self._isolation_history.append({
            'workflow_id': workflow_id, 'action': 'release', 'tick': tick,
        })
        del self._isolated[workflow_id]
        return {'released': True, 'workflow_id': workflow_id}

    def is_isolated(self, workflow_id: str) -> bool:
        return workflow_id in self._isolated

    def get_isolated_count(self) -> int:
        return len(self._isolated)

    def list_isolated(self) -> List[Dict[str, Any]]:
        return [{'workflow_id': r.workflow_id, 'workflow_type': r.workflow_type,
                 'status': r.status.value, 'isolated_at': r.isolation_tick,
                 'reason': r.reason}
                for r in self._isolated.values()]

    def clear(self):
        self._isolated.clear()
        self._isolation_history.clear()

"""Snapshot validator — validates snapshot integrity and completeness."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import SnapshotStatus


class SnapshotValidator:
    def __init__(self, max_history: int = 100):
        self._validation_history: deque = deque(maxlen=max_history)

    def validate_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        has_id = bool(snapshot.get('snapshot_id'))
        has_tick = snapshot.get('tick') is not None
        has_events = snapshot.get('event_count', 0) >= 0
        has_states = bool(snapshot.get('workflow_states'))
        is_valid = has_id and has_tick and has_states
        issues = []
        if not has_id: issues.append('Missing snapshot_id')
        if not has_tick: issues.append('Missing tick')
        if not has_states: issues.append('Missing workflow_states')
        status = SnapshotStatus.INTACT if is_valid else SnapshotStatus.CORRUPTED
        self._validation_history.append({
            'is_valid': is_valid, 'issues_found': len(issues),
        })
        return {'is_valid': is_valid, 'status': status.value,
                'issues': issues}

    def validate_snapshot_list(self, snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.validate_snapshot(s) for s in snapshots]

    def clear(self):
        self._validation_history.clear()

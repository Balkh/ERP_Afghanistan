"""Snapshot integrity — verifies snapshot integrity and lineage."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import SnapshotStatus


class SnapshotIntegrity:
    def __init__(self, max_history: int = 100):
        self._integrity_history: deque = deque(maxlen=max_history)

    def verify_integrity(self, snapshot: Dict[str, Any],
                         expected_hash: str = "") -> Dict[str, Any]:
        actual_hash = snapshot.get('hash_value', '')
        hash_match = not expected_hash or actual_hash == expected_hash
        has_workflows = bool(snapshot.get('workflow_states'))
        has_events = snapshot.get('event_count', 0) >= 0
        is_intact = hash_match and has_workflows
        status = SnapshotStatus.INTACT if is_intact else SnapshotStatus.CORRUPTED
        self._integrity_history.append({
            'snapshot_id': snapshot.get('snapshot_id', ''),
            'is_intact': is_intact, 'hash_match': hash_match,
        })
        return {'is_intact': is_intact, 'status': status.value,
                'hash_match': hash_match, 'has_workflows': has_workflows,
                'has_events': has_events}

    def verify_lineage(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not snapshots:
            return {'lineage_intact': True, 'checked': 0}
        chain_broken = False
        for i in range(len(snapshots) - 1):
            expected_parent = snapshots[i + 1].get('parent_snapshot_id')
            if expected_parent and expected_parent != snapshots[i].get('snapshot_id'):
                chain_broken = True
        ticks_in_order = all(
            snapshots[i].get('tick', 0) <= snapshots[i + 1].get('tick', 0)
            for i in range(len(snapshots) - 1)
        )
        self._integrity_history.append({
            'lineage_intact': not chain_broken,
            'chain_broken': chain_broken, 'ticks_ordered': ticks_in_order,
        })
        return {'lineage_intact': not chain_broken and ticks_in_order,
                'chain_broken': chain_broken, 'ticks_ordered': ticks_in_order}

    def clear(self):
        self._integrity_history.clear()

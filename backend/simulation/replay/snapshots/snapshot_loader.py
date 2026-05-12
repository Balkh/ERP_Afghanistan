"""Snapshot loader — loads replay snapshots from event data."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplaySnapshot, SnapshotStatus


class SnapshotLoader:
    def __init__(self, max_snapshots: int = 100):
        self._snapshots: Dict[str, ReplaySnapshot] = {}
        self._load_history: deque = deque(maxlen=max_snapshots)

    def load_snapshot(self, snapshot_id: str, tick: int,
                      workflow_states: Optional[Dict[str, Any]] = None,
                      event_count: int = 0, hash_value: str = "",
                      parent_id: Optional[str] = None) -> Dict[str, Any]:
        snapshot = ReplaySnapshot(
            snapshot_id=snapshot_id, tick=tick,
            status=SnapshotStatus.INTACT,
            workflow_states=workflow_states or {},
            event_count=event_count, hash_value=hash_value,
            parent_snapshot_id=parent_id,
        )
        self._snapshots[snapshot_id] = snapshot
        self._load_history.append(snapshot_id)
        return {'snapshot_id': snapshot_id, 'tick': tick,
                'status': 'intact', 'event_count': event_count}

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        s = self._snapshots.get(snapshot_id)
        if s is None:
            return None
        return {'snapshot_id': s.snapshot_id, 'tick': s.tick,
                'status': s.status.value, 'event_count': s.event_count,
                'hash_value': s.hash_value,
                'parent_snapshot_id': s.parent_snapshot_id}

    def get_snapshots_since(self, tick: int) -> List[Dict[str, Any]]:
        return [{'snapshot_id': s.snapshot_id, 'tick': s.tick,
                 'status': s.status.value, 'event_count': s.event_count}
                for s in self._snapshots.values() if s.tick >= tick]

    def get_snapshot_count(self) -> int:
        return len(self._snapshots)

    def clear(self):
        self._snapshots.clear()
        self._load_history.clear()

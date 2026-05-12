"""Snapshot history — tracks snapshot lineage and history."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import SnapshotStatus


class SnapshotHistory:
    def __init__(self, max_history: int = 200):
        self._history: deque = deque(maxlen=max_history)
        self._snapshot_count: int = 0

    def record_snapshot(self, snapshot_id: str, tick: int,
                        parent_id: Optional[str] = None) -> Dict[str, Any]:
        self._snapshot_count += 1
        record = {
            'snapshot_id': snapshot_id, 'tick': tick,
            'parent_id': parent_id, 'index': self._snapshot_count,
        }
        self._history.append(record)
        return record

    def get_lineage(self, snapshot_id: str) -> List[Dict[str, Any]]:
        lineage = []
        lookup = {r['snapshot_id']: r for r in self._history}
        current = lookup.get(snapshot_id)
        visited = set()
        while current and current['snapshot_id'] not in visited:
            visited.add(current['snapshot_id'])
            lineage.append(current)
            parent_id = current.get('parent_id')
            current = lookup.get(parent_id) if parent_id else None
            if len(lineage) > 100:
                break
        return lineage

    def get_history_count(self) -> int:
        return len(self._history)

    def clear(self):
        self._history.clear()
        self._snapshot_count = 0

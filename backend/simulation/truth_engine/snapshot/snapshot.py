import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from simulation.truth_engine.models.models import ExpectedState, ActualState


logger = logging.getLogger('erp.simulation.truth.snapshot')


class SnapshotManager:
    """
    Manages versioned snapshots of expected and actual states.
    Deterministic snapshots only. NO live mutation of past states.
    NO recalculation of history. Immutable after creation.
    """

    def __init__(self, max_snapshots: int = 100):
        self._max_snapshots = max_snapshots
        self._snapshots: List[Dict[str, Any]] = []
        self._versions: Dict[str, int] = {}

    def take_snapshot(
        self, snapshot_id: str, scenario_id: str,
        tick: int, timestamp, expected: ExpectedState,
        actual: Optional[ActualState] = None,
    ) -> str:
        version = self._versions.get(snapshot_id, 0)
        snapshot = {
            'snapshot_id': snapshot_id,
            'version': version,
            'scenario_id': scenario_id,
            'tick': tick,
            'timestamp': str(timestamp),
            'created_at': str(datetime.now()),
            'expected': expected.to_dict(),
            'actual': actual.to_dict() if actual else None,
        }
        self._snapshots.append(snapshot)
        self._versions[snapshot_id] = version + 1
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots.pop(0)
        logger.debug(
            "SnapshotManager: snapshot '%s' v%d taken at tick %d",
            snapshot_id, version, tick
        )
        return f"{snapshot_id}_v{version}"

    def get_snapshot(self, snapshot_id: str,
                     version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if version is None:
            version = self._versions.get(snapshot_id, 0) - 1
        for snap in reversed(self._snapshots):
            if snap['snapshot_id'] == snapshot_id and snap['version'] == version:
                return snap
        return None

    def get_latest_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        version = self._versions.get(snapshot_id, 0) - 1
        return self.get_snapshot(snapshot_id, version)

    def get_snapshots_by_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        return [
            s for s in self._snapshots
            if s['scenario_id'] == scenario_id
        ]

    def get_snapshot_count(self) -> int:
        return len(self._snapshots)

    def get_version(self, snapshot_id: str) -> int:
        return self._versions.get(snapshot_id, 0)

    def clear(self):
        self._snapshots.clear()
        self._versions.clear()

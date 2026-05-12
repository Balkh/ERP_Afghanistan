"""Dashboard model factory for creating and managing dashboard snapshots.

Strictly read-only, bounded memory, exception-safe.
"""
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.control_center.models import DashboardSnapshot


class DashboardModelFactory:
    """Factory for creating and managing DashboardSnapshot instances.
    
    Uses bounded deque for memory safety. All operations are exception-safe.
    """

    def __init__(self, max_snapshots: int = 100):
        """Initialize the factory with bounded snapshot storage.
        
        Args:
            max_snapshots: Maximum number of snapshots to retain. Defaults to 100.
        """
        self._max_snapshots = max(max_snapshots, 1)
        self._snapshots: deque = deque(maxlen=self._max_snapshots)
        self._snapshot_index: Dict[str, DashboardSnapshot] = {}

    def create_snapshot(
        self,
        snapshot_id: str,
        tick: int,
        operational_state: str,
        stability_score: float,
        health_status: str,
        active_incidents: int,
        widget_data: Optional[Dict[str, Any]] = None,
        summary: str = ""
    ) -> Optional[DashboardSnapshot]:
        """Create and store a new DashboardSnapshot.
        
        Args:
            snapshot_id: Unique identifier for the snapshot.
            tick: Simulation tick when snapshot was taken.
            operational_state: Current operational state ('normal', 'degraded', etc.).
            stability_score: Stability score between 0.0 and 1.0.
            health_status: Health status description.
            active_incidents: Count of active incidents.
            widget_data: Optional widget-specific data.
            summary: Optional text summary.
            
        Returns:
            The created DashboardSnapshot, or None on error.
        """
        try:
            snapshot = DashboardSnapshot(
                snapshot_id=snapshot_id,
                tick=tick,
                operational_state=operational_state,
                stability_score=max(0.0, min(1.0, float(stability_score))),
                health_status=health_status,
                active_incidents=max(0, int(active_incidents)),
                widget_data=dict(widget_data) if widget_data else {},
                summary=str(summary)
            )
            
            if len(self._snapshots) >= self._max_snapshots and self._snapshots:
                oldest = self._snapshots[0]
                self._snapshot_index.pop(oldest.snapshot_id, None)
            
            self._snapshots.append(snapshot)
            self._snapshot_index[snapshot_id] = snapshot
            
            return snapshot
        except Exception:
            return None

    def get_snapshot(self, snapshot_id: str) -> Optional[DashboardSnapshot]:
        """Retrieve a snapshot by its ID.
        
        Args:
            snapshot_id: The snapshot identifier to look up.
            
        Returns:
            The DashboardSnapshot if found, None otherwise.
        """
        try:
            return self._snapshot_index.get(snapshot_id)
        except Exception:
            return None

    def get_latest_snapshot(self) -> Optional[DashboardSnapshot]:
        """Get the most recently created snapshot.
        
        Returns:
            The latest DashboardSnapshot, or None if empty.
        """
        try:
            if self._snapshots:
                return self._snapshots[-1]
            return None
        except Exception:
            return None

    def get_snapshots(
        self,
        tick_start: Optional[int] = None,
        tick_end: Optional[int] = None,
        limit: int = 50
    ) -> List[DashboardSnapshot]:
        """Get snapshots filtered by tick range, limited by count.
        
        Args:
            tick_start: Minimum tick (inclusive). If None, no lower bound.
            tick_end: Maximum tick (inclusive). If None, no upper bound.
            limit: Maximum number of snapshots to return. Defaults to 50.
            
        Returns:
            List of matching DashboardSnapshot instances, newest first.
        """
        try:
            results = []
            limit = max(1, int(limit))
            
            for snapshot in reversed(self._snapshots):
                if len(results) >= limit:
                    break
                
                if tick_start is not None and snapshot.tick < tick_start:
                    continue
                if tick_end is not None and snapshot.tick > tick_end:
                    continue
                
                results.append(snapshot)
            
            return results
        except Exception:
            return []

    def get_snapshot_count(self) -> int:
        """Get the current number of stored snapshots.
        
        Returns:
            Count of snapshots in storage.
        """
        try:
            return len(self._snapshots)
        except Exception:
            return 0

    def clear(self) -> None:
        """Clear all stored snapshots and indices."""
        try:
            self._snapshots.clear()
            self._snapshot_index.clear()
        except Exception:
            pass

"""Snapshot reconstructor — reconstructs state from event sequences."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplaySnapshot, SnapshotStatus


class SnapshotReconstructor:
    def __init__(self, max_history: int = 100):
        self._reconstruction_history: deque = deque(maxlen=max_history)

    def reconstruct(self, snapshot_id: str, tick: int,
                    events: List[Dict[str, Any]],
                    base_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base_state = dict(base_state or {})
        state = dict(base_state)
        workflow_states: Dict[str, Any] = {}
        event_count = 0
        for e in events:
            e_type = e.get('event_type', '')
            source = e.get('source', '')
            if source not in workflow_states:
                workflow_states[source] = {'event_count': 0, 'last_tick': 0}
            workflow_states[source]['event_count'] += 1
            workflow_states[source]['last_tick'] = max(
                workflow_states[source]['last_tick'], e.get('tick', 0))
            event_count += 1
        self._reconstruction_history.append({
            'snapshot_id': snapshot_id, 'tick': tick,
            'events_consumed': event_count,
            'workflows_reconstructed': len(workflow_states),
        })
        return {
            'snapshot_id': snapshot_id, 'tick': tick,
            'workflow_states': workflow_states,
            'event_count': event_count,
            'status': 'reconstructed',
        }

    def get_reconstruction_count(self) -> int:
        return len(self._reconstruction_history)

    def clear(self):
        self._reconstruction_history.clear()

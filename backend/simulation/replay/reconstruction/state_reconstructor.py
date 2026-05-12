"""State reconstructor — reconstructs operational state at a given tick."""
from collections import deque
from typing import Any, Dict, List, Optional


class StateReconstructor:
    def __init__(self, max_history: int = 100):
        self._reconstruction_history: deque = deque(maxlen=max_history)

    def reconstruct_at_tick(self, target_tick: int,
                            events: List[Dict[str, Any]]) -> Dict[str, Any]:
        relevant = [e for e in events if e.get('tick', 0) <= target_tick]
        workflow_states: Dict[str, str] = {}
        event_counts: Dict[str, int] = {}
        for e in relevant:
            source = e.get('source', 'unknown')
            e_type = e.get('event_type', '')
            if e_type == 'workflow_started':
                workflow_states[source] = 'running'
            elif e_type == 'workflow_completed':
                workflow_states[source] = 'completed'
            elif e_type == 'workflow_failed':
                workflow_states[source] = 'failed'
            event_counts[source] = event_counts.get(source, 0) + 1
        self._reconstruction_history.append({
            'target_tick': target_tick, 'events_processed': len(relevant),
            'workflows_found': len(workflow_states),
        })
        return {
            'target_tick': target_tick,
            'workflow_states': workflow_states,
            'event_counts': event_counts,
            'total_events_processed': len(relevant),
            'active_workflows': sum(1 for s in workflow_states.values() if s == 'running'),
        }

    def get_reconstruction_count(self) -> int:
        return len(self._reconstruction_history)

    def clear(self):
        self._reconstruction_history.clear()

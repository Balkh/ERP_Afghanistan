"""Workflow reconstructor — reconstructs workflow execution from events."""
from collections import deque
from typing import Any, Dict, List, Optional


class WorkflowReconstructor:
    def __init__(self, max_history: int = 200):
        self._reconstruction_history: deque = deque(maxlen=max_history)

    def reconstruct(self, workflow_id: str, events: List[Dict[str, Any]],
                    workflow_type: str = "unknown") -> Dict[str, Any]:
        steps = []
        state = 'initialized'
        for e in events:
            if e.get('source') == workflow_id or e.get('payload', {}).get('workflow_id') == workflow_id:
                steps.append({
                    'tick': e.get('tick', 0), 'event_type': e.get('event_type', ''),
                    'description': e.get('description', ''),
                })
                if e.get('event_type') == 'workflow_started':
                    state = 'running'
                elif e.get('event_type') == 'workflow_completed':
                    state = 'completed'
                elif e.get('event_type') == 'workflow_failed':
                    state = 'failed'
        self._reconstruction_history.append({
            'workflow_id': workflow_id, 'steps_found': len(steps),
            'final_state': state,
        })
        return {'workflow_id': workflow_id, 'workflow_type': workflow_type,
                'steps': steps, 'total_steps': len(steps), 'final_state': state}

    def get_reconstruction_count(self) -> int:
        return len(self._reconstruction_history)

    def clear(self):
        self._reconstruction_history.clear()

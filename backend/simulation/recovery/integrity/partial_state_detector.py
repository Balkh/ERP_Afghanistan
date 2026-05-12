"""Partial state detection — detects incomplete or orphaned workflow state."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import IntegritySeverity


class PartialStateDetector:
    def __init__(self, max_history: int = 200):
        self._detection_history: deque = deque(maxlen=max_history)

    def detect_partial_states(self, workflows: List[Dict[str, Any]],
                              expected_steps: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        expected_steps = expected_steps or {}
        partial_states = []
        for wf in workflows:
            wf_id = wf.get('workflow_id', '')
            wf_type = wf.get('workflow_type', '')
            current_step = wf.get('current_step', 0)
            total_steps = expected_steps.get(wf_type, wf.get('total_steps', 1))
            if current_step < total_steps and wf.get('status') != 'completed':
                severity = (IntegritySeverity.HIGH if current_step == 0
                            else IntegritySeverity.MEDIUM if current_step < total_steps / 2
                            else IntegritySeverity.LOW)
                result = {
                    'workflow_id': wf_id, 'workflow_type': wf_type,
                    'current_step': current_step, 'total_steps': total_steps,
                    'progress_pct': round(current_step / total_steps * 100, 1) if total_steps else 0,
                    'severity': severity.value,
                    'description': f"Workflow {wf_id} at step {current_step}/{total_steps}",
                }
                partial_states.append(result)
        self._detection_history.append({
            'checked': len(workflows), 'partial_found': len(partial_states),
        })
        return partial_states

    def detect_orphan_workflows(self, workflows: List[Dict[str, Any]],
                                active_ids: set) -> List[Dict[str, Any]]:
        orphans = []
        for wf in workflows:
            wf_id = wf.get('workflow_id', '')
            if wf_id not in active_ids and wf.get('status') != 'completed':
                orphans.append({
                    'workflow_id': wf_id, 'workflow_type': wf.get('workflow_type', ''),
                    'status': wf.get('status', 'unknown'),
                    'severity': IntegritySeverity.MEDIUM.value,
                })
        self._detection_history.append({
            'orphan_checked': len(workflows), 'orphans_found': len(orphans),
        })
        return orphans

    def clear(self):
        self._detection_history.clear()

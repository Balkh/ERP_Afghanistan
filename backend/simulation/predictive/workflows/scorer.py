import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.workflows.scorer')


WORKFLOW_TYPES = ['sales', 'purchase', 'inventory', 'return', 'hr']


class WorkflowRiskScorer:
    def __init__(self, max_history: int = 500):
        self._max_history = max_history
        self._risk_history: deque = deque(maxlen=max_history)

    def record_risk(self, tick: int, workflow_type: str,
                    score: float, components: Dict[str, float]):
        self._risk_history.append({
            'tick': tick,
            'workflow_type': workflow_type,
            'score': score,
            'components': dict(components),
        })

    def score_workflow(self, workflow_type: str,
                       drift_history: List[Dict[str, Any]],
                       root_cause_recurrence: Dict[str, int],
                       graph_instability: float = 0.0,
                       event_fan_out: int = 0,
                       failure_density: float = 0.0) -> float:
        base_score = 0.0
        if workflow_type not in WORKFLOW_TYPES:
            return 0.0
        history_factor = self._calc_history_factor(workflow_type, drift_history)
        recurrence_penalty = root_cause_recurrence.get(workflow_type, 0) * 5
        graph_penalty = graph_instability * 10
        fan_out_penalty = min(event_fan_out * 2, 20)
        density_penalty = failure_density * 15
        raw = (history_factor + recurrence_penalty + graph_penalty
               + fan_out_penalty + density_penalty)
        clamped = min(max(raw, 0.0), 100.0)
        return round(clamped, 2)

    def _calc_history_factor(self, workflow_type: str,
                             drift_history: List[Dict]) -> float:
        relevant = [e for e in drift_history
                    if e.get('mismatch', {}).get('affected_module', '') == workflow_type]
        if not relevant:
            return 0.0
        recent = relevant[-10:] if len(relevant) >= 10 else relevant
        return len(recent) * 3

    def get_risk_trend(self, workflow_type: str) -> Dict[str, Any]:
        relevant = [r for r in self._risk_history if r['workflow_type'] == workflow_type]
        if not relevant:
            return {'workflow_type': workflow_type, 'direction': 'stable', 'avg_score': 0.0}
        recent = relevant[-5:] if len(relevant) >= 5 else relevant
        avg = sum(r['score'] for r in recent) / max(len(recent), 1)
        if len(relevant) >= 2:
            first_avg = sum(r['score'] for r in relevant[:len(relevant)//2]) / max(len(relevant)//2, 1)
            direction = 'worsening' if avg > first_avg * 1.1 else 'improving' if avg < first_avg * 0.9 else 'stable'
        else:
            direction = 'stable'
        return {'workflow_type': workflow_type, 'direction': direction,
                'avg_score': round(avg, 2), 'samples': len(relevant)}

    @property
    def record_count(self) -> int:
        return len(self._risk_history)

    def clear(self):
        self._risk_history.clear()

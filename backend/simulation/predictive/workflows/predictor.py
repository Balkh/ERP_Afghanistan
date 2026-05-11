import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.workflows.predictor')


class WorkflowInstabilityPredictor:
    def __init__(self, max_history: int = 200):
        self._max_history = max_history
        self._prediction_history: deque = deque(maxlen=max_history)

    def predict_degradation(self, workflow_type: str,
                            risk_score: float,
                            trend_direction: str,
                            recurrence_count: int,
                            recent_failures: int) -> float:
        base = risk_score * 0.5
        trend_bonus = 10 if trend_direction == 'worsening' else 0
        recurrence_bonus = recurrence_count * 3
        failure_bonus = recent_failures * 5
        raw = base + trend_bonus + recurrence_bonus + failure_bonus
        return round(min(max(raw, 0.0), 100.0), 2)

    def predict_instability_propagation(self,
                                        workflow_scores: Dict[str, float],
                                        causal_links: List[Dict]) -> Dict[str, float]:
        propagated: Dict[str, float] = {}
        for wf, score in workflow_scores.items():
            if score >= 50:
                linked = self._find_linked_workflows(wf, causal_links)
                for lwf in linked:
                    propagated[lwf] = max(propagated.get(lwf, 0), score * 0.3)
        return propagated

    def predict_collision_risk(self,
                               active_workflows: List[str],
                               workflow_scores: Dict[str, float]) -> float:
        if len(active_workflows) < 2:
            return 0.0
        high_risk = sum(1 for w in active_workflows if workflow_scores.get(w, 0) >= 50)
        return round(min(high_risk * 15, 100.0), 2)

    def predict_cascading_failure(self,
                                  workflow_scores: Dict[str, float],
                                  dependency_map: Dict[str, List[str]]) -> Dict[str, float]:
        cascade: Dict[str, float] = {}
        for wf, score in workflow_scores.items():
            if score >= 40:
                deps = dependency_map.get(wf, [])
                for dep in deps:
                    cascade[dep] = max(cascade.get(dep, 0), score * 0.5)
        return cascade

    def _find_linked_workflows(self, workflow_type: str,
                               causal_links: List[Dict]) -> List[str]:
        linked = set()
        for link in causal_links:
            if link.get('source_id', '').startswith(workflow_type):
                tid = link.get('target_id', '')
                for wt in ('sales', 'purchase', 'inventory', 'return', 'hr'):
                    if tid.startswith(wt):
                        linked.add(wt)
            if link.get('target_id', '').startswith(workflow_type):
                sid = link.get('source_id', '')
                for wt in ('sales', 'purchase', 'inventory', 'return', 'hr'):
                    if sid.startswith(wt):
                        linked.add(wt)
        return list(linked)

    def record_prediction(self, tick: int, workflow_type: str,
                          degradation_prob: float):
        self._prediction_history.append({
            'tick': tick,
            'workflow_type': workflow_type,
            'degradation_probability': degradation_prob,
        })

    @property
    def record_count(self) -> int:
        return len(self._prediction_history)

    def clear(self):
        self._prediction_history.clear()

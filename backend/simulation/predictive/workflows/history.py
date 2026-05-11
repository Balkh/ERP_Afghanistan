import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.workflows.history')


class WorkflowRiskHistory:
    def __init__(self, max_records: int = 500):
        self._max_records = max_records
        self._records: deque = deque(maxlen=max_records)
        self._type_index: Dict[str, List[int]] = {}

    def record(self, tick: int, workflow_type: str,
               risk_score: float, degradation_prob: float,
               components: Dict[str, Any]):
        idx = len(self._records)
        self._records.append({
            'tick': tick,
            'workflow_type': workflow_type,
            'risk_score': risk_score,
            'degradation_probability': degradation_prob,
            'components': dict(components),
        })
        if workflow_type not in self._type_index:
            self._type_index[workflow_type] = []
        self._type_index[workflow_type].append(idx)

    def get_history(self, workflow_type: Optional[str] = None,
                    since_tick: int = 0) -> List[Dict[str, Any]]:
        if workflow_type:
            indices = self._type_index.get(workflow_type, [])
            results = [self._records[i] for i in indices
                       if self._records[i]['tick'] >= since_tick]
        else:
            results = [r for r in self._records if r['tick'] >= since_tick]
        return list(results)

    def get_latest_score(self, workflow_type: str) -> Optional[float]:
        indices = self._type_index.get(workflow_type, [])
        if not indices:
            return None
        return self._records[indices[-1]]['risk_score']

    def get_average_score(self, workflow_type: str,
                          window: int = 10) -> float:
        indices = self._type_index.get(workflow_type, [])
        recent = indices[-window:] if len(indices) >= window else indices
        if not recent:
            return 0.0
        scores = [self._records[i]['risk_score'] for i in recent]
        return round(sum(scores) / len(scores), 2)

    def get_high_risk_workflows(self, threshold: float = 50.0) -> Dict[str, float]:
        latest: Dict[str, float] = {}
        for wt in ('sales', 'purchase', 'inventory', 'return', 'hr'):
            score = self.get_latest_score(wt)
            if score is not None and score >= threshold:
                latest[wt] = score
        return latest

    @property
    def record_count(self) -> int:
        return len(self._records)

    def clear(self):
        self._records.clear()
        self._type_index.clear()

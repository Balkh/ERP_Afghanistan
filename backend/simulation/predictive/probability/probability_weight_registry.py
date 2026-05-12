import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('erp.simulation.predictive.probability.weights')

DEFAULT_WEIGHTS: Dict[str, float] = {
    'mismatch_density': 0.6,
    'workflow_failure': 0.7,
    'propagation_risk': 0.5,
    'causal_chain_risk': 0.4,
    'escalation_speed': 0.3,
    'recurrence_impact': 0.5,
    'severity_impact': 0.8,
}


class ProbabilityWeightRegistry:
    def __init__(self):
        self._weights: Dict[str, float] = dict(DEFAULT_WEIGHTS)

    def get_weight(self, name: str) -> float:
        return self._weights.get(name, 1.0)

    def set_weight(self, name: str, value: float):
        clamped = min(max(value, 0.0), 1.0)
        self._weights[name] = clamped

    def get_all_weights(self) -> Dict[str, float]:
        return dict(self._weights)

    def reset_to_defaults(self):
        self._weights.clear()
        self._weights.update(DEFAULT_WEIGHTS)

    @property
    def weight_count(self) -> int:
        return len(self._weights)

    def clear(self):
        self._weights.clear()
        self._weights.update(DEFAULT_WEIGHTS)

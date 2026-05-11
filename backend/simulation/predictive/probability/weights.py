import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('erp.simulation.predictive.probability.weights')


class ProbabilityWeightRegistry:
    def __init__(self):
        self._weights: Dict[str, float] = {
            'mismatch_history_factor': 0.25,
            'root_cause_recurrence_factor': 0.20,
            'graph_instability_factor': 0.15,
            'event_fan_out_factor': 0.10,
            'failure_density_factor': 0.15,
            'trend_direction_factor': 0.10,
            'severity_escalation_factor': 0.05,
        }

    def get_weight(self, key: str) -> float:
        return self._weights.get(key, 0.0)

    def set_weight(self, key: str, value: float):
        if key not in self._weights:
            raise ValueError(f"Unknown weight key: {key}")
        self._weights[key] = max(0.0, min(1.0, value))

    def get_all_weights(self) -> Dict[str, float]:
        return dict(self._weights)

    def get_normalized_weights(self) -> Dict[str, float]:
        total = sum(self._weights.values())
        if total <= 0:
            return {k: 0.0 for k in self._weights}
        return {k: round(v / total, 4) for k, v in self._weights.items()}

    @property
    def weight_count(self) -> int:
        return len(self._weights)

"""
Task E: ScalabilityEstimator — estimates degradation trends under load.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger('erp.simulation.audit.performance.estimator')


class ScalabilityEstimator:
    def estimate(self, base_cost_ms: float, event_counts: List[int]) -> Dict[str, Any]:
        estimates = {}
        for count in event_counts:
            linear_estimate = base_cost_ms * (count / 100.0)
            estimates[str(count)] = {
                'event_count': count,
                'estimated_cost_ms': round(linear_estimate, 4),
                'estimated_cost_seconds': round(linear_estimate / 1000.0, 6),
            }
        estimates['degradation_trend'] = 'linear'
        return estimates

    def estimate_graph_scaling(self, base_nodes: int, base_cost_ms: float,
                                multipliers: List[int]) -> Dict[str, Any]:
        estimates = {}
        for mult in multipliers:
            node_count = base_nodes * mult
            estimated_cost = base_cost_ms * mult
            estimates[f'{mult}x'] = {
                'estimated_nodes': node_count,
                'estimated_cost_ms': round(estimated_cost, 4),
                'bottleneck_risk': estimated_cost > 500.0,
            }
        return estimates

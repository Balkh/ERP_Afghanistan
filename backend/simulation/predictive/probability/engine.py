import logging
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.predictive.probability.weights import ProbabilityWeightRegistry
from simulation.predictive.probability.thresholds import (
    ProbabilityThresholdManager,
)

logger = logging.getLogger('erp.simulation.predictive.probability.engine')


class FailureProbabilityEngine:
    def __init__(self):
        self._weights = ProbabilityWeightRegistry()
        self._thresholds = ProbabilityThresholdManager()
        self._estimate_history: deque = deque(maxlen=500)

    @property
    def weights(self) -> ProbabilityWeightRegistry:
        return self._weights

    @property
    def thresholds(self) -> ProbabilityThresholdManager:
        return self._thresholds

    def estimate_mismatch_probability(
        self, drift_trend: Dict[str, Any],
        velocity: Dict[str, Any],
        forecast: Dict[str, Any],
    ) -> Dict[str, Any]:
        growth_rate = abs(drift_trend.get('mismatch_growth_rate', 0))
        acceleration = abs(drift_trend.get('instability_acceleration', 0))
        momentum = abs(velocity.get('instability_momentum', 0))
        density = forecast.get('predicted_drift_density', 0)
        w = self._weights.get_normalized_weights()
        raw = (
            w.get('mismatch_history_factor', 0) * min(growth_rate / 50, 1) * 100 +
            w.get('graph_instability_factor', 0) * min(acceleration, 100) +
            w.get('event_fan_out_factor', 0) * min(momentum * 10, 100) +
            w.get('failure_density_factor', 0) * min(density / 10, 100)
        )
        prob = round(min(max(raw, 0.0), 100.0), 2)
        level = self._thresholds.classify(prob)
        return {
            'probability': prob,
            'level': level,
            'contributing_factors': {
                'mismatch_growth': round(growth_rate, 2),
                'instability_acceleration': round(acceleration, 2),
                'instability_momentum': round(momentum, 4),
                'predicted_drift_density': round(density, 2),
            },
            'explanation': self._build_explanation(prob, level),
        }

    def estimate_workflow_failure_probability(
        self, risk_score: float,
        degradation_prob: float,
        recurrence_count: int,
        recent_failures: int,
    ) -> Dict[str, Any]:
        w = self._weights.get_normalized_weights()
        raw = (
            w.get('root_cause_recurrence_factor', 0) * risk_score +
            w.get('trend_direction_factor', 0) * degradation_prob +
            w.get('failure_density_factor', 0) * min(recurrence_count * 5, 100) +
            w.get('mismatch_history_factor', 0) * min(recent_failures * 10, 100)
        )
        prob = round(min(max(raw, 0.0), 100.0), 2)
        level = self._thresholds.classify(prob)
        return {
            'probability': prob,
            'level': level,
            'risk_score': risk_score,
            'degradation_probability': degradation_prob,
            'explanation': self._build_explanation(prob, level),
        }

    def estimate_propagation_probability(
        self, source_score: float,
        linked_workflows: List[str],
        cascade_scores: Dict[str, float],
    ) -> Dict[str, float]:
        result = {}
        for lwf in linked_workflows:
            cascade = cascade_scores.get(lwf, 0)
            prob = round(min(source_score * 0.4 + cascade * 0.6, 100.0), 2)
            result[lwf] = prob
        return result

    def estimate_causal_chain_failure_probability(
        self, chain_length: int,
        max_confidence: float,
        avg_confidence: float,
    ) -> Dict[str, Any]:
        length_factor = min(chain_length * 5, 50)
        confidence_factor = (1.0 - avg_confidence) * 50
        raw = length_factor + confidence_factor
        prob = round(min(max(raw, 0.0), 100.0), 2)
        level = self._thresholds.classify(prob)
        return {
            'probability': prob,
            'level': level,
            'chain_length': chain_length,
            'max_confidence': round(max_confidence, 2),
            'avg_confidence': round(avg_confidence, 2),
            'explanation': self._build_explanation(prob, level),
        }

    def record_estimate(self, tick: int, estimate_type: str,
                        probability: float, level: str):
        self._estimate_history.append({
            'tick': tick,
            'type': estimate_type,
            'probability': probability,
            'level': level,
        })

    def _build_explanation(self, prob: float, level: str) -> str:
        if level == 'critical':
            return f"Critical failure probability ({prob}%) — immediate action required"
        if level == 'escalation':
            return f"Elevated failure probability ({prob}%) — monitoring recommended"
        if level == 'warning':
            return f"Above-normal failure probability ({prob}%) — observe trends"
        return f"Normal failure probability ({prob}%) — no action needed"

    @property
    def estimate_count(self) -> int:
        return len(self._estimate_history)

    def clear(self):
        self._estimate_history.clear()

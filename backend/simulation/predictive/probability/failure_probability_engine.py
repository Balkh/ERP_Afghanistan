import logging
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from simulation.predictive.models import (
    FailureProbability, PredictionConfidence, WarningSeverity,
)
from simulation.predictive.probability.probability_weight_registry import ProbabilityWeightRegistry
from simulation.predictive.probability.probability_threshold_manager import ProbabilityThresholdManager

logger = logging.getLogger('erp.simulation.predictive.probability.engine')


class FailureProbabilityEngine:
    def __init__(self, max_history: int = 500):
        self._max_history = max_history
        self._probability_history: deque = deque(maxlen=max_history)
        self._weights = ProbabilityWeightRegistry()
        self._thresholds = ProbabilityThresholdManager()

    def estimate(self, drift_history: List[Dict[str, Any]],
                 root_cause_data: List[Dict[str, Any]],
                 workflow_scores: Dict[str, float],
                 causal_chains: List[Dict[str, Any]],
                 current_tick: int) -> FailureProbability:
        mismatch_prob = self._calc_mismatch_probability(drift_history, current_tick)
        workflow_prob = self._calc_workflow_failure_probability(workflow_scores)
        propagation_prob = self._calc_propagation_probability(
            workflow_scores, causal_chains,
        )
        causal_prob = self._calc_causal_chain_probability(causal_chains)
        overall = self._calc_overall_risk(mismatch_prob, workflow_prob,
                                          propagation_prob, causal_prob)
        explanation = self._build_explanation(
            mismatch_prob, workflow_prob, propagation_prob, causal_prob, overall,
        )
        result = FailureProbability(
            mismatch_probability=round(mismatch_prob, 4),
            workflow_failure_probability=round(workflow_prob, 4),
            propagation_instability_probability=round(propagation_prob, 4),
            causal_chain_failure_probability=round(causal_prob, 4),
            overall_risk_score=round(overall, 4),
            components={
                'drift_count': len(drift_history),
                'workflow_count': len(workflow_scores),
                'causal_chain_count': len(causal_chains),
                'high_risk_workflows': sum(1 for s in workflow_scores.values() if s >= 50),
            },
            explanation=explanation,
        )
        self._probability_history.append({
            'tick': current_tick,
            'result': result,
        })
        return result

    def _calc_mismatch_probability(self, drift_history: List[Dict],
                                   current_tick: int) -> float:
        weight = self._weights.get_weight('mismatch_density')
        if not drift_history or current_tick == 0:
            return 0.0
        density = len(drift_history) / current_tick
        recent = [d for d in drift_history
                  if d.get('tick', 0) >= current_tick - 10]
        recent_density = len(recent) / max(len(drift_history), 1)
        raw = (density * weight + recent_density * (1 - weight)) * 100
        return min(max(raw, 0.0), 100.0)

    def _calc_workflow_failure_probability(self,
                                           workflow_scores: Dict[str, float]) -> float:
        if not workflow_scores:
            return 0.0
        scores = list(workflow_scores.values())
        avg = sum(scores) / len(scores)
        max_score = max(scores)
        return min(avg * 0.4 + max_score * 0.6, 100.0)

    def _calc_propagation_probability(self, workflow_scores: Dict[str, float],
                                      causal_chains: List[Dict]) -> float:
        if not workflow_scores or not causal_chains:
            return 0.0
        high_risk_count = sum(1 for s in workflow_scores.values() if s >= 50)
        propagation_weight = self._weights.get_weight('propagation_risk')
        raw = (high_risk_count / max(len(workflow_scores), 1)) * 100 * propagation_weight
        return min(raw, 100.0)

    def _calc_causal_chain_probability(self,
                                       causal_chains: List[Dict]) -> float:
        if not causal_chains:
            return 0.0
        chains_with_links = sum(1 for c in causal_chains if len(c.get('links', [])) > 0)
        if chains_with_links == 0:
            return 0.0
        avg_links = sum(len(c.get('links', [])) for c in causal_chains) / chains_with_links
        weight = self._weights.get_weight('causal_chain_risk')
        raw = (chains_with_links / max(len(causal_chains), 1)) * avg_links * 10 * weight
        return min(raw, 100.0)

    def _calc_overall_risk(self, mismatch_prob: float, workflow_prob: float,
                           propagation_prob: float, causal_prob: float) -> float:
        return (mismatch_prob * 0.3 + workflow_prob * 0.35
                + propagation_prob * 0.2 + causal_prob * 0.15)

    def _build_explanation(self, mismatch_prob: float, workflow_prob: float,
                           propagation_prob: float, causal_prob: float,
                           overall: float) -> List[str]:
        explanations: List[str] = []
        if mismatch_prob >= 50:
            explanations.append(f'High mismatch density probability ({mismatch_prob:.1f}%)')
        if workflow_prob >= 50:
            explanations.append(f'Elevated workflow failure risk ({workflow_prob:.1f}%)')
        if propagation_prob >= 30:
            explanations.append(f'Significant instability propagation risk ({propagation_prob:.1f}%)')
        if causal_prob >= 30:
            explanations.append(f'Notable causal chain failure probability ({causal_prob:.1f}%)')
        if not explanations:
            explanations.append('All risk factors within acceptable thresholds')
        explanations.append(f'Overall risk score: {overall:.1f}')
        return explanations

    @property
    def record_count(self) -> int:
        return len(self._probability_history)

    def clear(self):
        self._probability_history.clear()
        self._weights.clear()
        self._thresholds.clear()

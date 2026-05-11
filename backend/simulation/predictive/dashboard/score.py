import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.dashboard.score')


class PredictiveStabilityScore:
    def __init__(self, max_history: int = 100):
        self._max_history = max_history
        self._score_history: deque = deque(maxlen=max_history)

    def compute(self, drift_trend: Dict[str, Any],
                velocity: Dict[str, Any],
                forecast: Dict[str, Any],
                workflow_scores: Dict[str, float],
                warning_counts: Dict[str, int],
                failure_prob: Dict[str, Any]) -> Dict[str, Any]:
        deductions = 0.0
        if drift_trend.get('critical_escalation', False):
            deductions += 25
        elif drift_trend.get('worsening', False):
            deductions += 10
        accel = abs(velocity.get('drift_acceleration', 0))
        deductions += min(accel * 2, 10)
        density = forecast.get('predicted_drift_density', 0)
        deductions += min(density * 0.5, 10)
        high_risk_wf = sum(1 for s in workflow_scores.values() if s >= 50)
        deductions += high_risk_wf * 5
        critical_w = warning_counts.get('critical', 0)
        high_w = warning_counts.get('high', 0)
        deductions += critical_w * 8 + high_w * 3
        prob = failure_prob.get('probability', 0)
        deductions += prob * 0.2
        score = max(0, 100 - deductions)
        final_score = min(100, round(score, 2))
        level = self._classify(final_score)
        self._score_history.append({
            'score': final_score,
            'level': level,
            'deductions': round(deductions, 2),
        })
        return {
            'score': final_score,
            'level': level,
            'deductions': round(deductions, 2),
            'components': {
                'escalation_penalty': 25 if drift_trend.get('critical_escalation', False) else 10 if drift_trend.get('worsening', False) else 0,
                'acceleration_penalty': round(min(accel * 2, 10), 2),
                'density_penalty': round(min(density * 0.5, 10), 2),
                'high_risk_workflows': high_risk_wf * 5,
                'warning_penalty': critical_w * 8 + high_w * 3,
                'probability_penalty': round(prob * 0.2, 2),
            },
        }

    def _classify(self, score: float) -> str:
        if score >= 80:
            return 'stable'
        if score >= 60:
            return 'watch'
        if score >= 40:
            return 'unstable'
        return 'critical'

    def get_trend(self) -> List[Dict[str, Any]]:
        return [{'score': s['score'], 'level': s['level']}
                for s in self._score_history]

    @property
    def record_count(self) -> int:
        return len(self._score_history)

    def clear(self):
        self._score_history.clear()

import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.dashboard.report')


class PredictiveHealthReportGenerator:
    def generate(self, tick: int,
                 drift_trend: Dict[str, Any],
                 velocity: Dict[str, Any],
                 forecast: Dict[str, Any],
                 workflow_scores: Dict[str, float],
                 workflow_degradations: Dict[str, float],
                 warning_counts: Dict[str, int],
                 stability_score: Dict[str, Any],
                 failure_prob: Dict[str, Any],
                 high_risk_workflows: Dict[str, float],
                 timeline: Dict[str, Any]) -> Dict[str, Any]:
        top_risks = sorted(high_risk_workflows.items(), key=lambda x: x[1], reverse=True)[:3]
        wf_ranking = sorted(workflow_scores.items(), key=lambda x: x[1], reverse=True)
        return {
            'report_id': str(uuid.uuid4()),
            'tick': tick,
            'summary': {
                'stability_score': stability_score.get('score', 0),
                'stability_level': stability_score.get('level', 'unknown'),
                'trend_status': drift_trend.get('trend_status', 'unknown'),
                'predicted_drift_density': forecast.get('predicted_drift_density', 0),
                'total_warnings_active': sum(warning_counts.values()),
                'high_risk_workflow_count': len(high_risk_workflows),
                'failure_probability': failure_prob.get('probability', 0),
                'failure_level': failure_prob.get('level', 'normal'),
            },
            'top_predicted_risks': [
                {'workflow': wf, 'score': score}
                for wf, score in top_risks
            ],
            'workflow_instability_ranking': [
                {'workflow': wf, 'score': score}
                for wf, score in wf_ranking
            ],
            'escalation_indicators': self._detect_escalations(
                drift_trend, stability_score, warning_counts),
            'forecast': {
                'short_term': forecast.get('short_term'),
                'medium_term': forecast.get('medium_term'),
                'long_term': forecast.get('long_term'),
            },
            'operational_pressure': {
                'drift_acceleration': velocity.get('drift_acceleration', 0),
                'instability_momentum': velocity.get('instability_momentum', 0),
                'warning_pressure': sum(warning_counts.get(l, 0) * m
                                        for l, m in [('critical', 5), ('high', 3),
                                                     ('medium', 2), ('low', 1)]),
            },
            'confidence_summary': {
                'sample_size': drift_trend.get('sample_size', 0),
                'velocity_samples': velocity.get('sample_size', 0),
                'forecast_samples': forecast.get('sample_size', 0),
                'data_sufficient': drift_trend.get('sample_size', 0) >= 2,
            },
            'predictive_horizons': timeline.get('predicted_horizons', []),
        }

    def _detect_escalations(self, drift_trend: Dict[str, Any],
                            stability_score: Dict[str, Any],
                            warning_counts: Dict[str, int]) -> List[Dict[str, str]]:
        indicators = []
        if drift_trend.get('critical_escalation', False):
            indicators.append({'type': 'critical_escalation',
                               'severity': 'critical',
                               'message': 'Mismatch growth is critically accelerating'})
        if drift_trend.get('worsening', False):
            indicators.append({'type': 'worsening_trend',
                               'severity': 'high',
                               'message': 'Drift trend is worsening'})
        if stability_score.get('level') in ('unstable', 'critical'):
            indicators.append({'type': 'stability_degradation',
                               'severity': 'high',
                               'message': f"Stability score is {stability_score.get('level')}"})
        if warning_counts.get('critical', 0) > 0:
            indicators.append({'type': 'active_critical_warnings',
                               'severity': 'critical',
                               'message': f"{warning_counts['critical']} critical warnings active"})
        return indicators

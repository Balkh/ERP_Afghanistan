import logging
from typing import Any, Dict, List, Optional

from simulation.predictive.models import (
    PredictiveHealthReport, EarlyWarning, FailureProbability,
    DriftTrendResult, DriftForecastWindow, WarningSeverity,
    TrendDirection,
)
from simulation.predictive.dashboard.predictive_stability_score import PredictiveStabilityScore
from simulation.predictive.dashboard.predictive_timeline import PredictiveTimelineGenerator

logger = logging.getLogger('erp.simulation.predictive.dashboard.report')

WORKFLOW_TYPES = ['sales', 'purchase', 'inventory', 'return', 'hr']


class PredictiveHealthReportGenerator:
    def __init__(self):
        self._stability_score = PredictiveStabilityScore()
        self._timeline_generator = PredictiveTimelineGenerator()

    def generate(self, trends: List[DriftTrendResult],
                 forecast: DriftForecastWindow,
                 probability: FailureProbability,
                 warnings: List[EarlyWarning],
                 workflow_scores: Dict[str, float],
                 workflow_history: Any,
                 current_tick: int) -> PredictiveHealthReport:
        top_risks = self._identify_top_risks(trends, probability, warnings)
        instability_ranking = self._rank_workflow_instability(workflow_scores, trends)
        escalation_indicators = self._find_escalation_indicators(trends, warnings)
        drift_density = self._forecast_drift_density(forecast)
        pressure = self._assess_operational_pressure(trends, warnings, probability)
        confidence = self._summarize_confidence(forecast, probability)
        score = self._stability_score.calculate(trends, probability, warnings, workflow_scores)
        status = self._determine_status(score, warnings)
        report = PredictiveHealthReport(
            top_risks=top_risks,
            workflow_instability_ranking=instability_ranking,
            escalation_indicators=escalation_indicators,
            forecasted_drift_density=drift_density,
            operational_pressure_indicators=pressure,
            confidence_summary=confidence,
            stability_score=score,
            overall_status=status,
        )
        return report

    def _identify_top_risks(self, trends: List[DriftTrendResult],
                            probability: FailureProbability,
                            warnings: List[EarlyWarning]) -> List[Dict[str, Any]]:
        risks: List[Dict[str, Any]] = []
        for t in trends:
            if t.direction in (TrendDirection.WORSENING, TrendDirection.CRITICAL):
                risks.append({
                    'module': t.module,
                    'risk_type': 'drift_trend',
                    'severity': t.direction.value,
                    'description': f'{t.module} module has {t.direction.value} drift trend',
                    'details': {'mismatch_count': t.mismatch_count,
                                'acceleration': t.instability_acceleration},
                })
        if probability.overall_risk_score >= 50:
            risks.append({
                'module': 'system',
                'risk_type': 'failure_probability',
                'severity': 'high',
                'description': f'Overall failure probability: {probability.overall_risk_score:.1f}%',
                'details': {'mismatch_prob': probability.mismatch_probability,
                            'workflow_prob': probability.workflow_failure_probability},
            })
        critical_warnings = [w for w in warnings if w.severity == WarningSeverity.CRITICAL]
        for w in critical_warnings[:3]:
            risks.append({
                'module': w.source_module,
                'risk_type': 'early_warning',
                'severity': 'critical',
                'description': w.title,
                'details': w.details,
            })
        risks.sort(key=lambda r: {'critical': 0, 'high': 1, 'medium': 2,
                                  'low': 3, 'stable': 4}.get(r['severity'], 5))
        return risks[:10]

    def _rank_workflow_instability(self, workflow_scores: Dict[str, float],
                                   trends: List[DriftTrendResult]) -> List[Dict[str, Any]]:
        ranking: List[Dict[str, Any]] = []
        for wt in WORKFLOW_TYPES:
            score = workflow_scores.get(wt, 0.0)
            trend = next((t for t in trends if t.module == wt), None)
            ranking.append({
                'workflow': wt,
                'risk_score': score,
                'trend_direction': trend.direction.value if trend else 'stable',
                'mismatch_count': trend.mismatch_count if trend else 0,
            })
        ranking.sort(key=lambda r: r['risk_score'], reverse=True)
        return ranking

    def _find_escalation_indicators(self, trends: List[DriftTrendResult],
                                    warnings: List[EarlyWarning]) -> List[Dict[str, Any]]:
        indicators: List[Dict[str, Any]] = []
        for t in trends:
            if t.severity_escalation.value in ('high', 'critical'):
                indicators.append({
                    'module': t.module,
                    'type': 'severity_escalation',
                    'level': t.severity_escalation.value,
                    'detail': f'{t.module} severity escalating',
                })
        for w in warnings:
            if w.severity in (WarningSeverity.HIGH, WarningSeverity.CRITICAL):
                indicators.append({
                    'module': w.source_module,
                    'type': 'warning',
                    'level': w.severity.value,
                    'detail': w.title,
                })
        return indicators[:10]

    def _forecast_drift_density(self, forecast: DriftForecastWindow) -> Dict[str, Any]:
        short_avg = (sum(p.predicted_drift_density for p in forecast.short_term)
                     / max(len(forecast.short_term), 1))
        medium_avg = (sum(p.predicted_drift_density for p in forecast.medium_term)
                      / max(len(forecast.medium_term), 1))
        long_avg = (sum(p.predicted_drift_density for p in forecast.long_term)
                    / max(len(forecast.long_term), 1))
        return {
            'short_term_avg_density': round(short_avg, 4),
            'medium_term_avg_density': round(medium_avg, 4),
            'long_term_avg_density': round(long_avg, 4),
            'overall_trend': forecast.overall_trend.value,
        }

    def _assess_operational_pressure(self, trends: List[DriftTrendResult],
                                     warnings: List[EarlyWarning],
                                     probability: FailureProbability) -> List[Dict[str, Any]]:
        pressure: List[Dict[str, Any]] = []
        worsening_count = sum(1 for t in trends
                              if t.direction in (TrendDirection.WORSENING, TrendDirection.CRITICAL))
        active_warnings = len(warnings)
        if worsening_count >= 3:
            pressure.append({
                'type': 'degradation_pressure',
                'level': 'high',
                'detail': f'{worsening_count} modules in degradation',
            })
        if active_warnings >= 5:
            pressure.append({
                'type': 'warning_pressure',
                'level': 'medium',
                'detail': f'{active_warnings} active warnings',
            })
        if probability.overall_risk_score >= 60:
            pressure.append({
                'type': 'risk_pressure',
                'level': 'high',
                'detail': f'Risk score {probability.overall_risk_score:.1f} above threshold',
            })
        return pressure

    def _summarize_confidence(self, forecast: DriftForecastWindow,
                              probability: FailureProbability) -> Dict[str, Any]:
        high_confidence = sum(1 for p in forecast.short_term
                              if p.confidence.value == 'high')
        return {
            'forecast_confidence': 'high' if high_confidence >= len(forecast.short_term) * 0.5 else 'medium',
            'probability_explainability': len(probability.explanation),
            'data_sufficiency': 'adequate',
        }

    def _determine_status(self, score: float, warnings: List[EarlyWarning]) -> str:
        if score >= 80:
            return 'STABLE'
        if score >= 60:
            return 'MONITOR'
        if score >= 40:
            return 'WARNING'
        return 'CRITICAL'

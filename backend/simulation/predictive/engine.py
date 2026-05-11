"""
PredictiveEngine — Phase 3C orchestrator.
Wires all predictive subsystems together.
Read-only. Deterministic. Bounded memory.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.predictive.trends.analyzer import DriftTrendAnalyzer
from simulation.predictive.trends.velocity import DriftVelocityTracker
from simulation.predictive.trends.forecast import DriftForecastWindow
from simulation.predictive.workflows.scorer import WorkflowRiskScorer
from simulation.predictive.workflows.predictor import (
    WorkflowInstabilityPredictor,
)
from simulation.predictive.workflows.history import WorkflowRiskHistory
from simulation.predictive.probability.engine import FailureProbabilityEngine
from simulation.predictive.warnings.engine import EarlyWarningEngine
from simulation.predictive.dashboard.score import PredictiveStabilityScore
from simulation.predictive.dashboard.timeline import PredictiveTimeline
from simulation.predictive.dashboard.report import (
    PredictiveHealthReportGenerator,
)
from simulation.predictive.integration.root_cause_bridge import (
    RootCausePredictiveBridge,
)
from simulation.predictive.safety.memory_guard import PredictiveMemoryGuard
from simulation.predictive.safety.performance import (
    PredictivePerformanceMonitor,
)
from simulation.predictive.safety.isolation import PredictionFailureIsolation

logger = logging.getLogger('erp.simulation.predictive.engine')


class PredictiveEngine:
    def __init__(self):
        self._trend_analyzer = DriftTrendAnalyzer()
        self._velocity_tracker = DriftVelocityTracker()
        self._forecast_window = DriftForecastWindow()
        self._workflow_scorer = WorkflowRiskScorer()
        self._instability_predictor = WorkflowInstabilityPredictor()
        self._workflow_history = WorkflowRiskHistory()
        self._probability_engine = FailureProbabilityEngine()
        self._warning_engine = EarlyWarningEngine()
        self._stability_score = PredictiveStabilityScore()
        self._timeline = PredictiveTimeline()
        self._report_generator = PredictiveHealthReportGenerator()
        self._root_cause_bridge = RootCausePredictiveBridge()
        self._memory_guard = PredictiveMemoryGuard()
        self._perf_monitor = PredictivePerformanceMonitor()
        self._failure_isolation = PredictionFailureIsolation()
        self._current_tick: int = 0

    @property
    def trend_analyzer(self) -> DriftTrendAnalyzer:
        return self._trend_analyzer

    @property
    def velocity_tracker(self) -> DriftVelocityTracker:
        return self._velocity_tracker

    @property
    def forecast_window(self) -> DriftForecastWindow:
        return self._forecast_window

    @property
    def workflow_scorer(self) -> WorkflowRiskScorer:
        return self._workflow_scorer

    @property
    def instability_predictor(self) -> WorkflowInstabilityPredictor:
        return self._instability_predictor

    @property
    def workflow_history(self) -> WorkflowRiskHistory:
        return self._workflow_history

    @property
    def probability_engine(self) -> FailureProbabilityEngine:
        return self._probability_engine

    @property
    def warning_engine(self) -> EarlyWarningEngine:
        return self._warning_engine

    @property
    def stability_score(self) -> PredictiveStabilityScore:
        return self._stability_score

    @property
    def timeline(self) -> PredictiveTimeline:
        return self._timeline

    @property
    def report_generator(self) -> PredictiveHealthReportGenerator:
        return self._report_generator

    @property
    def root_cause_bridge(self) -> RootCausePredictiveBridge:
        return self._root_cause_bridge

    @property
    def memory_guard(self) -> PredictiveMemoryGuard:
        return self._memory_guard

    @property
    def perf_monitor(self) -> PredictivePerformanceMonitor:
        return self._perf_monitor

    @property
    def failure_isolation(self) -> PredictionFailureIsolation:
        return self._failure_isolation

    @property
    def current_tick(self) -> int:
        return self._current_tick

    def analyze_tick(self, tick: int,
                     mismatch_count: int,
                     severity_counts: Dict[str, int],
                     affected_modules: Dict[str, int],
                     workflow_completions: Dict[str, int],
                     agent_executions: Dict[str, int],
                     event_history: List[Any],
                     root_cause_engine: Any = None):
        self._current_tick = tick
        self._trend_analyzer.record_snapshot(
            tick, mismatch_count, severity_counts, affected_modules)
        self._velocity_tracker.record_tick(tick, mismatch_count)
        self._forecast_window.record(
            tick, mismatch_count, severity_counts, affected_modules)

        if root_cause_engine:
            self._root_cause_bridge.bind(root_cause_engine)
            recurring = self._root_cause_bridge.get_recurring_root_causes()
            causal_stats = self._root_cause_bridge.get_causal_chain_statistics()
        else:
            recurring = {}
            causal_stats = {}

        drift_trend = self._trend_analyzer.analyze_trends()
        velocity = self._velocity_tracker.compute_velocity()
        forecast = self._forecast_window.forecast()

        return {
            'tick': tick,
            'drift_trend': drift_trend,
            'velocity': velocity,
            'forecast': forecast,
            'recurring_root_causes': recurring,
            'causal_chain_stats': causal_stats,
        }

    def analyze_workflows(self, tick: int,
                          drift_history: List[Dict[str, Any]],
                          root_cause_recurrence: Dict[str, int],
                          causal_links: List[Dict],
                          active_workflows: List[str],
                          dependency_map: Dict[str, List[str]]):
        scores: Dict[str, float] = {}
        degradations: Dict[str, float] = {}
        for wf in ('sales', 'purchase', 'inventory', 'return', 'hr'):
            score = self._workflow_scorer.score_workflow(
                wf, drift_history, root_cause_recurrence)
            self._workflow_scorer.record_risk(
                tick, wf, score, {'base': score})
            trend = self._workflow_scorer.get_risk_trend(wf)
            degradation = self._instability_predictor.predict_degradation(
                wf, score, trend.get('direction', 'stable'),
                root_cause_recurrence.get(wf, 0), 0)
            self._instability_predictor.record_prediction(
                tick, wf, degradation)
            self._workflow_history.record(
                tick, wf, score, degradation,
                {'trend_direction': trend.get('direction', 'stable')})
            scores[wf] = score
            degradations[wf] = degradation

        propagation = self._instability_predictor.predict_instability_propagation(
            scores, causal_links)
        collision = self._instability_predictor.predict_collision_risk(
            active_workflows, scores)
        cascade = self._instability_predictor.predict_cascading_failure(
            scores, dependency_map)
        return {
            'workflow_scores': scores,
            'degradation_probabilities': degradations,
            'propagation_risk': propagation,
            'collision_risk': collision,
            'cascade_risk': cascade,
        }

    def evaluate_warnings(self, tick: int,
                          drift_trend: Dict[str, Any],
                          forecast: Dict[str, Any],
                          workflow_scores: Dict[str, float],
                          event_analysis: Dict[str, Any]):
        warnings_generated = []

        inv = self._warning_engine.evaluate_inventory_drift_risk(
            tick, drift_trend, forecast, workflow_scores)
        if inv:
            warnings_generated.append(inv)

        for wf, score in workflow_scores.items():
            w = self._warning_engine.evaluate_workflow_instability(
                tick, wf, score, score * 0.5,
                drift_trend.get('trend_status', 'stable'))
            if w:
                warnings_generated.append(w)

        if event_analysis:
            fan_out = event_analysis.get('fan_out_chains', [])
            total = event_analysis.get('total_events', 0)
            sat = self._warning_engine.evaluate_event_propagation_saturation(
                tick, total, fan_out, 100)
            if sat:
                warnings_generated.append(sat)

        severity_esc = drift_trend.get('severity_escalation', False)
        recon = self._warning_engine.evaluate_reconciliation_degradation(
            tick, drift_trend.get('sample_size', 0),
            severity_esc, drift_trend.get('trend_status', 'stable'))
        if recon:
            warnings_generated.append(recon)

        return warnings_generated

    def generate_health_report(self, tick: int) -> Dict[str, Any]:
        drift_trend = self._trend_analyzer.analyze_trends()
        velocity = self._velocity_tracker.compute_velocity()
        forecast = self._forecast_window.forecast()

        scores: Dict[str, float] = {}
        degradations: Dict[str, float] = {}
        for wf in ('sales', 'purchase', 'inventory', 'return', 'hr'):
            s = self._workflow_scorer.get_risk_trend(wf)
            scores[wf] = s.get('avg_score', 0)
            degradations[wf] = self._instability_predictor.predict_degradation(
                wf, scores[wf], s.get('direction', 'stable'), 0, 0)

        warning_counts = {}
        for level in ('info', 'low', 'medium', 'high', 'critical'):
            warning_counts[level] = self._warning_engine.retention.get_warning_count(level)

        failure_prob = self._probability_engine.estimate_mismatch_probability(
            drift_trend, velocity, forecast)

        stability = self._stability_score.compute(
            drift_trend, velocity, forecast, scores,
            warning_counts, failure_prob)

        high_risk = self._workflow_history.get_high_risk_workflows()
        timeline = self._timeline.build_timeline(
            {'short_term': forecast.get('short_term'),
             'medium_term': forecast.get('medium_term'),
             'long_term': forecast.get('long_term')},
            stability, high_risk)

        report = self._report_generator.generate(
            tick, drift_trend, velocity, forecast, scores,
            degradations, warning_counts, stability, failure_prob,
            high_risk, timeline)

        self._memory_guard.register(
            'trend_analyzer', self._trend_analyzer.snapshot_count, 1000)
        self._memory_guard.register(
            'velocity_tracker', self._velocity_tracker.sample_count, 100)
        self._memory_guard.register(
            'forecast_window', self._forecast_window.record_count, 500)
        self._memory_guard.register(
            'workflow_scorer', self._workflow_scorer.record_count, 500)
        self._memory_guard.register(
            'instability_predictor', self._instability_predictor.record_count, 200)
        self._memory_guard.register(
            'workflow_history', self._workflow_history.record_count, 500)
        self._memory_guard.register(
            'warning_retention',
            self._warning_engine.retention.warning_count,
            self._warning_engine.retention.max_warnings)

        report['memory_audit'] = self._memory_guard.audit_all()
        report['performance'] = self._perf_monitor.get_latency_report()
        report['failure_isolation'] = {
            'failure_count': self._failure_isolation.failure_count,
            'last_failure': self._failure_isolation.last_failure,
            'degraded_mode': self._failure_isolation.degraded_mode,
        }
        return report

    def reset(self):
        self._trend_analyzer.clear()
        self._velocity_tracker.clear()
        self._forecast_window.clear()
        self._workflow_scorer.clear()
        self._instability_predictor.clear()
        self._workflow_history.clear()
        self._probability_engine.clear()
        self._warning_engine.clear()
        self._stability_score.clear()
        self._timeline.clear()
        self._memory_guard.clear()
        self._perf_monitor.clear()
        self._failure_isolation.reset()
        self._current_tick = 0

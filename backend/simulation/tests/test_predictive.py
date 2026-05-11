"""Phase 3C: deterministic tests for predictive intelligence layer."""
import unittest
from collections import deque

from simulation.predictive.trends.analyzer import DriftTrendAnalyzer
from simulation.predictive.trends.velocity import DriftVelocityTracker
from simulation.predictive.trends.forecast import DriftForecastWindow
from simulation.predictive.workflows.scorer import WorkflowRiskScorer
from simulation.predictive.workflows.predictor import (
    WorkflowInstabilityPredictor,
)
from simulation.predictive.workflows.history import WorkflowRiskHistory
from simulation.predictive.probability.weights import (
    ProbabilityWeightRegistry,
)
from simulation.predictive.probability.thresholds import (
    ProbabilityThresholdManager,
)
from simulation.predictive.probability.engine import FailureProbabilityEngine
from simulation.predictive.warnings.classifier import WarningSeverityClassifier
from simulation.predictive.warnings.retention import WarningRetentionManager
from simulation.predictive.warnings.deduplicator import WarningDeduplicator
from simulation.predictive.warnings.engine import EarlyWarningEngine
from simulation.predictive.dashboard.score import PredictiveStabilityScore
from simulation.predictive.dashboard.timeline import PredictiveTimeline
from simulation.predictive.dashboard.report import (
    PredictiveHealthReportGenerator,
)
from simulation.predictive.safety.memory_guard import PredictiveMemoryGuard
from simulation.predictive.safety.performance import (
    PredictivePerformanceMonitor,
)
from simulation.predictive.safety.isolation import PredictionFailureIsolation
from simulation.predictive.engine import PredictiveEngine


class TestDriftTrendAnalyzer(unittest.TestCase):
    def test_insufficient_data_returns_stable(self):
        a = DriftTrendAnalyzer()
        result = a.analyze_trends()
        self.assertEqual(result['trend_status'], 'insufficient_data')
        self.assertTrue(result['stable'])

    def test_stable_trend_detected(self):
        a = DriftTrendAnalyzer()
        for i in range(10):
            a.record_snapshot(i, 5, {'low': 5}, {'sales': 5})
        result = a.analyze_trends()
        self.assertTrue(result['stable'])
        self.assertFalse(result['worsening'])

    def test_worsening_trend_detected(self):
        a = DriftTrendAnalyzer()
        for i in range(10):
            a.record_snapshot(i, i * 3, {'low': i * 3}, {'sales': i * 3})
        result = a.analyze_trends()
        self.assertTrue(result['worsening'])

    def test_critical_escalation_detected(self):
        a = DriftTrendAnalyzer()
        for i in range(5):
            a.record_snapshot(i, 1, {'low': 1}, {'inventory': 1})
        for i in range(5, 10):
            a.record_snapshot(i, 50 + i * 5, {'critical': i},
                              {'inventory': 50 + i * 5})
        result = a.analyze_trends()
        self.assertTrue(result['critical_escalation'])

    def test_severity_escalation_detected(self):
        a = DriftTrendAnalyzer()
        for i in range(5):
            a.record_snapshot(i, 1, {'critical': 1}, {'sales': 1})
        for i in range(5, 10):
            a.record_snapshot(i, 2, {'critical': 4}, {'sales': 2})
        result = a.analyze_trends()
        self.assertTrue(result['severity_escalation'])

    def test_dominant_category_found(self):
        a = DriftTrendAnalyzer()
        for i in range(5):
            a.record_snapshot(i, 5, {'low': 5},
                             {'inventory': 8, 'sales': 2})
        result = a.analyze_trends()
        self.assertEqual(result['dominant_drift_category'], 'inventory')

    def test_clear_resets(self):
        a = DriftTrendAnalyzer()
        a.record_snapshot(1, 5, {'low': 5}, {'sales': 5})
        a.clear()
        self.assertEqual(a.snapshot_count, 0)

    def test_bounded_memory(self):
        a = DriftTrendAnalyzer(max_history=5)
        for i in range(20):
            a.record_snapshot(i, i, {'low': i}, {'mod': i})
        self.assertEqual(a.snapshot_count, 5)

    def test_growth_rate_positive(self):
        a = DriftTrendAnalyzer()
        for i in range(10):
            a.record_snapshot(i, i * 2, {'low': i * 2}, {'mod': i * 2})
        result = a.analyze_trends()
        self.assertGreater(result['mismatch_growth_rate'], 0)


class TestDriftVelocityTracker(unittest.TestCase):
    def test_insufficient_data(self):
        v = DriftVelocityTracker()
        result = v.compute_velocity()
        self.assertEqual(result['sample_size'], 0)

    def test_velocity_computed(self):
        v = DriftVelocityTracker()
        for i in range(10):
            v.record_tick(i, i * 2)
        result = v.compute_velocity()
        self.assertGreaterEqual(result['sample_size'], 2)
        self.assertIsInstance(result['drift_acceleration'], float)

    def test_zero_velocity_when_flat(self):
        v = DriftVelocityTracker()
        for i in range(10):
            v.record_tick(i, 5)
        result = v.compute_velocity()
        self.assertEqual(result['instability_momentum'], 0)

    def test_recurrence_velocity(self):
        v = DriftVelocityTracker()
        for i in range(10):
            v.record_tick(i, i)
        result = v.compute_velocity()
        self.assertGreater(result['recurrence_velocity'], 0)

    def test_bounded_memory(self):
        v = DriftVelocityTracker(max_window=5)
        for i in range(20):
            v.record_tick(i, i)
        self.assertEqual(v.sample_count, 5)

    def test_clear(self):
        v = DriftVelocityTracker()
        v.record_tick(1, 5)
        v.clear()
        self.assertEqual(v.sample_count, 0)


class TestDriftForecastWindow(unittest.TestCase):
    def test_insufficient_data(self):
        f = DriftForecastWindow()
        result = f.forecast()
        self.assertIsNone(result['short_term'])

    def test_forecast_windows_produced(self):
        f = DriftForecastWindow()
        for i in range(20):
            f.record(i, i * 2, {'low': i}, {'mod': i})
        result = f.forecast()
        self.assertIsNotNone(result['short_term'])
        self.assertIsNotNone(result['medium_term'])
        self.assertIsNotNone(result['long_term'])

    def test_escalation_regions(self):
        f = DriftForecastWindow()
        for i in range(20):
            f.record(i, 5, {'low': 5},
                     {'inventory': i * 2, 'sales': 1})
        result = f.forecast()
        self.assertIn('inventory', result['probable_escalation_regions'])

    def test_predicted_drift_density(self):
        f = DriftForecastWindow()
        for i in range(20):
            f.record(i, 10 + i, {'low': 10 + i}, {'mod': 10 + i})
        result = f.forecast()
        self.assertGreater(result['predicted_drift_density'], 0)

    def test_bounded_memory(self):
        f = DriftForecastWindow(max_history=10)
        for i in range(50):
            f.record(i, i, {'low': i}, {'mod': i})
        self.assertEqual(f.record_count, 10)

    def test_clear(self):
        f = DriftForecastWindow()
        f.record(1, 5, {'low': 5}, {'mod': 5})
        f.clear()
        self.assertEqual(f.record_count, 0)


class TestWorkflowRiskScorer(unittest.TestCase):
    def test_unknown_wf_returns_zero(self):
        s = WorkflowRiskScorer()
        score = s.score_workflow('unknown', [], {})
        self.assertEqual(score, 0.0)

    def test_score_increases_with_history(self):
        s = WorkflowRiskScorer()
        drift = [{'mismatch': {'affected_module': 'sales'}}
                 for _ in range(10)]
        score = s.score_workflow('sales', drift, {'sales': 3})
        self.assertGreater(score, 0)

    def test_risk_trend_stable_initially(self):
        s = WorkflowRiskScorer()
        trend = s.get_risk_trend('sales')
        self.assertEqual(trend['direction'], 'stable')

    def test_risk_trend_detected(self):
        s = WorkflowRiskScorer()
        for i in range(10):
            s.record_risk(i, 'sales', 30 + i, {'base': 30 + i})
        trend = s.get_risk_trend('sales')
        self.assertIn(trend['direction'], ('worsening', 'stable'))

    def test_bounded_memory(self):
        s = WorkflowRiskScorer(max_history=5)
        for i in range(20):
            s.record_risk(i, 'sales', float(i), {'base': float(i)})
        self.assertEqual(s.record_count, 5)

    def test_clear(self):
        s = WorkflowRiskScorer()
        s.record_risk(1, 'sales', 10, {'base': 10})
        s.clear()
        self.assertEqual(s.record_count, 0)


class TestWorkflowInstabilityPredictor(unittest.TestCase):
    def test_degradation_increases_with_risk(self):
        p = WorkflowInstabilityPredictor()
        d1 = p.predict_degradation('sales', 20, 'stable', 0, 0)
        d2 = p.predict_degradation('sales', 80, 'worsening', 5, 3)
        self.assertGreater(d2, d1)

    def test_propagation_from_high_risk(self):
        p = WorkflowInstabilityPredictor()
        scores = {'sales': 70, 'purchase': 20}
        links = [{'source_id': 'sales_1', 'target_id': 'inventory_1'}]
        prop = p.predict_instability_propagation(scores, links)
        self.assertIn('inventory', prop)

    def test_collision_risk_zero_with_few_workflows(self):
        p = WorkflowInstabilityPredictor()
        risk = p.predict_collision_risk(['sales'], {'sales': 80})
        self.assertEqual(risk, 0.0)

    def test_collision_risk_increases(self):
        p = WorkflowInstabilityPredictor()
        risk = p.predict_collision_risk(
            ['sales', 'purchase', 'inventory'],
            {'sales': 80, 'purchase': 60, 'inventory': 30})
        self.assertGreater(risk, 0)

    def test_cascading_failure(self):
        p = WorkflowInstabilityPredictor()
        scores = {'sales': 70, 'purchase': 20}
        deps = {'sales': ['inventory'], 'purchase': ['hr']}
        cascade = p.predict_cascading_failure(scores, deps)
        self.assertIn('inventory', cascade)

    def test_record_prediction(self):
        p = WorkflowInstabilityPredictor()
        p.record_prediction(1, 'sales', 50.0)
        self.assertEqual(p.record_count, 1)

    def test_clear(self):
        p = WorkflowInstabilityPredictor()
        p.record_prediction(1, 'sales', 50.0)
        p.clear()
        self.assertEqual(p.record_count, 0)


class TestWorkflowRiskHistory(unittest.TestCase):
    def test_record_and_retrieve(self):
        h = WorkflowRiskHistory()
        h.record(1, 'sales', 50.0, 30.0, {})
        hist = h.get_history('sales')
        self.assertEqual(len(hist), 1)

    def test_latest_score(self):
        h = WorkflowRiskHistory()
        h.record(1, 'sales', 50.0, 30.0, {})
        h.record(2, 'sales', 70.0, 40.0, {})
        self.assertEqual(h.get_latest_score('sales'), 70.0)

    def test_average_score(self):
        h = WorkflowRiskHistory()
        h.record(1, 'sales', 50.0, 30.0, {})
        h.record(2, 'sales', 70.0, 40.0, {})
        self.assertEqual(h.get_average_score('sales'), 60.0)

    def test_high_risk_workflows(self):
        h = WorkflowRiskHistory()
        h.record(1, 'sales', 60.0, 30.0, {})
        h.record(1, 'hr', 20.0, 10.0, {})
        high = h.get_high_risk_workflows(threshold=50)
        self.assertIn('sales', high)
        self.assertNotIn('hr', high)

    def test_since_tick_filter(self):
        h = WorkflowRiskHistory()
        h.record(1, 'sales', 50.0, 30.0, {})
        h.record(5, 'sales', 70.0, 40.0, {})
        hist = h.get_history('sales', since_tick=3)
        self.assertEqual(len(hist), 1)

    def test_bounded_memory(self):
        h = WorkflowRiskHistory(max_records=5)
        for i in range(20):
            h.record(i, 'sales', float(i), float(i), {})
        self.assertEqual(h.record_count, 5)

    def test_clear(self):
        h = WorkflowRiskHistory()
        h.record(1, 'sales', 50.0, 30.0, {})
        h.clear()
        self.assertEqual(h.record_count, 0)


class TestProbabilityWeightRegistry(unittest.TestCase):
    def test_default_weights_exist(self):
        r = ProbabilityWeightRegistry()
        self.assertGreater(r.weight_count, 0)

    def test_get_weight_returns_default(self):
        r = ProbabilityWeightRegistry()
        w = r.get_weight('mismatch_history_factor')
        self.assertGreater(w, 0)

    def test_set_weight_validates(self):
        r = ProbabilityWeightRegistry()
        with self.assertRaises(ValueError):
            r.set_weight('invalid_key', 0.5)

    def test_set_weight_clamps(self):
        r = ProbabilityWeightRegistry()
        r.set_weight('mismatch_history_factor', 1.5)
        self.assertEqual(r.get_weight('mismatch_history_factor'), 1.0)

    def test_normalized_weights_sum_to_one(self):
        r = ProbabilityWeightRegistry()
        nw = r.get_normalized_weights()
        total = sum(nw.values())
        self.assertAlmostEqual(total, 1.0, places=4)

    def test_get_all_weights(self):
        r = ProbabilityWeightRegistry()
        all_w = r.get_all_weights()
        self.assertGreater(len(all_w), 0)


class TestProbabilityThresholdManager(unittest.TestCase):
    def test_default_thresholds(self):
        t = ProbabilityThresholdManager()
        self.assertGreater(t.get_threshold('warning'), 0)
        self.assertGreater(t.get_threshold('escalation'), 0)
        self.assertGreater(t.get_threshold('critical'), 0)

    def test_classify_normal(self):
        t = ProbabilityThresholdManager()
        level = t.classify(10.0)
        self.assertEqual(level, 'normal')

    def test_classify_warning(self):
        t = ProbabilityThresholdManager()
        level = t.classify(30.0)
        self.assertEqual(level, 'warning')

    def test_classify_escalation(self):
        t = ProbabilityThresholdManager()
        level = t.classify(60.0)
        self.assertEqual(level, 'escalation')

    def test_classify_critical(self):
        t = ProbabilityThresholdManager()
        level = t.classify(80.0)
        self.assertEqual(level, 'critical')

    def test_set_threshold_validates(self):
        t = ProbabilityThresholdManager()
        with self.assertRaises(ValueError):
            t.set_threshold('invalid', 50.0)

    def test_set_threshold_clamps(self):
        t = ProbabilityThresholdManager()
        t.set_threshold('critical', 200)
        self.assertEqual(t.get_threshold('critical'), 100.0)


class TestFailureProbabilityEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FailureProbabilityEngine()

    def test_estimate_mismatch_probability(self):
        drift = {'mismatch_growth_rate': 20, 'instability_acceleration': 5}
        velocity = {'instability_momentum': 0.5}
        forecast = {'predicted_drift_density': 15}
        result = self.engine.estimate_mismatch_probability(
            drift, velocity, forecast)
        self.assertIn('probability', result)
        self.assertIn('level', result)
        self.assertGreaterEqual(result['probability'], 0)
        self.assertLessEqual(result['probability'], 100)

    def test_estimate_workflow_failure(self):
        result = self.engine.estimate_workflow_failure_probability(
            60, 40, 3, 2)
        self.assertIn('probability', result)
        self.assertIn('explanation', result)

    def test_propagation_probability(self):
        result = self.engine.estimate_propagation_probability(
            70, ['inventory'], {'inventory': 30})
        self.assertIn('inventory', result)

    def test_causal_chain_failure(self):
        result = self.engine.estimate_causal_chain_failure_probability(
            5, 0.9, 0.7)
        self.assertIn('probability', result)
        self.assertIn('chain_length', result)

    def test_weights_property(self):
        self.assertIsInstance(self.engine.weights, ProbabilityWeightRegistry)

    def test_thresholds_property(self):
        self.assertIsInstance(self.engine.thresholds,
                              ProbabilityThresholdManager)

    def test_record_estimate(self):
        self.engine.record_estimate(1, 'mismatch', 50.0, 'warning')
        self.assertEqual(self.engine.estimate_count, 1)

    def test_clear(self):
        self.engine.record_estimate(1, 'mismatch', 50.0, 'warning')
        self.engine.clear()
        self.assertEqual(self.engine.estimate_count, 0)


class TestWarningSeverityClassifier(unittest.TestCase):
    def setUp(self):
        self.c = WarningSeverityClassifier()

    def test_critical_when_high_score(self):
        self.assertEqual(self.c.classify(85, 80), 'critical')

    def test_critical_when_escalation(self):
        self.assertEqual(self.c.classify(30, 20, escalation=True), 'critical')

    def test_high_when_elevated(self):
        self.assertEqual(self.c.classify(65, 55), 'high')

    def test_medium_when_moderate(self):
        self.assertEqual(self.c.classify(45, 30), 'medium')

    def test_low_when_low(self):
        self.assertEqual(self.c.classify(25, 15), 'low')

    def test_info_when_minimal(self):
        self.assertEqual(self.c.classify(5, 5), 'info')

    def test_level_value_ordering(self):
        self.assertLess(self.c.get_level_value('info'),
                        self.c.get_level_value('critical'))


class TestWarningRetentionManager(unittest.TestCase):
    def setUp(self):
        self.r = WarningRetentionManager()

    def test_add_and_count(self):
        self.r.add_warning({'tick': 1, 'severity': 'high'})
        self.assertEqual(self.r.warning_count, 1)

    def test_get_warnings_by_level(self):
        self.r.add_warning({'tick': 1, 'severity': 'high'})
        self.r.add_warning({'tick': 2, 'severity': 'low'})
        highs = self.r.get_warnings(level='high')
        self.assertEqual(len(highs), 1)

    def test_get_warnings_since_tick(self):
        self.r.add_warning({'tick': 1, 'severity': 'high'})
        self.r.add_warning({'tick': 5, 'severity': 'critical'})
        recent = self.r.get_warnings(since_tick=3)
        self.assertEqual(len(recent), 1)

    def test_critical_warnings(self):
        self.r.add_warning({'tick': 1, 'severity': 'critical'})
        self.r.add_warning({'tick': 2, 'severity': 'high'})
        crits = self.r.get_critical_warnings()
        self.assertEqual(len(crits), 1)

    def test_bounded_memory(self):
        r = WarningRetentionManager(max_warnings=5)
        for i in range(20):
            r.add_warning({'tick': i, 'severity': 'info'})
        self.assertEqual(r.warning_count, 5)

    def test_clear(self):
        self.r.add_warning({'tick': 1, 'severity': 'high'})
        self.r.clear()
        self.assertEqual(self.r.warning_count, 0)


class TestWarningDeduplicator(unittest.TestCase):
    def test_first_occurrence_not_duplicate(self):
        d = WarningDeduplicator()
        w = {'warning_type': 'drift', 'workflow_type': 'sales',
             'affected_module': 'inventory', 'severity': 'high'}
        self.assertFalse(d.is_duplicate(w))

    def test_duplicate_detected(self):
        d = WarningDeduplicator()
        w = {'warning_type': 'drift', 'workflow_type': 'sales',
             'affected_module': 'inventory', 'severity': 'high'}
        d.is_duplicate(w)
        self.assertTrue(d.is_duplicate(w))

    def test_different_warning_not_duplicate(self):
        d = WarningDeduplicator()
        d.is_duplicate({'warning_type': 'drift', 'workflow_type': 'sales',
                        'affected_module': 'inventory', 'severity': 'high'})
        w2 = {'warning_type': 'instability', 'workflow_type': 'purchase',
              'affected_module': 'hr', 'severity': 'low'}
        self.assertFalse(d.is_duplicate(w2))

    def test_clear(self):
        d = WarningDeduplicator()
        w = {'warning_type': 'drift', 'workflow_type': 'sales',
             'affected_module': 'inventory', 'severity': 'high'}
        d.is_duplicate(w)
        d.clear()
        self.assertFalse(d.is_duplicate(w))


class TestEarlyWarningEngine(unittest.TestCase):
    def setUp(self):
        self.e = EarlyWarningEngine()

    def test_inventory_drift_risk(self):
        result = self.e.evaluate_inventory_drift_risk(
            1, {'mismatch_growth_rate': 30},
            {'predicted_drift_density': 20},
            {'inventory': 50})
        self.assertIsNotNone(result)

    def test_workflow_instability(self):
        result = self.e.evaluate_workflow_instability(
            1, 'sales', 60, 40, 'worsening')
        self.assertIsNotNone(result)

    def test_event_saturation(self):
        result = self.e.evaluate_event_propagation_saturation(
            1, 100, [5, 8], 200)
        self.assertIsNotNone(result)

    def test_causal_chain_overload(self):
        result = self.e.evaluate_causal_chain_overload(
            1, [3, 5, 7], [0.9, 0.7, 0.5])
        self.assertIsNotNone(result)

    def test_reconciliation_degradation(self):
        result = self.e.evaluate_reconciliation_degradation(
            1, 10, True, 'critical')
        self.assertIsNotNone(result)

    def test_deduplication_works(self):
        r1 = self.e.evaluate_inventory_drift_risk(
            1, {'mismatch_growth_rate': 30},
            {'predicted_drift_density': 20},
            {'inventory': 50})
        r2 = self.e.evaluate_inventory_drift_risk(
            1, {'mismatch_growth_rate': 30},
            {'predicted_drift_density': 20},
            {'inventory': 50})
        self.assertIsNotNone(r1)
        self.assertIsNone(r2)

    def test_retention_accessible(self):
        self.assertIsInstance(self.e.retention, WarningRetentionManager)

    def test_classifier_accessible(self):
        self.assertIsInstance(self.e.classifier, WarningSeverityClassifier)

    def test_generated_count(self):
        self.e.evaluate_inventory_drift_risk(
            1, {'mismatch_growth_rate': 30},
            {'predicted_drift_density': 20},
            {'inventory': 50})
        self.assertGreater(self.e.generated_count, 0)

    def test_clear(self):
        self.e.evaluate_inventory_drift_risk(
            1, {'mismatch_growth_rate': 30},
            {'predicted_drift_density': 20},
            {'inventory': 50})
        self.e.clear()
        self.assertEqual(self.e.generated_count, 0)


class TestPredictiveStabilityScore(unittest.TestCase):
    def test_perfect_score(self):
        s = PredictiveStabilityScore()
        drift = {'critical_escalation': False, 'worsening': False}
        velocity = {'drift_acceleration': 0}
        forecast = {'predicted_drift_density': 0}
        wf_scores = {'sales': 10, 'purchase': 10}
        w_counts = {'critical': 0, 'high': 0}
        fp = {'probability': 0}
        result = s.compute(drift, velocity, forecast, wf_scores, w_counts, fp)
        self.assertGreaterEqual(result['score'], 80)

    def test_reduced_score(self):
        s = PredictiveStabilityScore()
        drift = {'critical_escalation': True, 'worsening': True}
        velocity = {'drift_acceleration': 10}
        forecast = {'predicted_drift_density': 30}
        wf_scores = {'sales': 80, 'purchase': 70}
        w_counts = {'critical': 2, 'high': 3}
        fp = {'probability': 60}
        result = s.compute(drift, velocity, forecast, wf_scores, w_counts, fp)
        self.assertLess(result['score'], 80)

    def test_level_stable(self):
        s = PredictiveStabilityScore()
        result = s._classify(85)
        self.assertEqual(result, 'stable')

    def test_level_watch(self):
        s = PredictiveStabilityScore()
        result = s._classify(70)
        self.assertEqual(result, 'watch')

    def test_level_unstable(self):
        s = PredictiveStabilityScore()
        result = s._classify(50)
        self.assertEqual(result, 'unstable')

    def test_level_critical(self):
        s = PredictiveStabilityScore()
        result = s._classify(30)
        self.assertEqual(result, 'critical')

    def test_trend_history(self):
        s = PredictiveStabilityScore()
        drift = {'critical_escalation': False, 'worsening': False}
        velocity = {'drift_acceleration': 0}
        forecast = {'predicted_drift_density': 0}
        wf_scores = {'sales': 10, 'purchase': 10}
        w_counts = {'critical': 0, 'high': 0}
        fp = {'probability': 0}
        s.compute(drift, velocity, forecast, wf_scores, w_counts, fp)
        self.assertEqual(len(s.get_trend()), 1)

    def test_clear(self):
        s = PredictiveStabilityScore()
        drift = {'critical_escalation': False, 'worsening': False}
        velocity = {'drift_acceleration': 0}
        forecast = {'predicted_drift_density': 0}
        wf_scores = {'sales': 10, 'purchase': 10}
        w_counts = {'critical': 0, 'high': 0}
        fp = {'probability': 0}
        s.compute(drift, velocity, forecast, wf_scores, w_counts, fp)
        s.clear()
        self.assertEqual(s.record_count, 0)


class TestPredictiveTimeline(unittest.TestCase):
    def test_record_and_build(self):
        t = PredictiveTimeline()
        t.record(1, 'test', 'test event', 50, 'high')
        result = t.build_timeline(
            {'short_term': 10, 'medium_term': 25, 'long_term': 50},
            {'score': 80}, {})
        self.assertGreater(len(result['current_events']), 0)
        self.assertGreater(len(result['predicted_horizons']), 0)

    def test_predicted_horizons(self):
        t = PredictiveTimeline()
        result = t.build_timeline(
            {'short_term': 10, 'medium_term': 25, 'long_term': 50},
            {'score': 80}, {'sales': 70})
        horizons = result['predicted_horizons']
        self.assertGreater(len(horizons), 0)
        for h in horizons:
            self.assertIn('window', h)

    def test_clear(self):
        t = PredictiveTimeline()
        t.record(1, 'test', 'test', 50, 'high')
        t.clear()
        self.assertEqual(t.entry_count, 0)


class TestPredictiveHealthReportGenerator(unittest.TestCase):
    def setUp(self):
        self.g = PredictiveHealthReportGenerator()

    def test_generates_full_report(self):
        drift = {'trend_status': 'stable', 'critical_escalation': False,
                 'worsening': False, 'sample_size': 10,
                 'severity_escalation': False}
        velocity = {'drift_acceleration': 0.5, 'instability_momentum': 0.2,
                    'sample_size': 10}
        forecast = {'short_term': 15, 'medium_term': 30, 'long_term': 50,
                    'predicted_drift_density': 30, 'sample_size': 20}
        wf_scores = {'sales': 30, 'purchase': 20, 'inventory': 40,
                     'return': 10, 'hr': 5}
        degradations = {'sales': 20, 'purchase': 15, 'inventory': 25,
                        'return': 8, 'hr': 3}
        w_counts = {'info': 5, 'low': 3, 'medium': 2, 'high': 1, 'critical': 0}
        stability = {'score': 80, 'level': 'stable'}
        fp = {'probability': 15, 'level': 'normal'}
        high_risk = {'inventory': 40}
        timeline = {'predicted_horizons': [
            {'window': 'near_future', 'tick_offset': 5,
             'predicted_score': 70, 'predicted_risk_workflows': 1,
             'forecast_density': 15}]}
        report = self.g.generate(
            1, drift, velocity, forecast, wf_scores, degradations,
            w_counts, stability, fp, high_risk, timeline)
        self.assertIn('report_id', report)
        self.assertIn('summary', report)
        self.assertIn('top_predicted_risks', report)
        self.assertIn('workflow_instability_ranking', report)
        self.assertIn('escalation_indicators', report)
        self.assertIn('forecast', report)
        self.assertIn('operational_pressure', report)
        self.assertIn('confidence_summary', report)

    def test_escalation_indicators_detected(self):
        drift = {'trend_status': 'critical', 'critical_escalation': True,
                 'worsening': True, 'sample_size': 10,
                 'severity_escalation': True}
        stability = {'score': 35, 'level': 'critical'}
        w_counts = {'critical': 2, 'high': 3, 'medium': 1, 'low': 2, 'info': 0}
        indicators = self.g._detect_escalations(drift, stability, w_counts)
        self.assertGreater(len(indicators), 0)
        severities = [i['severity'] for i in indicators]
        self.assertIn('critical', severities)


class TestPredictiveMemoryGuard(unittest.TestCase):
    def test_healthy_when_within_bounds(self):
        g = PredictiveMemoryGuard()
        g.register('test', 5, 100)
        audit = g.audit_all()
        self.assertTrue(audit['all_healthy'])

    def test_violation_detected(self):
        g = PredictiveMemoryGuard()
        g.register('test', 150, 100)
        audit = g.audit_all()
        self.assertFalse(audit['all_healthy'])
        self.assertEqual(audit['violations_found'], 1)

    def test_utilization_report(self):
        g = PredictiveMemoryGuard()
        g.register('test', 50, 100)
        report = g.get_utilization_report()
        self.assertEqual(report['test'], 50.0)

    def test_clear(self):
        g = PredictiveMemoryGuard()
        g.register('test', 5, 100)
        g.clear()
        audit = g.audit_all()
        self.assertEqual(audit['total_components_checked'], 0)


class TestPredictivePerformanceMonitor(unittest.TestCase):
    def test_empty_report(self):
        m = PredictivePerformanceMonitor()
        report = m.get_latency_report()
        for cat in ('forecast', 'scoring', 'warning_generation',
                    'trend_analysis'):
            self.assertEqual(report[cat]['avg_ms'], 0.0)

    def test_record_latencies(self):
        m = PredictivePerformanceMonitor()
        m.record_forecast_latency(10.5)
        m.record_scoring_latency(5.2)
        m.record_warning_latency(3.1)
        m.record_trend_latency(8.7)
        report = m.get_latency_report()
        self.assertGreater(report['forecast']['avg_ms'], 0)
        self.assertGreater(report['scoring']['avg_ms'], 0)

    def test_measure_call(self):
        m = PredictivePerformanceMonitor()
        result = m.measure_call('forecast', lambda x: x * 2, 5)
        self.assertEqual(result, 10)
        report = m.get_latency_report()
        self.assertGreater(report['forecast']['samples'], 0)

    def test_clear(self):
        m = PredictivePerformanceMonitor()
        m.record_forecast_latency(10.5)
        m.clear()
        report = m.get_latency_report()
        self.assertEqual(report['forecast']['samples'], 0)


class TestPredictionFailureIsolation(unittest.TestCase):
    def test_safe_call_returns_result(self):
        iso = PredictionFailureIsolation()
        result = iso.safe_call(lambda x: x * 2, default_return=0, x=5)
        self.assertEqual(result, 10)

    def test_safe_call_returns_default_on_error(self):
        iso = PredictionFailureIsolation()
        def broken(**kw):
            raise ValueError("test error")
        result = iso.safe_call(broken, default_return=-1)
        self.assertEqual(result, -1)

    def test_failure_count_increments(self):
        iso = PredictionFailureIsolation()
        def broken(**kw):
            raise ValueError("test error")
        iso.safe_call(broken, default_return=-1)
        self.assertEqual(iso.failure_count, 1)

    def test_last_failure_stored(self):
        iso = PredictionFailureIsolation()
        def broken(**kw):
            raise ValueError("test error")
        iso.safe_call(broken, default_return=-1)
        self.assertIsNotNone(iso.last_failure)

    def test_degraded_mode(self):
        iso = PredictionFailureIsolation()
        self.assertFalse(iso.degraded_mode)
        iso.enter_degraded_mode()
        self.assertTrue(iso.degraded_mode)
        iso.exit_degraded_mode()
        self.assertFalse(iso.degraded_mode)

    def test_reset(self):
        iso = PredictionFailureIsolation()
        def broken(**kw):
            raise ValueError("test error")
        iso.safe_call(broken, default_return=-1)
        iso.enter_degraded_mode()
        iso.reset()
        self.assertEqual(iso.failure_count, 0)
        self.assertFalse(iso.degraded_mode)


class TestPredictiveEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PredictiveEngine()

    def test_analyze_tick_returns_data(self):
        result = self.engine.analyze_tick(
            1, 10, {'low': 10}, {'sales': 10}, {'sales': 1}, {}, [])
        self.assertIn('drift_trend', result)
        self.assertIn('velocity', result)
        self.assertIn('forecast', result)

    def test_analyze_workflows_returns_scores(self):
        result = self.engine.analyze_workflows(
            1, [], {}, [], [], {})
        self.assertIn('workflow_scores', result)
        for wf in ('sales', 'purchase', 'inventory', 'return', 'hr'):
            self.assertIn(wf, result['workflow_scores'])

    def test_evaluate_warnings_returns_list(self):
        drift = {'trend_status': 'stable', 'severity_escalation': False,
                 'sample_size': 5}
        forecast = {'short_term': 10, 'predicted_drift_density': 15}
        wf_scores = {'inventory': 50, 'sales': 30}
        warnings = self.engine.evaluate_warnings(1, drift, forecast, wf_scores, {})
        self.assertIsInstance(warnings, list)

    def test_generate_health_report_returns_report(self):
        for i in range(10):
            self.engine.analyze_tick(
                i, i * 2, {'low': i * 2}, {'sales': i}, {'sales': 1}, {}, [])
        self.engine.analyze_workflows(10, [], {}, [], [], {})
        report = self.engine.generate_health_report(10)
        self.assertIn('summary', report)
        self.assertIn('memory_audit', report)
        self.assertIn('performance', report)
        self.assertIn('failure_isolation', report)

    def test_health_report_includes_risk_ranking(self):
        for i in range(10):
            self.engine.analyze_tick(
                i, 5, {'low': 5}, {'sales': 5}, {'sales': 1}, {}, [])
        self.engine.analyze_workflows(10, [], {}, [], [], {})
        report = self.engine.generate_health_report(10)
        self.assertIn('workflow_instability_ranking', report)

    def test_trend_analyzer_accessible(self):
        self.assertIsInstance(self.engine.trend_analyzer, DriftTrendAnalyzer)

    def test_velocity_tracker_accessible(self):
        self.assertIsInstance(self.engine.velocity_tracker, DriftVelocityTracker)

    def test_forecast_window_accessible(self):
        self.assertIsInstance(self.engine.forecast_window, DriftForecastWindow)

    def test_workflow_scorer_accessible(self):
        self.assertIsInstance(self.engine.workflow_scorer, WorkflowRiskScorer)

    def test_probability_engine_accessible(self):
        self.assertIsInstance(self.engine.probability_engine,
                              FailureProbabilityEngine)

    def test_warning_engine_accessible(self):
        self.assertIsInstance(self.engine.warning_engine, EarlyWarningEngine)

    def test_memory_guard_accessible(self):
        self.assertIsInstance(self.engine.memory_guard, PredictiveMemoryGuard)

    def test_perf_monitor_accessible(self):
        self.assertIsInstance(self.engine.perf_monitor,
                              PredictivePerformanceMonitor)

    def test_failure_isolation_accessible(self):
        self.assertIsInstance(self.engine.failure_isolation,
                              PredictionFailureIsolation)

    def test_reset_clears_everything(self):
        self.engine.analyze_tick(
            1, 10, {'low': 10}, {'sales': 10}, {'sales': 1}, {}, [])
        self.engine.reset()
        self.assertEqual(self.engine.current_tick, 0)

    def test_root_cause_bridge_accessible(self):
        from simulation.predictive.integration.root_cause_bridge import (
            RootCausePredictiveBridge,
        )
        self.assertIsInstance(self.engine.root_cause_bridge,
                              RootCausePredictiveBridge)

    def test_stability_score_accessible(self):
        self.assertIsInstance(self.engine.stability_score,
                              PredictiveStabilityScore)

    def test_timeline_accessible(self):
        self.assertIsInstance(self.engine.timeline, PredictiveTimeline)

    def test_report_generator_accessible(self):
        self.assertIsInstance(self.engine.report_generator,
                              PredictiveHealthReportGenerator)

    def test_analyze_tick_increments_tick(self):
        self.engine.analyze_tick(
            5, 10, {'low': 10}, {'sales': 10}, {'sales': 1}, {}, [])
        self.assertEqual(self.engine.current_tick, 5)


class TestNoERPMutation(unittest.TestCase):
    def test_no_domain_imports_in_predictive(self):
        import simulation.predictive
        import os
        base = os.path.dirname(simulation.predictive.__file__)
        forbidden = ['accounting', 'sales', 'purchases', 'inventory',
                     'payments', 'payroll', 'hr', 'backup']
        for root, dirs, files in os.walk(base):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, encoding='utf-8') as f:
                    content = f.read()
                for prod in forbidden:
                    if f'import {prod}' in content or f'from {prod}' in content:
                        self.fail(
                            f"{fname} imports production module '{prod}'")

    def test_no_erp_writes_in_predictive(self):
        import simulation.predictive
        import os
        base = os.path.dirname(simulation.predictive.__file__)
        write_patterns = [
            '.save()', '.create()', '.update()', '.delete()',
            'JournalEngine', 'PaymentEngine', 'StockMovement',
            'transaction.atomic',
        ]
        for root, dirs, files in os.walk(base):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, encoding='utf-8') as f:
                    content = f.read()
                for pattern in write_patterns:
                    if pattern in content:
                        self.fail(
                            f"{fname} contains write pattern '{pattern}'")


class TestRootCauseBridge(unittest.TestCase):
    def test_bridge_empty_when_no_engine(self):
        from simulation.predictive.integration.root_cause_bridge import (
            RootCausePredictiveBridge,
        )
        bridge = RootCausePredictiveBridge()
        self.assertEqual(bridge.get_recurring_patterns(), [])
        self.assertEqual(bridge.get_recurring_root_causes(), {})
        stats = bridge.get_causal_chain_statistics()
        self.assertEqual(stats['total_chains'], 0)

    def test_bridge_bind(self):
        from simulation.predictive.integration.root_cause_bridge import (
            RootCausePredictiveBridge,
        )
        from simulation.truth_engine.root_cause.engine import RootCauseEngine
        bridge = RootCausePredictiveBridge()
        engine = RootCauseEngine()
        bridge.bind(engine)
        self.assertIsNotNone(bridge.engine)

    def test_bridge_no_mutation(self):
        from simulation.predictive.integration.root_cause_bridge import (
            RootCausePredictiveBridge,
        )
        from simulation.truth_engine.root_cause.engine import RootCauseEngine
        engine = RootCauseEngine()
        bridge = RootCausePredictiveBridge(engine)
        patterns = bridge.get_recurring_patterns()
        causes = bridge.get_recurring_root_causes()
        deps = bridge.get_dependency_chain_analysis()
        self.assertIsInstance(patterns, list)
        self.assertIsInstance(causes, dict)
        self.assertIsInstance(deps, dict)

    def test_bridge_get_dependency_analysis(self):
        from simulation.predictive.integration.root_cause_bridge import (
            RootCausePredictiveBridge,
        )
        from simulation.truth_engine.root_cause.engine import RootCauseEngine
        engine = RootCauseEngine()
        bridge = RootCausePredictiveBridge(engine)
        deps = bridge.get_dependency_chain_analysis()
        self.assertIn('workflow_dependencies', deps)
        self.assertIn('agent_dependencies', deps)


class TestDetermineisticExecution(unittest.TestCase):
    def test_repeatable_trend_analysis(self):
        a1 = DriftTrendAnalyzer()
        a2 = DriftTrendAnalyzer()
        for i in range(10):
            a1.record_snapshot(i, i, {'low': i}, {'mod': i})
            a2.record_snapshot(i, i, {'low': i}, {'mod': i})
        self.assertEqual(a1.analyze_trends(), a2.analyze_trends())

    def test_repeatable_velocity(self):
        v1 = DriftVelocityTracker()
        v2 = DriftVelocityTracker()
        for i in range(10):
            v1.record_tick(i, i * 2)
            v2.record_tick(i, i * 2)
        self.assertEqual(v1.compute_velocity(), v2.compute_velocity())

    def test_repeatable_forecast(self):
        f1 = DriftForecastWindow()
        f2 = DriftForecastWindow()
        for i in range(20):
            f1.record(i, i, {'low': i}, {'mod': i})
            f2.record(i, i, {'low': i}, {'mod': i})
        self.assertEqual(f1.forecast(), f2.forecast())

    def test_repeatable_risk_score(self):
        s1 = WorkflowRiskScorer()
        s2 = WorkflowRiskScorer()
        drift = [{'mismatch': {'affected_module': 'sales'}}
                 for _ in range(5)]
        self.assertEqual(
            s1.score_workflow('sales', drift, {'sales': 2}),
            s2.score_workflow('sales', drift, {'sales': 2}))

    def test_repeatable_stability_score(self):
        s1 = PredictiveStabilityScore()
        s2 = PredictiveStabilityScore()
        drift = {'critical_escalation': False, 'worsening': False}
        velocity = {'drift_acceleration': 0}
        forecast = {'predicted_drift_density': 0}
        wf_scores = {'sales': 10, 'purchase': 10}
        w_counts = {'critical': 0, 'high': 0}
        fp = {'probability': 0}
        self.assertEqual(
            s1.compute(drift, velocity, forecast, wf_scores, w_counts, fp),
            s2.compute(drift, velocity, forecast, wf_scores, w_counts, fp))


if __name__ == '__main__':
    unittest.main()

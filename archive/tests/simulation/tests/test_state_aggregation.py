"""Phase 4C: deterministic tests for Control Center state aggregation."""
import unittest

from simulation.control_center.models import (
    AggregatedState, OperationalState, IntelligenceSeverity,
    OperationalPriority, SignalType,
)
from simulation.control_center.state.operational_state_aggregator import (
    OperationalStateAggregator,
)
from simulation.control_center.state.system_health_matrix import SystemHealthMatrix
from simulation.control_center.state.intelligence_state_classifier import (
    IntelligenceStateClassifier,
)
from simulation.control_center.state.operational_priority_engine import (
    OperationalPriorityEngine,
)


class TestOperationalStateAggregator(unittest.TestCase):
    """OperationalStateAggregator: ingest, aggregate, clear."""

    def setUp(self):
        self.agg = OperationalStateAggregator(max_signals=1000)

    def _ingest(self, signal_id, severity, signal_type=SignalType.TRUTH_MISMATCH,
                source='phase1', tick=1, desc='test'):
        return self.agg.ingest_signal(
            signal_id=signal_id, signal_type=signal_type,
            severity=severity, source_phase=source,
            tick=tick, description=desc,
        )

    def test_empty_state_returns_normal_and_zero_score(self):
        state = self.agg.aggregate_state()
        self.assertIsInstance(state, AggregatedState)
        self.assertEqual(state.state, OperationalState.NORMAL)
        self.assertEqual(state.severity_score, 0.0)
        self.assertEqual(state.active_signals, 0)
        self.assertEqual(state.critical_count, 0)
        self.assertEqual(state.incident_count, 0)

    def test_empty_signal_count(self):
        self.assertEqual(self.agg.get_signal_count(), 0)

    def test_ingest_returns_metadata(self):
        result = self._ingest('s1', IntelligenceSeverity.HIGH)
        self.assertEqual(result['signal_id'], 's1')
        self.assertEqual(result['tick'], 1)
        self.assertEqual(result['severity'], 'high')

    def test_signal_count_increases(self):
        self._ingest('s1', IntelligenceSeverity.INFO)
        self._ingest('s2', IntelligenceSeverity.LOW)
        self.assertEqual(self.agg.get_signal_count(), 2)

    def test_multiple_severities_aggregate_counts(self):
        self._ingest('s1', IntelligenceSeverity.CRITICAL, SignalType.INCIDENT)
        self._ingest('s2', IntelligenceSeverity.CRITICAL, SignalType.INCIDENT)
        self._ingest('s3', IntelligenceSeverity.HIGH)
        self._ingest('s4', IntelligenceSeverity.MEDIUM)
        state = self.agg.aggregate_state()
        self.assertEqual(state.active_signals, 4)
        self.assertEqual(state.critical_count, 2)
        self.assertEqual(state.incident_count, 2)

    def test_critical_count_over_five_triggers_emergency(self):
        for i in range(6):
            self._ingest(f'c{i}', IntelligenceSeverity.CRITICAL)
        state = self.agg.aggregate_state()
        self.assertEqual(state.state, OperationalState.EMERGENCY)
        self.assertEqual(state.critical_count, 6)

    def test_score_at_or_above_0_7_triggers_critical(self):
        self._ingest('s1', IntelligenceSeverity.CRITICAL)
        self._ingest('s2', IntelligenceSeverity.CRITICAL)
        self._ingest('s3', IntelligenceSeverity.CRITICAL)
        state = self.agg.aggregate_state()
        self.assertGreaterEqual(state.severity_score, 0.7)
        self.assertEqual(state.state, OperationalState.CRITICAL)

    def test_score_at_or_above_0_4_triggers_degraded(self):
        self._ingest('s1', IntelligenceSeverity.MEDIUM)
        self._ingest('s2', IntelligenceSeverity.MEDIUM)
        state = self.agg.aggregate_state()
        self.assertGreaterEqual(state.severity_score, 0.4)
        self.assertEqual(state.state, OperationalState.DEGRADED)

    def test_weighted_score_with_all_severities(self):
        self._ingest('c1', IntelligenceSeverity.CRITICAL)
        self._ingest('h1', IntelligenceSeverity.HIGH)
        self._ingest('m1', IntelligenceSeverity.MEDIUM)
        self._ingest('l1', IntelligenceSeverity.LOW)
        self._ingest('i1', IntelligenceSeverity.INFO)
        state = self.agg.aggregate_state()
        expected = min(1.0, (1.0 + 0.7 + 0.4 + 0.2 + 0.0) / 5)
        self.assertAlmostEqual(state.severity_score, expected)

    def test_score_capped_at_1_0(self):
        for i in range(10):
            self._ingest(f'c{i}', IntelligenceSeverity.CRITICAL)
        state = self.agg.aggregate_state()
        self.assertAlmostEqual(state.severity_score, 1.0)

    def test_source_summaries_populated(self):
        self._ingest('s1', IntelligenceSeverity.HIGH, source='phase_a')
        self._ingest('s2', IntelligenceSeverity.LOW, source='phase_b')
        self._ingest('s3', IntelligenceSeverity.LOW, source='phase_a')
        state = self.agg.aggregate_state()
        self.assertIn('phase_a', state.source_summaries)
        self.assertIn('phase_b', state.source_summaries)
        self.assertEqual(state.source_summaries['phase_a'], 2)
        self.assertEqual(state.source_summaries['phase_b'], 1)

    def test_priority_computed_in_aggregated_state(self):
        self._ingest('s1', IntelligenceSeverity.CRITICAL)
        state = self.agg.aggregate_state()
        self.assertIsInstance(state.priority, OperationalPriority)

    def test_clear_resets(self):
        self._ingest('s1', IntelligenceSeverity.HIGH)
        self.agg.clear()
        self.assertEqual(self.agg.get_signal_count(), 0)
        state = self.agg.aggregate_state()
        self.assertEqual(state.state, OperationalState.NORMAL)
        self.assertEqual(state.severity_score, 0.0)

    def test_priority_critical_when_count_exceeds_five(self):
        for i in range(6):
            self._ingest(f'c{i}', IntelligenceSeverity.CRITICAL)
        state = self.agg.aggregate_state()
        self.assertEqual(state.priority, OperationalPriority.CRITICAL)

    def test_priority_high_when_score_above_0_7(self):
        self._ingest('s1', IntelligenceSeverity.CRITICAL)
        self._ingest('s2', IntelligenceSeverity.CRITICAL)
        state = self.agg.aggregate_state()
        self.assertEqual(state.priority, OperationalPriority.HIGH)

    def test_priority_medium_when_score_above_0_4(self):
        self._ingest('s1', IntelligenceSeverity.MEDIUM)
        self._ingest('s2', IntelligenceSeverity.MEDIUM)
        state = self.agg.aggregate_state()
        self.assertEqual(state.priority, OperationalPriority.MEDIUM)

    def test_priority_lowest_with_no_signals(self):
        state = self.agg.aggregate_state()
        self.assertEqual(state.priority, OperationalPriority.LOWEST)


class TestSystemHealthMatrix(unittest.TestCase):
    """SystemHealthMatrix: compute_health, trend detection."""

    def setUp(self):
        self.matrix = SystemHealthMatrix(max_history=500)

    def test_healthy_when_score_zero(self):
        result = self.matrix.compute_health(
            severity_score=0.0, critical_count=0,
            incident_count=0, active_signals=0,
        )
        self.assertEqual(result['status'], 'healthy')
        self.assertEqual(result['health_score'], 1.0)

    def test_critical_when_score_above_0_7(self):
        result = self.matrix.compute_health(
            severity_score=0.7, critical_count=0,
            incident_count=0, active_signals=5,
        )
        self.assertEqual(result['status'], 'critical')
        self.assertAlmostEqual(result['health_score'], 0.3)

    def test_critical_when_critical_count_above_five(self):
        result = self.matrix.compute_health(
            severity_score=0.0, critical_count=6,
            incident_count=0, active_signals=6,
        )
        self.assertEqual(result['status'], 'critical')

    def test_degraded_when_score_above_0_4(self):
        result = self.matrix.compute_health(
            severity_score=0.4, critical_count=0,
            incident_count=0, active_signals=3,
        )
        self.assertEqual(result['status'], 'degraded')
        self.assertAlmostEqual(result['health_score'], 0.6)

    def test_degraded_when_critical_count_above_two(self):
        result = self.matrix.compute_health(
            severity_score=0.0, critical_count=3,
            incident_count=0, active_signals=3,
        )
        self.assertEqual(result['status'], 'degraded')

    def test_warning_when_critical_count_positive(self):
        result = self.matrix.compute_health(
            severity_score=0.0, critical_count=1,
            incident_count=0, active_signals=1,
        )
        self.assertEqual(result['status'], 'warning')

    def test_warning_when_incident_count_positive(self):
        result = self.matrix.compute_health(
            severity_score=0.0, critical_count=0,
            incident_count=1, active_signals=1,
        )
        self.assertEqual(result['status'], 'warning')

    def test_health_score_one_minus_severity(self):
        result = self.matrix.compute_health(
            severity_score=0.3, critical_count=0,
            incident_count=0, active_signals=0,
        )
        self.assertAlmostEqual(result['health_score'], 0.7)

    def test_trend_stable_when_less_than_two_entries(self):
        self.matrix.compute_health(0.0, 0, 0, 0)
        self.assertEqual(self.matrix.get_health_trend(), 'stable')

    def test_trend_stable_after_two_calls_no_change(self):
        self.matrix.compute_health(0.5, 0, 0, 0)
        self.matrix.compute_health(0.5, 0, 0, 0)
        self.assertEqual(self.matrix.get_health_trend(), 'stable')

    def test_trend_degrading_when_score_drops(self):
        self.matrix.compute_health(0.0, 0, 0, 0)
        self.matrix.compute_health(0.5, 0, 0, 0)
        self.matrix.compute_health(0.8, 0, 0, 0)
        self.assertEqual(self.matrix.get_health_trend(), 'degrading')

    def test_trend_improving_when_score_rises(self):
        self.matrix.compute_health(0.8, 0, 0, 0)
        self.matrix.compute_health(0.5, 0, 0, 0)
        self.matrix.compute_health(0.0, 0, 0, 0)
        self.assertEqual(self.matrix.get_health_trend(), 'improving')

    def test_output_fields(self):
        result = self.matrix.compute_health(
            severity_score=0.2, critical_count=1,
            incident_count=2, active_signals=10,
            source_summaries={'a': 5, 'b': 5},
        )
        self.assertIn('status', result)
        self.assertIn('health_score', result)
        self.assertIn('active_signals', result)
        self.assertIn('critical_signals', result)
        self.assertIn('active_incidents', result)
        self.assertIn('sources_monitored', result)
        self.assertEqual(result['active_signals'], 10)
        self.assertEqual(result['critical_signals'], 1)
        self.assertEqual(result['active_incidents'], 2)
        self.assertEqual(result['sources_monitored'], 2)

    def test_clear_resets_history(self):
        self.matrix.compute_health(0.8, 0, 0, 0)
        self.matrix.clear()
        self.assertEqual(self.matrix.get_health_trend(), 'stable')


class TestIntelligenceStateClassifier(unittest.TestCase):
    """IntelligenceStateClassifier: classify, severity, cascading risk."""

    def setUp(self):
        self.classifier = IntelligenceStateClassifier(max_history=200)

    def test_normal_classification(self):
        result = self.classifier.classify(
            severity_score=0.0, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['operational_state'], 'normal')
        self.assertEqual(result['severity'], 'info')
        self.assertEqual(result['priority'], '0')
        self.assertFalse(result['cascading_risk'])
        self.assertEqual(result['classification'], 'normal_info')

    def test_cascading_risk_detected(self):
        result = self.classifier.classify(
            severity_score=0.5, critical_count=4,
            incident_count=3, active_signals=25, source_count=3,
        )
        self.assertTrue(result['cascading_risk'])

    def test_cascading_not_detected_when_signals_too_low(self):
        result = self.classifier.classify(
            severity_score=0.5, critical_count=4,
            incident_count=3, active_signals=10, source_count=3,
        )
        self.assertFalse(result['cascading_risk'])

    def test_severity_critical_at_0_8(self):
        result = self.classifier.classify(
            severity_score=0.8, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['severity'], 'critical')

    def test_severity_high_at_0_5(self):
        result = self.classifier.classify(
            severity_score=0.5, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['severity'], 'high')

    def test_severity_medium_at_0_3(self):
        result = self.classifier.classify(
            severity_score=0.3, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['severity'], 'medium')

    def test_severity_low_above_zero(self):
        result = self.classifier.classify(
            severity_score=0.1, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['severity'], 'low')

    def test_emergency_state_when_critical_count_exceeds_five(self):
        result = self.classifier.classify(
            severity_score=0.0, critical_count=6,
            incident_count=0, active_signals=6, source_count=1,
        )
        self.assertEqual(result['operational_state'], 'emergency')

    def test_critical_state_at_0_7(self):
        result = self.classifier.classify(
            severity_score=0.7, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['operational_state'], 'critical')

    def test_degraded_with_critical_count_positive(self):
        result = self.classifier.classify(
            severity_score=0.0, critical_count=1,
            incident_count=0, active_signals=1, source_count=1,
        )
        self.assertEqual(result['operational_state'], 'degraded')

    def test_classification_format(self):
        result = self.classifier.classify(
            severity_score=0.7, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['classification'], 'critical_high')

    def test_priority_critical_when_count_exceeds_five(self):
        result = self.classifier.classify(
            severity_score=0.0, critical_count=6,
            incident_count=0, active_signals=6, source_count=1,
        )
        self.assertEqual(result['priority'], '4')

    def test_priority_lowest_for_normal(self):
        result = self.classifier.classify(
            severity_score=0.0, critical_count=0,
            incident_count=0, active_signals=0, source_count=0,
        )
        self.assertEqual(result['priority'], '0')


class TestOperationalPriorityEngine(unittest.TestCase):
    """OperationalPriorityEngine: compute_priority, identify, prioritize."""

    def setUp(self):
        self.engine = OperationalPriorityEngine(max_history=200)

    def test_cascading_risk_yields_critical_priority(self):
        result = self.engine.compute_priority(
            severity_score=0.0, critical_count=0,
            incident_count=0, source_count=0, cascading_risk=True,
        )
        self.assertEqual(result['priority'], '4')
        self.assertEqual(result['label'], 'CRITICAL')

    def test_critical_count_over_five_yields_critical_priority(self):
        result = self.engine.compute_priority(
            severity_score=0.0, critical_count=6,
            incident_count=0, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '4')
        self.assertEqual(result['label'], 'CRITICAL')

    def test_score_above_0_7_yields_high_priority(self):
        result = self.engine.compute_priority(
            severity_score=0.7, critical_count=0,
            incident_count=0, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '3')
        self.assertEqual(result['label'], 'HIGH')

    def test_critical_count_above_two_yields_high(self):
        result = self.engine.compute_priority(
            severity_score=0.0, critical_count=3,
            incident_count=0, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '3')
        self.assertEqual(result['label'], 'HIGH')

    def test_score_above_0_4_yields_medium_priority(self):
        result = self.engine.compute_priority(
            severity_score=0.4, critical_count=0,
            incident_count=0, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '2')
        self.assertEqual(result['label'], 'MEDIUM')

    def test_incident_count_above_three_yields_medium(self):
        result = self.engine.compute_priority(
            severity_score=0.0, critical_count=0,
            incident_count=4, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '2')
        self.assertEqual(result['label'], 'MEDIUM')

    def test_positive_score_yields_low_priority(self):
        result = self.engine.compute_priority(
            severity_score=0.1, critical_count=0,
            incident_count=0, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '1')
        self.assertEqual(result['label'], 'LOW')

    def test_positive_incident_yields_low_priority(self):
        result = self.engine.compute_priority(
            severity_score=0.0, critical_count=0,
            incident_count=1, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '1')
        self.assertEqual(result['label'], 'LOW')

    def test_all_zeros_yields_lowest_priority(self):
        result = self.engine.compute_priority(
            severity_score=0.0, critical_count=0,
            incident_count=0, source_count=0, cascading_risk=False,
        )
        self.assertEqual(result['priority'], '0')
        self.assertEqual(result['label'], 'LOWEST')

    def test_identify_critical_incidents_filters(self):
        signals = [
            {'severity': 'critical', 'signal_type': 'incident'},
            {'severity': 'high', 'signal_type': 'truth_mismatch'},
            {'severity': 'medium', 'signal_type': 'drift_trend'},
            {'severity': 'info', 'signal_type': 'info'},
        ]
        result = self.engine.identify_critical_incidents(signals)
        self.assertEqual(len(result), 2)
        self.assertIn(signals[0], result)
        self.assertIn(signals[1], result)

    def test_identify_critical_incidents_excludes_info_type(self):
        signals = [
            {'severity': 'high', 'signal_type': 'info'},
        ]
        result = self.engine.identify_critical_incidents(signals)
        self.assertEqual(len(result), 0)

    def test_prioritize_risks_sorts_by_severity(self):
        risks = [
            {'name': 'low_risk', 'severity': 'low'},
            {'name': 'critical_risk', 'severity': 'critical'},
            {'name': 'medium_risk', 'severity': 'medium'},
            {'name': 'high_risk', 'severity': 'high'},
        ]
        result = self.engine.prioritize_risks(risks)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]['severity'], 'critical')
        self.assertEqual(result[1]['severity'], 'high')
        self.assertEqual(result[2]['severity'], 'medium')
        self.assertEqual(result[3]['severity'], 'low')

    def test_prioritize_risks_handles_unknown_severity(self):
        risks = [
            {'name': 'unknown', 'severity': 'unknown'},
            {'name': 'critical', 'severity': 'critical'},
        ]
        result = self.engine.prioritize_risks(risks)
        self.assertEqual(result[0]['severity'], 'critical')
        self.assertEqual(result[1]['severity'], 'unknown')

    def test_prioritize_risks_preserves_related_high_count(self):
        risks = [
            {'severity': 'high'}, {'severity': 'high'},
            {'severity': 'medium'}, {'severity': 'low'},
        ]
        result = self.engine.prioritize_risks(risks)
        self.assertEqual(result[0]['severity'], 'high')
        self.assertEqual(result[1]['severity'], 'high')
        self.assertEqual(result[2]['severity'], 'medium')
        self.assertEqual(result[3]['severity'], 'low')

    def test_clear_resets_history(self):
        self.engine.compute_priority(0.5, 0, 0, 0, False)
        self.engine.clear()
        self.engine.compute_priority(0.0, 0, 0, 0, False)
        result = self.engine.compute_priority(0.0, 0, 0, 0, False)
        self.assertEqual(result['label'], 'LOWEST')

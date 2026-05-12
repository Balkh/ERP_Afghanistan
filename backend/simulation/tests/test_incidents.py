"""
Tests for Phase 4C Control Center — Incidents Subpackage.
Fully deterministic. No randomness. No ERP mutation.
"""
import unittest

from simulation.control_center.models import (
    OperationalSignal,
    IncidentRecord,
    IncidentStatus,
    IntelligenceSeverity,
    SignalType,
    EscalationLevel,
    OperationalPriority,
)
from simulation.control_center.incidents.incident_registry import IncidentRegistry
from simulation.control_center.incidents.incident_classifier import IncidentClassifier
from simulation.control_center.incidents.incident_lifecycle import IncidentLifecycle
from simulation.control_center.incidents.escalation_engine import EscalationEngine


def _make_incident(incident_id, severity, tick_detected):
    return IncidentRecord(
        incident_id=incident_id,
        signal_type=SignalType.TRUTH_MISMATCH,
        severity=severity,
        status=IncidentStatus.OPEN,
        tick_detected=tick_detected,
        description='test incident',
        occurrence_count=1,
    )


class TestIncidentRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = IncidentRegistry(max_incidents=10)

    def test_register_and_retrieve(self):
        record = self.registry.register_incident(
            incident_id='inc-001',
            signal_type=SignalType.TRUTH_MISMATCH,
            severity=IntelligenceSeverity.HIGH,
            tick=100,
            description='test incident',
            details={'key': 'value'},
        )
        self.assertIsNotNone(record)
        self.assertEqual(record.incident_id, 'inc-001')
        self.assertEqual(record.status, IncidentStatus.OPEN)
        self.assertEqual(record.occurrence_count, 1)
        self.assertEqual(record.details, {'key': 'value'})

        retrieved = self.registry.get_incident('inc-001')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.incident_id, 'inc-001')

    def test_update_status(self):
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.HIGH, 100, 'test'
        )
        result = self.registry.update_status(
            'inc-001', IncidentStatus.ACKNOWLEDGED
        )
        self.assertTrue(result)
        record = self.registry.get_incident('inc-001')
        self.assertIsNotNone(record)
        self.assertEqual(record.status, IncidentStatus.ACKNOWLEDGED)

    def test_update_status_resolved_sets_resolved_tick(self):
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.HIGH, 100, 'test'
        )
        self.registry.update_status('inc-001', IncidentStatus.RESOLVED, resolved_tick=150)
        record = self.registry.get_incident('inc-001')
        self.assertIsNotNone(record)
        self.assertEqual(record.status, IncidentStatus.RESOLVED)
        self.assertEqual(record.resolved_tick, 150)

    def test_update_status_nonexistent_returns_false(self):
        result = self.registry.update_status('nonexistent', IncidentStatus.RESOLVED)
        self.assertFalse(result)

    def test_get_incidents_filters_by_status(self):
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.HIGH, 100, 'test'
        )
        self.registry.register_incident(
            'inc-002', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.LOW, 101, 'test'
        )
        self.registry.update_status('inc-002', IncidentStatus.RESOLVED)

        open_incidents = self.registry.get_incidents(status=IncidentStatus.OPEN)
        resolved_incidents = self.registry.get_incidents(status=IncidentStatus.RESOLVED)

        self.assertEqual(len(open_incidents), 1)
        self.assertEqual(open_incidents[0].incident_id, 'inc-001')
        self.assertEqual(len(resolved_incidents), 1)
        self.assertEqual(resolved_incidents[0].incident_id, 'inc-002')

    def test_get_incidents_filters_by_severity(self):
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.CRITICAL, 100, 'test'
        )
        self.registry.register_incident(
            'inc-002', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 101, 'test'
        )
        critical = self.registry.get_incidents(severity=IntelligenceSeverity.CRITICAL)
        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0].incident_id, 'inc-001')

    def test_get_incidents_filters_by_signal_type(self):
        self.registry.register_incident(
            'inc-001', SignalType.ANOMALY,
            IntelligenceSeverity.HIGH, 100, 'test'
        )
        self.registry.register_incident(
            'inc-002', SignalType.DRIFT_TREND,
            IntelligenceSeverity.HIGH, 101, 'test'
        )
        anomalies = self.registry.get_incidents(signal_type=SignalType.ANOMALY)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0].incident_id, 'inc-001')

    def test_active_incidents_excludes_resolved_and_closed(self):
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.HIGH, 100, 'active'
        )
        self.registry.register_incident(
            'inc-002', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.LOW, 101, 'resolved'
        )
        self.registry.register_incident(
            'inc-003', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 102, 'closed'
        )
        self.registry.update_status('inc-002', IncidentStatus.RESOLVED)
        self.registry.update_status('inc-003', IncidentStatus.CLOSED)

        active = self.registry.get_active_incidents()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].incident_id, 'inc-001')

    def test_increment_occurrence(self):
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.HIGH, 100, 'test'
        )
        result = self.registry.increment_occurrence('inc-001')
        self.assertTrue(result)
        record = self.registry.get_incident('inc-001')
        self.assertIsNotNone(record)
        self.assertEqual(record.occurrence_count, 2)

    def test_increment_occurrence_nonexistent_returns_false(self):
        result = self.registry.increment_occurrence('nonexistent')
        self.assertFalse(result)

    def test_bounded_evicts_oldest(self):
        registry = IncidentRegistry(max_incidents=3)
        for i in range(4):
            registry.register_incident(
                f'inc-{i:03d}', SignalType.TRUTH_MISMATCH,
                IntelligenceSeverity.INFO, 100 + i, 'test'
            )
        self.assertEqual(registry.get_incident_count(), 3)
        self.assertIsNone(registry.get_incident('inc-000'))

    def test_get_incident_count(self):
        self.assertEqual(self.registry.get_incident_count(), 0)
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 100, 'test'
        )
        self.assertEqual(self.registry.get_incident_count(), 1)

    def test_clear(self):
        self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 100, 'test'
        )
        self.registry.clear()
        self.assertEqual(self.registry.get_incident_count(), 0)
        self.assertIsNone(self.registry.get_incident('inc-001'))

    def test_get_incidents_respects_limit(self):
        for i in range(10):
            self.registry.register_incident(
                f'inc-{i:03d}', SignalType.TRUTH_MISMATCH,
                IntelligenceSeverity.INFO, 100 + i, 'test'
            )
        result = self.registry.get_incidents(limit=3)
        self.assertEqual(len(result), 3)

    def test_get_incident_nonexistent(self):
        self.assertIsNone(self.registry.get_incident('nonexistent'))

    def test_register_without_details(self):
        record = self.registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 100, 'no details'
        )
        self.assertEqual(record.details, {})

    def test_increment_occurrence_on_evicted_returns_false(self):
        registry = IncidentRegistry(max_incidents=2)
        registry.register_incident(
            'inc-001', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 100, 'first'
        )
        registry.register_incident(
            'inc-002', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 101, 'second'
        )
        registry.register_incident(
            'inc-003', SignalType.TRUTH_MISMATCH,
            IntelligenceSeverity.INFO, 102, 'third'
        )
        result = registry.increment_occurrence('inc-001')
        self.assertFalse(result)


class TestIncidentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IncidentClassifier()

    def _make_signal(self, severity):
        return OperationalSignal(
            signal_id='sig-001',
            signal_type=SignalType.TRUTH_MISMATCH,
            severity=severity,
            source_phase='truth_engine',
            tick=100,
            description='test signal',
        )

    def test_critical_signal_requires_escalation(self):
        signal = self._make_signal(IntelligenceSeverity.CRITICAL)
        result = self.classifier.classify_signal(signal)
        self.assertEqual(result['severity'], IntelligenceSeverity.CRITICAL)
        self.assertEqual(result['priority'], OperationalPriority.CRITICAL)
        self.assertTrue(result['requires_escalation'])

    def test_high_signal_requires_escalation(self):
        signal = self._make_signal(IntelligenceSeverity.HIGH)
        result = self.classifier.classify_signal(signal)
        self.assertTrue(result['requires_escalation'])

    def test_info_signal_no_escalation(self):
        signal = self._make_signal(IntelligenceSeverity.INFO)
        result = self.classifier.classify_signal(signal)
        self.assertEqual(result['priority'], OperationalPriority.LOWEST)
        self.assertFalse(result['requires_escalation'])

    def test_medium_signal_no_escalation(self):
        signal = self._make_signal(IntelligenceSeverity.MEDIUM)
        result = self.classifier.classify_signal(signal)
        self.assertEqual(result['priority'], OperationalPriority.MEDIUM)
        self.assertFalse(result['requires_escalation'])

    def test_low_signal_no_escalation(self):
        signal = self._make_signal(IntelligenceSeverity.LOW)
        result = self.classifier.classify_signal(signal)
        self.assertEqual(result['priority'], OperationalPriority.LOW)
        self.assertFalse(result['requires_escalation'])

    def test_classify_incident_stale_detection(self):
        record = _make_incident('inc-001', IntelligenceSeverity.HIGH, 1)
        record.occurrence_count = 50
        result = self.classifier.classify_incident(record)
        self.assertTrue(result['is_stale'])

    def test_classify_incident_not_stale(self):
        record = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        record.occurrence_count = 5
        result = self.classifier.classify_incident(record)
        self.assertFalse(result['is_stale'])

    def test_classify_incident_resolved_not_stale(self):
        record = _make_incident('inc-001', IntelligenceSeverity.HIGH, 1)
        record.status = IncidentStatus.RESOLVED
        record.occurrence_count = 50
        result = self.classifier.classify_incident(record)
        self.assertFalse(result['is_stale'])

    def test_classify_incident_recommended_action_critical(self):
        record = _make_incident('inc-001', IntelligenceSeverity.CRITICAL, 100)
        result = self.classifier.classify_incident(record)
        self.assertEqual(result['severity_label'], 'critical')
        self.assertIn('immediate investigation', result['recommended_action'])

    def test_classify_incident_recommended_action_low(self):
        record = _make_incident('inc-001', IntelligenceSeverity.LOW, 100)
        result = self.classifier.classify_incident(record)
        self.assertIn('monitor and close', result['recommended_action'])

    def test_batch_classify(self):
        signals = [
            self._make_signal(IntelligenceSeverity.CRITICAL),
            self._make_signal(IntelligenceSeverity.INFO),
            self._make_signal(IntelligenceSeverity.HIGH),
        ]
        results = self.classifier.batch_classify(signals)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]['requires_escalation'])
        self.assertFalse(results[1]['requires_escalation'])
        self.assertTrue(results[2]['requires_escalation'])

    def test_classify_signal_incident_type_format(self):
        signal = self._make_signal(IntelligenceSeverity.HIGH)
        result = self.classifier.classify_signal(signal)
        self.assertEqual(result['incident_type'], 'truth_mismatch_incident')


class TestIncidentLifecycle(unittest.TestCase):
    def setUp(self):
        self.lifecycle = IncidentLifecycle(max_history=50)

    def test_open_to_acknowledged_valid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        result = self.lifecycle.transition(
            incident, IncidentStatus.ACKNOWLEDGED, tick=105
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['transition_valid'])
        self.assertEqual(result['old_status'], IncidentStatus.OPEN)
        self.assertEqual(result['new_status'], IncidentStatus.ACKNOWLEDGED)
        self.assertEqual(incident.status, IncidentStatus.ACKNOWLEDGED)

    def test_open_to_resolved_invalid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        result = self.lifecycle.transition(
            incident, IncidentStatus.RESOLVED, tick=105
        )
        self.assertFalse(result['success'])
        self.assertFalse(result['transition_valid'])
        self.assertEqual(incident.status, IncidentStatus.OPEN)

    def test_closed_is_terminal(self):
        self.assertTrue(self.lifecycle.is_terminal(IncidentStatus.CLOSED))

    def test_open_is_not_terminal(self):
        self.assertFalse(self.lifecycle.is_terminal(IncidentStatus.OPEN))

    def test_transition_history_recorded(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.ACKNOWLEDGED, tick=105)
        self.lifecycle.transition(incident, IncidentStatus.INVESTIGATING, tick=110)
        self.assertEqual(self.lifecycle.get_transition_count(), 2)

    def test_valid_transitions_for_open(self):
        valid = self.lifecycle.get_valid_transitions(IncidentStatus.OPEN)
        self.assertIn(IncidentStatus.ACKNOWLEDGED, valid)
        self.assertIn(IncidentStatus.INVESTIGATING, valid)
        self.assertIn(IncidentStatus.CLOSED, valid)
        self.assertNotIn(IncidentStatus.RESOLVED, valid)

    def test_valid_transitions_for_resolved(self):
        valid = self.lifecycle.get_valid_transitions(IncidentStatus.RESOLVED)
        self.assertIn(IncidentStatus.CLOSED, valid)
        self.assertIn(IncidentStatus.REOPENED, valid)

    def test_reopened_from_closed(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.CLOSED, tick=200)
        result = self.lifecycle.transition(
            incident, IncidentStatus.REOPENED, tick=210
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['transition_valid'])
        self.assertEqual(incident.status, IncidentStatus.REOPENED)

    def test_acknowledged_to_investigating_valid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.ACKNOWLEDGED, tick=105)
        result = self.lifecycle.transition(
            incident, IncidentStatus.INVESTIGATING, tick=110
        )
        self.assertTrue(result['success'])

    def test_acknowledged_to_resolved_valid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.ACKNOWLEDGED, tick=105)
        result = self.lifecycle.transition(
            incident, IncidentStatus.RESOLVED, tick=110
        )
        self.assertTrue(result['success'])

    def test_investigating_to_resolved_valid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.INVESTIGATING, tick=105)
        result = self.lifecycle.transition(
            incident, IncidentStatus.RESOLVED, tick=110
        )
        self.assertTrue(result['success'])

    def test_resolved_to_closed_valid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.ACKNOWLEDGED, tick=105)
        self.lifecycle.transition(incident, IncidentStatus.RESOLVED, tick=110)
        result = self.lifecycle.transition(
            incident, IncidentStatus.CLOSED, tick=115
        )
        self.assertTrue(result['success'])

    def test_closed_to_open_invalid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.CLOSED, tick=200)
        result = self.lifecycle.transition(
            incident, IncidentStatus.OPEN, tick=210
        )
        self.assertFalse(result['success'])
        self.assertFalse(result['transition_valid'])

    def test_clear_history(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.ACKNOWLEDGED, tick=105)
        self.lifecycle.clear()
        self.assertEqual(self.lifecycle.get_transition_count(), 0)

    def test_transition_records_incident_id(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.ACKNOWLEDGED, tick=105)
        history = self.lifecycle._history
        self.assertEqual(history[0].incident_id, 'inc-001')

    def test_reopened_transitions_valid(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        self.lifecycle.transition(incident, IncidentStatus.CLOSED, tick=200)
        self.lifecycle.transition(incident, IncidentStatus.REOPENED, tick=210)
        valid = self.lifecycle.get_valid_transitions(IncidentStatus.REOPENED)
        self.assertIn(IncidentStatus.ACKNOWLEDGED, valid)
        self.assertIn(IncidentStatus.INVESTIGATING, valid)
        self.assertIn(IncidentStatus.CLOSED, valid)


class TestEscalationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EscalationEngine(max_escalations=50)

    def test_critical_and_ticks_open_gt_10_returns_emergency(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.CRITICAL, 100)
        result = self.engine.evaluate_escalation(incident, tick=115, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.EMERGENCY)

    def test_high_and_ticks_open_gt_20_returns_escalate(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.HIGH, 100)
        result = self.engine.evaluate_escalation(incident, tick=125, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.ESCALATE)

    def test_medium_and_ticks_open_gt_30_returns_warn(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.MEDIUM, 100)
        result = self.engine.evaluate_escalation(incident, tick=135, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.WARN)

    def test_low_and_ticks_open_gt_50_returns_observe(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.LOW, 100)
        result = self.engine.evaluate_escalation(incident, tick=155, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.OBSERVE)

    def test_below_threshold_returns_none(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.CRITICAL, 100)
        result = self.engine.evaluate_escalation(incident, tick=105, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.NONE)

    def test_active_incident_count_bumps_level(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.CRITICAL, 100)
        result = self.engine.evaluate_escalation(incident, tick=115, active_incident_count=11)
        self.assertEqual(result['escalation_level'], EscalationLevel.EMERGENCY)

    def test_active_count_bump_from_none_to_observe(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.LOW, 100)
        result = self.engine.evaluate_escalation(incident, tick=105, active_incident_count=15)
        self.assertEqual(result['escalation_level'], EscalationLevel.OBSERVE)

    def test_active_count_bump_from_warn_to_escalate(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.MEDIUM, 100)
        result = self.engine.evaluate_escalation(incident, tick=135, active_incident_count=15)
        self.assertEqual(result['escalation_level'], EscalationLevel.ESCALATE)

    def test_record_escalation(self):
        result = self.engine.record_escalation(
            'inc-001', EscalationLevel.EMERGENCY, 'critical failure'
        )
        self.assertEqual(result['incident_id'], 'inc-001')
        self.assertEqual(result['level'], EscalationLevel.EMERGENCY)
        self.assertEqual(result['reason'], 'critical failure')

    def test_get_escalation_summary(self):
        self.engine.record_escalation('inc-001', EscalationLevel.WARN, 'high tick count')
        self.engine.record_escalation('inc-002', EscalationLevel.EMERGENCY, 'critical failure')
        summary = self.engine.get_escalation_summary()
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]['incident_id'], 'inc-001')
        self.assertEqual(summary[0]['level'], EscalationLevel.WARN)

    def test_get_escalation_count(self):
        self.assertEqual(self.engine.get_escalation_count(), 0)
        self.engine.record_escalation('inc-001', EscalationLevel.WARN, 'test')
        self.assertEqual(self.engine.get_escalation_count(), 1)

    def test_clear(self):
        self.engine.record_escalation('inc-001', EscalationLevel.WARN, 'test')
        self.engine.clear()
        self.assertEqual(self.engine.get_escalation_count(), 0)

    def test_evaluate_returns_priority_for_emergency(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.CRITICAL, 100)
        result = self.engine.evaluate_escalation(incident, tick=115, active_incident_count=1)
        self.assertEqual(result['priority'], OperationalPriority.CRITICAL)

    def test_evaluate_returns_priority_for_none(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.INFO, 100)
        result = self.engine.evaluate_escalation(incident, tick=105, active_incident_count=1)
        self.assertEqual(result['priority'], OperationalPriority.LOWEST)

    def test_low_ticks_open_exactly_50_no_observe(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.LOW, 100)
        result = self.engine.evaluate_escalation(incident, tick=150, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.NONE)

    def test_low_ticks_open_exactly_51_observe(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.LOW, 100)
        result = self.engine.evaluate_escalation(incident, tick=151, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.OBSERVE)

    def test_critical_exactly_10_ticks_no_emergency(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.CRITICAL, 100)
        result = self.engine.evaluate_escalation(incident, tick=110, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.NONE)

    def test_info_severity_never_escalates(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.INFO, 100)
        result = self.engine.evaluate_escalation(incident, tick=200, active_incident_count=1)
        self.assertEqual(result['escalation_level'], EscalationLevel.NONE)

    def test_reason_contains_severity_and_ticks(self):
        incident = _make_incident('inc-001', IntelligenceSeverity.CRITICAL, 100)
        result = self.engine.evaluate_escalation(incident, tick=115, active_incident_count=3)
        self.assertIn('critical', result['reason'])
        self.assertIn('15', result['reason'])
        self.assertIn('3', result['reason'])

    def test_escalation_summary_empty_initially(self):
        self.assertEqual(self.engine.get_escalation_summary(), [])


if __name__ == '__main__':
    unittest.main()

"""
Tests for Phase 4C — Control Center Orchestrator.
Covers ControlCenterEngine, ControlCenterRouter, OperationalCommandOrchestrator.
Deterministic tests. NO ERP mutation. Read-only verification only.
"""
import unittest
import unittest.mock
from typing import Any, Dict

from simulation.control_center.models import (
    OperationalSignal, SignalType, IntelligenceSeverity, AggregatedState,
    DashboardSnapshot, SafetyReport, OperationalState, OperationalPriority,
)
from simulation.control_center.orchestrator.control_center_engine import (
    ControlCenterEngine,
)
from simulation.control_center.orchestrator.control_center_router import (
    ControlCenterRouter,
)
from simulation.control_center.orchestrator.operational_command_orchestrator import (
    OperationalCommandOrchestrator,
)


def _make_signal(
    signal_id: str = 'sig_1',
    severity: IntelligenceSeverity = IntelligenceSeverity.INFO,
    source_phase: str = 'test',
    tick: int = 1,
) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id,
        signal_type=SignalType.TRUTH_MISMATCH,
        severity=severity,
        source_phase=source_phase,
        tick=tick,
        description=f'Test signal {signal_id}',
        payload={'key': 'value'},
    )


class TestControlCenterEngine(unittest.TestCase):
    """ControlCenterEngine: initialization, signal processing, pipeline outputs."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_engine_initializes_all_subcomponents(self):
        getters = [
            self.engine.get_aggregated_state,
            self.engine.get_unified_timeline,
            self.engine.get_incident_registry,
            self.engine.get_health_matrix,
            self.engine.get_state_classifier,
            self.engine.get_priority_engine,
            self.engine.get_stability_widgets,
            self.engine.get_health_summary,
            self.engine.get_heatmap,
            self.engine.get_dashboard_factory,
            self.engine.get_executive_summary,
            self.engine.get_risk_report,
            self.engine.get_intelligence_digest,
            self.engine.get_stability_report,
            self.engine.get_safety_monitor,
            self.engine.get_recursion_guard,
            self.engine.get_graph_guard,
            self.engine.get_memory_guard,
            self.engine.get_cross_phase_correlator,
            self.engine.get_sequence_tracker,
            self.engine.get_incident_lifecycle,
            self.engine.get_escalation_engine,
        ]
        for i, getter in enumerate(getters):
            with self.subTest(getter=f'getter_{i}'):
                instance = getter()
                self.assertIsNotNone(instance)

    def test_process_signal_returns_expected_keys(self):
        signal = _make_signal()
        result = self.engine.process_signal(signal)
        expected_keys = {
            'signal_id', 'success', 'ingest', 'timeline_event_id',
            'classification', 'incident', 'escalation',
            'aggregated_state', 'health', 'state_classification',
        }
        self.assertEqual(result['signal_id'], 'sig_1')
        self.assertTrue(result['success'])
        self.assertEqual(expected_keys, set(result.keys()))

    def test_process_signal_critical_creates_incident(self):
        signal = _make_signal(
            signal_id='sig_crit', severity=IntelligenceSeverity.CRITICAL,
        )
        result = self.engine.process_signal(signal)
        self.assertTrue(result['success'])
        self.assertTrue(result['incident']['registered'])
        self.assertIsNotNone(result['incident']['incident_id'])
        self.assertIsNotNone(result['escalation'])

    def test_process_signal_info_does_not_register_incident(self):
        signal = _make_signal(
            signal_id='sig_info', severity=IntelligenceSeverity.INFO,
        )
        result = self.engine.process_signal(signal)
        self.assertTrue(result['success'])
        self.assertFalse(result['incident']['registered'])
        self.assertIsNone(result['incident']['incident_id'])
        self.assertIsNone(result['escalation'])

    def test_process_signal_failure_returns_error(self):
        signal = _make_signal(signal_id='broken')
        with unittest.mock.patch.object(
            self.engine._state_aggregator, 'ingest_signal',
            side_effect=ValueError('broken'),
        ):
            result = self.engine.process_signal(signal)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_generate_dashboard_snapshot_returns_snapshot(self):
        self.engine.process_signal(_make_signal(tick=1))
        snapshot = self.engine.generate_dashboard_snapshot(tick=5)
        self.assertIsInstance(snapshot, DashboardSnapshot)
        self.assertEqual(snapshot.snapshot_id, 'snapshot_5')
        self.assertEqual(snapshot.tick, 5)

    def test_snapshot_widget_data_populated(self):
        self.engine.process_signal(
            _make_signal(severity=IntelligenceSeverity.CRITICAL, tick=1),
        )
        snapshot = self.engine.generate_dashboard_snapshot(tick=2)
        wd = snapshot.widget_data
        for key in ('aggregated_state', 'health', 'classification',
                    'priority', 'stability', 'health_summary',
                    'timeline_preview', 'active_incidents'):
            self.assertIn(key, wd, f'missing widget_data.{key}')

    def test_safety_report_returns_safe_for_fresh_engine(self):
        report = self.engine.generate_safety_report(context='test')
        self.assertIsInstance(report, SafetyReport)
        self.assertTrue(report.is_safe)

    def test_get_aggregated_state(self):
        state = self.engine.get_aggregated_state()
        self.assertIsInstance(state, AggregatedState)
        self.assertEqual(state.state, OperationalState.NORMAL)

    def test_get_unified_timeline(self):
        timeline = self.engine.get_unified_timeline()
        self.assertIsNotNone(timeline)

    def test_get_incident_registry(self):
        registry = self.engine.get_incident_registry()
        self.assertIsNotNone(registry)

    def test_engine_delegates_to_all_subcomponent_getters(self):
        self.assertIsNotNone(self.engine.get_health_matrix())
        self.assertIsNotNone(self.engine.get_state_classifier())
        self.assertIsNotNone(self.engine.get_priority_engine())
        self.assertIsNotNone(self.engine.get_stability_widgets())
        self.assertIsNotNone(self.engine.get_health_summary())
        self.assertIsNotNone(self.engine.get_heatmap())
        self.assertIsNotNone(self.engine.get_dashboard_factory())
        self.assertIsNotNone(self.engine.get_executive_summary())
        self.assertIsNotNone(self.engine.get_risk_report())
        self.assertIsNotNone(self.engine.get_intelligence_digest())
        self.assertIsNotNone(self.engine.get_stability_report())
        self.assertIsNotNone(self.engine.get_safety_monitor())
        self.assertIsNotNone(self.engine.get_recursion_guard())
        self.assertIsNotNone(self.engine.get_graph_guard())
        self.assertIsNotNone(self.engine.get_memory_guard())
        self.assertIsNotNone(self.engine.get_cross_phase_correlator())
        self.assertIsNotNone(self.engine.get_sequence_tracker())
        self.assertIsNotNone(self.engine.get_incident_lifecycle())
        self.assertIsNotNone(self.engine.get_escalation_engine())
        self.assertIsNotNone(self.engine.get_drift_visualization())

    def test_clear_all_resets_state(self):
        for i in range(5):
            self.engine.process_signal(
                _make_signal(signal_id=f'sig_{i}', tick=i),
            )
        self.assertEqual(self.engine.get_orchestration_count(), 5)
        self.engine.clear_all()
        self.assertEqual(self.engine.get_orchestration_count(), 0)
        state = self.engine.get_aggregated_state()
        self.assertEqual(state.active_signals, 0)

    def test_orchestration_count_increases(self):
        self.assertEqual(self.engine.get_orchestration_count(), 0)
        self.engine.process_signal(_make_signal(signal_id='a'))
        self.assertEqual(self.engine.get_orchestration_count(), 1)
        self.engine.process_signal(_make_signal(signal_id='b'))
        self.assertEqual(self.engine.get_orchestration_count(), 2)


class TestControlCenterRouter(unittest.TestCase):
    """ControlCenterRouter: signal routing, batch processing, query dispatching."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_init_stores_engine_reference(self):
        self.assertIs(self.router.get_engine(), self.engine)

    def test_route_signal_processes_and_returns_dict(self):
        signal = _make_signal()
        result = self.router.route_signal(signal)
        self.assertTrue(result['success'])
        self.assertIn('signal_id', result)

    def test_route_signal_sets_source_phase_when_empty(self):
        signal = _make_signal(source_phase='')
        result = self.router.route_signal(signal)
        self.assertTrue(result['success'])
        self.assertEqual(signal.source_phase, 'control_center')

    def test_route_batch_processes_all_signals(self):
        signals = [
            _make_signal(signal_id=f'sig_{i}', tick=i)
            for i in range(5)
        ]
        results = self.router.route_batch(signals)
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertTrue(r['success'])

    def test_route_query_state(self):
        self.engine.process_signal(_make_signal(tick=1))
        result = self.router.route_query('state')
        self.assertTrue(result['success'])
        self.assertEqual(result['query_type'], 'state')
        self.assertIn('state', result['data'])

    def test_route_query_timeline(self):
        self.engine.process_signal(_make_signal(tick=1))
        result = self.router.route_query('timeline')
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['data']['event_count'], 1)

    def test_route_query_incidents(self):
        self.engine.process_signal(
            _make_signal(severity=IntelligenceSeverity.CRITICAL, tick=1),
        )
        result = self.router.route_query('incidents')
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['data']['incident_count'], 1)

    def test_route_query_dashboard(self):
        self.engine.process_signal(_make_signal(tick=1))
        result = self.router.route_query('dashboard', {'tick': 5})
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['tick'], 5)

    def test_route_query_health(self):
        self.engine.process_signal(_make_signal(tick=1))
        result = self.router.route_query('health')
        self.assertTrue(result['success'])
        self.assertIn('health', result['data'])

    def test_route_query_safety(self):
        result = self.router.route_query('safety')
        self.assertTrue(result['success'])
        self.assertTrue(result['data']['is_safe'])

    def test_route_query_reports_executive_summary(self):
        result = self.router.route_query('reports', {
            'report_type': 'executive_summary', 'tick': 1,
        })
        self.assertTrue(result['success'])
        self.assertEqual(result['report_type'], 'executive_summary')

    def test_route_query_unknown(self):
        result = self.router.route_query('unknown')
        self.assertFalse(result['success'])

    def test_get_engine_returns_engine(self):
        self.assertIs(self.router.get_engine(), self.engine)

    def test_get_routing_count_increments(self):
        self.assertEqual(self.router.get_routing_count(), 0)
        self.router.route_signal(_make_signal())
        self.assertEqual(self.router.get_routing_count(), 1)
        self.router.route_query('state')
        self.assertEqual(self.router.get_routing_count(), 2)


class TestOperationalCommandOrchestrator(unittest.TestCase):
    """OperationalCommandOrchestrator: command validation, execution, history."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.orchestrator = OperationalCommandOrchestrator(self.engine)

    def test_execute_aggregate_state(self):
        result = self.orchestrator.execute_command('aggregate_state')
        self.assertTrue(result['success'])
        self.assertIn('state', result['result'])

    def test_execute_generate_snapshot(self):
        result = self.orchestrator.execute_command(
            'generate_snapshot', tick=5,
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['result']['snapshot_id'], 'snapshot_5')

    def test_execute_safety_check(self):
        result = self.orchestrator.execute_command('safety_check')
        self.assertTrue(result['success'])
        self.assertTrue(result['result']['is_safe'])

    def test_execute_report_executive_summary(self):
        result = self.orchestrator.execute_command('generate_report', {
            'report_type': 'executive_summary', 'tick': 1,
        })
        self.assertTrue(result['success'])

    def test_execute_report_risk_report(self):
        result = self.orchestrator.execute_command('generate_report', {
            'report_type': 'risk_report', 'tick': 1,
        })
        self.assertTrue(result['success'])

    def test_execute_report_stability_report(self):
        result = self.orchestrator.execute_command('generate_report', {
            'report_type': 'stability_report', 'tick': 1,
        })
        self.assertTrue(result['success'])

    def test_execute_get_timeline(self):
        result = self.orchestrator.execute_command('get_timeline')
        self.assertTrue(result['success'])

    def test_execute_get_incidents(self):
        result = self.orchestrator.execute_command('get_incidents')
        self.assertTrue(result['success'])

    def test_execute_get_health(self):
        result = self.orchestrator.execute_command('get_health')
        self.assertTrue(result['success'])

    def test_execute_clear_without_confirm_fails(self):
        result = self.orchestrator.execute_command(
            'clear', {'confirm': False},
        )
        self.assertFalse(result['success'])

    def test_execute_clear_with_confirm_succeeds(self):
        self.engine.process_signal(_make_signal(tick=1))
        self.assertGreater(self.engine.get_orchestration_count(), 0)
        result = self.orchestrator.execute_command(
            'clear', {'confirm': True},
        )
        self.assertTrue(result['success'])
        self.assertEqual(self.engine.get_orchestration_count(), 0)

    def test_execute_unknown_command(self):
        result = self.orchestrator.execute_command('unknown')
        self.assertFalse(result['success'])

    def test_is_command_allowed(self):
        self.assertTrue(
            self.orchestrator.is_command_allowed('aggregate_state'),
        )
        self.assertFalse(self.orchestrator.is_command_allowed('unknown'))

    def test_command_history_records_commands(self):
        self.assertEqual(self.orchestrator.get_command_count(), 0)
        self.orchestrator.execute_command('aggregate_state')
        self.assertEqual(self.orchestrator.get_command_count(), 1)
        self.orchestrator.execute_command('safety_check')
        self.assertEqual(self.orchestrator.get_command_count(), 2)

    def test_command_history_and_clear(self):
        self.orchestrator.execute_command('aggregate_state')
        self.orchestrator.execute_command('get_health')
        self.assertEqual(len(self.orchestrator.get_command_history()), 2)
        self.orchestrator.clear_history()
        self.assertEqual(self.orchestrator.get_command_count(), 0)


if __name__ == '__main__':
    unittest.main()

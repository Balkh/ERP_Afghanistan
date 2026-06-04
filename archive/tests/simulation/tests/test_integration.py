"""
Integration tests for Phase 4C — Control Center full pipeline.
Exercises the complete end-to-end signal processing, state aggregation,
dashboard snapshots, safety reports, routing, and command orchestration.
Deterministic tests. NO ERP mutation. Read-only verification only.
"""
import unittest

from simulation.control_center.models import (
    OperationalSignal, SignalType, IntelligenceSeverity,
    OperationalState, OperationalPriority,
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


class TestFullPipeline(unittest.TestCase):
    """Full pipeline with 10 signals of varying severity."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_full_pipeline_ten_signals(self):
        severities = [
            IntelligenceSeverity.CRITICAL,
            IntelligenceSeverity.CRITICAL,
            IntelligenceSeverity.HIGH,
            IntelligenceSeverity.HIGH,
            IntelligenceSeverity.HIGH,
            IntelligenceSeverity.MEDIUM,
            IntelligenceSeverity.MEDIUM,
            IntelligenceSeverity.MEDIUM,
            IntelligenceSeverity.INFO,
            IntelligenceSeverity.INFO,
        ]
        for i, sev in enumerate(severities):
            result = self.engine.process_signal(
                _make_signal(signal_id=f'sig_{i}', severity=sev, tick=i + 1),
            )
            self.assertTrue(result['success'], f'sig_{i} failed')

        self.assertEqual(self.engine.get_orchestration_count(), 10)

        aggregated = self.engine.get_aggregated_state()
        self.assertGreaterEqual(aggregated.critical_count, 2)

        timeline = self.engine.get_unified_timeline()
        self.assertEqual(timeline.get_event_count(), 10)

        registry = self.engine.get_incident_registry()
        incidents = registry.get_incidents()
        self.assertGreaterEqual(len(incidents), 1)

        critical_severity_signals = sum(
            1 for sev in (IntelligenceSeverity.CRITICAL, IntelligenceSeverity.HIGH)
            for s in [sev]
        )
        incident_count = len(incidents)
        self.assertGreaterEqual(incident_count, 1)

        snapshot = self.engine.generate_dashboard_snapshot(tick=10)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.tick, 10)
        self.assertIn('aggregated_state', snapshot.widget_data)

        report = self.engine.generate_safety_report(context='integration')
        self.assertTrue(report.is_safe)

        self.assertIn(
            aggregated.state,
            (OperationalState.DEGRADED, OperationalState.CRITICAL, OperationalState.EMERGENCY),
        )


class TestPipelineWithRecoveryState(unittest.TestCase):
    """Pipeline producing EMERGENCY state via critical_count > 5."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_emergency_state_from_critical_signals(self):
        for i in range(7):
            result = self.engine.process_signal(
                _make_signal(
                    signal_id=f'critical_{i}',
                    severity=IntelligenceSeverity.CRITICAL,
                    tick=i + 1,
                ),
            )
            self.assertTrue(result['success'])

        aggregated = self.engine.get_aggregated_state()
        self.assertGreater(aggregated.critical_count, 5)
        self.assertEqual(aggregated.state, OperationalState.EMERGENCY)
        self.assertEqual(aggregated.priority, OperationalPriority.CRITICAL)

        report = self.engine.generate_safety_report(context='emergency')
        self.assertTrue(report.is_safe)


class TestBoundedMemoryInPipeline(unittest.TestCase):
    """Pipeline bounds: 2000 signals should be capped at 1000."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.max_signals = 2000

    def test_bounded_memory_caps_signals(self):
        for i in range(self.max_signals):
            result = self.engine.process_signal(
                _make_signal(
                    signal_id=f'sig_{i}',
                    severity=IntelligenceSeverity.INFO,
                    tick=i,
                ),
            )
            if i < 1500:
                self.assertTrue(result['success'], f'sig_{i} failed at {i}')
        aggregated = self.engine.get_aggregated_state()
        self.assertLessEqual(aggregated.active_signals, 1000)
        self.assertEqual(self.engine.get_orchestration_count(), self.max_signals)

        snapshot = self.engine.generate_dashboard_snapshot(tick=2000)
        self.assertIsNotNone(snapshot)


class TestExceptionSafety(unittest.TestCase):
    """Exception safety: minimal signals, negative tick, clear after errors."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_minimal_signal_processes(self):
        signal = _make_signal(
            signal_id='minimal',
            severity=IntelligenceSeverity.LOW,
            tick=0,
        )
        result = self.engine.process_signal(signal)
        self.assertTrue(result['success'])

    def test_negative_tick_snapshot(self):
        snapshot = self.engine.generate_dashboard_snapshot(tick=-1)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.tick, -1)

    def test_clear_all_after_processing(self):
        for i in range(10):
            self.engine.process_signal(
                _make_signal(signal_id=f'sig_{i}', tick=i),
            )
        self.assertEqual(self.engine.get_orchestration_count(), 10)
        self.engine.clear_all()
        self.assertEqual(self.engine.get_orchestration_count(), 0)
        aggregated = self.engine.get_aggregated_state()
        self.assertEqual(aggregated.active_signals, 0)


class TestRouterQueryTypes(unittest.TestCase):
    """All 7 route_query types return success."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)
        self.engine.process_signal(
            _make_signal(
                signal_id='init',
                severity=IntelligenceSeverity.CRITICAL,
                tick=1,
            ),
        )
        self.engine.process_signal(
            _make_signal(
                signal_id='init2',
                severity=IntelligenceSeverity.HIGH,
                tick=2,
            ),
        )
        self.engine.process_signal(
            _make_signal(
                signal_id='init3',
                severity=IntelligenceSeverity.INFO,
                tick=3,
            ),
        )

    def test_batch_routing_then_all_query_types(self):
        batch_signals = [
            _make_signal(signal_id=f'batch_{i}', tick=10 + i)
            for i in range(3)
        ]
        batch_results = self.router.route_batch(batch_signals)
        self.assertEqual(len(batch_results), 3)
        for r in batch_results:
            self.assertTrue(r['success'])

        query_types = [
            ('state', {}),
            ('timeline', {}),
            ('incidents', {}),
            ('dashboard', {'tick': 5}),
            ('health', {}),
            ('safety', {}),
            ('reports', {'report_type': 'executive_summary', 'tick': 1}),
        ]
        for qt, params in query_types:
            with self.subTest(query_type=qt):
                result = self.router.route_query(qt, params)
                self.assertTrue(
                    result['success'],
                    f'query {qt} failed: {result}',
                )


class TestCommandOrchestratorAllCommands(unittest.TestCase):
    """All 8 command types succeed through Orchestrator."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.engine.process_signal(
            _make_signal(
                signal_id='crit',
                severity=IntelligenceSeverity.CRITICAL,
                tick=1,
            ),
        )
        self.engine.process_signal(
            _make_signal(
                signal_id='high',
                severity=IntelligenceSeverity.HIGH,
                tick=2,
            ),
        )
        self.engine.process_signal(
            _make_signal(
                signal_id='med',
                severity=IntelligenceSeverity.MEDIUM,
                tick=3,
            ),
        )
        self.orchestrator = OperationalCommandOrchestrator(self.engine)

    def test_all_commands_succeed(self):
        commands = [
            ('aggregate_state', {}, 0),
            ('generate_snapshot', {}, 5),
            ('safety_check', {}, 0),
            ('generate_report', {'report_type': 'executive_summary', 'tick': 1}, 0),
            ('generate_report', {'report_type': 'risk_report', 'tick': 1}, 0),
            ('generate_report', {'report_type': 'stability_report', 'tick': 1}, 0),
            ('get_timeline', {}, 0),
            ('get_incidents', {}, 0),
            ('get_health', {}, 0),
        ]
        for cmd, params, tick in commands:
            with self.subTest(command=cmd):
                result = self.orchestrator.execute_command(cmd, params, tick)
                self.assertTrue(
                    result['success'],
                    f'command {cmd} failed: {result.get("error")}',
                )

        self.assertEqual(self.orchestrator.get_command_count(), len(commands))

    def test_clear_command_with_confirm(self):
        result = self.orchestrator.execute_command(
            'clear', {'confirm': True}, 0,
        )
        self.assertTrue(result['success'])
        self.assertEqual(self.engine.get_orchestration_count(), 0)


if __name__ == '__main__':
    unittest.main()

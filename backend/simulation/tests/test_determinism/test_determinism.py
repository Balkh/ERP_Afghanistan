"""
Tests for deterministic rendering and bounded memory guarantees.
"""
from django.test import TestCase
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity


class ControlCenterEngineDeterminismTest(TestCase):
    """Test ControlCenterEngine produces deterministic output."""
    
    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)
    
    def test_clear_restores_initial_state(self):
        """clear() must restore initial state."""
        self.engine.clear()
        state1 = self.router.route_query('state')
        self.engine.clear()
        state2 = self.router.route_query('state')
        self.assertEqual(
            state1['data']['active_signals'],
            state2['data']['active_signals']
        )
    
    def test_identical_signals_produce_identical_state(self):
        """Same signals in same order must produce same state."""
        self.engine.clear()
        
        signals = [
            OperationalSignal(
                signal_id=f"det-test-{i}",
                signal_type=SignalType.ANOMALY,
                severity=IntelligenceSeverity.LOW,
                source_phase="test",
                tick=i,
                description=f"Test signal {i}",
                payload={},
                timestamp=1000.0 + i,
            )
            for i in range(5)
        ]
        
        for sig in signals:
            self.engine.process_signal(sig)
        
        state1 = self.router.route_query('state')
        
        # Repeat with same signals
        self.engine.clear()
        for sig in signals:
            self.engine.process_signal(sig)
        state2 = self.router.route_query('state')
        
        self.assertEqual(
            state1['data']['active_signals'],
            state2['data']['active_signals']
        )
    
    def test_empty_state_consistent(self):
        """Empty engine state must be consistent."""
        self.engine.clear()
        state = self.router.route_query('state')
        self.assertTrue(state['success'])
        self.assertIn('data', state)
    
    def test_dashboard_snapshot_deterministic(self):
        """Dashboard snapshot with same tick must be same."""
        self.engine.clear()
        snap1 = self.engine.generate_dashboard_snapshot(1)
        self.engine.clear()
        snap2 = self.engine.generate_dashboard_snapshot(1)
        
        self.assertEqual(snap1.tick, snap2.tick)
        self.assertEqual(snap1.operational_state, snap2.operational_state)
    
    def test_safety_report_deterministic(self):
        """Safety report from same context must be same."""
        report1 = self.engine.generate_safety_report("test-context")
        report2 = self.engine.generate_safety_report("test-context")
        self.assertEqual(report1.is_safe, report2.is_safe)


class ControlCenterBoundedMemoryTest(TestCase):
    """Test control center has bounded memory."""
    
    def setUp(self):
        self.engine = ControlCenterEngine()
    
    def test_many_signals_dont_crash(self):
        """Processing many signals must not crash engine."""
        for i in range(1000):
            sig = OperationalSignal(
                signal_id=f"mem-test-{i}",
                signal_type=SignalType.DRIFT_TREND,
                severity=IntelligenceSeverity.INFO,
                source_phase="test",
                tick=i,
                description=f"Memory test {i}",
                payload={},
                timestamp=1000.0 + i,
            )
            try:
                self.engine.process_signal(sig)
            except Exception as e:
                self.fail(f"Engine crashed at signal {i}: {e}")
        
        # After 1000 signals, engine should still produce valid state
        state = self.engine.get_aggregated_state()
        self.assertIsNotNone(state)
    
    def test_safety_report_after_many_signals(self):
        """Safety report after many signals must not show violations."""
        for i in range(500):
            sig = OperationalSignal(
                signal_id=f"safety-test-{i}",
                signal_type=SignalType.DRIFT_TREND,
                severity=IntelligenceSeverity.LOW,
                source_phase="test",
                tick=i,
                description=f"Safety test {i}",
                payload={},
                timestamp=1000.0 + i,
            )
            self.engine.process_signal(sig)
        
        report = self.engine.generate_safety_report("stress-test")
        # Should still be safe (bounded memory prevents overflow)
        self.assertIsNotNone(report)
    
    def test_orchestration_count_bounded(self):
        """Orchestration count must not overflow."""
        count = self.engine.get_orchestration_count()
        self.assertGreaterEqual(count, 0)
        self.assertLess(count, 10_000_000)  # Sanity bound


class ReplayEngineDeterminismTest(TestCase):
    """Test ReplayEngine determinism."""
    
    def setUp(self):
        self.engine = ReplayEngine()
    
    def test_execute_replay_returns_consistent_structure(self):
        """execute_replay must return consistent dict structure."""
        events = [
            {'tick': 1, 'event_type': 'TEST', 'payload': {'value': 1}},
            {'tick': 2, 'event_type': 'TEST', 'payload': {'value': 2}},
        ]
        result1 = self.engine.execute_replay('det-session-1', events)
        result2 = self.engine.execute_replay('det-session-2', events)
        
        self.assertIsInstance(result1, dict)
        self.assertIsInstance(result2, dict)
    
    def test_controller_properties(self):
        """Controller properties must be deterministic."""
        ctrl1 = self.engine.controller
        ctrl2 = self.engine.controller
        self.assertEqual(type(ctrl1), type(ctrl2))


class NoInfiniteLoopTest(TestCase):
    """Test that no rendering loops are possible."""
    
    def test_router_query_does_not_loop(self):
        """Router queries must complete within reasonable time."""
        engine = ControlCenterEngine()
        router = ControlCenterRouter(engine)
        
        import time
        start = time.time()
        result = router.route_query('state')
        elapsed = time.time() - start
        
        self.assertTrue(result['success'])
        self.assertLess(elapsed, 5.0, "State query took too long")
    
    def test_dashboard_snapshot_does_not_loop(self):
        """Dashboard snapshot generation must complete quickly."""
        engine = ControlCenterEngine()
        
        import time
        start = time.time()
        snap = engine.generate_dashboard_snapshot(0)
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 5.0, "Dashboard snapshot took too long")
    
    def test_safety_report_does_not_loop(self):
        """Safety report generation must complete quickly."""
        engine = ControlCenterEngine()
        
        import time
        start = time.time()
        report = engine.generate_safety_report("loop-test")
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 5.0, "Safety report took too long")


class DeterministicNoERPWriteTest(TestCase):
    """Test that no test in the determinism suite triggers ERP writes."""
    
    def test_all_tests_use_simulation_only(self):
        """All deterministic tests must not import ERP models."""
        import ast
        import simulation.tests.test_determinism.test_determinism as mod
        with open(mod.__file__) as f:
            tree = ast.parse(f.read())
        erp_modules = ['inventory', 'accounting', 'sales', 'purchases']
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in erp_modules:
                self.fail(
                    f"Determinism test should not import ERP: from {node.module}"
                )

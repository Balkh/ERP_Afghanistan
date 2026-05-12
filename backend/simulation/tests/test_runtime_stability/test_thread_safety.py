"""
Phase 5A.5 — Thread Starvation & Deadlock Safety.

Validates:
- Concurrent safety guard behavior
- No deadlocks under concurrent signal processing
- Safe worker cancellation (simulated via sequential patterns)
- Engine isolation across simulated concurrent access

All tests are deterministic (no actual threading — we simulate
concurrent access patterns via sequential interleaving).

Deterministic. Bounded. No ERP mutation.
"""
import unittest
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.replay.replay_engine.replay_safety_guard import ReplaySafetyGuard


def _make_signal(signal_id: str, tick: int,
                 stype: SignalType = SignalType.ANOMALY,
                 severity: IntelligenceSeverity = IntelligenceSeverity.LOW) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id, signal_type=stype, severity=severity,
        source_phase="thread_test", tick=tick,
        description=f"Thread {signal_id}", payload={}, timestamp=float(tick),
    )


class ConcurrentAccessPatternTest(unittest.TestCase):
    """Simulates concurrent access to engine from multiple 'threads'."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_interleaved_read_write(self):
        """Interleaved signal processing and queries work."""
        for i in range(1000):
            sig = _make_signal(f"interleave-{i}", i)
            result = self.engine.process_signal(sig)
            self.assertTrue(result["success"])
            if i % 100 == 0:
                state = self.router.route_query("state")
                self.assertTrue(state["success"])
                snap = self.engine.generate_dashboard_snapshot(i)
                self.assertIsNotNone(snap)

    def test_multiple_routers_same_engine(self):
        """Multiple router instances accessing same engine work."""
        router2 = ControlCenterRouter(self.engine)
        router3 = ControlCenterRouter(self.engine)
        for i in range(500):
            sig = _make_signal(f"multi-router-{i}", i)
            self.engine.process_signal(sig)
            if i % 200 == 0:
                r1 = self.router.route_query("state")
                r2 = router2.route_query("state")
                r3 = router3.route_query("state")
                self.assertTrue(r1["success"])
                self.assertTrue(r2["success"])
                self.assertTrue(r3["success"])

    def test_concurrent_safety_and_dashboard(self):
        """Safety report and dashboard generation interleaved."""
        for i in range(500):
            sig = _make_signal(f"conc-sd-{i}", i)
            self.engine.process_signal(sig)
            if i % 50 == 0:
                report = self.engine.generate_safety_report("conc-test")
                self.assertIsNotNone(report)
                snap = self.engine.generate_dashboard_snapshot(i)
                self.assertIsNotNone(snap)


class DeadlockPreventionTest(unittest.TestCase):
    """No deadlocks under pressure (simulated)."""

    def test_engine_operations_sequence(self):
        """Sequential engine operations complete without hanging."""
        engine = ControlCenterEngine()
        router = ControlCenterRouter(engine)
        for i in range(1000):
            sig = _make_signal(f"deadlock-{i}", i)
            engine.process_signal(sig)
            if i % 100 == 0:
                router.route_query("state")
                router.route_query("timeline")
                router.route_query("incidents")
                router.route_query("dashboard", {"tick": i})
                router.route_query("health")
                engine.generate_safety_report("deadlock-test")

    def test_clear_during_processing(self):
        """Clear during active processing recovers cleanly."""
        engine = ControlCenterEngine()
        for i in range(2000):
            sig = _make_signal(f"clrproc-{i}", i)
            engine.process_signal(sig)
            if i == 1000:
                engine.clear()
        state = engine.get_aggregated_state()
        self.assertIsNotNone(state)


class WorkerCleanupTest(unittest.TestCase):
    """Simulates worker cleanup patterns."""

    def test_engine_reuse_after_clear(self):
        """Engine reused after clear produces valid state."""
        engine = ControlCenterEngine()
        for i in range(1000):
            sig = _make_signal(f"reuse-{i}", i)
            engine.process_signal(sig)
        engine.clear()
        for i in range(100):
            sig = _make_signal(f"reuse-after-{i}", i)
            result = engine.process_signal(sig)
            self.assertTrue(result["success"])
        state = engine.get_aggregated_state()
        self.assertIsNotNone(state)

    def test_safety_guard_reuse_after_clear(self):
        """Safety guard reused after clear works correctly."""
        guard = ReplaySafetyGuard()
        for i in range(50):
            guard.check_write_operation(f"op-{i}")
        guard.clear()
        self.assertEqual(guard._violation_count, 0)
        result = guard.check_write_operation("new-op")
        self.assertFalse(result["allowed"])


class StarvationResistanceTest(unittest.TestCase):
    """No operation starvation under sustained load."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_all_query_types_succeed_under_load(self):
        """All query types succeed even after heavy signal processing."""
        for i in range(5000):
            sig = _make_signal(f"starv-{i}", i)
            self.engine.process_signal(sig)
        query_types = ["state", "timeline", "incidents", "dashboard", "health", "safety"]
        for qtype in query_types:
            result = self.router.route_query(qtype)
            self.assertTrue(result.get("success", False), f"Query {qtype} failed")

    def test_timeline_query_not_starved(self):
        """Timeline queries not starved by signal processing."""
        for i in range(5000):
            sig = _make_signal(f"starvtl-{i}", i)
            self.engine.process_signal(sig)
            if i % 100 == 0:
                result = self.router.route_query("timeline")
                self.assertTrue(result["success"])

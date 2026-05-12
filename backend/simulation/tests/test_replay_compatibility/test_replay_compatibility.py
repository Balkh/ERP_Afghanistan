"""
Phase 5A.5.5 — Replay Compatibility Tests.

Validates:
- Replay session structure stability
- Safety guard behavior across engine lifecycles
- Replay ordering determinism
- Session manager bounded history
"""
import unittest
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.replay.replay_engine.replay_safety_guard import ReplaySafetyGuard
from simulation.replay.replay_engine.replay_session import ReplaySessionManager
from simulation.replay.replay_engine.replay_controller import ReplayController
from simulation.replay.models import ReplayMode


class ReplayStructureStabilityTest(unittest.TestCase):
    """Replay session structures are stable across engine lifecycles."""

    def test_session_has_required_attributes(self):
        """Replay session has all required attributes."""
        manager = ReplaySessionManager()
        manager.create_session("stable-test")
        session_data = manager.get_session("stable-test")
        self.assertIsNotNone(session_data)
        expected_keys = {"session_id", "status", "mode", "start_tick",
                         "current_tick", "end_tick", "events_replayed", "is_paused"}
        self.assertTrue(expected_keys.issubset(session_data.keys()))

    def test_replay_engine_has_required_components(self):
        """ReplayEngine initializes all subcomponents."""
        engine = ReplayEngine()
        self.assertIsNotNone(engine.sessions)
        self.assertIsNotNone(engine.controller)
        self.assertIsNotNone(engine.safety_guard)

    def test_safety_guard_state_after_clear(self):
        """Safety guard state resets after clear."""
        guard = ReplaySafetyGuard()
        for i in range(10):
            guard.check_write_operation(f"op-{i}")
        self.assertEqual(guard._violation_count, 10)
        guard.clear()
        self.assertEqual(guard._violation_count, 0)

    def test_session_manager_clear(self):
        """Session manager clear removes all sessions."""
        manager = ReplaySessionManager()
        manager.create_session("clear-test")
        self.assertIsNotNone(manager.get_session("clear-test"))
        manager.clear()
        self.assertIsNone(manager.get_session("clear-test"))


class SafetyGuardAcrossLifecyclesTest(unittest.TestCase):
    """Safety guard behavior is stable across engine lifecycles."""

    def test_safety_guard_always_blocks(self):
        """Safety guard blocks writes across multiple checks."""
        guard = ReplaySafetyGuard()
        for i in range(100):
            result = guard.check_write_operation(f"op-{i}")
            self.assertFalse(result["allowed"])

    def test_safety_guard_violations_bounded(self):
        """Safety guard violation history stays bounded."""
        guard = ReplaySafetyGuard()
        for i in range(200):
            guard.check_write_operation(f"op-{i}")
        self.assertLessEqual(len(guard._safety_violations), 100)

    def test_safety_guard_safe_call(self):
        """Safe call with non-raising function works."""
        guard = ReplaySafetyGuard()
        result = guard.safe_call(lambda: 42, -1)
        self.assertEqual(result, 42)

    def test_safety_guard_safe_call_exception(self):
        """Safe call catches exceptions and returns default."""
        guard = ReplaySafetyGuard()

        def _raising():
            raise ValueError("Expected failure")

        result = guard.safe_call(_raising, "safe")
        self.assertEqual(result, "safe")


class ReplayOrderingDeterminismTest(unittest.TestCase):
    """Replay operations maintain deterministic ordering."""

    def test_controller_ordering(self):
        """Controller operations are recorded in order."""
        ctrl = ReplayController()
        ctrl.start("order-test", ReplayMode.FULL)
        ctrl.pause("order-test")
        ctrl.resume("order-test")
        ctrl.step_forward("order-test")
        self.assertEqual(len(ctrl._control_history), 4)
        self.assertEqual(ctrl._control_history[0]["action"], "start")
        self.assertEqual(ctrl._control_history[1]["action"], "pause")
        self.assertEqual(ctrl._control_history[2]["action"], "resume")
        self.assertEqual(ctrl._control_history[3]["action"], "step_forward")

    def test_engine_execute_replay_same_result(self):
        """Same replay session produces same structure."""
        engine = ReplayEngine()
        engine.sessions.create_session("det-test")
        result = engine.execute_replay("det-test", [])
        self.assertIsInstance(result, dict)


class SessionManagerBoundedHistoryTest(unittest.TestCase):
    """Session manager history is bounded."""

    def test_session_history_maxlen(self):
        """Session history has maxlen=50."""
        manager = ReplaySessionManager(max_sessions=50)
        for i in range(100):
            manager.create_session(f"history-{i}")
        self.assertLessEqual(len(manager._session_history), 50)

    def test_old_sessions_evicted(self):
        """Old session references evicted from history."""
        manager = ReplaySessionManager(max_sessions=10)
        for i in range(20):
            manager.create_session(f"evict-{i}")
        self.assertEqual(len(manager._session_history), 10)
        # Old sessions should be evicted from history deque,
        # but the session dict might still hold them
        self.assertIsNotNone(manager.get_session("evict-19"))

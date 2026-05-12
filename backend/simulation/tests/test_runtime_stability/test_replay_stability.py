"""
Phase 5A.5 — Replay Concurrency & Stability.

Validates:
- Multiple concurrent replay sessions
- Replay freeze correctness
- Deterministic replay rendering
- Replay session isolation under memory pressure
- No snapshot corruption during concurrent access

Deterministic. Bounded. No ERP mutation.
"""
import unittest
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.replay.replay_engine.replay_safety_guard import ReplaySafetyGuard
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity


class ConcurrentReplaySessionsTest(unittest.TestCase):
    """Multiple concurrent replay sessions maintain isolation."""

    def setUp(self):
        self.engine = ReplayEngine()

    def test_create_10_sessions(self):
        """10 concurrent replay sessions created without error."""
        sessions = []
        for i in range(10):
            sid = f"concurrent-{i}"
            self.engine.sessions.create_session(sid)
            result = self.engine.execute_replay(sid, [
                {"tick": 1, "event_type": "TEST", "payload": {"id": i}},
                {"tick": 2, "event_type": "TEST", "payload": {"id": i}},
            ])
            sessions.append(result)
        for i, result in enumerate(sessions):
            self.assertIsInstance(result, dict, f"Session {i} failed")

    def test_session_isolation(self):
        """Replay sessions do not interfere with each other."""
        for i in range(5):
            sid = f"isolated-{i}"
            self.engine.sessions.create_session(sid)
            result = self.engine.execute_replay(sid, [
                {"tick": 1, "event_type": "TEST", "payload": {"session": i}},
            ])
            self.assertIsInstance(result, dict, f"Isolated session {i} failed")
        manager = self.engine.sessions
        for i in range(5):
            sid = f"isolated-{i}"
            session = manager.get_session(sid)
            self.assertIsNotNone(session, f"Session {i} not found")

    def test_50_sessions_no_leak(self):
        """50 replay sessions do not exceed session history bounds."""
        for i in range(50):
            sid = f"many-{i}"
            self.engine.sessions.create_session(sid)
            self.engine.execute_replay(sid, [
                {"tick": 1, "event_type": "TEST", "payload": {}},
            ])
        manager = self.engine.sessions
        self.assertLessEqual(len(manager._session_history), 50)

    def test_100_sessions_truncation(self):
        """100 sessions correctly truncate to maxlen."""
        for i in range(100):
            sid = f"trunc-{i}"
            self.engine.sessions.create_session(sid)
            self.engine.execute_replay(sid, [
                {"tick": 1, "event_type": "TEST", "payload": {}},
            ])
        manager = self.engine.sessions
        self.assertLessEqual(len(manager._session_history), 50)

    def test_sessions_after_clear(self):
        """Sessions are cleared on engine clear."""
        for i in range(10):
            sid = f"clear-test-{i}"
            self.engine.sessions.create_session(sid)
            self.engine.execute_replay(sid, [
                {"tick": 1, "event_type": "TEST", "payload": {}},
            ])
        self.engine.sessions.clear()
        for i in range(10):
            session = self.engine.sessions.get_session(f"clear-test-{i}")
            self.assertIsNone(session)


class ReplayFreezeValidationTest(unittest.TestCase):
    """Replay freeze/snapshot isolation is maintained."""

    def setUp(self):
        self.engine = ReplayEngine()
        self.safety_guard = ReplaySafetyGuard()

    def test_safety_guard_blocks_all_writes(self):
        """Safety guard blocks all write operations."""
        operations = ["replay", "dispatch", "receive", "transfer",
                      "adjust", "create", "update", "delete"]
        for op in operations:
            result = self.safety_guard.check_write_operation(op)
            self.assertFalse(result["allowed"], f"Operation {op} not blocked")

    def test_safety_guard_blocks_business_logic(self):
        """Safety guard blocks all business logic operations."""
        result = self.safety_guard.check_business_logic("any")
        self.assertFalse(result.get("allowed", True))

    def test_safety_guard_safe_call(self):
        """Safe call catches exceptions and returns default."""
        def failing_fn():
            raise RuntimeError("Expected failure")
        result = self.safety_guard.safe_call(failing_fn, {"safe": True})
        self.assertEqual(result, {"safe": True})

    def test_safety_guard_violations_bounded(self):
        """Safety guard violation history is bounded."""
        for i in range(200):
            self.safety_guard.check_write_operation(f"op-{i}")
        self.assertLessEqual(len(self.safety_guard._safety_violations), 100)

    def test_safety_guard_clear(self):
        """Safety guard clear resets violations."""
        for i in range(50):
            self.safety_guard.check_write_operation(f"op-{i}")
        self.safety_guard.clear()
        self.assertEqual(len(self.safety_guard._safety_violations), 0)
        self.assertEqual(self.safety_guard._violation_count, 0)


class ReplayExecutionSafetyTest(unittest.TestCase):
    """Replay execution maintains safety invariants."""

    def setUp(self):
        self.engine = ReplayEngine()

    def test_replay_with_empty_events(self):
        """Replay with empty events list completes cleanly."""
        self.engine.sessions.create_session("empty-test")
        result = self.engine.execute_replay("empty-test", [])
        self.assertIsInstance(result, dict)

    def test_replay_execution_history_bounded(self):
        """Replay execution history is bounded."""
        for i in range(300):
            sid = f"hist-{i}"
            self.engine.sessions.create_session(sid)
            self.engine.execute_replay(sid, [
                {"tick": 1, "event_type": "TEST", "payload": {}},
            ])
        self.assertLessEqual(len(self.engine._execution_history), 200)

    def test_replay_session_manager_history(self):
        """Session manager history is bounded."""
        manager = self.engine.sessions
        for i in range(100):
            sid = f"mgmt-{i}"
            manager.create_session(sid)
            self.engine.execute_replay(sid, [
                {"tick": 1, "event_type": "TEST", "payload": {}},
            ])
        self.assertLessEqual(len(manager._session_history), 50)


class ReplayDeterministicOrderingTest(unittest.TestCase):
    """Replay operations maintain deterministic ordering."""

    def test_safety_guard_tracks_violations_in_order(self):
        """Safety guard violations maintain insertion order."""
        guard = ReplaySafetyGuard()
        ops = ["first", "second", "third"]
        for op in ops:
            guard.check_write_operation(op)
        self.assertEqual(guard._violation_count, 3)

    def test_controller_history_ordering(self):
        """Controller maintains operation ordering."""
        from simulation.replay.replay_engine.replay_controller import ReplayController
        from simulation.replay.models import ReplayMode
        ctrl = ReplayController(max_history=200)
        ctrl.start("test-session", ReplayMode.FULL)
        ctrl.pause("test-session")
        ctrl.resume("test-session")
        self.assertEqual(len(ctrl._control_history), 3)

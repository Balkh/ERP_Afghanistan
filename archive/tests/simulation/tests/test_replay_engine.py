"""Phase 4B: deterministic tests for replay engine components."""
import unittest

from simulation.replay.replay_engine.replay_session import ReplaySessionManager
from simulation.replay.replay_engine.replay_controller import ReplayController
from simulation.replay.replay_engine.replay_safety_guard import ReplaySafetyGuard
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.replay.models import ReplayMode, ReplayStatus


class TestReplaySessionManager(unittest.TestCase):
    def test_create_session(self):
        mgr = ReplaySessionManager()
        result = mgr.create_session('sess1', ReplayMode.FULL, 0, 100)
        self.assertEqual(result['status'], 'idle')
        self.assertEqual(result['session_id'], 'sess1')

    def test_start_session(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1')
        result = mgr.start_session('sess1')
        self.assertTrue(result['started'])

    def test_start_nonexistent_session(self):
        mgr = ReplaySessionManager()
        result = mgr.start_session('ghost')
        self.assertFalse(result['started'])

    def test_pause_session(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1')
        mgr.start_session('sess1')
        result = mgr.pause_session('sess1')
        self.assertTrue(result['paused'])

    def test_pause_nonexistent_session(self):
        mgr = ReplaySessionManager()
        result = mgr.pause_session('ghost')
        self.assertFalse(result['paused'])

    def test_resume_session(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1')
        mgr.start_session('sess1')
        mgr.pause_session('sess1')
        result = mgr.resume_session('sess1')
        self.assertTrue(result['resumed'])

    def test_complete_session(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1')
        mgr.start_session('sess1')
        result = mgr.complete_session('sess1')
        self.assertTrue(result['completed'])

    def test_fail_session(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1')
        result = mgr.fail_session('sess1', 'test error')
        self.assertTrue(result['failed'])
        self.assertEqual(result['error'], 'test error')

    def test_fail_nonexistent_session(self):
        mgr = ReplaySessionManager()
        result = mgr.fail_session('ghost')
        self.assertFalse(result['failed'])

    def test_get_session(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1', ReplayMode.STEP, 5, 50)
        result = mgr.get_session('sess1')
        self.assertEqual(result['start_tick'], 5)
        self.assertEqual(result['end_tick'], 50)
        self.assertEqual(result['mode'], 'step')

    def test_get_session_nonexistent(self):
        mgr = ReplaySessionManager()
        self.assertIsNone(mgr.get_session('ghost'))

    def test_session_lifecycle(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1')
        mgr.start_session('sess1')
        s = mgr.get_session('sess1')
        self.assertEqual(s['status'], 'running')
        mgr.pause_session('sess1')
        s = mgr.get_session('sess1')
        self.assertTrue(s['is_paused'])
        mgr.resume_session('sess1')
        s = mgr.get_session('sess1')
        self.assertFalse(s['is_paused'])
        mgr.complete_session('sess1')
        s = mgr.get_session('sess1')
        self.assertEqual(s['status'], 'completed')

    def test_clear(self):
        mgr = ReplaySessionManager()
        mgr.create_session('sess1')
        mgr.clear()
        self.assertIsNone(mgr.get_session('sess1'))

    def test_bounded_session_history(self):
        mgr = ReplaySessionManager(max_sessions=2)
        for i in range(5):
            mgr.create_session(f's{i}')
        self.assertIsNotNone(mgr.get_session('s0'))
        self.assertEqual(len(mgr._session_history), 2)


class TestReplayController(unittest.TestCase):
    def test_start(self):
        ctrl = ReplayController()
        result = ctrl.start('sess1')
        self.assertTrue(result['started'])

    def test_start_with_mode(self):
        ctrl = ReplayController()
        result = ctrl.start('sess1', ReplayMode.STEP)
        self.assertEqual(result['mode'], 'step')

    def test_stop(self):
        ctrl = ReplayController()
        result = ctrl.stop('sess1')
        self.assertTrue(result['stopped'])

    def test_pause(self):
        ctrl = ReplayController()
        result = ctrl.pause('sess1')
        self.assertTrue(result['paused'])

    def test_resume(self):
        ctrl = ReplayController()
        result = ctrl.resume('sess1')
        self.assertTrue(result['resumed'])

    def test_step_forward(self):
        ctrl = ReplayController()
        result = ctrl.step_forward('sess1')
        self.assertTrue(result['stepped'])
        self.assertEqual(result['direction'], 'forward')

    def test_step_backward(self):
        ctrl = ReplayController()
        result = ctrl.step_backward('sess1')
        self.assertTrue(result['stepped'])
        self.assertEqual(result['direction'], 'backward')

    def test_clear(self):
        ctrl = ReplayController()
        ctrl.start('sess1')
        ctrl.stop('sess1')
        ctrl.clear()
        self.assertEqual(len(ctrl._control_history), 0)
        self.assertEqual(ctrl._control_count, 0)


class TestReplaySafetyGuard(unittest.TestCase):
    def test_check_write_operation_blocked(self):
        guard = ReplaySafetyGuard()
        result = guard.check_write_operation('test_write')
        self.assertFalse(result['allowed'])
        self.assertIn('blocked', result['reason'])

    def test_check_business_logic_blocked(self):
        guard = ReplaySafetyGuard()
        result = guard.check_business_logic('test_logic')
        self.assertFalse(result['allowed'])
        self.assertIn('blocked', result['reason'])

    def test_safe_call_success(self):
        guard = ReplaySafetyGuard()
        result = guard.safe_call(lambda x: x + 1, -1, 5)
        self.assertEqual(result, 6)

    def test_safe_call_exception(self):
        guard = ReplaySafetyGuard()
        def failing():
            raise ValueError('test error')
        result = guard.safe_call(failing, default_return='fallback')
        self.assertEqual(result, 'fallback')

    def test_get_violation_count(self):
        guard = ReplaySafetyGuard()
        self.assertEqual(guard.get_violation_count(), 0)
        guard.check_write_operation('op1')
        guard.check_business_logic('logic1')
        self.assertEqual(guard.get_violation_count(), 2)

    def test_safe_call_increments_violation_on_error(self):
        guard = ReplaySafetyGuard()
        def failing():
            raise RuntimeError('err')
        guard.safe_call(failing)
        self.assertEqual(guard.get_violation_count(), 1)

    def test_clear(self):
        guard = ReplaySafetyGuard()
        guard.check_write_operation('op1')
        guard.clear()
        self.assertEqual(guard.get_violation_count(), 0)
        self.assertEqual(len(guard._safety_violations), 0)

    def test_safe_call_nested(self):
        guard = ReplaySafetyGuard()
        inner = guard.safe_call(lambda: {'key': 'val'}, default_return={})
        self.assertEqual(inner['key'], 'val')


class TestReplayEngine(unittest.TestCase):
    def test_execute_replay_blocked_by_safety(self):
        eng = ReplayEngine()
        eng.sessions.create_session('sess1', ReplayMode.FULL, 0, 10)
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'test', 'source': 'src'},
        ]
        result = eng.execute_replay('sess1', events)
        self.assertFalse(result['executed'])
        self.assertEqual(result['reason'], 'Write blocked during replay')

    def test_execute_replay_session_not_found(self):
        eng = ReplayEngine()
        result = eng.execute_replay('ghost', [])
        self.assertFalse(result['executed'])

    def test_execute_replay_multiple_events_blocked(self):
        eng = ReplayEngine()
        eng.sessions.create_session('sess1', ReplayMode.FULL, 0, 10)
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'b', 'source': 's'},
            {'event_id': 'e3', 'tick': 3, 'event_type': 'c', 'source': 's'},
        ]
        result = eng.execute_replay('sess1', events)
        self.assertFalse(result['executed'])

    def test_execute_replay_updates_session_failed(self):
        eng = ReplayEngine()
        eng.sessions.create_session('sess1')
        eng.execute_replay('sess1', [
            {'event_id': 'e1', 'tick': 1, 'event_type': 't', 'source': 's'},
        ])
        session = eng.sessions.get_session('sess1')
        self.assertEqual(session['status'], 'failed')

    def test_engine_properties(self):
        eng = ReplayEngine()
        self.assertIsNotNone(eng.sessions)
        self.assertIsNotNone(eng.controller)
        self.assertIsNotNone(eng.safety_guard)

    def test_clear(self):
        eng = ReplayEngine()
        eng.sessions.create_session('sess1')
        eng.clear()
        self.assertIsNone(eng.sessions.get_session('sess1'))

    def test_execute_replay_empty_events_succeeds(self):
        eng = ReplayEngine()
        eng.sessions.create_session('sess1')
        result = eng.execute_replay('sess1', [])
        self.assertTrue(result['executed'])
        self.assertEqual(result['events_replayed'], 0)


if __name__ == '__main__':
    unittest.main()

"""Phase 4B: integration tests for replay orchestration components."""
import unittest

from simulation.replay.orchestration.replay_orchestrator import ReplayOrchestrator
from simulation.replay.orchestration.replay_pipeline import ReplayPipeline
from simulation.replay.orchestration.replay_router import ReplayRouter
from simulation.replay.models import ReplayMode


class TestReplayPipeline(unittest.TestCase):
    def test_pipeline_initialization(self):
        p = ReplayPipeline('p1', ['build', 'validate', 'replay'])
        self.assertEqual(p.pipeline_id, 'p1')
        self.assertEqual(p.current_step, 0)
        self.assertFalse(p.is_running)
        self.assertFalse(p.is_complete)
        self.assertFalse(p.has_failed)

    def test_start_pipeline(self):
        p = ReplayPipeline('p1', ['step1', 'step2'])
        result = p.start()
        self.assertTrue(result['started'])
        self.assertTrue(p.is_running)

    def test_start_pipeline_no_steps(self):
        p = ReplayPipeline('p1', [])
        result = p.start()
        self.assertFalse(result['started'])

    def test_advance_pipeline(self):
        p = ReplayPipeline('p1', ['step1', 'step2'])
        p.start()
        result = p.advance()
        self.assertTrue(result['advanced'])
        self.assertEqual(result['step_name'], 'step1')
        self.assertEqual(p.current_step, 1)

    def test_advance_completes_pipeline(self):
        p = ReplayPipeline('p1', ['step1'])
        p.start()
        result = p.advance()
        self.assertTrue(result['complete'])
        self.assertFalse(p.is_running)
        self.assertTrue(p.is_complete)

    def test_advance_not_running(self):
        p = ReplayPipeline('p1', ['step1'])
        result = p.advance()
        self.assertFalse(result['advanced'])

    def test_fail_pipeline(self):
        p = ReplayPipeline('p1', ['step1'])
        p.start()
        result = p.fail('critical error')
        self.assertTrue(result['failed'])
        self.assertTrue(p.has_failed)
        self.assertFalse(p.is_running)

    def test_reset_pipeline(self):
        p = ReplayPipeline('p1', ['step1'])
        p.start()
        p.advance()
        p.reset()
        self.assertEqual(p.current_step, 0)
        self.assertFalse(p.is_running)
        self.assertFalse(p.is_complete)
        self.assertFalse(p.has_failed)

    def test_get_status(self):
        p = ReplayPipeline('p1', ['a', 'b', 'c'])
        status = p.get_status()
        self.assertEqual(status['total_steps'], 3)
        self.assertEqual(status['current_step'], 0)
        self.assertFalse(status['is_running'])

    def test_multiple_advances(self):
        p = ReplayPipeline('p1', ['a', 'b', 'c'])
        p.start()
        p.advance()
        p.advance()
        p.advance()
        self.assertTrue(p.is_complete)
        self.assertEqual(p.current_step, 3)

    def test_advance_after_complete(self):
        p = ReplayPipeline('p1', ['a'])
        p.start()
        p.advance()
        result = p.advance()
        self.assertFalse(result['advanced'])

    def test_pipeline_id_immutable(self):
        p = ReplayPipeline('fixed_id', ['a'])
        self.assertEqual(p.pipeline_id, 'fixed_id')


class TestReplayRouter(unittest.TestCase):
    def test_route_replay_full(self):
        r = ReplayRouter()
        result = r.route_replay(ReplayMode.FULL, 'sess1', [])
        self.assertEqual(result['mode'], 'full')
        self.assertEqual(result['strategy'], 'process_all')

    def test_route_replay_step(self):
        r = ReplayRouter()
        result = r.route_replay(ReplayMode.STEP, 'sess1', [])
        self.assertEqual(result['strategy'], 'process_step')

    def test_route_replay_window(self):
        r = ReplayRouter()
        result = r.route_replay(ReplayMode.WINDOW, 'sess1', [])
        self.assertEqual(result['strategy'], 'process_window')

    def test_route_replay_bookmark(self):
        r = ReplayRouter()
        result = r.route_replay(ReplayMode.BOOKMARK, 'sess1', [])
        self.assertEqual(result['strategy'], 'process_bookmark')

    def test_get_route_count(self):
        r = ReplayRouter()
        self.assertEqual(r.get_route_count(), 0)
        r.route_replay(ReplayMode.FULL, 's1', [])
        self.assertEqual(r.get_route_count(), 1)

    def test_route_replay_includes_session(self):
        r = ReplayRouter()
        result = r.route_replay(ReplayMode.FULL, 'my_session', [{'e1': 1}])
        self.assertEqual(result['session_id'], 'my_session')

    def test_clear(self):
        r = ReplayRouter()
        r.route_replay(ReplayMode.FULL, 's1', [])
        r.clear()
        self.assertEqual(r.get_route_count(), 0)


class TestReplayOrchestratorIntegration(unittest.TestCase):
    def test_orchestrator_initialization(self):
        orch = ReplayOrchestrator()
        self.assertIsNotNone(orch.timeline_builder)
        self.assertIsNotNone(orch.timeline_indexer)
        self.assertIsNotNone(orch.timeline_cursor)
        self.assertIsNotNone(orch.timeline_validator)
        self.assertIsNotNone(orch.snapshot_loader)
        self.assertIsNotNone(orch.snapshot_reconstructor)
        self.assertIsNotNone(orch.snapshot_integrity)
        self.assertIsNotNone(orch.snapshot_history)
        self.assertIsNotNone(orch.replay_engine)
        self.assertIsNotNone(orch.workflow_reconstructor)
        self.assertIsNotNone(orch.event_chain)
        self.assertIsNotNone(orch.incident_reconstructor)
        self.assertIsNotNone(orch.state_reconstructor)
        self.assertIsNotNone(orch.time_travel)
        self.assertIsNotNone(orch.navigation)
        self.assertIsNotNone(orch.bookmarks)
        self.assertIsNotNone(orch.windows)
        self.assertIsNotNone(orch.forensic_analyzer)
        self.assertIsNotNone(orch.incident_forensics)
        self.assertIsNotNone(orch.causal_forensics)
        self.assertIsNotNone(orch.evidence)
        self.assertIsNotNone(orch.determinism)
        self.assertIsNotNone(orch.consistency)
        self.assertIsNotNone(orch.divergence)
        self.assertIsNotNone(orch.replay_validator)
        self.assertIsNotNone(orch.snapshot_validator)
        self.assertIsNotNone(orch.timeline_integrity)
        self.assertIsNotNone(orch.causal_integrity)
        self.assertIsNotNone(orch.router)

    def test_run_replay_full(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'start',
             'source': 'sys', 'description': 'started'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'step',
             'source': 'sys', 'description': 'processing'},
            {'event_id': 'e3', 'tick': 3, 'event_type': 'end',
             'source': 'sys', 'description': 'completed'},
        ]
        result = orch.run_replay('sess_int', events, ReplayMode.FULL)
        self.assertFalse(result['executed'])
        self.assertEqual(result['events_replayed'], 3)
        self.assertEqual(result['session_id'], 'sess_int')

    def test_run_replay_mode_step(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'},
        ]
        result = orch.run_replay('sess_step', events, ReplayMode.STEP)
        self.assertFalse(result['executed'])
        self.assertEqual(result['routing']['mode'], 'step')

    def test_run_replay_mode_window(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'},
        ]
        result = orch.run_replay('sess_win', events, ReplayMode.WINDOW)
        self.assertEqual(result['routing']['mode'], 'window')

    def test_run_replay_mode_bookmark(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'},
        ]
        result = orch.run_replay('sess_bm', events, ReplayMode.BOOKMARK)
        self.assertEqual(result['routing']['mode'], 'bookmark')

    def test_run_replay_empty_events(self):
        orch = ReplayOrchestrator()
        result = orch.run_replay('sess_empty', [], ReplayMode.FULL)
        self.assertTrue(result['executed'])
        self.assertEqual(result['events_replayed'], 0)

    def test_run_replay_builds_timeline(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'test',
             'source': 'src', 'description': 'd',
             'payload': {'k': 'v'}, 'causal_parent': None},
        ]
        orch.run_replay('sess_tl', events)
        tl_events = orch.timeline_builder.get_events()
        self.assertEqual(len(tl_events), 1)
        self.assertEqual(tl_events[0]['event_id'], 'ev_1_1')

    def test_run_replay_indexes_events(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'test',
             'source': 'src'},
        ]
        orch.run_replay('sess_idx', events)
        by_tick = orch.timeline_indexer.get_events_by_tick(1)
        self.assertIn('e1', by_tick)

    def test_run_replay_creates_session(self):
        orch = ReplayOrchestrator()
        orch.run_replay('sess_check', [
            {'event_id': 'e1', 'tick': 1, 'event_type': 't', 'source': 's'},
        ])
        session = orch.replay_engine.sessions.get_session('sess_check')
        self.assertIsNotNone(session)
        self.assertEqual(session['status'], 'failed')

    def test_run_replay_updates_session_tick_range(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'},
            {'event_id': 'e2', 'tick': 5, 'event_type': 'b', 'source': 's'},
        ]
        orch.run_replay('sess_range', events)
        session = orch.replay_engine.sessions.get_session('sess_range')
        self.assertEqual(session['end_tick'], 5)

    def test_reset_clears_all_components(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'},
        ]
        orch.run_replay('sess_reset', events)
        self.assertEqual(orch.timeline_builder.get_event_count(), 1)
        orch.reset()
        self.assertEqual(orch.timeline_builder.get_event_count(), 0)
        self.assertIsNone(
            orch.replay_engine.sessions.get_session('sess_reset'))

    def test_multiple_replays_increment_count(self):
        orch = ReplayOrchestrator()
        e = [{'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'}]
        r1 = orch.run_replay('s1', e)
        r2 = orch.run_replay('s2', e)
        self.assertNotEqual(r1['replay_id'], r2['replay_id'])

    def test_run_replay_with_causal_parent(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'start',
             'source': 'wf', 'causal_parent': None},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'step',
             'source': 'wf', 'causal_parent': 'e1'},
        ]
        result = orch.run_replay('sess_causal', events)
        self.assertFalse(result['executed'])
        self.assertEqual(result['events_replayed'], 2)

    def test_full_replay_report_structure(self):
        orch = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 't', 'source': 's'},
        ]
        result = orch.run_replay('sess_rpt', events)
        self.assertIn('replay_id', result)
        self.assertIn('session_id', result)
        self.assertIn('executed', result)
        self.assertIn('events_replayed', result)
        self.assertIn('routing', result)
        self.assertIn('session', result)

    def test_run_replay_deterministic_same_inputs(self):
        orch1 = ReplayOrchestrator()
        orch2 = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'test', 'source': 's'},
        ]
        r1 = orch1.run_replay('sa', events)
        r2 = orch2.run_replay('sb', events)
        self.assertEqual(r1['executed'], r2['executed'])
        self.assertEqual(r1['events_replayed'], r2['events_replayed'])
        self.assertFalse(r1['executed'])


if __name__ == '__main__':
    unittest.main()

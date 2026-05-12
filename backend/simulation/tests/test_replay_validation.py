"""Phase 4B: deterministic tests for replay validation components."""
import unittest

from simulation.replay.validation.replay_validator import ReplayValidator
from simulation.replay.validation.snapshot_validator import SnapshotValidator
from simulation.replay.validation.timeline_integrity import TimelineIntegrity
from simulation.replay.validation.causal_integrity import CausalIntegrity
from simulation.replay.models import TimelineDirection


class TestReplayValidator(unittest.TestCase):
    def test_validate_session_valid(self):
        rv = ReplayValidator()
        session = {
            'status': 'completed',
            'start_tick': 0,
            'end_tick': 100,
        }
        events = [{'event_id': 'e1'}]
        result = rv.validate_session(session, events)
        self.assertTrue(result['is_valid'])

    def test_validate_session_no_events(self):
        rv = ReplayValidator()
        session = {
            'status': 'completed',
            'start_tick': 0,
            'end_tick': 100,
        }
        result = rv.validate_session(session, [])
        self.assertFalse(result['is_valid'])
        self.assertIn('No events', result['issues'][0])

    def test_validate_session_invalid_range(self):
        rv = ReplayValidator()
        session = {
            'status': 'completed',
            'start_tick': 100,
            'end_tick': 0,
        }
        events = [{'event_id': 'e1'}]
        result = rv.validate_session(session, events)
        self.assertFalse(result['is_valid'])

    def test_validate_session_invalid_status(self):
        rv = ReplayValidator()
        session = {
            'status': 'running',
            'start_tick': 0,
            'end_tick': 100,
        }
        events = [{'event_id': 'e1'}]
        result = rv.validate_session(session, events)
        self.assertTrue(result['is_valid'])

    def test_validate_session_bad_status(self):
        rv = ReplayValidator()
        session = {
            'status': 'unknown_status',
            'start_tick': 0,
            'end_tick': 100,
        }
        events = [{'event_id': 'e1'}]
        result = rv.validate_session(session, events)
        self.assertFalse(result['is_valid'])

    def test_validate_results_valid(self):
        rv = ReplayValidator()
        result = rv.validate_results({'executed': True, 'session_id': 's1'})
        self.assertTrue(result['is_valid'])
        self.assertTrue(result['executed'])

    def test_validate_results_not_executed(self):
        rv = ReplayValidator()
        result = rv.validate_results({'executed': False, 'session_id': None})
        self.assertFalse(result['is_valid'])

    def test_validate_results_no_session(self):
        rv = ReplayValidator()
        result = rv.validate_results({'executed': True, 'session_id': None})
        self.assertFalse(result['is_valid'])

    def test_clear(self):
        rv = ReplayValidator()
        rv.validate_session(
            {'status': 'completed', 'start_tick': 0, 'end_tick': 10},
            [{'event_id': 'e1'}])
        rv.clear()
        self.assertEqual(len(rv._validation_history), 0)

    def test_validate_session_empty_session(self):
        rv = ReplayValidator()
        result = rv.validate_session({}, [])
        self.assertFalse(result['is_valid'])


class TestSnapshotValidator(unittest.TestCase):
    def test_validate_snapshot_valid(self):
        sv = SnapshotValidator()
        snapshot = {
            'snapshot_id': 's1',
            'tick': 10,
            'workflow_states': {'wf': 'ok'},
            'event_count': 5,
        }
        result = sv.validate_snapshot(snapshot)
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['status'], 'intact')

    def test_validate_snapshot_missing_id(self):
        sv = SnapshotValidator()
        snapshot = {
            'tick': 10,
            'workflow_states': {'wf': 'ok'},
        }
        result = sv.validate_snapshot(snapshot)
        self.assertFalse(result['is_valid'])
        self.assertIn('Missing snapshot_id', result['issues'])

    def test_validate_snapshot_missing_tick(self):
        sv = SnapshotValidator()
        snapshot = {
            'snapshot_id': 's1',
            'workflow_states': {'wf': 'ok'},
        }
        result = sv.validate_snapshot(snapshot)
        self.assertFalse(result['is_valid'])
        self.assertIn('Missing tick', result['issues'])

    def test_validate_snapshot_missing_workflows(self):
        sv = SnapshotValidator()
        snapshot = {
            'snapshot_id': 's1',
            'tick': 10,
            'workflow_states': {},
        }
        result = sv.validate_snapshot(snapshot)
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['status'], 'corrupted')

    def test_validate_snapshot_list(self):
        sv = SnapshotValidator()
        snapshots = [
            {'snapshot_id': 's1', 'tick': 1, 'workflow_states': {'w': 'ok'}},
            {'snapshot_id': 's2', 'tick': 2, 'workflow_states': {'w': 'ok'}},
        ]
        results = sv.validate_snapshot_list(snapshots)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r['is_valid'] for r in results))

    def test_clear(self):
        sv = SnapshotValidator()
        sv.validate_snapshot(
            {'snapshot_id': 's1', 'tick': 1, 'workflow_states': {'w': 'ok'}})
        sv.clear()
        self.assertEqual(len(sv._validation_history), 0)

    def test_validate_snapshot_tick_zero_valid(self):
        sv = SnapshotValidator()
        snapshot = {
            'snapshot_id': 's1',
            'tick': 0,
            'workflow_states': {'wf': 'ok'},
        }
        result = sv.validate_snapshot(snapshot)
        self.assertTrue(result['is_valid'])


class TestTimelineIntegrity(unittest.TestCase):
    def test_check_ordering_ordered(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
        ]
        result = ti.check_ordering(events)
        self.assertTrue(result['is_ordered'])

    def test_check_ordering_unordered(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e1', 'tick': 3},
            {'event_id': 'e2', 'tick': 1},
        ]
        result = ti.check_ordering(events)
        self.assertFalse(result['is_ordered'])

    def test_check_ordering_negative_tick(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e1', 'tick': -1},
            {'event_id': 'e2', 'tick': 1},
        ]
        result = ti.check_ordering(events)
        self.assertFalse(result['has_no_negative_ticks'])

    def test_check_contiguity_contiguous(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
            {'event_id': 'e3', 'tick': 3},
        ]
        result = ti.check_contiguity(events)
        self.assertTrue(result['is_contiguous'])

    def test_check_contiguity_with_gaps(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
        ]
        result = ti.check_contiguity(events)
        self.assertFalse(result['is_contiguous'])
        self.assertEqual(len(result['gaps']), 1)

    def test_check_contiguity_empty(self):
        ti = TimelineIntegrity()
        result = ti.check_contiguity([])
        self.assertTrue(result['is_contiguous'])

    def test_check_direction_forward(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
        ]
        result = ti.check_direction(events, TimelineDirection.FORWARD)
        self.assertTrue(result['is_correct_direction'])

    def test_check_direction_backward(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e2', 'tick': 5},
            {'event_id': 'e1', 'tick': 1},
        ]
        result = ti.check_direction(events, TimelineDirection.BACKWARD)
        self.assertTrue(result['is_correct_direction'])

    def test_check_direction_wrong(self):
        ti = TimelineIntegrity()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
        ]
        result = ti.check_direction(events, TimelineDirection.BACKWARD)
        self.assertFalse(result['is_correct_direction'])

    def test_check_direction_single_event(self):
        ti = TimelineIntegrity()
        result = ti.check_direction(
            [{'event_id': 'e1', 'tick': 1}], TimelineDirection.FORWARD)
        self.assertTrue(result['is_correct_direction'])

    def test_clear(self):
        ti = TimelineIntegrity()
        ti.check_ordering([{'event_id': 'e1', 'tick': 1}])
        ti.clear()
        self.assertEqual(len(ti._integrity_history), 0)

    def test_check_direction_empty(self):
        ti = TimelineIntegrity()
        result = ti.check_direction([], TimelineDirection.FORWARD)
        self.assertTrue(result['is_correct_direction'])


class TestCausalIntegrity(unittest.TestCase):
    def test_check_chain_integrity_intact(self):
        ci = CausalIntegrity()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'e1'},
        ]
        result = ci.check_chain_integrity(events)
        self.assertTrue(result['chain_integrity'])

    def test_check_chain_integrity_broken(self):
        ci = CausalIntegrity()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'missing_parent'},
        ]
        result = ci.check_chain_integrity(events)
        self.assertFalse(result['chain_integrity'])
        self.assertEqual(len(result['broken_links']), 1)

    def test_check_chain_integrity_empty(self):
        ci = CausalIntegrity()
        result = ci.check_chain_integrity([])
        self.assertTrue(result['chain_integrity'])

    def test_check_chain_integrity_single_event(self):
        ci = CausalIntegrity()
        result = ci.check_chain_integrity(
            [{'event_id': 'e1', 'causal_parent': None}])
        self.assertTrue(result['chain_integrity'])

    def test_verify_chain_completeness_complete(self):
        ci = CausalIntegrity()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e2'},
        ]
        result = ci.verify_chain_completeness(events, 'e1')
        self.assertTrue(result['is_complete'])

    def test_verify_chain_completeness_empty(self):
        ci = CausalIntegrity()
        result = ci.verify_chain_completeness([], 'unknown')
        self.assertFalse(result['is_complete'])

    def test_verify_chain_completeness_single_root(self):
        ci = CausalIntegrity()
        events = [{'event_id': 'e1', 'causal_parent': None}]
        result = ci.verify_chain_completeness(events, 'e1')
        self.assertTrue(result['is_complete'])

    def test_clear(self):
        ci = CausalIntegrity()
        ci.check_chain_integrity(
            [{'event_id': 'e1', 'causal_parent': None}])
        ci.clear()
        self.assertEqual(len(ci._integrity_history), 0)

    def test_verify_chain_completeness_bounded_at_100(self):
        ci = CausalIntegrity()
        events = []
        for i in range(150):
            parent = f'e{i - 1}' if i > 0 else None
            events.append({'event_id': f'e{i}', 'causal_parent': parent})
        result = ci.verify_chain_completeness(events, 'e0')
        self.assertLessEqual(result['events_in_chain'], 101)


if __name__ == '__main__':
    unittest.main()

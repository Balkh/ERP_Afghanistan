"""Phase 4B: deterministic tests for replay reconstruction components."""
import unittest

from simulation.replay.reconstruction.workflow_reconstructor import WorkflowReconstructor
from simulation.replay.reconstruction.event_chain_builder import EventChainBuilder
from simulation.replay.reconstruction.incident_reconstructor import IncidentReconstructor
from simulation.replay.reconstruction.state_reconstructor import StateReconstructor


class TestWorkflowReconstructor(unittest.TestCase):
    def test_reconstruct_empty_events(self):
        wr = WorkflowReconstructor()
        result = wr.reconstruct('wf1', events=[])
        self.assertEqual(result['workflow_id'], 'wf1')
        self.assertEqual(result['total_steps'], 0)
        self.assertEqual(result['final_state'], 'initialized')

    def test_reconstruct_with_matching_events(self):
        wr = WorkflowReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'wf1', 'description': 'start'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'workflow_completed',
             'source': 'wf1', 'description': 'done'},
        ]
        result = wr.reconstruct('wf1', events=events)
        self.assertEqual(result['total_steps'], 2)
        self.assertEqual(result['final_state'], 'completed')

    def test_reconstruct_tracks_failed_state(self):
        wr = WorkflowReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'wf1'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'workflow_failed',
             'source': 'wf1'},
        ]
        result = wr.reconstruct('wf1', events=events)
        self.assertEqual(result['final_state'], 'failed')

    def test_reconstruct_with_workflow_id_in_payload(self):
        wr = WorkflowReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'other', 'payload': {'workflow_id': 'wf1'}},
        ]
        result = wr.reconstruct('wf1', events=events)
        self.assertEqual(result['total_steps'], 1)

    def test_reconstruct_non_matching_events(self):
        wr = WorkflowReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'wf_other'},
        ]
        result = wr.reconstruct('wf1', events=events)
        self.assertEqual(result['total_steps'], 0)

    def test_get_reconstruction_count(self):
        wr = WorkflowReconstructor()
        self.assertEqual(wr.get_reconstruction_count(), 0)
        wr.reconstruct('wf1', events=[])
        self.assertEqual(wr.get_reconstruction_count(), 1)

    def test_clear(self):
        wr = WorkflowReconstructor()
        wr.reconstruct('wf1', events=[])
        wr.clear()
        self.assertEqual(wr.get_reconstruction_count(), 0)

    def test_reconstruct_with_workflow_type(self):
        wr = WorkflowReconstructor()
        result = wr.reconstruct('wf1', events=[], workflow_type='sales')
        self.assertEqual(result['workflow_type'], 'sales')

    def test_reconstruct_multiple_calls(self):
        wr = WorkflowReconstructor()
        wr.reconstruct('wf1', events=[])
        wr.reconstruct('wf2', events=[])
        self.assertEqual(wr.get_reconstruction_count(), 2)


class TestEventChainBuilder(unittest.TestCase):
    def test_build_chain_empty_events(self):
        cb = EventChainBuilder()
        result = cb.build_chain([])
        self.assertEqual(result['length'], 0)

    def test_build_chain_via_parents(self):
        cb = EventChainBuilder()
        events = [
            {'event_id': 'e3', 'causal_parent': 'e2'},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e1', 'causal_parent': None},
        ]
        result = cb.build_chain(events)
        self.assertEqual(result['length'], 3)

    def test_build_chain_with_start_event(self):
        cb = EventChainBuilder()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e2'},
        ]
        result = cb.build_chain(events, start_event_id='e2')
        self.assertEqual(result['start_event'], 'e2')

    def test_build_chain_cycle_detection(self):
        cb = EventChainBuilder()
        events = [
            {'event_id': 'e1', 'causal_parent': 'e3'},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e2'},
        ]
        result = cb.build_chain(events, start_event_id='e1')
        self.assertLessEqual(result['length'], 3)

    def test_build_downstream_chain(self):
        cb = EventChainBuilder()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e1'},
            {'event_id': 'e4', 'causal_parent': 'e2'},
        ]
        result = cb.build_downstream_chain(events, 'e1')
        self.assertEqual(result['length'], 4)

    def test_build_downstream_chain_unknown_start(self):
        cb = EventChainBuilder()
        events = [{'event_id': 'e1', 'causal_parent': None}]
        result = cb.build_downstream_chain(events, 'unknown')
        self.assertEqual(result['length'], 0)

    def test_build_chain_bounded_at_100(self):
        cb = EventChainBuilder()
        events = []
        for i in range(150):
            parent = f'e{i - 1}' if i > 0 else None
            events.append({'event_id': f'e{i}', 'causal_parent': parent})
        result = cb.build_chain(events)
        self.assertLessEqual(result['length'], 101)

    def test_clear(self):
        cb = EventChainBuilder()
        cb.build_chain([{'event_id': 'e1', 'causal_parent': None}])
        cb.clear()
        self.assertEqual(len(cb._chains), 0)

    def test_build_chain_single_event(self):
        cb = EventChainBuilder()
        result = cb.build_chain([{'event_id': 'e1', 'causal_parent': None}])
        self.assertEqual(result['length'], 1)

    def test_build_downstream_bounded(self):
        cb = EventChainBuilder()
        events = [{'event_id': f'e{i}', 'causal_parent': f'e{i-1}' if i > 0 else None}
                  for i in range(150)]
        result = cb.build_downstream_chain(events, 'e0')
        self.assertLessEqual(result['length'], 100)


class TestIncidentReconstructor(unittest.TestCase):
    def test_reconstruct_empty_events(self):
        ir = IncidentReconstructor()
        result = ir.reconstruct('inc1', events=[])
        self.assertEqual(result['incident_id'], 'inc1')
        self.assertEqual(result['total_related'], 0)

    def test_reconstruct_with_trigger(self):
        ir = IncidentReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'normal'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'error_timeout'},
        ]
        result = ir.reconstruct('inc1', events=events, trigger_event_id='e2')
        self.assertIsNotNone(result['trigger_event'])
        self.assertEqual(result['trigger_event']['event_id'], 'e2')

    def test_reconstruct_finds_error_events(self):
        ir = IncidentReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'normal'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'error_timeout'},
            {'event_id': 'e3', 'tick': 3, 'event_type': 'failure_disk'},
            {'event_id': 'e4', 'tick': 4, 'event_type': 'incident_report'},
        ]
        result = ir.reconstruct('inc1', events=events)
        self.assertEqual(result['total_related'], 3)

    def test_reconstruct_trigger_not_found(self):
        ir = IncidentReconstructor()
        events = [{'event_id': 'e1', 'tick': 1, 'event_type': 'normal'}]
        result = ir.reconstruct('inc1', events=events, trigger_event_id='ghost')
        self.assertIsNone(result['trigger_event'])

    def test_get_reconstruction_count(self):
        ir = IncidentReconstructor()
        self.assertEqual(ir.get_reconstruction_count(), 0)
        ir.reconstruct('inc1', events=[])
        self.assertEqual(ir.get_reconstruction_count(), 1)

    def test_clear(self):
        ir = IncidentReconstructor()
        ir.reconstruct('inc1', events=[])
        ir.clear()
        self.assertEqual(ir.get_reconstruction_count(), 0)

    def test_reconstruct_no_error_events(self):
        ir = IncidentReconstructor()
        events = [
            {'event_id': 'e1', 'event_type': 'info'},
            {'event_id': 'e2', 'event_type': 'debug'},
        ]
        result = ir.reconstruct('inc1', events=events)
        self.assertEqual(result['total_related'], 0)


class TestStateReconstructor(unittest.TestCase):
    def test_reconstruct_at_tick(self):
        sr = StateReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'wf_a'},
            {'event_id': 'e2', 'tick': 3, 'event_type': 'workflow_completed',
             'source': 'wf_a'},
            {'event_id': 'e3', 'tick': 5, 'event_type': 'workflow_started',
             'source': 'wf_b'},
        ]
        result = sr.reconstruct_at_tick(4, events)
        self.assertEqual(result['target_tick'], 4)
        self.assertEqual(result['total_events_processed'], 2)
        self.assertEqual(result['workflow_states']['wf_a'], 'completed')
        self.assertNotIn('wf_b', result['workflow_states'])

    def test_reconstruct_at_tick_all_events(self):
        sr = StateReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'wf_x'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'workflow_started',
             'source': 'wf_y'},
        ]
        result = sr.reconstruct_at_tick(10, events)
        self.assertEqual(result['total_events_processed'], 2)

    def test_reconstruct_at_tick_no_events(self):
        sr = StateReconstructor()
        result = sr.reconstruct_at_tick(5, [])
        self.assertEqual(result['total_events_processed'], 0)

    def test_reconstruct_tracks_workflow_states(self):
        sr = StateReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'wf_a'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'workflow_failed',
             'source': 'wf_a'},
        ]
        result = sr.reconstruct_at_tick(5, events)
        self.assertEqual(result['workflow_states']['wf_a'], 'failed')

    def test_reconstruct_counts_active_workflows(self):
        sr = StateReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
             'source': 'wf_a'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'workflow_started',
             'source': 'wf_b'},
            {'event_id': 'e3', 'tick': 3, 'event_type': 'workflow_completed',
             'source': 'wf_a'},
        ]
        result = sr.reconstruct_at_tick(10, events)
        self.assertEqual(result['active_workflows'], 1)

    def test_get_reconstruction_count(self):
        sr = StateReconstructor()
        self.assertEqual(sr.get_reconstruction_count(), 0)
        sr.reconstruct_at_tick(1, [])
        self.assertEqual(sr.get_reconstruction_count(), 1)

    def test_clear(self):
        sr = StateReconstructor()
        sr.reconstruct_at_tick(1, [])
        sr.clear()
        self.assertEqual(sr.get_reconstruction_count(), 0)

    def test_reconstruct_irrelevant_events_excluded(self):
        sr = StateReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 10, 'event_type': 'workflow_started',
             'source': 'wf_a'},
        ]
        result = sr.reconstruct_at_tick(5, events)
        self.assertEqual(result['total_events_processed'], 0)

    def test_reconstruct_event_counts(self):
        sr = StateReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 'wf_x'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'b', 'source': 'wf_x'},
            {'event_id': 'e3', 'tick': 3, 'event_type': 'c', 'source': 'wf_y'},
        ]
        result = sr.reconstruct_at_tick(5, events)
        self.assertEqual(result['event_counts']['wf_x'], 2)
        self.assertEqual(result['event_counts']['wf_y'], 1)


if __name__ == '__main__':
    unittest.main()

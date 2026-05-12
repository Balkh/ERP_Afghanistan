"""Phase 4B: deterministic tests for replay timeline components."""
import unittest

from simulation.replay.timeline.timeline_builder import TimelineBuilder
from simulation.replay.timeline.timeline_indexer import TimelineIndexer
from simulation.replay.timeline.timeline_cursor import TimelineCursorManager
from simulation.replay.timeline.timeline_validator import TimelineValidator
from simulation.replay.models import TimelineDirection


class TestTimelineBuilder(unittest.TestCase):
    def test_add_event_returns_id(self):
        tb = TimelineBuilder()
        eid = tb.add_event(1, 'test_event', 'test_source')
        self.assertTrue(eid.startswith('ev_'))

    def test_get_events_returns_list(self):
        tb = TimelineBuilder()
        tb.add_event(1, 'type_a', 'src_a')
        tb.add_event(2, 'type_b', 'src_b')
        events = tb.get_events()
        self.assertEqual(len(events), 2)

    def test_get_events_since_tick_filters(self):
        tb = TimelineBuilder()
        tb.add_event(1, 'a', 's1')
        tb.add_event(3, 'b', 's2')
        tb.add_event(5, 'c', 's3')
        events = tb.get_events(since_tick=3)
        self.assertEqual(len(events), 2)

    def test_get_events_until_tick_filters(self):
        tb = TimelineBuilder()
        tb.add_event(1, 'a', 's1')
        tb.add_event(3, 'b', 's2')
        tb.add_event(5, 'c', 's3')
        events = tb.get_events(until_tick=3)
        self.assertEqual(len(events), 2)

    def test_get_events_range_filters(self):
        tb = TimelineBuilder()
        tb.add_event(1, 'a', 's1')
        tb.add_event(3, 'b', 's2')
        tb.add_event(5, 'c', 's3')
        events = tb.get_events(since_tick=2, until_tick=4)
        self.assertEqual(len(events), 1)

    def test_get_event_count(self):
        tb = TimelineBuilder()
        self.assertEqual(tb.get_event_count(), 0)
        tb.add_event(1, 'a', 's1')
        self.assertEqual(tb.get_event_count(), 1)
        tb.add_event(2, 'b', 's2')
        self.assertEqual(tb.get_event_count(), 2)

    def test_clear_removes_all_events(self):
        tb = TimelineBuilder()
        tb.add_event(1, 'a', 's1')
        tb.add_event(2, 'b', 's2')
        tb.clear()
        self.assertEqual(tb.get_event_count(), 0)
        self.assertEqual(tb.get_events(), [])

    def test_bounded_maxlen(self):
        tb = TimelineBuilder(max_events=3)
        for i in range(5):
            tb.add_event(i, 't', 's')
        self.assertEqual(tb.get_event_count(), 3)

    def test_payload_stored_correctly(self):
        tb = TimelineBuilder()
        eid = tb.add_event(1, 't', 's', payload={'key': 'val'})
        events = tb.get_events()
        self.assertEqual(events[0]['payload']['key'], 'val')

    def test_causal_parent_stored(self):
        tb = TimelineBuilder()
        eid = tb.add_event(2, 't', 's', causal_parent='parent_1')
        events = tb.get_events()
        self.assertEqual(events[0]['causal_parent'], 'parent_1')


class TestTimelineIndexer(unittest.TestCase):
    def test_index_event_by_tick(self):
        idx = TimelineIndexer()
        idx.index_event('e1', 5, 'type_a', 'src_a')
        result = idx.get_events_by_tick(5)
        self.assertEqual(result, ['e1'])

    def test_index_event_by_type(self):
        idx = TimelineIndexer()
        idx.index_event('e1', 1, 'error', 'src_a')
        result = idx.get_events_by_type('error')
        self.assertEqual(result, ['e1'])

    def test_index_event_by_source(self):
        idx = TimelineIndexer()
        idx.index_event('e1', 1, 't', 'system_a')
        result = idx.get_events_by_source('system_a')
        self.assertEqual(result, ['e1'])

    def test_get_tick_range(self):
        idx = TimelineIndexer()
        idx.index_event('e1', 1, 't', 's')
        idx.index_event('e2', 3, 't', 's')
        idx.index_event('e3', 5, 't', 's')
        result = idx.get_tick_range(2, 4)
        self.assertEqual(result, ['e2'])

    def test_get_tick_range_empty(self):
        idx = TimelineIndexer()
        result = idx.get_tick_range(0, 10)
        self.assertEqual(result, [])

    def test_clear(self):
        idx = TimelineIndexer()
        idx.index_event('e1', 1, 't', 's')
        idx.clear()
        self.assertEqual(idx.get_events_by_tick(1), [])

    def test_multiple_events_same_tick(self):
        idx = TimelineIndexer()
        idx.index_event('e1', 5, 't', 's')
        idx.index_event('e2', 5, 't', 's')
        self.assertEqual(len(idx.get_events_by_tick(5)), 2)

    def test_bounded_index_history(self):
        idx = TimelineIndexer(max_index_size=2)
        for i in range(5):
            idx.index_event(f'e{i}', 1, 't', 's')
        self.assertEqual(len(idx._index_history), 2)


class TestTimelineCursorManager(unittest.TestCase):
    def test_create_cursor(self):
        mgr = TimelineCursorManager()
        result = mgr.create_cursor('cur1', start_tick=0, total_events=10)
        self.assertEqual(result['cursor_id'], 'cur1')
        self.assertEqual(result['current_tick'], 0)

    def test_advance_forward(self):
        mgr = TimelineCursorManager()
        mgr.create_cursor('cur1', start_tick=0,
                          direction=TimelineDirection.FORWARD)
        result = mgr.advance('cur1', steps=3)
        self.assertTrue(result['advanced'])
        self.assertEqual(result['current_tick'], 3)

    def test_advance_backward(self):
        mgr = TimelineCursorManager()
        mgr.create_cursor('cur1', start_tick=10,
                          direction=TimelineDirection.BACKWARD)
        result = mgr.advance('cur1', steps=3)
        self.assertTrue(result['advanced'])
        self.assertEqual(result['current_tick'], 7)

    def test_advance_backward_stops_at_zero(self):
        mgr = TimelineCursorManager()
        mgr.create_cursor('cur1', start_tick=2,
                          direction=TimelineDirection.BACKWARD)
        result = mgr.advance('cur1', steps=5)
        self.assertTrue(result['advanced'])
        self.assertEqual(result['current_tick'], 0)

    def test_advance_nonexistent_cursor(self):
        mgr = TimelineCursorManager()
        result = mgr.advance('ghost')
        self.assertFalse(result['advanced'])

    def test_get_cursor(self):
        mgr = TimelineCursorManager()
        mgr.create_cursor('cur1', start_tick=5)
        result = mgr.get_cursor('cur1')
        self.assertEqual(result['current_tick'], 5)

    def test_get_cursor_nonexistent(self):
        mgr = TimelineCursorManager()
        self.assertIsNone(mgr.get_cursor('ghost'))

    def test_delete_cursor(self):
        mgr = TimelineCursorManager()
        mgr.create_cursor('cur1')
        self.assertTrue(mgr.delete_cursor('cur1'))
        self.assertIsNone(mgr.get_cursor('cur1'))

    def test_delete_nonexistent_cursor(self):
        mgr = TimelineCursorManager()
        self.assertFalse(mgr.delete_cursor('ghost'))

    def test_clear(self):
        mgr = TimelineCursorManager()
        mgr.create_cursor('cur1')
        mgr.create_cursor('cur2')
        mgr.clear()
        self.assertIsNone(mgr.get_cursor('cur1'))

    def test_bounded_cursor_history(self):
        mgr = TimelineCursorManager(max_cursors=2)
        for i in range(5):
            mgr.create_cursor(f'cur{i}')
        self.assertIsNotNone(mgr.get_cursor('cur0'))
        self.assertEqual(len(mgr._cursor_history), 2)


class TestTimelineValidator(unittest.TestCase):
    def test_validate_ordering_ordered(self):
        v = TimelineValidator()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
            {'event_id': 'e3', 'tick': 3},
        ]
        result = v.validate_ordering(events)
        self.assertTrue(result['is_ordered'])
        self.assertEqual(result['gaps_found'], 0)

    def test_validate_ordering_unordered(self):
        v = TimelineValidator()
        events = [
            {'event_id': 'e1', 'tick': 3},
            {'event_id': 'e2', 'tick': 1},
            {'event_id': 'e3', 'tick': 2},
        ]
        result = v.validate_ordering(events)
        self.assertFalse(result['is_ordered'])

    def test_validate_ordering_detects_gaps(self):
        v = TimelineValidator()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
        ]
        result = v.validate_ordering(events)
        self.assertTrue(result['is_ordered'])
        self.assertEqual(result['gaps_found'], 1)

    def test_validate_no_duplicates(self):
        v = TimelineValidator()
        events = [
            {'event_id': 'e1'},
            {'event_id': 'e2'},
            {'event_id': 'e3'},
        ]
        result = v.validate_no_duplicates(events)
        self.assertTrue(result['no_duplicates'])

    def test_validate_duplicates_detected(self):
        v = TimelineValidator()
        events = [
            {'event_id': 'e1'},
            {'event_id': 'e2'},
            {'event_id': 'e1'},
        ]
        result = v.validate_no_duplicates(events)
        self.assertFalse(result['no_duplicates'])
        self.assertIn('e1', result['duplicates'])

    def test_validate_causal_continuity_intact(self):
        v = TimelineValidator()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e2'},
        ]
        result = v.validate_causal_continuity(events)
        self.assertTrue(result['causal_continuity'])

    def test_validate_causal_continuity_broken(self):
        v = TimelineValidator()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'missing_parent'},
        ]
        result = v.validate_causal_continuity(events)
        self.assertFalse(result['causal_continuity'])
        self.assertEqual(len(result['broken_links']), 1)

    def test_clear(self):
        v = TimelineValidator()
        v.validate_ordering([{'event_id': 'e1', 'tick': 1}])
        v.clear()
        self.assertEqual(len(v._validation_history), 0)

    def test_empty_events_ordering(self):
        v = TimelineValidator()
        result = v.validate_ordering([])
        self.assertTrue(result['is_ordered'])

    def test_single_event_ordering(self):
        v = TimelineValidator()
        result = v.validate_ordering([{'event_id': 'e1', 'tick': 1}])
        self.assertTrue(result['is_ordered'])

    def test_empty_events_no_duplicates(self):
        v = TimelineValidator()
        result = v.validate_no_duplicates([])
        self.assertTrue(result['no_duplicates'])

    def test_empty_events_causal_continuity(self):
        v = TimelineValidator()
        result = v.validate_causal_continuity([])
        self.assertTrue(result['causal_continuity'])


if __name__ == '__main__':
    unittest.main()

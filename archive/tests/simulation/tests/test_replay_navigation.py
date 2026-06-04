"""Phase 4B: deterministic tests for replay navigation components."""
import unittest

from simulation.replay.navigation.time_travel import TimeTravel
from simulation.replay.navigation.replay_navigation import ReplayNavigation
from simulation.replay.navigation.replay_bookmarks import ReplayBookmarks
from simulation.replay.navigation.replay_windows import ReplayWindows
from simulation.replay.models import TimelineDirection


class TestTimeTravel(unittest.TestCase):
    def test_navigate_to_forward(self):
        tt = TimeTravel()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 3},
            {'event_id': 'e3', 'tick': 5},
        ]
        result = tt.navigate_to(5, 1, events)
        self.assertEqual(result['target_tick'], 5)
        self.assertEqual(result['direction'], 'forward')
        self.assertEqual(result['ticks_traveled'], 4)
        self.assertEqual(result['events_found'], 3)

    def test_navigate_to_backward(self):
        tt = TimeTravel()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
        ]
        result = tt.navigate_to(1, 5, events)
        self.assertEqual(result['direction'], 'backward')

    def test_navigate_to_same_tick(self):
        tt = TimeTravel()
        events = [{'event_id': 'e1', 'tick': 3}]
        result = tt.navigate_to(3, 3, events)
        self.assertEqual(result['ticks_traveled'], 0)
        self.assertEqual(result['events_found'], 1)

    def test_navigate_to_start(self):
        tt = TimeTravel()
        events = [
            {'event_id': 'e1', 'tick': 5},
            {'event_id': 'e2', 'tick': 3},
            {'event_id': 'e3', 'tick': 7},
        ]
        result = tt.navigate_to_start(events)
        self.assertEqual(result['target_tick'], 3)

    def test_navigate_to_start_empty(self):
        tt = TimeTravel()
        result = tt.navigate_to_start([])
        self.assertEqual(result['start_tick'], 0)

    def test_navigate_to_end(self):
        tt = TimeTravel()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
        ]
        result = tt.navigate_to_end(events)
        self.assertEqual(result['target_tick'], 5)

    def test_navigate_to_end_empty(self):
        tt = TimeTravel()
        result = tt.navigate_to_end([])
        self.assertEqual(result['end_tick'], 0)

    def test_clear(self):
        tt = TimeTravel()
        tt.navigate_to(5, 1, [{'event_id': 'e1', 'tick': 5}])
        tt.clear()
        self.assertEqual(len(tt._travel_history), 0)

    def test_navigate_to_no_events_in_range(self):
        tt = TimeTravel()
        events = [{'event_id': 'e1', 'tick': 10}]
        result = tt.navigate_to(1, 5, events)
        self.assertEqual(result['events_found'], 0)


class TestReplayNavigation(unittest.TestCase):
    def test_next_event(self):
        nav = ReplayNavigation()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
        ]
        result = nav.next_event(0, events)
        self.assertTrue(result['navigated'])
        self.assertEqual(result['current_index'], 1)
        self.assertEqual(result['event']['event_id'], 'e2')

    def test_next_event_at_end(self):
        nav = ReplayNavigation()
        result = nav.next_event(1, [{'event_id': 'e1'}, {'event_id': 'e2'}])
        self.assertFalse(result['navigated'])

    def test_previous_event(self):
        nav = ReplayNavigation()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
        ]
        result = nav.previous_event(1, events)
        self.assertTrue(result['navigated'])
        self.assertEqual(result['current_index'], 0)

    def test_previous_event_at_start(self):
        nav = ReplayNavigation()
        result = nav.previous_event(0, [{'event_id': 'e1'}])
        self.assertFalse(result['navigated'])

    def test_skip_to_tick(self):
        nav = ReplayNavigation()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
            {'event_id': 'e3', 'tick': 10},
        ]
        result = nav.skip_to_tick(5, 0, events)
        self.assertTrue(result['navigated'])
        self.assertEqual(result['current_index'], 1)

    def test_skip_to_tick_not_found(self):
        nav = ReplayNavigation()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
        ]
        result = nav.skip_to_tick(100, 0, events)
        self.assertFalse(result['navigated'])

    def test_skip_to_tick_first_match(self):
        nav = ReplayNavigation()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 3},
            {'event_id': 'e3', 'tick': 3},
        ]
        result = nav.skip_to_tick(3, 0, events)
        self.assertEqual(result['current_index'], 1)

    def test_clear(self):
        nav = ReplayNavigation()
        nav.next_event(0, [{'event_id': 'e1', 'tick': 1},
                           {'event_id': 'e2', 'tick': 2}])
        nav.clear()
        self.assertEqual(len(nav._navigation_history), 0)

    def test_empty_events_next(self):
        nav = ReplayNavigation()
        result = nav.next_event(0, [])
        self.assertFalse(result['navigated'])

    def test_empty_events_previous(self):
        nav = ReplayNavigation()
        result = nav.previous_event(0, [])
        self.assertFalse(result['navigated'])


class TestReplayBookmarks(unittest.TestCase):
    def test_add_bookmark(self):
        bm = ReplayBookmarks()
        result = bm.add_bookmark('bm1', tick=10, label='checkpoint')
        self.assertEqual(result['bookmark_id'], 'bm1')
        self.assertEqual(result['tick'], 10)

    def test_get_bookmark(self):
        bm = ReplayBookmarks()
        bm.add_bookmark('bm1', tick=10, label='cp1')
        result = bm.get_bookmark('bm1')
        self.assertEqual(result['label'], 'cp1')

    def test_get_bookmark_nonexistent(self):
        bm = ReplayBookmarks()
        self.assertIsNone(bm.get_bookmark('ghost'))

    def test_list_bookmarks(self):
        bm = ReplayBookmarks()
        bm.add_bookmark('bm1', tick=10, label='cp1')
        bm.add_bookmark('bm2', tick=20, label='cp2')
        result = bm.list_bookmarks()
        self.assertEqual(len(result), 2)

    def test_remove_bookmark(self):
        bm = ReplayBookmarks()
        bm.add_bookmark('bm1', tick=10, label='cp1')
        self.assertTrue(bm.remove_bookmark('bm1'))
        self.assertIsNone(bm.get_bookmark('bm1'))

    def test_remove_nonexistent_bookmark(self):
        bm = ReplayBookmarks()
        self.assertFalse(bm.remove_bookmark('ghost'))

    def test_add_bookmark_with_snapshot(self):
        bm = ReplayBookmarks()
        result = bm.add_bookmark('bm1', tick=10, label='cp1',
                                  snapshot_id='snap1')
        self.assertEqual(result['snapshot_id'], 'snap1')

    def test_clear(self):
        bm = ReplayBookmarks()
        bm.add_bookmark('bm1', tick=10, label='cp1')
        bm.clear()
        self.assertEqual(bm.list_bookmarks(), [])

    def test_bounded_bookmarks(self):
        bm = ReplayBookmarks(max_bookmarks=2)
        bm.add_bookmark('bm1', tick=1, label='a')
        bm.add_bookmark('bm2', tick=2, label='b')
        bm.add_bookmark('bm3', tick=3, label='c')
        self.assertEqual(len(bm.list_bookmarks()), 3)
        self.assertEqual(len(bm._bookmark_list), 2)


class TestReplayWindows(unittest.TestCase):
    def test_create_window(self):
        rw = ReplayWindows()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
            {'event_id': 'e3', 'tick': 10},
        ]
        result = rw.create_window('w1', 2, 8, events)
        self.assertEqual(result['event_count'], 1)
        self.assertEqual(result['window_id'], 'w1')

    def test_create_window_no_events(self):
        rw = ReplayWindows()
        result = rw.create_window('w1', 0, 10)
        self.assertEqual(result['event_count'], 0)

    def test_get_window(self):
        rw = ReplayWindows()
        rw.create_window('w1', 0, 10)
        result = rw.get_window('w1')
        self.assertEqual(result['start_tick'], 0)
        self.assertEqual(result['end_tick'], 10)

    def test_get_window_nonexistent(self):
        rw = ReplayWindows()
        self.assertIsNone(rw.get_window('ghost'))

    def test_slide_window(self):
        rw = ReplayWindows()
        events = [
            {'event_id': 'e1', 'tick': 5},
            {'event_id': 'e2', 'tick': 10},
        ]
        rw.create_window('w1', 0, 10, events)
        result = rw.slide_window('w1', 5, events)
        self.assertEqual(result['start_tick'], 5)
        self.assertEqual(result['end_tick'], 15)

    def test_slide_window_nonexistent(self):
        rw = ReplayWindows()
        result = rw.slide_window('ghost', 5)
        self.assertFalse(result['slid'])

    def test_slide_window_counts_filtered_events(self):
        rw = ReplayWindows()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 5},
            {'event_id': 'e3', 'tick': 10},
        ]
        rw.create_window('w1', 0, 10, events)
        result = rw.slide_window('w1', 3, events)
        self.assertEqual(result['start_tick'], 3)
        self.assertEqual(result['end_tick'], 13)
        self.assertGreaterEqual(result['event_count'], 1)

    def test_clear(self):
        rw = ReplayWindows()
        rw.create_window('w1', 0, 10)
        rw.clear()
        self.assertIsNone(rw.get_window('w1'))

    def test_bounded_windows(self):
        rw = ReplayWindows(max_windows=2)
        rw.create_window('w1', 0, 10)
        rw.create_window('w2', 10, 20)
        rw.create_window('w3', 20, 30)
        self.assertEqual(len(rw._window_history), 2)

    def test_create_window_all_events_in_range(self):
        rw = ReplayWindows()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
            {'event_id': 'e3', 'tick': 3},
        ]
        result = rw.create_window('w1', 1, 3, events)
        self.assertEqual(result['event_count'], 3)


if __name__ == '__main__':
    unittest.main()

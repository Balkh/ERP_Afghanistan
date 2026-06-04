"""Phase 4B: deterministic tests for replay snapshot components."""
import unittest

from simulation.replay.snapshots.snapshot_loader import SnapshotLoader
from simulation.replay.snapshots.snapshot_reconstructor import SnapshotReconstructor
from simulation.replay.snapshots.snapshot_integrity import SnapshotIntegrity
from simulation.replay.snapshots.snapshot_history import SnapshotHistory


class TestSnapshotLoader(unittest.TestCase):
    def test_load_snapshot(self):
        sl = SnapshotLoader()
        result = sl.load_snapshot('snap1', tick=10, event_count=5)
        self.assertEqual(result['snapshot_id'], 'snap1')
        self.assertEqual(result['tick'], 10)

    def test_get_snapshot(self):
        sl = SnapshotLoader()
        sl.load_snapshot('snap1', tick=10)
        result = sl.get_snapshot('snap1')
        self.assertEqual(result['tick'], 10)

    def test_get_snapshot_nonexistent(self):
        sl = SnapshotLoader()
        self.assertIsNone(sl.get_snapshot('ghost'))

    def test_get_snapshots_since(self):
        sl = SnapshotLoader()
        sl.load_snapshot('s1', tick=5)
        sl.load_snapshot('s2', tick=10)
        sl.load_snapshot('s3', tick=15)
        result = sl.get_snapshots_since(10)
        self.assertEqual(len(result), 2)

    def test_get_snapshot_count(self):
        sl = SnapshotLoader()
        self.assertEqual(sl.get_snapshot_count(), 0)
        sl.load_snapshot('s1', tick=1)
        self.assertEqual(sl.get_snapshot_count(), 1)

    def test_load_snapshot_with_parent(self):
        sl = SnapshotLoader()
        sl.load_snapshot('s1', tick=1, parent_id='p1')
        result = sl.get_snapshot('s1')
        self.assertEqual(result['parent_snapshot_id'], 'p1')

    def test_clear(self):
        sl = SnapshotLoader()
        sl.load_snapshot('s1', tick=1)
        sl.clear()
        self.assertEqual(sl.get_snapshot_count(), 0)

    def test_bounded_load_history(self):
        sl = SnapshotLoader(max_snapshots=2)
        sl.load_snapshot('s1', tick=1)
        sl.load_snapshot('s2', tick=2)
        sl.load_snapshot('s3', tick=3)
        self.assertEqual(sl.get_snapshot_count(), 3)
        self.assertEqual(len(sl._load_history), 2)

    def test_get_snapshot_returns_all_fields(self):
        sl = SnapshotLoader()
        sl.load_snapshot('s1', tick=5, event_count=3,
                         hash_value='abc123', parent_id='p0')
        result = sl.get_snapshot('s1')
        self.assertEqual(result['hash_value'], 'abc123')
        self.assertEqual(result['parent_snapshot_id'], 'p0')
        self.assertEqual(result['status'], 'intact')

    def test_get_snapshots_since_no_match(self):
        sl = SnapshotLoader()
        sl.load_snapshot('s1', tick=1)
        result = sl.get_snapshots_since(10)
        self.assertEqual(result, [])


class TestSnapshotReconstructor(unittest.TestCase):
    def test_reconstruct_empty_events(self):
        sr = SnapshotReconstructor()
        result = sr.reconstruct('snap1', tick=10, events=[])
        self.assertEqual(result['snapshot_id'], 'snap1')
        self.assertEqual(result['event_count'], 0)

    def test_reconstruct_with_events(self):
        sr = SnapshotReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'start', 'source': 'wf_a'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'step', 'source': 'wf_a'},
        ]
        result = sr.reconstruct('snap1', tick=10, events=events)
        self.assertEqual(result['event_count'], 2)
        self.assertIn('wf_a', result['workflow_states'])

    def test_reconstruct_tracks_workflow_states(self):
        sr = SnapshotReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'start', 'source': 'wf_a'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'start', 'source': 'wf_b'},
        ]
        result = sr.reconstruct('snap1', tick=10, events=events)
        self.assertEqual(len(result['workflow_states']), 2)

    def test_reconstruct_with_base_state(self):
        sr = SnapshotReconstructor()
        result = sr.reconstruct('snap1', tick=5, events=[],
                                base_state={'existing': 'val'})
        self.assertEqual(result['status'], 'reconstructed')

    def test_get_reconstruction_count(self):
        sr = SnapshotReconstructor()
        self.assertEqual(sr.get_reconstruction_count(), 0)
        sr.reconstruct('s1', tick=1, events=[])
        self.assertEqual(sr.get_reconstruction_count(), 1)

    def test_clear(self):
        sr = SnapshotReconstructor()
        sr.reconstruct('s1', tick=1, events=[])
        sr.clear()
        self.assertEqual(sr.get_reconstruction_count(), 0)

    def test_reconstruct_updates_last_tick(self):
        sr = SnapshotReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 'wf_x'},
            {'event_id': 'e2', 'tick': 5, 'event_type': 'b', 'source': 'wf_x'},
        ]
        result = sr.reconstruct('s1', tick=10, events=events)
        wf = result['workflow_states']['wf_x']
        self.assertEqual(wf['last_tick'], 5)
        self.assertEqual(wf['event_count'], 2)

    def test_reconstruct_multiple_workflows(self):
        sr = SnapshotReconstructor()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 'wf_x'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'b', 'source': 'wf_y'},
            {'event_id': 'e3', 'tick': 3, 'event_type': 'c', 'source': 'wf_x'},
        ]
        result = sr.reconstruct('s1', tick=10, events=events)
        self.assertEqual(result['workflow_states']['wf_x']['event_count'], 2)
        self.assertEqual(result['workflow_states']['wf_y']['event_count'], 1)


class TestSnapshotIntegrity(unittest.TestCase):
    def test_verify_integrity_intact(self):
        si = SnapshotIntegrity()
        snapshot = {
            'snapshot_id': 's1', 'hash_value': 'abc',
            'workflow_states': {'wf': 'ok'}, 'event_count': 5,
        }
        result = si.verify_integrity(snapshot, expected_hash='abc')
        self.assertTrue(result['is_intact'])

    def test_verify_integrity_corrupted_hash(self):
        si = SnapshotIntegrity()
        snapshot = {
            'snapshot_id': 's1', 'hash_value': 'abc',
            'workflow_states': {'wf': 'ok'}, 'event_count': 5,
        }
        result = si.verify_integrity(snapshot, expected_hash='xyz')
        self.assertFalse(result['is_intact'])
        self.assertFalse(result['hash_match'])

    def test_verify_integrity_no_workflows(self):
        si = SnapshotIntegrity()
        snapshot = {
            'snapshot_id': 's1', 'hash_value': 'abc',
            'workflow_states': {}, 'event_count': 0,
        }
        result = si.verify_integrity(snapshot)
        self.assertFalse(result['is_intact'])

    def test_verify_integrity_no_expected_hash(self):
        si = SnapshotIntegrity()
        snapshot = {
            'snapshot_id': 's1', 'hash_value': 'abc',
            'workflow_states': {'wf': 'ok'}, 'event_count': 5,
        }
        result = si.verify_integrity(snapshot)
        self.assertTrue(result['is_intact'])

    def test_verify_lineage_empty(self):
        si = SnapshotIntegrity()
        result = si.verify_lineage([])
        self.assertTrue(result['lineage_intact'])

    def test_verify_lineage_intact(self):
        si = SnapshotIntegrity()
        snapshots = [
            {'snapshot_id': 's1', 'tick': 1, 'parent_snapshot_id': None},
            {'snapshot_id': 's2', 'tick': 2, 'parent_snapshot_id': 's1'},
            {'snapshot_id': 's3', 'tick': 3, 'parent_snapshot_id': 's2'},
        ]
        result = si.verify_lineage(snapshots)
        self.assertTrue(result['lineage_intact'])

    def test_verify_lineage_broken(self):
        si = SnapshotIntegrity()
        snapshots = [
            {'snapshot_id': 's1', 'tick': 1, 'parent_snapshot_id': None},
            {'snapshot_id': 's2', 'tick': 2, 'parent_snapshot_id': 'missing'},
        ]
        result = si.verify_lineage(snapshots)
        self.assertFalse(result['lineage_intact'])
        self.assertTrue(result['chain_broken'])

    def test_clear(self):
        si = SnapshotIntegrity()
        si.verify_integrity({'snapshot_id': 's1', 'workflow_states': {'a': 1}})
        si.clear()
        self.assertEqual(len(si._integrity_history), 0)

    def test_verify_lineage_ticks_out_of_order(self):
        si = SnapshotIntegrity()
        snapshots = [
            {'snapshot_id': 's1', 'tick': 5, 'parent_snapshot_id': None},
            {'snapshot_id': 's2', 'tick': 1, 'parent_snapshot_id': 's1'},
        ]
        result = si.verify_lineage(snapshots)
        self.assertFalse(result['ticks_ordered'])

    def test_verify_integrity_has_events_negative(self):
        si = SnapshotIntegrity()
        snapshot = {
            'snapshot_id': 's1', 'hash_value': '',
            'workflow_states': {'wf': 'ok'}, 'event_count': -1,
        }
        result = si.verify_integrity(snapshot)
        self.assertFalse(result['has_events'])


class TestSnapshotHistory(unittest.TestCase):
    def test_record_snapshot(self):
        sh = SnapshotHistory()
        result = sh.record_snapshot('s1', tick=10)
        self.assertEqual(result['snapshot_id'], 's1')
        self.assertEqual(result['tick'], 10)

    def test_record_snapshot_with_parent(self):
        sh = SnapshotHistory()
        sh.record_snapshot('s1', tick=1)
        result = sh.record_snapshot('s2', tick=2, parent_id='s1')
        self.assertEqual(result['parent_id'], 's1')

    def test_get_lineage(self):
        sh = SnapshotHistory()
        sh.record_snapshot('s1', tick=1)
        sh.record_snapshot('s2', tick=2, parent_id='s1')
        sh.record_snapshot('s3', tick=3, parent_id='s2')
        lineage = sh.get_lineage('s3')
        self.assertEqual(len(lineage), 3)
        self.assertEqual(lineage[0]['snapshot_id'], 's3')
        self.assertEqual(lineage[-1]['snapshot_id'], 's1')

    def test_get_lineage_empty(self):
        sh = SnapshotHistory()
        lineage = sh.get_lineage('nonexistent')
        self.assertEqual(lineage, [])

    def test_get_history_count(self):
        sh = SnapshotHistory()
        self.assertEqual(sh.get_history_count(), 0)
        sh.record_snapshot('s1', tick=1)
        self.assertEqual(sh.get_history_count(), 1)

    def test_clear(self):
        sh = SnapshotHistory()
        sh.record_snapshot('s1', tick=1)
        sh.clear()
        self.assertEqual(sh.get_history_count(), 0)

    def test_get_lineage_bounded_at_100(self):
        sh = SnapshotHistory()
        for i in range(150):
            parent = f's{i}' if i > 0 else None
            sh.record_snapshot(f's{i}', tick=i, parent_id=parent)
        lineage = sh.get_lineage('s149')
        self.assertLessEqual(len(lineage), 101)

    def test_get_lineage_cycle_detection(self):
        sh = SnapshotHistory()
        sh.record_snapshot('s1', tick=1, parent_id='s3')
        sh.record_snapshot('s2', tick=2, parent_id='s1')
        sh.record_snapshot('s3', tick=3, parent_id='s2')
        lineage = sh.get_lineage('s1')
        self.assertGreaterEqual(len(lineage), 1)

    def test_bounded_history(self):
        sh = SnapshotHistory(max_history=2)
        sh.record_snapshot('s1', tick=1)
        sh.record_snapshot('s2', tick=2)
        sh.record_snapshot('s3', tick=3)
        self.assertEqual(sh.get_history_count(), 2)


if __name__ == '__main__':
    unittest.main()

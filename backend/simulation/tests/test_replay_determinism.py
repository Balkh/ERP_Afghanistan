"""Phase 4B: deterministic tests for replay determinism components."""
import hashlib
import json
import unittest

from simulation.replay.determinism.replay_hashing import ReplayHashing
from simulation.replay.determinism.replay_determinism import ReplayDeterminism
from simulation.replay.determinism.divergence_detector import DivergenceDetector
from simulation.replay.determinism.replay_consistency import ReplayConsistency
from simulation.replay.models import DivergenceType


class TestReplayHashing(unittest.TestCase):
    def test_hash_event_deterministic(self):
        rh = ReplayHashing()
        event = {'event_id': 'e1', 'tick': 1, 'event_type': 'test'}
        h1 = rh.hash_event(event)
        h2 = rh.hash_event(event)
        self.assertEqual(h1, h2)

    def test_hash_event_sha256_length(self):
        rh = ReplayHashing()
        h = rh.hash_event({'event_id': 'e1'})
        self.assertEqual(len(h), 64)

    def test_hash_event_different_events_different_hashes(self):
        rh = ReplayHashing()
        h1 = rh.hash_event({'event_id': 'e1', 'tick': 1})
        h2 = rh.hash_event({'event_id': 'e2', 'tick': 2})
        self.assertNotEqual(h1, h2)

    def test_hash_events_batch(self):
        rh = ReplayHashing()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
        ]
        h = rh.hash_events_batch(events)
        self.assertEqual(len(h), 64)

    def test_hash_events_batch_deterministic(self):
        rh = ReplayHashing()
        events = [{'event_id': 'e1', 'tick': 1}]
        self.assertEqual(rh.hash_events_batch(events),
                         rh.hash_events_batch(events))

    def test_hash_events_batch_empty(self):
        rh = ReplayHashing()
        h = rh.hash_events_batch([])
        self.assertEqual(len(h), 64)

    def test_record_hash(self):
        rh = ReplayHashing()
        result = rh.record_hash('h1', tick=1)
        self.assertEqual(result['tick'], 1)
        self.assertEqual(result['component'], 'timeline')
        self.assertIsNone(result['previous_hash'])

    def test_record_hash_chains(self):
        rh = ReplayHashing()
        r1 = rh.record_hash('h1', tick=1)
        r2 = rh.record_hash('h2', tick=2)
        self.assertEqual(r2['previous_hash'], r1['hash_value'])

    def test_verify_hash_chain_intact(self):
        rh = ReplayHashing()
        rh.record_hash('h1', tick=1)
        rh.record_hash('h2', tick=2)
        result = rh.verify_hash_chain()
        self.assertTrue(result['chain_intact'])

    def test_verify_hash_chain_empty(self):
        rh = ReplayHashing()
        result = rh.verify_hash_chain()
        self.assertTrue(result['chain_intact'])

    def test_reset(self):
        rh = ReplayHashing()
        rh.record_hash('h1', tick=1)
        rh.reset()
        self.assertIsNone(rh._previous_hash)
        result = rh.verify_hash_chain()
        self.assertEqual(result['hashes_checked'], 0)

    def test_hash_canonical_json_order(self):
        rh = ReplayHashing()
        h1 = rh.hash_event({'b': 2, 'a': 1})
        h2 = rh.hash_event({'a': 1, 'b': 2})
        self.assertEqual(h1, h2)

    def test_record_hash_with_component(self):
        rh = ReplayHashing()
        result = rh.record_hash('h1', tick=1, component='snapshot')
        self.assertEqual(result['component'], 'snapshot')

    def test_bounded_hash_history(self):
        rh = ReplayHashing(max_history=2)
        rh.record_hash('h1', tick=1)
        rh.record_hash('h2', tick=2)
        rh.record_hash('h3', tick=3)
        self.assertEqual(len(rh._hash_history), 2)


class TestReplayDeterminism(unittest.TestCase):
    def test_verify_determinism_identical(self):
        rd = ReplayDeterminism()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
        ]
        result = rd.verify_determinism(events, events)
        self.assertTrue(result['is_deterministic'])
        self.assertEqual(result['total_mismatches'], 0)

    def test_verify_determinism_different(self):
        rd = ReplayDeterminism()
        run1 = [{'event_id': 'e1', 'tick': 1}]
        run2 = [{'event_id': 'e2', 'tick': 2}]
        result = rd.verify_determinism(run1, run2)
        self.assertFalse(result['is_deterministic'])
        self.assertGreater(result['total_mismatches'], 0)

    def test_verify_determinism_empty_runs(self):
        rd = ReplayDeterminism()
        result = rd.verify_determinism([], [])
        self.assertTrue(result['is_deterministic'])

    def test_verify_determinism_only_10_mismatches_reported(self):
        rd = ReplayDeterminism()
        run1 = [{'event_id': f'e{i}', 'tick': i} for i in range(20)]
        run2 = [{'event_id': f'x{i}', 'tick': i} for i in range(20)]
        result = rd.verify_determinism(run1, run2)
        self.assertLessEqual(result['total_mismatches'], 10)

    def test_clear(self):
        rd = ReplayDeterminism()
        rd.verify_determinism([], [])
        rd.clear()
        self.assertEqual(len(rd._determinism_history), 0)


class TestDivergenceDetector(unittest.TestCase):
    def test_detect_state_mismatch_detected(self):
        dd = DivergenceDetector()
        result = dd.detect_state_mismatch(1, {'key': 'val1'}, {'key': 'val2'})
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'state_mismatch')

    def test_detect_state_mismatch_no_mismatch(self):
        dd = DivergenceDetector()
        result = dd.detect_state_mismatch(1, {'key': 'val'}, {'key': 'val'})
        self.assertIsNone(result)

    def test_detect_state_mismatch_empty(self):
        dd = DivergenceDetector()
        result = dd.detect_state_mismatch(1, {}, {})
        self.assertIsNone(result)

    def test_detect_event_mismatch_detected(self):
        dd = DivergenceDetector()
        result = dd.detect_event_mismatch(
            1, {'event_id': 'e1'}, {'event_id': 'e2'})
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'event_mismatch')

    def test_detect_event_mismatch_same(self):
        dd = DivergenceDetector()
        result = dd.detect_event_mismatch(
            1, {'event_id': 'e1'}, {'event_id': 'e1'})
        self.assertIsNone(result)

    def test_detect_event_mismatch_none(self):
        dd = DivergenceDetector()
        result = dd.detect_event_mismatch(1, None, None)
        self.assertIsNone(result)

    def test_detect_order_mismatch_detected(self):
        dd = DivergenceDetector()
        result = dd.detect_order_mismatch(
            1, ['e1', 'e2'], ['e2', 'e1'])
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'order_mismatch')

    def test_detect_order_mismatch_same(self):
        dd = DivergenceDetector()
        result = dd.detect_order_mismatch(
            1, ['e1', 'e2'], ['e1', 'e2'])
        self.assertIsNone(result)

    def test_get_divergence_count(self):
        dd = DivergenceDetector()
        self.assertEqual(dd.get_divergence_count(), 0)
        dd.detect_state_mismatch(1, {'a': 1}, {'a': 2})
        self.assertEqual(dd.get_divergence_count(), 1)

    def test_clear(self):
        dd = DivergenceDetector()
        dd.detect_state_mismatch(1, {'a': 1}, {'a': 2})
        dd.clear()
        self.assertEqual(dd.get_divergence_count(), 0)

    def test_detect_state_mismatch_multiple_keys(self):
        dd = DivergenceDetector()
        result = dd.detect_state_mismatch(
            1, {'a': 1, 'b': 2}, {'a': 1, 'b': 99})
        self.assertIsNotNone(result)


class TestReplayConsistency(unittest.TestCase):
    def test_check_consistency_consistent(self):
        rc = ReplayConsistency()
        events = [
            {'event_id': 'e1', 'tick': 1},
            {'event_id': 'e2', 'tick': 2},
        ]
        result = rc.check_consistency(events, events)
        self.assertTrue(result['is_consistent'])
        self.assertEqual(result['total_divergences'], 0)

    def test_check_consistency_inconsistent(self):
        rc = ReplayConsistency()
        run1 = [{'event_id': 'e1', 'tick': 1}]
        run2 = [{'event_id': 'e2', 'tick': 2}]
        result = rc.check_consistency(run1, run2)
        self.assertFalse(result['is_consistent'])
        self.assertGreater(result['total_divergences'], 0)

    def test_check_consistency_empty_runs(self):
        rc = ReplayConsistency()
        result = rc.check_consistency([], [])
        self.assertTrue(result['is_consistent'])

    def test_clear(self):
        rc = ReplayConsistency()
        rc.check_consistency([], [])
        rc.clear()
        self.assertEqual(len(rc._consistency_history), 0)

    def test_check_consistency_has_divergences_key(self):
        rc = ReplayConsistency()
        result = rc.check_consistency([{'event_id': 'e1'}],
                                       [{'event_id': 'e2'}])
        self.assertIn('divergences', result)


if __name__ == '__main__':
    unittest.main()

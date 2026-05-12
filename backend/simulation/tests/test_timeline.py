"""Phase 4C: deterministic tests for Control Center timeline components."""
import unittest

from simulation.control_center.models import (
    IntelligenceSeverity, OperationalSignal, SignalType, UnifiedTimelineEvent,
)
from simulation.control_center.timeline.unified_timeline import UnifiedTimeline
from simulation.control_center.timeline.intelligence_timeline_builder import (
    IntelligenceTimelineBuilder,
)
from simulation.control_center.timeline.cross_phase_correlator import (
    CrossPhaseCorrelator,
)
from simulation.control_center.timeline.operational_sequence_tracker import (
    OperationalSequenceTracker,
)


def _make_event(event_id, tick, source='test', event_type='test_event',
                severity=IntelligenceSeverity.INFO, desc='test event',
                related=None):
    return UnifiedTimelineEvent(
        event_id=event_id, tick=tick, source_phase=source,
        event_type=event_type, description=desc, severity=severity,
        related_event_ids=related or [],
    )


class TestUnifiedTimeline(unittest.TestCase):
    """UnifiedTimeline: add, get, filter, bounded."""

    def setUp(self):
        self.timeline = UnifiedTimeline(max_events=1000)

    def test_empty_timeline_returns_empty_list(self):
        self.assertEqual(self.timeline.get_events(), [])
        self.assertEqual(self.timeline.get_event_count(), 0)

    def test_add_event_returns_event(self):
        event = self.timeline.add_event(
            event_id='ev1', tick=1, source_phase='phase_a',
            event_type='test', description='test event',
            severity=IntelligenceSeverity.INFO,
        )
        self.assertIsInstance(event, UnifiedTimelineEvent)
        self.assertEqual(event.event_id, 'ev1')
        self.assertEqual(event.tick, 1)
        self.assertEqual(event.source_phase, 'phase_a')
        self.assertEqual(event.event_type, 'test')
        self.assertEqual(event.description, 'test event')
        self.assertEqual(event.severity, IntelligenceSeverity.INFO)
        self.assertEqual(event.payload, {})
        self.assertEqual(event.related_event_ids, [])

    def test_add_event_with_payload_and_relations(self):
        event = self.timeline.add_event(
            event_id='ev2', tick=5, source_phase='phase_b',
            event_type='alert', description='alert event',
            severity=IntelligenceSeverity.HIGH,
            payload={'key': 'value'},
            related_event_ids=['ev1'],
        )
        self.assertEqual(event.payload, {'key': 'value'})
        self.assertEqual(event.related_event_ids, ['ev1'])

    def test_get_event_count(self):
        self.assertEqual(self.timeline.get_event_count(), 0)
        self.timeline.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.assertEqual(self.timeline.get_event_count(), 1)
        self.timeline.add_event('e2', 2, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.assertEqual(self.timeline.get_event_count(), 2)

    def test_get_events_returns_sorted_by_tick(self):
        self.timeline.add_event('e3', 3, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e2', 2, 's', 't', 'd', IntelligenceSeverity.INFO)
        events = self.timeline.get_events()
        self.assertEqual([e.tick for e in events], [1, 2, 3])

    def test_filter_by_tick_range(self):
        self.timeline.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e2', 5, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e3', 10, 's', 't', 'd', IntelligenceSeverity.INFO)
        result = self.timeline.get_events(tick_start=2, tick_end=8)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event_id, 'e2')

    def test_filter_by_tick_start_only(self):
        self.timeline.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e2', 5, 's', 't', 'd', IntelligenceSeverity.INFO)
        result = self.timeline.get_events(tick_start=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event_id, 'e2')

    def test_filter_by_tick_end_only(self):
        self.timeline.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e2', 5, 's', 't', 'd', IntelligenceSeverity.INFO)
        result = self.timeline.get_events(tick_end=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event_id, 'e1')

    def test_filter_by_source_phase(self):
        self.timeline.add_event('e1', 1, 'alpha', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e2', 2, 'beta', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e3', 3, 'alpha', 't', 'd', IntelligenceSeverity.INFO)
        result = self.timeline.get_events(source_phase='alpha')
        self.assertEqual(len(result), 2)
        for e in result:
            self.assertEqual(e.source_phase, 'alpha')

    def test_filter_by_severity(self):
        self.timeline.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.LOW)
        self.timeline.add_event('e2', 2, 's', 't', 'd', IntelligenceSeverity.HIGH)
        self.timeline.add_event('e3', 3, 's', 't', 'd', IntelligenceSeverity.LOW)
        result = self.timeline.get_events(severity=IntelligenceSeverity.LOW)
        self.assertEqual(len(result), 2)
        for e in result:
            self.assertEqual(e.severity, IntelligenceSeverity.LOW)

    def test_filter_by_event_type(self):
        self.timeline.add_event('e1', 1, 's', 'alert', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e2', 2, 's', 'log', 'd', IntelligenceSeverity.INFO)
        result = self.timeline.get_events(event_type='alert')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event_type, 'alert')

    def test_combined_filters(self):
        self.timeline.add_event('e1', 1, 'src_a', 'type_x', 'd', IntelligenceSeverity.LOW)
        self.timeline.add_event('e2', 5, 'src_a', 'type_x', 'd', IntelligenceSeverity.HIGH)
        self.timeline.add_event('e3', 10, 'src_b', 'type_x', 'd', IntelligenceSeverity.LOW)
        result = self.timeline.get_events(
            tick_start=2, tick_end=8, source_phase='src_a',
            severity=IntelligenceSeverity.HIGH,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event_id, 'e2')

    def test_limit_default_is_100(self):
        for i in range(150):
            self.timeline.add_event(
                f'e{i}', i, 's', 't', 'd', IntelligenceSeverity.INFO,
            )
        result = self.timeline.get_events()
        self.assertLessEqual(len(result), 100)

    def test_limit_parameter(self):
        for i in range(50):
            self.timeline.add_event(
                f'e{i}', i, 's', 't', 'd', IntelligenceSeverity.INFO,
            )
        result = self.timeline.get_events(limit=10)
        self.assertEqual(len(result), 10)

    def test_validation_empty_event_id_raises(self):
        with self.assertRaises(ValueError):
            self.timeline.add_event(
                event_id='', tick=1, source_phase='s',
                event_type='t', description='d',
                severity=IntelligenceSeverity.INFO,
            )

    def test_validation_non_string_event_id_raises(self):
        with self.assertRaises(ValueError):
            self.timeline.add_event(
                event_id=123, tick=1, source_phase='s',
                event_type='t', description='d',
                severity=IntelligenceSeverity.INFO,
            )

    def test_validation_negative_tick_raises(self):
        with self.assertRaises(ValueError):
            self.timeline.add_event(
                event_id='e1', tick=-1, source_phase='s',
                event_type='t', description='d',
                severity=IntelligenceSeverity.INFO,
            )

    def test_bounded_by_max_events_evicts_oldest(self):
        tl = UnifiedTimeline(max_events=3)
        tl.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.INFO)
        tl.add_event('e2', 2, 's', 't', 'd', IntelligenceSeverity.INFO)
        tl.add_event('e3', 3, 's', 't', 'd', IntelligenceSeverity.INFO)
        tl.add_event('e4', 4, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.assertEqual(tl.get_event_count(), 3)
        ids = [e.event_id for e in tl.get_events()]
        self.assertNotIn('e1', ids)
        self.assertIn('e4', ids)

    def test_clear_removes_all_events(self):
        self.timeline.add_event('e1', 1, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.add_event('e2', 2, 's', 't', 'd', IntelligenceSeverity.INFO)
        self.timeline.clear()
        self.assertEqual(self.timeline.get_event_count(), 0)
        self.assertEqual(self.timeline.get_events(), [])


class TestIntelligenceTimelineBuilder(unittest.TestCase):
    """IntelligenceTimelineBuilder: signal, mismatch, recovery, replay."""

    def setUp(self):
        self.builder = IntelligenceTimelineBuilder()

    def _make_signal(self, sid='sig1', severity=IntelligenceSeverity.HIGH,
                     stype=SignalType.TRUTH_MISMATCH, source='phase3a',
                     tick=1, desc='test', payload=None):
        return OperationalSignal(
            signal_id=sid, signal_type=stype, severity=severity,
            source_phase=source, tick=tick, description=desc,
            payload=payload or {},
        )

    def test_build_from_signal_produces_correct_fields(self):
        signal = self._make_signal()
        event = self.builder.build_from_signal(signal, tick=10)
        self.assertIsInstance(event, UnifiedTimelineEvent)
        self.assertEqual(event.event_id, 'sig1')
        self.assertEqual(event.tick, 10)
        self.assertEqual(event.source_phase, 'phase3a')
        self.assertEqual(event.event_type, 'truth_mismatch')
        self.assertEqual(event.description, 'test')
        self.assertEqual(event.severity, IntelligenceSeverity.HIGH)
        self.assertEqual(event.payload, {})
        self.assertEqual(event.related_event_ids, [])

    def test_build_from_signal_preserves_payload(self):
        signal = self._make_signal(payload={'key': 'val'})
        event = self.builder.build_from_signal(signal, tick=5)
        self.assertEqual(event.payload, {'key': 'val'})

    def test_build_from_signal_uses_signal_type_value(self):
        signal = self._make_signal(stype=SignalType.PREDICTIVE_WARNING)
        event = self.builder.build_from_signal(signal, tick=1)
        self.assertEqual(event.event_type, 'predictive_warning')

    def test_build_from_signals_batch_conversion(self):
        signals = [
            self._make_signal(sid='a', desc='first'),
            self._make_signal(sid='b', desc='second'),
        ]
        events = self.builder.build_from_signals(signals, tick=20)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_id, 'a')
        self.assertEqual(events[1].event_id, 'b')
        for e in events:
            self.assertEqual(e.tick, 20)

    def test_build_from_signals_empty_list(self):
        events = self.builder.build_from_signals([], tick=1)
        self.assertEqual(events, [])

    def test_build_mismatch_event(self):
        data = {
            'event_id': 'mm1',
            'source_phase': 'truth_engine',
            'description': 'Stock imbalance detected',
            'severity': 'high',
            'related_event_ids': ['prev_id'],
            'extra': 'value',
        }
        event = self.builder.build_mismatch_event(data, tick=15)
        self.assertEqual(event.event_id, 'mm1')
        self.assertEqual(event.tick, 15)
        self.assertEqual(event.source_phase, 'truth_engine')
        self.assertEqual(event.event_type, 'truth_mismatch')
        self.assertEqual(event.description, 'Stock imbalance detected')
        self.assertEqual(event.severity, IntelligenceSeverity.HIGH)
        self.assertEqual(event.related_event_ids, ['prev_id'])
        self.assertEqual(event.payload['extra'], 'value')

    def test_build_mismatch_event_defaults(self):
        event = self.builder.build_mismatch_event({}, tick=7)
        self.assertTrue(event.event_id.startswith('mismatch_'))
        self.assertEqual(event.source_phase, 'truth_engine')
        self.assertEqual(event.event_type, 'truth_mismatch')
        self.assertEqual(event.severity, IntelligenceSeverity.MEDIUM)

    def test_build_recovery_event(self):
        data = {
            'event_id': 'rec1',
            'source_phase': 'recovery_system',
            'description': 'System recovered',
            'severity': 'info',
        }
        event = self.builder.build_recovery_event(data, tick=25)
        self.assertEqual(event.event_id, 'rec1')
        self.assertEqual(event.tick, 25)
        self.assertEqual(event.source_phase, 'recovery_system')
        self.assertEqual(event.event_type, 'recovery_event')
        self.assertEqual(event.description, 'System recovered')
        self.assertEqual(event.severity, IntelligenceSeverity.INFO)

    def test_build_recovery_event_defaults(self):
        event = self.builder.build_recovery_event({}, tick=3)
        self.assertTrue(event.event_id.startswith('recovery_'))
        self.assertEqual(event.source_phase, 'recovery_system')
        self.assertEqual(event.event_type, 'recovery_event')
        self.assertEqual(event.severity, IntelligenceSeverity.INFO)

    def test_build_replay_event(self):
        data = {
            'event_id': 'rp1',
            'source_phase': 'replay_system',
            'description': 'Replay completed',
            'severity': 'low',
        }
        event = self.builder.build_replay_event(data, tick=30)
        self.assertEqual(event.event_id, 'rp1')
        self.assertEqual(event.tick, 30)
        self.assertEqual(event.source_phase, 'replay_system')
        self.assertEqual(event.event_type, 'replay_event')
        self.assertEqual(event.description, 'Replay completed')
        self.assertEqual(event.severity, IntelligenceSeverity.LOW)

    def test_build_replay_event_defaults(self):
        event = self.builder.build_replay_event({}, tick=4)
        self.assertTrue(event.event_id.startswith('replay_'))
        self.assertEqual(event.source_phase, 'replay_system')
        self.assertEqual(event.event_type, 'replay_event')
        self.assertEqual(event.severity, IntelligenceSeverity.INFO)

    def test_parse_severity_invalid_fallback_to_info(self):
        data = {'severity': 'unknown_value'}
        event = self.builder.build_mismatch_event(data, tick=1)
        self.assertEqual(event.severity, IntelligenceSeverity.INFO)

    def test_parse_severity_case_sensitivity(self):
        data = {'severity': 'CRITICAL'}
        event = self.builder.build_mismatch_event(data, tick=1)
        self.assertEqual(event.severity, IntelligenceSeverity.INFO)


class TestCrossPhaseCorrelator(unittest.TestCase):
    """CrossPhaseCorrelator: time, source, chain correlation."""

    def setUp(self):
        self.correlator = CrossPhaseCorrelator(max_correlations=500)

    def test_correlate_by_time_empty_events(self):
        result = self.correlator.correlate_by_time([], window_ticks=5)
        self.assertEqual(result, [])

    def test_correlate_by_time_single_event_no_group(self):
        events = [_make_event('e1', 10)]
        result = self.correlator.correlate_by_time(events, window_ticks=5)
        self.assertEqual(result, [])

    def test_correlate_by_time_groups_close_events(self):
        events = [
            _make_event('e1', 10),
            _make_event('e2', 12),
            _make_event('e3', 11),
            _make_event('e4', 20),
        ]
        result = self.correlator.correlate_by_time(events, window_ticks=5)
        self.assertEqual(len(result), 1)
        group = result[0]
        self.assertEqual(group['event_count'], 3)
        self.assertIn('e1', group['event_ids'])
        self.assertIn('e2', group['event_ids'])
        self.assertIn('e3', group['event_ids'])
        self.assertNotIn('e4', group['event_ids'])

    def test_correlate_by_time_multiple_groups(self):
        events = [
            _make_event('e1', 10),
            _make_event('e2', 12),
            _make_event('e3', 30),
            _make_event('e4', 33),
        ]
        result = self.correlator.correlate_by_time(events, window_ticks=5)
        self.assertEqual(len(result), 2)

    def test_correlate_by_time_respects_window_boundary(self):
        events = [
            _make_event('e1', 10),
            _make_event('e2', 15),
        ]
        result = self.correlator.correlate_by_time(events, window_ticks=5)
        self.assertEqual(len(result), 1)
        result2 = self.correlator.correlate_by_time(events, window_ticks=1)
        self.assertEqual(len(result2), 0)

    def test_correlate_by_source_empty(self):
        result = self.correlator.correlate_by_source([])
        self.assertEqual(result, [])

    def test_correlate_by_source_single_event_no_group(self):
        events = [_make_event('e1', 1, source='alpha')]
        result = self.correlator.correlate_by_source(events)
        self.assertEqual(result, [])

    def test_correlate_by_source_groups_same_phase(self):
        events = [
            _make_event('e1', 1, source='alpha'),
            _make_event('e2', 2, source='alpha'),
            _make_event('e3', 3, source='beta'),
            _make_event('e4', 4, source='beta'),
        ]
        result = self.correlator.correlate_by_source(events)
        self.assertEqual(len(result), 2)
        source_labels = [g['correlation_id'] for g in result]
        self.assertIn('source_alpha', source_labels)
        self.assertIn('source_beta', source_labels)

    def test_correlate_by_source_ignores_single_source_events(self):
        events = [
            _make_event('e1', 1, source='alpha'),
            _make_event('e2', 2, source='beta'),
        ]
        result = self.correlator.correlate_by_source(events)
        self.assertEqual(result, [])

    def test_correlate_by_chain_empty(self):
        result = self.correlator.correlate_by_chain([], max_chain_depth=10)
        self.assertEqual(result, [])

    def test_correlate_by_chain_single_event_no_group(self):
        events = [_make_event('e1', 1)]
        result = self.correlator.correlate_by_chain(events)
        self.assertEqual(result, [])

    def test_correlate_by_chain_links_related_events(self):
        events = [
            _make_event('e1', 1, related=['e2']),
            _make_event('e2', 2, related=['e3']),
            _make_event('e3', 3),
            _make_event('e4', 4),
        ]
        result = self.correlator.correlate_by_chain(events)
        self.assertEqual(len(result), 1)
        chain = result[0]
        self.assertEqual(chain['event_count'], 3)
        self.assertIn('e1', chain['event_ids'])
        self.assertIn('e2', chain['event_ids'])
        self.assertIn('e3', chain['event_ids'])

    def test_cycle_detection_prevents_infinite_loop(self):
        events = [
            _make_event('e1', 1, related=['e2']),
            _make_event('e2', 2, related=['e3']),
            _make_event('e3', 3, related=['e1']),
        ]
        result = self.correlator.correlate_by_chain(events)
        self.assertEqual(len(result), 1)
        self.assertLessEqual(result[0]['event_count'], 3)

    def test_max_chain_depth_limit(self):
        events = [_make_event(f'e{i}', i, related=[f'e{i+1}']) for i in range(10)]
        events.append(_make_event('e10', 10))
        result = self.correlator.correlate_by_chain(events, max_chain_depth=3)
        self.assertGreater(len(result), 0)
        for chain in result:
            self.assertLessEqual(chain['event_count'], 4)

    def test_chain_multiple_independent_chains(self):
        events = [
            _make_event('a1', 1, related=['a2']),
            _make_event('a2', 2),
            _make_event('b1', 3, related=['b2']),
            _make_event('b2', 4),
        ]
        result = self.correlator.correlate_by_chain(events)
        self.assertEqual(len(result), 2)

    def test_build_correlation_includes_metadata(self):
        events = [
            _make_event('e1', 1, source='a', severity=IntelligenceSeverity.HIGH),
            _make_event('e2', 2, source='b', severity=IntelligenceSeverity.LOW),
        ]
        result = self.correlator.correlate_by_time(events, window_ticks=5)
        self.assertEqual(len(result), 1)
        group = result[0]
        self.assertIn('correlation_id', group)
        self.assertIn('event_count', group)
        self.assertIn('source_phases', group)
        self.assertIn('severities', group)
        self.assertIn('tick_start', group)
        self.assertIn('tick_end', group)
        self.assertIn('event_ids', group)
        self.assertEqual(group['event_count'], 2)
        self.assertEqual(group['tick_start'], 1)
        self.assertEqual(group['tick_end'], 2)

    def test_get_correlation_count(self):
        self.assertEqual(self.correlator.get_correlation_count(), 0)
        events = [
            _make_event('e1', 1, source='a'),
            _make_event('e2', 2, source='a'),
        ]
        self.correlator.correlate_by_source(events)
        self.assertEqual(self.correlator.get_correlation_count(), 1)
        self.correlator.correlate_by_time(events, window_ticks=5)
        self.assertEqual(self.correlator.get_correlation_count(), 2)

    def test_clear_resets_count(self):
        events = [
            _make_event('e1', 1, source='a'),
            _make_event('e2', 2, source='a'),
        ]
        self.correlator.correlate_by_source(events)
        self.assertGreater(self.correlator.get_correlation_count(), 0)
        self.correlator.clear()
        self.assertEqual(self.correlator.get_correlation_count(), 0)


class TestOperationalSequenceTracker(unittest.TestCase):
    """OperationalSequenceTracker: start, add, get, bounded."""

    def setUp(self):
        self.tracker = OperationalSequenceTracker(
            max_sequences=10, max_events_per_sequence=5,
        )

    def test_start_sequence_returns_sequence_dict(self):
        seq = self.tracker.start_sequence('seq1', tick=1, description='Test sequence')
        self.assertEqual(seq['sequence_id'], 'seq1')
        self.assertEqual(seq['tick_start'], 1)
        self.assertEqual(seq['tick_end'], 1)
        self.assertEqual(seq['description'], 'Test sequence')
        self.assertEqual(seq['event_count'], 0)
        self.assertEqual(seq['events'], [])
        self.assertTrue(seq['active'])

    def test_get_sequence_returns_same_data(self):
        self.tracker.start_sequence('seq1', tick=1, description='Test')
        seq = self.tracker.get_sequence('seq1')
        self.assertIsNotNone(seq)
        self.assertEqual(seq['sequence_id'], 'seq1')
        self.assertEqual(seq['description'], 'Test')

    def test_get_nonexistent_sequence_returns_none(self):
        result = self.tracker.get_sequence('nonexistent')
        self.assertIsNone(result)

    def test_add_event_to_sequence_returns_true(self):
        self.tracker.start_sequence('seq1', tick=1, description='Test')
        event = _make_event('e1', 5)
        result = self.tracker.add_to_sequence('seq1', event)
        self.assertTrue(result)

    def test_add_event_updates_tick_end(self):
        self.tracker.start_sequence('seq1', tick=1, description='Test')
        self.tracker.add_to_sequence('seq1', _make_event('e1', 10))
        seq = self.tracker.get_sequence('seq1')
        self.assertIsNotNone(seq)
        self.assertEqual(seq['tick_end'], 10)

    def test_add_event_increments_count(self):
        self.tracker.start_sequence('seq1', tick=1, description='Test')
        self.tracker.add_to_sequence('seq1', _make_event('e1', 2))
        self.tracker.add_to_sequence('seq1', _make_event('e2', 3))
        seq = self.tracker.get_sequence('seq1')
        self.assertIsNotNone(seq)
        self.assertEqual(seq['event_count'], 2)
        self.assertEqual(len(seq['events']), 2)

    def test_add_event_preserves_event_details(self):
        self.tracker.start_sequence('seq1', tick=1, description='Test')
        event = _make_event('e1', 5, event_type='alert',
                            severity=IntelligenceSeverity.HIGH,
                            desc='critical alert')
        self.tracker.add_to_sequence('seq1', event)
        seq = self.tracker.get_sequence('seq1')
        self.assertIsNotNone(seq)
        ev = seq['events'][0]
        self.assertEqual(ev['event_id'], 'e1')
        self.assertEqual(ev['tick'], 5)
        self.assertEqual(ev['event_type'], 'alert')
        self.assertEqual(ev['description'], 'critical alert')
        self.assertEqual(ev['severity'], 'high')

    def test_add_event_to_nonexistent_returns_false(self):
        event = _make_event('e1', 1)
        result = self.tracker.add_to_sequence('nonexistent', event)
        self.assertFalse(result)

    def test_max_events_per_sequence_returns_false_when_full(self):
        self.tracker.start_sequence('seq1', tick=1, description='Test')
        for i in range(5):
            result = self.tracker.add_to_sequence(
                'seq1', _make_event(f'e{i}', i),
            )
            self.assertTrue(result)
        result = self.tracker.add_to_sequence(
            'seq1', _make_event('e_extra', 99),
        )
        self.assertFalse(result)

    def test_max_sequences_bounded_evicts_oldest(self):
        tracker = OperationalSequenceTracker(
            max_sequences=3, max_events_per_sequence=10,
        )
        tracker.start_sequence('seq1', 1, 'First')
        tracker.start_sequence('seq2', 2, 'Second')
        tracker.start_sequence('seq3', 3, 'Third')
        tracker.start_sequence('seq4', 4, 'Fourth')
        self.assertEqual(tracker.get_sequence_count(), 3)
        self.assertIsNone(tracker.get_sequence('seq1'))
        self.assertIsNotNone(tracker.get_sequence('seq4'))

    def test_get_all_sequences_returns_list(self):
        self.tracker.start_sequence('a', 1, 'A')
        self.tracker.start_sequence('b', 2, 'B')
        all_seq = self.tracker.get_all_sequences()
        self.assertEqual(len(all_seq), 2)
        ids = [s['sequence_id'] for s in all_seq]
        self.assertIn('a', ids)
        self.assertIn('b', ids)

    def test_get_all_sequences_returns_copies(self):
        self.tracker.start_sequence('seq1', 1, 'Test')
        all_seq = self.tracker.get_all_sequences()
        all_seq[0]['description'] = 'mutated'
        original = self.tracker.get_sequence('seq1')
        self.assertIsNotNone(original)
        self.assertEqual(original['description'], 'Test')

    def test_get_sequence_count(self):
        self.assertEqual(self.tracker.get_sequence_count(), 0)
        self.tracker.start_sequence('a', 1, 'A')
        self.assertEqual(self.tracker.get_sequence_count(), 1)
        self.tracker.start_sequence('b', 2, 'B')
        self.assertEqual(self.tracker.get_sequence_count(), 2)

    def test_clear_removes_all_sequences(self):
        self.tracker.start_sequence('a', 1, 'A')
        self.tracker.start_sequence('b', 2, 'B')
        self.tracker.clear()
        self.assertEqual(self.tracker.get_sequence_count(), 0)
        self.assertEqual(self.tracker.get_all_sequences(), [])
        self.assertIsNone(self.tracker.get_sequence('a'))

"""Phase 4B: deterministic tests for replay forensics components."""
import unittest

from simulation.replay.forensics.forensic_analyzer import ForensicAnalyzer
from simulation.replay.forensics.incident_forensics import IncidentForensics
from simulation.replay.forensics.causal_forensics import CausalForensics
from simulation.replay.forensics.operational_evidence import OperationalEvidence


class TestForensicAnalyzer(unittest.TestCase):
    def test_record_evidence(self):
        fa = ForensicAnalyzer()
        result = fa.record_evidence(1, 'src_a', 'test evidence')
        self.assertEqual(result['tick'], 1)
        self.assertEqual(result['source'], 'src_a')

    def test_analyze_event_pattern_finds_matches(self):
        fa = ForensicAnalyzer()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'error_timeout',
             'source': 'sys', 'description': 'timed out'},
            {'event_id': 'e2', 'tick': 2, 'event_type': 'info',
             'source': 'sys', 'description': 'all good'},
        ]
        matches = fa.analyze_event_pattern(events, pattern_type='error')
        self.assertEqual(len(matches), 1)

    def test_analyze_event_pattern_no_matches(self):
        fa = ForensicAnalyzer()
        events = [
            {'event_id': 'e1', 'event_type': 'info', 'source': 'sys',
             'description': 'normal operation'},
        ]
        matches = fa.analyze_event_pattern(events, pattern_type='error')
        self.assertEqual(len(matches), 0)

    def test_analyze_event_pattern_empty_events(self):
        fa = ForensicAnalyzer()
        matches = fa.analyze_event_pattern([], pattern_type='error')
        self.assertEqual(matches, [])

    def test_analyze_event_pattern_matches_description(self):
        fa = ForensicAnalyzer()
        events = [
            {'event_id': 'e1', 'event_type': 'info', 'source': 'sys',
             'description': 'error occurred'},
        ]
        matches = fa.analyze_event_pattern(events, pattern_type='error')
        self.assertEqual(len(matches), 1)

    def test_get_evidence_count(self):
        fa = ForensicAnalyzer()
        self.assertEqual(fa.get_evidence_count(), 0)
        fa.record_evidence(1, 's', 'd')
        self.assertEqual(fa.get_evidence_count(), 1)

    def test_clear(self):
        fa = ForensicAnalyzer()
        fa.record_evidence(1, 's', 'd')
        fa.clear()
        self.assertEqual(fa.get_evidence_count(), 0)

    def test_analyze_event_pattern_case_insensitive(self):
        fa = ForensicAnalyzer()
        events = [
            {'event_id': 'e1', 'event_type': 'ERROR_TIMEOUT',
             'source': 'sys', 'description': 'Critical'},
        ]
        matches = fa.analyze_event_pattern(events, pattern_type='error')
        self.assertEqual(len(matches), 1)

    def test_bounded_evidence(self):
        fa = ForensicAnalyzer(max_evidence=2)
        for i in range(5):
            fa.record_evidence(i, 's', 'd')
        self.assertLessEqual(fa.get_evidence_count(), 2)

    def test_record_evidence_with_details(self):
        fa = ForensicAnalyzer()
        result = fa.record_evidence(1, 's', 'd', evidence_type='anomaly',
                                     related_events=['e1', 'e2'],
                                     details={'key': 'val'})
        self.assertEqual(result['evidence_id'][:3], 'ev_')


class TestIncidentForensics(unittest.TestCase):
    def test_analyze_incident_info_severity(self):
        fi = IncidentForensics()
        result = fi.analyze_incident('inc1', None, [])
        self.assertEqual(result['severity'], 'info')

    def test_analyze_incident_medium_severity(self):
        fi = IncidentForensics()
        events = [{'event_id': f'e{i}', 'tick': i, 'source': 's'}
                  for i in range(3)]
        result = fi.analyze_incident('inc1', None, events)
        self.assertEqual(result['severity'], 'medium')

    def test_analyze_incident_high_severity(self):
        fi = IncidentForensics()
        events = [{'event_id': f'e{i}', 'tick': i, 'source': 's'}
                  for i in range(6)]
        result = fi.analyze_incident('inc1', None, events)
        self.assertEqual(result['severity'], 'high')

    def test_analyze_incident_critical_severity(self):
        fi = IncidentForensics()
        events = [{'event_id': f'e{i}', 'tick': i, 'source': 's'}
                  for i in range(11)]
        result = fi.analyze_incident('inc1', None, events)
        self.assertEqual(result['severity'], 'critical')

    def test_analyze_incident_sources_involved(self):
        fi = IncidentForensics()
        events = [
            {'event_id': 'e1', 'tick': 1, 'source': 'sys_a'},
            {'event_id': 'e2', 'tick': 2, 'source': 'sys_b'},
        ]
        result = fi.analyze_incident('inc1', None, events)
        self.assertEqual(len(result['sources_involved']), 2)

    def test_analyze_incident_includes_trigger(self):
        fi = IncidentForensics()
        trigger = {'event_id': 'e_trigger', 'tick': 1, 'source': 'sys'}
        result = fi.analyze_incident('inc1', trigger, [])
        self.assertEqual(result['trigger']['event_id'], 'e_trigger')

    def test_analyze_incident_timeline_sorted(self):
        fi = IncidentForensics()
        events = [
            {'event_id': 'e2', 'tick': 5, 'source': 's'},
            {'event_id': 'e1', 'tick': 1, 'source': 's'},
        ]
        result = fi.analyze_incident('inc1', None, events)
        self.assertEqual(result['timeline'][0]['tick'], 1)

    def test_clear(self):
        fi = IncidentForensics()
        fi.analyze_incident('inc1', None, [])
        fi.clear()
        self.assertEqual(len(fi._forensic_history), 0)

    def test_analyze_incident_findings(self):
        fi = IncidentForensics()
        events = [{'event_id': 'e1', 'tick': 1, 'source': 's'}]
        result = fi.analyze_incident('inc1', None, events)
        self.assertIn('1 source(s)', result['findings'])


class TestCausalForensics(unittest.TestCase):
    def test_trace_causal_chain(self):
        cf = CausalForensics()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e2'},
        ]
        result = cf.trace_causal_chain(events, 'e3')
        self.assertEqual(result['depth'], 3)
        self.assertEqual(result['severity'], 'info')

    def test_trace_causal_chain_single(self):
        cf = CausalForensics()
        events = [{'event_id': 'e1', 'causal_parent': None}]
        result = cf.trace_causal_chain(events, 'e1')
        self.assertEqual(result['depth'], 1)
        self.assertEqual(result['severity'], 'info')

    def test_find_root_cause(self):
        cf = CausalForensics()
        events = [
            {'event_id': 'e1', 'causal_parent': None},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e2'},
        ]
        result = cf.find_root_cause(events, 'e3')
        self.assertEqual(result['root_event_id'], 'e1')

    def test_find_root_cause_unknown_event(self):
        cf = CausalForensics()
        result = cf.find_root_cause([], 'unknown')
        self.assertEqual(result['root_event_id'], 'unknown')

    def test_find_root_cause_no_parent(self):
        cf = CausalForensics()
        events = [{'event_id': 'e1', 'causal_parent': None}]
        result = cf.find_root_cause(events, 'e1')
        self.assertEqual(result['root_event_id'], 'e1')

    def test_trace_chain_cycle_detection(self):
        cf = CausalForensics()
        events = [
            {'event_id': 'e1', 'causal_parent': 'e3'},
            {'event_id': 'e2', 'causal_parent': 'e1'},
            {'event_id': 'e3', 'causal_parent': 'e2'},
        ]
        result = cf.trace_causal_chain(events, 'e1')
        self.assertLessEqual(result['depth'], 3)

    def test_trace_chain_bounded_at_100(self):
        cf = CausalForensics()
        events = []
        for i in range(150):
            parent = f'e{i - 1}' if i > 0 else None
            events.append({'event_id': f'e{i}', 'causal_parent': parent})
        result = cf.trace_causal_chain(events, 'e149')
        self.assertLessEqual(result['depth'], 101)

    def test_clear(self):
        cf = CausalForensics()
        cf.trace_causal_chain([{'event_id': 'e1', 'causal_parent': None}], 'e1')
        cf.clear()
        self.assertEqual(len(cf._forensic_history), 0)

    def test_find_root_cause_bounded(self):
        cf = CausalForensics()
        events = []
        for i in range(150):
            parent = f'e{i - 1}' if i > 0 else None
            events.append({'event_id': f'e{i}', 'causal_parent': parent})
        result = cf.find_root_cause(events, 'e149')
        self.assertIsNotNone(result['root_event_id'])


class TestOperationalEvidence(unittest.TestCase):
    def test_add_evidence(self):
        oe = OperationalEvidence()
        result = oe.add_evidence('ev1', tick=1, source='src_a',
                                  description='evidence item')
        self.assertEqual(result['evidence_id'], 'ev1')

    def test_get_evidence_chain(self):
        oe = OperationalEvidence()
        oe.add_evidence('ev1', tick=1, source='s', description='d1')
        oe.add_evidence('ev2', tick=5, source='s', description='d2')
        chain = oe.get_evidence_chain()
        self.assertEqual(len(chain), 2)

    def test_get_evidence_chain_since_tick(self):
        oe = OperationalEvidence()
        oe.add_evidence('ev1', tick=1, source='s', description='d1')
        oe.add_evidence('ev2', tick=5, source='s', description='d2')
        chain = oe.get_evidence_chain(since_tick=3)
        self.assertEqual(len(chain), 1)

    def test_get_evidence_count(self):
        oe = OperationalEvidence()
        self.assertEqual(oe.get_evidence_count(), 0)
        oe.add_evidence('ev1', tick=1, source='s', description='d')
        self.assertEqual(oe.get_evidence_count(), 1)

    def test_add_evidence_with_related_events(self):
        oe = OperationalEvidence()
        oe.add_evidence('ev1', tick=1, source='s', description='d',
                         related_events=['e1', 'e2'])
        chain = oe.get_evidence_chain()
        self.assertEqual(chain[0]['related_events'], ['e1', 'e2'])

    def test_clear(self):
        oe = OperationalEvidence()
        oe.add_evidence('ev1', tick=1, source='s', description='d')
        oe.clear()
        self.assertEqual(oe.get_evidence_count(), 0)

    def test_bounded_evidence_chain(self):
        oe = OperationalEvidence(max_evidence=2)
        for i in range(5):
            oe.add_evidence(f'ev{i}', tick=i, source='s', description='d')
        self.assertEqual(len(oe._evidence_chain), 2)

    def test_get_evidence_chain_empty(self):
        oe = OperationalEvidence()
        chain = oe.get_evidence_chain()
        self.assertEqual(chain, [])

    def test_add_evidence_with_details(self):
        oe = OperationalEvidence()
        oe.add_evidence('ev1', tick=1, source='s', description='d',
                         details={'metric': 42})
        chain = oe.get_evidence_chain()
        self.assertEqual(chain[0]['evidence_id'], 'ev1')


if __name__ == '__main__':
    unittest.main()

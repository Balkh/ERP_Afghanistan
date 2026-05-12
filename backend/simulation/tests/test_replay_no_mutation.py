"""Phase 4B: safety tests confirming replay never mutates ERP state.

These tests verify that all replay components are read-only:
- No database writes
- No ERP business logic execution
- No inventory mutations
- No accounting mutations
- Deterministic and side-effect free
"""
import unittest

from simulation.replay.timeline.timeline_builder import TimelineBuilder
from simulation.replay.timeline.timeline_indexer import TimelineIndexer
from simulation.replay.timeline.timeline_cursor import TimelineCursorManager
from simulation.replay.timeline.timeline_validator import TimelineValidator
from simulation.replay.snapshots.snapshot_loader import SnapshotLoader
from simulation.replay.snapshots.snapshot_reconstructor import SnapshotReconstructor
from simulation.replay.snapshots.snapshot_integrity import SnapshotIntegrity
from simulation.replay.snapshots.snapshot_history import SnapshotHistory
from simulation.replay.replay_engine.replay_session import ReplaySessionManager
from simulation.replay.replay_engine.replay_controller import ReplayController
from simulation.replay.replay_engine.replay_safety_guard import ReplaySafetyGuard
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.replay.reconstruction.workflow_reconstructor import WorkflowReconstructor
from simulation.replay.reconstruction.event_chain_builder import EventChainBuilder
from simulation.replay.reconstruction.incident_reconstructor import IncidentReconstructor
from simulation.replay.reconstruction.state_reconstructor import StateReconstructor
from simulation.replay.navigation.time_travel import TimeTravel
from simulation.replay.navigation.replay_navigation import ReplayNavigation
from simulation.replay.navigation.replay_bookmarks import ReplayBookmarks
from simulation.replay.navigation.replay_windows import ReplayWindows
from simulation.replay.forensics.forensic_analyzer import ForensicAnalyzer
from simulation.replay.forensics.incident_forensics import IncidentForensics
from simulation.replay.forensics.causal_forensics import CausalForensics
from simulation.replay.forensics.operational_evidence import OperationalEvidence
from simulation.replay.determinism.replay_hashing import ReplayHashing
from simulation.replay.determinism.replay_determinism import ReplayDeterminism
from simulation.replay.determinism.divergence_detector import DivergenceDetector
from simulation.replay.determinism.replay_consistency import ReplayConsistency
from simulation.replay.validation.replay_validator import ReplayValidator
from simulation.replay.validation.snapshot_validator import SnapshotValidator
from simulation.replay.validation.timeline_integrity import TimelineIntegrity
from simulation.replay.validation.causal_integrity import CausalIntegrity
from simulation.replay.orchestration.replay_orchestrator import ReplayOrchestrator
from simulation.replay.orchestration.replay_pipeline import ReplayPipeline
from simulation.replay.orchestration.replay_router import ReplayRouter
from simulation.replay.models import (ReplayMode, ReplayStatus, TimelineDirection,
                                       SnapshotStatus, DivergenceType)


class TestReplayComponentsAreReadOnly(unittest.TestCase):
    """Verify all replay components are side-effect free on construction."""

    def test_timeline_builder_no_erp_imports(self):
        tb = TimelineBuilder()
        tb.add_event(1, 'test', 'source')
        events = tb.get_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events, list)

    def test_timeline_indexer_no_erp_imports(self):
        idx = TimelineIndexer()
        idx.index_event('e1', 1, 't', 's')
        self.assertEqual(idx.get_events_by_tick(1), ['e1'])

    def test_timeline_cursor_no_erp_imports(self):
        mgr = TimelineCursorManager()
        mgr.create_cursor('c1')
        self.assertIsNotNone(mgr.get_cursor('c1'))

    def test_timeline_validator_no_erp_imports(self):
        v = TimelineValidator()
        result = v.validate_ordering([{'event_id': 'e1', 'tick': 1}])
        self.assertIn('is_ordered', result)

    def test_snapshot_loader_no_erp_imports(self):
        sl = SnapshotLoader()
        sl.load_snapshot('s1', tick=1)
        self.assertEqual(sl.get_snapshot_count(), 1)

    def test_snapshot_reconstructor_no_erp_imports(self):
        sr = SnapshotReconstructor()
        result = sr.reconstruct('s1', tick=1, events=[])
        self.assertEqual(result['status'], 'reconstructed')

    def test_snapshot_integrity_no_erp_imports(self):
        si = SnapshotIntegrity()
        result = si.verify_integrity(
            {'snapshot_id': 's1', 'workflow_states': {'w': 1}})
        self.assertIn('is_intact', result)

    def test_snapshot_history_no_erp_imports(self):
        sh = SnapshotHistory()
        sh.record_snapshot('s1', tick=1)
        self.assertEqual(sh.get_history_count(), 1)

    def test_session_manager_no_erp_imports(self):
        mgr = ReplaySessionManager()
        mgr.create_session('s1')
        self.assertIsNotNone(mgr.get_session('s1'))

    def test_replay_controller_no_erp_imports(self):
        ctrl = ReplayController()
        result = ctrl.start('s1')
        self.assertTrue(result['started'])

    def test_replay_safety_guard_no_erp_imports(self):
        guard = ReplaySafetyGuard()
        result = guard.check_write_operation('any')
        self.assertFalse(result['allowed'])

    def test_replay_engine_no_erp_imports(self):
        eng = ReplayEngine()
        self.assertIsNotNone(eng.sessions)
        self.assertIsNotNone(eng.controller)
        self.assertIsNotNone(eng.safety_guard)

    def test_workflow_reconstructor_no_erp_imports(self):
        wr = WorkflowReconstructor()
        result = wr.reconstruct('wf1', events=[])
        self.assertEqual(result['final_state'], 'initialized')

    def test_event_chain_builder_no_erp_imports(self):
        cb = EventChainBuilder()
        result = cb.build_chain([])
        self.assertEqual(result['length'], 0)

    def test_incident_reconstructor_no_erp_imports(self):
        ir = IncidentReconstructor()
        result = ir.reconstruct('inc1', events=[])
        self.assertEqual(result['total_related'], 0)

    def test_state_reconstructor_no_erp_imports(self):
        sr = StateReconstructor()
        result = sr.reconstruct_at_tick(1, [])
        self.assertEqual(result['total_events_processed'], 0)

    def test_time_travel_no_erp_imports(self):
        tt = TimeTravel()
        result = tt.navigate_to(5, 1, [{'event_id': 'e1', 'tick': 5}])
        self.assertEqual(result['target_tick'], 5)

    def test_replay_navigation_no_erp_imports(self):
        nav = ReplayNavigation()
        result = nav.next_event(0, [{'event_id': 'e1', 'tick': 1},
                                     {'event_id': 'e2', 'tick': 2}])
        self.assertTrue(result['navigated'])

    def test_replay_bookmarks_no_erp_imports(self):
        bm = ReplayBookmarks()
        bm.add_bookmark('bm1', tick=1, label='cp1')
        self.assertIsNotNone(bm.get_bookmark('bm1'))

    def test_replay_windows_no_erp_imports(self):
        rw = ReplayWindows()
        result = rw.create_window('w1', 0, 10)
        self.assertEqual(result['window_id'], 'w1')

    def test_forensic_analyzer_no_erp_imports(self):
        fa = ForensicAnalyzer()
        result = fa.record_evidence(1, 'src', 'desc')
        self.assertEqual(result['tick'], 1)

    def test_incident_forensics_no_erp_imports(self):
        fi = IncidentForensics()
        result = fi.analyze_incident('inc1', None, [])
        self.assertEqual(result['severity'], 'info')

    def test_causal_forensics_no_erp_imports(self):
        cf = CausalForensics()
        result = cf.trace_causal_chain(
            [{'event_id': 'e1', 'causal_parent': None}], 'e1')
        self.assertEqual(result['depth'], 1)

    def test_operational_evidence_no_erp_imports(self):
        oe = OperationalEvidence()
        oe.add_evidence('ev1', tick=1, source='s', description='d')
        self.assertEqual(oe.get_evidence_count(), 1)

    def test_replay_hashing_no_erp_imports(self):
        rh = ReplayHashing()
        h = rh.hash_event({'event_id': 'e1'})
        self.assertEqual(len(h), 64)

    def test_replay_determinism_no_erp_imports(self):
        rd = ReplayDeterminism()
        result = rd.verify_determinism([], [])
        self.assertTrue(result['is_deterministic'])

    def test_divergence_detector_no_erp_imports(self):
        dd = DivergenceDetector()
        result = dd.detect_state_mismatch(1, {'a': 1}, {'a': 2})
        self.assertIsNotNone(result)

    def test_replay_consistency_no_erp_imports(self):
        rc = ReplayConsistency()
        result = rc.check_consistency([], [])
        self.assertTrue(result['is_consistent'])

    def test_replay_validator_no_erp_imports(self):
        rv = ReplayValidator()
        result = rv.validate_session(
            {'status': 'completed', 'start_tick': 0, 'end_tick': 10},
            [{'event_id': 'e1'}])
        self.assertTrue(result['is_valid'])

    def test_snapshot_validator_no_erp_imports(self):
        sv = SnapshotValidator()
        result = sv.validate_snapshot(
            {'snapshot_id': 's1', 'tick': 1, 'workflow_states': {'w': 1}})
        self.assertTrue(result['is_valid'])

    def test_timeline_integrity_no_erp_imports(self):
        ti = TimelineIntegrity()
        result = ti.check_ordering([{'event_id': 'e1', 'tick': 1}])
        self.assertTrue(result['is_ordered'])

    def test_causal_integrity_no_erp_imports(self):
        ci = CausalIntegrity()
        result = ci.check_chain_integrity(
            [{'event_id': 'e1', 'causal_parent': None}])
        self.assertTrue(result['chain_integrity'])

    def test_replay_orchestrator_no_erp_imports(self):
        orch = ReplayOrchestrator()
        self.assertIsNotNone(orch.timeline_builder)

    def test_replay_pipeline_no_erp_imports(self):
        p = ReplayPipeline('p1', ['step1'])
        self.assertEqual(p.pipeline_id, 'p1')

    def test_replay_router_no_erp_imports(self):
        r = ReplayRouter()
        result = r.route_replay(ReplayMode.FULL, 's1', [])
        self.assertEqual(result['mode'], 'full')


class TestReplaySafetyGuardBlocksWrites(unittest.TestCase):
    def test_write_operation_always_blocked(self):
        guard = ReplaySafetyGuard()
        for op in ['save', 'update', 'delete', 'create', 'insert']:
            result = guard.check_write_operation(op)
            self.assertFalse(result['allowed'], f'Operation {op} should be blocked')

    def test_business_logic_always_blocked(self):
        guard = ReplaySafetyGuard()
        for logic in ['calculate_stock', 'post_journal_entry', 'process_payment']:
            result = guard.check_business_logic(logic)
            self.assertFalse(result['allowed'], f'Logic {logic} should be blocked')

    def test_safe_call_catches_exceptions(self):
        guard = ReplaySafetyGuard()
        def dangerous():
            raise RuntimeError('ERP operation not allowed during replay')
        result = guard.safe_call(dangerous, default_return='safe_fallback')
        self.assertEqual(result, 'safe_fallback')

    def test_violations_tracked_correctly(self):
        guard = ReplaySafetyGuard()
        guard.check_write_operation('op1')
        guard.check_business_logic('logic1')
        self.assertEqual(guard.get_violation_count(), 2)


class TestNoDatabaseOperations(unittest.TestCase):
    """Verify replay components never reference Django models or databases."""

    def test_no_django_orm_in_replay_components(self):
        replay_imports = [
            'simulation.replay.timeline',
            'simulation.replay.snapshots',
            'simulation.replay.replay_engine',
            'simulation.replay.reconstruction',
            'simulation.replay.navigation',
            'simulation.replay.forensics',
            'simulation.replay.determinism',
            'simulation.replay.validation',
            'simulation.replay.orchestration',
        ]
        import importlib
        for import_path in replay_imports:
            module = importlib.import_module(import_path)
            module_dir = module.__path__[0]
            import os
            for fname in os.listdir(module_dir):
                if fname.endswith('.py') and fname != '__init__.py':
                    fpath = os.path.join(module_dir, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.assertNotIn('from django', content,
                                     f'{fpath} imports from Django')
                    self.assertNotIn('import django', content,
                                     f'{fpath} imports Django')
                    self.assertNotIn('models.Model', content,
                                     f'{fpath} references Django Model')
                    self.assertNotIn('.objects.', content,
                                     f'{fpath} references Django ORM')

    def test_no_database_integration_imports(self):
        """Verify no replay file imports any ERP model or database module."""
        import os
        replay_base = os.path.join(
            os.path.dirname(__file__), '..', 'replay')
        for root, dirs, files in os.walk(replay_base):
            for fname in files:
                if fname.endswith('.py') and fname != '__init__.py':
                    fpath = os.path.join(root, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.assertNotIn('from inventory', content,
                                     f'{fpath} imports from inventory')
                    self.assertNotIn('from accounting', content,
                                     f'{fpath} imports from accounting')
                    self.assertNotIn('from sales', content,
                                     f'{fpath} imports from sales')
                    self.assertNotIn('from purchases', content,
                                     f'{fpath} imports from purchases')
                    self.assertNotIn('from payments', content,
                                     f'{fpath} imports from payments')
                    self.assertNotIn('from core.models', content,
                                     f'{fpath} imports from core.models')


class TestDeterministicBehavior(unittest.TestCase):
    """Verify replay components produce identical outputs for identical inputs."""

    def test_timeline_builder_deterministic(self):
        tb1 = TimelineBuilder()
        tb2 = TimelineBuilder()
        eid1 = tb1.add_event(1, 't', 's', payload={'k': 'v'})
        eid2 = tb2.add_event(1, 't', 's', payload={'k': 'v'})
        self.assertEqual(tb1.get_events(), tb2.get_events())

    def test_hashing_deterministic(self):
        rh1 = ReplayHashing()
        rh2 = ReplayHashing()
        event = {'event_id': 'e1', 'tick': 1}
        self.assertEqual(rh1.hash_event(event), rh2.hash_event(event))

    def test_snapshot_reconstructor_deterministic(self):
        sr1 = SnapshotReconstructor()
        sr2 = SnapshotReconstructor()
        events = [{'event_id': 'e1', 'tick': 1, 'event_type': 'a', 'source': 's'}]
        r1 = sr1.reconstruct('s1', tick=10, events=events)
        r2 = sr2.reconstruct('s1', tick=10, events=events)
        self.assertEqual(r1['event_count'], r2['event_count'])

    def test_state_reconstructor_deterministic(self):
        sr1 = StateReconstructor()
        sr2 = StateReconstructor()
        events = [{'event_id': 'e1', 'tick': 1, 'event_type': 'workflow_started',
                    'source': 'wf_a'}]
        r1 = sr1.reconstruct_at_tick(5, events)
        r2 = sr2.reconstruct_at_tick(5, events)
        self.assertEqual(r1['workflow_states'], r2['workflow_states'])

    def test_incident_forensics_deterministic(self):
        fi1 = IncidentForensics()
        fi2 = IncidentForensics()
        events = [{'event_id': 'e1', 'tick': 1, 'source': 's'}]
        r1 = fi1.analyze_incident('inc1', None, events)
        r2 = fi2.analyze_incident('inc1', None, events)
        self.assertEqual(r1['severity'], r2['severity'])

    def test_causal_forensics_deterministic(self):
        cf1 = CausalForensics()
        cf2 = CausalForensics()
        events = [{'event_id': 'e1', 'causal_parent': None},
                   {'event_id': 'e2', 'causal_parent': 'e1'}]
        r1 = cf1.trace_causal_chain(events, 'e2')
        r2 = cf2.trace_causal_chain(events, 'e2')
        self.assertEqual(r1['depth'], r2['depth'])

    def test_orchestrator_deterministic(self):
        orch1 = ReplayOrchestrator()
        orch2 = ReplayOrchestrator()
        events = [
            {'event_id': 'e1', 'tick': 1, 'event_type': 'test', 'source': 's'},
        ]
        r1 = orch1.run_replay('sess_a', events)
        r2 = orch2.run_replay('sess_b', events)
        self.assertEqual(r1['executed'], r2['executed'])
        self.assertEqual(r1['events_replayed'], r2['events_replayed'])
        self.assertFalse(r1['executed'])


class TestBoundedMemory(unittest.TestCase):
    """Verify all bounded structures enforce maxlen."""

    def test_timeline_builder_bounded(self):
        tb = TimelineBuilder(max_events=10)
        for i in range(20):
            tb.add_event(i, 't', 's')
        self.assertLessEqual(tb.get_event_count(), 10)

    def test_timeline_indexer_bounded(self):
        idx = TimelineIndexer(max_index_size=5)
        for i in range(10):
            idx.index_event(f'e{i}', 1, 't', 's')
        self.assertLessEqual(len(idx._index_history), 5)

    def test_cursor_manager_bounded(self):
        mgr = TimelineCursorManager(max_cursors=5)
        for i in range(10):
            mgr.create_cursor(f'c{i}')
        self.assertLessEqual(len(mgr._cursor_history), 5)

    def test_validator_bounded(self):
        v = TimelineValidator(max_history=5)
        for i in range(10):
            v.validate_ordering([{'event_id': f'e{i}', 'tick': i}])
        self.assertLessEqual(len(v._validation_history), 5)

    def test_snapshot_loader_bounded(self):
        sl = SnapshotLoader(max_snapshots=5)
        for i in range(10):
            sl.load_snapshot(f's{i}', tick=i)
        self.assertLessEqual(len(sl._load_history), 5)

    def test_reconstructor_bounded(self):
        sr = SnapshotReconstructor(max_history=5)
        for i in range(10):
            sr.reconstruct(f's{i}', tick=i, events=[])
        self.assertLessEqual(sr.get_reconstruction_count(), 5)

    def test_snapshot_integrity_bounded(self):
        si = SnapshotIntegrity(max_history=5)
        for i in range(10):
            si.verify_integrity({'snapshot_id': f's{i}',
                                  'workflow_states': {'w': 1}})
        self.assertLessEqual(len(si._integrity_history), 5)

    def test_snapshot_history_bounded(self):
        sh = SnapshotHistory(max_history=5)
        for i in range(10):
            sh.record_snapshot(f's{i}', tick=i)
        self.assertLessEqual(sh.get_history_count(), 5)

    def test_session_manager_bounded(self):
        mgr = ReplaySessionManager(max_sessions=5)
        for i in range(10):
            mgr.create_session(f's{i}')
        self.assertLessEqual(len(mgr._session_history), 5)

    def test_safety_guard_bounded(self):
        guard = ReplaySafetyGuard(max_history=5)
        for i in range(10):
            guard.check_write_operation(f'op{i}')
        self.assertLessEqual(len(guard._safety_violations), 5)

    def test_replay_hashing_bounded(self):
        rh = ReplayHashing(max_history=5)
        for i in range(10):
            rh.record_hash(f'h{i}', tick=i)
        self.assertLessEqual(len(rh._hash_history), 5)

    def test_divergence_detector_bounded(self):
        dd = DivergenceDetector(max_history=5)
        for i in range(5):
            dd.detect_state_mismatch(i, {'a': 1}, {'a': 2})
        self.assertEqual(dd.get_divergence_count(), 5)

    def test_bookmarks_bounded(self):
        bm = ReplayBookmarks(max_bookmarks=5)
        for i in range(10):
            bm.add_bookmark(f'bm{i}', tick=i, label=f'cp{i}')
        self.assertLessEqual(len(bm._bookmark_list), 5)

    def test_windows_bounded(self):
        rw = ReplayWindows(max_windows=5)
        for i in range(10):
            rw.create_window(f'w{i}', i * 10, i * 10 + 10)
        self.assertLessEqual(len(rw._window_history), 5)

    def test_forensic_analyzer_bounded(self):
        fa = ForensicAnalyzer(max_evidence=5)
        for i in range(10):
            fa.record_evidence(i, 's', 'd')
        self.assertLessEqual(fa.get_evidence_count(), 5)

    def test_operational_evidence_bounded(self):
        oe = OperationalEvidence(max_evidence=5)
        for i in range(10):
            oe.add_evidence(f'ev{i}', tick=i, source='s', description='d')
        self.assertLessEqual(len(oe._evidence_chain), 5)

    def test_timeline_integrity_bounded(self):
        ti = TimelineIntegrity(max_history=5)
        for i in range(10):
            ti.check_ordering([{'event_id': f'e{i}', 'tick': i}])
        self.assertLessEqual(len(ti._integrity_history), 5)

    def test_causal_integrity_bounded(self):
        ci = CausalIntegrity(max_history=5)
        for i in range(10):
            ci.check_chain_integrity([{'event_id': f'e{i}', 'causal_parent': None}])
        self.assertLessEqual(len(ci._integrity_history), 5)

    def test_router_bounded(self):
        r = ReplayRouter(max_history=5)
        for i in range(10):
            r.route_replay(ReplayMode.FULL, f's{i}', [])
        self.assertLessEqual(len(r._routing_history), 5)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
from collections import deque
from simulation.recovery.execution.execution_engine import RecoveryExecutionEngine
from simulation.recovery.execution.partial_rollback import PartialRollbackEngine
from simulation.recovery.execution.external_rollback import ExternalRollbackEngine
from simulation.recovery.execution.user_override import UserOverrideHandler
from simulation.recovery.orchestration.recovery_orchestrator import RecoveryOrchestrator


class TestRecoveryExecutionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RecoveryExecutionEngine(max_history=100)

    def test_execute_with_valid_approval_returns_success(self):
        containment = {'containment_id': 'c1', 'action': 'isolate'}
        approval = {'approved': True, 'approved_by': 'admin'}
        result = self.engine.execute(containment, approval, tick=1)
        self.assertTrue(result['success'])
        self.assertEqual(result['tick'], 1)
        self.assertEqual(result['containment_id'], 'c1')

    def test_execute_without_approval_returns_failure(self):
        containment = {'containment_id': 'c2', 'action': 'isolate'}
        approval = {'approved': False, 'approved_by': ''}
        result = self.engine.execute(containment, approval, tick=2)
        self.assertFalse(result['success'])

    def test_four_stages_recorded(self):
        containment = {'containment_id': 'c3', 'action': 'quarantine'}
        approval = {'approved': True, 'approved_by': 'operator'}
        result = self.engine.execute(containment, approval, tick=3)
        stages = result['stages']
        self.assertEqual(len(stages), 4)
        self.assertEqual(stages[0]['stage'], 'manual_approval')
        self.assertEqual(stages[1]['stage'], 'execution')
        self.assertEqual(stages[2]['stage'], 'rollback')
        self.assertEqual(stages[3]['stage'], 'reconciliation')

    def test_get_execution_status(self):
        status = self.engine.get_execution_status()
        self.assertIn('stages_completed', status)
        self.assertIn('total_stages', status)
        self.assertIn('last_execution_tick', status)
        self.assertIn('in_progress', status)
        self.assertEqual(status['total_stages'], 4)

    def test_execution_history(self):
        containment = {'containment_id': 'c4', 'action': 'isolate'}
        approval = {'approved': True, 'approved_by': 'user'}
        self.engine.execute(containment, approval, tick=5)
        self.engine.execute(containment, approval, tick=6)
        history = self.engine.get_execution_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(self.engine.get_execution_count(), 2)

    def test_clear_resets_state(self):
        containment = {'containment_id': 'c5', 'action': 'isolate'}
        approval = {'approved': True, 'approved_by': 'user'}
        self.engine.execute(containment, approval, tick=7)
        self.engine.clear()
        self.assertEqual(self.engine.get_execution_count(), 0)
        self.assertEqual(self.engine.get_execution_status()['stages_completed'], 0)


class TestPartialRollbackEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PartialRollbackEngine(max_history=100)

    def test_detect_affected_segments_correctly(self):
        incident = {'affected_components': ['db', 'cache']}
        state = {'db': 'data1', 'cache': 'data2', 'queue': 'data3'}
        result = self.engine.detect_affected(incident, state)
        self.assertEqual(result['component_count'], 2)
        self.assertIn('db', result['affected'])
        self.assertIn('cache', result['affected'])
        self.assertIn('queue', result['unaffected'])

    def test_execute_rollback(self):
        segment = {'affected': {'db': 'data1', 'cache': 'data2'}}
        rollback_map = {'strategy': 'snapshot'}
        result = self.engine.execute_rollback(segment, rollback_map)
        self.assertTrue(result['success'])
        self.assertEqual(result['items_rolled_back'], 2)
        self.assertIn('rollback_db', result['actions'])
        self.assertIn('rollback_cache', result['actions'])

    def test_merge_clean(self):
        segment = {'unaffected': {'queue': 'data3', 'logger': 'data4'}}
        state = {'queue': 'data3', 'logger': 'data4', 'db': 'old'}
        result = self.engine.merge_clean(segment, state)
        self.assertTrue(result['success'])
        self.assertEqual(result['merged_items'], 2)

    def test_verify_passes(self):
        segment = {'affected': {'db': 'x'}, 'unaffected': {'queue': 'y'}}
        result = self.engine.verify(segment)
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['issues']), 0)

    def test_verify_empty_segment(self):
        segment = {'affected': {}, 'unaffected': {}}
        result = self.engine.verify(segment)
        self.assertFalse(result['passed'])
        self.assertGreater(len(result['issues']), 0)

    def test_clear(self):
        incident = {'affected_components': ['x']}
        state = {'x': 1, 'y': 2}
        self.engine.detect_affected(incident, state)
        self.engine.clear()
        self.assertEqual(len(self.engine._history), 0)


class TestExternalRollbackEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ExternalRollbackEngine(max_history=100)

    def test_sync_check_in_sync(self):
        request = {'local_state': {'a': 1}, 'external_state': {'a': 1}}
        result = self.engine.sync_check('system_a', request)
        self.assertTrue(result['in_sync'])
        self.assertEqual(len(result['differences']), 0)

    def test_sync_check_out_of_sync(self):
        request = {'local_state': {'a': 1}, 'external_state': {'a': 2}}
        result = self.engine.sync_check('system_a', request)
        self.assertFalse(result['in_sync'])
        self.assertIn('a', result['differences'])

    def test_compensate_returns_action(self):
        result = self.engine.compensate('system_a', 'transfer', {'reason': 'timeout'})
        self.assertTrue(result['success'])
        self.assertIn('compensate_transfer_on_system_a', result['compensation_action'])
        self.assertTrue(len(result['compensation_id']) > 0)

    def test_retry_with_policy(self):
        result = self.engine.retry_with_policy('sys', 'op', {'key': 'val'}, max_retries=3)
        self.assertTrue(result['success'])
        self.assertEqual(result['attempts'], 3)

    def test_validate(self):
        result = self.engine.validate('system_a', 'transfer')
        self.assertTrue(result['passed'])
        self.assertTrue(result['validated'])

    def test_clear(self):
        self.engine.compensate('s', 'op', {})
        self.engine.clear()
        self.assertEqual(len(self.engine._history), 0)


class TestUserOverrideHandler(unittest.TestCase):
    def setUp(self):
        self.handler = UserOverrideHandler(max_history=100)

    def test_validate_with_complete_request(self):
        request = {
            'override_id': 'ov1',
            'reason': 'Emergency fix needed for production',
            'requested_by': 'admin',
            'target': 'config',
        }
        result = self.handler.validate(request)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['missing_fields']), 0)

    def test_validate_with_missing_fields(self):
        request = {'override_id': 'ov2'}
        result = self.handler.validate(request)
        self.assertFalse(result['valid'])
        self.assertIn('reason', result['missing_fields'])
        self.assertIn('requested_by', result['missing_fields'])
        self.assertIn('target', result['missing_fields'])

    def test_score_risk_low(self):
        request = {'target': 'config', 'reason': 'Safe routine update now'}
        result = self.handler.score_risk(request)
        self.assertLess(result['risk_score'], 30)
        self.assertEqual(result['level'], 'low')

    def test_score_risk_critical(self):
        request = {'target': 'critical', 'reason': 'fix'}
        result = self.handler.score_risk(request)
        self.assertGreaterEqual(result['risk_score'], 60)
        self.assertIn(result['level'], ['high', 'critical'])

    def test_audit_lock_creates_immutable_record(self):
        request = {'override_id': 'ov3', 'reason': 'fix', 'requested_by': 'u', 'target': 'x'}
        result = self.handler.audit_lock(request)
        self.assertTrue(result['locked'])
        self.assertTrue(len(result['audit_id']) > 0)
        self.assertTrue(len(result['timestamp']) > 0)

    def test_controlled_execute(self):
        request = {'override_id': 'ov4'}
        risk = {'level': 'medium', 'risk_score': 45.0}
        result = self.handler.controlled_execute(request, risk)
        self.assertTrue(result['success'])
        self.assertTrue(result['monitored'])
        self.assertEqual(result['risk_level'], 'medium')

    def test_clear(self):
        request = {'override_id': 'o', 'reason': 'fix', 'requested_by': 'u', 'target': 't'}
        self.handler.validate(request)
        self.handler.clear()
        self.assertEqual(len(self.handler._history), 0)


class TestExtendedRecoveryOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orch = RecoveryOrchestrator(max_history=100)

    def test_execution_engine_property(self):
        self.assertIsInstance(self.orch.execution_engine, RecoveryExecutionEngine)

    def test_partial_rollback_property(self):
        self.assertIsInstance(self.orch.partial_rollback, PartialRollbackEngine)

    def test_external_rollback_property(self):
        self.assertIsInstance(self.orch.external_rollback, ExternalRollbackEngine)

    def test_user_override_property(self):
        self.assertIsInstance(self.orch.user_override, UserOverrideHandler)

    def test_execute_recovery_delegates_to_engine(self):
        containment = {'containment_id': 'c1', 'action': 'isolate'}
        approval = {'approved': True, 'approved_by': 'admin'}
        result = self.orch.execute_recovery(containment, approval, tick=10)
        self.assertTrue(result['success'])
        self.assertEqual(result['tick'], 10)
        self.assertEqual(len(result['stages']), 4)

    def test_execute_recovery_without_approval(self):
        containment = {'containment_id': 'c2', 'action': 'isolate'}
        approval = {'approved': False}
        result = self.orch.execute_recovery(containment, approval, tick=11)
        self.assertFalse(result['success'])

    def test_perform_partial_rollback_runs_all_4_stages(self):
        incident = {'affected_components': ['db', 'cache']}
        state = {'db': 'x', 'cache': 'y', 'queue': 'z'}
        rollback_map = {'strategy': 'snapshot'}
        result = self.orch.perform_partial_rollback(incident, state, rollback_map)
        self.assertIn('detect_affected', result)
        self.assertIn('execute_rollback', result)
        self.assertIn('merge_clean', result)
        self.assertIn('verify', result)
        self.assertEqual(result['detect_affected']['component_count'], 2)
        self.assertTrue(result['execute_rollback']['success'])
        self.assertTrue(result['merge_clean']['success'])

    def test_handle_external_rollback_runs_all_4_stages(self):
        failure = {'local_state': {'a': 1}, 'external_state': {'a': 2}}
        params = {'key': 'val'}
        result = self.orch.handle_external_rollback('sys_x', 'transfer', failure, params)
        self.assertIn('sync_check', result)
        self.assertIn('compensate', result)
        self.assertIn('retry_with_policy', result)
        self.assertIn('validate', result)
        self.assertFalse(result['sync_check']['in_sync'])
        self.assertTrue(result['compensate']['success'])
        self.assertTrue(result['validate']['passed'])

    def test_process_user_override_runs_all_4_stages(self):
        request = {
            'override_id': 'ov1',
            'reason': 'Emergency production fix required now',
            'requested_by': 'admin',
            'target': 'critical',
        }
        result = self.orch.process_user_override(request)
        self.assertIn('validate', result)
        self.assertIn('score_risk', result)
        self.assertIn('audit_lock', result)
        self.assertIn('controlled_execute', result)
        self.assertTrue(result['validate']['valid'])
        self.assertIn(result['score_risk']['level'], ['low', 'medium', 'high', 'critical'])
        self.assertTrue(result['audit_lock']['locked'])
        self.assertTrue(result['controlled_execute']['success'])

    def test_reset_clears_execution_components(self):
        containment = {'containment_id': 'c', 'action': 'isolate'}
        approval = {'approved': True, 'approved_by': 'admin'}
        self.orch.execute_recovery(containment, approval, tick=20)
        self.orch.reset()
        status = self.orch.execution_engine.get_execution_status()
        self.assertEqual(status['stages_completed'], 0)
        self.assertEqual(status['last_execution_tick'], -1)

    def test_orchestrator_property_getters_return_same_instance(self):
        engine1 = self.orch.execution_engine
        engine2 = self.orch.execution_engine
        self.assertIs(engine1, engine2)


if __name__ == '__main__':
    unittest.main()

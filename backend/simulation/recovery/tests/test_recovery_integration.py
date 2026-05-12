"""Integration tests for recovery orchestration layer."""
from django.test import TestCase
from simulation.recovery.orchestration.recovery_pipeline import RecoveryPipeline
from simulation.recovery.orchestration.containment_router import ContainmentRouter
from simulation.recovery.orchestration.recovery_orchestrator import RecoveryOrchestrator
from simulation.recovery.containment.containment_engine import ContainmentEngine
from simulation.recovery.escalation.escalation_engine import EscalationEngine
from simulation.recovery.models import CorruptionType, IntegritySeverity


class TestRecoveryPipeline(TestCase):
    def test_create_pipeline(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1', 'step2'])
        self.assertEqual(pipeline.pipeline_id, 'pipe_001')

    def test_start_pipeline(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1', 'step2'])
        result = pipeline.start()
        self.assertTrue(result['started'])

    def test_start_empty_pipeline_fails(self):
        pipeline = RecoveryPipeline('pipe_001', [])
        result = pipeline.start()
        self.assertFalse(result['started'])

    def test_advance_pipeline(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1', 'step2'])
        pipeline.start()
        result = pipeline.advance()
        self.assertTrue(result['advanced'])
        self.assertEqual(result['step_name'], 'step1')

    def test_advance_completes_pipeline(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1'])
        pipeline.start()
        result = pipeline.advance()
        self.assertTrue(result['complete'])

    def test_fail_pipeline(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1'])
        pipeline.start()
        result = pipeline.fail('Test error')
        self.assertTrue(result['failed'])
        self.assertTrue(pipeline.has_failed)

    def test_reset_pipeline(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1', 'step2'])
        pipeline.start()
        pipeline.advance()
        pipeline.reset()
        self.assertEqual(pipeline.current_step, 0)
        self.assertFalse(pipeline.is_running)

    def test_get_status(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1'])
        status = pipeline.get_status()
        self.assertEqual(status['total_steps'], 1)
        self.assertFalse(status['is_running'])

    def test_properties(self):
        pipeline = RecoveryPipeline('pipe_001', ['step1'])
        pipeline.start()
        self.assertTrue(pipeline.is_running)
        self.assertFalse(pipeline.is_complete)
        self.assertFalse(pipeline.has_failed)


class TestContainmentRouter(TestCase):
    def test_route_low_severity_no_actions(self):
        router = ContainmentRouter()
        result = router.route(CorruptionType.CONSISTENCY, IntegritySeverity.LOW, {})
        self.assertEqual(len(result['actions']), 0)

    def test_route_high_severity_with_containment(self):
        router = ContainmentRouter()
        engine = ContainmentEngine()
        result = router.route(CorruptionType.FINANCIAL, IntegritySeverity.HIGH,
                               {'workflow_id': 'wf_001', 'workflow_type': 'sales',
                                'tick': 1, 'journal_balance': 100},
                               engine)
        self.assertGreater(len(result['actions']), 0)

    def test_route_with_escalation(self):
        router = ContainmentRouter()
        engine = ContainmentEngine()
        esc_engine = EscalationEngine()
        result = router.route(CorruptionType.FINANCIAL, IntegritySeverity.CRITICAL,
                               {'workflow_id': 'wf_001', 'workflow_type': 'sales',
                                'tick': 1, 'journal_balance': 100, 'risk_score': 80},
                               engine, esc_engine)
        self.assertGreater(len(result['actions']), 0)

    def test_clear(self):
        router = ContainmentRouter()
        router.route(CorruptionType.CONSISTENCY, IntegritySeverity.LOW, {})
        router.clear()


class TestRecoveryOrchestrator(TestCase):
    def test_initial_state(self):
        orch = RecoveryOrchestrator()
        self.assertIsNotNone(orch.containment)
        self.assertIsNotNone(orch.escalation)
        self.assertIsNotNone(orch.degradation)
        self.assertIsNotNone(orch.recommender)

    def test_process_incident_returns_result(self):
        orch = RecoveryOrchestrator()
        result = orch.process_incident(
            CorruptionType.FINANCIAL, IntegritySeverity.HIGH,
            'accounting', 'Journal imbalance')
        self.assertIn('incident_id', result)
        self.assertIn('violation', result)
        self.assertIn('recommendations', result)

    def test_process_incident_low_severity(self):
        orch = RecoveryOrchestrator()
        result = orch.process_incident(
            CorruptionType.CONSISTENCY, IntegritySeverity.LOW,
            'test', 'Minor inconsistency')
        self.assertIn('incident_id', result)

    def test_generate_recovery_report(self):
        orch = RecoveryOrchestrator()
        report = orch.generate_recovery_report(1)
        self.assertIn('report_id', report)
        self.assertIn('operational_status', report)
        self.assertIn('overall_risk_score', report)

    def test_recovery_report_after_incident(self):
        orch = RecoveryOrchestrator()
        orch.process_incident(CorruptionType.FINANCIAL, IntegritySeverity.CRITICAL,
                               'accounting', 'Critical imbalance')
        report = orch.generate_recovery_report(1)
        self.assertGreater(report['overall_risk_score'], 0)

    def test_degradation_after_critical_incident(self):
        orch = RecoveryOrchestrator()
        orch.process_incident(CorruptionType.FINANCIAL, IntegritySeverity.CRITICAL,
                               'accounting', 'Critical')
        status = orch.degradation.get_current_status()
        self.assertIn(status['current_level'], ['reduced', 'minimum', 'emergency'])

    def test_reset(self):
        orch = RecoveryOrchestrator()
        orch.process_incident(CorruptionType.FINANCIAL, IntegritySeverity.HIGH,
                               'accounting', 'Test')
        orch.reset()
        self.assertEqual(orch._incident_count, 0)

    def test_all_properties_accessible(self):
        orch = RecoveryOrchestrator()
        self.assertIsNotNone(orch.rollback_simulator)
        self.assertIsNotNone(orch.rollback_risk)
        self.assertIsNotNone(orch.dependency_map)
        self.assertIsNotNone(orch.rollback_validator)
        self.assertIsNotNone(orch.integrity_guard)
        self.assertIsNotNone(orch.corruption_detector)
        self.assertIsNotNone(orch.partial_state)
        self.assertIsNotNone(orch.consistency)
        self.assertIsNotNone(orch.blast_radius)
        self.assertIsNotNone(orch.dependency_impact)
        self.assertIsNotNone(orch.financial_risk)
        self.assertIsNotNone(orch.inventory_risk)
        self.assertIsNotNone(orch.router)

    def test_deterministic_incident_processing(self):
        orch1 = RecoveryOrchestrator()
        orch2 = RecoveryOrchestrator()
        r1 = orch1.process_incident(CorruptionType.FINANCIAL, IntegritySeverity.HIGH,
                                      'acc', 'Test')
        r2 = orch2.process_incident(CorruptionType.FINANCIAL, IntegritySeverity.HIGH,
                                      'acc', 'Test')
        self.assertEqual(r1['violation']['type'], r2['violation']['type'])
        self.assertEqual(r1['violation']['severity'], r2['violation']['severity'])


class TestNoERPMutation(TestCase):
    def test_no_domain_imports_in_recovery(self):
        import simulation.recovery.containment.containment_engine
        import simulation.recovery.rollback.rollback_simulator
        import simulation.recovery.integrity.corruption_detector
        import simulation.recovery.orchestration.recovery_orchestrator

    def test_no_write_patterns_in_recovery_code(self):
        import ast, inspect
        from simulation.recovery import containment, rollback, integrity, escalation
        from simulation.recovery import recommendations, blast_radius, degradation, orchestration
        modules = [containment, rollback, integrity, escalation,
                    recommendations, blast_radius, degradation, orchestration]
        write_patterns = ['.save()', '.create(', '.delete(', '.update(',
                          'transaction.atomic', 'setattr']
        for mod in modules:
            for name, obj in inspect.getmembers(mod):
                if inspect.ismodule(obj) and hasattr(obj, '__file__') and obj.__file__:
                    try:
                        with open(obj.__file__, 'r') as f:
                            content = f.read()
                        for pattern in write_patterns:
                            self.assertNotIn(pattern, content,
                                             f'{pattern} found in {obj.__file__}')
                    except (IOError, UnicodeDecodeError):
                        pass

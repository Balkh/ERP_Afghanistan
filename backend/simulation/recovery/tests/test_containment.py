"""Tests for containment subpackage — workflow isolation, quarantine, and rules."""
from django.test import TestCase
from simulation.recovery.containment.containment_rules import ContainmentRules
from simulation.recovery.containment.workflow_isolator import WorkflowIsolator
from simulation.recovery.containment.quarantine_manager import QuarantineManager
from simulation.recovery.containment.containment_engine import ContainmentEngine
from simulation.recovery.models import IntegritySeverity


class TestContainmentRules(TestCase):
    def test_known_rules_exist(self):
        rules = ContainmentRules()
        self.assertGreater(len(rules.KNOWN_RULES), 0)

    def test_get_known_rule(self):
        rules = ContainmentRules()
        rule = rules.get_rule('financial_imbalance')
        self.assertIsNotNone(rule)
        self.assertEqual(rule.rule_id, 'fin_001')

    def test_get_unknown_rule(self):
        rules = ContainmentRules()
        self.assertIsNone(rules.get_rule('nonexistent'))

    def test_evaluate_financial_imbalance_triggered(self):
        rules = ContainmentRules()
        result = rules.evaluate_rule('financial_imbalance', {'journal_balance': 100})
        self.assertTrue(result['triggered'])

    def test_evaluate_financial_imbalance_not_triggered(self):
        rules = ContainmentRules()
        result = rules.evaluate_rule('financial_imbalance', {'journal_balance': 0})
        self.assertFalse(result['triggered'])

    def test_evaluate_inventory_drift_triggered(self):
        rules = ContainmentRules()
        result = rules.evaluate_rule('inventory_drift', {'inventory_delta': 10, 'movement_sum': 5})
        self.assertTrue(result['triggered'])

    def test_evaluate_inventory_drift_not_triggered(self):
        rules = ContainmentRules()
        result = rules.evaluate_rule('inventory_drift', {'inventory_delta': 10, 'movement_sum': 10})
        self.assertFalse(result['triggered'])

    def test_evaluate_multi_returns_list(self):
        rules = ContainmentRules()
        contexts = {
            'financial_imbalance': {'journal_balance': 0},
            'inventory_drift': {'inventory_delta': 5, 'movement_sum': 5},
            'orphan_state': {'orphan_found': False},
            'reconciliation_failure': {'reconciliation_gap': 0, 'threshold': 10},
            'cascade_risk': {'cascade_probability': 0.1},
        }
        results = rules.evaluate_multi(contexts)
        self.assertEqual(len(results), 5)

    def test_evaluation_count_tracks(self):
        rules = ContainmentRules()
        self.assertEqual(rules.evaluation_count(), 0)
        rules.evaluate_rule('financial_imbalance', {'journal_balance': 100})
        self.assertEqual(rules.evaluation_count(), 1)

    def test_clear_resets(self):
        rules = ContainmentRules()
        rules.evaluate_rule('financial_imbalance', {'journal_balance': 100})
        rules.clear()
        self.assertEqual(rules.evaluation_count(), 0)


class TestWorkflowIsolator(TestCase):
    def test_isolate_workflow(self):
        isolator = WorkflowIsolator()
        result = isolator.isolate_workflow('wf_001', 'sales', 1, 'Test isolation')
        self.assertTrue(result['isolated'])

    def test_isolate_twice_returns_false(self):
        isolator = WorkflowIsolator()
        isolator.isolate_workflow('wf_001', 'sales', 1, 'Test')
        result = isolator.isolate_workflow('wf_001', 'sales', 2, 'Again')
        self.assertFalse(result['isolated'])

    def test_is_isolated(self):
        isolator = WorkflowIsolator()
        self.assertFalse(isolator.is_isolated('wf_001'))
        isolator.isolate_workflow('wf_001', 'sales', 1, 'Test')
        self.assertTrue(isolator.is_isolated('wf_001'))

    def test_release_workflow(self):
        isolator = WorkflowIsolator()
        isolator.isolate_workflow('wf_001', 'sales', 1, 'Test')
        result = isolator.release_workflow('wf_001', 2)
        self.assertTrue(result['released'])
        self.assertFalse(isolator.is_isolated('wf_001'))

    def test_release_not_isolated(self):
        isolator = WorkflowIsolator()
        result = isolator.release_workflow('wf_001', 1)
        self.assertFalse(result['released'])

    def test_get_isolated_count(self):
        isolator = WorkflowIsolator()
        self.assertEqual(isolator.get_isolated_count(), 0)
        isolator.isolate_workflow('wf_001', 'sales', 1, 'Test')
        self.assertEqual(isolator.get_isolated_count(), 1)

    def test_list_isolated(self):
        isolator = WorkflowIsolator()
        isolator.isolate_workflow('wf_001', 'sales', 1, 'Test')
        isolated = isolator.list_isolated()
        self.assertEqual(len(isolated), 1)
        self.assertEqual(isolated[0]['workflow_id'], 'wf_001')

    def test_clear(self):
        isolator = WorkflowIsolator()
        isolator.isolate_workflow('wf_001', 'sales', 1, 'Test')
        isolator.clear()
        self.assertEqual(isolator.get_isolated_count(), 0)


class TestQuarantineManager(TestCase):
    def test_quarantine_workflow(self):
        mgr = QuarantineManager()
        result = mgr.quarantine('wf_001', 'sales', 1, 'Test quarantine',
                                severity=IntegritySeverity.HIGH)
        self.assertTrue(result['quarantined'])

    def test_quarantine_twice_returns_false(self):
        mgr = QuarantineManager()
        mgr.quarantine('wf_001', 'sales', 1, 'Test')
        result = mgr.quarantine('wf_001', 'sales', 2, 'Again')
        self.assertFalse(result['quarantined'])

    def test_release_from_quarantine(self):
        mgr = QuarantineManager()
        mgr.quarantine('wf_001', 'sales', 1, 'Test')
        result = mgr.release_from_quarantine('wf_001', 2)
        self.assertTrue(result['released'])

    def test_release_not_quarantined(self):
        mgr = QuarantineManager()
        result = mgr.release_from_quarantine('wf_001', 1)
        self.assertFalse(result['released'])

    def test_active_quarantine_count(self):
        mgr = QuarantineManager()
        self.assertEqual(mgr.get_active_quarantine_count(), 0)
        mgr.quarantine('wf_001', 'sales', 1, 'Test')
        self.assertEqual(mgr.get_active_quarantine_count(), 1)

    def test_list_quarantined(self):
        mgr = QuarantineManager()
        mgr.quarantine('wf_001', 'sales', 1, 'Test')
        quarantined = mgr.list_quarantined()
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0]['workflow_id'], 'wf_001')

    def test_quarantine_with_severity(self):
        mgr = QuarantineManager()
        result = mgr.quarantine('wf_001', 'sales', 1, 'Critical',
                                severity=IntegritySeverity.CRITICAL)
        self.assertEqual(result['severity'], 'critical')

    def test_clear(self):
        mgr = QuarantineManager()
        mgr.quarantine('wf_001', 'sales', 1, 'Test')
        mgr.clear()
        self.assertEqual(mgr.get_active_quarantine_count(), 0)


class TestContainmentEngine(TestCase):
    def test_evaluate_no_trigger(self):
        engine = ContainmentEngine()
        result = engine.evaluate_and_contain('wf_001', 'sales', 1, {
            'financial_imbalance': {'journal_balance': 0},
        })
        self.assertFalse(result['contained'])

    def test_evaluate_with_trigger(self):
        engine = ContainmentEngine()
        result = engine.evaluate_and_contain('wf_001', 'sales', 1, {
            'financial_imbalance': {'journal_balance': 100},
        })
        self.assertTrue(result['contained'])
        self.assertTrue(result['blocking'])

    def test_containment_tracks_count(self):
        engine = ContainmentEngine()
        result = engine.get_containment_report()
        self.assertEqual(result['total_containments'], 0)

    def test_release_workflow(self):
        engine = ContainmentEngine()
        result = engine.release_workflow('wf_001', 1)
        self.assertIn('isolated_released', result)

    def test_containment_report_after_contain(self):
        engine = ContainmentEngine()
        engine.evaluate_and_contain('wf_001', 'sales', 1, {
            'financial_imbalance': {'journal_balance': 100},
        })
        report = engine.get_containment_report()
        self.assertGreater(report['total_containments'], 0)

    def test_clear(self):
        engine = ContainmentEngine()
        engine.evaluate_and_contain('wf_001', 'sales', 1, {
            'financial_imbalance': {'journal_balance': 100},
        })
        engine.clear()
        report = engine.get_containment_report()
        self.assertEqual(report['total_containments'], 0)

    def test_rules_property(self):
        engine = ContainmentEngine()
        self.assertIsNotNone(engine.rules)

    def test_isolator_property(self):
        engine = ContainmentEngine()
        self.assertIsNotNone(engine.isolator)

    def test_quarantine_property(self):
        engine = ContainmentEngine()
        self.assertIsNotNone(engine.quarantine)

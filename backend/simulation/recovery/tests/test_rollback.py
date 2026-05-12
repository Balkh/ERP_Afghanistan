"""Tests for rollback simulation subpackage."""
from django.test import TestCase
from simulation.recovery.rollback.rollback_simulator import RollbackSimulator
from simulation.recovery.rollback.rollback_risk_analyzer import RollbackRiskAnalyzer
from simulation.recovery.rollback.dependency_rollback_map import DependencyRollbackMap
from simulation.recovery.rollback.rollback_validator import RollbackValidator


class TestRollbackSimulator(TestCase):
    def test_simulate_rollback_empty(self):
        sim = RollbackSimulator()
        result = sim.simulate_rollback('sim_001', 5)
        self.assertEqual(result['simulation_id'], 'sim_001')
        self.assertEqual(result['workflows_affected'], 0)

    def test_simulate_rollback_with_history(self):
        sim = RollbackSimulator()
        history = [
            {'workflow_id': 'wf_001', 'tick': 10, 'journal_entries': 3, 'inventory_movements': 2,
             'is_posted': False},
            {'workflow_id': 'wf_002', 'tick': 8, 'journal_entries': 1, 'inventory_movements': 0,
             'is_posted': False},
        ]
        result = sim.simulate_rollback('sim_001', 5, history)
        self.assertEqual(result['workflows_affected'], 2)

    def test_simulate_rollback_identifies_conflicts(self):
        sim = RollbackSimulator()
        history = [
            {'workflow_id': 'wf_001', 'tick': 10, 'journal_entries': 1, 'inventory_movements': 0,
             'is_posted': True},
        ]
        result = sim.simulate_rollback('sim_001', 5, history)
        self.assertTrue(result['has_conflicts'])

    def test_simulate_rollback_risk_score(self):
        sim = RollbackSimulator()
        history = [
            {'workflow_id': 'wf_001', 'tick': 10, 'journal_entries': 10, 'inventory_movements': 5,
             'is_posted': False},
        ]
        result = sim.simulate_rollback('sim_001', 5, history)
        self.assertGreater(result['estimated_risk_score'], 0)

    def test_get_simulation_count(self):
        sim = RollbackSimulator()
        self.assertEqual(sim.get_simulation_count(), 0)
        sim.simulate_rollback('sim_001', 5)
        self.assertEqual(sim.get_simulation_count(), 1)

    def test_clear(self):
        sim = RollbackSimulator()
        sim.simulate_rollback('sim_001', 5)
        sim.clear()
        self.assertEqual(sim.get_simulation_count(), 0)


class TestRollbackRiskAnalyzer(TestCase):
    def test_analyze_low_risk(self):
        analyzer = RollbackRiskAnalyzer()
        sim_result = {'estimated_risk_score': 3, 'has_conflicts': False, 'conflicts': []}
        result = analyzer.analyze_risk(sim_result)
        self.assertEqual(result['severity'], 'info')

    def test_analyze_medium_risk(self):
        analyzer = RollbackRiskAnalyzer()
        sim_result = {'estimated_risk_score': 25, 'has_conflicts': False, 'conflicts': []}
        result = analyzer.analyze_risk(sim_result)
        self.assertEqual(result['severity'], 'medium')

    def test_analyze_high_risk(self):
        analyzer = RollbackRiskAnalyzer()
        sim_result = {'estimated_risk_score': 50, 'has_conflicts': False, 'conflicts': []}
        result = analyzer.analyze_risk(sim_result)
        self.assertEqual(result['severity'], 'high')

    def test_analyze_critical_risk(self):
        analyzer = RollbackRiskAnalyzer()
        sim_result = {'estimated_risk_score': 80, 'has_conflicts': True, 'conflicts': ['wf_001']}
        result = analyzer.analyze_risk(sim_result)
        self.assertEqual(result['severity'], 'critical')

    def test_analyze_tracks_conflicts(self):
        analyzer = RollbackRiskAnalyzer()
        sim_result = {'estimated_risk_score': 50, 'has_conflicts': True, 'conflicts': ['wf_001', 'wf_002']}
        result = analyzer.analyze_risk(sim_result)
        self.assertEqual(len(result['conflicting_transactions']), 2)

    def test_average_risk_score(self):
        analyzer = RollbackRiskAnalyzer()
        self.assertEqual(analyzer.get_average_risk_score(), 0.0)
        analyzer.analyze_risk({'estimated_risk_score': 10, 'has_conflicts': False, 'conflicts': []})
        self.assertAlmostEqual(analyzer.get_average_risk_score(), 10.0)

    def test_clear(self):
        analyzer = RollbackRiskAnalyzer()
        analyzer.analyze_risk({'estimated_risk_score': 10, 'has_conflicts': False, 'conflicts': []})
        analyzer.clear()
        self.assertEqual(analyzer.get_average_risk_score(), 0.0)


class TestDependencyRollbackMap(TestCase):
    def test_build_empty(self):
        dep_map = DependencyRollbackMap()
        result = dep_map.build_dependency_map([])
        self.assertEqual(result['max_depth'], 0)

    def test_build_with_workflows(self):
        dep_map = DependencyRollbackMap()
        workflows = [{'workflow_id': 'wf_001'}, {'workflow_id': 'wf_002'}]
        links = [{'source': 'wf_001', 'target': 'wf_002'}]
        result = dep_map.build_dependency_map(workflows, links)
        self.assertIn('wf_001', result['dependency_map'])
        self.assertIn('wf_002', result['dependency_map'])
        self.assertIn('wf_002', result['dependency_map']['wf_001'])

    def test_build_no_links(self):
        dep_map = DependencyRollbackMap()
        workflows = [{'workflow_id': 'wf_001'}, {'workflow_id': 'wf_002'}]
        result = dep_map.build_dependency_map(workflows)
        self.assertEqual(len(result['dependency_map']['wf_001']), 0)

    def test_chain_lengths(self):
        dep_map = DependencyRollbackMap()
        workflows = [{'workflow_id': 'a'}, {'workflow_id': 'b'}, {'workflow_id': 'c'}]
        links = [{'source': 'a', 'target': 'b'}, {'source': 'b', 'target': 'c'}]
        result = dep_map.build_dependency_map(workflows, links)
        self.assertGreater(result['chain_lengths'].get('a', 0), 0)

    def test_clear(self):
        dep_map = DependencyRollbackMap()
        dep_map.build_dependency_map([{'workflow_id': 'wf_001'}])
        dep_map.clear()


class TestRollbackValidator(TestCase):
    def test_validate_safe_rollback(self):
        validator = RollbackValidator()
        sim_result = {'has_conflicts': False}
        risk = {'has_irreversible_operations': False, 'risk_score': 10}
        result = validator.validate_rollback(sim_result, risk)
        self.assertTrue(result['is_safe'])

    def test_validate_unsafe_with_conflicts(self):
        validator = RollbackValidator()
        sim_result = {'has_conflicts': True}
        risk = {'has_irreversible_operations': False, 'risk_score': 30}
        result = validator.validate_rollback(sim_result, risk)
        self.assertFalse(result['is_safe'])

    def test_validate_unsafe_with_irreversible(self):
        validator = RollbackValidator()
        sim_result = {'has_conflicts': False}
        risk = {'has_irreversible_operations': True, 'risk_score': 30}
        result = validator.validate_rollback(sim_result, risk)
        self.assertFalse(result['is_safe'])

    def test_validate_high_risk(self):
        validator = RollbackValidator()
        sim_result = {'has_conflicts': False}
        risk = {'has_irreversible_operations': False, 'risk_score': 60}
        result = validator.validate_rollback(sim_result, risk)
        self.assertFalse(result['is_safe'])

    def test_validate_generates_warnings(self):
        validator = RollbackValidator()
        sim_result = {'has_conflicts': True}
        risk = {'has_irreversible_operations': True, 'risk_score': 80}
        result = validator.validate_rollback(sim_result, risk)
        self.assertGreater(len(result['warnings']), 0)

    def test_validation_count(self):
        validator = RollbackValidator()
        self.assertEqual(validator.get_validation_count(), 0)
        validator.validate_rollback({'has_conflicts': False},
                                    {'has_irreversible_operations': False, 'risk_score': 10})
        self.assertEqual(validator.get_validation_count(), 1)

    def test_clear(self):
        validator = RollbackValidator()
        validator.validate_rollback({'has_conflicts': False},
                                    {'has_irreversible_operations': False, 'risk_score': 10})
        validator.clear()
        self.assertEqual(validator.get_validation_count(), 0)

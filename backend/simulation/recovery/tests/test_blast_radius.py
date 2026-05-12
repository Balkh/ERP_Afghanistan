"""Tests for blast radius analysis subpackage."""
from django.test import TestCase
from simulation.recovery.blast_radius.blast_radius_engine import BlastRadiusEngine
from simulation.recovery.blast_radius.dependency_impact_map import DependencyImpactMap
from simulation.recovery.blast_radius.financial_risk_estimator import FinancialRiskEstimator
from simulation.recovery.blast_radius.inventory_risk_estimator import InventoryRiskEstimator


class TestBlastRadiusEngine(TestCase):
    def test_analyze_empty(self):
        engine = BlastRadiusEngine()
        result = engine.analyze({'estimated_blast_radius': 0})
        self.assertEqual(result['estimated_impact_score'], 0.0)

    def test_analyze_with_workflows(self):
        engine = BlastRadiusEngine()
        result = engine.analyze({'estimated_blast_radius': 5},
                                 affected_workflows=['wf_001', 'wf_002'])
        self.assertGreater(result['estimated_impact_score'], 0)

    def test_analyze_with_modules(self):
        engine = BlastRadiusEngine()
        result = engine.analyze({'estimated_blast_radius': 3},
                                 affected_modules=['accounting', 'inventory'])
        self.assertGreater(result['estimated_impact_score'], 0)

    def test_get_analysis_count(self):
        engine = BlastRadiusEngine()
        self.assertEqual(engine.get_analysis_count(), 0)
        engine.analyze({'estimated_blast_radius': 1})
        self.assertEqual(engine.get_analysis_count(), 1)

    def test_clear(self):
        engine = BlastRadiusEngine()
        engine.analyze({'estimated_blast_radius': 1})
        engine.clear()
        self.assertEqual(engine.get_analysis_count(), 0)


class TestDependencyImpactMap(TestCase):
    def test_build_empty(self):
        dep_map = DependencyImpactMap()
        result = dep_map.build_impact_map([])
        self.assertEqual(len(result), 0)

    def test_build_single_module(self):
        dep_map = DependencyImpactMap()
        result = dep_map.build_impact_map(['accounting'])
        self.assertIn('accounting', result)

    def test_build_with_dependencies(self):
        dep_map = DependencyImpactMap()
        graph = {'accounting': ['inventory'], 'inventory': []}
        result = dep_map.build_impact_map(['accounting', 'inventory'], graph)
        self.assertIn('accounting', result)
        self.assertIn('inventory', result)

    def test_build_critical_path(self):
        dep_map = DependencyImpactMap()
        result = dep_map.build_impact_map(['accounting'], critical_paths=['accounting'])
        self.assertTrue(result['accounting']['is_critical_path'])

    def test_clear(self):
        dep_map = DependencyImpactMap()
        dep_map.build_impact_map(['accounting'])
        dep_map.clear()


class TestFinancialRiskEstimator(TestCase):
    def test_estimate_zero_exposure(self):
        estimator = FinancialRiskEstimator()
        result = estimator.estimate_exposure(0)
        self.assertEqual(result['estimated_exposure'], 0)

    def test_estimate_low_exposure(self):
        estimator = FinancialRiskEstimator()
        result = estimator.estimate_exposure(50)
        self.assertEqual(result['risk_level'], 'low')

    def test_estimate_medium_exposure(self):
        estimator = FinancialRiskEstimator()
        result = estimator.estimate_exposure(500)
        self.assertEqual(result['risk_level'], 'medium')

    def test_estimate_high_exposure(self):
        estimator = FinancialRiskEstimator()
        result = estimator.estimate_exposure(5000)
        self.assertEqual(result['risk_level'], 'high')

    def test_estimate_critical_exposure(self):
        estimator = FinancialRiskEstimator()
        result = estimator.estimate_exposure(50000)
        self.assertEqual(result['risk_level'], 'critical')

    def test_estimate_with_accounts(self):
        estimator = FinancialRiskEstimator()
        result = estimator.estimate_exposure(100, affected_accounts=['acc_001', 'acc_002'])
        self.assertEqual(len(result['affected_accounts']), 2)

    def test_clear(self):
        estimator = FinancialRiskEstimator()
        estimator.estimate_exposure(100)
        estimator.clear()


class TestInventoryRiskEstimator(TestCase):
    def test_estimate_zero(self):
        estimator = InventoryRiskEstimator()
        result = estimator.estimate_inventory_risk(0)
        self.assertEqual(result['risk_level'], 'info')

    def test_estimate_low(self):
        estimator = InventoryRiskEstimator()
        result = estimator.estimate_inventory_risk(3)
        self.assertEqual(result['risk_level'], 'low')

    def test_estimate_medium(self):
        estimator = InventoryRiskEstimator()
        result = estimator.estimate_inventory_risk(10)
        self.assertEqual(result['risk_level'], 'medium')

    def test_estimate_high(self):
        estimator = InventoryRiskEstimator()
        result = estimator.estimate_inventory_risk(30)
        self.assertEqual(result['risk_level'], 'high')

    def test_estimate_critical(self):
        estimator = InventoryRiskEstimator()
        result = estimator.estimate_inventory_risk(100)
        self.assertEqual(result['risk_level'], 'critical')

    def test_estimate_with_value(self):
        estimator = InventoryRiskEstimator()
        result = estimator.estimate_inventory_risk(5, estimated_value_at_risk=5000)
        self.assertGreater(result['estimated_value_at_risk'], 0)

    def test_estimate_with_warehouses(self):
        estimator = InventoryRiskEstimator()
        result = estimator.estimate_inventory_risk(3, affected_warehouses=['wh_001'])
        self.assertEqual(len(result['affected_warehouses']), 1)

    def test_clear(self):
        estimator = InventoryRiskEstimator()
        estimator.estimate_inventory_risk(5)
        estimator.clear()

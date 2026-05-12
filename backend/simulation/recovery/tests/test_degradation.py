"""Tests for graceful degradation subpackage."""
from django.test import TestCase
from simulation.recovery.degradation.degradation_levels import DegradationLevels
from simulation.recovery.degradation.operational_fallbacks import OperationalFallbacks
from simulation.recovery.degradation.service_reduction_policy import ServiceReductionPolicy
from simulation.recovery.degradation.graceful_degradation import GracefulDegradation
from simulation.recovery.models import DegradationLevel, IntegritySeverity


class TestDegradationLevels(TestCase):
    def test_default_is_full(self):
        levels = DegradationLevels()
        self.assertEqual(levels.current, DegradationLevel.FULL)

    def test_set_level(self):
        levels = DegradationLevels()
        result = levels.set_level(DegradationLevel.REDUCED, 'Test')
        self.assertEqual(result['current_level'], 'reduced')

    def test_select_full_for_info(self):
        levels = DegradationLevels()
        result = levels.select_level(IntegritySeverity.INFO)
        self.assertEqual(result, DegradationLevel.FULL)

    def test_select_reduced_for_medium(self):
        levels = DegradationLevels()
        result = levels.select_level(IntegritySeverity.MEDIUM)
        self.assertEqual(result, DegradationLevel.REDUCED)

    def test_select_minimum_for_high(self):
        levels = DegradationLevels()
        result = levels.select_level(IntegritySeverity.HIGH)
        self.assertEqual(result, DegradationLevel.MINIMUM)

    def test_select_emergency_for_critical(self):
        levels = DegradationLevels()
        result = levels.select_level(IntegritySeverity.CRITICAL)
        self.assertEqual(result, DegradationLevel.EMERGENCY)

    def test_select_emergency_for_irreversible(self):
        levels = DegradationLevels()
        result = levels.select_level(IntegritySeverity.LOW, has_irreversible=True)
        self.assertEqual(result, DegradationLevel.EMERGENCY)

    def test_get_level_defines_full(self):
        levels = DegradationLevels()
        result = levels.get_level(DegradationLevel.FULL)
        self.assertTrue(result['allow_new_workflows'])

    def test_get_level_defines_emergency(self):
        levels = DegradationLevels()
        result = levels.get_level(DegradationLevel.EMERGENCY)
        self.assertFalse(result['allow_new_workflows'])

    def test_clear(self):
        levels = DegradationLevels()
        levels.set_level(DegradationLevel.EMERGENCY, 'Test')
        levels.clear()
        self.assertEqual(levels.current, DegradationLevel.FULL)


class TestOperationalFallbacks(TestCase):
    def test_full_strategy_retry_on_write(self):
        fallbacks = OperationalFallbacks()
        strategy = fallbacks.get_strategy(DegradationLevel.FULL)
        self.assertEqual(strategy['on_write_failure'], 'retry')

    def test_emergency_strategy_reject_on_write(self):
        fallbacks = OperationalFallbacks()
        strategy = fallbacks.get_strategy(DegradationLevel.EMERGENCY)
        self.assertEqual(strategy['on_write_failure'], 'reject')

    def test_apply_fallback_returns_action(self):
        fallbacks = OperationalFallbacks()
        result = fallbacks.apply_fallback(DegradationLevel.REDUCED, 'on_write_failure', 'DB error')
        self.assertEqual(result['action'], 'queue')

    def test_clear(self):
        fallbacks = OperationalFallbacks()
        fallbacks.apply_fallback(DegradationLevel.FULL, 'on_write_failure')
        fallbacks.clear()


class TestServiceReductionPolicy(TestCase):
    def test_full_no_reduction(self):
        policy = ServiceReductionPolicy()
        plan = policy.get_plan(DegradationLevel.FULL)
        self.assertEqual(len(plan['services_to_reduce']), 0)

    def test_emergency_reduces_all(self):
        policy = ServiceReductionPolicy()
        plan = policy.get_plan(DegradationLevel.EMERGENCY)
        self.assertGreater(len(plan['services_to_reduce']), 0)

    def test_apply_reduction(self):
        policy = ServiceReductionPolicy()
        result = policy.apply_reduction(DegradationLevel.MINIMUM)
        self.assertEqual(result['degradation_level'], 'minimum')
        self.assertIn('accounting', result['services_to_preserve'])

    def test_clear(self):
        policy = ServiceReductionPolicy()
        policy.apply_reduction(DegradationLevel.REDUCED)
        policy.clear()


class TestGracefulDegradation(TestCase):
    def test_initial_full_operation(self):
        deg = GracefulDegradation()
        status = deg.get_current_status()
        self.assertEqual(status['current_level'], 'full')

    def test_degrade_to_reduced(self):
        deg = GracefulDegradation()
        result = deg.degrade(IntegritySeverity.MEDIUM, reason='Load')
        self.assertTrue(result['degraded'])
        self.assertEqual(result['current_level'], 'reduced')

    def test_degrade_to_emergency(self):
        deg = GracefulDegradation()
        result = deg.degrade(IntegritySeverity.CRITICAL, has_irreversible=True, reason='Critical')
        self.assertTrue(result['degraded'])
        self.assertEqual(result['current_level'], 'emergency')

    def test_degrade_same_level_returns_no_action(self):
        deg = GracefulDegradation()
        result = deg.degrade(IntegritySeverity.INFO, reason='Test')
        self.assertFalse(result['degraded'])

    def test_degrade_changes_fallback_strategy(self):
        deg = GracefulDegradation()
        deg.degrade(IntegritySeverity.CRITICAL, reason='Critical')
        status = deg.get_current_status()
        self.assertIn('fallback_strategy', status)

    def test_levels_property(self):
        deg = GracefulDegradation()
        self.assertIsNotNone(deg.levels)

    def test_fallbacks_property(self):
        deg = GracefulDegradation()
        self.assertIsNotNone(deg.fallbacks)

    def test_service_reduction_property(self):
        deg = GracefulDegradation()
        self.assertIsNotNone(deg.service_reduction)

    def test_clear(self):
        deg = GracefulDegradation()
        deg.degrade(IntegritySeverity.HIGH, reason='Test')
        deg.clear()
        status = deg.get_current_status()
        self.assertEqual(status['current_level'], 'full')

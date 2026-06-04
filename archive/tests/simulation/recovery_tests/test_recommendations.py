"""Tests for recovery recommendations subpackage."""
from django.test import TestCase
from simulation.recovery.recommendations.recovery_paths import RecoveryPathsRegistry
from simulation.recovery.recommendations.operational_playbooks import OperationalPlaybooks
from simulation.recovery.recommendations.remediation_priority import RemediationPriority
from simulation.recovery.recommendations.recovery_recommender import RecoveryRecommender
from simulation.recovery.models import RecoveryPathType, CorruptionType, IntegritySeverity


class TestRecoveryPathsRegistry(TestCase):
    def test_get_known_path(self):
        registry = RecoveryPathsRegistry()
        result = registry.get_path(RecoveryPathType.ROLLBACK)
        self.assertEqual(result['name'], 'Rollback')

    def test_get_unknown_path_defaults_to_ignore(self):
        registry = RecoveryPathsRegistry()
        result = registry.get_path_by_str('nonexistent')
        self.assertEqual(result['path_type'], 'ignore')

    def test_all_paths_have_definitions(self):
        registry = RecoveryPathsRegistry()
        for path_type in RecoveryPathType:
            result = registry.get_path(path_type)
            self.assertIn('name', result)

    def test_rollback_requires_manual_review(self):
        registry = RecoveryPathsRegistry()
        result = registry.get_path(RecoveryPathType.ROLLBACK)
        self.assertTrue(result['requires_manual_review'])

    def test_clear(self):
        registry = RecoveryPathsRegistry()
        registry.get_path(RecoveryPathType.ROLLBACK)
        registry.clear()


class TestOperationalPlaybooks(TestCase):
    def test_get_known_playbook(self):
        playbooks = OperationalPlaybooks()
        result = playbooks.get_playbook('financial_imbalance')
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Financial Imbalance Response')

    def test_get_unknown_playbook(self):
        playbooks = OperationalPlaybooks()
        self.assertIsNone(playbooks.get_playbook('nonexistent'))

    def test_find_playbooks_by_type(self):
        playbooks = OperationalPlaybooks()
        results = playbooks.find_playbooks(CorruptionType.FINANCIAL, IntegritySeverity.HIGH)
        self.assertGreater(len(results), 0)

    def test_find_playbooks_no_match(self):
        playbooks = OperationalPlaybooks()
        results = playbooks.find_playbooks(CorruptionType.ORPHAN_STATE, IntegritySeverity.INFO)
        self.assertEqual(len(results), 0)

    def test_clear(self):
        playbooks = OperationalPlaybooks()
        playbooks.get_playbook('pb_fin_001')
        playbooks.clear()


class TestRemediationPriority(TestCase):
    def test_critical_priority(self):
        priority = RemediationPriority()
        result = priority.calculate_priority(IntegritySeverity.CRITICAL)
        self.assertGreaterEqual(result['priority_score'], 80)

    def test_info_priority(self):
        priority = RemediationPriority()
        result = priority.calculate_priority(IntegritySeverity.INFO)
        self.assertLessEqual(result['priority_score'], 10)

    def test_priority_with_bonus(self):
        priority = RemediationPriority()
        base = priority.calculate_priority(IntegritySeverity.MEDIUM)
        with_bonus = priority.calculate_priority(IntegritySeverity.MEDIUM,
                                                  blast_radius_score=50)
        self.assertGreater(with_bonus['priority_score'], base['priority_score'])

    def test_irreversible_bonus(self):
        priority = RemediationPriority()
        result = priority.calculate_priority(IntegritySeverity.MEDIUM,
                                              has_irreversible=True)
        self.assertGreater(result['bonus'], 0)

    def test_clear(self):
        priority = RemediationPriority()
        priority.calculate_priority(IntegritySeverity.MEDIUM)
        priority.clear()


class TestRecoveryRecommender(TestCase):
    def test_generate_recommendations_financial(self):
        recommender = RecoveryRecommender()
        results = recommender.generate_recommendations(
            CorruptionType.FINANCIAL, IntegritySeverity.HIGH)
        self.assertGreater(len(results), 0)

    def test_generate_recommendations_inventory(self):
        recommender = RecoveryRecommender()
        results = recommender.generate_recommendations(
            CorruptionType.INVENTORY, IntegritySeverity.MEDIUM)
        self.assertGreater(len(results), 0)

    def test_recommendation_has_path_type(self):
        recommender = RecoveryRecommender()
        results = recommender.generate_recommendations(
            CorruptionType.FINANCIAL, IntegritySeverity.LOW)
        for r in results:
            self.assertIn('path_type', r)

    def test_high_severity_requires_manual(self):
        recommender = RecoveryRecommender()
        results = recommender.generate_recommendations(
            CorruptionType.FINANCIAL, IntegritySeverity.CRITICAL)
        for r in results:
            self.assertTrue(r['requires_manual_review'])

    def test_get_recommendation_count(self):
        recommender = RecoveryRecommender()
        self.assertEqual(recommender.get_recommendation_count(), 0)
        recommender.generate_recommendations(CorruptionType.FINANCIAL, IntegritySeverity.HIGH)
        self.assertGreater(recommender.get_recommendation_count(), 0)

    def test_paths_property(self):
        recommender = RecoveryRecommender()
        self.assertIsNotNone(recommender.paths)

    def test_playbooks_property(self):
        recommender = RecoveryRecommender()
        self.assertIsNotNone(recommender.playbooks)

    def test_priority_property(self):
        recommender = RecoveryRecommender()
        self.assertIsNotNone(recommender.priority)

    def test_clear(self):
        recommender = RecoveryRecommender()
        recommender.generate_recommendations(CorruptionType.FINANCIAL, IntegritySeverity.HIGH)
        recommender.clear()
        self.assertEqual(recommender.get_recommendation_count(), 0)

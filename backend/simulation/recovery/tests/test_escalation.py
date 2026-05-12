"""Tests for escalation subpackage."""
from django.test import TestCase
from simulation.recovery.escalation.severity_classifier import SeverityClassifier
from simulation.recovery.escalation.escalation_policy import EscalationPolicyEngine, EscalationPolicy
from simulation.recovery.escalation.notification_priority import NotificationPriorityMapper
from simulation.recovery.escalation.escalation_engine import EscalationEngine
from simulation.recovery.models import EscalationPriority


class TestSeverityClassifier(TestCase):
    def test_classify_info(self):
        classifier = SeverityClassifier()
        result = classifier.classify(risk_score=3)
        self.assertEqual(result['severity'], 'info')

    def test_classify_low(self):
        classifier = SeverityClassifier()
        result = classifier.classify(risk_score=15)
        self.assertEqual(result['severity'], 'low')

    def test_classify_medium(self):
        classifier = SeverityClassifier()
        result = classifier.classify(risk_score=35)
        self.assertEqual(result['severity'], 'medium')

    def test_classify_high(self):
        classifier = SeverityClassifier()
        result = classifier.classify(risk_score=60)
        self.assertEqual(result['severity'], 'high')

    def test_classify_critical_by_score(self):
        classifier = SeverityClassifier()
        result = classifier.classify(risk_score=85)
        self.assertEqual(result['severity'], 'critical')

    def test_classify_critical_by_conflicts(self):
        classifier = SeverityClassifier()
        result = classifier.classify(risk_score=30, has_conflicts=True)
        self.assertEqual(result['severity'], 'critical')

    def test_classify_affected_workflows(self):
        classifier = SeverityClassifier()
        result = classifier.classify(risk_score=20, workflows_affected=5)
        self.assertEqual(result['severity'], 'high')

    def test_get_classification_count(self):
        classifier = SeverityClassifier()
        self.assertEqual(classifier.get_classification_count(), 0)
        classifier.classify(risk_score=10)
        self.assertEqual(classifier.get_classification_count(), 1)

    def test_clear(self):
        classifier = SeverityClassifier()
        classifier.classify(risk_score=10)
        classifier.clear()
        self.assertEqual(classifier.get_classification_count(), 0)


class TestEscalationPolicyEngine(TestCase):
    def test_default_policies_exist(self):
        engine = EscalationPolicyEngine()
        self.assertGreater(len(engine.DEFAULT_POLICIES), 0)

    def test_evaluate_critical_severity(self):
        engine = EscalationPolicyEngine()
        results = engine.evaluate({'severity': 'critical'})
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['policy_id'], 'esc_001')

    def test_evaluate_no_trigger(self):
        engine = EscalationPolicyEngine()
        results = engine.evaluate({'severity': 'info', 'risk_score': 5})
        self.assertEqual(len(results), 0)

    def test_evaluate_high_risk(self):
        engine = EscalationPolicyEngine()
        results = engine.evaluate({'risk_score': 75})
        self.assertGreater(len(results), 0)

    def test_add_custom_policy(self):
        engine = EscalationPolicyEngine()
        policy = EscalationPolicy('custom_001', 'Custom', lambda ctx: True,
                                   EscalationPriority.HIGH, 'Custom policy')
        engine.add_policy(policy)
        results = engine.evaluate({})
        policy_ids = [r['policy_id'] for r in results]
        self.assertIn('custom_001', policy_ids)

    def test_clear(self):
        engine = EscalationPolicyEngine()
        engine.evaluate({'severity': 'critical'})
        engine.clear()


class TestNotificationPriorityMapper(TestCase):
    def test_map_immediate(self):
        mapper = NotificationPriorityMapper()
        result = mapper.map_priority(EscalationPriority.IMMEDIATE)
        self.assertTrue(result['notify'])
        self.assertEqual(result['channel'], 'emergency')

    def test_map_low(self):
        mapper = NotificationPriorityMapper()
        result = mapper.map_priority(EscalationPriority.LOW)
        self.assertFalse(result['notify'])

    def test_map_by_string(self):
        mapper = NotificationPriorityMapper()
        result = mapper.map_priority_str('high')
        self.assertEqual(result['channel'], 'urgent')

    def test_map_invalid_string_defaults_low(self):
        mapper = NotificationPriorityMapper()
        result = mapper.map_priority_str('invalid')
        self.assertFalse(result['notify'])

    def test_clear(self):
        mapper = NotificationPriorityMapper()
        mapper.map_priority(EscalationPriority.HIGH)
        mapper.clear()


class TestEscalationEngine(TestCase):
    def test_evaluate_returns_escalation(self):
        engine = EscalationEngine()
        result = engine.evaluate({'risk_score': 75, 'severity': 'critical', 'tick': 1})
        self.assertIn('escalation_id', result)

    def test_evaluate_triggers_policies(self):
        engine = EscalationEngine()
        result = engine.evaluate({'risk_score': 75, 'tick': 1})
        self.assertGreater(len(result['triggered_policies']), 0)

    def test_evaluate_immediate_action(self):
        engine = EscalationEngine()
        result = engine.evaluate({'risk_score': 90, 'has_irreversible': True, 'tick': 1})
        self.assertTrue(result['requires_immediate_action'])

    def test_get_escalation_count(self):
        engine = EscalationEngine()
        self.assertEqual(engine.get_escalation_count(), 0)
        engine.evaluate({'risk_score': 50, 'tick': 1})
        self.assertEqual(engine.get_escalation_count(), 1)

    def test_classifier_property(self):
        engine = EscalationEngine()
        self.assertIsNotNone(engine.classifier)

    def test_policy_engine_property(self):
        engine = EscalationEngine()
        self.assertIsNotNone(engine.policy_engine)

    def test_notification_mapper_property(self):
        engine = EscalationEngine()
        self.assertIsNotNone(engine.notification_mapper)

    def test_clear(self):
        engine = EscalationEngine()
        engine.evaluate({'risk_score': 50, 'tick': 1})
        engine.clear()
        self.assertEqual(engine.get_escalation_count(), 0)

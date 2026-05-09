from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model

from audit.models import AuditTrail, AuditRetentionPolicy
from audit.services.audit_service import AuditService

User = get_user_model()


class AuditTrailModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='test123')

    def test_create_audit_trail(self):
        trail = AuditTrail.objects.create(
            user=self.user,
            username=self.user.username,
            action='CREATE',
            app_label='inventory',
            model_name='Product',
            object_id='123',
            object_repr='Test Product'
        )
        self.assertEqual(trail.action, 'CREATE')
        self.assertEqual(trail.model_name, 'Product')

    def test_audit_trail_str(self):
        trail = AuditTrail.objects.create(
            user=self.user,
            username=self.user.username,
            action='UPDATE',
            app_label='sales',
            model_name='Invoice'
        )
        self.assertIn('UPDATE', str(trail))


class AuditServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='audituser', password='test123')

    def test_log_creation(self):
        AuditService.log(
            user=self.user,
            action='CREATE',
            app_label='inventory',
            model_name='Product',
            object_id='1',
            object_repr='New Product',
            new_values={'name': 'New Product', 'price': '100'}
        )
        trail = AuditTrail.objects.filter(action='CREATE').first()
        self.assertIsNotNone(trail)
        self.assertEqual(trail.new_values['name'], 'New Product')

    def test_log_with_changes(self):
        AuditService.log(
            user=self.user,
            action='UPDATE',
            app_label='inventory',
            model_name='Product',
            object_id='1',
            old_values={'price': '100'},
            new_values={'price': '150'}
        )
        trail = AuditTrail.objects.filter(action='UPDATE').first()
        self.assertIn('price', trail.changes)
        self.assertEqual(trail.changes['price'], {'old': '100', 'new': '150'})

    def test_cleanup_old_logs(self):
        AuditTrail.objects.create(
            user=self.user,
            username=self.user.username,
            action='VIEW',
            app_label='test',
            model_name='Test'
        )
        deleted = AuditService.cleanup_old_logs()
        self.assertIsInstance(deleted, int)


class AuditRetentionPolicyTests(TestCase):
    def test_create_policy(self):
        policy = AuditRetentionPolicy.objects.create(
            name='Sales Logs',
            app_labels=['sales'],
            action_types=['CREATE', 'UPDATE', 'DELETE'],
            retention_days=90,
            is_active=True
        )
        self.assertEqual(policy.retention_days, 90)
        self.assertTrue(policy.is_active)

    def test_default_cleanup(self):
        deleted = AuditService.cleanup_old_logs()
        self.assertIsInstance(deleted, int)


class AuditTrailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='viewuser', password='test123')
        cls.user2 = User.objects.create_user(username='otheruser', password='test123')
        
        AuditTrail.objects.create(
            user=cls.user,
            username=cls.user.username,
            action='CREATE',
            app_label='sales',
            model_name='Invoice',
            object_id='1'
        )
        AuditTrail.objects.create(
            user=cls.user2,
            username=cls.user2.username,
            action='UPDATE',
            app_label='inventory',
            model_name='Product',
            object_id='2'
        )

    def test_queryset_count(self):
        self.assertEqual(AuditTrail.objects.count(), 2)

    def test_filter_by_action(self):
        create_logs = AuditTrail.objects.filter(action='CREATE')
        self.assertEqual(create_logs.count(), 1)

    def test_filter_by_app(self):
        sales_logs = AuditTrail.objects.filter(app_label='sales')
        self.assertEqual(sales_logs.count(), 1)
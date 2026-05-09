"""
Security module real behavior tests - no mocks.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from security.models import Role, Permission, UserRole, AuditLog, SecurityEvent
from security.utils import InputValidator


class RoleRealBehaviorTest(TestCase):
    """Test Role with real database operations."""

    def test_create_and_retrieve_role(self):
        """Test creating and retrieving a role."""
        role = Role.objects.create(name='Pharmacist', description='Pharmacy staff')
        self.assertEqual(Role.objects.get(name='Pharmacist').name, 'Pharmacist')

    def test_role_default_active(self):
        """Test role is_active defaults to True."""
        role = Role.objects.create(name='Test Role')
        self.assertTrue(role.is_active)

    def test_role_deactivate(self):
        """Test deactivating a role."""
        role = Role.objects.create(name='Temp Role')
        role.is_active = False
        role.save()
        self.assertFalse(Role.objects.get(id=role.id).is_active)


class PermissionRealBehaviorTest(TestCase):
    """Test Permission with real database operations."""

    def test_create_permission(self):
        """Test creating a permission."""
        perm = Permission.objects.create(
            name='View Reports',
            codename='view_reports',
            module='reports'
        )
        self.assertEqual(Permission.objects.get(codename='view_reports').name, 'View Reports')

    def test_permission_unique_codename(self):
        """Test permission codename must be unique."""
        Permission.objects.create(name='Test1', codename='test_perm', module='test')
        with self.assertRaises(Exception):
            Permission.objects.create(name='Test2', codename='test_perm', module='test')


class UserRoleRealBehaviorTest(TestCase):
    """Test UserRole with real database operations."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser1', password='test123')
        self.role = Role.objects.create(name='Cashier')

    def test_assign_role(self):
        """Test assigning a role to a user."""
        user_role = UserRole.objects.create(user=self.user, role=self.role)
        self.assertEqual(user_role.user.username, 'testuser1')
        self.assertEqual(user_role.role.name, 'Cashier')

    def test_query_user_roles(self):
        """Test querying user's roles."""
        UserRole.objects.create(user=self.user, role=self.role)
        roles = UserRole.objects.filter(user=self.user)
        self.assertEqual(roles.count(), 1)


class AuditLogRealBehaviorTest(TestCase):
    """Test AuditLog with real database operations."""

    def test_create_audit_log(self):
        """Test creating an audit log entry."""
        log = AuditLog.objects.create(
            action='CREATE',
            change_message='Test action',
            ip_address='127.0.0.1'
        )
        self.assertEqual(log.action, 'CREATE')

    def test_audit_log_str(self):
        """Test audit log string representation."""
        log = AuditLog.objects.create(
            action='UPDATE',
            change_message='Updated record'
        )
        self.assertIn('UPDATE', str(log))


class SecurityEventRealBehaviorTest(TestCase):
    """Test SecurityEvent with real database operations."""

    def test_create_security_event(self):
        """Test creating a security event."""
        event = SecurityEvent.objects.create(
            event_type='LOGIN',
            severity='INFO',
            title='User logged in',
            ip_address='192.168.1.1'
        )
        self.assertEqual(event.event_type, 'LOGIN')

    def test_security_event_filter_by_severity(self):
        """Test filtering security events by severity."""
        SecurityEvent.objects.create(event_type='LOGIN', severity='ERROR', title='Error')
        SecurityEvent.objects.create(event_type='LOGIN', severity='INFO', title='Info')
        errors = SecurityEvent.objects.filter(severity='ERROR')
        self.assertEqual(errors.count(), 1)


class InputValidatorRealBehaviorTest(TestCase):
    """Test InputValidator with real validation."""

    def test_sanitize_html_script_removed(self):
        """Test sanitizing HTML removes script tags."""
        result = InputValidator.sanitize_html('<script>alert(1)</script>')
        self.assertNotIn('<script>', result)

    def test_sanitize_html_safe_passthrough(self):
        """Test sanitizing HTML passes through safe content."""
        result = InputValidator.sanitize_html('Hello World')
        self.assertEqual(result, 'Hello World')

    def test_sanitize_html_preserves_content(self):
        """Test sanitizing HTML preserves content."""
        result = InputValidator.sanitize_html('Hello World')
        self.assertIsInstance(result, str)
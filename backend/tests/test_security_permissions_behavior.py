"""
Security permissions behavior tests.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from security.models import Role, Permission, UserRole


class RoleModelBehaviorTest(TestCase):
    """Test Role model behavior."""

    def test_create_role_with_defaults(self):
        """Test creating a role with default values."""
        role = Role.objects.create(name='Admin', description='Administrator')
        self.assertTrue(role.is_active)

    def test_role_unique_name(self):
        """Test role name must be unique."""
        Role.objects.create(name='Manager')
        with self.assertRaises(Exception):
            Role.objects.create(name='Manager')

    def test_role_str(self):
        """Test role string representation."""
        role = Role.objects.create(name='Cashier')
        self.assertEqual(str(role), 'Cashier')


class PermissionModelBehaviorTest(TestCase):
    """Test Permission model behavior."""

    def test_create_permission(self):
        """Test creating a permission."""
        perm = Permission.objects.create(
            name='View Sales',
            codename='view_sales',
            module='sales'
        )
        self.assertEqual(perm.codename, 'view_sales')

    def test_permission_str(self):
        """Test permission string representation."""
        perm = Permission.objects.create(
            name='Create Invoice',
            codename='create_invoice',
            module='sales'
        )
        self.assertIn('create_invoice', str(perm))


class UserRoleBehaviorTest(TestCase):
    """Test UserRole model behavior."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.role = Role.objects.create(name='Cashier')

    def test_assign_role_to_user(self):
        """Test assigning a role to a user."""
        user_role = UserRole.objects.create(user=self.user, role=self.role)
        self.assertEqual(user_role.user, self.user)
        self.assertEqual(user_role.role, self.role)

    def test_user_can_have_multiple_roles(self):
        """Test user can have multiple roles."""
        role2 = Role.objects.create(name='Manager')
        UserRole.objects.create(user=self.user, role=self.role)
        UserRole.objects.create(user=self.user, role=role2)
        self.assertEqual(UserRole.objects.filter(user=self.user).count(), 2)

    def test_user_role_cascade_delete(self):
        """Test user role deleted when user is deleted."""
        UserRole.objects.create(user=self.user, role=self.role)
        user_id = self.user.id
        self.user.delete()
        self.assertEqual(UserRole.objects.filter(user_id=user_id).count(), 0)
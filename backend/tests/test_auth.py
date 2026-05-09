"""
Tests for User Authentication & Role Management (Phase 5).
Uses factory patterns from tests.factories where applicable.
"""
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from security.models import Role, Permission, UserRole, AuditLog

User = get_user_model()


class LoginViewTests(APITestCase):
    """Tests for the login endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='StrongPass123!',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )

    def test_login_success(self):
        """Test successful login returns JWT token."""
        url = '/api/auth/login/'
        data = {'username': 'testuser', 'password': 'StrongPass123!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user_id', response.data)
        self.assertIn('roles', response.data)

    def test_login_invalid_password(self):
        """Test login with wrong password fails."""
        url = '/api/auth/login/'
        data = {'username': 'testuser', 'password': 'WrongPass'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_login_nonexistent_user(self):
        """Test login with nonexistent username fails."""
        url = '/api/auth/login/'
        data = {'username': 'nobody', 'password': 'test123'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        """Test login with missing fields fails."""
        url = '/api/auth/login/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_creates_audit_log(self):
        """Test successful login creates audit log entry."""
        url = '/api/auth/login/'
        data = {'username': 'testuser', 'password': 'StrongPass123!'}
        self.client.post(url, data, format='json')
        audit = AuditLog.objects.filter(
            user=self.user,
            action='LOGIN'
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.additional_data['username'], 'testuser')

    def test_failed_login_creates_audit_log(self):
        """Test failed login creates security event."""
        url = '/api/auth/login/'
        data = {'username': 'testuser', 'password': 'WrongPass'}
        self.client.post(url, data, format='json')
        audit = AuditLog.objects.filter(
            action='LOGIN_FAILED'
        ).first()
        self.assertIsNotNone(audit)


class LogoutViewTests(APITestCase):
    """Tests for the logout endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='logoutuser',
            password='StrongPass123!'
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_logout_success(self):
        """Test successful logout."""
        url = '/api/auth/logout/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_logout_creates_audit_log(self):
        """Test logout creates audit log entry."""
        url = '/api/auth/logout/'
        self.client.post(url, {}, format='json')
        audit = AuditLog.objects.filter(
            user=self.user,
            action='LOGOUT'
        ).first()
        self.assertIsNotNone(audit)

    def test_logout_without_auth(self):
        """Test logout without authentication fails."""
        self.client.force_authenticate(user=None)
        url = '/api/auth/logout/'
        response = self.client.post(url, {}, format='json')
        # Either 401 or 403 is acceptable
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class UserProfileTests(APITestCase):
    """Tests for the user profile endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='profileuser',
            password='StrongPass123!',
            email='profile@example.com',
            first_name='Profile',
            last_name='User'
        )
        # Create a role and assign to user
        cls.role = Role.objects.create(name='Pharmacist', description='Pharmacist role')
        Permission.objects.create(
            codename='view_inventory',
            module='inventory',
            description='View inventory'
        )
        cls.permission = Permission.objects.get(codename='view_inventory')
        from security.models import RolePermission
        RolePermission.objects.create(role=cls.role, permission=cls.permission)
        UserRole.objects.create(user=cls.user, role=cls.role)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_profile_success(self):
        """Test getting user profile returns roles and permissions."""
        url = '/api/auth/profile/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'profileuser')
        self.assertIn('roles', response.data)
        self.assertIn('permissions', response.data)
        self.assertIn('Pharmacist', response.data['roles'])
        self.assertIn('view_inventory', response.data['permissions'])

    def test_profile_without_auth(self):
        """Test profile without authentication fails."""
        self.client.force_authenticate(user=None)
        url = '/api/auth/profile/'
        response = self.client.get(url)
        # Either 401 or 403 is acceptable
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class ChangePasswordTests(APITestCase):
    """Tests for the change password endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='passuser',
            password='OldPass123!'
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_change_password_success(self):
        """Test successful password change."""
        url = '/api/auth/change-password/'
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify can login with new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_change_password_wrong_old(self):
        """Test change password fails with wrong old password."""
        url = '/api/auth/change-password/'
        data = {
            'old_password': 'WrongPass',
            'new_password': 'NewPass456!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_missing_fields(self):
        """Test change password fails with missing fields."""
        url = '/api/auth/change-password/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_weak_password(self):
        """Test change password fails with weak password."""
        url = '/api/auth/change-password/'
        data = {
            'old_password': 'OldPass123!',
            'new_password': '123'  # Too short, all digits
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_creates_audit_log(self):
        """Test password change creates audit log."""
        url = '/api/auth/change-password/'
        data = {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!'
        }
        self.client.post(url, data, format='json')
        audit = AuditLog.objects.filter(
            user=self.user,
            action='UPDATE'
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.additional_data['action'], 'password_change')


class JWTAuthenticationTests(APITestCase):
    """Tests for JWT authentication integration."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='jwtuser',
            password='JwtPass123!'
        )

    def test_access_protected_endpoint_with_jwt(self):
        """Test accessing protected endpoint with JWT token."""
        # Login to get token
        login_url = '/api/auth/login/'
        login_data = {'username': 'jwtuser', 'password': 'JwtPass123!'}
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['token']

        # Access protected endpoint with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = '/api/auth/profile/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_access_without_token_fails(self):
        """Test accessing protected endpoint without token fails."""
        self.client.credentials()
        url = '/api/auth/profile/'
        response = self.client.get(url)
        # Either 401 or 403 is acceptable for unauthenticated requests
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_access_with_invalid_token_fails(self):
        """Test accessing protected endpoint with invalid token fails."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        url = '/api/auth/profile/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

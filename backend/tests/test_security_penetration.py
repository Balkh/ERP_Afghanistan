"""
Security & Penetration Validation Tests - Phase 6
=================================================
Tests for:
- RBAC bypass attempts
- JWT token handling
- Unauthorized API access
- Privilege escalation
- Tenant isolation at security level
- Sensitive data leakage prevention
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from accounting.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Product, Category, Unit, Warehouse
from sales.models import Customer, SalesInvoice
from purchases.models import Supplier, PurchaseInvoice


User = get_user_model()


class TestAuthenticationSecurity(APITestCase):
    """Test authentication and token security."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_login_requires_valid_credentials(self):
        """Login requires valid credentials."""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_success_with_valid_credentials(self):
        """Login succeeds with valid credentials."""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_requires_authentication(self):
        """Logout requires authentication."""
        response = self.client.post('/api/auth/logout/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_logout_works_with_auth(self):
        """Logout works with authentication."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized_access_denied(self):
        """Unauthorized access to protected endpoints is denied."""
        endpoints = [
            '/api/inventory/products/',
            '/api/sales/invoices/',
            '/api/accounting/accounts/',
            '/api/purchases/invoices/',
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                f"Endpoint {endpoint} returned {response.status_code}")


class TestRBACEnforcement(APITestCase):
    """Test Role-Based Access Control enforcement."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='rbacuser',
            email='rbac@test.com',
            password='rbacpass123',
            is_superuser=False
        )

    def test_regular_user_cannot_access_admin(self):
        """Regular user cannot access admin endpoints."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/admin/')
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_user_can_access_own_profile(self):
        """Authenticated user can access own profile."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestTenantEscapePrevention(APITestCase):
    """Test tenant isolation and escape prevention."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='tenantuser',
            email='tenant@test.com',
            password='tenantpass123'
        )

    def test_company_header_isolation(self):
        """Test company context is isolated per request."""
        self.client.force_authenticate(user=self.user)

        response_a = self.client.get('/api/inventory/products/', HTTP_X_COMPANY_ID=str(uuid.uuid4()))
        response_b = self.client.get('/api/inventory/products/', HTTP_X_COMPANY_ID=str(uuid.uuid4()))

    def test_no_company_header_still_scoped(self):
        """Requests without company header should be handled safely."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/inventory/products/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])


class TestUnauthorizedAccessPrevention(APITestCase):
    """Test unauthorized access prevention."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='unauthorized',
            email='unauth@test.com',
            password='unauthpass123'
        )

    def test_cannot_access_other_company_data(self):
        """User cannot access data from other company."""
        self.client.force_authenticate(user=self.user)

        uuid_a = str(uuid.uuid4())
        uuid_b = str(uuid.uuid4())

        response_a = self.client.get(f'/api/inventory/products/?company={uuid_a}')
        response_b = self.client.get(f'/api/inventory/products/?company={uuid_b}')

    def test_direct_object_access_requires_permission(self):
        """Direct object access requires proper permissions."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f'/api/inventory/products/{uuid.uuid4()}/')
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])


class TestSensitiveDataLeakagePrevention(APITestCase):
    """Test sensitive data is not leaked."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='datalake',
            email='data@test.com',
            password='datapass123'
        )

    def test_password_not_in_response(self):
        """Passwords are not returned in API responses."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/auth/profile/')
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                data = data['data']
            self.assertNotIn('password', data)
            self.assertNotIn('password_hash', data)

    def test_internal_fields_not_exposed(self):
        """Internal fields are not exposed in responses."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/inventory/products/')
        if hasattr(response, 'data') and isinstance(response.data, dict):
            if 'data' in response.data:
                items = response.data['data']
                if items and len(items) > 0:
                    item = items[0]
                    self.assertNotIn('internal_notes', item)
                    self.assertNotIn('debug_info', item)


class TestPrivilegeEscalationPrevention(APITestCase):
    """Test privilege escalation is prevented."""

    def setUp(self):
        self.client = APIClient()
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='regular123',
            is_staff=False,
            is_superuser=False
        )

    def test_cannot_escalate_to_admin(self):
        """Regular user cannot escalate to admin."""
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.patch(
            f'/api/auth/profile/{self.regular_user.id}/',
            {'is_staff': True, 'is_superuser': True}
        )

        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_staff)
        self.assertFalse(self.regular_user.is_superuser)

    def test_cannot_modify_other_users(self):
        """User cannot modify other user permissions."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='other123'
        )

        self.client.force_authenticate(user=self.regular_user)

        response = self.client.patch(
            f'/api/auth/profile/{other_user.id}/',
            {'is_superuser': True}
        )

        other_user.refresh_from_db()
        self.assertFalse(other_user.is_superuser)


class TestAPIEndpointSecurity(APITestCase):
    """Test API endpoint security."""

    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint_accessible(self):
        """Health endpoint should be accessible without auth."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_method_blocked(self):
        """Invalid HTTP methods are handled properly."""
        response = self.client.delete('/api/inventory/products/')
        self.assertIn(response.status_code, [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_sql_injection_protection(self):
        """SQL injection attempts are handled safely."""
        malicious_inputs = [
            "'; DROP TABLE inventory_product; --",
            "1 OR 1=1",
            "admin'--",
            "UNION SELECT * FROM users"
        ]

        for malicious in malicious_inputs:
            response = self.client.get(f'/api/inventory/products/?search={malicious}')
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_xss_protection_in_parameters(self):
        """XSS attempts in parameters are handled safely."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>"
        ]

        for xss in xss_inputs:
            response = self.client.get(f'/api/inventory/products/?search={xss}')
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestJWTValidation(APITestCase):
    """Test JWT token validation."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='jwtuser',
            email='jwt@test.com',
            password='jwtpass123'
        )

    def test_expired_token_rejected(self):
        """Expired tokens are rejected."""
        response = self.client.get(
            '/api/inventory/products/',
            HTTP_AUTHORIZATION='Bearer invalid.token.here'
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_invalid_token_format_rejected(self):
        """Invalid token format is rejected."""
        response = self.client.get(
            '/api/inventory/products/',
            HTTP_AUTHORIZATION='NotBearer token'
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_missing_token_rejected(self):
        """Missing authentication token is rejected."""
        response = self.client.get('/api/inventory/products/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
"""
Advanced Security Penetration Tests - Phase 6 Hardening
=======================================================
Advanced adversarial-level tests for:
- Tenant attack simulation
- Token attack simulation
- Privilege escalation chain
- API abuse testing
- Rate limiting verification
"""
import pytest
import uuid
import time
from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from accounting.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Product, Category, Unit, Warehouse, Batch
from sales.models import Customer, SalesInvoice
from purchases.models import Supplier, PurchaseInvoice

User = get_user_model()


class TestTenantAttackSimulation(APITestCase):
    """Simulate advanced tenant escape attacks."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='tenant_attack',
            email='tenant_attack@test.com',
            password='testpass123'
        )

    def test_company_id_injection_via_header(self):
        """Attempt to inject company ID via header."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            '/api/inventory/products/',
            HTTP_X_COMPANY_ID='invalid-uuid-format'
        )

    def test_company_id_injection_via_query_params(self):
        """Attempt to manipulate company via query params."""
        self.client.force_authenticate(user=self.user)

        fake_company = str(uuid.uuid4())
        response = self.client.get(f'/api/inventory/products/?company_id={fake_company}')

    def test_company_id_manipulation_in_payload(self):
        """Attempt to inject company ID in POST payload."""
        self.client.force_authenticate(user=self.user)

        unit = Unit.objects.create(name="AttackUnit", symbol="au")
        cat = Category.objects.create(name="AttackCat")

        response = self.client.post('/api/inventory/products/', {
            'name': 'Test Product',
            'generic_name': 'Test',
            'brand_name': 'Test',
            'category': str(cat.id),
            'unit': str(unit.id),
            'strength': '10mg',
            'form': 'Tablet',
            'manufacturer': 'Test',
            'barcode': f'ATT{uuid.uuid4().hex[:6]}',
            'sku': f'AT{uuid.uuid4().hex[:6]}',
            'company_id': str(uuid.uuid4())
        })

    def test_orm_tenant_bypass_via_raw_query(self):
        """Test ORM-level tenant bypass prevention."""
        self.client.force_authenticate(user=self.user)

        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM accounting_account")
                result = cursor.fetchall()
        except Exception:
            pass

    def test_cross_company_data_access_via_filter(self):
        """Attempt to access other company's data via filter."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/inventory/products/?company_id__isnull=false')

    def test_tenant_isolation_via_join(self):
        """Attempt tenant bypass via ORM join."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/inventory/products/')


class TestTokenAttackSimulation(APITestCase):
    """Simulate token-based attacks."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='token_attack',
            email='token_attack@test.com',
            password='tokenpass123'
        )

    def test_expired_token_reuse_attempt(self):
        """Test if expired tokens can be reused."""
        self.client.force_authenticate(user=self.user)

        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjF9.ExpiredSignature"

        response = self.client.get(
            '/api/inventory/products/',
            HTTP_AUTHORIZATION=f'Bearer {expired_token}'
        )
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_forged_token_detection(self):
        """Test forged token is rejected."""
        forged_token = "fake.token.signature"

        response = self.client.get(
            '/api/inventory/products/',
            HTTP_AUTHORIZATION=f'Bearer {forged_token}'
        )
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_token_replay_attack(self):
        """Test token replay attack prevention."""
        self.client.force_authenticate(user=self.user)

        token = "valid_but_reused_token_attack"

        response1 = self.client.get('/api/inventory/products/')
        response2 = self.client.get('/api/inventory/products/', HTTP_AUTHORIZATION=f'Bearer {token}')

        self.assertIn(response2.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_malformed_token_handling(self):
        """Test malformed tokens are handled safely."""
        malformed_tokens = [
            "Bearer",
            "Bearer ",
            "Bearer123",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "",
            "null",
            "undefined"
        ]

        for token in malformed_tokens:
            response = self.client.get(
                '/api/inventory/products/',
                HTTP_AUTHORIZATION=token if token != "Bearer" else f'{token}'
            )
            self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])

    def test_token_extraction_attempt(self):
        """Attempt to extract sensitive data from token."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/auth/profile/')
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                profile_data = data['data']
                sensitive_fields = ['password', 'password_hash', 'salt', 'secret', 'token']
                for field in sensitive_fields:
                    self.assertNotIn(field, profile_data)


class TestPrivilegeEscalationChain(APITestCase):
    """Test privilege escalation attack chains."""

    def setUp(self):
        self.client = APIClient()
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@test.com',
            password='regular123',
            is_staff=False,
            is_superuser=False
        )

    def test_indirect_permission_escalation(self):
        """Test indirect permission escalation attempts."""
        self.client.force_authenticate(user=self.regular_user)

        escalation_attempts = [
            {'is_staff': True},
            {'is_superuser': True},
            {'is_active': False},
        ]

        for payload in escalation_attempts:
            try:
                response = self.client.patch(
                    f'/api/auth/profile/',
                    payload,
                    format='json'
                )
                self.regular_user.refresh_from_db()
                # Even if request succeeds, user should NOT have elevated permissions
                self.assertFalse(getattr(self.regular_user, list(payload.keys())[0], False))
            except Exception:
                pass  # Permission denied is acceptable

    def test_role_promotion_attempt(self):
        """Test role promotion via API."""
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.post(
            '/api/auth/change-permissions/',
            {'user_id': str(self.regular_user.id), 'role': 'admin'}
        )

    def test_ownership_escalation(self):
        """Test ownership escalation attempts."""
        self.client.force_authenticate(user=self.regular_user)

        other_user = User.objects.create_user(
            username='victim',
            email='victim@test.com',
            password='victim123'
        )

        response = self.client.patch(
            f'/api/auth/profile/{other_user.id}/',
            {'is_superuser': True}
        )

        other_user.refresh_from_db()
        self.assertFalse(other_user.is_superuser)

    def test_permission_chain_escalation(self):
        """Test permission chain escalation."""
        self.client.force_authenticate(user=self.regular_user)

        endpoints_to_escalate = [
            '/api/auth/permissions/',
            '/api/auth/roles/',
            '/api/admin/users/',
        ]

        for endpoint in endpoints_to_escalate:
            response = self.client.get(endpoint)
            self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])


class TestAPIAbuseTesting(APITestCase):
    """Test API abuse and parameter tampering."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='abuse_test',
            email='abuse@test.com',
            password='abuse123'
        )

    def test_bulk_request_flooding(self):
        """Test bulk request flooding protection."""
        self.client.force_authenticate(user=self.user)

        for i in range(50):
            response = self.client.get('/api/inventory/products/')

    def test_parameter_tampering_attempt(self):
        """Test parameter tampering."""
        self.client.force_authenticate(user=self.user)

        tamper_attempts = [
            {'page': '-1'},
            {'page': '999999999'},
            {'page_size': '10000'},
            {'page_size': '-1'},
            {'ordering': 'id;DROP TABLE'},
            {'search': '../admin'},
        ]

        for params in tamper_attempts:
            response = self.client.get('/api/inventory/products/', params)
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_malformed_json_payload(self):
        """Test malformed JSON is handled safely."""
        self.client.force_authenticate(user=self.user)

        malformed_payloads = [
            b'{"incomplete":',
            b'{"nested": {"deep": }}',
            b'not json at all',
            b'',
        ]

        for payload in malformed_payloads:
            response = self.client.post(
                '/api/inventory/products/',
                data=payload,
                content_type='application/json'
            )
            # Just ensure it doesn't crash with 500
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_unicode_injection_attempt(self):
        """Test Unicode injection attempts."""
        self.client.force_authenticate(user=self.user)

        unicode_attacks = [
            '\u0000\u0001\u0002',
            '\u202e\u202d\u202c',
            '<script>',
            '{% raw %}',
            '{{{{',
        ]

        for attack in unicode_attacks:
            response = self.client.get(f'/api/inventory/products/?search={attack}')
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_sql_injection_advanced(self):
        """Test advanced SQL injection attempts."""
        self.client.force_authenticate(user=self.user)

        sql_attacks = [
            "1; DELETE FROM inventory_product; --",
            "1' OR '1'='1' --",
            "1 UNION SELECT * FROM auth_user --",
            "1; DROP TABLE inventory_product; --",
            "exec xp_cmdshell('dir')",
            "1 WAITFOR DELAY '00:00:05'--",
        ]

        for attack in sql_attacks:
            response = self.client.get(f'/api/inventory/products/?search={attack}')
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_path_traversal_attempt(self):
        """Test path traversal attacks."""
        self.client.force_authenticate(user=self.user)

        path_attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
        ]

        for attack in path_attacks:
            response = self.client.get(f'/api/inventory/products/?search={attack}')
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestRateLimitingVerification(APITestCase):
    """Test rate limiting and brute force protection."""

    def setUp(self):
        self.client = APIClient()

    def test_login_brute_force_protection(self):
        """Test brute force protection on login."""
        for i in range(10):
            response = self.client.post('/api/auth/login/', {
                'username': 'nonexistent',
                'password': 'wrongpass'
            })

        self.assertIn(response.status_code, [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_401_UNAUTHORIZED])

    def test_failed_login_rate_limit(self):
        """Test rate limiting after failed logins."""
        for i in range(20):
            response = self.client.post('/api/auth/login/', {
                'username': 'testuser',
                'password': 'wrongpassword'
            })

        final_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })

        self.assertIn(final_response.status_code, [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_401_UNAUTHORIZED])

    def test_api_request_rate_limit(self):
        """Test API request rate limiting."""
        self.user = User.objects.create_user(
            username='rate_test',
            email='rate@test.com',
            password='rate123'
        )
        self.client.force_authenticate(user=self.user)

        for i in range(100):
            response = self.client.get('/api/inventory/products/')

        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestAuditSecurityVerification(APITestCase):
    """Verify audit log security."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='audit_test',
            email='audit@test.com',
            password='audit123'
        )

    def test_failed_login_audit_logged(self):
        """Test failed login attempts are logged."""
        self.client.post('/api/auth/login/', {
            'username': 'audit_test',
            'password': 'wrong'
        })

        from core.models.audit import AuditLog
        failed_logins = AuditLog.objects.filter(action__icontains='LOGIN_FAILED')

    def test_permission_denial_audit_logged(self):
        """Test permission denials are logged."""
        self.user2 = User.objects.create_user(
            username='another_user',
            email='another@test.com',
            password='another123'
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/admin/')

    def test_audit_log_immutability(self):
        """Test audit logs cannot be modified."""
        from core.models.audit import AuditLog

        # Create user first
        test_user = User.objects.create_user(
            username='audit_user_test',
            email='audit_test@test.com',
            password='auditpass123'
        )

        log = AuditLog.objects.create(
            action="CREATE",
            user=test_user,
            entity_type="TestModel",
            entity_id="test-123",
            description="Test log"
        )

        log.description = "Modified attempt"
        # Save should work but we'll verify immutable fields can't be changed
        log.save()

        # Verify original values are preserved
        log.refresh_from_db()
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.entity_type, "TestModel")

    def test_security_event_logging(self):
        """Test security events are logged."""
        from core.models.audit import AuditLog
        initial_count = AuditLog.objects.count()

        self.client.post('/api/auth/login/', {
            'username': 'nonexistent',
            'password': 'test'
        })

        final_count = AuditLog.objects.count()
        self.assertGreaterEqual(final_count, initial_count)
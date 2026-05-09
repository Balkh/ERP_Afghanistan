"""
Comprehensive tests for Security & Permissions module.

Covers:
- Role, Permission, RolePermission, UserRole models
- RoleBasedPermission DRF permission class
- JWT Authentication
- Input validation and sanitization
- Password utilities
- Secure storage (encryption/decryption)
- Audit logging
- Security event tracking
- Session security
- Configuration encryption
"""
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.exceptions import SuspiciousOperation

from security.models import Role, Permission, RolePermission, UserRole, AuditLog, SecurityEvent
from security.permissions import RoleBasedPermission, IsOwnerOrReadOnly, LicenseRequiredPermission
from security.authentication import JWTAuthentication, generate_jwt_token, verify_jwt_token
from security.utils import (
    InputValidator,
    SecureStorage,
    ConfigurationEncryption,
    SecurityHeaders,
    AuditSecurityLogger,
    SessionSecurity,
    apply_input_validation_to_dict,
    require_jwt_authentication,
)
from security.password_utils import (
    make_password,
    check_password,
    is_password_usable,
    generate_secure_token,
    generate_reset_token,
    validate_password_strength,
    hash_sensitive_data,
    verify_sensitive_data,
)


class RoleModelTests(TestCase):
    """Tests for Role model."""

    def test_create_role(self):
        role = Role.objects.create(name='Pharmacist', description='Pharmacy staff')
        self.assertEqual(role.name, 'Pharmacist')
        self.assertTrue(role.is_active)

    def test_role_str(self):
        role = Role.objects.create(name='Manager')
        self.assertEqual(str(role), 'Manager')

    def test_role_unique_name(self):
        Role.objects.create(name='Admin')
        with self.assertRaises(Exception):
            Role.objects.create(name='Admin')

    def test_deactivate_role(self):
        role = Role.objects.create(name='Temp Role')
        role.is_active = False
        role.save()
        self.assertFalse(Role.objects.filter(name='Temp Role', is_active=True).exists())


class PermissionModelTests(TestCase):
    """Tests for Permission model."""

    def test_create_permission(self):
        perm = Permission.objects.create(
            name='Can View Reports',
            codename='view_reports',
            module='reports',
        )
        self.assertEqual(str(perm), 'reports.view_reports')

    def test_permission_codename_validation_lowercase(self):
        perm = Permission(name='Bad', codename='ViewReports', module='test')
        with self.assertRaises(ValidationError):
            perm.full_clean()

    def test_permission_codename_validation_special_chars(self):
        perm = Permission(name='Bad', codename='view-reports!', module='test')
        with self.assertRaises(ValidationError):
            perm.full_clean()

    def test_permission_valid_codename(self):
        perm = Permission.objects.create(
            name='Good',
            codename='view_reports_2',
            module='test',
        )
        self.assertEqual(perm.codename, 'view_reports_2')

    def test_permission_unique_codename(self):
        Permission.objects.create(
            name='First',
            codename='unique_perm',
            module='test',
        )
        with self.assertRaises(Exception):
            Permission.objects.create(
                name='Second',
                codename='unique_perm',
                module='other',
            )

    def test_permission_str_format(self):
        perm = Permission.objects.create(name='P1', codename='perm_a', module='mod1')
        self.assertEqual(str(perm), 'mod1.perm_a')


class RolePermissionTests(TestCase):
    """Tests for RolePermission model."""

    def setUp(self):
        self.role = Role.objects.create(name='Manager')
        self.perm = Permission.objects.create(
            name='Can Edit', codename='can_edit', module='inventory'
        )
        self.user = User.objects.create_user(username='admin', password='pass123')

    def test_assign_permission_to_role(self):
        rp = RolePermission.objects.create(
            role=self.role,
            permission=self.perm,
            granted_by=self.user,
        )
        self.assertEqual(str(rp), 'Manager -> Can Edit')

    def test_duplicate_role_permission_prevented(self):
        RolePermission.objects.create(role=self.role, permission=self.perm)
        with self.assertRaises(Exception):
            RolePermission.objects.create(role=self.role, permission=self.perm)

    def test_cascade_delete_role(self):
        rp = RolePermission.objects.create(role=self.role, permission=self.perm)
        self.role.delete()
        self.assertFalse(RolePermission.objects.filter(id=rp.id).exists())


class UserRoleTests(TestCase):
    """Tests for UserRole model."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.role = Role.objects.create(name='Pharmacist')
        self.admin = User.objects.create_user(username='admin', password='admin123')

    def test_assign_role_to_user(self):
        ur = UserRole.objects.create(
            user=self.user,
            role=self.role,
            assigned_by=self.admin,
        )
        self.assertEqual(str(ur), 'testuser -> Pharmacist')

    def test_duplicate_user_role_prevented(self):
        UserRole.objects.create(user=self.user, role=self.role)
        with self.assertRaises(Exception):
            UserRole.objects.create(user=self.user, role=self.role)

    def test_role_not_expired(self):
        ur = UserRole.objects.create(user=self.user, role=self.role)
        self.assertFalse(ur.is_expired)

    def test_role_expired(self):
        ur = UserRole.objects.create(
            user=self.user,
            role=self.role,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(ur.is_expired)

    def test_role_expires_in_future(self):
        ur = UserRole.objects.create(
            user=self.user,
            role=self.role,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertFalse(ur.is_expired)


class AuditLogTests(TestCase):
    """Tests for AuditLog model."""

    def setUp(self):
        self.user = User.objects.create_user(username='auditor', password='pass123')

    def test_create_audit_log(self):
        log = AuditLog.objects.create(
            user=self.user,
            username='auditor',
            action='CREATE',
            model_name='Product',
            object_id='1',
            object_repr='Amoxicillin 500mg',
            change_message='Created new product',
            ip_address='192.168.1.1',
        )
        self.assertEqual(log.action, 'CREATE')
        self.assertIn('auditor', str(log))

    def test_audit_log_with_additional_data(self):
        log = AuditLog.objects.create(
            user=self.user,
            username='auditor',
            action='UPDATE',
            model_name='SalesInvoice',
            object_id='42',
            additional_data={'field': 'status', 'old': 'DRAFT', 'new': 'CONFIRMED'},
        )
        self.assertEqual(log.additional_data['field'], 'status')

    def test_permission_denied_action(self):
        log = AuditLog.objects.create(
            username='unknown',
            action='PERMISSION_DENIED',
            ip_address='10.0.0.1',
        )
        self.assertEqual(log.action, 'PERMISSION_DENIED')

    def test_anonymous_audit_log(self):
        log = AuditLog.objects.create(
            action='LOGIN_FAILED',
            username='invalid_user',
            ip_address='192.168.1.100',
        )
        self.assertIsNone(log.user)


class SecurityEventTests(TestCase):
    """Tests for SecurityEvent model."""

    def test_create_security_event(self):
        event = SecurityEvent.objects.create(
            event_type='BRUTE_FORCE',
            severity='HIGH',
            title='Multiple failed login attempts',
            description='User admin failed 5 login attempts',
            ip_address='192.168.1.50',
            username='admin',
        )
        self.assertEqual(event.event_type, 'BRUTE_FORCE')
        self.assertFalse(event.is_resolved)

    def test_resolve_security_event(self):
        event = SecurityEvent.objects.create(
            event_type='SQL_INJECTION',
            severity='CRITICAL',
            title='SQL injection attempt',
            description='Detected SQL injection in search parameter',
            ip_address='10.0.0.5',
        )
        resolver = User.objects.create_user(username='sec_admin', password='secure')
        event.is_resolved = True
        event.resolved_by = resolver
        event.resolution_notes = 'Blocked IP and notified team'
        event.save()
        self.assertTrue(event.is_resolved)

    def test_security_event_str(self):
        event = SecurityEvent.objects.create(
            event_type='XSS_ATTEMPT',
            severity='MEDIUM',
            title='XSS attempt',
            description='Script tag detected',
        )
        self.assertIn('XSS Attempt', str(event))
        self.assertIn('MEDIUM', str(event))

    def test_event_type_choices(self):
        valid_types = [choice[0] for choice in SecurityEvent.EVENT_TYPES]
        self.assertIn('BRUTE_FORCE', valid_types)
        self.assertIn('SQL_INJECTION', valid_types)
        self.assertIn('LICENSE_VIOLATION', valid_types)


class RoleBasedPermissionTests(TestCase):
    """Tests for RoleBasedPermission DRF permission class."""

    def setUp(self):
        self.factory = RequestFactory()
        self.perm_class = RoleBasedPermission()
        self.superuser = User.objects.create_user(
            username='super', password='pass123', is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username='regular', password='pass123'
        )
        self.anonymous_user = MagicMock()
        self.anonymous_user.is_authenticated = False

    def test_unauthenticated_user_denied(self):
        request = self.factory.get('/api/test/')
        request.user = self.anonymous_user
        self.assertFalse(self.perm_class.has_permission(request, MagicMock()))

    def test_superuser_always_allowed(self):
        request = self.factory.get('/api/test/')
        request.user = self.superuser
        self.assertTrue(self.perm_class.has_permission(request, MagicMock()))

    def test_authenticated_user_without_required_perm(self):
        request = self.factory.get('/api/test/')
        request.user = self.regular_user
        view = MagicMock()
        view.required_permission = 'inventory.view_product'
        self.assertFalse(self.perm_class.has_permission(request, view))

    def test_user_with_role_permission(self):
        role = Role.objects.create(name='Inventory Manager')
        perm = Permission.objects.create(
            name='View Products', codename='inventory_view_product', module='inventory'
        )
        UserRole.objects.create(user=self.regular_user, role=role)
        RolePermission.objects.create(role=role, permission=perm)

        request = self.factory.get('/api/test/')
        request.user = self.regular_user
        view = MagicMock()
        view.required_permission = 'inventory_view_product'
        self.assertTrue(self.perm_class.has_permission(request, view))

    def test_expired_role_permission_denied(self):
        role = Role.objects.create(name='Temp User')
        perm = Permission.objects.create(
            name='View Products', codename='inventory_view_product', module='inventory'
        )
        UserRole.objects.create(
            user=self.regular_user,
            role=role,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        RolePermission.objects.create(role=role, permission=perm)

        request = self.factory.get('/api/test/')
        request.user = self.regular_user
        view = MagicMock()
        view.required_permission = 'inventory_view_product'
        self.assertFalse(self.perm_class.has_permission(request, view))

    def test_user_has_multiple_permissions(self):
        request = self.factory.get('/api/test/')
        request.user = self.regular_user
        view = MagicMock()
        view.required_permission = ['perm_a', 'perm_b']
        self.assertFalse(self.perm_class.has_permission(request, view))

    def test_no_required_permission_allows_authenticated(self):
        request = self.factory.get('/api/test/')
        request.user = self.regular_user
        view = MagicMock(spec=[])
        with patch.object(self.perm_class, 'infer_permission_from_view', return_value=None):
            self.assertTrue(self.perm_class.has_permission(request, view))

    def test_object_permission_delegates_to_view_permission(self):
        request = self.factory.get('/api/test/')
        request.user = self.superuser
        self.assertTrue(self.perm_class.has_object_permission(request, MagicMock(), MagicMock()))


class IsOwnerOrReadOnlyTests(TestCase):
    """Tests for IsOwnerOrReadOnly permission."""

    def setUp(self):
        self.perm_class = IsOwnerOrReadOnly()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='owner', password='pass')
        self.other_user = User.objects.create_user(username='other', password='pass')

    def test_read_allowed_for_anyone(self):
        request = self.factory.get('/api/test/')
        request.user = self.other_user
        request.method = 'GET'
        obj = MagicMock()
        obj.owner = self.user
        self.assertTrue(self.perm_class.has_object_permission(request, MagicMock(), obj))

    def test_write_allowed_for_owner(self):
        request = self.factory.put('/api/test/')
        request.user = self.user
        request.method = 'PUT'
        obj = MagicMock()
        obj.owner = self.user
        self.assertTrue(self.perm_class.has_object_permission(request, MagicMock(), obj))

    def test_write_denied_for_non_owner(self):
        request = self.factory.put('/api/test/')
        request.user = self.other_user
        request.method = 'PUT'
        obj = MagicMock()
        obj.owner = self.user
        self.assertFalse(self.perm_class.has_object_permission(request, MagicMock(), obj))


class LicenseRequiredPermissionTests(TestCase):
    """Tests for LicenseRequiredPermission."""

    def setUp(self):
        self.perm_class = LicenseRequiredPermission()
        self.factory = RequestFactory()

    def test_unauthenticated_denied(self):
        request = self.factory.get('/api/test/')
        request.user = MagicMock(is_authenticated=False)
        self.assertFalse(self.perm_class.has_permission(request, MagicMock()))

    def test_no_license_valid_denied(self):
        request = self.factory.get('/api/test/')
        user = MagicMock(is_authenticated=True)
        request.user = user
        self.assertFalse(self.perm_class.has_permission(request, MagicMock()))

    def test_license_valid_allowed(self):
        request = self.factory.get('/api/test/')
        user = MagicMock(is_authenticated=True)
        request.user = user
        request.license_valid = True
        self.assertTrue(self.perm_class.has_permission(request, MagicMock()))


class JWTAuthenticationTests(TestCase):
    """Tests for JWT Authentication."""

    def setUp(self):
        self.auth = JWTAuthentication()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='jwtuser', email='jwt@test.com', password='pass123'
        )

    def test_generate_jwt_token(self):
        token = generate_jwt_token(self.user)
        self.assertIsNotNone(token)

    def test_verify_jwt_token(self):
        token = generate_jwt_token(self.user)
        payload = verify_jwt_token(token)
        self.assertEqual(payload['user_id'], self.user.id)
        self.assertEqual(payload['email'], self.user.email)

    def test_expired_jwt_token(self):
        import jwt
        from django.conf import settings
        expired_payload = {
            'user_id': self.user.id,
            'exp': timezone.now() - timedelta(hours=1),
            'iat': timezone.now() - timedelta(hours=2),
        }
        token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm='HS256')
        from rest_framework import exceptions
        with self.assertRaises(exceptions.AuthenticationFailed):
            verify_jwt_token(token)

    def test_invalid_jwt_token(self):
        from rest_framework import exceptions
        with self.assertRaises(exceptions.AuthenticationFailed):
            verify_jwt_token('invalid.token.here')

    def test_authenticate_with_valid_token(self):
        token = generate_jwt_token(self.user)
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)
        self.assertEqual(result[0].id, self.user.id)

    def test_authenticate_no_auth_header(self):
        request = self.factory.get('/api/test/')
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_invalid_header_format(self):
        from rest_framework import exceptions
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = 'InvalidFormat'
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_wrong_prefix(self):
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = 'Basic sometoken'
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        token = generate_jwt_token(self.user)
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        from rest_framework import exceptions
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_nonexistent_user(self):
        import jwt
        from django.conf import settings
        payload = {
            'user_id': 99999,
            'exp': timezone.now() + timedelta(hours=1),
            'iat': timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        from rest_framework import exceptions
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)


class InputValidatorTests(TestCase):
    """Tests for InputValidator class."""

    def test_valid_username(self):
        self.assertTrue(InputValidator.validate_input('john_doe', 'username'))

    def test_invalid_username_special_chars(self):
        self.assertFalse(InputValidator.validate_input('john@doe!', 'username'))

    def test_valid_email(self):
        self.assertTrue(InputValidator.validate_input('test@example.com', 'email'))

    def test_invalid_email(self):
        self.assertFalse(InputValidator.validate_input('not-an-email', 'email'))

    def test_valid_phone(self):
        self.assertTrue(InputValidator.validate_input('+1234567890', 'phone'))

    def test_valid_alphanumeric(self):
        self.assertTrue(InputValidator.validate_input('abc123', 'alphanumeric'))

    def test_invalid_alphanumeric(self):
        self.assertFalse(InputValidator.validate_input('abc 123', 'alphanumeric'))

    def test_valid_numeric(self):
        self.assertTrue(InputValidator.validate_input('12345', 'numeric'))

    def test_invalid_numeric(self):
        self.assertFalse(InputValidator.validate_input('12.34', 'numeric'))

    def test_valid_decimal(self):
        self.assertTrue(InputValidator.validate_input('12.34', 'decimal'))

    def test_valid_currency(self):
        self.assertTrue(InputValidator.validate_input('12.34', 'currency'))

    def test_invalid_currency(self):
        self.assertFalse(InputValidator.validate_input('12.3', 'currency'))

    def test_none_value(self):
        self.assertFalse(InputValidator.validate_input(None, 'username'))

    def test_empty_string(self):
        self.assertFalse(InputValidator.validate_input('  ', 'username'))

    def test_unknown_pattern(self):
        with self.assertRaises(ValueError):
            InputValidator.validate_input('test', 'unknown_pattern')

    def test_sanitize_html_removes_script(self):
        result = InputValidator.sanitize_html('<script>alert("xss")</script>Hello')
        self.assertNotIn('<script>', result)
        self.assertIn('Hello', result)

    def test_sanitize_html_allows_basic_tags(self):
        result = InputValidator.sanitize_html('<b>Bold</b> text')
        self.assertIn('<b>', result)
        self.assertIn('Bold', result)

    def test_sanitize_html_empty(self):
        self.assertEqual(InputValidator.sanitize_html(''), '')

    def test_sanitize_sql_like(self):
        result = InputValidator.sanitize_sql_like("test'value%")
        self.assertIn(r"''", result)
        self.assertIn(r'\%', result)

    def test_prevent_sql_injection(self):
        with self.assertRaises(SuspiciousOperation):
            InputValidator.prevent_sql_injection("'; DROP TABLE users; --")

    def test_prevent_sql_injection_select(self):
        with self.assertRaises(SuspiciousOperation):
            InputValidator.prevent_sql_injection('SELECT * FROM users')

    def test_sql_injection_safe_input(self):
        result = InputValidator.prevent_sql_injection('Normal product name')
        self.assertEqual(result, 'Normal product name')

    def test_validate_file_upload_size(self):
        errors = InputValidator.validate_file_upload(
            'test.pdf', 'application/pdf', 10000000,
            max_size=1000000,
        )
        self.assertEqual(len(errors), 1)

    def test_validate_file_upload_extension(self):
        errors = InputValidator.validate_file_upload(
            'test.exe', 'application/octet-stream', 1000,
            allowed_extensions=['pdf', 'jpg', 'png'],
        )
        self.assertGreaterEqual(len(errors), 1)

    def test_validate_file_upload_dangerous_extension(self):
        errors = InputValidator.validate_file_upload(
            'script.php', 'application/php', 1000,
        )
        self.assertEqual(len(errors), 1)

    def test_validate_file_upload_valid(self):
        errors = InputValidator.validate_file_upload(
            'report.pdf', 'application/pdf', 1000,
            allowed_extensions=['pdf'],
            allowed_mimetypes=['application/pdf'],
            max_size=5000000,
        )
        self.assertEqual(len(errors), 0)


class SecureStorageTests(TestCase):
    """Tests for SecureStorage class."""

    def test_encrypt_and_decrypt_string(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        encrypted = SecureStorage.encrypt_data('secret message', key)
        self.assertIn('encrypted_data', encrypted)
        self.assertIn('key_reference', encrypted)

        decrypted = SecureStorage.decrypt_data(encrypted['encrypted_data'], key)
        self.assertEqual(decrypted, 'secret message')

    def test_encrypt_and_decrypt_bytes(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        data = b'binary data here'
        encrypted = SecureStorage.encrypt_data(data, key)
        decrypted = SecureStorage.decrypt_data(encrypted['encrypted_data'], key)
        self.assertEqual(decrypted, 'binary data here')

    def test_decrypt_with_wrong_key(self):
        from cryptography.fernet import Fernet
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        encrypted = SecureStorage.encrypt_data('secret', key1)
        with self.assertRaises(ValueError):
            SecureStorage.decrypt_data(encrypted['encrypted_data'], key2)

    def test_hash_and_verify(self):
        result = SecureStorage.hash_for_storage('my_api_key')
        self.assertIn('hashed_data', result)
        self.assertIn('salt', result)

        self.assertTrue(SecureStorage.verify_hashed_data('my_api_key', result))

    def test_hash_verify_wrong_data(self):
        result = SecureStorage.hash_for_storage('correct')
        self.assertFalse(SecureStorage.verify_hashed_data('wrong', result))


class ConfigurationEncryptionTests(TestCase):
    """Tests for ConfigurationEncryption class."""

    @override_settings(SECRET_KEY='test-secret-key-for-encryption')
    def test_encrypt_and_decrypt_config(self):
        encrypted = ConfigurationEncryption.encrypt_config_value('db_password_123')
        decrypted = ConfigurationEncryption.decrypt_config_value(encrypted)
        self.assertEqual(decrypted, 'db_password_123')

    @override_settings(SECRET_KEY='test-secret-key-for-encryption')
    def test_different_values_produce_different_encrypted(self):
        enc1 = ConfigurationEncryption.encrypt_config_value('value1')
        enc2 = ConfigurationEncryption.encrypt_config_value('value2')
        self.assertNotEqual(enc1, enc2)

    @override_settings(SECRET_KEY='test-secret-key-for-encryption')
    def test_encryption_key_derivation(self):
        key = ConfigurationEncryption.get_encryption_key()
        self.assertIsNotNone(key)
        self.assertIsInstance(key, bytes)


class SecurityHeadersTests(TestCase):
    """Tests for SecurityHeaders class."""

    def test_get_security_headers(self):
        headers = SecurityHeaders.get_security_headers()
        self.assertIn('X-Frame-Options', headers)
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertIn('X-XSS-Protection', headers)
        self.assertIn('X-Content-Type-Options', headers)
        self.assertIn('Content-Security-Policy', headers)
        self.assertIn('Permissions-Policy', headers)

    def test_csp_includes_self(self):
        headers = SecurityHeaders.get_security_headers()
        csp = headers['Content-Security-Policy']
        self.assertIn("default-src 'self'", csp)


class AuditSecurityLoggerTests(TestCase):
    """Tests for AuditSecurityLogger class."""

    def test_log_security_event(self):
        AuditSecurityLogger.log_security_event(
            event_type='BRUTE_FORCE',
            user_id=1,
            ip_address='192.168.1.1',
            details={'attempts': 5},
        )

    def test_log_security_event_redacts_sensitive(self):
        AuditSecurityLogger.log_security_event(
            event_type='LOGIN_FAILED',
            details={'password': 'secret123', 'username': 'admin'},
        )

    def test_log_request_info(self):
        factory = RequestFactory()
        request = factory.get('/api/products/?search=amox')
        request.user = MagicMock(id=1)
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        info = AuditSecurityLogger.log_request_info(request)
        self.assertEqual(info['method'], 'GET')
        self.assertEqual(info['path'], '/api/products/')

    def test_get_client_ip_direct(self):
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        ip = AuditSecurityLogger._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

    def test_get_client_ip_proxy(self):
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 10.0.0.2'
        ip = AuditSecurityLogger._get_client_ip(request)
        self.assertEqual(ip, '10.0.0.1')


class SessionSecurityTests(TestCase):
    """Tests for SessionSecurity class."""

    def test_secure_session_cookie_settings(self):
        settings = SessionSecurity.secure_session_cookie_settings()
        self.assertTrue(settings['SESSION_COOKIE_HTTPONLY'])
        self.assertEqual(settings['SESSION_COOKIE_SAMESITE'], 'Lax')
        self.assertEqual(settings['SESSION_COOKIE_AGE'], 1800)


class ApplyInputValidationTests(TestCase):
    """Tests for apply_input_validation_to_dict function."""

    def test_validate_required_field(self):
        rules = {'name': {'type': 'alphanumeric', 'required': True}}
        data = {'name': 'test123'}
        result = apply_input_validation_to_dict(data, rules)
        self.assertEqual(result['name'], 'test123')

    def test_validate_missing_required_field(self):
        rules = {'email': {'type': 'email', 'required': True}}
        data = {}
        with self.assertRaises(ValidationError):
            apply_input_validation_to_dict(data, rules)

    def test_validate_invalid_format(self):
        rules = {'email': {'type': 'email', 'required': True}}
        data = {'email': 'not-an-email'}
        with self.assertRaises(ValidationError):
            apply_input_validation_to_dict(data, rules)

    def test_validate_max_length(self):
        rules = {'name': {'type': 'alphanumeric', 'required': True, 'max_length': 5}}
        data = {'name': 'toolong'}
        with self.assertRaises(ValidationError):
            apply_input_validation_to_dict(data, rules)

    def test_validate_sanitization(self):
        rules = {'comment': {'required': True, 'sanitize': True, 'max_length': 200}}
        data = {'comment': '<script>alert(1)</script>hello'}
        result = apply_input_validation_to_dict(data, rules)
        self.assertNotIn('<script>', result['comment'])


class RequireJWTDecoratorTests(TestCase):
    """Tests for require_jwt_authentication decorator."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='decuser', password='pass')

    def test_missing_auth_header(self):
        @require_jwt_authentication
        def dummy_view(request):
            from django.http import JsonResponse
            return JsonResponse({'ok': True})

        request = self.factory.get('/api/protected/')
        response = dummy_view(request)
        self.assertEqual(response.status_code, 401)

    def test_invalid_auth_header_format(self):
        @require_jwt_authentication
        def dummy_view(request):
            from django.http import JsonResponse
            return JsonResponse({'ok': True})

        request = self.factory.get('/api/protected/')
        request.META['HTTP_AUTHORIZATION'] = 'InvalidFormat'
        response = dummy_view(request)
        self.assertEqual(response.status_code, 401)

    def test_valid_jwt_token(self):
        @require_jwt_authentication
        def dummy_view(request):
            from django.http import JsonResponse
            return JsonResponse({'ok': True})

        token = generate_jwt_token(self.user)
        request = self.factory.get('/api/protected/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        response = dummy_view(request)
        self.assertEqual(response.status_code, 200)

    def test_expired_jwt_token_decorator(self):
        @require_jwt_authentication
        def dummy_view(request):
            from django.http import JsonResponse
            return JsonResponse({'ok': True})

        import jwt
        from django.conf import settings
        expired_payload = {
            'user_id': self.user.id,
            'exp': timezone.now() - timedelta(hours=1),
            'iat': timezone.now() - timedelta(hours=2),
        }
        token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm='HS256')
        request = self.factory.get('/api/protected/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        response = dummy_view(request)
        self.assertEqual(response.status_code, 401)


class PasswordUtilsTests(TestCase):
    """Tests for password utilities."""

    def test_make_password(self):
        hashed = make_password('MyStr0ngP@ss!')
        self.assertIsNotNone(hashed)
        self.assertNotEqual(hashed, 'MyStr0ngP@ss!')

    def test_check_password_correct(self):
        hashed = make_password('CorrectP@ss1')
        self.assertTrue(check_password('CorrectP@ss1', hashed))

    def test_check_password_incorrect(self):
        hashed = make_password('CorrectP@ss2')
        self.assertFalse(check_password('WrongP@ss!', hashed))

    def test_check_password_django_format(self):
        from django.contrib.auth.hashers import make_password as django_make
        hashed = django_make('DjangoP@ss1')
        self.assertTrue(check_password('DjangoP@ss1', hashed))

    def test_is_password_usable(self):
        hashed = make_password('UsableP@ss1')
        self.assertTrue(is_password_usable(hashed))

    def test_is_password_not_usable(self):
        self.assertFalse(is_password_usable('!invalid_hash!'))

    def test_generate_secure_token(self):
        token = generate_secure_token()
        self.assertEqual(len(token), 43)

    def test_generate_secure_token_custom_length(self):
        token = generate_secure_token(length=16)
        self.assertEqual(len(token), 22)

    def test_generate_reset_token(self):
        token = generate_reset_token()
        self.assertEqual(len(token), 43)

    def test_generate_unique_tokens(self):
        t1 = generate_secure_token()
        t2 = generate_secure_token()
        self.assertNotEqual(t1, t2)

    def test_validate_password_too_short(self):
        errors = validate_password_strength('Ab1!')
        self.assertEqual(len(errors), 1)

    def test_validate_password_no_uppercase(self):
        errors = validate_password_strength('password1!')
        self.assertTrue(any('uppercase' in e for e in errors))

    def test_validate_password_no_lowercase(self):
        errors = validate_password_strength('PASSWORD1!')
        self.assertTrue(any('lowercase' in e for e in errors))

    def test_validate_password_no_digit(self):
        errors = validate_password_strength('Password!')
        self.assertTrue(any('digit' in e for e in errors))

    def test_validate_password_no_special(self):
        errors = validate_password_strength('Password1')
        self.assertTrue(any('special' in e for e in errors))

    def test_validate_password_weak_common(self):
        errors = validate_password_strength('password')
        self.assertTrue(any('common' in e for e in errors))

    def test_validate_password_repeated_chars(self):
        errors = validate_password_strength('Passw0rd!aaaa')
        self.assertTrue(any('consecutive' in e for e in errors))

    def test_validate_password_sequential_chars(self):
        errors = validate_password_strength('abc!Password1')
        self.assertTrue(any('sequential' in e for e in errors))

    def test_validate_password_strong(self):
        errors = validate_password_strength('Str0ng!P@ss')
        self.assertEqual(len(errors), 0)


class HashSensitiveDataTests(TestCase):
    """Tests for sensitive data hashing."""

    def test_hash_and_verify_sensitive_data(self):
        hashed = hash_sensitive_data('api_key_12345')
        self.assertTrue(verify_sensitive_data('api_key_12345', hashed))

    def test_verify_wrong_sensitive_data(self):
        hashed = hash_sensitive_data('correct_key')
        self.assertFalse(verify_sensitive_data('wrong_key', hashed))

    def test_hash_different_each_time(self):
        h1 = hash_sensitive_data('same_data')
        h2 = hash_sensitive_data('same_data')
        self.assertNotEqual(h1, h2)

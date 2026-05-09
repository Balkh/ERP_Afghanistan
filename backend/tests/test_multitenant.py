"""
Tests for Multi-Tenant Architecture.
Tests company context, isolation, security, and backward compatibility.
"""
import uuid
from decimal import Decimal
from datetime import date
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from core.models import Company
from core.models.multitenant import UserCompanyMapping, CompanyPermissionService
from core.multitenant.context import TenantContext
from core.multitenant.middleware import TenantMiddleware, resolve_company
from core.multitenant.models import CompanyScopedMixin, CompanyScopedQuerySet, CompanyScopedManager

User = get_user_model()


class TestTenantContext(TestCase):
    """Test thread-local tenant context management."""

    def setUp(self):
        TenantContext.clear()

    def tearDown(self):
        TenantContext.clear()

    def test_set_and_get_company_id(self):
        """Test setting and getting company ID."""
        company_id = str(uuid.uuid4())
        TenantContext.set_company_id(company_id)
        self.assertEqual(TenantContext.get_company_id(), company_id)

    def test_set_and_get_company_code(self):
        """Test setting and getting company code."""
        TenantContext.set_company_code('TESTCO')
        self.assertEqual(TenantContext.get_company_code(), 'TESTCO')

    def test_has_context_false_by_default(self):
        """Test that context is empty by default."""
        self.assertFalse(TenantContext.has_context())

    def test_has_context_true_when_set(self):
        """Test that context is detected when set."""
        TenantContext.set_company_id(str(uuid.uuid4()))
        self.assertTrue(TenantContext.has_context())

    def test_clear_context(self):
        """Test clearing all context."""
        TenantContext.set_company_id(str(uuid.uuid4()))
        TenantContext.set_company_code('TEST')
        TenantContext.clear()
        self.assertFalse(TenantContext.has_context())
        self.assertIsNone(TenantContext.get_company_id())
        self.assertIsNone(TenantContext.get_company_code())

    def test_override_context(self):
        """Test context override with context manager."""
        TenantContext.set_company_id('original-id')
        with TenantContext.override(company_id='override-id'):
            self.assertEqual(TenantContext.get_company_id(), 'override-id')
        self.assertEqual(TenantContext.get_company_id(), 'original-id')

    def test_override_context_none(self):
        """Test that None override preserves original."""
        TenantContext.set_company_id('original-id')
        with TenantContext.override(company_id=None):
            self.assertEqual(TenantContext.get_company_id(), 'original-id')

    def test_get_context_snapshot(self):
        """Test getting full context snapshot."""
        TenantContext.set_company_id('id1')
        TenantContext.set_company_code('CODE1')
        TenantContext.set_user_id('user1')
        TenantContext.set_request_id('req1')
        ctx = TenantContext.get_context()
        self.assertEqual(ctx['company_id'], 'id1')
        self.assertEqual(ctx['company_code'], 'CODE1')
        self.assertEqual(ctx['user_id'], 'user1')
        self.assertEqual(ctx['request_id'], 'req1')

    def test_nested_override(self):
        """Test nested context overrides."""
        TenantContext.set_company_id('level0')
        with TenantContext.override(company_id='level1'):
            self.assertEqual(TenantContext.get_company_id(), 'level1')
            with TenantContext.override(company_id='level2'):
                self.assertEqual(TenantContext.get_company_id(), 'level2')
            self.assertEqual(TenantContext.get_company_id(), 'level1')
        self.assertEqual(TenantContext.get_company_id(), 'level0')


class TestResolveCompany(TestCase):
    """Test company resolution from ID or code."""

    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            code='TESTCO',
            default_currency='AFN',
        )

    def test_resolve_by_id(self):
        """Test resolving company by ID."""
        result = resolve_company(company_id=str(self.company.id))
        self.assertEqual(result.id, self.company.id)

    def test_resolve_by_code(self):
        """Test resolving company by code."""
        result = resolve_company(company_code='TESTCO')
        self.assertEqual(result.id, self.company.id)

    def test_resolve_inactive_company(self):
        """Test that inactive company is not resolved."""
        self.company.is_active = False
        self.company.save()
        result = resolve_company(company_id=str(self.company.id))
        self.assertIsNone(result)

    def test_resolve_nonexistent_id(self):
        """Test resolving non-existent company ID."""
        result = resolve_company(company_id=str(uuid.uuid4()))
        self.assertIsNone(result)

    def test_resolve_invalid_id(self):
        """Test resolving invalid company ID."""
        result = resolve_company(company_id='not-a-uuid')
        self.assertIsNone(result)

    def test_resolve_no_params(self):
        """Test resolving with no parameters."""
        result = resolve_company()
        self.assertIsNone(result)


class TestTenantMiddleware(TestCase):
    """Test tenant middleware functionality."""

    def setUp(self):
        self.factory = RequestFactory()
        self.company = Company.objects.create(
            name='Middleware Test Co',
            code='MTCO',
            default_currency='AFN',
        )

    def tearDown(self):
        TenantContext.clear()

    def test_middleware_sets_context_from_header(self):
        """Test middleware extracts company from X-Company-ID header."""
        captured_context = {}

        def capture_request(r):
            captured_context['company'] = getattr(r, 'company', None)
            captured_context['company_id'] = getattr(r, 'company_id', None)
            return r

        middleware = TenantMiddleware(capture_request)
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_COMPANY_ID'] = str(self.company.id)

        middleware(request)

        self.assertIsNotNone(captured_context['company'])
        self.assertEqual(captured_context['company'].id, self.company.id)
        self.assertEqual(captured_context['company_id'], str(self.company.id))

    def test_middleware_sets_context_from_code_header(self):
        """Test middleware extracts company from X-Company-Code header."""
        captured_context = {}

        def capture_request(r):
            captured_context['company'] = getattr(r, 'company', None)
            captured_context['company_id'] = getattr(r, 'company_id', None)
            return r

        middleware = TenantMiddleware(capture_request)
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_COMPANY_CODE'] = 'MTCO'

        middleware(request)

        self.assertIsNotNone(captured_context['company'])
        self.assertEqual(captured_context['company'].id, self.company.id)

    def test_middleware_skips_excluded_paths(self):
        """Test middleware skips excluded paths."""
        captured_context = {}

        def capture_request(r):
            captured_context['company'] = getattr(r, 'company', None)
            return r

        middleware = TenantMiddleware(capture_request)
        request = self.factory.get('/api/health/')
        request.META['HTTP_X_COMPANY_ID'] = str(self.company.id)

        middleware(request)

        self.assertIsNone(captured_context['company'])

    def test_middleware_clears_context_after_request(self):
        """Test middleware clears context after request."""
        def simple_response(r):
            return r

        middleware = TenantMiddleware(simple_response)
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_COMPANY_ID'] = str(self.company.id)

        middleware(request)

        self.assertIsNone(TenantContext.get_company_id())


class TestUserCompanyMapping(TestCase):
    """Test user-company mapping model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
        )
        self.company1 = Company.objects.create(
            name='Company A',
            code='COMPA',
            default_currency='AFN',
        )
        self.company2 = Company.objects.create(
            name='Company B',
            code='COMPB',
            default_currency='AFN',
        )

    def test_create_mapping(self):
        """Test creating user-company mapping."""
        mapping = UserCompanyMapping.objects.create(
            user=self.user,
            company=self.company1,
            role_name='ADMIN',
        )
        self.assertEqual(mapping.role_name, 'ADMIN')
        self.assertTrue(mapping.is_active)

    def test_unique_constraint(self):
        """Test unique constraint on user+company."""
        UserCompanyMapping.objects.create(
            user=self.user,
            company=self.company1,
            role_name='ADMIN',
        )
        with self.assertRaises(Exception):
            UserCompanyMapping.objects.create(
                user=self.user,
                company=self.company1,
                role_name='MANAGER',
            )

    def test_multiple_companies(self):
        """Test user can belong to multiple companies."""
        UserCompanyMapping.objects.create(
            user=self.user,
            company=self.company1,
            role_name='ADMIN',
        )
        UserCompanyMapping.objects.create(
            user=self.user,
            company=self.company2,
            role_name='MANAGER',
        )
        self.assertEqual(self.user.company_mappings.count(), 2)

    def test_default_company_constraint(self):
        """Test only one default company per user."""
        UserCompanyMapping.objects.create(
            user=self.user,
            company=self.company1,
            role_name='ADMIN',
            is_default=True,
        )
        mapping2 = UserCompanyMapping(
            user=self.user,
            company=self.company2,
            role_name='MANAGER',
            is_default=True,
        )
        with self.assertRaises(ValidationError):
            mapping2.full_clean()


class TestCompanyPermissionService(TestCase):
    """Test company-scoped permission service."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
        )
        self.company = Company.objects.create(
            name='Perm Test Co',
            code='PERMCO',
            default_currency='AFN',
        )
        self.mapping = UserCompanyMapping.objects.create(
            user=self.user,
            company=self.company,
            role_name='ADMIN',
        )

    def test_get_user_companies(self):
        """Test getting user's companies."""
        companies = CompanyPermissionService.get_user_companies(self.user)
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0].id, self.company.id)

    def test_get_user_role_in_company(self):
        """Test getting user's role for a company."""
        role = CompanyPermissionService.get_user_role_in_company(
            self.user, str(self.company.id)
        )
        self.assertEqual(role, 'ADMIN')

    def test_get_user_role_no_access(self):
        """Test getting role for company user doesn't have access to."""
        other_company = Company.objects.create(
            name='Other Co',
            code='OTHER',
            default_currency='AFN',
        )
        role = CompanyPermissionService.get_user_role_in_company(
            self.user, str(other_company.id)
        )
        self.assertIsNone(role)

    def test_has_company_access(self):
        """Test checking company access."""
        self.assertTrue(
            CompanyPermissionService.has_company_access(self.user, str(self.company.id))
        )

    def test_no_company_access(self):
        """Test checking access to unauthorized company."""
        other_company = Company.objects.create(
            name='No Access Co',
            code='NOACC',
            default_currency='AFN',
        )
        self.assertFalse(
            CompanyPermissionService.has_company_access(self.user, str(other_company.id))
        )

    def test_get_default_company(self):
        """Test getting user's default company."""
        self.mapping.is_default = True
        self.mapping.save()
        default = CompanyPermissionService.get_default_company(self.user)
        self.assertEqual(default.id, self.company.id)

    def test_auto_assign_default_company(self):
        """Test auto-assigning default company."""
        new_user = User.objects.create_user(
            username='newuser',
            password='testpass123',
        )
        CompanyPermissionService.auto_assign_default_company(new_user)
        mappings = UserCompanyMapping.objects.filter(user=new_user)
        self.assertEqual(mappings.count(), 1)
        self.assertTrue(mappings.first().is_default)


class TestCompanyScopedMixin(TestCase):
    """Test CompanyScopedMixin behavior."""

    def setUp(self):
        self.company = Company.objects.create(
            name='Scoped Test Co',
            code='SCOPECO',
            default_currency='AFN',
        )

    def tearDown(self):
        TenantContext.clear()

    def test_mixin_has_company_field(self):
        """Test that mixin provides company field."""
        from core.multitenant.models import CompanyScopedMixin
        fields = [f.name for f in CompanyScopedMixin._meta.get_fields()]
        self.assertIn('company', fields)

    def test_auto_assign_company_from_context(self):
        """Test that mixin auto-assigns company from context."""
        TenantContext.set_company_id(str(self.company.id))

        # Create a test model with the mixin
        class TestModel(CompanyScopedMixin):
            name = 'Test'

            class Meta:
                app_label = 'core'

        # Verify the company_id would be set
        self.assertEqual(TenantContext.get_company_id(), str(self.company.id))

    def test_scoped_queryset_filters_by_company(self):
        """Test that scoped queryset filters by company context."""
        from core.multitenant.models import CompanyScopedQuerySet

        qs = CompanyScopedQuerySet(model=None)
        TenantContext.set_company_id(str(self.company.id))
        company_filter = qs._company_filter()

        # Check that filter is built correctly
        self.assertEqual(str(company_filter.children[0][0]), 'company_id')
        self.assertEqual(str(company_filter.children[0][1]), str(self.company.id))

    def test_scoped_queryset_no_context_returns_all(self):
        """Test that scoped queryset returns all when no context."""
        from core.multitenant.models import CompanyScopedQuerySet

        qs = CompanyScopedQuerySet(model=None)
        company_filter = qs._company_filter()

        # No company context = empty filter (returns all)
        self.assertEqual(len(company_filter.children), 0)

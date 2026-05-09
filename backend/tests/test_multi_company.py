"""
Multi-Company Architecture Tests
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model

from entities.models import Entity
from entities.services.company_service import (
    CompanyService, CompanyContext, MultiCompanyMiddleware
)
from accounting.models import Account, Currency


class CompanyContextTests(TestCase):
    """Test company context management."""

    def test_set_and_get_company(self):
        """Test setting and getting company context."""
        company_id = 'test-company-123'
        CompanyContext.set_company(company_id)
        
        self.assertEqual(CompanyContext.get_company(), company_id)
        
        CompanyContext.clear()
        self.assertIsNone(CompanyContext.get_company())

    def test_clear_company(self):
        """Test clearing company context."""
        CompanyContext.set_company('test-id')
        CompanyContext.clear()
        
        self.assertIsNone(CompanyContext.get_company())


class CompanyServiceTests(TestCase):
    """Test company service functionality."""

    def test_get_current_company(self):
        """Test getting current company."""
        CompanyContext.set_company('company-1')
        
        result = CompanyService.get_current_company()
        
        self.assertEqual(result, 'company-1')
        
        CompanyContext.clear()

    def test_set_current_company(self):
        """Test setting current company."""
        CompanyService.set_current_company('new-company')
        
        self.assertEqual(CompanyContext.get_company(), 'new-company')
        
        CompanyContext.clear()

    def test_filter_by_company_without_field(self):
        """Test filtering returns unmodified queryset when field doesn't exist."""
        from sales.models import SalesInvoice
        
        CompanyContext.set_company('test-company')
        
        qs = SalesInvoice.objects.all()
        filtered = CompanyService.filter_by_company(qs, 'entity_id')
        
        self.assertEqual(filtered.query, qs.query)
        
        CompanyContext.clear()

    def test_validate_company_access_superuser(self):
        """Test superuser has access to all companies."""
        User = get_user_model()
        user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        
        result = CompanyService.validate_company_access(user, 'any-company')
        
        self.assertTrue(result)


class CompanyMiddlewareTests(TestCase):
    """Test middleware functionality."""

    def test_middleware_exists(self):
        """Test middleware class exists."""
        self.assertTrue(hasattr(MultiCompanyMiddleware, '__init__'))
        self.assertTrue(hasattr(MultiCompanyMiddleware, '__call__'))


class EntityModelTests(TestCase):
    """Test Entity model for multi-company support."""

    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.first()
        if not cls.currency:
            cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)

    def test_create_entity(self):
        """Test creating a company/entity."""
        entity = Entity.objects.create(
            name='Test Company',
            code='TC001',
            entity_type='PHARMACY',
            base_currency=self.currency,
            is_default=True,
            is_active=True
        )
        
        self.assertEqual(entity.code, 'TC001')
        self.assertTrue(entity.is_active)

    def test_default_entity_only_one(self):
        """Test only one default entity allowed."""
        Entity.objects.create(
            name='Company 1',
            code='C1',
            entity_type='PHARMACY',
            is_default=True,
            is_active=True
        )
        
        with self.assertRaises(Exception):
            Entity.objects.create(
                name='Company 2',
                code='C2',
                entity_type='PHARMACY',
                is_default=True,
                is_active=True
            )

    def test_multiple_entities_allowed(self):
        """Test multiple non-default entities allowed."""
        Entity.objects.create(
            name='Entity A',
            code='EA',
            entity_type='PHARMACY',
            is_active=True
        )
        
        Entity.objects.create(
            name='Entity B',
            code='EB',
            entity_type='WAREHOUSE',
            is_active=True
        )
        
        count = Entity.objects.filter(is_active=True).count()
        self.assertEqual(count, 2)


class CompanyIsolationTests(TestCase):
    """Test data isolation between companies."""

    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.first()
        if not cls.currency:
            cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)

    def test_entity_separation(self):
        """Test companies are separate."""
        company1 = Entity.objects.create(
            name='Company One',
            code='C1',
            entity_type='PHARMACY',
            is_active=True
        )
        
        company2 = Entity.objects.create(
            name='Company Two',
            code='C2',
            entity_type='PHARMACY',
            is_active=True
        )
        
        self.assertNotEqual(company1.id, company2.id)
        
        CompanyContext.set_company(str(company1.id))
        
        self.assertEqual(CompanyContext.get_company(), str(company1.id))
        
        CompanyContext.clear()

    def test_company_isolation_with_entities(self):
        """Test that different companies can be created and accessed."""
        company1 = Entity.objects.create(
            name='Company A',
            code='CA',
            entity_type='PHARMACY',
            is_active=True
        )
        
        company2 = Entity.objects.create(
            name='Company B',
            code='CB',
            entity_type='PHARMACY',
            is_active=True
        )
        
        self.assertNotEqual(company1.id, company2.id)
        
        CompanyContext.set_company(str(company1.id))
        self.assertEqual(CompanyContext.get_company(), str(company1.id))
        CompanyContext.clear()
        
        CompanyContext.set_company(str(company2.id))
        self.assertEqual(CompanyContext.get_company(), str(company2.id))
        CompanyContext.clear()
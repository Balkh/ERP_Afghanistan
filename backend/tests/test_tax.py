"""
Tests for Tax Management module.

Covers:
- TaxCategory model
- TaxRate model
- TaxReturn model
- TaxTransaction model
- TaxCalculationService
- TaxReportingService
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
import uuid as uuid_module

from accounting.models import Currency, Account
from tax.models import (
    TaxCategory, TaxRate, TaxJurisdiction, TaxReturn, TaxTransaction
)
from tax.services.tax_calculator import TaxCalculationService
from tax.services.tax_reporting import TaxReportingService


class TestHelper:
    """Helper for test data."""

    @staticmethod
    def get_currency():
        currency, _ = Currency.objects.get_or_create(
            code='AFN',
            defaults={
                'name': 'Afghan Afghani',
                'symbol': '؋',
                'is_default': True,
                'is_active': True
            }
        )
        return currency


class TaxCategoryModelTests(TestCase):
    """Tests for TaxCategory model."""

    def test_create_tax_category(self):
        """Test creating a tax category."""
        category = TaxCategory.objects.create(
            name='Essential Medicines',
            code='ESS',
            default_rate=Decimal('2.00'),
            is_exempt=False
        )
        self.assertEqual(category.name, 'Essential Medicines')
        self.assertEqual(category.code, 'ESS')

    def test_category_str(self):
        """Test string representation."""
        category = TaxCategory.objects.create(
            name='Regular',
            code='REG',
            is_active=True
        )
        self.assertIn('REG', str(category))


class TaxRateModelTests(TestCase):
    """Tests for TaxRate model."""

    def test_create_tax_rate(self):
        """Test creating a tax rate."""
        rate = TaxRate.objects.create(
            name='Standard VAT',
            code='STD',
            rate_percentage=Decimal('10.00'),
            tax_type='STANDARD',
            effective_from=date(2025, 1, 1)
        )
        self.assertEqual(rate.rate_percentage, Decimal('10.00'))
        self.assertEqual(rate.tax_type, 'STANDARD')

    def test_rate_str(self):
        """Test string representation."""
        rate = TaxRate.objects.create(
            name='Reduced',
            code='RED',
            rate_percentage=Decimal('5.00'),
            effective_from=date(2025, 1, 1)
        )
        self.assertIn('5.00', str(rate))

    def test_rate_validation_negative(self):
        """Test validation rejects negative rate."""
        with self.assertRaises(ValidationError):
            rate = TaxRate(
                name='Invalid',
                code='INV',
                rate_percentage=Decimal('-5.00'),
                effective_from=date(2025, 1, 1)
            )
            rate.full_clean()

    def test_rate_validation_dates(self):
        """Test validation rejects invalid date range."""
        with self.assertRaises(ValidationError):
            rate = TaxRate(
                name='Invalid',
                code='INV',
                rate_percentage=Decimal('10.00'),
                effective_from=date(2025, 12, 31),
                effective_to=date(2025, 1, 1)
            )
            rate.full_clean()


class TaxReturnModelTests(TestCase):
    """Tests for TaxReturn model."""

    def setUp(self):
        TestHelper.get_currency()

    def test_create_tax_return(self):
        """Test creating a tax return."""
        tax_return = TaxReturn.objects.create(
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            status='DRAFT',
            gross_sales=Decimal('100000.00'),
            output_tax=Decimal('10000.00'),
            input_tax=Decimal('5000.00')
        )
        self.assertEqual(tax_return.status, 'DRAFT')

    def test_period_display(self):
        """Test period display property."""
        tax_return = TaxReturn.objects.create(
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            status='DRAFT'
        )
        self.assertIn('2025-01-01', tax_return.period_display)

    def test_calculate_net_tax(self):
        """Test net tax calculation."""
        tax_return = TaxReturn.objects.create(
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            status='DRAFT',
            output_tax=Decimal('10000.00'),
            input_tax=Decimal('3000.00')
        )
        tax_return.calculate_net_tax()
        self.assertEqual(tax_return.net_tax, Decimal('7000.00'))


class TaxTransactionModelTests(TestCase):
    """Tests for TaxTransaction model."""

    def setUp(self):
        TestHelper.get_currency()
        self.rate = TaxRate.objects.create(
            name='Standard',
            code='STD',
            rate_percentage=Decimal('10.00'),
            effective_from=date(2025, 1, 1)
        )

    def test_create_tax_transaction(self):
        """Test creating a tax transaction."""
        tx = TaxTransaction.objects.create(
            transaction_type='SALE',
            reference_id=uuid_module.uuid4(),
            base_amount=Decimal('10000.00'),
            tax_amount=Decimal('1000.00'),
            tax_rate=self.rate,
            transaction_date=date(2025, 2, 1)
        )
        self.assertEqual(tx.transaction_type, 'SALE')
        self.assertEqual(tx.tax_amount, Decimal('1000.00'))


class TaxCalculationServiceTests(TestCase):
    """Tests for TaxCalculationService."""

    def setUp(self):
        TestHelper.get_currency()
        self.rate = TaxRate.objects.create(
            name='Standard VAT',
            code='STD',
            rate_percentage=Decimal('10.00'),
            tax_type='STANDARD',
            effective_from=date(2020, 1, 1)
        )
        self.exempt_rate = TaxRate.objects.create(
            name='Exempt',
            code='EXM',
            rate_percentage=Decimal('0.00'),
            tax_type='EXEMPT',
            effective_from=date(2020, 1, 1)
        )

    def test_get_active_rate_for_date(self):
        """Test getting active rate for date."""
        rate = TaxCalculationService.get_active_rate_for_date(
            date(2025, 6, 15), 'STANDARD'
        )
        self.assertIsNotNone(rate)
        self.assertEqual(rate.code, 'STD')

    def test_calculate_tax_standard(self):
        """Test calculating standard tax."""
        result = TaxCalculationService.calculate_tax(
            Decimal('10000.00'),
            date(2025, 6, 15),
            'STANDARD'
        )
        self.assertEqual(result['rate'], Decimal('10.00'))
        self.assertEqual(result['tax_amount'], Decimal('1000.00'))
        self.assertEqual(result['total_amount'], Decimal('11000.00'))

    def test_calculate_tax_exempt(self):
        """Test calculating tax for exempt rate."""
        result = TaxCalculationService.calculate_tax(
            Decimal('10000.00'),
            date(2025, 6, 15),
            'EXEMPT'
        )
        self.assertEqual(result['tax_amount'], Decimal('0.00'))
        self.assertEqual(result['tax_type'], 'EXEMPT')

    def test_calculate_tax_no_rate(self):
        """Test calculating tax when no rate exists."""
        result = TaxCalculationService.calculate_tax(
            Decimal('10000.00'),
            date(2025, 6, 15),
            'NONEXISTENT'
        )
        self.assertEqual(result['tax_amount'], Decimal('0.00'))

    def test_validate_tax_configuration(self):
        """Test tax configuration validation."""
        issues = TaxCalculationService.validate_tax_configuration()
        self.assertIsInstance(issues, list)


class TaxReportingServiceTests(TestCase):
    """Tests for TaxReportingService."""

    def test_prepare_tax_return(self):
        """Test preparing a tax return."""
        tax_return = TaxReportingService.prepare_tax_return(
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31)
        )
        self.assertIsNotNone(tax_return)
        self.assertEqual(tax_return.status, 'DRAFT')

    def test_validate_return_valid(self):
        """Test validating a valid return."""
        tax_return = TaxReturn.objects.create(
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            status='DRAFT',
            output_tax=Decimal('10000.00'),
            input_tax=Decimal('3000.00'),
            net_tax=Decimal('7000.00')
        )
        issues = TaxReportingService.validate_return(tax_return)
        self.assertEqual(issues, [])

    def test_validate_return_negative_output(self):
        """Test validation catches negative output tax."""
        tax_return = TaxReturn.objects.create(
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            status='DRAFT',
            output_tax=Decimal('-1000.00'),
            input_tax=Decimal('0.00'),
            net_tax=Decimal('-1000.00')
        )
        issues = TaxReportingService.validate_return(tax_return)
        self.assertIn('Output tax cannot be negative.', issues)


class TaxJurisdictionModelTests(TestCase):
    """Tests for TaxJurisdiction model."""

    def setUp(self):
        TestHelper.get_currency()
        self.rate = TaxRate.objects.create(
            name='Standard',
            code='STD',
            rate_percentage=Decimal('10.00'),
            effective_from=date(2025, 1, 1)
        )

    def test_create_jurisdiction(self):
        """Test creating a tax jurisdiction."""
        jurisdiction = TaxJurisdiction.objects.create(
            name='Afghanistan National',
            code='AFG',
            tax_rate=self.rate
        )
        self.assertEqual(jurisdiction.name, 'Afghanistan National')
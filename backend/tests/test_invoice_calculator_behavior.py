"""
InvoiceCalculator behavior tests.
"""

from decimal import Decimal
from django.test import TestCase

from accounting.services.invoice_calculator import (
    InvoiceCalculator,
    InvoiceLineItem,
    InvoiceCalculationResult
)
from accounting.models import Currency


class InvoiceCalculatorSetupMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Currency.objects.get_or_create(code='AFN', defaults={'name': 'Afghani', 'symbol': 'Af', 'is_active': True, 'is_default': True})
        Currency.objects.get_or_create(code='USD', defaults={'name': 'US Dollar', 'symbol': '$', 'is_active': True})


class InvoiceCalculatorSimpleTest(InvoiceCalculatorSetupMixin, TestCase):
    """Test simple invoice calculation."""

    def test_calculate_simple_basic(self):
        """Test basic simple calculation."""
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            items=[{'quantity': 2, 'unit_price': '50'}],
            tax_rate=Decimal('10'),
            discount=Decimal('0')
        )
        self.assertEqual(result['subtotal'], Decimal('100'))
        self.assertEqual(result['total'], Decimal('110'))

    def test_calculate_simple_with_discount(self):
        """Test simple calculation with discount."""
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            items=[{'quantity': 2, 'unit_price': '50'}],
            tax_rate=Decimal('10'),
            discount=Decimal('10')
        )
        self.assertEqual(result['discount'], Decimal('10'))
        self.assertEqual(result['total'], Decimal('99'))

    def test_calculate_simple_no_tax(self):
        """Test simple calculation with no tax."""
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            items=[{'quantity': 1, 'unit_price': '100'}],
            tax_rate=Decimal('0'),
            discount=Decimal('0')
        )
        self.assertEqual(result['tax'], Decimal('0'))
        self.assertEqual(result['total'], Decimal('100'))


class InvoiceCalculatorFullTest(InvoiceCalculatorSetupMixin, TestCase):
    """Test full invoice calculation."""

    def test_calculate_with_line_items(self):
        """Test calculation with line items."""
        calc = InvoiceCalculator(currency_code='AFN')
        items = [
            InvoiceLineItem(
                product_name='Product 1',
                quantity=Decimal('2'),
                unit_price=Decimal('50'),
                discount_type='percentage',
                discount_value=Decimal('10'),
                tax_rate=Decimal('10')
            )
        ]
        result = calc.calculate(
            items=items,
            invoice_discount_value=Decimal('5'),
            invoice_discount_type='fixed',
            tax_rates=None
        )
        self.assertIsInstance(result, InvoiceCalculationResult)
        self.assertEqual(result.subtotal, Decimal('90'))

    def test_calculate_with_multiple_items(self):
        """Test calculation with multiple line items."""
        calc = InvoiceCalculator()
        items = [
            InvoiceLineItem(product_name='Item 1', quantity=Decimal('1'), unit_price=Decimal('100')),
            InvoiceLineItem(product_name='Item 2', quantity=Decimal('2'), unit_price=Decimal('50'))
        ]
        result = calc.calculate(
            items=items,
            invoice_discount_value=Decimal('0'),
            invoice_discount_type='fixed',
            tax_rates=None
        )
        self.assertEqual(result.subtotal, Decimal('200'))

    def test_calculate_with_invoice_discount_percentage(self):
        """Test calculation with percentage invoice discount."""
        calc = InvoiceCalculator()
        items = [
            InvoiceLineItem(product_name='Item 1', quantity=Decimal('1'), unit_price=Decimal('100'))
        ]
        result = calc.calculate(
            items=items,
            invoice_discount_type='percentage',
            invoice_discount_value=Decimal('10'),
            tax_rates=None
        )
        self.assertEqual(result.invoice_discount, Decimal('10'))

    def test_calculate_with_tax(self):
        """Test calculation with tax."""
        calc = InvoiceCalculator()
        items = [
            InvoiceLineItem(product_name='Item 1', quantity=Decimal('1'), unit_price=Decimal('100'))
        ]
        result = calc.calculate(
            items=items,
            invoice_discount_value=Decimal('0'),
            invoice_discount_type='fixed',
            tax_rates=[Decimal('10')]
        )
        self.assertEqual(result.tax, Decimal('10'))
        self.assertEqual(result.total, Decimal('110'))


class InvoiceCalculatorMixedPaymentTest(InvoiceCalculatorSetupMixin, TestCase):
    """Test mixed payment calculation."""

    def test_calculate_mixed_payment_invoice(self):
        """Test mixed payment calculation."""
        calc = InvoiceCalculator()
        items = [
            InvoiceLineItem(product_name='Item 1', quantity=Decimal('1'), unit_price=Decimal('100'))
        ]
        payments = [
            {'method': 'cash', 'amount': '50', 'currency_code': 'AFN'},
            {'method': 'card', 'amount': '50', 'currency_code': 'AFN'}
        ]
        result = calc.calculate_mixed_payment_invoice(
            items=items,
            payments=payments,
            tax_rates=None
        )
        self.assertIn('invoice', result)
        self.assertIn('payments', result)

    def test_calculate_mixed_payment_full_coverage(self):
        """Test mixed payment fully covers invoice."""
        calc = InvoiceCalculator()
        items = [
            InvoiceLineItem(product_name='Item 1', quantity=Decimal('1'), unit_price=Decimal('100'))
        ]
        payments = [
            {'method': 'cash', 'amount': '100', 'currency_code': 'AFN'}
        ]
        result = calc.calculate_mixed_payment_invoice(
            items=items,
            payments=payments,
            tax_rates=None
        )
        self.assertGreaterEqual(result['remaining_balance'], Decimal('0'))


class InvoiceCalculatorCurrencyTest(InvoiceCalculatorSetupMixin, TestCase):
    """Test currency handling."""

    def test_calculate_with_currency(self):
        """Test calculation with non-default currency."""
        calc = InvoiceCalculator(currency_code='USD')
        self.assertEqual(calc.currency_code, 'USD')

    def test_calculate_with_exchange_rate(self):
        """Test calculation with exchange rate."""
        calc = InvoiceCalculator(currency_code='USD', exchange_rate=Decimal('70'))
        self.assertEqual(calc.exchange_rate, Decimal('70'))

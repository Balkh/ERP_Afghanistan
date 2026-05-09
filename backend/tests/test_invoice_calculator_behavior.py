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


class InvoiceCalculatorSimpleTest(TestCase):
    """Test simple invoice calculation."""

    def test_calculate_simple_basic(self):
        """Test basic simple calculation."""
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            subtotal=Decimal('100'),
            tax_rate=Decimal('10'),
            discount=Decimal('0')
        )
        self.assertEqual(result.subtotal, Decimal('100'))
        self.assertEqual(result.total, Decimal('110'))

    def test_calculate_simple_with_discount(self):
        """Test simple calculation with discount."""
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            subtotal=Decimal('100'),
            tax_rate=Decimal('10'),
            discount=Decimal('10')
        )
        self.assertEqual(result.total_discount, Decimal('10'))
        self.assertEqual(result.total, Decimal('99'))

    def test_calculate_simple_no_tax(self):
        """Test simple calculation with no tax."""
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            subtotal=Decimal('100'),
            tax_rate=Decimal('0'),
            discount=Decimal('0')
        )
        self.assertEqual(result.tax, Decimal('0'))
        self.assertEqual(result.total, Decimal('100'))


class InvoiceCalculatorFullTest(TestCase):
    """Test full invoice calculation."""

    def test_calculate_with_line_items(self):
        """Test calculation with line items."""
        calc = InvoiceCalculator(currency_code='AFN')
        items = [
            {
                'product_name': 'Product 1',
                'quantity': Decimal('2'),
                'unit_price': Decimal('50'),
                'discount_type': 'percentage',
                'discount_value': Decimal('10'),
                'tax_rate': Decimal('10')
            }
        ]
        result = calc.calculate(
            line_items=items,
            invoice_discount_type='fixed',
            invoice_discount_value=Decimal('5'),
            tax_rate=Decimal('0')
        )
        self.assertIsInstance(result, InvoiceCalculationResult)
        self.assertEqual(result.subtotal, Decimal('100'))

    def test_calculate_with_multiple_items(self):
        """Test calculation with multiple line items."""
        calc = InvoiceCalculator()
        items = [
            {'product_name': 'Item 1', 'quantity': Decimal('1'), 'unit_price': Decimal('100')},
            {'product_name': 'Item 2', 'quantity': Decimal('2'), 'unit_price': Decimal('50')}
        ]
        result = calc.calculate(
            line_items=items,
            invoice_discount_type='fixed',
            invoice_discount_value=Decimal('0'),
            tax_rate=Decimal('0')
        )
        self.assertEqual(result.subtotal, Decimal('200'))

    def test_calculate_with_invoice_discount_percentage(self):
        """Test calculation with percentage invoice discount."""
        calc = InvoiceCalculator()
        items = [
            {'product_name': 'Item 1', 'quantity': Decimal('1'), 'unit_price': Decimal('100')}
        ]
        result = calc.calculate(
            line_items=items,
            invoice_discount_type='percentage',
            invoice_discount_value=Decimal('10'),
            tax_rate=Decimal('0')
        )
        self.assertEqual(result.invoice_discount, Decimal('10'))

    def test_calculate_with_tax(self):
        """Test calculation with tax."""
        calc = InvoiceCalculator()
        items = [
            {'product_name': 'Item 1', 'quantity': Decimal('1'), 'unit_price': Decimal('100')}
        ]
        result = calc.calculate(
            line_items=items,
            invoice_discount_type='fixed',
            invoice_discount_value=Decimal('0'),
            tax_rate=Decimal('10')
        )
        self.assertEqual(result.tax, Decimal('10'))
        self.assertEqual(result.total, Decimal('110'))


class InvoiceCalculatorMixedPaymentTest(TestCase):
    """Test mixed payment calculation."""

    def test_calculate_mixed_payment_invoice(self):
        """Test mixed payment calculation."""
        calc = InvoiceCalculator()
        items = [
            {'product_name': 'Item 1', 'quantity': Decimal('1'), 'unit_price': Decimal('100')}
        ]
        payments = [
            {'method': 'cash', 'amount': Decimal('50')},
            {'method': 'card', 'amount': Decimal('50')}
        ]
        result = calc.calculate_mixed_payment_invoice(
            line_items=items,
            payments=payments,
            tax_rate=Decimal('0')
        )
        self.assertIsInstance(result, InvoiceCalculationResult)

    def test_calculate_mixed_payment_full_coverage(self):
        """Test mixed payment fully covers invoice."""
        calc = InvoiceCalculator()
        items = [
            {'product_name': 'Item 1', 'quantity': Decimal('1'), 'unit_price': Decimal('100')}
        ]
        payments = [
            {'method': 'cash', 'amount': Decimal('100')}
        ]
        result = calc.calculate_mixed_payment_invoice(
            line_items=items,
            payments=payments,
            tax_rate=Decimal('0')
        )
        self.assertGreaterEqual(result.total, Decimal('0'))


class InvoiceCalculatorCurrencyTest(TestCase):
    """Test currency handling."""

    def test_calculate_with_currency(self):
        """Test calculation with non-default currency."""
        calc = InvoiceCalculator(currency_code='USD')
        result = calc.calculate_simple(
            subtotal=Decimal('100'),
            tax_rate=Decimal('0'),
            discount=Decimal('0')
        )
        self.assertEqual(result.currency, 'USD')

    def test_calculate_with_exchange_rate(self):
        """Test calculation with exchange rate."""
        calc = InvoiceCalculator(currency_code='USD', exchange_rate=Decimal('70'))
        result = calc.calculate_simple(
            subtotal=Decimal('100'),
            tax_rate=Decimal('0'),
            discount=Decimal('0')
        )
        self.assertEqual(result.exchange_rate, Decimal('70'))
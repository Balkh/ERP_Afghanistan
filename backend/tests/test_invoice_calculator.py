"""
Comprehensive tests for Invoice Calculator service.

Covers:
- Line item calculations
- Item-level discounts
- Invoice-level discounts
- Tax calculations (percentage, compound)
- Currency conversion on invoice
- Simple calculation
- Mixed payment invoice
- Warnings on conversion failure
"""
from datetime import date
from decimal import Decimal

from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import CurrencyFactory
from accounting.models import ExchangeRate
from accounting.services.invoice_calculator import (
    InvoiceCalculator,
    InvoiceLineItem,
    InvoiceCalculationResult,
)


class InvoiceResultDefaultsTests(BaseTestCase):

    def test_result_defaults(self):
        result = InvoiceCalculationResult()
        self.assertEqual(result.subtotal, Decimal('0'))
        self.assertEqual(result.total, Decimal('0'))
        self.assertEqual(result.currency, 'AFN')
        self.assertEqual(result.amount_in_base, Decimal('0'))
        self.assertEqual(result.exchange_rate, Decimal('1'))


class CalculateTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011500'),
            effective_date=self.today,
            is_active=True,
        )
        ExchangeRate.objects.create(
            from_currency=self.currency_usd,
            to_currency=self.currency,
            rate=Decimal('86.956522'),
            effective_date=self.today,
            is_active=True,
        )

    def test_basic_invoice_no_discount_no_tax(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('2'), unit_price=Decimal('50')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items)
        self.assertEqual(result.subtotal, Decimal('100'))
        self.assertEqual(result.total_discount, Decimal('0'))
        self.assertEqual(result.tax, Decimal('0'))
        self.assertEqual(result.total, Decimal('100'))

    def test_multiple_items(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('2'), unit_price=Decimal('50')),
            InvoiceLineItem(product_name='Drug B', quantity=Decimal('1'), unit_price=Decimal('200')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items)
        self.assertEqual(result.subtotal, Decimal('300'))

    def test_item_fixed_discount(self):
        items = [
            InvoiceLineItem(
                product_name='Drug A',
                quantity=Decimal('2'),
                unit_price=Decimal('50'),
                discount_type='fixed',
                discount_value=Decimal('5'),
            ),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items)
        self.assertEqual(result.subtotal, Decimal('90'))

    def test_item_percentage_discount(self):
        items = [
            InvoiceLineItem(
                product_name='Drug A',
                quantity=Decimal('2'),
                unit_price=Decimal('50'),
                discount_type='percentage',
                discount_value=Decimal('10'),
            ),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items)
        self.assertEqual(result.subtotal, Decimal('90'))

    def test_invoice_fixed_discount(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('2'), unit_price=Decimal('50')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items, invoice_discount_value=Decimal('10'), invoice_discount_type='fixed')
        self.assertEqual(result.invoice_discount, Decimal('10'))
        self.assertEqual(result.taxable_amount, Decimal('90'))
        self.assertEqual(result.total, Decimal('90'))

    def test_invoice_percentage_discount(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('2'), unit_price=Decimal('50')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items, invoice_discount_value=Decimal('10'), invoice_discount_type='percentage')
        self.assertEqual(result.invoice_discount, Decimal('10.00'))

    def test_invoice_discount_exceeds_subtotal_raises(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('2'), unit_price=Decimal('50')),
        ]
        calc = InvoiceCalculator()
        with self.assertRaises(ValueError):
            calc.calculate(items, invoice_discount_value=Decimal('150'), invoice_discount_type='fixed')

    def test_percentage_tax(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items, tax_rates=[Decimal('10')])
        self.assertEqual(result.tax, Decimal('10.00'))
        self.assertEqual(result.total, Decimal('110.00'))

    def test_multiple_tax_rates(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items, tax_rates=[Decimal('10'), Decimal('5')])
        self.assertEqual(result.tax, Decimal('15.00'))

    def test_compound_tax(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items, tax_rates=[Decimal('10'), Decimal('5')], use_compound_tax=True)
        self.assertEqual(result.tax, Decimal('15.50'))

    def test_taxable_amount_after_discount(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(
            items,
            invoice_discount_value=Decimal('20'),
            invoice_discount_type='fixed',
            tax_rates=[Decimal('10')],
        )
        self.assertEqual(result.taxable_amount, Decimal('80'))
        self.assertEqual(result.tax, Decimal('8.00'))

    def test_total_discount_includes_item_and_invoice(self):
        items = [
            InvoiceLineItem(
                product_name='Drug A',
                quantity=Decimal('1'),
                unit_price=Decimal('100'),
                discount_type='fixed',
                discount_value=Decimal('10'),
            ),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(
            items,
            invoice_discount_value=Decimal('5'),
            invoice_discount_type='fixed',
        )
        self.assertEqual(result.item_discounts, Decimal('10'))
        self.assertEqual(result.invoice_discount, Decimal('5'))
        self.assertEqual(result.total_discount, Decimal('15'))

    def test_line_items_detail(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('2'), unit_price=Decimal('50')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate(items)
        self.assertEqual(len(result.line_items), 1)
        line = result.line_items[0]
        self.assertEqual(line['product_name'], 'Drug A')
        self.assertEqual(line['line_total'], Decimal('100'))

    def test_currency_code_on_result(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        calc = InvoiceCalculator(currency_code='AFN')
        result = calc.calculate(items)
        self.assertEqual(result.currency, 'AFN')


class CalculateWithCurrencyTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011500'),
            effective_date=self.today,
            is_active=True,
        )
        ExchangeRate.objects.create(
            from_currency=self.currency_usd,
            to_currency=self.currency,
            rate=Decimal('86.956522'),
            effective_date=self.today,
            is_active=True,
        )

    def test_same_currency_no_conversion(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        calc = InvoiceCalculator(currency_code='AFN')
        result = calc.calculate(items)
        self.assertEqual(result.amount_in_base, Decimal('100'))
        self.assertEqual(result.exchange_rate, Decimal('1'))

    def test_different_currency_converts(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        calc = InvoiceCalculator(currency_code='USD')
        result = calc.calculate(items)
        self.assertEqual(result.currency, 'USD')
        self.assertEqual(result.amount_in_base, Decimal('8695.65'))

    def test_conversion_failure_produces_warning(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('100')),
        ]
        eur = CurrencyFactory.create(code='EUR', name='Euro', symbol='\u20ac')
        calc = InvoiceCalculator(currency_code='EUR')
        result = calc.calculate(items)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn('Currency conversion failed', result.warnings[0])
        self.assertEqual(result.amount_in_base, Decimal('100'))


class CalculateSimpleTests(BaseTestCase):

    def test_basic_simple(self):
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            items=[{'quantity': 2, 'unit_price': 50}],
            discount=Decimal('10'),
            tax_rate=Decimal('10'),
        )
        self.assertEqual(result['subtotal'], Decimal('100'))
        self.assertEqual(result['after_discount'], Decimal('90'))
        self.assertEqual(result['tax'], Decimal('9.00'))
        self.assertEqual(result['total'], Decimal('99.00'))
        self.assertEqual(result['item_count'], 1)

    def test_zero_items(self):
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            items=[],
        )
        self.assertEqual(result['subtotal'], Decimal('0'))
        self.assertEqual(result['total'], Decimal('0'))
        self.assertEqual(result['item_count'], 0)

    def test_no_discount_no_tax(self):
        calc = InvoiceCalculator()
        result = calc.calculate_simple(
            items=[{'quantity': 1, 'unit_price': 50}],
        )
        self.assertEqual(result['subtotal'], Decimal('50'))
        self.assertEqual(result['discount'], Decimal('0'))
        self.assertEqual(result['tax'], Decimal('0'))
        self.assertEqual(result['total'], Decimal('50'))


class MixedPaymentInvoiceTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        ExchangeRate.objects.create(
            from_currency=self.currency_usd,
            to_currency=self.currency,
            rate=Decimal('86.956522'),
            effective_date=self.today,
            is_active=True,
        )

    def test_fully_paid(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('1000')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate_mixed_payment_invoice(
            items,
            payments=[
                {'amount': 1000, 'currency_code': 'AFN', 'payment_method': 'cash'},
            ],
        )
        self.assertTrue(result['is_fully_paid'])
        self.assertEqual(result['remaining_balance'], Decimal('0'))

    def test_partial_payment(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('1000')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate_mixed_payment_invoice(
            items,
            payments=[
                {'amount': 500, 'currency_code': 'AFN', 'payment_method': 'cash'},
            ],
        )
        self.assertFalse(result['is_fully_paid'])
        self.assertEqual(result['remaining_balance'], Decimal('500'))

    def test_overpayment(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('1000')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate_mixed_payment_invoice(
            items,
            payments=[
                {'amount': 1500, 'currency_code': 'AFN', 'payment_method': 'cash'},
            ],
        )
        self.assertEqual(result['remaining_balance'], Decimal('0'))
        self.assertEqual(result['overpayment'], Decimal('500'))

    def test_mixed_currency_payments(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('1000')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate_mixed_payment_invoice(
            items,
            payments=[
                {'amount': 500, 'currency_code': 'AFN', 'payment_method': 'cash'},
                {'amount': 10, 'currency_code': 'USD', 'payment_method': 'bank', 'exchange_rate': 86.956522},
            ],
        )
        self.assertTrue(result['is_fully_paid'])

    def test_returns_invoice_totals(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('1000')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate_mixed_payment_invoice(items, payments=[])
        self.assertIn('subtotal', result['invoice'])
        self.assertIn('total', result['invoice'])
        self.assertIn('tax', result['invoice'])

    def test_with_discount_and_tax(self):
        items = [
            InvoiceLineItem(product_name='Drug A', quantity=Decimal('1'), unit_price=Decimal('1000')),
        ]
        calc = InvoiceCalculator()
        result = calc.calculate_mixed_payment_invoice(
            items,
            payments=[{'amount': 1050, 'currency_code': 'AFN', 'payment_method': 'cash'}],
            invoice_discount_value=Decimal('100'),
            invoice_discount_type='fixed',
            tax_rates=[Decimal('10')],
        )
        self.assertTrue(result['is_fully_paid'])

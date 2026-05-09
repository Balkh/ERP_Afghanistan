"""
Comprehensive tests for Tax Calculator service.

Covers:
- Percentage tax calculation
- Fixed tax calculation
- Compound tax calculation
- Multi-tax calculation
- Item-level tax calculation
- Afghanistan Business Tax
- Validation error handling
"""
from decimal import Decimal

from tests.base import BaseTestCase
from accounting.services.tax_calculator import (
    TaxCalculator,
    TaxType,
    TaxResult,
)


class TaxResultTests(BaseTestCase):

    def test_tax_result_defaults(self):
        result = TaxResult(
            tax_amount=Decimal('10.00'),
            tax_type=TaxType.PERCENTAGE,
            tax_rate=Decimal('10'),
            tax_description='10% tax on 100',
        )
        self.assertEqual(result.tax_amount, Decimal('10.00'))
        self.assertFalse(result.is_compound)


class PercentageTaxTests(BaseTestCase):

    def test_basic_percentage_tax(self):
        result = TaxCalculator.calculate_percentage_tax(
            Decimal('10'), Decimal('100')
        )
        self.assertEqual(result.tax_amount, Decimal('10.00'))
        self.assertEqual(result.tax_type, TaxType.PERCENTAGE)
        self.assertEqual(result.tax_rate, Decimal('10'))

    def test_percentage_tax_rounding(self):
        result = TaxCalculator.calculate_percentage_tax(
            Decimal('7.5'), Decimal('100.55')
        )
        expected = (Decimal('100.55') * Decimal('7.5') / Decimal('100')).quantize(
            Decimal('0.01')
        )
        self.assertEqual(result.tax_amount, expected)

    def test_zero_tax_rate(self):
        result = TaxCalculator.calculate_percentage_tax(
            Decimal('0'), Decimal('100')
        )
        self.assertEqual(result.tax_amount, Decimal('0.00'))

    def test_zero_taxable_amount(self):
        result = TaxCalculator.calculate_percentage_tax(
            Decimal('10'), Decimal('0')
        )
        self.assertEqual(result.tax_amount, Decimal('0.00'))

    def test_compound_flag(self):
        result = TaxCalculator.calculate_percentage_tax(
            Decimal('10'), Decimal('100'), is_compound=True
        )
        self.assertTrue(result.is_compound)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError) as ctx:
            TaxCalculator.calculate_percentage_tax(Decimal('-5'), Decimal('100'))
        self.assertIn('negative', str(ctx.exception).lower())

    def test_negative_amount_raises(self):
        with self.assertRaises(ValueError) as ctx:
            TaxCalculator.calculate_percentage_tax(Decimal('10'), Decimal('-100'))
        self.assertIn('negative', str(ctx.exception).lower())

    def test_description_format(self):
        result = TaxCalculator.calculate_percentage_tax(
            Decimal('5'), Decimal('200')
        )
        self.assertIn('5', result.tax_description)
        self.assertIn('200', result.tax_description)


class FixedTaxTests(BaseTestCase):

    def test_basic_fixed_tax(self):
        result = TaxCalculator.calculate_fixed_tax(Decimal('25.00'))
        self.assertEqual(result.tax_amount, Decimal('25.00'))
        self.assertEqual(result.tax_type, TaxType.FIXED)
        self.assertEqual(result.tax_rate, Decimal('0'))

    def test_zero_fixed_tax(self):
        result = TaxCalculator.calculate_fixed_tax(Decimal('0'))
        self.assertEqual(result.tax_amount, Decimal('0.00'))

    def test_negative_amount_raises(self):
        with self.assertRaises(ValueError) as ctx:
            TaxCalculator.calculate_fixed_tax(Decimal('-10'))
        self.assertIn('negative', str(ctx.exception).lower())


class CompoundTaxTests(BaseTestCase):

    def test_single_rate(self):
        result = TaxCalculator.calculate_compound_tax(
            Decimal('100'), [Decimal('10')]
        )
        self.assertEqual(result.tax_amount, Decimal('10.00'))
        self.assertTrue(result.is_compound)

    def test_two_rates(self):
        result = TaxCalculator.calculate_compound_tax(
            Decimal('100'), [Decimal('10'), Decimal('5')]
        )
        expected = (Decimal('100') * Decimal('10') / Decimal('100')).quantize(Decimal('0.01'))
        second = ((Decimal('100') + expected) * Decimal('5') / Decimal('100')).quantize(Decimal('0.01'))
        self.assertEqual(result.tax_amount, expected + second)

    def test_empty_rates(self):
        result = TaxCalculator.calculate_compound_tax(Decimal('100'), [])
        self.assertEqual(result.tax_amount, Decimal('0'))

    def test_three_rates(self):
        result = TaxCalculator.calculate_compound_tax(
            Decimal('1000'), [Decimal('10'), Decimal('5'), Decimal('2')]
        )
        step1 = (Decimal('1000') * Decimal('10') / Decimal('100')).quantize(Decimal('0.01'))
        amt2 = Decimal('1000') + step1
        step2 = (amt2 * Decimal('5') / Decimal('100')).quantize(Decimal('0.01'))
        amt3 = amt2 + step2
        step3 = (amt3 * Decimal('2') / Decimal('100')).quantize(Decimal('0.01'))
        self.assertEqual(result.tax_amount, step1 + step2 + step3)

    def test_description_contains_all_rates(self):
        result = TaxCalculator.calculate_compound_tax(
            Decimal('100'), [Decimal('10'), Decimal('5')]
        )
        self.assertIn('10', result.tax_description)
        self.assertIn('5', result.tax_description)
        self.assertIn('Compound', result.tax_description)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_compound_tax(Decimal('100'), [Decimal('-5')])

    def test_negative_base_raises(self):
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_compound_tax(Decimal('-100'), [Decimal('10')])

    def test_combined_rate_is_sum(self):
        result = TaxCalculator.calculate_compound_tax(
            Decimal('100'), [Decimal('10'), Decimal('5')]
        )
        self.assertEqual(result.tax_rate, Decimal('15'))


class ItemLevelTaxTests(BaseTestCase):

    def test_single_item_percentage(self):
        items = [{'quantity': 2, 'unit_price': 50, 'tax_type': 'percentage', 'tax_rate': 10}]
        total_tax, updated = TaxCalculator.calculate_item_level_taxes(items)
        self.assertEqual(total_tax, Decimal('10.00'))
        self.assertEqual(updated[0]['line_total'], Decimal('100'))
        self.assertEqual(updated[0]['item_tax'], Decimal('10.00'))
        self.assertEqual(updated[0]['line_total_after_tax'], Decimal('110.00'))

    def test_single_item_exempt(self):
        items = [{'quantity': 2, 'unit_price': 50, 'tax_type': 'exempt'}]
        total_tax, updated = TaxCalculator.calculate_item_level_taxes(items)
        self.assertEqual(total_tax, Decimal('0'))
        self.assertEqual(updated[0]['item_tax'], Decimal('0'))

    def test_single_item_fixed(self):
        items = [{'quantity': 3, 'unit_price': 10, 'tax_type': 'fixed', 'tax_amount': Decimal('2')}]
        total_tax, updated = TaxCalculator.calculate_item_level_taxes(items)
        self.assertEqual(total_tax, Decimal('6.00'))

    def test_default_tax_rate_applied(self):
        items = [{'quantity': 1, 'unit_price': 100, 'tax_type': 'percentage'}]
        total_tax, updated = TaxCalculator.calculate_item_level_taxes(
            items, default_tax_rate=Decimal('15')
        )
        self.assertEqual(total_tax, Decimal('15.00'))

    def test_multiple_items_mixed_types(self):
        items = [
            {'quantity': 1, 'unit_price': 100, 'tax_type': 'percentage', 'tax_rate': 10},
            {'quantity': 2, 'unit_price': 50, 'tax_type': 'exempt'},
            {'quantity': 1, 'unit_price': 200, 'tax_type': 'percentage', 'tax_rate': 5},
        ]
        total_tax, updated = TaxCalculator.calculate_item_level_taxes(items)
        expected = Decimal('10.00') + Decimal('0') + Decimal('10.00')
        self.assertEqual(total_tax, expected)
        self.assertEqual(len(updated), 3)

    def test_empty_items(self):
        total_tax, updated = TaxCalculator.calculate_item_level_taxes([])
        self.assertEqual(total_tax, Decimal('0'))
        self.assertEqual(len(updated), 0)


class MultiTaxTests(BaseTestCase):

    def test_single_percentage_tax(self):
        total, results = TaxCalculator.calculate_multi_tax(
            Decimal('100'), [{'type': 'percentage', 'rate': 10}]
        )
        self.assertEqual(total, Decimal('10.00'))
        self.assertEqual(len(results), 1)

    def test_single_fixed_tax(self):
        total, results = TaxCalculator.calculate_multi_tax(
            Decimal('100'), [{'type': 'fixed', 'amount': 25}]
        )
        self.assertEqual(total, Decimal('25.00'))

    def test_compound_type(self):
        total, results = TaxCalculator.calculate_multi_tax(
            Decimal('100'), [{'type': 'compound', 'rates': [10, 5]}]
        )
        self.assertTrue(results[0].is_compound)

    def test_multiple_taxes(self):
        taxes = [
            {'type': 'percentage', 'rate': 10},
            {'type': 'fixed', 'amount': 5},
        ]
        total, results = TaxCalculator.calculate_multi_tax(Decimal('100'), taxes)
        self.assertEqual(total, Decimal('15.00'))
        self.assertEqual(len(results), 2)

    def test_negative_amount_raises(self):
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_multi_tax(Decimal('-100'), [{'type': 'percentage', 'rate': 10}])

    def test_default_type_is_percentage(self):
        total, results = TaxCalculator.calculate_multi_tax(
            Decimal('100'), [{'rate': 5}]
        )
        self.assertEqual(results[0].tax_type, TaxType.PERCENTAGE)


class AfghanistanBusinessTaxTests(BaseTestCase):

    def test_default_brt_rate(self):
        result = TaxCalculator.calculate_afghanistan_business_tax(Decimal('1000'))
        self.assertEqual(result.tax_amount, Decimal('40.00'))

    def test_brt_on_zero(self):
        result = TaxCalculator.calculate_afghanistan_business_tax(Decimal('0'))
        self.assertEqual(result.tax_amount, Decimal('0.00'))

    def test_brt_rounding(self):
        result = TaxCalculator.calculate_afghanistan_business_tax(Decimal('123.45'))
        expected = (Decimal('123.45') * Decimal('4') / Decimal('100')).quantize(Decimal('0.01'))
        self.assertEqual(result.tax_amount, expected)

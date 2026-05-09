"""
TaxCalculator behavior tests.
"""

from decimal import Decimal
from django.test import TestCase

from accounting.services.tax_calculator import TaxCalculator, TaxType


class TaxCalculatorPercentageTest(TestCase):
    """Test percentage tax calculation."""

    def test_calculate_percentage_tax_basic(self):
        """Test basic percentage tax calculation."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('10'),
            taxable_amount=Decimal('100')
        )
        self.assertEqual(result.tax_amount, Decimal('10.00'))
        self.assertEqual(result.tax_type, TaxType.PERCENTAGE)
        self.assertEqual(result.tax_rate, Decimal('10'))

    def test_calculate_percentage_tax_zero_rate(self):
        """Test percentage tax with zero rate."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('0'),
            taxable_amount=Decimal('100')
        )
        self.assertEqual(result.tax_amount, Decimal('0.00'))

    def test_calculate_percentage_tax_decimal_amount(self):
        """Test percentage tax with decimal amount."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('8'),
            taxable_amount=Decimal('125.50')
        )
        self.assertEqual(result.tax_amount, Decimal('10.04'))

    def test_calculate_percentage_tax_negative_rate_raises(self):
        """Test negative tax rate raises error."""
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_percentage_tax(
                rate=Decimal('-5'),
                taxable_amount=Decimal('100')
            )

    def test_calculate_percentage_tax_negative_amount_raises(self):
        """Test negative taxable amount raises error."""
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_percentage_tax(
                rate=Decimal('10'),
                taxable_amount=Decimal('-50')
            )


class TaxCalculatorFixedTest(TestCase):
    """Test fixed tax calculation."""

    def test_calculate_fixed_tax_basic(self):
        """Test basic fixed tax calculation."""
        result = TaxCalculator.calculate_fixed_tax(
            amount=Decimal('15')
        )
        self.assertEqual(result.tax_amount, Decimal('15.00'))
        self.assertEqual(result.tax_type, TaxType.FIXED)

    def test_calculate_fixed_tax_zero(self):
        """Test fixed tax with zero amount."""
        result = TaxCalculator.calculate_fixed_tax(
            amount=Decimal('0')
        )
        self.assertEqual(result.tax_amount, Decimal('0.00'))

    def test_calculate_fixed_tax_negative_raises(self):
        """Test negative fixed tax raises error."""
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_fixed_tax(amount=Decimal('-5'))


class TaxCalculatorCompoundTest(TestCase):
    """Test compound tax calculation."""

    def test_calculate_compound_tax_single_rate(self):
        """Test compound tax with single rate."""
        result = TaxCalculator.calculate_compound_tax(
            base_amount=Decimal('100'),
            tax_rates=[Decimal('10')]
        )
        self.assertEqual(result.tax_amount, Decimal('10.00'))
        self.assertTrue(result.is_compound)

    def test_calculate_compound_tax_multiple_rates(self):
        """Test compound tax with multiple rates."""
        result = TaxCalculator.calculate_compound_tax(
            base_amount=Decimal('100'),
            tax_rates=[Decimal('10'), Decimal('5')]
        )
        self.assertEqual(result.tax_amount, Decimal('15.50'))
        self.assertTrue(result.is_compound)


class TaxCalculatorItemLevelTest(TestCase):
    """Test item-level tax calculation."""

    def test_calculate_item_level_taxes_percentage(self):
        """Test item-level tax with percentage tax."""
        items = [
            {'quantity': Decimal('2'), 'unit_price': Decimal('50'), 'tax_rate': Decimal('10')}
        ]
        total_tax, updated_items = TaxCalculator.calculate_item_level_taxes(items)
        self.assertEqual(total_tax, Decimal('10.00'))

    def test_calculate_item_level_taxes_exempt(self):
        """Test item-level tax with exempt items."""
        items = [
            {'quantity': Decimal('2'), 'unit_price': Decimal('50'), 'tax_type': 'exempt'}
        ]
        total_tax, updated_items = TaxCalculator.calculate_item_level_taxes(items)
        self.assertEqual(total_tax, Decimal('0.00'))


class TaxCalculatorMultiTaxTest(TestCase):
    """Test multi tax calculation."""

    def test_calculate_multi_tax(self):
        """Test multi tax calculation."""
        taxes = [
            {'rate': Decimal('10'), 'type': 'percentage'},
            {'rate': Decimal('5'), 'type': 'percentage'}
        ]
        total_tax, results = TaxCalculator.calculate_multi_tax(
            taxable_amount=Decimal('100'),
            taxes=taxes
        )
        self.assertEqual(total_tax, Decimal('15.00'))
        self.assertEqual(len(results), 2)
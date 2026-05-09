"""
DiscountCalculator behavior tests.
"""

from decimal import Decimal
from django.test import TestCase

from accounting.services.discount_calculator import DiscountCalculator, DiscountType


class DiscountCalculatorFixedTest(TestCase):
    """Test fixed discount calculation."""

    def test_calculate_fixed_discount_basic(self):
        """Test basic fixed discount calculation."""
        result = DiscountCalculator.calculate_fixed_discount(
            discount_value=Decimal('15')
        )
        self.assertEqual(result.discount_amount, Decimal('15.00'))
        self.assertEqual(result.discount_type, DiscountType.FIXED)

    def test_calculate_fixed_discount_with_subtotal(self):
        """Test fixed discount with subtotal validation."""
        result = DiscountCalculator.calculate_fixed_discount(
            discount_value=Decimal('10'),
            subtotal=Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('10.00'))

    def test_calculate_fixed_discount_exceeds_subtotal_raises(self):
        """Test fixed discount exceeding subtotal raises error."""
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_fixed_discount(
                discount_value=Decimal('150'),
                subtotal=Decimal('100')
            )

    def test_calculate_fixed_discount_negative_raises(self):
        """Test negative fixed discount raises error."""
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_fixed_discount(discount_value=Decimal('-5'))


class DiscountCalculatorPercentageTest(TestCase):
    """Test percentage discount calculation."""

    def test_calculate_percentage_discount_basic(self):
        """Test basic percentage discount."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('10'),
            subtotal=Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('10.00'))
        self.assertEqual(result.discount_type, DiscountType.PERCENTAGE)

    def test_calculate_percentage_discount_zero(self):
        """Test percentage discount with zero rate."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('0'),
            subtotal=Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('0.00'))

    def test_calculate_percentage_discount_100_percent(self):
        """Test 100% discount."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('100'),
            subtotal=Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('100.00'))

    def test_calculate_percentage_discount_decimal_subtotal(self):
        """Test percentage discount with decimal subtotal."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('8'),
            subtotal=Decimal('125.50')
        )
        self.assertEqual(result.discount_amount, Decimal('10.04'))


class DiscountCalculatorTieredTest(TestCase):
    """Test tiered discount calculation."""

    def test_calculate_tiered_discount(self):
        """Test tiered discount based on subtotal."""
        tiers = [(Decimal('100'), Decimal('5')), (Decimal('500'), Decimal('10'))]
        result = DiscountCalculator.calculate_tiered_discount(
            subtotal=Decimal('600'),
            tiers=tiers
        )
        self.assertEqual(result.discount_amount, Decimal('60.00'))

    def test_calculate_tiered_discount_no_tiers_match(self):
        """Test tiered discount when no tiers match."""
        tiers = [(Decimal('100'), Decimal('5'))]
        result = DiscountCalculator.calculate_tiered_discount(
            subtotal=Decimal('50'),
            tiers=tiers
        )
        self.assertEqual(result.discount_amount, Decimal('0.00'))


class DiscountCalculatorItemLevelTest(TestCase):
    """Test item-level discount calculation."""

    def test_calculate_item_level_discounts_percentage(self):
        """Test item-level discount with percentage."""
        items = [
            {'quantity': Decimal('2'), 'unit_price': Decimal('50'), 'discount_type': 'percentage', 'discount_value': Decimal('10')}
        ]
        total_discount, updated_items = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertIsInstance(total_discount, Decimal)

    def test_calculate_item_level_discounts_fixed(self):
        """Test item-level discount with fixed amount."""
        items = [
            {'quantity': Decimal('2'), 'unit_price': Decimal('50'), 'discount_type': 'fixed', 'discount_value': Decimal('5')}
        ]
        total_discount, updated_items = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertIsInstance(total_discount, Decimal)

    def test_calculate_item_level_discounts_no_discount(self):
        """Test item-level discount with no discount."""
        items = [
            {'quantity': Decimal('2'), 'unit_price': Decimal('50')}
        ]
        total_discount, updated_items = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertEqual(total_discount, Decimal('0.00'))
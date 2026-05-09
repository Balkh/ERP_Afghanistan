"""
Comprehensive tests for Discount Calculator service.

Covers:
- Fixed discount calculation
- Percentage discount calculation
- Tiered discount calculation
- Volume discount
- Item-level discount calculation
- Validation error handling
"""
from decimal import Decimal

from tests.base import BaseTestCase
from accounting.services.discount_calculator import (
    DiscountCalculator,
    DiscountType,
    DiscountResult,
)


class DiscountResultTests(BaseTestCase):

    def test_discount_result_creation(self):
        result = DiscountResult(
            discount_amount=Decimal('10.00'),
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('10'),
            discount_description='10% discount on 100',
        )
        self.assertEqual(result.discount_amount, Decimal('10.00'))


class FixedDiscountTests(BaseTestCase):

    def test_basic_fixed_discount(self):
        result = DiscountCalculator.calculate_fixed_discount(Decimal('25'))
        self.assertEqual(result.discount_amount, Decimal('25.00'))
        self.assertEqual(result.discount_type, DiscountType.FIXED)

    def test_fixed_discount_with_subtotal_validation(self):
        result = DiscountCalculator.calculate_fixed_discount(
            Decimal('50'), subtotal=Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('50.00'))

    def test_fixed_discount_equals_subtotal(self):
        result = DiscountCalculator.calculate_fixed_discount(
            Decimal('100'), subtotal=Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('100.00'))

    def test_fixed_discount_exceeds_subtotal_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DiscountCalculator.calculate_fixed_discount(
                Decimal('150'), subtotal=Decimal('100')
            )
        self.assertIn('cannot exceed subtotal', str(ctx.exception).lower())

    def test_negative_discount_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DiscountCalculator.calculate_fixed_discount(Decimal('-10'))
        self.assertIn('negative', str(ctx.exception).lower())

    def test_zero_discount(self):
        result = DiscountCalculator.calculate_fixed_discount(Decimal('0'))
        self.assertEqual(result.discount_amount, Decimal('0.00'))


class PercentageDiscountTests(BaseTestCase):

    def test_basic_percentage_discount(self):
        result = DiscountCalculator.calculate_percentage_discount(
            Decimal('10'), Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('10.00'))
        self.assertEqual(result.discount_type, DiscountType.PERCENTAGE)

    def test_percentage_discount_rounding(self):
        result = DiscountCalculator.calculate_percentage_discount(
            Decimal('7.5'), Decimal('100.55')
        )
        expected = (Decimal('100.55') * Decimal('7.5') / Decimal('100')).quantize(
            Decimal('0.01')
        )
        self.assertEqual(result.discount_amount, expected)

    def test_zero_percent(self):
        result = DiscountCalculator.calculate_percentage_discount(
            Decimal('0'), Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('0.00'))

    def test_hundred_percent(self):
        result = DiscountCalculator.calculate_percentage_discount(
            Decimal('100'), Decimal('100')
        )
        self.assertEqual(result.discount_amount, Decimal('100.00'))

    def test_percentage_over_100_raises(self):
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_percentage_discount(
                Decimal('101'), Decimal('100')
            )

    def test_negative_percentage_raises(self):
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_percentage_discount(
                Decimal('-5'), Decimal('100')
            )

    def test_negative_subtotal_raises(self):
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_percentage_discount(
                Decimal('10'), Decimal('-100')
            )

    def test_description_format(self):
        result = DiscountCalculator.calculate_percentage_discount(
            Decimal('15'), Decimal('200')
        )
        self.assertIn('15', result.discount_description)
        self.assertIn('200', result.discount_description)


class TieredDiscountTests(BaseTestCase):

    def test_below_all_tiers(self):
        tiers = [(1000, 5), (5000, 10), (10000, 15)]
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('500'), tiers
        )
        self.assertEqual(result.discount_amount, Decimal('0.00'))
        self.assertEqual(result.discount_value, Decimal('0'))

    def test_first_tier(self):
        tiers = [(1000, 5), (5000, 10), (10000, 15)]
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('2000'), tiers
        )
        self.assertEqual(result.discount_amount, Decimal('100.00'))
        self.assertEqual(result.discount_value, Decimal('5'))

    def test_second_tier(self):
        tiers = [(1000, 5), (5000, 10), (10000, 15)]
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('7000'), tiers
        )
        self.assertEqual(result.discount_amount, Decimal('700.00'))
        self.assertEqual(result.discount_value, Decimal('10'))

    def test_highest_tier(self):
        tiers = [(1000, 5), (5000, 10), (10000, 15)]
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('15000'), tiers
        )
        self.assertEqual(result.discount_amount, Decimal('2250.00'))
        self.assertEqual(result.discount_value, Decimal('15'))

    def test_exact_tier_boundary(self):
        tiers = [(1000, 5), (5000, 10)]
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('1000'), tiers
        )
        self.assertEqual(result.discount_value, Decimal('5'))

    def test_unsorted_tiers(self):
        tiers = [(10000, 15), (1000, 5), (5000, 10)]
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('7000'), tiers
        )
        self.assertEqual(result.discount_value, Decimal('10'))

    def test_single_tier(self):
        tiers = [(500, 10)]
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('1000'), tiers
        )
        self.assertEqual(result.discount_amount, Decimal('100.00'))

    def test_empty_tiers(self):
        result = DiscountCalculator.calculate_tiered_discount(
            Decimal('1000'), []
        )
        self.assertEqual(result.discount_amount, Decimal('0.00'))

    def test_negative_subtotal_raises(self):
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_tiered_discount(
                Decimal('-100'), [(1000, 5)]
            )


class VolumeDiscountTests(BaseTestCase):

    def test_volume_discount_delegates_to_tiered(self):
        thresholds = [(1000, 5), (5000, 10)]
        result = DiscountCalculator.apply_volume_discount(
            Decimal('3000'), thresholds
        )
        self.assertEqual(result.discount_amount, Decimal('150.00'))
        self.assertEqual(result.discount_type, DiscountType.TIERED)


class ItemLevelDiscountTests(BaseTestCase):

    def test_single_item_fixed_discount(self):
        items = [{'quantity': 2, 'unit_price': 50, 'discount_type': 'fixed', 'discount_value': 5}]
        total_discount, updated = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertEqual(total_discount, Decimal('10.00'))
        self.assertEqual(updated[0]['line_total'], Decimal('100'))
        self.assertEqual(updated[0]['item_discount'], Decimal('10.00'))
        self.assertEqual(updated[0]['line_total_after_discount'], Decimal('90.00'))

    def test_single_item_percentage_discount(self):
        items = [{'quantity': 2, 'unit_price': 50, 'discount_type': 'percentage', 'discount_value': 10}]
        total_discount, updated = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertEqual(total_discount, Decimal('10.00'))
        self.assertEqual(updated[0]['item_discount'], Decimal('10.00'))

    def test_zero_discount_value(self):
        items = [{'quantity': 1, 'unit_price': 100, 'discount_type': 'fixed', 'discount_value': 0}]
        total_discount, updated = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertEqual(total_discount, Decimal('0'))

    def test_multiple_items(self):
        items = [
            {'quantity': 2, 'unit_price': 50, 'discount_type': 'fixed', 'discount_value': 5},
            {'quantity': 1, 'unit_price': 200, 'discount_type': 'percentage', 'discount_value': 10},
        ]
        total_discount, updated = DiscountCalculator.calculate_item_level_discounts(items)
        expected = Decimal('10.00') + Decimal('20.00')
        self.assertEqual(total_discount, expected)
        self.assertEqual(len(updated), 2)

    def test_default_discount_type_fixed(self):
        items = [{'quantity': 1, 'unit_price': 100}]
        total_discount, updated = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertEqual(total_discount, Decimal('0'))

    def test_empty_items(self):
        total_discount, updated = DiscountCalculator.calculate_item_level_discounts([])
        self.assertEqual(total_discount, Decimal('0'))
        self.assertEqual(len(updated), 0)

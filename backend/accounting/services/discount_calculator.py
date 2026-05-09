from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class DiscountType(str, Enum):
    FIXED = 'fixed'
    PERCENTAGE = 'percentage'
    TIERED = 'tiered'


@dataclass
class DiscountResult:
    discount_amount: Decimal
    discount_type: str
    discount_value: Decimal
    discount_description: str


class DiscountCalculator:
    """
    Handles all discount calculations for invoices.
    Supports fixed, percentage, and tiered discounts.
    """

    @staticmethod
    def calculate_fixed_discount(
        discount_value: Decimal,
        subtotal: Optional[Decimal] = None
    ) -> DiscountResult:
        """
        Calculate a fixed amount discount.
        
        Args:
            discount_value: Fixed discount amount
            subtotal: Optional subtotal to validate discount doesn't exceed it
            
        Returns:
            DiscountResult with calculated discount
        """
        if discount_value < 0:
            raise ValueError('Fixed discount cannot be negative.')
        
        if subtotal is not None and discount_value > subtotal:
            raise ValueError('Fixed discount cannot exceed subtotal.')
        
        return DiscountResult(
            discount_amount=discount_value,
            discount_type=DiscountType.FIXED,
            discount_value=discount_value,
            discount_description=f'Fixed discount: {discount_value}'
        )

    @staticmethod
    def calculate_percentage_discount(
        percentage: Decimal,
        subtotal: Decimal
    ) -> DiscountResult:
        """
        Calculate a percentage-based discount.
        
        Args:
            percentage: Discount percentage (0-100)
            subtotal: Amount to apply discount to
            
        Returns:
            DiscountResult with calculated discount
        """
        if percentage < 0 or percentage > 100:
            raise ValueError('Discount percentage must be between 0 and 100.')
        
        if subtotal < 0:
            raise ValueError('Subtotal cannot be negative.')
        
        discount_amount = (subtotal * percentage / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return DiscountResult(
            discount_amount=discount_amount,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=percentage,
            discount_description=f'{percentage}% discount on {subtotal}'
        )

    @staticmethod
    def calculate_tiered_discount(
        subtotal: Decimal,
        tiers: list[tuple[Decimal, Decimal]]
    ) -> DiscountResult:
        """
        Calculate a tiered discount based on subtotal ranges.
        
        Args:
            subtotal: Amount to evaluate
            tiers: List of (threshold, percentage) tuples
                   Example: [(1000, 5), (5000, 10), (10000, 15)]
                   Means: 5% for >1000, 10% for >5000, 15% for >10000
        
        Returns:
            DiscountResult with calculated discount
        """
        if subtotal < 0:
            raise ValueError('Subtotal cannot be negative.')
        
        applicable_percentage = Decimal('0')
        
        # Sort tiers by threshold and find applicable tier
        sorted_tiers = sorted(tiers, key=lambda x: x[0])
        for threshold, percentage in sorted_tiers:
            if subtotal >= threshold:
                applicable_percentage = percentage
            else:
                break
        
        discount_amount = (subtotal * applicable_percentage / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return DiscountResult(
            discount_amount=discount_amount,
            discount_type=DiscountType.TIERED,
            discount_value=applicable_percentage,
            discount_description=f'Tiered discount: {applicable_percentage}% for subtotal {subtotal}'
        )

    @staticmethod
    def calculate_item_level_discounts(
        items: list[dict]
    ) -> tuple[Decimal, list[dict]]:
        """
        Calculate discounts at the item level.
        
        Args:
            items: List of item dicts with keys:
                   - quantity
                   - unit_price
                   - discount_type ('fixed' or 'percentage')
                   - discount_value
        
        Returns:
            Tuple of (total_discount_amount, updated_items)
        """
        total_discount = Decimal('0')
        updated_items = []
        
        for item in items:
            quantity = Decimal(str(item['quantity']))
            unit_price = Decimal(str(item['unit_price']))
            line_total = quantity * unit_price
            
            discount_type = item.get('discount_type', 'fixed')
            discount_value = Decimal(str(item.get('discount_value', 0)))
            
            item_discount = Decimal('0')
            if discount_type == 'fixed':
                item_discount = discount_value * quantity
            elif discount_type == 'percentage':
                item_discount = (line_total * discount_value / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            
            total_discount += item_discount
            
            updated_item = item.copy()
            updated_item['line_total'] = line_total
            updated_item['item_discount'] = item_discount
            updated_item['line_total_after_discount'] = line_total - item_discount
            updated_items.append(updated_item)
        
        return total_discount, updated_items

    @staticmethod
    def apply_volume_discount(
        subtotal: Decimal,
        volume_thresholds: list[tuple[int, Decimal]]
    ) -> DiscountResult:
        """
        Apply volume-based discount based on invoice subtotal.
        
        Args:
            subtotal: Invoice subtotal
            volume_thresholds: List of (minimum_quantity, percentage) tuples
        
        Returns:
            DiscountResult with calculated discount
        """
        return DiscountCalculator.calculate_tiered_discount(subtotal, volume_thresholds)

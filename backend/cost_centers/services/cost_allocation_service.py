from decimal import Decimal
from datetime import date
from typing import List, Optional, Dict
from django.db import models
from django.db.models import Sum

from cost_centers.models import CostCenter, CostAllocation, CostAllocationLine
from accounting.models import JournalEntryLine, Account


class CostAllocationService:
    """
    Service for cost allocation calculations.
    """

    @staticmethod
    def calculate_allocation(
        source_amount: Decimal,
        allocation: CostAllocation
    ) -> Dict[CostCenter, Decimal]:
        """
        Calculate allocated amounts for a source cost center.

        Args:
            source_amount: Total amount to allocate
            allocation: CostAllocation rule

        Returns:
            Dictionary of cost center to allocated amount
        """
        if not allocation.is_active:
            return {}

        if allocation.allocation_method == 'PERCENTAGE':
            return CostAllocationService._allocate_by_percentage(
                source_amount, allocation
            )
        elif allocation.allocation_method == 'EQUAL':
            return CostAllocationService._allocate_equal(
                source_amount, allocation
            )
        return {}

    @staticmethod
    def _allocate_by_percentage(
        source_amount: Decimal,
        allocation: CostAllocation
    ) -> Dict[CostCenter, Decimal]:
        """Allocate by percentage."""
        result = {}
        for line in allocation.lines.all():
            allocated = (source_amount * line.percentage / Decimal('100')).quantize(
                Decimal('0.01')
            )
            result[line.target_cost_center] = allocated
        return result

    @staticmethod
    def _allocate_equal(
        source_amount: Decimal,
        allocation: CostAllocation
    ) -> Dict[CostCenter, Decimal]:
        """Allocate equally."""
        lines = list(allocation.lines.all())
        if not lines:
            return {}
        equal_amount = (source_amount / len(lines)).quantize(Decimal('0.01'))
        return {line.target_cost_center: equal_amount for line in lines}

    @staticmethod
    def validate_allocation(allocation: CostAllocation) -> List[str]:
        """Validate allocation percentages sum to 100%."""
        if allocation.allocation_method != 'PERCENTAGE':
            return []

        total = sum(
            line.percentage for line in allocation.lines.all()
        )
        if total != Decimal('100.00'):
            return [f'Percentages sum to {total}%, must be 100%']
        return []

    @staticmethod
    def get_cost_center_balance(
        cost_center: CostCenter,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Calculate total costs for a cost center in a period."""
        from accounting.models import JournalEntry

        lines = JournalEntryLine.objects.filter(
            account__in=Account.objects.filter(
                account_type='EXPENSE'
            )
        )

        if start_date:
            lines = lines.filter(entry__entry_date__gte=start_date)
        if end_date:
            lines = lines.filter(entry__entry_date__lte=end_date)

        return lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
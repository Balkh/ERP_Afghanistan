"""
Cost Center Analytics Engine.
Read-only analytical layer for cost center accounting.
Does NOT modify transactional data.
"""
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, List
from django.db.models import Sum, Q, F
from django.db.models.functions import TruncMonth

from accounting.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Product
from sales.models import SalesInvoice


class CostCenter:
    """
    Analytical cost center representation.
    Read-only mapping of accounts/departments to cost centers.
    """
    COST_CENTERS = {
        'CC_PHARMACY': {
            'name': 'Pharmacy Operations',
            'accounts': ['5000', '5001', '5002'],
            'departments': ['PHARMACY'],
        },
        'CC_WHOLESALE': {
            'name': 'Wholesale Distribution',
            'accounts': ['5100', '5101'],
            'departments': ['WHOLESALE'],
        },
        'CC_ADMIN': {
            'name': 'Administration',
            'accounts': ['6000', '6001', '6002', '6003'],
            'departments': ['ADMIN'],
        },
        'CC_WAREHOUSE': {
            'name': 'Warehouse Operations',
            'accounts': ['6100', '6101'],
            'departments': ['WAREHOUSE'],
        },
        'CC_SALES': {
            'name': 'Sales & Marketing',
            'accounts': ['6200', '6201'],
            'departments': ['SALES'],
        },
    }


class CostAllocationEngine:
    """
    Distributes expenses across cost centers based on rules.
    Read-only - computes allocations without writing to DB.
    """

    @staticmethod
    def allocate_by_percentage(
        total_amount: Decimal,
        allocations: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """
        Allocate amount by percentage rules.

        Args:
            total_amount: Total amount to distribute
            allocations: {cost_center_code: percentage}

        Returns:
            {cost_center_code: allocated_amount}
        """
        result = {}
        for cc_code, percentage in allocations.items():
            allocated = total_amount * (percentage / Decimal('100'))
            result[cc_code] = allocated.quantize(Decimal('0.01'))
        return result

    @staticmethod
    def allocate_by_quantity(
        total_amount: Decimal,
        allocations: Dict[str, int]
    ) -> Dict[str, Decimal]:
        """
        Allocate amount by quantity rules.

        Args:
            total_amount: Total amount to distribute
            allocations: {cost_center_code: quantity}

        Returns:
            {cost_center_code: allocated_amount}
        """
        total_qty = sum(allocations.values())
        if total_qty == 0:
            return {cc: Decimal('0') for cc in allocations}

        result = {}
        for cc_code, qty in allocations.items():
            ratio = Decimal(qty) / Decimal(total_qty)
            allocated = total_amount * ratio
            result[cc_code] = allocated.quantize(Decimal('0.01'))
        return result

    @staticmethod
    def allocate_fixed_split(
        total_amount: Decimal,
        allocations: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """
        Allocate using fixed amounts (remainder goes to largest).

        Args:
            total_amount: Total amount
            allocations: {cost_center_code: fixed_amount}

        Returns:
            {cost_center_code: allocated_amount}
        """
        total_fixed = sum(allocations.values())
        result = dict(allocations)

        # Distribute remainder proportionally
        remainder = total_amount - total_fixed
        if remainder > 0:
            for cc_code in allocations:
                ratio = allocations[cc_code] / total_fixed if total_fixed > 0 else Decimal('1') / len(allocations)
                result[cc_code] += (remainder * ratio).quantize(Decimal('0.01'))

        return result


class CostAggregator:
    """
    Aggregates costs by cost center, product, and department.
    Read-only analytical queries only.
    """

    @staticmethod
    def get_cost_center_expenses(
        cost_center: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get total expenses for a cost center.

        Args:
            cost_center: Cost center code (e.g., 'CC_ADMIN')
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with total expenses and breakdown
        """
        cc_config = CostCenter.COST_CENTERS.get(cost_center)
        if not cc_config:
            return {'error': f'Unknown cost center: {cost_center}'}

        account_codes = cc_config['accounts']
        base_filter = Q(
            entry__is_posted=True,
            entry__is_active=True,
            account__code__in=account_codes
        )

        if start_date:
            base_filter &= Q(entry__entry_date__gte=start_date)
        if end_date:
            base_filter &= Q(entry__entry_date__lte=end_date)

        expenses = JournalEntryLine.objects.filter(base_filter).values(
            'account__code', 'account__name'
        ).annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        ).order_by('account__code')

        total = Decimal('0')
        for item in expenses:
            debit = item['total_debit'] or Decimal('0')
            credit = item['total_credit'] or Decimal('0')
            total += debit - credit

        return {
            'cost_center': cost_center,
            'cost_center_name': cc_config['name'],
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'total_expenses': total.quantize(Decimal('0.01')),
            'breakdown': [
                {
                    'account_code': item['account__code'],
                    'account_name': item['account__name'],
                    'amount': ((item['total_debit'] or Decimal('0')) - (item['total_credit'] or Decimal('0'))).quantize(Decimal('0.01')),
                }
                for item in expenses
            ]
        }

    @staticmethod
    def get_all_cost_centers_summary(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """Get summary for all cost centers."""
        results = []
        for cc_code in CostCenter.COST_CENTERS:
            summary = CostAggregator.get_cost_center_expenses(cc_code, start_date, end_date)
            if 'error' not in summary:
                results.append(summary)
        return results

    @staticmethod
    def get_product_cost(product_id: str) -> Dict:
        """
        Calculate total cost per product from inventory + purchases.
        Read-only aggregation.
        """
        from purchases.models import PurchaseItem
        from inventory.models import StockMovement

        purchase_cost = PurchaseItem.objects.filter(
            product_id=product_id
        ).aggregate(total=Sum(F('unit_price') * F('quantity')))['total'] or Decimal('0')

        stock_movements = StockMovement.objects.filter(
            product_id=product_id,
            movement_type='IN'
        ).aggregate(total=Sum('quantity'))

        quantity_in = stock_movements['total'] or 0

        return {
            'product_id': product_id,
            'total_purchase_cost': purchase_cost.quantize(Decimal('0.01')),
            'total_quantity_received': quantity_in,
            'average_unit_cost': (purchase_cost / quantity_in).quantize(Decimal('0.01')) if quantity_in > 0 else Decimal('0'),
        }

    @staticmethod
    def get_monthly_cost_trend(
        cost_center: str,
        months: int = 12
    ) -> List[Dict]:
        """Get monthly cost trend for a cost center."""
        cc_config = CostCenter.COST_CENTERS.get(cost_center)
        if not cc_config:
            return []

        expenses = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            entry__is_active=True,
            account__code__in=cc_config['accounts']
        ).annotate(
            month=TruncMonth('entry__entry_date')
        ).values('month').annotate(
            total=Sum('debit') - Sum('credit')
        ).order_by('month')[:months]

        return [
            {
                'month': item['month'],
                'total_expenses': (item['total'] or Decimal('0')).quantize(Decimal('0.01')),
            }
            for item in expenses
        ]

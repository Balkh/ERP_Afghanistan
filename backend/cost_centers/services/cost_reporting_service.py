from decimal import Decimal
from datetime import date
from typing import Optional, List
from django.db.models import Sum, Count

from accounting.models import JournalEntryLine
from cost_centers.models import CostCenter, CostTransaction


class CostReportingService:
    """
    Service for cost center reporting.
    """

    @staticmethod
    def get_cost_center_summary(
        cost_center: CostCenter,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """Get summary for a cost center."""
        transactions = CostTransaction.objects.filter(cost_center=cost_center)

        if start_date:
            transactions = transactions.filter(transaction_date__gte=start_date)
        if end_date:
            transactions = transactions.filter(transaction_date__lte=end_date)

        total_spent = transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        transaction_count = transactions.count()

        budget = cost_center.budget
        remaining = budget - total_spent
        utilization_pct = (total_spent / budget * 100) if budget > 0 else Decimal('0.00')

        return {
            'cost_center_code': cost_center.code,
            'cost_center_name': cost_center.name,
            'type': cost_center.cost_center_type,
            'budget': budget,
            'total_spent': total_spent,
            'remaining': remaining,
            'utilization_percentage': utilization_pct,
            'transaction_count': transaction_count,
        }

    @staticmethod
    def get_all_centers_summary(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[dict]:
        """Get summary for all active cost centers."""
        centers = CostCenter.objects.filter(is_active=True)
        return [
            CostReportingService.get_cost_center_summary(cc, start_date, end_date)
            for cc in centers
        ]

    @staticmethod
    def get_cost_by_type_report(start_date: date, end_date: date) -> dict:
        """Get cost breakdown by cost center type."""
        centers = CostCenter.objects.filter(is_active=True)
        by_type = {}

        for cc in centers:
            txns = CostTransaction.objects.filter(
                cost_center=cc,
                transaction_date__gte=start_date,
                transaction_date__lte=end_date
            )
            total = txns.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            if cc.cost_center_type not in by_type:
                by_type[cc.cost_center_type] = {
                    'type': cc.cost_center_type,
                    'total_cost': Decimal('0.00'),
                    'center_count': 0,
                    'centers': []
                }

            by_type[cc.cost_center_type]['total_cost'] += total
            by_type[cc.cost_center_type]['center_count'] += 1

        return {
            'period_start': start_date,
            'period_end': end_date,
            'by_type': list(by_type.values()),
            'total_cost': sum(t['total_cost'] for t in by_type.values())
        }

    @staticmethod
    def get_top_cost_centers(
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> List[dict]:
        """Get top cost centers by spending."""
        centers = CostCenter.objects.filter(is_active=True)
        results = []

        for cc in centers:
            txns = CostTransaction.objects.filter(
                cost_center=cc,
                transaction_date__gte=start_date,
                transaction_date__lte=end_date
            )
            total = txns.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            results.append({
                'cost_center': cc.name,
                'code': cc.code,
                'type': cc.cost_center_type,
                'total_spent': total
            })

        results.sort(key=lambda x: x['total_spent'], reverse=True)
        return results[:limit]

    @staticmethod
    def get_budget_variance_report() -> List[dict]:
        """Get budget variance for all cost centers."""
        centers = CostCenter.objects.filter(is_active=True, budget__gt=0)
        results = []

        for cc in centers:
            txns = CostTransaction.objects.filter(cost_center=cc)
            total = txns.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            variance = cc.budget - total
            variance_pct = (variance / cc.budget * 100) if cc.budget > 0 else Decimal('0.00')

            results.append({
                'code': cc.code,
                'name': cc.name,
                'budget': cc.budget,
                'actual': total,
                'variance': variance,
                'variance_percentage': variance_pct,
                'status': 'OVER' if variance < 0 else 'UNDER'
            })

        return results
from decimal import Decimal
from datetime import date
from typing import Optional, List
from django.db.models import Sum

from accounting.models import Account
from budgeting.models import Budget, BudgetLine


class BudgetReportingService:
    """
    Service for budget vs actual reporting.
    Generates variance reports integrated with account structure.
    """

    @staticmethod
    def get_budget_variance_report(
        budget: Budget,
        period: Optional[str] = None
    ) -> dict:
        """
        Generate budget vs actual variance report.

        Args:
            budget: Budget to report on
            period: Optional period filter

        Returns:
            Dictionary with variance report data
        """
        lines = budget.lines.all()
        if period:
            lines = lines.filter(period=period)

        rows = []
        total_budgeted = Decimal('0.00')
        total_actual = Decimal('0.00')

        for line in lines.select_related('account'):
            variance = line.budgeted_amount - line.actual_amount
            variance_pct = (
                (variance / line.budgeted_amount * 100)
                if line.budgeted_amount != 0 else Decimal('0.00')
            )

            rows.append({
                'account_code': line.account.code,
                'account_name': line.account.name,
                'account_type': line.account.account_type,
                'period': line.period,
                'budgeted': line.budgeted_amount,
                'actual': line.actual_amount,
                'variance': variance,
                'variance_percentage': variance_pct,
                'status': 'OVER_BUDGET' if variance < 0 else 'UNDER_BUDGET'
            })

            total_budgeted += line.budgeted_amount
            total_actual += line.actual_amount

        total_variance = total_budgeted - total_actual
        total_variance_pct = (
            (total_variance / total_budgeted * 100)
            if total_budgeted != 0 else Decimal('0.00')
        )

        return {
            'budget_name': budget.name,
            'fiscal_year': budget.fiscal_year,
            'status': budget.status,
            'total_budgeted': total_budgeted,
            'total_actual': total_actual,
            'total_variance': total_variance,
            'total_variance_percentage': total_variance_pct,
            'lines': rows,
            'over_budget_count': sum(1 for r in rows if r['status'] == 'OVER_BUDGET'),
            'under_budget_count': sum(1 for r in rows if r['status'] == 'UNDER_BUDGET'),
        }

    @staticmethod
    def get_account_variance_summary(
        account: Account,
        fiscal_year: int
    ) -> dict:
        """
        Get variance summary for a specific account across all budgets.

        Args:
            account: Account to summarize
            fiscal_year: Fiscal year

        Returns:
            Dictionary with account variance data
        """
        lines = BudgetLine.objects.filter(
            account=account,
            budget__fiscal_year=fiscal_year,
            budget__status='APPROVED'
        )

        total_budgeted = lines.aggregate(
            total=Sum('budgeted_amount')
        )['total'] or Decimal('0.00')

        total_actual = lines.aggregate(
            total=Sum('actual_amount')
        )['total'] or Decimal('0.00')

        variance = total_budgeted - total_actual

        return {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'fiscal_year': fiscal_year,
            'total_budgeted': total_budgeted,
            'total_actual': total_actual,
            'variance': variance,
            'variance_percentage': (
                (variance / total_budgeted * 100)
                if total_budgeted != 0 else Decimal('0.00')
            ),
            'budget_count': lines.count(),
        }

    @staticmethod
    def get_department_variance(
        budgets: List[Budget],
        period: Optional[str] = None
    ) -> dict:
        """
        Get department-wise variance (grouped by account category).

        Args:
            budgets: List of budgets
            period: Optional period filter

        Returns:
            Dictionary with department-wise variance
        """
        lines = BudgetLine.objects.filter(budget__in=budgets)
        if period:
            lines = lines.filter(period=period)

        by_category = {}

        for line in lines.select_related('account', 'budget'):
            category = line.account.account_category or 'OTHER'
            if category not in by_category:
                by_category[category] = {
                    'category': category,
                    'budgeted': Decimal('0.00'),
                    'actual': Decimal('0.00'),
                    'accounts': set()
                }

            by_category[category]['budgeted'] += line.budgeted_amount
            by_category[category]['actual'] += line.actual_amount
            by_category[category]['accounts'].add(line.account.code)

        results = []
        for cat_data in by_category.values():
            variance = cat_data['budgeted'] - cat_data['actual']
            results.append({
                'category': cat_data['category'],
                'budgeted': cat_data['budgeted'],
                'actual': cat_data['actual'],
                'variance': variance,
                'variance_percentage': (
                    (variance / cat_data['budgeted'] * 100)
                    if cat_data['budgeted'] != 0 else Decimal('0.00')
                ),
                'account_count': len(cat_data['accounts'])
            })

        return {
            'by_category': sorted(results, key=lambda x: abs(x['variance']), reverse=True),
            'total_budgeted': sum(r['budgeted'] for r in results),
            'total_actual': sum(r['actual'] for r in results),
        }

    @staticmethod
    def get_budget_summary(budget: Budget) -> dict:
        """
        Get quick budget summary.

        Args:
            budget: Budget to summarize

        Returns:
            Summary dictionary
        """
        lines = budget.lines.all()

        total_budgeted = lines.aggregate(
            total=Sum('budgeted_amount')
        )['total'] or Decimal('0.00')

        total_actual = lines.aggregate(
            total=Sum('actual_amount')
        )['total'] or Decimal('0.00')

        variance = total_budgeted - total_actual
        variance_pct = (
            (variance / total_budgeted * 100)
            if total_budgeted != 0 else Decimal('0.00')
        )

        return {
            'id': str(budget.id),
            'name': budget.name,
            'fiscal_year': budget.fiscal_year,
            'period_type': budget.period_type,
            'status': budget.status,
            'total_budgeted': total_budgeted,
            'total_actual': total_actual,
            'variance': variance,
            'variance_percentage': variance_pct,
            'line_count': lines.count(),
            'approved': budget.status == 'APPROVED'
        }
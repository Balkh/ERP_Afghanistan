"""
Production Optimization Service
Budget vs Actual, Variance Analysis, and Production KPIs.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, List, Dict
from django.db.models import Sum, Q, Count, Avg, F
from django.db.models.functions import TruncMonth
from accounting.models import Account, JournalEntry, JournalEntryLine
from budgeting.models import Budget, BudgetLine
from sales.models import SalesInvoice
from purchases.models import PurchaseInvoice


class VarianceAnalysis:
    """
    Budget vs Actual Variance Analysis.
    """

    @staticmethod
    def get_budget_variance(budget_id: str) -> dict:
        """
        Get detailed variance analysis for a budget.
        
        Returns:
            - Budget vs Actual by account
            - Variance amount and percentage
            - Favorable/Unfavorable indicators
        """
        try:
            budget = Budget.objects.get(id=budget_id)
        except (Budget.DoesNotExist, ValueError, Exception):
            return {'error': 'Budget not found'}

        lines = BudgetLine.objects.filter(budget=budget).select_related('account')

        result_lines = []
        total_budgeted = Decimal('0')
        total_actual = Decimal('0')

        for line in lines:
            variance = line.budgeted_amount - line.actual_amount
            variance_pct = (variance / line.budgeted_amount * 100) if line.budgeted_amount > 0 else Decimal('0')

            favorable = (line.account.account_type in ['EXPENSE', 'COGS'] and variance >= 0) or \
                       (line.account.account_type in ['REVENUE', 'INCOME'] and variance <= 0)

            result_lines.append({
                'account_code': line.account.code,
                'account_name': line.account.name,
                'account_type': line.account.account_type,
                'budgeted': line.budgeted_amount,
                'actual': line.actual_amount,
                'variance': variance,
                'variance_percent': round(variance_pct, 2),
                'favorable': favorable,
                'period': line.period
            })

            total_budgeted += line.budgeted_amount
            total_actual += line.actual_amount

        total_variance = total_budgeted - total_actual
        total_variance_pct = (total_variance / total_budgeted * 100) if total_budgeted > 0 else Decimal('0')

        return {
            'budget_name': budget.name,
            'fiscal_year': budget.fiscal_year,
            'period': budget.period_type,
            'total_budgeted': total_budgeted,
            'total_actual': total_actual,
            'total_variance': total_variance,
            'total_variance_percent': round(total_variance_pct, 2),
            'lines': result_lines
        }

    @staticmethod
    def get_department_variance(fiscal_year: int) -> dict:
        """
        Aggregate variance by department/cost center.
        """
        budgets = Budget.objects.filter(
            fiscal_year=fiscal_year,
            status='APPROVED'
        )

        result = []
        total_budgeted = Decimal('0')
        total_actual = Decimal('0')

        for budget in budgets:
            result.append({
                'department': budget.name,
                'budgeted': budget.total_budgeted,
                'actual': budget.total_actual,
                'variance': budget.variance,
                'variance_percent': round(budget.variance_percentage, 2)
            })
            total_budgeted += budget.total_budgeted
            total_actual += budget.total_actual

        return {
            'fiscal_year': fiscal_year,
            'departments': result,
            'total_budgeted': total_budgeted,
            'total_actual': total_actual,
            'total_variance': total_budgeted - total_actual
        }


class ProductionKPI:
    """
    Production-related KPIs.
    """

    @staticmethod
    def get_production_efficiency(days: int = 30) -> dict:
        """
        Calculate production efficiency metrics.
        
        Returns:
            - Revenue per day
            - Purchase cost per day
            - Gross margin
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        revenue = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        purchases = PurchaseInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        gross_profit = revenue - purchases

        return {
            'period_days': days,
            'total_revenue': revenue,
            'total_purchases': purchases,
            'gross_profit': gross_profit,
            'gross_margin_percent': round((gross_profit / revenue * 100) if revenue > 0 else 0, 2),
            'avg_revenue_per_day': round(revenue / days, 2),
            'avg_cost_per_day': round(purchases / days, 2)
        }

    @staticmethod
    def get_working_capital_metrics(as_of_date: Optional[date] = None) -> dict:
        """
        Working capital efficiency metrics.
        """
        if as_of_date is None:
            as_of_date = date.today()

        ar = SalesInvoice.objects.filter(
            payment_status__in=['UNPAID', 'PARTIAL']
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or Decimal('0')

        ap = PurchaseInvoice.objects.filter(
            payment_status__in=['UNPAID', 'PARTIAL']
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or Decimal('0')

        return {
            'as_of_date': as_of_date,
            'accounts_receivable': ar,
            'accounts_payable': ap,
            'net_working_capital': ar - ap,
            'working_capital_ratio': round((ar / ap) if ap > 0 else 0, 2)
        }

    @staticmethod
    def get_turnover_ratios(days: int = 90) -> dict:
        """
        Calculate inventory and receivables turnover.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        cogs = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
            account__account_category='COST_OF_GOODS_SOLD'
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        sales = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        avg_inventory = cogs / 2 if cogs > 0 else Decimal('1')

        inventory_turnover = cogs / avg_inventory if avg_inventory > 0 else Decimal('0')
        days_inventory = days / inventory_turnover if inventory_turnover > 0 else Decimal('0')

        avg_receivables = sales / 2 if sales > 0 else Decimal('1')
        receivables_turnover = sales / avg_receivables if avg_receivables > 0 else Decimal('0')
        days_sales_outstanding = days / receivables_turnover if receivables_turnover > 0 else Decimal('0')

        return {
            'period_days': days,
            'cogs': cogs,
            'sales': sales,
            'inventory_turnover': round(inventory_turnover, 2),
            'days_in_inventory': round(days_inventory, 1),
            'receivables_turnover': round(receivables_turnover, 2),
            'days_sales_outstanding': round(days_sales_outstanding, 1)
        }


class BudgetForecast:
    """
    Budget forecasting and projections.
    """

    @staticmethod
    def forecast_revenue(fiscal_year: int, months_ahead: int = 3) -> dict:
        """
        Forecast revenue based on historical trends.
        """
        current_date = date.today()
        start_of_year = date(fiscal_year, 1, 1)

        historical = SalesInvoice.objects.filter(
            invoice_date__gte=start_of_year,
            invoice_date__lt=current_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).annotate(
            month=TruncMonth('invoice_date')
        ).values('month').annotate(
            total=Sum('total_amount')
        ).order_by('month')

        monthly_avg = sum(item['total'] for item in historical) / max(len(list(historical)), 1)

        last_month = SalesInvoice.objects.filter(
            invoice_date__year=current_date.year,
            invoice_date__month=current_date.month,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        growth_rate = Decimal('1.05')
        forecasts = []
        for i in range(1, months_ahead + 1):
            forecast_date = current_date + timedelta(days=30 * i)
            forecast_amount = last_month * (growth_rate ** i)

            forecasts.append({
                'month': forecast_date.strftime('%Y-%m'),
                'forecasted_revenue': round(forecast_amount, 2)
            })

        return {
            'fiscal_year': fiscal_year,
            'monthly_average': round(monthly_avg, 2),
            'last_month_actual': last_month,
            'forecasts': forecasts
        }

    @staticmethod
    def forecast_expenses(fiscal_year: int, months_ahead: int = 3) -> dict:
        """
        Forecast expenses based on historical trends.
        """
        current_date = date.today()
        start_of_year = date(fiscal_year, 1, 1)

        historical = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            entry__entry_date__gte=start_of_year,
            entry__entry_date__lt=current_date,
            account__account_category__in=['OPERATING_EXPENSE', 'COST_OF_GOODS_SOLD']
        ).annotate(
            month=TruncMonth('entry__entry_date')
        ).values('month').annotate(
            total=Sum('debit')
        ).order_by('month')

        monthly_avg = sum(item['total'] for item in historical) / max(len(list(historical)), 1)

        forecasts = []
        for i in range(1, months_ahead + 1):
            forecast_date = current_date + timedelta(days=30 * i)
            forecast_amount = monthly_avg

            forecasts.append({
                'month': forecast_date.strftime('%Y-%m'),
                'forecasted_expenses': round(forecast_amount, 2)
            })

        return {
            'fiscal_year': fiscal_year,
            'monthly_average': round(monthly_avg, 2),
            'forecasts': forecasts
        }

    @staticmethod
    def get_budget_utilization(fiscal_year: int) -> dict:
        """
        Track budget utilization by month.
        """
        budgets = Budget.objects.filter(
            fiscal_year=fiscal_year,
            status='APPROVED'
        )

        monthly_data = []
        total_budgeted = Decimal('0')
        total_actual = Decimal('0')

        for budget in budgets:
            monthly_data.append({
                'budget_name': budget.name,
                'budgeted': budget.total_budgeted,
                'actual': budget.total_actual,
                'utilization_percent': round((budget.total_actual / budget.total_budgeted * 100) if budget.total_budgeted > 0 else 0, 2)
            })
            total_budgeted += budget.total_budgeted
            total_actual += budget.total_actual

        return {
            'fiscal_year': fiscal_year,
            'budgets': monthly_data,
            'total_budgeted': total_budgeted,
            'total_actual': total_actual,
            'overall_utilization': round((total_actual / total_budgeted * 100) if total_budgeted > 0 else 0, 2)
        }
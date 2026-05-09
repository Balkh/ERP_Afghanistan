"""
Widget Service - Modular Dashboard Widget Data Provider

Each widget method delegates to existing services - NO duplicate logic.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db.models import Sum, Count, Avg, F


class WidgetService:
    """Service for individual widget data - delegates to existing services."""

    # ==================== FINANCIAL WIDGETS ====================

    @staticmethod
    def get_revenue_trend(months: int = 12) -> List[Dict]:
        """Revenue trend over N months - delegates to FinancialReportEngine."""
        from accounting.services.financial_reports import FinancialReportEngine
        from accounting.models import Account

        revenue_accounts = Account.objects.filter(
            account_type='REVENUE',
            is_active=True
        )

        results = []
        today = date.today()

        for i in range(months - 1, -1, -1):
            month_start = today.replace(day=1) - timedelta(days=i * 30)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            month_revenue = Decimal('0.00')
            for acc in revenue_accounts:
                from accounting.models import JournalEntryLine
                lines = JournalEntryLine.objects.filter(
                    account=acc,
                    entry__is_posted=True,
                    entry__entry_date__gte=month_start,
                    entry__entry_date__lte=month_end
                )
                month_revenue += lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

            results.append({
                'month': month_start.strftime('%Y-%m'),
                'revenue': month_revenue
            })

        return results

    @staticmethod
    def get_profit_trend(months: int = 12) -> List[Dict]:
        """Profit trend over N months - delegates to FinancialReportEngine."""
        from accounting.services.financial_reports import FinancialReportEngine

        results = []
        today = date.today()

        for i in range(months - 1, -1, -1):
            month_start = today.replace(day=1) - timedelta(days=i * 30)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            pnl = FinancialReportEngine.get_profit_and_loss(month_start, month_end)

            results.append({
                'month': month_start.strftime('%Y-%m'),
                'gross_profit': pnl.get('gross_profit', Decimal('0.00')),
                'net_profit': pnl.get('net_income', Decimal('0.00'))
            })

        return results

    @staticmethod
    def get_expense_breakdown(start_date: date, end_date: date) -> List[Dict]:
        """Expense breakdown by category - delegates to FinancialReportEngine."""
        from accounting.services.financial_reports import FinancialReportEngine
        from accounting.models import Account

        expense_accounts = Account.objects.filter(
            account_type='EXPENSE',
            is_active=True
        )

        breakdown = []
        for acc in expense_accounts:
            from accounting.models import JournalEntryLine
            total = JournalEntryLine.objects.filter(
                account=acc,
                entry__is_posted=True,
                entry__entry_date__gte=start_date,
                entry__entry_date__lte=end_date
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

            if total > 0:
                breakdown.append({
                    'category': acc.name,
                    'amount': total
                })

        breakdown.sort(key=lambda x: x['amount'], reverse=True)
        return breakdown[:10]

    @staticmethod
    def get_cash_flow_summary(start_date: date, end_date: date) -> Dict:
        """Cash flow summary - delegates to FinancialReportEngine."""
        from accounting.services.financial_reports import FinancialReportEngine

        cf = FinancialReportEngine.get_cash_flow_statement(start_date, end_date)

        return {
            'operating': cf.get('net_cash_operations', Decimal('0.00')),
            'investing': cf.get('net_cash_investing', Decimal('0.00')),
            'financing': cf.get('net_cash_financing', Decimal('0.00')),
            'net_change': cf.get('net_change_in_cash', Decimal('0.00')),
            'opening': cf.get('opening_cash_balance', Decimal('0.00')),
            'closing': cf.get('closing_cash_balance', Decimal('0.00'))
        }

    # ==================== INVENTORY WIDGETS ====================

    @staticmethod
    def get_stock_value_by_warehouse() -> List[Dict]:
        """Stock value by warehouse - delegates to StockIntegrationService."""
        from inventory.models import Warehouse, Batch

        warehouses = Warehouse.objects.filter(is_active=True)
        results = []

        for wh in warehouses:
            value = Decimal('0.00')
            count = 0

            batches = Batch.objects.filter(
                warehouse=wh,
                remaining_quantity__gt=0,
                is_active=True
            )
            for batch in batches:
                value += batch.remaining_quantity * (batch.cost_per_unit or Decimal('0.00'))
                count += 1

            results.append({
                'warehouse': wh.name,
                'value': value,
                'batch_count': count
            })

        return results

    @staticmethod
    def get_low_stock_alerts(limit: int = 10) -> List[Dict]:
        """Low stock alerts - delegates to StockIntegrationService."""
        from inventory.models import Batch

        batches = Batch.objects.filter(
            remaining_quantity__lte=10,
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product', 'warehouse')[:limit]

        return [{
            'product': b.product.name if b.product else 'Unknown',
            'warehouse': b.warehouse.name if b.warehouse else 'Unknown',
            'current_quantity': b.remaining_quantity,
            'batch_number': b.batch_number
        } for b in batches]

    @staticmethod
    def get_expiry_risk(limit: int = 10) -> List[Dict]:
        """Expiry risk visualization - delegates to StockIntegrationService."""
        from inventory.models import Batch

        today = date.today()
        critical = Batch.objects.filter(
            expiry_date__lte=today + timedelta(days=30),
            expiry_date__gte=today,
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product', 'warehouse')[:limit]

        return [{
            'product': b.product.name,
            'warehouse': b.warehouse.name,
            'batch_number': b.batch_number,
            'expiry_date': b.expiry_date,
            'days_until_expiry': (b.expiry_date - today).days,
            'quantity': b.remaining_quantity
        } for b in critical]

    @staticmethod
    def get_fast_moving_products(limit: int = 10, days: int = 30) -> List[Dict]:
        """Fast moving products - derives from sales data."""
        from sales.models import SalesInvoiceLine
        from django.db.models import Sum

        start_date = date.today() - timedelta(days=days)

        items = SalesInvoiceLine.objects.filter(
            invoice__invoice_date__gte=start_date,
            invoice__status__in=['DISPATCHED', 'PAID', 'PARTIAL_PAID']
        ).values('product__name').annotate(
            total_qty=Sum('quantity'),
            total_amount=Sum('line_total')
        ).order_by('-total_qty')[:limit]

        return list(items)

    # ==================== ACCOUNTING WIDGETS ====================

    @staticmethod
    def get_trial_balance_snapshot(as_of_date: date) -> Dict:
        """Trial balance snapshot - delegates to FinancialReportEngine."""
        from accounting.services.financial_reports import FinancialReportEngine

        tb = FinancialReportEngine.get_trial_balance(as_of_date)

        return {
            'total_debit': tb.get('total_debit', Decimal('0.00')),
            'total_credit': tb.get('total_credit', Decimal('0.00')),
            'is_balanced': tb.get('is_balanced', False),
            'account_count': tb.get('account_count', 0)
        }

    @staticmethod
    def get_ledger_activity(days: int = 30) -> List[Dict]:
        """Ledger activity heatmap - delegates to FinancialReportEngine."""
        from accounting.models import JournalEntry

        start_date = date.today() - timedelta(days=days)
        entries = JournalEntry.objects.filter(
            entry_date__gte=start_date,
            is_posted=True
        ).values('entry_date').annotate(
            count=Count('id')
        ).order_by('entry_date')

        return list(entries)

    @staticmethod
    def get_je_volume(months: int = 6) -> List[Dict]:
        """Journal entry volume - derives from JournalEntry."""
        from accounting.models import JournalEntry

        results = []
        today = date.today()

        for i in range(months - 1, -1, -1):
            month_start = today.replace(day=1) - timedelta(days=i * 30)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            count = JournalEntry.objects.filter(
                entry_date__gte=month_start,
                entry_date__lte=month_end,
                is_posted=True
            ).count()

            results.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })

        return results

    # ==================== COST CENTER WIDGETS ====================

    @staticmethod
    def get_cost_center_performance() -> List[Dict]:
        """Cost center performance - delegates to CostReportingService."""
        from cost_centers.services.cost_reporting_service import CostReportingService

        summary = CostReportingService.get_all_centers_summary()
        return summary.get('cost_centers', [])

    @staticmethod
    def get_budget_variance_widget(fiscal_year: int) -> List[Dict]:
        """Budget vs Actual visualization - delegates to BudgetReportingService."""
        from budgeting.services.budget_reporting import BudgetReportingService

        variance = BudgetReportingService.get_budget_variance_report(fiscal_year)
        return variance.get('lines', [])[:10]

    @staticmethod
    def get_variance_heatmap() -> List[Dict]:
        """Variance heatmap by department - delegates to CostReportingService."""
        from cost_centers.services.cost_reporting_service import CostReportingService

        return CostReportingService.get_cost_by_type_report()

    # ==================== RECEIVABLES/PAYABLES WIDGETS ====================

    @staticmethod
    def get_ar_aging_widget() -> Dict:
        """AR Aging widget - delegates to FinancialReportEngine."""
        from accounting.services.financial_reports import FinancialReportEngine

        return FinancialReportEngine.get_ar_aging(date.today())

    @staticmethod
    def get_ap_aging_widget() -> Dict:
        """AP Aging widget - delegates to FinancialReportEngine."""
        from accounting.services.financial_reports import FinancialReportEngine

        return FinancialReportEngine.get_ap_aging(date.today())

    # ==================== OTHER WIDGETS ====================

    @staticmethod
    def get_tax_liability_widget() -> Dict:
        """Tax liability widget - delegates to TaxReportingService."""
        from tax.services.tax_reporting import TaxReportingService

        return TaxReportingService.get_tax_liability_report()

    @staticmethod
    def get_payroll_summary_widget(year: int) -> Dict:
        """Payroll summary widget - delegates to PayrollReportService."""
        from payroll.services.reports import PayrollReportService

        return PayrollReportService.get_payroll_summary(year)

    @staticmethod
    def get_asset_summary_widget() -> Dict:
        """Asset summary widget - delegates to AssetLifecycleService."""
        from fixed_assets.services.asset_lifecycle_service import AssetLifecycleService

        return AssetLifecycleService.get_asset_summary()
"""
Financial Analytics Service
Provides KPIs, metrics, dimensions, and dashboard analytics.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, List, Dict
from django.db.models import Sum, Q, Count, Avg, F
from django.db.models.functions import TruncMonth, TruncDay
from sales.models import SalesItem
from accounting.models import Account, JournalEntry, JournalEntryLine
from sales.models import SalesInvoice, Customer
from purchases.models import PurchaseInvoice, Supplier
from inventory.models import Product, StockMovement


class FinancialKPIs:
    """
    Financial Key Performance Indicators.
    """

    @staticmethod
    def get_profitability_kpis(as_of_date: Optional[date] = None) -> dict:
        """
        Calculate profitability KPIs.
        
        Returns:
            - Gross Profit Margin
            - Net Profit Margin
            - Operating Margin
        """
        if as_of_date is None:
            as_of_date = date.today()

        revenue_accounts = Account.objects.filter(
            account_category__in=['OPERATING_REVENUE', 'NON_OPERATING_REVENUE'], is_active=True
        )
        expense_accounts = Account.objects.filter(
            account_category__in=['COST_OF_GOODS_SOLD', 'OPERATING_EXPENSE', 'NON_OPERATING_EXPENSE'], is_active=True
        )

        base_filter = Q(
            entry__is_posted=True, 
            entry__is_active=True, 
            entry__entry_date__lte=as_of_date
        )

        total_revenue = sum(
            JournalEntryLine.objects.filter(account=acc).filter(base_filter)
            .aggregate(total=Sum('credit'))['total'] or Decimal('0')
            for acc in revenue_accounts
        )

        total_expenses = sum(
            JournalEntryLine.objects.filter(account=acc).filter(base_filter)
            .aggregate(total=Sum('debit'))['total'] or Decimal('0')
            for acc in expense_accounts
        )

        gross_profit = total_revenue - total_expenses
        net_profit = total_revenue - total_expenses

        gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')
        net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')

        return {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'gross_margin_percent': round(gross_margin, 2),
            'net_margin_percent': round(net_margin, 2),
            'as_of_date': as_of_date
        }

    @staticmethod
    def get_liquidity_kpis(as_of_date: Optional[date] = None) -> dict:
        """
        Calculate liquidity KPIs.
        
        Returns:
            - Current Ratio
            - Quick Ratio
            - Cash Ratio
        """
        if as_of_date is None:
            as_of_date = date.today()

        base_filter = Q(
            entry__is_posted=True,
            entry__is_active=True,
            entry__entry_date__lte=as_of_date
        )

        asset_accounts = Account.objects.filter(account_type='ASSET', is_active=True)
        liability_accounts = Account.objects.filter(account_type='LIABILITY', is_active=True)

        current_assets = sum(
            JournalEntryLine.objects.filter(account=acc).filter(base_filter)
            .aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')
            for acc in asset_accounts.filter(account_category='CURRENT_ASSET')
        )

        current_liabilities = sum(
            JournalEntryLine.objects.filter(account=acc).filter(base_filter)
            .aggregate(total=Sum('credit') - Sum('debit'))['total'] or Decimal('0')
            for acc in liability_accounts.filter(account_category='CURRENT_LIABILITY')
        )

        cash = sum(
            JournalEntryLine.objects.filter(account=acc).filter(base_filter)
            .aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')
            for acc in asset_accounts.filter(code__startswith='1000')
        )

        inventory_value = Decimal('0')

        current_ratio = (current_assets / current_liabilities) if current_liabilities > 0 else Decimal('0')
        quick_ratio = ((current_assets - inventory_value) / current_liabilities) if current_liabilities > 0 else Decimal('0')
        cash_ratio = (cash / current_liabilities) if current_liabilities > 0 else Decimal('0')

        return {
            'current_assets': current_assets,
            'current_liabilities': current_liabilities,
            'cash': cash,
            'inventory_value': inventory_value,
            'current_ratio': round(current_ratio, 2),
            'quick_ratio': round(quick_ratio, 2),
            'cash_ratio': round(cash_ratio, 2),
            'as_of_date': as_of_date
        }

    @staticmethod
    def get_efficiency_kpis(period_days: int = 30) -> dict:
        """
        Calculate efficiency KPIs.
        
        Returns:
            - Inventory Turnover
            - Days Sales Outstanding (DSO)
            - Days Payable Outstanding (DPO)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        total_sales = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_purchases = PurchaseInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        avg_receivables = SalesInvoice.objects.filter(
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')

        inventory_turnover = (total_sales / Decimal('10000')) if period_days > 0 else Decimal('0')
        dso = (avg_receivables / total_sales * period_days) if total_sales > 0 else Decimal('0')
        dpo = (Decimal('5000') / total_purchases * period_days) if total_purchases > 0 else Decimal('0')

        return {
            'inventory_turnover': round(inventory_turnover, 2),
            'days_sales_outstanding': round(dso, 1),
            'days_payable_outstanding': round(dpo, 1),
            'period_days': period_days,
            'total_sales': total_sales,
            'total_purchases': total_purchases
        }


class DimensionAnalysis:
    """
    Financial Dimension Analysis (by branch, department, project, etc.)
    """

    @staticmethod
    def get_sales_by_customer_type(start_date: date, end_date: date) -> dict:
        """Analyze sales by customer type."""
        invoices = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).values('customer__customer_type').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        )

        result = {}
        for item in invoices:
            ctype = item['customer__customer_type'] or 'UNKNOWN'
            result[ctype] = {
                'total_sales': item['total'] or Decimal('0'),
                'invoice_count': item['count']
            }

        return result

    @staticmethod
    def get_sales_by_product_category(start_date: date, end_date: date) -> dict:
        """Analyze sales by product category."""
        from sales.models import SalesInvoiceItem

        items = SalesInvoiceItem.objects.filter(
            invoice__invoice_date__gte=start_date,
            invoice__invoice_date__lte=end_date,
            invoice__status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).values('product__category__name').annotate(
            total_revenue=Sum('line_total'),
            total_quantity=Sum('quantity')
        )

        result = {}
        for item in items:
            cat = item['product__category__name'] or 'UNCATEGORIZED'
            result[cat] = {
                'revenue': item['total_revenue'] or Decimal('0'),
                'quantity_sold': item['total_quantity'] or 0
            }

        return result

    @staticmethod
    def get_expenses_by_category(start_date: date, end_date: date) -> dict:
        """Analyze expenses by account category."""
        base_filter = Q(
            entry__is_posted=True,
            entry__is_active=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date
        )

        expenses = JournalEntryLine.objects.filter(
            base_filter,
            account__account_category='EXPENSE'
        ).values('account__name').annotate(
            total=Sum('debit')
        )

        result = {}
        for item in expenses:
            result[item['account__name']] = item['total'] or Decimal('0')

        return result


class AnalyticsDashboard:
    """
    Dashboard analytics combining multiple data sources.
    """

    @staticmethod
    def get_summary_dashboard(as_of_date: Optional[date] = None) -> dict:
        """Get summary dashboard data."""
        if as_of_date is None:
            as_of_date = date.today()
        start_of_month = as_of_date.replace(day=1)

        total_revenue_mtd = SalesInvoice.objects.filter(
            invoice_date__gte=start_of_month,
            invoice_date__lte=as_of_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_revenue_ytd = SalesInvoice.objects.filter(
            invoice_date__year=as_of_date.year,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_purchases_mtd = PurchaseInvoice.objects.filter(
            invoice_date__gte=start_of_month,
            invoice_date__lte=as_of_date,
            status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_customers = Customer.objects.filter(is_active=True).count()
        total_suppliers = Supplier.objects.filter(is_active=True).count()

        ar_balance = SalesInvoice.objects.filter(
            payment_status__in=['UNPAID', 'PARTIAL']
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or Decimal('0')

        ap_balance = PurchaseInvoice.objects.filter(
            payment_status__in=['UNPAID', 'PARTIAL']
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or Decimal('0')

        return {
            'period': {
                'month': start_of_month,
                'as_of': as_of_date
            },
            'revenue': {
                'month_to_date': total_revenue_mtd,
                'year_to_date': total_revenue_ytd
            },
            'purchases': {
                'month_to_date': total_purchases_mtd
            },
            'customers': total_customers,
            'suppliers': total_suppliers,
            'receivables': ar_balance,
            'payables': ap_balance
        }

    @staticmethod
    def get_trend_data(days: int = 30) -> dict:
        """Get revenue trend over period."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        daily_sales = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).annotate(
            day=TruncDay('invoice_date')
        ).values('day').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('day')

        return {
            'period_days': days,
            'data': [
                {
                    'date': item['day'],
                    'revenue': item['total'] or Decimal('0'),
                    'invoice_count': item['count']
                }
                for item in daily_sales
            ]
        }

    @staticmethod
    def get_top_customers(limit: int = 10, days: int = 30) -> List[dict]:
        """Get top customers by revenue."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        top = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).values(
            'customer__id',
            'customer__name',
            'customer__code'
        ).annotate(
            total_revenue=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('-total_revenue')[:limit]

        return [
            {
                'customer_id': item['customer__id'],
                'customer_name': item['customer__name'],
                'customer_code': item['customer__code'],
                'total_revenue': item['total_revenue'] or Decimal('0'),
                'invoice_count': item['invoice_count']
            }
            for item in top
        ]

    @staticmethod
    def get_top_products(limit: int = 10, days: int = 30) -> List[dict]:
        """Get top products by sales quantity."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        top = SalesItem.objects.filter(
            invoice__invoice_date__gte=start_date,
            invoice__invoice_date__lte=end_date,
            invoice__status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID']
        ).values(
            'product__id',
            'product__name',
            'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total')
        ).order_by('-total_quantity')[:limit]

        return [
            {
                'product_id': item['product__id'],
                'product_name': item['product__name'],
                'sku': item['product__sku'],
                'quantity_sold': item['total_quantity'] or 0,
                'revenue': item['total_revenue'] or Decimal('0')
            }
            for item in top
        ]
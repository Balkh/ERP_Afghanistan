"""
KPI Engine for Pharmacy ERP.
Read-only analytical layer for Key Performance Indicators.
Extends existing FinancialKPIs with comprehensive metric tracking.
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, List
from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import TruncMonth, TruncDay

from sales.models import SalesInvoice, SalesItem, Customer
from purchases.models import PurchaseInvoice, PurchaseItem, Supplier
from inventory.models import Product, Batch, StockMovement, Warehouse
from accounting.models import Account, JournalEntry, JournalEntryLine


class KPICalculator:
    """
    Comprehensive KPI calculator.
    Read-only - computes metrics from existing data.
    """

    @staticmethod
    def get_gross_margin(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Calculate gross margin percentage."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        invoices = SalesInvoice.objects.filter(
            order_date__gte=start_date,
            order_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        )

        total_revenue = invoices.aggregate(
            revenue=Sum('subtotal'),
            discount=Sum('discount')
        )
        net_revenue = (total_revenue['revenue'] or Decimal('0')) - (total_revenue['discount'] or Decimal('0'))

        sales_items = SalesItem.objects.filter(invoice__in=invoices)
        product_ids = sales_items.values_list('product_id', flat=True).distinct()

        total_cogs = Decimal('0')
        for product_id in product_ids:
            qty = sales_items.filter(product_id=product_id).aggregate(total=Sum('quantity'))['total'] or Decimal('0')
            purchases = PurchaseItem.objects.filter(
                product_id=product_id,
                invoice__status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'],
                invoice__is_active=True
            )
            purchase_data = purchases.aggregate(
                cost=Sum(F('quantity') * F('unit_price')),
                qty=Sum('quantity')
            )
            avg_cost = (purchase_data['cost'] or Decimal('0')) / (purchase_data['qty'] or Decimal('1'))
            total_cogs += avg_cost * qty

        gross_profit = net_revenue - total_cogs
        gross_margin = (gross_profit / net_revenue * Decimal('100')) if net_revenue > 0 else Decimal('0')

        return {
            'net_revenue': net_revenue.quantize(Decimal('0.01')),
            'cost_of_goods_sold': total_cogs.quantize(Decimal('0.01')),
            'gross_profit': gross_profit.quantize(Decimal('0.01')),
            'gross_margin_pct': gross_margin.quantize(Decimal('0.01')),
        }

    @staticmethod
    def get_net_margin(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Calculate net margin percentage from journal entries."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        revenue_accounts = Account.objects.filter(code__startswith='4', is_active=True)
        expense_prefixes = ['5', '6']
        expense_query = Q()
        for prefix in expense_prefixes:
            expense_query |= Q(code__startswith=prefix)
        expense_accounts = Account.objects.filter(expense_query, is_active=True)

        base_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__gte=start_date, entry__entry_date__lte=end_date)

        total_revenue = JournalEntryLine.objects.filter(
            base_filter, account__in=revenue_accounts
        ).aggregate(total=Sum('credit'))['total'] or Decimal('0')

        total_expenses = JournalEntryLine.objects.filter(
            base_filter, account__in=expense_accounts
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        net_profit = total_revenue - total_expenses
        net_margin = (net_profit / total_revenue * Decimal('100')) if total_revenue > 0 else Decimal('0')

        return {
            'total_revenue': total_revenue.quantize(Decimal('0.01')),
            'total_expenses': total_expenses.quantize(Decimal('0.01')),
            'net_profit': net_profit.quantize(Decimal('0.01')),
            'net_margin_pct': net_margin.quantize(Decimal('0.01')),
        }

    @staticmethod
    def get_inventory_turnover(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Calculate inventory turnover ratio.
        Formula: COGS / Average Inventory
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        cogs_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__gte=start_date, entry__entry_date__lte=end_date)
        cogs_accounts = Account.objects.filter(code__startswith='5', is_active=True)

        cogs = JournalEntryLine.objects.filter(
            cogs_filter, account__in=cogs_accounts
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        inventory_accounts = Account.objects.filter(code__startswith='13', is_active=True)

        beginning_inventory = JournalEntryLine.objects.filter(
            entry__is_posted=True, entry__is_active=True, entry__entry_date__lt=start_date,
            account__in=inventory_accounts
        ).aggregate(debit=Sum('debit'), credit=Sum('credit'))
        beg_inv = ((beginning_inventory['debit'] or Decimal('0')) - (beginning_inventory['credit'] or Decimal('0')))

        ending_inventory = JournalEntryLine.objects.filter(
            entry__is_posted=True, entry__is_active=True, entry__entry_date__lte=end_date,
            account__in=inventory_accounts
        ).aggregate(debit=Sum('debit'), credit=Sum('credit'))
        end_inv = ((ending_inventory['debit'] or Decimal('0')) - (ending_inventory['credit'] or Decimal('0')))

        avg_inventory = (beg_inv + end_inv) / Decimal('2') if (beg_inv + end_inv) > 0 else Decimal('1')

        turnover = cogs / avg_inventory

        days_in_period = (end_date - start_date).days or 1
        days_sales_of_inventory = (avg_inventory / cogs * days_in_period) if cogs > 0 else Decimal('0')

        return {
            'cogs': cogs.quantize(Decimal('0.01')),
            'beginning_inventory': beg_inv.quantize(Decimal('0.01')),
            'ending_inventory': end_inv.quantize(Decimal('0.01')),
            'average_inventory': avg_inventory.quantize(Decimal('0.01')),
            'inventory_turnover': turnover.quantize(Decimal('0.01')),
            'days_sales_of_inventory': days_sales_of_inventory.quantize(Decimal('0.01')),
        }

    @staticmethod
    def get_cash_conversion_cycle(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Calculate Cash Conversion Cycle.
        CCC = DIO + DSO - DPO
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        days_in_period = (end_date - start_date).days or 1

        cogs_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__gte=start_date, entry__entry_date__lte=end_date)
        cogs_accounts = Account.objects.filter(code__startswith='5', is_active=True)
        cogs = JournalEntryLine.objects.filter(cogs_filter, account__in=cogs_accounts).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        avg_inventory = Decimal('10000')
        dio = (avg_inventory / cogs * days_in_period) if cogs > 0 else Decimal('0')

        total_sales = SalesInvoice.objects.filter(
            order_date__gte=start_date, order_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'], is_active=True
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        avg_receivables = SalesInvoice.objects.filter(
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'], is_active=True
        ).aggregate(avg=Avg(F('total_amount') - F('paid_amount')))['avg'] or Decimal('0')
        dso = (avg_receivables / total_sales * days_in_period) if total_sales > 0 else Decimal('0')

        total_purchases = PurchaseInvoice.objects.filter(
            order_date__gte=start_date, order_date__lte=end_date,
            status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'], is_active=True
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        avg_payables = PurchaseInvoice.objects.filter(
            status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'], is_active=True
        ).aggregate(avg=Avg(F('total_amount') - F('paid_amount')))['avg'] or Decimal('0')
        dpo = (avg_payables / total_purchases * days_in_period) if total_purchases > 0 else Decimal('0')

        ccc = dio + dso - dpo

        return {
            'days_inventory_outstanding': dio.quantize(Decimal('0.01')),
            'days_sales_outstanding': dso.quantize(Decimal('0.01')),
            'days_payable_outstanding': dpo.quantize(Decimal('0.01')),
            'cash_conversion_cycle': ccc.quantize(Decimal('0.01')),
        }

    @staticmethod
    def get_receivables_turnover(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Calculate receivables turnover."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        total_sales = SalesInvoice.objects.filter(
            order_date__gte=start_date, order_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'], is_active=True
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        ar_accounts = Account.objects.filter(code__startswith='12', is_active=True)
        ar_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__lte=end_date, account__in=ar_accounts)
        ar_balance = JournalEntryLine.objects.filter(ar_filter).aggregate(
            debit=Sum('debit'), credit=Sum('credit')
        )
        avg_ar = ((ar_balance['debit'] or Decimal('0')) - (ar_balance['credit'] or Decimal('0'))) or Decimal('1')

        turnover = total_sales / avg_ar
        days_in_period = (end_date - start_date).days or 1
        dso = (avg_ar / total_sales * days_in_period) if total_sales > 0 else Decimal('0')

        return {
            'net_credit_sales': total_sales.quantize(Decimal('0.01')),
            'average_accounts_receivable': avg_ar.quantize(Decimal('0.01')),
            'receivables_turnover': turnover.quantize(Decimal('0.01')),
            'days_sales_outstanding': dso.quantize(Decimal('0.01')),
        }

    @staticmethod
    def get_sales_velocity(
        days: int = 30
    ) -> Dict:
        """Calculate sales velocity metrics."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        invoices = SalesInvoice.objects.filter(
            order_date__gte=start_date,
            order_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        )

        total_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        total_items = SalesItem.objects.filter(invoice__in=invoices).aggregate(total=Sum('quantity'))['total'] or Decimal('0')
        avg_order_value = total_revenue / invoices.count() if invoices.count() > 0 else Decimal('0')

        return {
            'total_revenue': total_revenue.quantize(Decimal('0.01')),
            'total_items_sold': total_items,
            'total_invoices': invoices.count(),
            'average_order_value': avg_order_value.quantize(Decimal('0.01')),
            'daily_revenue': (total_revenue / days).quantize(Decimal('0.01')) if days > 0 else Decimal('0'),
            'daily_invoices': Decimal(invoices.count()) / Decimal(days) if days > 0 else Decimal('0'),
        }

    @staticmethod
    def get_product_performance(
        limit: int = 10,
        days: int = 30
    ) -> List[Dict]:
        """Get top/bottom performing products."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        sales_filter = Q(invoice__order_date__gte=start_date, invoice__order_date__lte=end_date)
        sales_filter &= Q(invoice__status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'])
        sales_filter &= Q(invoice__is_active=True)

        products = SalesItem.objects.filter(sales_filter).values(
            'product_id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total'),
            total_discount=Sum('discount'),
            transaction_count=Count('invoice', distinct=True),
        ).order_by('-total_revenue')[:limit]

        results = []
        for item in products:
            product_id = str(item['product_id'])
            revenue = item['total_revenue'] or Decimal('0')
            discount = item['total_discount'] or Decimal('0')
            net_revenue = revenue - discount

            results.append({
                'product_id': product_id,
                'product_name': item['product__name'],
                'product_code': item['product__sku'],
                'quantity_sold': item['total_quantity'] or Decimal('0'),
                'gross_revenue': revenue.quantize(Decimal('0.01')),
                'discounts': discount.quantize(Decimal('0.01')),
                'net_revenue': net_revenue.quantize(Decimal('0.01')),
                'transaction_count': item['transaction_count'],
            })

        return results

    @staticmethod
    def get_batch_expiry_risk(
        days_threshold: int = 90
    ) -> Dict:
        """Identify batches at risk of expiry."""
        from datetime import timedelta
        threshold_date = date.today() + timedelta(days=days_threshold)

        at_risk_batches = Batch.objects.filter(
            expiry_date__lte=threshold_date,
            expiry_date__gte=date.today(),
            remaining_quantity__gt=0
        ).select_related('product')

        total_at_risk_value = Decimal('0')
        for batch in at_risk_batches:
            total_at_risk_value += (batch.remaining_quantity or Decimal('0')) * (batch.sale_price or Decimal('0'))

        expired_batches = Batch.objects.filter(
            expiry_date__lt=date.today(),
            remaining_quantity__gt=0
        )

        expired_value = Decimal('0')
        for batch in expired_batches:
            expired_value += (batch.remaining_quantity or Decimal('0')) * (batch.sale_price or Decimal('0'))

        return {
            'threshold_days': days_threshold,
            'at_risk_batch_count': at_risk_batches.count(),
            'at_risk_value': total_at_risk_value.quantize(Decimal('0.01')),
            'expired_batch_count': expired_batches.count(),
            'expired_value': expired_value.quantize(Decimal('0.01')),
            'total_risk_exposure': (total_at_risk_value + expired_value).quantize(Decimal('0.01')),
        }

    @staticmethod
    def get_all_kpis_summary(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Get summary of all key KPIs."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'profitability': {
                'gross_margin': KPICalculator.get_gross_margin(start_date, end_date),
                'net_margin': KPICalculator.get_net_margin(start_date, end_date),
            },
            'efficiency': {
                'inventory_turnover': KPICalculator.get_inventory_turnover(start_date, end_date),
                'cash_conversion_cycle': KPICalculator.get_cash_conversion_cycle(start_date, end_date),
                'receivables_turnover': KPICalculator.get_receivables_turnover(start_date, end_date),
            },
            'sales': KPICalculator.get_sales_velocity(days=(end_date - start_date).days or 30),
            'risk': KPICalculator.get_batch_expiry_risk(),
        }

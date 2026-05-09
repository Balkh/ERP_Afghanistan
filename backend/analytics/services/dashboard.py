"""
Dashboard Engine for Pharmacy ERP.
Read-only analytical layer for dashboard data aggregation.
Combines multiple data sources for unified dashboard views.
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


class DashboardAggregator:
    """
    Aggregates dashboard data from multiple sources.
    Read-only - does not modify any data.
    """

    @staticmethod
    def get_executive_summary(as_of_date: Optional[date] = None) -> Dict:
        """
        Get executive-level summary dashboard.
        High-level KPIs for management review.
        """
        if as_of_date is None:
            as_of_date = date.today()

        start_of_month = as_of_date.replace(day=1)
        start_of_year = as_of_date.replace(month=1, day=1)

        revenue_mtd = SalesInvoice.objects.filter(
            order_date__gte=start_of_month,
            order_date__lte=as_of_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        revenue_ytd = SalesInvoice.objects.filter(
            order_date__gte=start_of_year,
            order_date__lte=as_of_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        purchases_mtd = PurchaseInvoice.objects.filter(
            order_date__gte=start_of_month,
            order_date__lte=as_of_date,
            status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        ar_balance = SalesInvoice.objects.filter(
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or Decimal('0')

        ap_balance = PurchaseInvoice.objects.filter(
            status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or Decimal('0')

        cash_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__lte=as_of_date)
        cash_accounts = Account.objects.filter(code__startswith='1000', is_active=True)
        cash_balance = JournalEntryLine.objects.filter(
            cash_filter, account__in=cash_accounts
        ).aggregate(debit=Sum('debit'), credit=Sum('credit'))
        cash = ((cash_balance['debit'] or Decimal('0')) - (cash_balance['credit'] or Decimal('0')))

        total_products = Product.objects.filter(is_active=True).count()
        total_customers = Customer.objects.filter(is_active=True).count()
        total_suppliers = Supplier.objects.filter(is_active=True).count()

        low_stock_products = Batch.objects.filter(
            remaining_quantity__gt=0,
            remaining_quantity__lte=10
        ).count()

        expiring_batches = Batch.objects.filter(
            expiry_date__lte=as_of_date + timedelta(days=90),
            expiry_date__gte=as_of_date,
            remaining_quantity__gt=0
        ).count()

        return {
            'as_of_date': as_of_date,
            'financial': {
                'revenue_mtd': revenue_mtd.quantize(Decimal('0.01')),
                'revenue_ytd': revenue_ytd.quantize(Decimal('0.01')),
                'purchases_mtd': purchases_mtd.quantize(Decimal('0.01')),
                'cash_balance': cash.quantize(Decimal('0.01')),
                'accounts_receivable': ar_balance.quantize(Decimal('0.01')),
                'accounts_payable': ap_balance.quantize(Decimal('0.01')),
                'working_capital': (cash + ar_balance - ap_balance).quantize(Decimal('0.01')),
            },
            'counts': {
                'active_products': total_products,
                'active_customers': total_customers,
                'active_suppliers': total_suppliers,
            },
            'alerts': {
                'low_stock_products': low_stock_products,
                'expiring_batches_90d': expiring_batches,
            }
        }

    @staticmethod
    def get_sales_dashboard(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Get sales-focused dashboard."""
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

        total_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        total_discount = invoices.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        total_paid = invoices.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
        avg_order_value = total_revenue / invoices.count() if invoices.count() > 0 else Decimal('0')

        daily_trend = SalesInvoice.objects.filter(
            order_date__gte=start_date,
            order_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        ).annotate(
            day=TruncDay('order_date')
        ).values('day').annotate(
            revenue=Sum('total_amount'),
            count=Count('id')
        ).order_by('day')

        top_products = SalesItem.objects.filter(
            invoice__order_date__gte=start_date,
            invoice__order_date__lte=end_date,
            invoice__status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            invoice__is_active=True
        ).values(
            'product__name'
        ).annotate(
            quantity=Sum('quantity'),
            revenue=Sum('total')
        ).order_by('-revenue')[:5]

        payment_status_dist = invoices.values('payment_status').annotate(count=Count('id'))

        return {
            'period': {'start_date': start_date, 'end_date': end_date},
            'summary': {
                'total_revenue': total_revenue.quantize(Decimal('0.01')),
                'total_discounts': total_discount.quantize(Decimal('0.01')),
                'net_revenue': (total_revenue - total_discount).quantize(Decimal('0.01')),
                'total_collected': total_paid.quantize(Decimal('0.01')),
                'outstanding': (total_revenue - total_paid).quantize(Decimal('0.01')),
                'total_invoices': invoices.count(),
                'avg_order_value': avg_order_value.quantize(Decimal('0.01')),
            },
            'daily_trend': [
                {
                    'date': item['day'],
                    'revenue': (item['revenue'] or Decimal('0')).quantize(Decimal('0.01')),
                    'invoice_count': item['count'],
                }
                for item in daily_trend
            ],
            'top_products': [
                {
                    'product_name': item['product__name'],
                    'quantity': item['quantity'] or Decimal('0'),
                    'revenue': (item['revenue'] or Decimal('0')).quantize(Decimal('0.01')),
                }
                for item in top_products
            ],
            'payment_status': [
                {
                    'status': item['payment_status'],
                    'count': item['count'],
                }
                for item in payment_status_dist
            ]
        }

    @staticmethod
    def get_inventory_dashboard(as_of_date: Optional[date] = None) -> Dict:
        """Get inventory-focused dashboard."""
        if as_of_date is None:
            as_of_date = date.today()

        total_products = Product.objects.filter(is_active=True).count()
        total_batches = Batch.objects.filter(remaining_quantity__gt=0).count()

        total_stock_value = Batch.objects.filter(
            remaining_quantity__gt=0
        ).aggregate(
            total=Sum(F('remaining_quantity') * F('sale_price'))
        )['total'] or Decimal('0')

        low_stock_count = Batch.objects.filter(
            remaining_quantity__gt=0,
            remaining_quantity__lte=10
        ).count()

        expiring_soon = Batch.objects.filter(
            expiry_date__gte=as_of_date,
            expiry_date__lte=as_of_date + timedelta(days=30),
            remaining_quantity__gt=0
        ).select_related('product')

        expired = Batch.objects.filter(
            expiry_date__lt=as_of_date,
            remaining_quantity__gt=0
        ).select_related('product')

        warehouse_stats = Warehouse.objects.filter(is_active=True)

        return {
            'as_of_date': as_of_date,
            'summary': {
                'total_products': total_products,
                'active_batches': total_batches,
                'total_stock_value': total_stock_value.quantize(Decimal('0.01')),
            },
            'alerts': {
                'low_stock_count': low_stock_count,
                'expiring_30d_count': expiring_soon.count(),
                'expired_count': expired.count(),
            },
            'warehouse_distribution': [
                {
                    'warehouse_name': w.name,
                    'warehouse_code': w.code,
                }
                for w in warehouse_stats
            ]
        }

    @staticmethod
    def get_financial_dashboard(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Get financial-focused dashboard."""
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
        asset_accounts = Account.objects.filter(code__startswith='1', is_active=True)
        liability_accounts = Account.objects.filter(code__startswith='2', is_active=True)

        base_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__gte=start_date, entry__entry_date__lte=end_date)

        total_revenue = JournalEntryLine.objects.filter(
            base_filter, account__in=revenue_accounts
        ).aggregate(total=Sum('credit'))['total'] or Decimal('0')

        total_expenses = JournalEntryLine.objects.filter(
            base_filter, account__in=expense_accounts
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        net_profit = total_revenue - total_expenses

        cumulative_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__lte=end_date)

        total_assets = JournalEntryLine.objects.filter(
            cumulative_filter, account__in=asset_accounts
        ).aggregate(debit=Sum('debit'), credit=Sum('credit'))
        assets = ((total_assets['debit'] or Decimal('0')) - (total_assets['credit'] or Decimal('0')))

        total_liabilities = JournalEntryLine.objects.filter(
            cumulative_filter, account__in=liability_accounts
        ).aggregate(credit=Sum('credit'), debit=Sum('debit'))
        liabilities = ((total_liabilities['credit'] or Decimal('0')) - (total_liabilities['debit'] or Decimal('0')))

        equity = assets - liabilities

        monthly_revenue = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            entry__is_active=True,
            account__in=revenue_accounts
        ).annotate(month=TruncMonth('entry__entry_date')).values('month').annotate(
            revenue=Sum('credit')
        ).order_by('month')

        return {
            'period': {'start_date': start_date, 'end_date': end_date},
            'performance': {
                'total_revenue': total_revenue.quantize(Decimal('0.01')),
                'total_expenses': total_expenses.quantize(Decimal('0.01')),
                'net_profit': net_profit.quantize(Decimal('0.01')),
                'profit_margin_pct': ((net_profit / total_revenue * Decimal('100')) if total_revenue > 0 else Decimal('0')).quantize(Decimal('0.01')),
            },
            'position': {
                'total_assets': assets.quantize(Decimal('0.01')),
                'total_liabilities': liabilities.quantize(Decimal('0.01')),
                'equity': equity.quantize(Decimal('0.01')),
            },
            'monthly_trend': [
                {
                    'month': item['month'],
                    'revenue': (item['revenue'] or Decimal('0')).quantize(Decimal('0.01')),
                }
                for item in monthly_revenue
            ]
        }

    @staticmethod
    def get_hr_dashboard(as_of_date: Optional[date] = None) -> Dict:
        """Get HR-focused dashboard."""
        if as_of_date is None:
            as_of_date = date.today()

        try:
            from hr.models import Employee, Department, Attendance, LeaveRequest, PayrollCycle

            total_employees = Employee.objects.filter(is_active=True).count()
            departments = Department.objects.filter(is_active=True).count()

            today_attendance = Attendance.objects.filter(date=as_of_date)
            present_count = today_attendance.filter(status='PRESENT').count()
            absent_count = today_attendance.filter(status='ABSENT').count()
            late_count = today_attendance.filter(status='LATE').count()

            pending_leaves = LeaveRequest.objects.filter(status='PENDING').count()

            current_payroll = PayrollCycle.objects.filter(
                status__in=['PENDING', 'APPROVED']
            ).first()

            return {
                'as_of_date': as_of_date,
                'summary': {
                    'total_employees': total_employees,
                    'departments': departments,
                },
                'attendance_today': {
                    'present': present_count,
                    'absent': absent_count,
                    'late': late_count,
                },
                'leaves': {
                    'pending_requests': pending_leaves,
                },
                'payroll': {
                    'active_cycle': current_payroll.period if current_payroll else None,
                    'cycle_status': current_payroll.status if current_payroll else 'NONE',
                }
            }
        except ImportError:
            return {
                'as_of_date': as_of_date,
                'summary': {'total_employees': 0, 'departments': 0},
                'attendance_today': {'present': 0, 'absent': 0, 'late': 0},
                'leaves': {'pending_requests': 0},
                'payroll': {'active_cycle': None, 'cycle_status': 'NONE'},
            }

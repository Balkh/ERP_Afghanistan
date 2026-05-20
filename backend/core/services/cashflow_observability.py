"""Cashflow Observability Engine — On-Demand Financial Visibility.

Provides cash inflow/outflow trends, net liquidity snapshots, and
outstanding exposure summary. Computed on-demand only — no background
aggregation or persistent recalculation.

Usage:
    cashflow = CashflowObservability.get_cashflow_summary(days=30)
    liquidity = CashflowObservability.get_liquidity_snapshot()
"""
from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum
from django.utils import timezone


class CashflowObservability:
    """On-demand cashflow observability — lightweight, stateless computation.
    
    All methods are read-only and computed on-demand. No caching, no
    background jobs, no persistent tables.
    """

    @staticmethod
    def get_cashflow_summary(days: int = 30) -> dict:
        """Compute cash inflow/outflow trends for the last N days.
        
        Returns:
            dict with inflow, outflow, net, daily breakdown, and trends.
        """
        from sales.models import CustomerPayment
        from purchases.models import SupplierPayment

        today = timezone.now().date()
        start_date = today - timedelta(days=days)

        # Customer payments (inflow)
        total_inflow = CustomerPayment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Supplier payments (outflow)
        total_outflow = SupplierPayment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        net_liquidity = total_inflow - total_outflow

        # Daily breakdown (bounded to last 14 days for performance)
        daily = []
        for i in range(min(days, 14)):
            day = today - timedelta(days=i)
            day_inflow = CustomerPayment.objects.filter(
                payment_date=day,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            day_outflow = SupplierPayment.objects.filter(
                payment_date=day,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            daily.append({
                'date': str(day),
                'inflow': str(day_inflow),
                'outflow': str(day_outflow),
                'net': str(day_inflow - day_outflow),
            })

        # Trend comparison (previous period vs current period)
        half = days // 2
        mid_date = today - timedelta(days=half)
        first_half_start = mid_date - timedelta(days=half)

        inflow_first = CustomerPayment.objects.filter(
            payment_date__gte=first_half_start,
            payment_date__lt=mid_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        inflow_second = CustomerPayment.objects.filter(
            payment_date__gte=mid_date,
            payment_date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        outflow_first = SupplierPayment.objects.filter(
            payment_date__gte=first_half_start,
            payment_date__lt=mid_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        outflow_second = SupplierPayment.objects.filter(
            payment_date__gte=mid_date,
            payment_date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        inflow_trend = 'INCREASING' if inflow_second > inflow_first else ('DECREASING' if inflow_second < inflow_first else 'STABLE')
        outflow_trend = 'INCREASING' if outflow_second > outflow_first else ('DECREASING' if outflow_second < outflow_first else 'STABLE')

        return {
            'period_days': days,
            'start_date': str(start_date),
            'end_date': str(today),
            'total_inflow': str(total_inflow),
            'total_outflow': str(total_outflow),
            'net_liquidity': str(net_liquidity),
            'inflow_trend': inflow_trend,
            'outflow_trend': outflow_trend,
            'daily_breakdown': daily,
            'summary': {
                'inflow_first_half': str(inflow_first),
                'inflow_second_half': str(inflow_second),
                'outflow_first_half': str(outflow_first),
                'outflow_second_half': str(outflow_second),
            },
        }

    @staticmethod
    def get_liquidity_snapshot() -> dict:
        """Point-in-time liquidity snapshot.
        
        Returns current cash position based on:
        - Outstanding receivables (what customers owe)
        - Outstanding payables (what we owe suppliers)
        - Net exposure
        """
        from sales.models import CustomerPayment, SalesInvoice
        from purchases.models import SupplierPayment, PurchaseInvoice
        from core.services.financial_truth_engine import FinancialTruthEngine

        today = timezone.now().date()

        # Total receivables (sum of all outstanding customer balances)
        total_receivables = Decimal('0.00')
        from sales.models import Customer
        for customer in Customer.objects.filter(status='ACTIVE')[:200]:
            balance = FinancialTruthEngine.get_customer_balance(customer)
            if balance > 0:
                total_receivables += balance

        # Total payables (sum of all outstanding supplier balances)
        total_payables = Decimal('0.00')
        from purchases.models import Supplier
        for supplier in Supplier.objects.filter(status='ACTIVE')[:200]:
            balance = FinancialTruthEngine.get_supplier_balance(supplier)
            if balance > 0:
                total_payables += balance

        # Overdue receivables
        overdue_receivables = Decimal('0.00')
        for customer in Customer.objects.filter(status='ACTIVE')[:200]:
            overdue = FinancialTruthEngine.get_customer_overdue_balance(customer)
            overdue_receivables += overdue

        # Overdue payables
        overdue_payables = Decimal('0.00')
        for supplier in Supplier.objects.filter(status='ACTIVE')[:200]:
            overdue = FinancialTruthEngine.get_supplier_overdue_balance(supplier)
            overdue_payables += overdue

        net_exposure = total_receivables - total_payables

        return {
            'snapshot_date': str(today),
            'total_receivables': str(total_receivables),
            'total_payables': str(total_payables),
            'net_exposure': str(net_exposure),
            'overdue_receivables': str(overdue_receivables),
            'overdue_payables': str(overdue_payables),
            'receivables_to_payables_ratio': round(
                float(total_receivables / total_payables) if total_payables > 0 else 0, 2
            ),
            'overdue_ratio_pct': round(
                float(overdue_receivables / total_receivables * 100) if total_receivables > 0 else 0, 1
            ),
        }

    @staticmethod
    def get_outstanding_exposure() -> dict:
        """Summary of outstanding financial exposure.
        
        Returns aging buckets for receivables and payables.
        """
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice

        today = timezone.now().date()

        # Receivables aging
        def aging_bucket(invoices, today):
            buckets = {
                'current': Decimal('0.00'),
                '1_30_days': Decimal('0.00'),
                '31_60_days': Decimal('0.00'),
                '61_90_days': Decimal('0.00'),
                'over_90_days': Decimal('0.00'),
            }
            for inv in invoices:
                unpaid = inv.total_amount - inv.paid_amount
                if unpaid <= Decimal('0.00'):
                    continue
                try:
                    days_overdue = (today - inv.due_date).days
                except (TypeError, ValueError):
                    days_overdue = 0

                if days_overdue <= 0:
                    buckets['current'] += unpaid
                elif days_overdue <= 30:
                    buckets['1_30_days'] += unpaid
                elif days_overdue <= 60:
                    buckets['31_60_days'] += unpaid
                elif days_overdue <= 90:
                    buckets['61_90_days'] += unpaid
                else:
                    buckets['over_90_days'] += unpaid
            return {k: str(v) for k, v in buckets.items()}

        receivable_invoices = list(SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
        ))
        payable_invoices = list(PurchaseInvoice.objects.filter(
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
        ))

        return {
            'receivables_aging': aging_bucket(receivable_invoices, today),
            'payables_aging': aging_bucket(payable_invoices, today),
            'total_outstanding_receivables': str(
                sum(inv.total_amount - inv.paid_amount for inv in receivable_invoices
                    if inv.total_amount - inv.paid_amount > Decimal('0.00'))
            ),
            'total_outstanding_payables': str(
                sum(inv.total_amount - inv.paid_amount for inv in payable_invoices
                    if inv.total_amount - inv.paid_amount > Decimal('0.00'))
            ),
        }

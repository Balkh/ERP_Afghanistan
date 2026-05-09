"""
DrillDown Engine - Navigation from Dashboard KPI to Source Records

RULES:
- MUST reuse existing API endpoints/views
- No duplicate query logic
- Preserve audit trail traceability
"""

from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db.models import Q, Sum


class DrillDownEngine:
    """Engine for drilling down from dashboard KPIs to source records."""

    @staticmethod
    def drill_revenue_to_invoices(
        start_date: date,
        end_date: date,
        entity_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Drill down from revenue KPI to sales invoices."""
        from sales.models import SalesInvoice
        from sales.serializers import SalesInvoiceSerializer

        queryset = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['DISPATCHED', 'PAID', 'PARTIAL_PAID']
        ).select_related('customer', 'currency').order_by('-invoice_date')[:limit]

        return [{
            'id': str(inv.id),
            'invoice_number': inv.invoice_number,
            'customer': str(inv.customer),
            'invoice_date': inv.invoice_date,
            'total_amount': inv.total_amount,
            'status': inv.status,
            'payment_status': inv.payment_status
        } for inv in queryset]

    @staticmethod
    def drill_inventory_value_to_batches(
        warehouse_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Drill down from inventory value to batch details."""
        from inventory.models import Batch

        queryset = Batch.objects.filter(
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product')

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        queryset = queryset.order_by('-remaining_quantity')[:limit]

        return [{
            'id': str(b.id),
            'product': b.product.name if b.product else 'Unknown',
            'batch_number': b.batch_number,
            'quantity': b.remaining_quantity,
            'cost_per_unit': b.cost_per_unit,
            'total_value': b.remaining_quantity * (b.cost_per_unit or Decimal('0.00')),
            'expiry_date': b.expiry_date
        } for b in queryset]

    @staticmethod
    def drill_cash_position_to_transactions(
        start_date: date,
        end_date: date,
        transaction_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Drill down from cash position to payment transactions."""
        from payments.models import FinancialTransaction

        queryset = FinancialTransaction.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status='COMPLETED'
        ).select_related('payment_account', 'payment_method')

        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        queryset = queryset.order_by('-created_at')[:limit]

        return [{
            'id': str(t.id),
            'transaction_number': t.transaction_number,
            'payment_account': str(t.payment_account),
            'transaction_type': t.transaction_type,
            'amount': t.amount,
            'fee_amount': t.fee_amount or Decimal('0.00'),
            'status': t.status,
            'created_at': t.created_at
        } for t in queryset]

    @staticmethod
    def drill_ar_to_invoices(
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Drill down from AR to sales invoices."""
        from sales.models import SalesInvoice

        queryset = SalesInvoice.objects.filter(
            status__in=['DISPATCHED', 'PARTIAL_PAID'],
            payment_status__in=['UNPAID', 'PARTIAL']
        ).select_related('customer')

        if status == 'overdue':
            queryset = queryset.filter(due_date__lt=date.today())

        queryset = queryset.order_by('invoice_date')[:limit]

        return [{
            'id': str(inv.id),
            'invoice_number': inv.invoice_number,
            'customer': str(inv.customer),
            'invoice_date': inv.invoice_date,
            'due_date': inv.due_date,
            'total_amount': inv.total_amount,
            'paid_amount': inv.paid_amount,
            'outstanding': inv.total_amount - inv.paid_amount,
            'is_overdue': inv.due_date < date.today() if inv.due_date else False
        } for inv in queryset]

    @staticmethod
    def drill_ap_to_invoices(
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Drill down from AP to purchase invoices."""
        from purchases.models import PurchaseInvoice

        queryset = PurchaseInvoice.objects.filter(
            status__in=['RECEIVED', 'PARTIAL_RECEIVED'],
            payment_status__in=['UNPAID', 'PARTIAL']
        ).select_related('supplier')

        if status == 'overdue':
            queryset = queryset.filter(due_date__lt=date.today())

        queryset = queryset.order_by('invoice_date')[:limit]

        return [{
            'id': str(inv.id),
            'invoice_number': inv.invoice_number,
            'supplier': str(inv.supplier),
            'invoice_date': inv.invoice_date,
            'due_date': inv.due_date,
            'total_amount': inv.total_amount,
            'paid_amount': inv.paid_amount,
            'outstanding': inv.total_amount - inv.paid_amount,
            'is_overdue': inv.due_date < date.today() if inv.due_date else False
        } for inv in queryset]

    @staticmethod
    def drill_profit_to_journal_entries(
        start_date: date,
        end_date: date,
        limit: int = 50
    ) -> List[Dict]:
        """Drill down from profit to journal entries."""
        from accounting.models import JournalEntry, Account

        revenue_accounts = Account.objects.filter(
            account_type='REVENUE',
            is_active=True
        )
        expense_accounts = Account.objects.filter(
            account_type='EXPENSE',
            is_active=True
        )

        from accounting.models import JournalEntryLine
        lines = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
            account__in=list(revenue_accounts) + list(expense_accounts)
        ).select_related('entry', 'account').order_by('-entry__entry_date')[:limit]

        seen = set()
        result = []
        for line in lines:
            entry_id = str(line.entry.id)
            if entry_id not in seen:
                seen.add(entry_id)
                result.append({
                    'id': entry_id,
                    'entry_number': line.entry.entry_number,
                    'entry_date': line.entry.entry_date,
                    'description': line.entry.description,
                    'total_debit': line.entry.lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00'),
                    'is_posted': line.entry.is_posted
                })

        return result

    @staticmethod
    def drill_budget_variance_to_lines(fiscal_year: int) -> List[Dict]:
        """Drill down from budget variance to budget lines."""
        from budgeting.models import BudgetLine
        from django.db.models import F

        lines = BudgetLine.objects.filter(
            budget__fiscal_year=fiscal_year,
            budget__is_active=True
        ).select_related('account', 'budget').order_by('-actual_amount')[:50]

        return [{
            'id': str(line.id),
            'account': str(line.account.name),
            'budgeted': line.budgeted_amount,
            'actual': line.actual_amount,
            'variance': line.budgeted_amount - line.actual_amount,
            'variance_pct': ((line.actual_amount - line.budgeted_amount) / line.budgeted_amount * 100) if line.budgeted_amount > 0 else 0
        } for line in lines]

    @staticmethod
    def drill_cost_center_to_transactions(
        cost_center_id: str,
        start_date: date,
        end_date: date,
        limit: int = 50
    ) -> List[Dict]:
        """Drill down from cost center to journal entries."""
        from accounting.models import JournalEntryLine, JournalEntry

        lines = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
            cost_center_id=cost_center_id
        ).select_related('entry', 'account').order_by('-entry__entry_date')[:limit]

        return [{
            'id': str(line.id),
            'entry_number': line.entry.entry_number,
            'entry_date': line.entry.entry_date,
            'account': str(line.account.name),
            'debit': line.debit,
            'credit': line.credit,
            'description': line.entry.description
        } for line in lines]

    @staticmethod
    def drill_low_stock_to_batches(limit: int = 50) -> List[Dict]:
        """Drill down from low stock alerts to batch details."""
        from inventory.models import Batch
        from django.db.models import F

        batches = Batch.objects.filter(
            remaining_quantity__lte=F('product__min_stock_level'),
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product', 'warehouse').order_by('remaining_quantity')[:limit]

        return [{
            'id': str(b.id),
            'product': b.product.name,
            'warehouse': b.warehouse.name,
            'current_qty': b.remaining_quantity,
            'min_level': b.product.min_stock_level,
            'shortage': b.product.min_stock_level - b.remaining_quantity
        } for b in batches]

    @staticmethod
    def drill_expiry_to_batches(days_ahead: int = 30, limit: int = 50) -> List[Dict]:
        """Drill down from expiry risk to batch details."""
        from inventory.models import Batch
        from datetime import timedelta

        today = date.today()
        batches = Batch.objects.filter(
            expiry_date__lte=today + timedelta(days=days_ahead),
            expiry_date__gte=today,
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product', 'warehouse').order_by('expiry_date')[:limit]

        return [{
            'id': str(b.id),
            'product': b.product.name,
            'warehouse': b.warehouse.name,
            'batch_number': b.batch_number,
            'quantity': b.remaining_quantity,
            'expiry_date': b.expiry_date,
            'days_until_expiry': (b.expiry_date - today).days
        } for b in batches]
"""Consolidated Statement Engine.

Lightweight statement generation for customers and suppliers.
Generates running balance statements with opening/closing balances,
transaction history, and aging summary.

Usage:
    StatementService.customer_statement(customer, from_date, to_date)
    StatementService.supplier_statement(supplier, from_date, to_date)
"""
from decimal import Decimal
from datetime import date
from typing import Optional
from django.db.models import Sum, Q


class StatementService:
    """Lightweight statement generator for customers and suppliers."""

    @staticmethod
    def customer_statement(customer, from_date: Optional[date] = None, to_date: Optional[date] = None) -> dict:
        """Generate customer statement with running balance.

        Returns:
            Dict with opening_balance, transactions, closing_balance, aging_summary
        """
        from sales.models import SalesInvoice, CustomerPayment

        from_date = from_date or date.today().replace(day=1)
        to_date = to_date or date.today()

        # Opening balance (before from_date)
        opening_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
            invoice_date__lt=from_date,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        opening_payments = CustomerPayment.objects.filter(
            customer=customer,
            payment_date__lt=from_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        opening_balance = opening_invoices - opening_payments

        # Transactions within date range
        transactions = []

        # Invoices
        invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
            invoice_date__range=[from_date, to_date],
        ).order_by('invoice_date', 'created_at')

        for inv in invoices:
            transactions.append({
                'date': inv.invoice_date.isoformat(),
                'type': 'INVOICE',
                'reference': inv.invoice_number,
                'debit': inv.total_amount,
                'credit': Decimal('0.00'),
                'description': f'Sales Invoice {inv.invoice_number}',
            })

        # Payments
        payments = CustomerPayment.objects.filter(
            customer=customer,
            payment_date__range=[from_date, to_date],
        ).order_by('payment_date', 'created_at')

        for pay in payments:
            transactions.append({
                'date': pay.payment_date.isoformat(),
                'type': 'PAYMENT',
                'reference': pay.reference_number or str(pay.pk)[:8],
                'debit': Decimal('0.00'),
                'credit': pay.amount,
                'description': f'Payment {pay.reference_number or pay.pk}',
            })

        # Sort by date
        transactions.sort(key=lambda x: x['date'])

        # Calculate running balance
        running_balance = opening_balance
        for txn in transactions:
            running_balance += txn['debit'] - txn['credit']
            txn['running_balance'] = running_balance

        # Closing balance
        closing_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
            invoice_date__lte=to_date,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        closing_payments = CustomerPayment.objects.filter(
            customer=customer,
            payment_date__lte=to_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        closing_balance = closing_invoices - closing_payments

        # Aging summary
        aging_summary = StatementService._customer_aging(customer, to_date)

        return {
            'customer': {
                'id': str(customer.pk),
                'code': customer.code,
                'name': customer.name,
            },
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat(),
            },
            'opening_balance': opening_balance,
            'transactions': transactions,
            'closing_balance': closing_balance,
            'aging_summary': aging_summary,
            'total_invoices': closing_invoices,
            'total_payments': closing_payments,
        }

    @staticmethod
    def supplier_statement(supplier, from_date: Optional[date] = None, to_date: Optional[date] = None) -> dict:
        """Generate supplier statement with running balance.

        Returns:
            Dict with opening_balance, transactions, closing_balance, aging_summary
        """
        from purchases.models import PurchaseInvoice, SupplierPayment

        from_date = from_date or date.today().replace(day=1)
        to_date = to_date or date.today()

        # Opening balance
        opening_invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
            invoice_date__lt=from_date,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        opening_payments = SupplierPayment.objects.filter(
            supplier=supplier,
            payment_date__lt=from_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        opening_balance = opening_invoices - opening_payments

        # Transactions
        transactions = []

        # Purchase invoices
        invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
            invoice_date__range=[from_date, to_date],
        ).order_by('invoice_date', 'created_at')

        for inv in invoices:
            transactions.append({
                'date': inv.invoice_date.isoformat(),
                'type': 'PURCHASE',
                'reference': inv.invoice_number,
                'debit': inv.total_amount,
                'credit': Decimal('0.00'),
                'description': f'Purchase Invoice {inv.invoice_number}',
            })

        # Payments
        payments = SupplierPayment.objects.filter(
            supplier=supplier,
            payment_date__range=[from_date, to_date],
        ).order_by('payment_date', 'created_at')

        for pay in payments:
            transactions.append({
                'date': pay.payment_date.isoformat(),
                'type': 'PAYMENT',
                'reference': pay.reference_number or str(pay.pk)[:8],
                'debit': Decimal('0.00'),
                'credit': pay.amount,
                'description': f'Payment {pay.reference_number or pay.pk}',
            })

        transactions.sort(key=lambda x: x['date'])

        # Running balance
        running_balance = opening_balance
        for txn in transactions:
            running_balance += txn['debit'] - txn['credit']
            txn['running_balance'] = running_balance

        # Closing balance
        closing_invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
            invoice_date__lte=to_date,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        closing_payments = SupplierPayment.objects.filter(
            supplier=supplier,
            payment_date__lte=to_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        closing_balance = closing_invoices - closing_payments

        # Aging summary
        aging_summary = StatementService._supplier_aging(supplier, to_date)

        return {
            'supplier': {
                'id': str(supplier.pk),
                'code': supplier.code,
                'name': supplier.name,
            },
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat(),
            },
            'opening_balance': opening_balance,
            'transactions': transactions,
            'closing_balance': closing_balance,
            'aging_summary': aging_summary,
            'total_invoices': closing_invoices,
            'total_payments': closing_payments,
        }

    @staticmethod
    def _customer_aging(customer, as_of_date: date) -> dict:
        """Calculate customer aging summary."""
        from sales.models import SalesInvoice

        outstanding = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
            due_date__lte=as_of_date,
        )

        aging = {
            'current': Decimal('0.00'),
            '1_30_days': Decimal('0.00'),
            '31_60_days': Decimal('0.00'),
            '61_90_days': Decimal('0.00'),
            'over_90_days': Decimal('0.00'),
            'total_outstanding': Decimal('0.00'),
        }

        for inv in outstanding:
            remaining = inv.total_amount - inv.paid_amount
            if remaining <= 0:
                continue

            days_overdue = (as_of_date - inv.due_date).days
            aging['total_outstanding'] += remaining

            if days_overdue <= 0:
                aging['current'] += remaining
            elif days_overdue <= 30:
                aging['1_30_days'] += remaining
            elif days_overdue <= 60:
                aging['31_60_days'] += remaining
            elif days_overdue <= 90:
                aging['61_90_days'] += remaining
            else:
                aging['over_90_days'] += remaining

        return aging

    @staticmethod
    def _supplier_aging(supplier, as_of_date: date) -> dict:
        """Calculate supplier aging summary."""
        from purchases.models import PurchaseInvoice

        outstanding = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
            due_date__lte=as_of_date,
        )

        aging = {
            'current': Decimal('0.00'),
            '1_30_days': Decimal('0.00'),
            '31_60_days': Decimal('0.00'),
            '61_90_days': Decimal('0.00'),
            'over_90_days': Decimal('0.00'),
            'total_outstanding': Decimal('0.00'),
        }

        for inv in outstanding:
            remaining = inv.total_amount - inv.paid_amount
            if remaining <= 0:
                continue

            days_overdue = (as_of_date - inv.due_date).days
            aging['total_outstanding'] += remaining

            if days_overdue <= 0:
                aging['current'] += remaining
            elif days_overdue <= 30:
                aging['1_30_days'] += remaining
            elif days_overdue <= 60:
                aging['31_60_days'] += remaining
            elif days_overdue <= 90:
                aging['61_90_days'] += remaining
            else:
                aging['over_90_days'] += remaining

        return aging

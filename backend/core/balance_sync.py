"""Centralized balance synchronization service for Pharmacy ERP.

Single source of truth for customer and supplier balance calculations.
Eliminates dual-path inconsistency by providing one authoritative path.

Usage:
    BalanceSyncService.sync_customer(customer)
    BalanceSyncService.sync_supplier(supplier)
    BalanceSyncService.sync_all()  # on-demand integrity check
"""
from decimal import Decimal
from typing import Optional
from django.db import models, transaction
from django.db.models import Sum


class BalanceSyncService:
    """Authoritative balance recalculation service.

    All balance updates MUST flow through this service.
    Direct mutation of Customer.balance or Supplier.balance is forbidden.
    """

    @staticmethod
    def sync_customer(customer, *, lock: bool = True, user=None, reason: str = '') -> Decimal:
        """Recalculate and persist customer balance atomically.

        Balance = total_invoices - total_payments - total_approved_return_credits
        where invoices are CONFIRMED/DISPATCHED/PARTIAL_PAID/PAID and active,
        and return credits are approved SALE_RETURN credit notes.

        Args:
            customer: Customer instance
            lock: If True, acquire row-level lock for concurrent safety
            user: Optional user performing the sync (for audit)
            reason: Optional reason for the sync (for audit)

        Returns:
            New balance as Decimal
        """
        from sales.models import Customer, SalesInvoice, CustomerPayment
        from returns.models import ReturnOrder
        from core.services.financial_audit import FinancialAuditService

        qs = Customer.objects
        if lock:
            qs = qs.select_for_update()

        customer = qs.get(pk=customer.pk)
        old_balance = customer.balance

        total_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_invoices = total_invoices.quantize(Decimal('0.01'))

        total_payments = CustomerPayment.objects.filter(
            customer=customer,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_payments = total_payments.quantize(Decimal('0.01'))

        total_returns = ReturnOrder.objects.filter(
            party=customer,
            return_type='SALE_RETURN',
            status__in=['APPROVED', 'COMPLETED'],
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_returns = total_returns.quantize(Decimal('0.01'))

        new_balance = (total_invoices - total_payments - total_returns).quantize(Decimal('0.01'))
        customer.balance = new_balance
        customer.save(update_fields=['balance', 'updated_at'])

        if old_balance != new_balance:
            FinancialAuditService.log_balance_sync(
                entity_type='customer',
                entity_id=str(customer.pk),
                balance_before=old_balance,
                balance_after=new_balance,
                user=user,
                reason=reason,
            )

        return new_balance

    @staticmethod
    def sync_supplier(supplier, *, lock: bool = True, user=None, reason: str = '') -> Decimal:
        """Recalculate and persist supplier balance atomically.

        Balance = total_invoices - total_payments - total_approved_return_debits

        Args:
            supplier: Supplier instance
            lock: If True, acquire row-level lock for concurrent safety
            user: Optional user performing the sync (for audit)
            reason: Optional reason for the sync (for audit)

        Returns:
            New balance as Decimal
        """
        from purchases.models import Supplier, PurchaseInvoice, SupplierPayment
        from returns.models import ReturnOrder
        from core.services.financial_audit import FinancialAuditService

        qs = Supplier.objects
        if lock:
            qs = qs.select_for_update()

        supplier = qs.get(pk=supplier.pk)
        old_balance = supplier.balance

        total_invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_invoices = total_invoices.quantize(Decimal('0.01'))

        total_payments = SupplierPayment.objects.filter(
            supplier=supplier,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_payments = total_payments.quantize(Decimal('0.01'))

        total_returns = ReturnOrder.objects.filter(
            supplier=supplier,
            return_type='PURCHASE_RETURN',
            status__in=['APPROVED', 'COMPLETED'],
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_returns = total_returns.quantize(Decimal('0.01'))

        new_balance = (total_invoices - total_payments - total_returns).quantize(Decimal('0.01'))
        supplier.balance = new_balance
        supplier.save(update_fields=['balance', 'updated_at'])

        if old_balance != new_balance:
            FinancialAuditService.log_balance_sync(
                entity_type='supplier',
                entity_id=str(supplier.pk),
                balance_before=old_balance,
                balance_after=new_balance,
                user=user,
                reason=reason,
            )

        return new_balance

    @staticmethod
    def sync_customer_by_invoice(invoice, *, lock: bool = True, user=None) -> Decimal:
        """Sync customer balance after an invoice change.

        More efficient than full recalculation when only one invoice changed.

        Args:
            invoice: SalesInvoice instance
            lock: If True, acquire row-level lock
            user: Optional user (for audit)

        Returns:
            New balance as Decimal
        """
        from sales.models import Customer
        from returns.models import ReturnOrder
        from core.services.financial_audit import FinancialAuditService

        qs = Customer.objects
        if lock:
            qs = qs.select_for_update()

        customer = qs.get(pk=invoice.customer.pk)
        old_balance = customer.balance

        total_invoices = invoice.customer.sales_invoices.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_invoices = total_invoices.quantize(Decimal('0.01'))

        total_payments = invoice.customer.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        total_payments = total_payments.quantize(Decimal('0.01'))

        # X-03: include return credits so this method matches sync_customer()
        total_returns = ReturnOrder.objects.filter(
            party=customer,
            return_type='SALE_RETURN',
            status__in=['APPROVED', 'COMPLETED'],
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_returns = total_returns.quantize(Decimal('0.01'))

        new_balance = (total_invoices - total_payments - total_returns).quantize(Decimal('0.01'))
        customer.balance = new_balance
        customer.save(update_fields=['balance', 'updated_at'])

        if old_balance != new_balance:
            FinancialAuditService.log_balance_sync(
                entity_type='customer',
                entity_id=str(customer.pk),
                balance_before=old_balance,
                balance_after=new_balance,
                user=user,
                reason='Invoice change',
            )

        return new_balance

    @staticmethod
    def sync_supplier_by_invoice(invoice, *, lock: bool = True, user=None) -> Decimal:
        """Sync supplier balance after a purchase invoice change.

        Args:
            invoice: PurchaseInvoice instance
            lock: If True, acquire row-level lock
            user: Optional user (for audit)

        Returns:
            New balance as Decimal
        """
        from purchases.models import Supplier
        from returns.models import ReturnOrder
        from core.services.financial_audit import FinancialAuditService

        qs = Supplier.objects
        if lock:
            qs = qs.select_for_update()

        supplier = qs.get(pk=invoice.supplier.pk)
        old_balance = supplier.balance

        total_invoices = invoice.supplier.purchase_invoices.filter(
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_invoices = total_invoices.quantize(Decimal('0.01'))

        total_payments = invoice.supplier.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        total_payments = total_payments.quantize(Decimal('0.01'))

        # X-03: include return debits so this method matches sync_supplier()
        total_returns = ReturnOrder.objects.filter(
            supplier=supplier,
            return_type='PURCHASE_RETURN',
            status__in=['APPROVED', 'COMPLETED'],
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_returns = total_returns.quantize(Decimal('0.01'))

        new_balance = (total_invoices - total_payments - total_returns).quantize(Decimal('0.01'))
        supplier.balance = new_balance
        supplier.save(update_fields=['balance', 'updated_at'])

        if old_balance != new_balance:
            FinancialAuditService.log_balance_sync(
                entity_type='supplier',
                entity_id=str(supplier.pk),
                balance_before=old_balance,
                balance_after=new_balance,
                user=user,
                reason='Invoice change',
            )

        return new_balance

    @staticmethod
    def sync_all(user=None) -> dict:
        """On-demand integrity check — recalculate ALL balances.

        Returns dict with counts and any discrepancies found.
        """
        from sales.models import Customer
        from purchases.models import Supplier

        customers_synced = 0
        suppliers_synced = 0
        errors = []

        with transaction.atomic():
            for customer in Customer.objects.all():
                try:
                    BalanceSyncService.sync_customer(customer, lock=False, user=user, reason='Full sync')
                    customers_synced += 1
                except Exception as e:
                    errors.append(f"Customer {customer.code}: {e}")

            for supplier in Supplier.objects.all():
                try:
                    BalanceSyncService.sync_supplier(supplier, lock=False, user=user, reason='Full sync')
                    suppliers_synced += 1
                except Exception as e:
                    errors.append(f"Supplier {supplier.code}: {e}")

        return {
            'customers_synced': customers_synced,
            'suppliers_synced': suppliers_synced,
            'errors': errors,
            'success': len(errors) == 0,
        }

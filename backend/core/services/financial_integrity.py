"""Financial Integrity Validation Service.

Lightweight, read-only validation of financial consistency across the ERP.
Checks for balance mismatches, orphaned records, overpayments, and
unbalanced journal entries.

Usage:
    FinancialIntegrityService.validate_all()
    FinancialIntegrityService.validate_customer_balances()
    FinancialIntegrityService.validate_journal_entries()
"""
from decimal import Decimal
from django.db import models
from django.db.models import Sum, Q


class FinancialIntegrityService:
    """Read-only financial integrity validator.

    All methods return structured dicts with:
    - 'ok': bool — whether the check passed
    - 'issues': list — details of any problems found
    - 'checked': int — number of records examined
    """

    @staticmethod
    def validate_all() -> dict:
        """Run all integrity checks.

        Returns:
            Dict with overall status and per-check results.
        """
        checks = {
            'customer_balances': FinancialIntegrityService.validate_customer_balances(),
            'supplier_balances': FinancialIntegrityService.validate_supplier_balances(),
            'invoice_paid_amounts': FinancialIntegrityService.validate_invoice_paid_amounts(),
            'journal_entry_balances': FinancialIntegrityService.validate_journal_entry_balances(),
            'orphaned_payments': FinancialIntegrityService.find_orphaned_payments(),
            'overpaid_invoices': FinancialIntegrityService.find_overpaid_invoices(),
            'negative_balances': FinancialIntegrityService.find_negative_balances(),
        }

        all_ok = all(c['ok'] for c in checks.values())
        total_issues = sum(len(c['issues']) for c in checks.values())

        return {
            'ok': all_ok,
            'total_issues': total_issues,
            'checks': checks,
        }

    @staticmethod
    def validate_customer_balances() -> dict:
        """Check that all customer balances match calculated values.

        Expected: balance = sum(invoices) - sum(payments)
        """
        from sales.models import Customer, SalesInvoice, CustomerPayment

        issues = []
        checked = 0

        for customer in Customer.objects.all():
            checked += 1
            total_invoices = SalesInvoice.objects.filter(
                customer=customer,
                status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
                is_active=True,
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

            total_payments = CustomerPayment.objects.filter(
                customer=customer,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            expected = total_invoices - total_payments
            if abs(customer.balance - expected) > Decimal('0.01'):
                issues.append({
                    'customer_code': customer.code,
                    'customer_name': customer.name,
                    'stored_balance': str(customer.balance),
                    'expected_balance': str(expected),
                    'difference': str(customer.balance - expected),
                    'total_invoices': str(total_invoices),
                    'total_payments': str(total_payments),
                })

        return {
            'ok': len(issues) == 0,
            'issues': issues,
            'checked': checked,
        }

    @staticmethod
    def validate_supplier_balances() -> dict:
        """Check that all supplier balances match calculated values."""
        from purchases.models import Supplier, PurchaseInvoice, SupplierPayment

        issues = []
        checked = 0

        for supplier in Supplier.objects.all():
            checked += 1
            total_invoices = PurchaseInvoice.objects.filter(
                supplier=supplier,
                status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
                is_active=True,
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

            total_payments = SupplierPayment.objects.filter(
                supplier=supplier,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            expected = total_invoices - total_payments
            if abs(supplier.balance - expected) > Decimal('0.01'):
                issues.append({
                    'supplier_code': supplier.code,
                    'supplier_name': supplier.name,
                    'stored_balance': str(supplier.balance),
                    'expected_balance': str(expected),
                    'difference': str(supplier.balance - expected),
                })

        return {
            'ok': len(issues) == 0,
            'issues': issues,
            'checked': checked,
        }

    @staticmethod
    def validate_invoice_paid_amounts() -> dict:
        """Check that invoice paid_amount matches sum of payments + allocations."""
        from sales.models import SalesInvoice, CustomerPayment, PaymentAllocation

        issues = []
        checked = 0

        for invoice in SalesInvoice.objects.filter(is_active=True):
            checked += 1
            direct_payments = CustomerPayment.objects.filter(
                invoice=invoice,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            allocated = PaymentAllocation.objects.filter(
                invoice=invoice,
            ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0.00')

            expected_paid = direct_payments + allocated
            if abs(invoice.paid_amount - expected_paid) > Decimal('0.01'):
                issues.append({
                    'invoice_number': invoice.invoice_number,
                    'stored_paid': str(invoice.paid_amount),
                    'expected_paid': str(expected_paid),
                    'difference': str(invoice.paid_amount - expected_paid),
                    'direct_payments': str(direct_payments),
                    'allocated': str(allocated),
                })

        return {
            'ok': len(issues) == 0,
            'issues': issues,
            'checked': checked,
        }

    @staticmethod
    def validate_journal_entry_balances() -> dict:
        """Check that all posted journal entries have debits == credits."""
        from accounting.models import JournalEntry

        issues = []
        checked = 0

        for je in JournalEntry.objects.filter(is_posted=True):
            checked += 1
            totals = je.lines.aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit'),
            )
            total_debit = totals['total_debit'] or Decimal('0.00')
            total_credit = totals['total_credit'] or Decimal('0.00')

            if abs(total_debit - total_credit) > Decimal('0.01'):
                issues.append({
                    'entry_number': je.entry_number,
                    'total_debit': str(total_debit),
                    'total_credit': str(total_credit),
                    'difference': str(total_debit - total_credit),
                })

        return {
            'ok': len(issues) == 0,
            'issues': issues,
            'checked': checked,
        }

    @staticmethod
    def find_orphaned_payments() -> dict:
        """Find payments with no invoice reference and no allocation."""
        from sales.models import CustomerPayment, PaymentAllocation

        orphaned = CustomerPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(
            id__in=PaymentAllocation.objects.values_list('payment_id', flat=True).distinct()
        )

        issues = []
        for p in orphaned:
            issues.append({
                'payment_id': str(p.id),
                'customer': p.customer.name,
                'amount': str(p.amount),
                'payment_date': p.payment_date.isoformat(),
                'reference': p.reference_number,
            })

        return {
            'ok': len(issues) == 0,
            'issues': issues,
            'checked': orphaned.count(),
        }

    @staticmethod
    def find_overpaid_invoices() -> dict:
        """Find invoices where paid_amount > total_amount."""
        from sales.models import SalesInvoice

        overpaid = SalesInvoice.objects.filter(
            is_active=True,
            paid_amount__gt=models.F('total_amount'),
        )

        issues = []
        for inv in overpaid:
            issues.append({
                'invoice_number': inv.invoice_number,
                'total_amount': str(inv.total_amount),
                'paid_amount': str(inv.paid_amount),
                'overpaid_by': str(inv.paid_amount - inv.total_amount),
            })

        return {
            'ok': len(issues) == 0,
            'issues': issues,
            'checked': overpaid.count(),
        }

    @staticmethod
    def find_negative_balances() -> dict:
        """Find customers/suppliers with negative balances (credit balance)."""
        from sales.models import Customer
        from purchases.models import Supplier

        issues = []

        for customer in Customer.objects.filter(balance__lt=0):
            issues.append({
                'type': 'CUSTOMER',
                'code': customer.code,
                'name': customer.name,
                'balance': str(customer.balance),
                'note': 'Customer has credit balance (overpaid)',
            })

        for supplier in Supplier.objects.filter(balance__lt=0):
            issues.append({
                'type': 'SUPPLIER',
                'code': supplier.code,
                'name': supplier.name,
                'balance': str(supplier.balance),
                'note': 'Supplier has credit balance (overpaid)',
            })

        return {
            'ok': len(issues) == 0,
            'issues': issues,
            'checked': Customer.objects.filter(balance__lt=0).count() +
                       Supplier.objects.filter(balance__lt=0).count(),
        }

    @staticmethod
    def auto_fix_customer_balances(user=None) -> dict:
        """Fix all customer balance mismatches using BalanceSyncService."""
        from core.balance_sync import BalanceSyncService
        from core.services.financial_audit import FinancialAuditService
        from sales.models import Customer

        fixed = 0
        errors = []

        for customer in Customer.objects.all():
            old_balance = customer.balance
            try:
                new_balance = BalanceSyncService.sync_customer(customer, lock=False, user=user, reason='Integrity auto-fix')
                if old_balance != new_balance:
                    FinancialAuditService.log_integrity_fix(
                        entity_type='customer',
                        entity_id=str(customer.pk),
                        balance_before=old_balance,
                        balance_after=new_balance,
                        user=user,
                        fix_type='Auto-fix customer balance',
                    )
                fixed += 1
            except Exception as e:
                errors.append(f"Customer {customer.code}: {e}")

        return {
            'fixed': fixed,
            'errors': errors,
            'success': len(errors) == 0,
        }

    @staticmethod
    def auto_fix_supplier_balances(user=None) -> dict:
        """Fix all supplier balance mismatches using BalanceSyncService."""
        from core.balance_sync import BalanceSyncService
        from core.services.financial_audit import FinancialAuditService
        from purchases.models import Supplier

        fixed = 0
        errors = []

        for supplier in Supplier.objects.all():
            old_balance = supplier.balance
            try:
                new_balance = BalanceSyncService.sync_supplier(supplier, lock=False, user=user, reason='Integrity auto-fix')
                if old_balance != new_balance:
                    FinancialAuditService.log_integrity_fix(
                        entity_type='supplier',
                        entity_id=str(supplier.pk),
                        balance_before=old_balance,
                        balance_after=new_balance,
                        user=user,
                        fix_type='Auto-fix supplier balance',
                    )
                fixed += 1
            except Exception as e:
                errors.append(f"Supplier {supplier.code}: {e}")

        return {
            'fixed': fixed,
            'errors': errors,
            'success': len(errors) == 0,
        }

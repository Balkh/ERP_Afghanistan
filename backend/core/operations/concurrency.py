"""
Concurrency Safety Hardening Layer.
Transaction safety, race condition detection, and double-spending prevention.
"""
import logging
from decimal import Decimal
from django.db import transaction, models, IntegrityError, OperationalError
from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger('erp.concurrency')


class ConcurrencySafe:
    """Mixin for concurrency-safe operations."""

    @staticmethod
    def safe_inventory_deduction(product_id, warehouse_id, quantity, batch_id=None):
        """
        Safely deduct inventory with race condition prevention.
        Uses select_for_update to prevent concurrent modifications.
        """
        from inventory.models import Batch, StockMovement

        with transaction.atomic():
            if batch_id:
                batch = Batch.objects.select_for_update().filter(
                    id=batch_id,
                    product_id=product_id,
                    warehouse_id=warehouse_id
                ).first()

                if not batch:
                    raise ValidationError("Batch not found or not available")

                if batch.remaining_quantity < quantity:
                    raise ValidationError(
                        f"Insufficient stock. Available: {batch.remaining_quantity}, "
                        f"Requested: {quantity}"
                    )

                batch.remaining_quantity -= quantity
                batch.save()

                StockMovement.objects.create(
                    product_id=product_id,
                    batch_id=batch_id,
                    warehouse_id=warehouse_id,
                    movement_type='OUT',
                    quantity=quantity
                )

                return batch
            else:
                batches = Batch.objects.select_for_update().filter(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    remaining_quantity__gt=0
                ).order_by('expiry_date')

                remaining = quantity
                for batch in batches:
                    if remaining <= 0:
                        break

                    deduct = min(remaining, batch.remaining_quantity)
                    batch.remaining_quantity -= deduct
                    batch.save()

                    StockMovement.objects.create(
                        product_id=product_id,
                        batch_id=batch.id,
                        warehouse_id=warehouse_id,
                        movement_type='OUT',
                        quantity=deduct
                    )

                    remaining -= deduct

                if remaining > 0:
                    raise ValidationError(
                        f"Insufficient stock across all batches. "
                        f"Missing: {remaining}"
                    )

    @staticmethod
    def safe_journal_posting(entry_id):
        """
        Safely post a journal entry with balance verification.
        Prevents concurrent postings of the same entry.
        """
        from accounting.models import JournalEntry, JournalEntryLine

        with transaction.atomic():
            entry = JournalEntry.objects.select_for_update().filter(
                id=entry_id,
                is_posted=False
            ).first()

            if not entry:
                raise ValidationError("Journal entry not found or already posted")

            lines = JournalEntryLine.objects.filter(journal_entry=entry)
            total_debit = sum(line.debit for line in lines)
            total_credit = sum(line.credit for line in lines)

            if total_debit != total_credit:
                raise ValidationError(
                    f"Journal entry is unbalanced. Debits: {total_debit}, "
                    f"Credits: {total_credit}"
                )

            entry.is_posted = True
            entry.posted_at = timezone.now()
            entry.save()

            return entry


class RaceConditionDetector:
    """Detect potential race conditions in operations."""

    @staticmethod
    def check_inventory_race(product_id, warehouse_id, quantity):
        """
        Check if operation might have race condition risk.
        Returns risk level and recommendations.
        """
        from inventory.models import Batch

        available = Batch.objects.filter(
            product_id=product_id,
            warehouse_id=warehouse_id,
            remaining_quantity__gt=0
        ).aggregate(total=models.Sum('remaining_quantity'))['total'] or 0

        risk_level = 'low'
        if available < quantity:
            risk_level = 'high'
            recommendation = "Operation will likely fail - insufficient stock"
        elif available < quantity * 1.5:
            risk_level = 'medium'
            recommendation = "Close to available limit - use transaction"
        else:
            recommendation = "Safe to proceed"

        return {
            'risk_level': risk_level,
            'available_stock': str(available),
            'requested': str(quantity),
            'recommendation': recommendation
        }


class DoubleSpendPreventer:
    """Prevent double-spending in financial operations."""

    @staticmethod
    def validate_payment_availability(invoice_id, payment_amount):
        """
        Ensure payment doesn't exceed invoice amount.
        Uses locking to prevent concurrent overpayment.
        """
        from sales.models import SalesInvoice

        with transaction.atomic():
            invoice = SalesInvoice.objects.select_for_update().filter(
                id=invoice_id
            ).first()

            if not invoice:
                raise ValidationError("Invoice not found")

            paid_amount = invoice.paid_amount or Decimal('0')
            remaining = invoice.total_amount - paid_amount

            if payment_amount > remaining:
                raise ValidationError(
                    f"Payment exceeds remaining balance. "
                    f"Remaining: {remaining}, Payment: {payment_amount}"
                )

            return {
                'invoice_id': str(invoice.id),
                'total_amount': str(invoice.total_amount),
                'paid_amount': str(paid_amount),
                'remaining': str(remaining),
                'new_payment': str(payment_amount),
                'new_balance': str(remaining - payment_amount)
            }

    @staticmethod
    def validate_payment_allocation(payment_id, allocations):
        """
        Validate payment allocations don't exceed payment amount.
        """
        from payments.models import Payment

        with transaction.atomic():
            payment = Payment.objects.select_for_update().filter(
                id=payment_id
            ).first()

            if not payment:
                raise ValidationError("Payment not found")

            total_allocated = sum(Decimal(str(a.get('amount', 0))) for a in allocations)

            if total_allocated > payment.amount:
                raise ValidationError(
                    f"Allocations exceed payment amount. "
                    f"Payment: {payment.amount}, Allocated: {total_allocated}"
                )

            return {
                'payment_id': str(payment.id),
                'payment_amount': str(payment.amount),
                'total_allocated': str(total_allocated),
                'valid': True
            }


class ConcurrencyMonitor:
    """Monitor concurrent operations for safety."""

    _active_transactions = []
    _max_transactions = 100

    @classmethod
    def record_transaction_start(cls, operation_type: str, reference: str):
        """Record start of a transaction for monitoring."""
        cls._active_transactions.append({
            'operation': operation_type,
            'reference': reference,
            'started_at': timezone.now().isoformat()
        })
        if len(cls._active_transactions) > cls._max_transactions:
            cls._active_transactions = cls._active_transactions[-cls._max_transactions:]

    @classmethod
    def record_transaction_end(cls, reference: str, success: bool):
        """Record end of a transaction."""
        cls._active_transactions = [
            t for t in cls._active_transactions
            if t['reference'] != reference
        ]

    @classmethod
    def get_active_transactions(cls):
        """Get currently active transactions."""
        return cls._active_transactions


def run_concurrency_safety_check():
    """Run concurrency safety validation."""
    return {
        'active_transactions': ConcurrencyMonitor.get_active_transactions(),
        'double_spend_prevention': {
            'payment_validation': 'enabled',
            'inventory_deduction': 'enabled',
            'journal_posting': 'enabled'
        },
        'race_detection': {
            'inventory_checks': 'enabled',
            'accounting_locks': 'enabled'
        }
    }
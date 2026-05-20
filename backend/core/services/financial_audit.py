"""Financial Audit Service.

Lightweight audit logging for all financial events: balance syncs, credit
overrides, integrity fixes, FIFO allocations, and payment adjustments.
Uses the existing AuditTrail model with financial-specific action types.
"""
from typing import Optional, Dict, Any
from django.utils import timezone
from audit.services.audit_service import AuditService


FINANCIAL_ACTIONS = [
    'BALANCE_SYNC',
    'CREDIT_OVERRIDE',
    'CREDIT_BLOCK',
    'INTEGRITY_FIX',
    'FIFO_ALLOCATE',
    'PAYMENT_ADJUST',
    'RETURN_VOID',
    'REFUND_PROCESS',
    # FCUE Phase 16 events
    'RECONCILIATION_MISMATCH',
    'CREDIT_POLICY_BLOCK',
    'ALLOCATION_AUTO',
    'BALANCE_DERIVED',
    # Ledger Purification Phase 19
    'JOURNAL_CREATE',
    'JOURNAL_POST',
    'JOURNAL_REVERSE',
]

# Maximum number of audit log entries per event type (bounded retention)
MAX_LOG_ENTRIES = 100_000


class FinancialAuditService:
    """Structured audit logging for financial events."""

    APP_LABEL = 'core'
    MODEL_NAME = 'financial_event'

    @classmethod
    def log_balance_sync(cls, entity_type: str, entity_id: str,
                         balance_before, balance_after, user=None,
                         reason: str = ''):
        """Log a balance synchronization event."""
        AuditService.log(
            user=user,
            action='BALANCE_SYNC',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(entity_id),
            object_repr=f'{entity_type.title()} balance sync: {entity_id} ({balance_before} -> {balance_after})',
            old_values={'balance': str(balance_before), 'entity_type': entity_type},
            new_values={'balance': str(balance_after), 'reason': reason or 'Automatic reconciliation'},
        )

    @classmethod
    def log_credit_override(cls, customer_id: str, customer_name: str,
                            credit_limit, current_balance, invoice_amount,
                            user=None):
        """Log a credit limit override (proceeding despite warning)."""
        utilization = (current_balance / credit_limit * 100) if credit_limit > 0 else 0
        AuditService.log(
            user=user,
            action='CREDIT_OVERRIDE',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(customer_id),
            object_repr=f'Credit override: {customer_name} ({utilization:.1f}%)',
            old_values={'credit_limit': str(credit_limit), 'balance': str(current_balance)},
            new_values={'invoice_amount': str(invoice_amount), 'customer_name': customer_name},
        )

    @classmethod
    def log_credit_block(cls, customer_id: str, customer_name: str,
                         credit_limit, current_balance, invoice_amount,
                         user=None):
        """Log a blocked transaction due to credit limit."""
        AuditService.log(
            user=user,
            action='CREDIT_BLOCK',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(customer_id),
            object_repr=f'Credit blocked: {customer_name}',
            old_values={'credit_limit': str(credit_limit), 'balance': str(current_balance)},
            new_values={'attempted_amount': str(invoice_amount), 'customer_name': customer_name},
        )

    @classmethod
    def log_integrity_fix(cls, entity_type: str, entity_id: str,
                          balance_before, balance_after, user=None,
                          fix_type: str = ''):
        """Log an automatic integrity fix."""
        AuditService.log(
            user=user,
            action='INTEGRITY_FIX',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(entity_id),
            object_repr=f'Integrity fix: {entity_type} {entity_id} ({balance_before} -> {balance_after})',
            old_values={'balance': str(balance_before), 'entity_type': entity_type},
            new_values={'balance': str(balance_after), 'fix_type': fix_type or 'Balance recalculation'},
        )

    @classmethod
    def log_fifo_allocation(cls, payment_id: str, invoice_id: str,
                            amount, user=None):
        """Log a FIFO payment allocation."""
        AuditService.log(
            user=user,
            action='FIFO_ALLOCATE',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(payment_id),
            object_repr=f'FIFO allocation: Payment {payment_id} -> Invoice {invoice_id} ({amount})',
            old_values={},
            new_values={'allocated_amount': str(amount), 'invoice_id': str(invoice_id), 'payment_id': str(payment_id)},
        )

    @classmethod
    def log_payment_adjust(cls, payment_id: str, amount_before, amount_after,
                           user=None, reason: str = ''):
        """Log a payment amount adjustment."""
        AuditService.log(
            user=user,
            action='PAYMENT_ADJUST',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(payment_id),
            object_repr=f'Payment adjustment: {payment_id} ({amount_before} -> {amount_after})',
            old_values={'amount': str(amount_before)},
            new_values={'amount': str(amount_after), 'reason': reason},
        )

    @classmethod
    def log_return_void(cls, return_id: str, entity_type: str, entity_id: str,
                        balance_before, balance_after, user=None):
        """Log a return order void that affects balances."""
        AuditService.log(
            user=user,
            action='RETURN_VOID',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(return_id),
            object_repr=f'Return void: {return_id} ({balance_before} -> {balance_after})',
            old_values={'balance': str(balance_before), 'entity_type': entity_type},
            new_values={'balance': str(balance_after), 'entity_id': str(entity_id)},
        )

    @classmethod
    def log_reconciliation_mismatch(cls, entity_type: str, entity_id: str,
                                    mismatch_type: str, detail: str,
                                    user=None):
        """Log a reconciliation mismatch detected by the Payment Reconciliation Engine."""
        AuditService.log(
            user=user,
            action='RECONCILIATION_MISMATCH',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(entity_id),
            object_repr=f'Reconciliation mismatch: {mismatch_type} on {entity_type} {entity_id}',
            old_values={},
            new_values={
                'entity_type': entity_type,
                'mismatch_type': mismatch_type,
                'detail': detail,
            },
        )

    @classmethod
    def log_credit_policy_block(cls, party_type: str, party_id: str,
                                 party_name: str, invoice_amount, reason: str,
                                 user=None):
        """Log a credit policy block from the central CreditPolicyEngine."""
        AuditService.log(
            user=user,
            action='CREDIT_POLICY_BLOCK',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(party_id),
            object_repr=f'Credit policy block: {party_name} ({party_type})',
            old_values={},
            new_values={
                'party_type': party_type,
                'party_name': party_name,
                'attempted_amount': str(invoice_amount),
                'reason': reason,
            },
        )

    @classmethod
    def log_allocation_auto(cls, payment_id: str, entity_type: str,
                             entity_id: str, amount, user=None):
        """Log an automatic FIFO allocation during payment creation."""
        AuditService.log(
            user=user,
            action='ALLOCATION_AUTO',
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(payment_id),
            object_repr=f'Auto-allocation: Payment {payment_id} allocated to {entity_type} {entity_id} ({amount})',
            old_values={},
            new_values={
                'payment_id': str(payment_id),
                'entity_type': entity_type,
                'entity_id': str(entity_id),
                'amount': str(amount),
            },
        )

    @classmethod
    def log_journal_entry(
        cls,
        entry_id: str,
        entry_type: str,
        action: str,
        entity_type: str = '',
        entity_id: str = '',
        reference: str = '',
        transaction_id: str = '',
        reason: str = '',
        user=None,
        company=None,
    ):
        """Log a journal entry lifecycle event (create, post, reverse).

        Args:
            entry_id: UUID of the journal entry
            entry_type: Type of entry (SALE, PURCHASE, EXPENSE, etc.)
            action: One of 'JOURNAL_CREATE', 'JOURNAL_POST', 'JOURNAL_REVERSE'
            entity_type: Originating entity type (e.g., 'SalesInvoice')
            entity_id: Originating entity ID
            reference: External reference number
            transaction_id: Atomic transaction ID for traceability
            reason: Reason for the action (especially for reversals)
            user: User performing the action
            company: Company context

        Returns:
            Audit log record ID (for traceability)
        """
        object_repr = f'Journal {action}: {entry_type} {entry_id}'
        if reference:
            object_repr += f' (ref: {reference})'
        if entity_type:
            object_repr += f' [{entity_type}:{entity_id}]'

        AuditService.log(
            user=user,
            action=action,
            app_label=cls.APP_LABEL,
            model_name=cls.MODEL_NAME,
            object_id=str(entry_id),
            object_repr=object_repr,
            old_values={},
            new_values={
                'entry_type': entry_type,
                'entity_type': entity_type,
                'entity_id': str(entity_id),
                'reference': reference,
                'transaction_id': transaction_id,
                'reason': reason,
            },
        )

    @staticmethod
    def enforce_log_retention():
        """Enforce bounded retention by trimming oldest logs beyond MAX_LOG_ENTRIES.
        
        Designed for on-demand or scheduled calls — never runs inline.
        """
        from audit.models import AuditTrail
        for action in FINANCIAL_ACTIONS:
            count = AuditTrail.objects.filter(action=action).count()
            if count > MAX_LOG_ENTRIES:
                to_delete = count - MAX_LOG_ENTRIES
                oldest_ids = AuditTrail.objects.filter(
                    action=action
                ).order_by('created_at').values_list('id', flat=True)[:to_delete]
                AuditTrail.objects.filter(id__in=list(oldest_ids)).delete()

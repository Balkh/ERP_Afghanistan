"""Journal Gateway — mandatory enforcement layer for all financial operations.

This is the SINGLE PATH through which ALL financial state changes must flow.
No module may bypass this gateway to create, post, or reverse journal entries.

Rules:
1. All journal entry creation goes through JournalGateway.create_entry()
2. All journal entry posting goes through JournalGateway.post_entry()
3. All journal entry reversal goes through JournalGateway.reverse_entry()
4. If any operation fails, the entire transaction rolls back
5. Every operation produces an audit trace with entity reference and transaction ID

This is NOT a new architecture — it is a logical enforcement wrapper around JournalEngine.
"""
import logging
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounting.models import JournalEntry, JournalEntryLine, Account
from accounting.services.journal_engine import JournalEngine
from core.services.financial_audit import FinancialAuditService
from accounting.models import is_period_locked, get_open_period_for_date

logger = logging.getLogger('erp.journal_gateway')


class JournalGateway:
    """Mandatory gateway for all journal entry operations.

    All financial modules MUST use this gateway instead of calling JournalEngine directly.
    This ensures:
    - Consistent validation before entry creation
    - Atomic transaction boundaries
    - Structured audit logging
    - No partial financial states
    """

    @classmethod
    @transaction.atomic
    def create_entry(
        cls,
        entry_type: str,
        description: str,
        lines: List[Dict[str, Any]],
        entry_date=None,
        reference: str = '',
        auto_post: bool = False,
        entity_type: str = '',
        entity_id: str = '',
        company=None,
    ) -> Dict[str, Any]:
        """Create a journal entry through the enforced gateway.

        Args:
            entry_type: Type of entry (SALE, PURCHASE, EXPENSE, RECEIPT, PAYMENT, etc.)
            description: Human-readable description
            lines: List of line dicts with account_code, debit, credit, description
            entry_date: Date of the entry (defaults to today)
            reference: External reference number
            auto_post: If True, automatically post the entry
            entity_type: Type of originating entity (e.g., 'SalesInvoice', 'Expense')
            entity_id: ID of originating entity
            company: Company context (for multi-tenant)

        Returns:
            Dict with 'success', 'entry_id', 'entry_number', 'audit_id'

        Raises:
            ValidationError: If validation fails or entry creation fails
        """
        transaction_id = str(uuid.uuid4())

        cls._validate_lines(lines)
        cls._validate_double_entry(lines)

        if not entry_date:
            entry_date = timezone.now().date()

        if is_period_locked(entry_date):
            period = get_open_period_for_date(entry_date)
            period_info = f' (period: {period.code})' if period else ''
            raise ValidationError(
                f'Cannot create journal entry in a locked/closed period{period_info}. '
                f'Date: {entry_date}. Transaction ID: {transaction_id}'
            )

        result = JournalEngine.create_entry(
            entry_type=entry_type,
            description=description,
            lines=lines,
            entry_date=entry_date,
            reference=reference,
            auto_post=auto_post,
        )

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            logger.error(
                f'[JOURNAL_GATEWAY] Entry creation failed: {error_msg}. '
                f'Transaction ID: {transaction_id}, Type: {entry_type}, '
                f'Entity: {entity_type}:{entity_id}'
            )
            raise ValidationError(
                f'Journal entry creation failed: {error_msg}. '
                f'Transaction ID: {transaction_id}'
            )

        entry_id = result.get('entry_id')
        entry_number = result.get('entry_number', '')

        audit_id = FinancialAuditService.log_journal_entry(
            entry_id=entry_id,
            entry_type=entry_type,
            entity_type=entity_type,
            entity_id=entity_id,
            reference=reference,
            transaction_id=transaction_id,
            action='created',
            company=company,
        )

        logger.info(
            f'[JOURNAL_GATEWAY] Entry created: {entry_number} '
            f'(ID: {entry_id}, Txn: {transaction_id}, Audit: {audit_id})'
        )

        return {
            'success': True,
            'entry_id': entry_id,
            'entry_number': entry_number,
            'transaction_id': transaction_id,
            'audit_id': audit_id,
        }

    @classmethod
    @transaction.atomic
    def post_entry(cls, entry_id: str, posted_by: str = '') -> Dict[str, Any]:
        """Post a journal entry through the enforced gateway.

        Args:
            entry_id: UUID of the journal entry to post
            posted_by: User performing the post

        Returns:
            Dict with 'success', 'entry_id', 'transaction_id', 'audit_id'

        Raises:
            ValidationError: If posting fails
        """
        transaction_id = str(uuid.uuid4())

        try:
            entry = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            raise ValidationError(f'Journal entry {entry_id} not found.')

        if entry.is_posted:
            raise ValidationError(f'Journal entry {entry.entry_number} is already posted.')

        if is_period_locked(entry.entry_date):
            period = get_open_period_for_date(entry.entry_date)
            period_info = f' (period: {period.code})' if period else ''
            raise ValidationError(
                f'Cannot post journal entry in a locked/closed period{period_info}. '
                f'Entry: {entry.entry_number}, Date: {entry.entry_date}'
            )

        result = JournalEngine.post_entry(entry_id=entry_id)

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            logger.error(
                f'[JOURNAL_GATEWAY] Entry posting failed: {error_msg}. '
                f'Entry: {entry.entry_number}, Txn: {transaction_id}'
            )
            raise ValidationError(
                f'Journal entry posting failed: {error_msg}. '
                f'Transaction ID: {transaction_id}'
            )

        audit_id = FinancialAuditService.log_journal_entry(
            entry_id=entry_id,
            entry_type=entry.entry_type,
            entity_type='',
            entity_id='',
            reference=entry.reference,
            transaction_id=transaction_id,
            action='posted',
            user=posted_by,
        )

        logger.info(
            f'[JOURNAL_GATEWAY] Entry posted: {entry.entry_number} '
            f'(Txn: {transaction_id}, Audit: {audit_id})'
        )

        return {
            'success': True,
            'entry_id': entry_id,
            'transaction_id': transaction_id,
            'audit_id': audit_id,
        }

    @classmethod
    @transaction.atomic
    def reverse_entry(
        cls,
        entry_id: str,
        reason: str = '',
        reversed_by: str = '',
        entity_type: str = '',
        entity_id: str = '',
        company=None,
    ) -> Dict[str, Any]:
        """Reverse a journal entry through the enforced gateway.

        Args:
            entry_id: UUID of the journal entry to reverse
            reason: Reason for reversal
            reversed_by: User performing the reversal
            entity_type: Type of originating entity
            entity_id: ID of originating entity
            company: Company context

        Returns:
            Dict with 'success', 'reversal_entry_id', 'transaction_id', 'audit_id'

        Raises:
            ValidationError: If reversal fails
        """
        transaction_id = str(uuid.uuid4())

        try:
            entry = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            raise ValidationError(f'Journal entry {entry_id} not found.')

        if not entry.is_posted:
            raise ValidationError(
                f'Journal entry {entry.entry_number} must be posted before reversal.'
            )

        if is_period_locked(entry.entry_date):
            period = get_open_period_for_date(entry.entry_date)
            period_info = f' (period: {period.code})' if period else ''
            raise ValidationError(
                f'Cannot reverse journal entry in a locked/closed period{period_info}. '
                f'Entry: {entry.entry_number}, Date: {entry.entry_date}'
            )

        result = JournalEngine.reverse_entry(entry_id=entry_id)

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            logger.error(
                f'[JOURNAL_GATEWAY] Entry reversal failed: {error_msg}. '
                f'Entry: {entry.entry_number}, Txn: {transaction_id}, Reason: {reason}'
            )
            raise ValidationError(
                f'Journal entry reversal failed: {error_msg}. '
                f'Transaction ID: {transaction_id}'
            )

        reversal_entry_id = result.get('reversal_entry_id')

        audit_id = FinancialAuditService.log_journal_entry(
            entry_id=reversal_entry_id,
            entry_type='REVERSAL',
            entity_type=entity_type,
            entity_id=entity_id,
            reference=f'REV-{entry.reference}',
            transaction_id=transaction_id,
            action='reversed',
            reason=reason,
            user=reversed_by,
            company=company,
        )

        logger.info(
            f'[JOURNAL_GATEWAY] Entry reversed: {entry.entry_number} -> {reversal_entry_id} '
            f'(Txn: {transaction_id}, Audit: {audit_id}, Reason: {reason})'
        )

        return {
            'success': True,
            'entry_id': entry_id,
            'reversal_entry_id': reversal_entry_id,
            'transaction_id': transaction_id,
            'audit_id': audit_id,
        }

    @classmethod
    def validate_entry(
        cls,
        entry_type: str,
        lines: List[Dict[str, Any]],
    ) -> List[str]:
        """Validate a journal entry without creating it.

        Args:
            entry_type: Type of entry
            lines: List of line dicts

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            cls._validate_lines(lines)
        except ValidationError as e:
            errors.append(str(e))

        try:
            cls._validate_double_entry(lines)
        except ValidationError as e:
            errors.append(str(e))

        return errors

    @classmethod
    def _validate_lines(cls, lines: List[Dict[str, Any]]) -> None:
        """Validate line structure and account existence.

        Raises:
            ValidationError: If lines are invalid
        """
        if not lines:
            raise ValidationError('Journal entry must have at least one line.')

        for i, line in enumerate(lines):
            if 'account_code' not in line:
                raise ValidationError(f'Line {i + 1}: missing account_code.')

            account = Account.objects.filter(code=line['account_code'], is_active=True).first()
            if not account:
                raise ValidationError(
                    f'Line {i + 1}: account code "{line["account_code"]}" not found or inactive.'
                )

            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))

            if debit < 0 or credit < 0:
                raise ValidationError(
                    f'Line {i + 1}: debit and credit must be non-negative.'
                )

            if debit == 0 and credit == 0:
                raise ValidationError(
                    f'Line {i + 1}: at least one of debit or credit must be non-zero.'
                )

    @classmethod
    def _validate_double_entry(cls, lines: List[Dict[str, Any]]) -> None:
        """Validate that total debits equal total credits.

        Raises:
            ValidationError: If double-entry rule is violated
        """
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')

        for line in lines:
            total_debit += Decimal(str(line.get('debit', 0)))
            total_credit += Decimal(str(line.get('credit', 0)))

        if total_debit != total_credit:
            raise ValidationError(
                f'Double-entry violation: total debits ({total_debit}) != '
                f'total credits ({total_credit}). Difference: {abs(total_debit - total_credit)}'
            )

    @classmethod
    def get_entry_trace(cls, entry_id: str) -> Dict[str, Any]:
        """Get full audit trace for a journal entry.

        Args:
            entry_id: UUID of the journal entry

        Returns:
            Dict with entry details, lines, and audit history
        """
        try:
            entry = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            return {'error': f'Journal entry {entry_id} not found.'}

        lines = JournalEntryLine.objects.filter(entry=entry).values(
            'id', 'account__code', 'account__name', 'debit', 'credit', 'description'
        )

        return {
            'entry_id': str(entry.id),
            'entry_number': entry.entry_number,
            'entry_type': entry.entry_type,
            'entry_date': str(entry.entry_date),
            'description': entry.description,
            'reference': entry.reference,
            'is_posted': entry.is_posted,
            'posted_at': str(entry.posted_at) if entry.posted_at else None,
            'total_debit': entry.total_debit,
            'total_credit': entry.total_credit,
            'lines': list(lines),
        }

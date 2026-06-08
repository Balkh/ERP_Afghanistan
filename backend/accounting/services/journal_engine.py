from decimal import Decimal
from datetime import date
from typing import Optional
from django.db import transaction, IntegrityError
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine, JournalEventLog
from accounting.services.journal_validators import validate_lines, generate_entry_number
from accounting.services.journal_calculators import (
    compute_account_balance,
    compute_opening_balance,
    apply_running_delta,
    compute_inverse_balance_delta,
)
from accounting.services.journal_mappers import format_ledger_entry


class AccountingError(Exception):
    """Raised when an accounting operation fails and MUST be handled."""
    pass


class JournalEngine:
    """
    Double-entry accounting engine.
    
    Handles:
    - Journal entry creation with validation
    - Debit/credit balance enforcement
    - Posting and unposting logic
    - Entry reversal
    - Account balance updates
    - Automatic entry numbering
    - Audit trail
    """

    @staticmethod
    def generate_entry_number(entry_type: str = 'GENERAL') -> str:
        """
        Generate a unique journal entry number.
        Format: JE-{YEAR}{MONTH}-{SEQUENCE}-{TYPE}
        """
        return generate_entry_number(entry_type)

    @staticmethod
    def validate_lines(lines: list[dict]) -> list[str]:
        """
        Validate journal entry lines.
        Returns list of validation error messages.
        """
        return validate_lines(lines)

    @staticmethod
    def create_entry(
        entry_type: str,
        description: str,
        lines: list[dict],
        entry_date: Optional[date] = None,
        reference: str = '',
        entry_number: Optional[str] = None,
        auto_post: bool = False,
        source_module: str = '',
        source_document: str = '',
        change_reason: str = '',
        created_by: Optional[int] = None,
    ) -> dict:
        """
        Create a new journal entry with double-entry validation and full audit trail.
        Retries on IntegrityError (duplicate entry_number) with fresh number generation.
        """
        if entry_date is None:
            entry_date = django_timezone.now().date()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    if not entry_number:
                        entry_number = JournalEngine.generate_entry_number(entry_type)

                    validation_errors = JournalEngine.validate_lines(lines)

                    if JournalEntry.objects.filter(entry_number=entry_number).exists():
                        validation_errors.append(f"Entry number {entry_number} already exists.")

                    if validation_errors:
                        return {'success': False, 'errors': validation_errors}

                    total_debit = Decimal('0.00')
                    total_credit = Decimal('0.00')

                    entry = JournalEntry.objects.create(
                        entry_number=entry_number,
                        entry_date=entry_date,
                        entry_type=entry_type,
                        description=description,
                        reference=reference,
                        is_posted=auto_post,
                        source_module=source_module,
                        source_document=source_document,
                        change_reason=change_reason,
                        created_by_id=created_by,
                    )

                    for line_data in lines:
                        account = None
                        if 'account_id' in line_data:
                            account = Account.objects.select_for_update().get(id=line_data['account_id'])
                        elif 'account_code' in line_data:
                            account = Account.objects.select_for_update().get(code=line_data['account_code'])

                        debit = Decimal(str(line_data.get('debit', 0)))
                        credit = Decimal(str(line_data.get('credit', 0)))

                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=account,
                            debit=debit,
                            credit=credit,
                            description=line_data.get('description', ''),
                            created_by_id=created_by,
                        )

                        total_debit += debit
                        total_credit += credit

                    # Log creation event
                    JournalEventLog.objects.create(
                        entry=entry,
                        event_type='CREATED',
                        user_id=created_by,
                        notes=change_reason or f'Entry created: {entry_number}',
                    )

                    if auto_post:
                        JournalEngine.update_account_balances(entry)
                        entry.is_posted = True
                        entry.posted_by_id = created_by
                        entry.save(update_fields=['is_posted', 'posted_by', 'updated_at'])
                        JournalEventLog.objects.create(
                            entry=entry,
                            event_type='POSTED',
                            user_id=created_by,
                            notes='Auto-posted on creation',
                        )

                    return {
                        'success': True,
                        'entry_id': str(entry.id),
                        'entry_number': entry.entry_number,
                        'total_debit': total_debit,
                        'total_credit': total_credit,
                    }
            except IntegrityError:
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'errors': [f'Failed to create entry after {max_retries} attempts due to a database conflict.']
                    }
                # Force fresh entry_number on retry
                entry_number = None
                continue

        return {'success': False, 'errors': ['Failed to create journal entry.']}

    @staticmethod
    def log_event(
        entry: JournalEntry,
        event_type: str,
        user_id: Optional[int] = None,
        reference: str = '',
        notes: str = '',
        ip_address: str = ''
    ) -> JournalEventLog:
        """
        Centralized helper to log a journal event.
        Use this for all event logging to ensure consistency.
        """
        return JournalEventLog.objects.create(
            entry=entry,
            event_type=event_type,
            user_id=user_id,
            reference=reference,
            notes=notes,
            ip_address=ip_address,
        )

    @staticmethod
    @transaction.atomic
    def post_entry(entry_id, posted_by: Optional[int] = None) -> dict:
        """Post a journal entry, locking it and updating account balances."""
        from accounting.models import is_period_locked

        try:
            entry = JournalEntry.objects.select_for_update().get(id=entry_id)
        except JournalEntry.DoesNotExist:
            return {'success': False, 'errors': ['Journal entry not found']}

        if entry.is_posted:
            return {'success': False, 'errors': ['Entry is already posted']}

        if is_period_locked(entry.entry_date):
            return {'success': False, 'errors': [f'Cannot post entry: the fiscal period for {entry.entry_date} is locked.']}

        if not entry.is_balanced:
            return {
                'success': False,
                'errors': [f'Cannot post unbalanced entry. Debits: {entry.total_debit:.2f}, Credits: {entry.total_credit:.2f}']
            }

        entry.is_posted = True
        entry.posted_by_id = posted_by
        entry.save(update_fields=['is_posted', 'posted_by', 'updated_at'])

        JournalEngine.update_account_balances(entry)

        JournalEngine.log_event(
            entry=entry,
            event_type='POSTED',
            user_id=posted_by,
            notes='Entry posted',
        )

        return {
            'success': True,
            'message': 'Journal entry posted successfully',
            'entry_id': str(entry.id),
        }

    @staticmethod
    @transaction.atomic
    def unpost_entry(entry_id, user_id: Optional[int] = None) -> dict:
        """Unpost a journal entry, reverting account balance changes."""
        from accounting.models import is_period_locked

        try:
            entry = JournalEntry.objects.select_for_update().get(id=entry_id)
        except JournalEntry.DoesNotExist:
            return {'success': False, 'errors': ['Journal entry not found']}

        if not entry.is_posted:
            return {'success': False, 'errors': ['Entry is not posted']}

        if is_period_locked(entry.entry_date):
            return {'success': False, 'errors': [f'Cannot unpost entry: the fiscal period for {entry.entry_date} is locked.']}

        entry.is_posted = False
        entry.save(update_fields=['is_posted', 'updated_at'])

        JournalEngine._inverse_update_balances(entry)

        JournalEngine.log_event(
            entry=entry,
            event_type='UNPOSTED',
            user_id=user_id,
            notes='Entry unposted',
        )

        return {
            'success': True,
            'message': 'Journal entry unposted successfully',
            'entry_id': str(entry.id),
        }

    @staticmethod
    @transaction.atomic
    def reverse_entry(entry_id, reason: str = '', user_id: Optional[int] = None) -> dict:
        """Reverse a posted journal entry by creating an opposite entry."""
        from accounting.models import is_period_locked

        try:
            original = JournalEntry.objects.select_for_update().get(id=entry_id)
        except JournalEntry.DoesNotExist:
            return {'success': False, 'errors': ['Original journal entry not found']}

        if not original.is_posted:
            return {'success': False, 'errors': ['Cannot reverse an unposted entry']}

        if is_period_locked(original.entry_date):
            return {'success': False, 'errors': [f'Cannot reverse entry: the fiscal period for {original.entry_date} is locked.']}

        if original.is_reversed:
            return {'success': False, 'errors': ['Entry has already been reversed']}

        reversed_lines = []
        for line in original.lines.all():
            reversed_lines.append({
                'account_id': line.account_id,
                'debit': line.credit,
                'credit': line.debit,
                'description': f"Reversal: {line.description}"
            })

        reversal_number = f"REV-{original.entry_number}"

        # Log reversal event on original BEFORE creating reversal entry
        JournalEngine.log_event(
            entry=original,
            event_type='REVERSED',
            user_id=user_id,
            notes=f'Reversed by entry {reversal_number}: {reason}',
            reference=reversal_number,
        )

        result = JournalEngine.create_entry(
            entry_type='REVERSAL',
            description=f"Reversal of {original.entry_number}: {reason or original.description}",
            lines=reversed_lines,
            entry_date=django_timezone.now().date(),
            reference=original.reference,
            entry_number=reversal_number,
            auto_post=True,
            source_module='accounting',
            source_document=str(original.id),
            change_reason=f'Reversal: {reason}',
            created_by=user_id,
        )

        if result.get('success'):
            reversal_entry = JournalEntry.objects.get(id=result['entry_id'])
            reversal_entry.reversed_by_entry = original
            reversal_entry.save(update_fields=['reversed_by_entry', 'updated_at'])

        return result

    @staticmethod
    @transaction.atomic
    def update_account_balances(entry: JournalEntry):
        """Update account balances based on a posted journal entry with row-level locking."""
        for line in entry.lines.all():
            account = Account.objects.select_for_update().get(id=line.account.id)
            balance = compute_account_balance(account)
            Account.objects.filter(id=account.id).update(balance=balance)

    @staticmethod
    @transaction.atomic
    def _inverse_update_balances(entry: JournalEntry):
        """Inverse update: subtract this entry's amounts from account balances (for unpost)."""
        for line in entry.lines.all():
            account = Account.objects.select_for_update().get(id=line.account.id)
            delta = compute_inverse_balance_delta(account, line.debit, line.credit)
            new_balance = account.balance + delta
            Account.objects.filter(id=account.id).update(balance=new_balance)

    @staticmethod
    def recalculate_all_balances():
        """Recalculate balances for all accounts from posted journal entries."""
        accounts = Account.objects.filter(is_active=True)

        for account in accounts:
            balance = compute_account_balance(account)
            Account.objects.filter(id=account.id).update(balance=balance)

    @staticmethod
    def get_account_ledger(account_id, start_date=None, end_date=None):
        """Get ledger for an account with running balance."""
        lines = JournalEntryLine.objects.filter(
            account_id=account_id, entry__is_posted=True, entry__is_active=True
        ).select_related('entry').order_by('entry__entry_date', 'entry__created_at')

        if start_date:
            lines = lines.filter(entry__entry_date__gte=start_date)
        if end_date:
            lines = lines.filter(entry__entry_date__lte=end_date)

        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return {'error': 'Account not found', 'entries': []}

        opening_debit = Decimal('0.00')
        opening_credit = Decimal('0.00')

        if start_date:
            from django.db.models import Sum
            opening_debit = JournalEntryLine.objects.filter(
                account_id=account_id, entry__is_posted=True, entry__is_active=True,
                entry__entry_date__lt=start_date
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

            opening_credit = JournalEntryLine.objects.filter(
                account_id=account_id, entry__is_posted=True, entry__is_active=True,
                entry__entry_date__lt=start_date
            ).aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

        running_balance = compute_opening_balance(account, opening_debit, opening_credit)

        ledger_entries = []
        for line in lines:
            running_balance = apply_running_delta(account, running_balance, line.debit, line.credit)
            ledger_entries.append(format_ledger_entry(line, running_balance))

        return {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'opening_balance': compute_opening_balance(account, opening_debit, opening_credit),
            'entries': ledger_entries,
            'closing_balance': running_balance,
        }

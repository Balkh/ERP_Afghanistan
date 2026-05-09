from decimal import Decimal
from datetime import date
from typing import Optional, Union
from dataclasses import dataclass, field
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine


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
        now = django_timezone.now()
        prefix = f"JE-{now.strftime('%Y%m')}"
        
        last_entry = JournalEntry.objects.filter(
            entry_number__startswith=prefix
        ).order_by('-entry_number').first()
        
        if last_entry:
            try:
                parts = last_entry.entry_number.split('-')
                sequence = int(parts[2]) + 1
            except (IndexError, ValueError):
                sequence = 1
        else:
            sequence = 1
        
        return f"{prefix}-{sequence:04d}-{entry_type[:3].upper()}"

    @staticmethod
    def validate_lines(lines: list[dict]) -> list[str]:
        """
        Validate journal entry lines.
        Returns list of validation error messages.
        """
        errors = []
        
        if len(lines) < 2:
            errors.append('Journal entry must have at least 2 lines.')
        
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        seen_accounts = set()
        
        for i, line in enumerate(lines):
            account = None
            if 'account_id' in line:
                try:
                    account = Account.objects.get(id=line['account_id'], is_active=True)
                except Account.DoesNotExist:
                    errors.append(f"Line {i+1}: Account not found or inactive.")
                    continue
            elif 'account_code' in line:
                try:
                    account = Account.objects.get(code=line['account_code'], is_active=True)
                except Account.DoesNotExist:
                    errors.append(f"Line {i+1}: Account '{line['account_code']}' not found or inactive.")
                    continue
            
            if account:
                if account.id in seen_accounts:
                    errors.append(f"Line {i+1}: Account '{account.code}' appears multiple times.")
                seen_accounts.add(account.id)
            
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            
            if debit < 0 or credit < 0:
                errors.append(f"Line {i+1}: Amounts cannot be negative.")
            if debit == 0 and credit == 0:
                errors.append(f"Line {i+1}: Either debit or credit must be positive.")
            if debit > 0 and credit > 0:
                errors.append(f"Line {i+1}: Cannot have both debit and credit on the same line.")
            
            total_debit += debit
            total_credit += credit
        
        if total_debit != total_credit:
            errors.append(
                f'Journal entry is not balanced. '
                f'Debits: {total_debit:.2f}, Credits: {total_credit:.2f}, '
                f'Difference: {abs(total_debit - total_credit):.2f}'
            )
        
        return errors

    @staticmethod
    @transaction.atomic
    def create_entry(
        entry_type: str,
        description: str,
        lines: list[dict],
        entry_date: Optional[date] = None,
        reference: str = '',
        entry_number: Optional[str] = None,
        auto_post: bool = False
    ) -> dict:
        """
        Create a new journal entry with double-entry validation.
        """
        if entry_date is None:
            entry_date = django_timezone.now().date()
        
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
            is_posted=auto_post
        )
        
        for line_data in lines:
            account = None
            if 'account_id' in line_data:
                account = Account.objects.get(id=line_data['account_id'])
            elif 'account_code' in line_data:
                account = Account.objects.get(code=line_data['account_code'])
            
            debit = Decimal(str(line_data.get('debit', 0)))
            credit = Decimal(str(line_data.get('credit', 0)))
            
            JournalEntryLine.objects.create(
                entry=entry,
                account=account,
                debit=debit,
                credit=credit,
                description=line_data.get('description', '')
            )
            
            total_debit += debit
            total_credit += credit
        
        if auto_post:
            JournalEngine.update_account_balances(entry)
        
        return {
            'success': True,
            'entry_id': str(entry.id),
            'entry_number': entry.entry_number,
            'total_debit': total_debit,
            'total_credit': total_credit,
        }

    @staticmethod
    @transaction.atomic
    def post_entry(entry_id) -> dict:
        """Post a journal entry, locking it and updating account balances."""
        try:
            entry = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            return {'success': False, 'errors': ['Journal entry not found']}
        
        if entry.is_posted:
            return {'success': False, 'errors': ['Entry is already posted']}
        
        if not entry.is_balanced:
            return {
                'success': False,
                'errors': [f'Cannot post unbalanced entry. Debits: {entry.total_debit:.2f}, Credits: {entry.total_credit:.2f}']
            }
        
        entry.is_posted = True
        entry.save(update_fields=['is_posted', 'updated_at'])
        
        JournalEngine.update_account_balances(entry)
        
        return {
            'success': True,
            'message': 'Journal entry posted successfully',
            'entry_id': str(entry.id),
        }

    @staticmethod
    @transaction.atomic
    def unpost_entry(entry_id) -> dict:
        """Unpost a journal entry, reverting account balance changes."""
        try:
            entry = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            return {'success': False, 'errors': ['Journal entry not found']}
        
        if not entry.is_posted:
            return {'success': False, 'errors': ['Entry is not posted']}
        
        entry.is_posted = False
        entry.save(update_fields=['is_posted', 'updated_at'])
        
        JournalEngine.recalculate_all_balances()
        
        return {
            'success': True,
            'message': 'Journal entry unposted successfully',
            'entry_id': str(entry.id),
        }

    @staticmethod
    @transaction.atomic
    def reverse_entry(entry_id, reason: str = '') -> dict:
        """Reverse a posted journal entry by creating an opposite entry."""
        try:
            original = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            return {'success': False, 'errors': ['Original journal entry not found']}
        
        if not original.is_posted:
            return {'success': False, 'errors': ['Cannot reverse an unposted entry']}
        
        reversed_lines = []
        for line in original.lines.all():
            reversed_lines.append({
                'account_id': line.account_id,
                'debit': line.credit,
                'credit': line.debit,
                'description': f"Reversal: {line.description}"
            })
        
        reversal_number = f"REV-{original.entry_number}"
        return JournalEngine.create_entry(
            entry_type='REVERSAL',
            description=f"Reversal of {original.entry_number}: {reason or original.description}",
            lines=reversed_lines,
            entry_date=django_timezone.now().date(),
            reference=original.reference,
            entry_number=reversal_number,
            auto_post=True
        )

    @staticmethod
    def update_account_balances(entry: JournalEntry):
        """Update account balances based on a posted journal entry."""
        for line in entry.lines.all():
            account = line.account
            
            total_debit = JournalEntryLine.objects.filter(
                account=account, entry__is_posted=True, entry__is_active=True
            ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
            
            total_credit = JournalEntryLine.objects.filter(
                account=account, entry__is_posted=True, entry__is_active=True
            ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
            
            if account.account_type in ['ASSET', 'EXPENSE']:
                balance = total_debit - total_credit
            else:
                balance = total_credit - total_debit
            
            Account.objects.filter(id=account.id).update(balance=balance)

    @staticmethod
    def recalculate_all_balances():
        """Recalculate balances for all accounts from posted journal entries."""
        accounts = Account.objects.filter(is_active=True)
        
        for account in accounts:
            total_debit = JournalEntryLine.objects.filter(
                account=account, entry__is_posted=True, entry__is_active=True
            ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
            
            total_credit = JournalEntryLine.objects.filter(
                account=account, entry__is_posted=True, entry__is_active=True
            ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
            
            if account.account_type in ['ASSET', 'EXPENSE']:
                balance = total_debit - total_credit
            else:
                balance = total_credit - total_debit
            
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
            opening_debit = JournalEntryLine.objects.filter(
                account_id=account_id, entry__is_posted=True, entry__is_active=True,
                entry__entry_date__lt=start_date
            ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
            
            opening_credit = JournalEntryLine.objects.filter(
                account_id=account_id, entry__is_posted=True, entry__is_active=True,
                entry__entry_date__lt=start_date
            ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
        
        if account.account_type in ['ASSET', 'EXPENSE']:
            running_balance = opening_debit - opening_credit
        else:
            running_balance = opening_credit - opening_debit
        
        ledger_entries = []
        for line in lines:
            if account.account_type in ['ASSET', 'EXPENSE']:
                running_balance += line.debit - line.credit
            else:
                running_balance += line.credit - line.debit
            
            ledger_entries.append({
                'entry_number': line.entry.entry_number,
                'entry_date': line.entry.entry_date.isoformat(),
                'entry_type': line.entry.entry_type,
                'description': line.entry.description,
                'reference': line.entry.reference,
                'debit': line.debit,
                'credit': line.credit,
                'running_balance': running_balance,
            })
        
        return {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'opening_balance': opening_debit - opening_credit if account.account_type in ['ASSET', 'EXPENSE'] else opening_credit - opening_debit,
            'entries': ledger_entries,
            'closing_balance': running_balance,
        }

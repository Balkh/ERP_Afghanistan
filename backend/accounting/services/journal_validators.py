"""
Journal entry validators and number generators.

Extracted from JournalEngine in Sprint 4.
Pure logic — no DB writes, no transaction boundaries, no save calls.
"""
from typing import Optional

from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry


def validate_lines(lines: list[dict]) -> list[str]:
    """
    Validate journal entry lines.

    Returns list of validation error messages.
    """
    from decimal import Decimal
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

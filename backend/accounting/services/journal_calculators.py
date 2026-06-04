"""
Account balance calculators.

Extracted from JournalEngine in Sprint 4.
Pure math — no DB writes, no transaction boundaries, no save calls.
"""
from decimal import Decimal

from django.db import models

from accounting.models import Account, JournalEntryLine


_DEBIT_NORMAL_ACCOUNTS = ('ASSET', 'EXPENSE')


def compute_account_balance(account: Account) -> Decimal:
    """
    Compute the current balance for an account by aggregating
    all posted journal entry lines.
    """
    total_debit = JournalEntryLine.objects.filter(
        account=account, entry__is_posted=True, entry__is_active=True
    ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')

    total_credit = JournalEntryLine.objects.filter(
        account=account, entry__is_posted=True, entry__is_active=True
    ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')

    return _apply_balance_sign(account, total_debit, total_credit)


def compute_opening_balance(account: Account, opening_debit: Decimal, opening_credit: Decimal) -> Decimal:
    """
    Compute opening balance for a date range.
    """
    return _apply_balance_sign(account, opening_debit, opening_credit)


def apply_running_delta(account: Account, running_balance: Decimal, debit: Decimal, credit: Decimal) -> Decimal:
    """
    Apply a single journal entry line's debit/credit to a running balance
    using the account's normal balance convention.
    """
    if account.account_type in _DEBIT_NORMAL_ACCOUNTS:
        return running_balance + debit - credit
    return running_balance + credit - debit


def compute_inverse_balance_delta(account: Account, line_debit: Decimal, line_credit: Decimal) -> Decimal:
    """
    Compute the inverse delta to subtract from an account balance
    when unposting a journal entry line.
    """
    if account.account_type in _DEBIT_NORMAL_ACCOUNTS:
        return -line_debit + line_credit
    return -line_credit + line_debit


def _apply_balance_sign(account: Account, total_debit: Decimal, total_credit: Decimal) -> Decimal:
    if account.account_type in _DEBIT_NORMAL_ACCOUNTS:
        return total_debit - total_credit
    return total_credit - total_debit

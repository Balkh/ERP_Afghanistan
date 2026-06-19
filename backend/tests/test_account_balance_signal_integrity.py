import pytest
from decimal import Decimal

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_calculators import compute_account_balance


@pytest.mark.django_db
def test_unposted_entry_does_not_affect_account_balance():
    """Regression: the balance-sync signal must ignore unposted entries,
    matching compute_account_balance (posted + active only)."""
    cash = Account.objects.create(code='9101', name='Cash repro', account_type='ASSET',
                                  account_category='CURRENT_ASSET')
    rev = Account.objects.create(code='9102', name='Rev repro', account_type='REVENUE',
                                 account_category='OPERATING_REVENUE')

    entry = JournalEntry.objects.create(
        entry_number='REPRO-UNPOSTED-1', entry_date='2026-01-15', entry_type='SALE',
        description='unposted', is_posted=False,
    )
    JournalEntryLine.objects.create(entry=entry, account=cash, debit=Decimal('100.00'), credit=Decimal('0.00'))
    JournalEntryLine.objects.create(entry=entry, account=rev, debit=Decimal('0.00'), credit=Decimal('100.00'))

    cash.refresh_from_db()
    rev.refresh_from_db()

    assert compute_account_balance(cash) == Decimal('0.00')
    assert cash.balance == Decimal('0.00'), f"unposted leaked into stored balance: {cash.balance}"
    assert rev.balance == Decimal('0.00'), f"unposted leaked into stored balance: {rev.balance}"


@pytest.mark.django_db
def test_posted_entry_updates_balance_via_signal():
    """Posted, active entries DO contribute to Account.balance."""
    cash = Account.objects.create(code='9103', name='Cash posted', account_type='ASSET',
                                  account_category='CURRENT_ASSET')
    rev = Account.objects.create(code='9104', name='Rev posted', account_type='REVENUE',
                                 account_category='OPERATING_REVENUE')

    entry = JournalEntry.objects.create(
        entry_number='REPRO-POSTED-1', entry_date='2026-01-15', entry_type='SALE',
        description='posted', is_posted=True,
    )
    JournalEntryLine.objects.create(entry=entry, account=cash, debit=Decimal('250.00'), credit=Decimal('0.00'))
    JournalEntryLine.objects.create(entry=entry, account=rev, debit=Decimal('0.00'), credit=Decimal('250.00'))

    cash.refresh_from_db()
    rev.refresh_from_db()

    assert cash.balance == Decimal('250.00')
    assert rev.balance == Decimal('250.00')


@pytest.mark.django_db
def test_inactive_entry_excluded_from_balance():
    """is_active=False entries must not count toward balance."""
    cash = Account.objects.create(code='9105', name='Cash inactive', account_type='ASSET',
                                  account_category='CURRENT_ASSET')
    rev = Account.objects.create(code='9106', name='Rev inactive', account_type='REVENUE',
                                 account_category='OPERATING_REVENUE')

    entry = JournalEntry.objects.create(
        entry_number='REPRO-INACTIVE-1', entry_date='2026-01-15', entry_type='SALE',
        description='inactive', is_posted=True, is_active=False,
    )
    JournalEntryLine.objects.create(entry=entry, account=cash, debit=Decimal('70.00'), credit=Decimal('0.00'))
    JournalEntryLine.objects.create(entry=entry, account=rev, debit=Decimal('0.00'), credit=Decimal('70.00'))

    cash.refresh_from_db()
    assert cash.balance == Decimal('0.00')

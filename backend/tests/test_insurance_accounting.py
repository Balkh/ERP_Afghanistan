"""Regression: insurance claim accounting must create balanced, posted journal
entries. Previously crashed: JournalEntryLine(journal_entry=...) (field is `entry`)
and JournalEngine.post(...) (method is `post_entry`)."""
import uuid
from decimal import Decimal
from datetime import timedelta

import pytest
from django.utils import timezone

from accounting.models import Account, JournalEntry
from insurance.models import InsuranceProvider, InsurancePolicy, Claim
from insurance.services import InsuranceAccountingService
from sales.models import Customer


def _accounts():
    # Service looks up code__startswith '1200'/'4000' and code '1100'.
    Account.objects.get_or_create(code='1200', defaults=dict(
        name='AR', account_type='ASSET', account_category='CURRENT_ASSET'))
    Account.objects.get_or_create(code='1100', defaults=dict(
        name='Cash', account_type='ASSET', account_category='CURRENT_ASSET'))
    Account.objects.get_or_create(code='4000', defaults=dict(
        name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE'))


def _claim(covered=Decimal('500.00')):
    provider = InsuranceProvider.objects.create(name='Prov', code=f'PR{uuid.uuid4().hex[:5]}')
    customer = Customer(name='Cust', code=f'K{uuid.uuid4().hex[:6]}', phone='+100')
    customer.save()
    policy = InsurancePolicy.objects.create(
        policy_number=f'POL{uuid.uuid4().hex[:6]}', provider=provider, customer=customer,
        start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=365),
    )
    return Claim.objects.create(
        policy=policy, total_amount=Decimal('800.00'), covered_amount=covered,
        status='APPROVED',
    )


@pytest.mark.django_db
def test_claim_receivable_entry_is_balanced_and_posted():
    _accounts()
    claim = _claim(Decimal('500.00'))

    entry = InsuranceAccountingService.create_claim_receivable_entry(claim)

    assert isinstance(entry, JournalEntry)
    entry.refresh_from_db()
    assert entry.is_posted is True
    lines = list(entry.lines.all())
    assert len(lines) == 2
    assert sum(l.debit for l in lines) == Decimal('500.00')
    assert sum(l.credit for l in lines) == sum(l.debit for l in lines)
    claim.refresh_from_db()
    assert claim.journal_entry_id == entry.id


@pytest.mark.django_db
def test_claim_payment_entry_is_balanced_and_marks_paid():
    _accounts()
    claim = _claim(Decimal('500.00'))
    InsuranceAccountingService.create_claim_receivable_entry(claim)
    claim.refresh_from_db()

    pay_entry = InsuranceAccountingService.record_claim_payment(claim)

    assert isinstance(pay_entry, JournalEntry)
    pay_entry.refresh_from_db()
    assert pay_entry.is_posted is True
    lines = list(pay_entry.lines.all())
    assert len(lines) == 2
    assert sum(l.debit for l in lines) == sum(l.credit for l in lines) == Decimal('500.00')
    claim.refresh_from_db()
    assert claim.status == 'PAID'
    assert claim.paid_at is not None

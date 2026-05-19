"""Insurance accounting integration service."""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class InsuranceAccountingService:
    """Handles journal entry creation for insurance claim approvals/payments."""

    @staticmethod
    @transaction.atomic
    def create_claim_receivable_entry(claim):
        """Create journal entry recording insurance receivable when claim is approved."""
        from accounting.models import JournalEntry, JournalEntryLine
        from accounting.services.journal_engine import JournalEngine

        if claim.journal_entry:
            return claim.journal_entry

        # Find relevant accounts
        from accounting.models import Account
        receivable_acct = Account.objects.filter(code__startswith='1200').first()
        revenue_acct = Account.objects.filter(code__startswith='4000').first()
        if not receivable_acct or not revenue_acct:
            return None

        entry = JournalEntry.objects.create(
            entry_number=f"INS-{claim.claim_number}",
            entry_type='RECEIPT',
            description=_('Insurance claim receivable: ') + claim.claim_number,
            entry_date=timezone.now().date(),
            is_posted=True,
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=receivable_acct,
            debit=claim.covered_amount,
            credit=Decimal('0.00'),
            description=_('Insurance receivable'),
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=revenue_acct,
            debit=Decimal('0.00'),
            credit=claim.covered_amount,
            description=_('Claim covered amount'),
        )

        JournalEngine.post(entry)
        claim.journal_entry = entry
        claim.save(update_fields=['journal_entry'])
        return entry

    @staticmethod
    @transaction.atomic
    def record_claim_payment(claim, payment_account_code='1100'):
        """Record payment received from insurance provider."""
        from accounting.models import Account, JournalEntry, JournalEntryLine
        from accounting.services.journal_engine import JournalEngine

        if not claim.journal_entry:
            return None

        cash_acct = Account.objects.filter(code=payment_account_code).first()
        receivable_acct = Account.objects.filter(code__startswith='1200').first()
        if not cash_acct or not receivable_acct:
            return None

        entry = JournalEntry.objects.create(
            entry_number=f"INS-PAY-{claim.claim_number}",
            entry_type='RECEIPT',
            description=_('Insurance payment received: ') + claim.claim_number,
            entry_date=timezone.now().date(),
            is_posted=True,
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=cash_acct,
            debit=claim.covered_amount,
            credit=Decimal('0.00'),
            description=_('Insurance payment'),
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=receivable_acct,
            debit=Decimal('0.00'),
            credit=claim.covered_amount,
            description=_('Receivable settled'),
        )

        JournalEngine.post(entry)
        claim.status = 'PAID'
        claim.paid_at = timezone.now()
        claim.save(update_fields=['status', 'paid_at'])
        return entry

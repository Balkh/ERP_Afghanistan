"""Tests for Phase 21 — Reversal Safety."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from accounting.models import (
    FiscalPeriod,
    Account,
    JournalEntry,
    JournalEntryLine,
)
from accounting.services.reversal_safety import ReversalSafetyService


class ReversalSafetyImpactTest(TestCase):
    """Test reversal impact analysis."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.account_dr = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        self.account_cr = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE',
        )
        self.entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Test sale',
            is_posted=True,
        )
        JournalEntryLine.objects.create(entry=self.entry, account=self.account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=self.entry, account=self.account_cr, credit=Decimal('100.00'))

    def test_analyze_impact_returns_safe_for_valid_entry(self):
        impact = ReversalSafetyService.analyze_impact(str(self.entry.id))
        self.assertTrue(impact.is_safe)
        self.assertEqual(len(impact.blockers), 0)

    def test_analyze_impact_shows_affected_accounts(self):
        impact = ReversalSafetyService.analyze_impact(str(self.entry.id))
        self.assertEqual(len(impact.affected_accounts), 2)
        account_codes = [a['account_code'] for a in impact.affected_accounts]
        self.assertIn('1001', account_codes)
        self.assertIn('4001', account_codes)

    def test_analyze_impact_shows_reversal_amounts(self):
        impact = ReversalSafetyService.analyze_impact(str(self.entry.id))
        cash_account = next(a for a in impact.affected_accounts if a['account_code'] == '1001')
        revenue_account = next(a for a in impact.affected_accounts if a['account_code'] == '4001')
        self.assertEqual(cash_account['reversal_debit'], '0.00')
        self.assertEqual(cash_account['reversal_credit'], '100.00')
        self.assertEqual(revenue_account['reversal_debit'], '100.00')
        self.assertEqual(revenue_account['reversal_credit'], '0.00')

    def test_analyze_impact_raises_for_nonexistent_entry(self):
        with self.assertRaises(ValidationError):
            ReversalSafetyService.analyze_impact('00000000-0000-0000-0000-000000000000')


class ReversalSafetyBlockersTest(TestCase):
    """Test reversal safety blockers."""

    def setUp(self):
        self.account_dr = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        self.account_cr = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE',
        )

    def test_unposted_entry_blocked(self):
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Unposted entry',
            is_posted=False,
        )
        impact = ReversalSafetyService.analyze_impact(str(entry.id))
        self.assertFalse(impact.is_safe)
        self.assertEqual(impact.blockers[0]['code'], 'ENTRY_NOT_POSTED')

    def test_reversal_entry_blocked(self):
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-REV',
            entry_date=date(2026, 2, 15),
            entry_type='REVERSAL',
            description='Already a reversal',
            is_posted=True,
        )
        impact = ReversalSafetyService.analyze_impact(str(entry.id))
        self.assertFalse(impact.is_safe)
        self.assertEqual(impact.blockers[0]['code'], 'ALREADY_REVERSAL')

    def test_locked_period_blocked(self):
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 6, 15),
            entry_type='SALE',
            description='Entry in locked period',
            is_posted=True,
        )
        FiscalPeriod.objects.create(
            name='Locked Period',
            code='LOCKED-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status='LOCKED',
            is_locked=True,
        )
        impact = ReversalSafetyService.analyze_impact(str(entry.id))
        self.assertFalse(impact.is_safe)
        self.assertEqual(impact.blockers[0]['code'], 'PERIOD_LOCKED')

    def test_already_reversed_blocked(self):
        original = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Original entry',
            is_posted=True,
        )
        reversal = JournalEntry.objects.create(
            entry_number='JE-202601-002-REV',
            entry_date=date(2026, 2, 20),
            entry_type='REVERSAL',
            description='Reversal entry',
            is_posted=True,
            original_entry=original,
        )
        original.reversed_by_entry = reversal
        original.save()

        impact = ReversalSafetyService.analyze_impact(str(original.id))
        self.assertFalse(impact.is_safe)
        self.assertEqual(impact.blockers[0]['code'], 'ALREADY_REVERSED')


class ReversalChainTest(TestCase):
    """Test reversal chain visualization."""

    def setUp(self):
        self.account_dr = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        self.account_cr = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE',
        )

    def test_chain_for_single_entry(self):
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Single entry',
            is_posted=True,
        )
        chain = ReversalSafetyService.get_reversal_chain_visualization(str(entry.id))
        self.assertEqual(chain['chain_length'], 1)
        self.assertEqual(len(chain['nodes']), 1)
        self.assertEqual(len(chain['edges']), 0)

    def test_chain_for_reversed_entry(self):
        original = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Original entry',
            is_posted=True,
        )
        reversal = JournalEntry.objects.create(
            entry_number='JE-202601-002-REV',
            entry_date=date(2026, 2, 20),
            entry_type='REVERSAL',
            description='Reversal entry',
            is_posted=True,
            original_entry=original,
        )

        chain = ReversalSafetyService.get_reversal_chain_visualization(str(original.id))
        self.assertEqual(chain['chain_length'], 2)
        self.assertEqual(len(chain['edges']), 1)
        self.assertEqual(chain['edges'][0]['relationship'], 'reversed_by')


class ReversalExecutionTest(TestCase):
    """Test reversal execution with safety."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.account_dr = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        self.account_cr = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE',
        )
        self.entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Test sale',
            is_posted=True,
        )
        JournalEntryLine.objects.create(entry=self.entry, account=self.account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=self.entry, account=self.account_cr, credit=Decimal('100.00'))

    def test_execute_reversal_requires_reason(self):
        with self.assertRaises(ValidationError):
            ReversalSafetyService.execute_reversal(
                entry_id=str(self.entry.id),
                reason='',
            )

    def test_execute_reversal_requires_minimum_reason_length(self):
        with self.assertRaises(ValidationError):
            ReversalSafetyService.execute_reversal(
                entry_id=str(self.entry.id),
                reason='Short',
            )

    def test_execute_reversal_fails_when_blocked(self):
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-002-SALE',
            entry_date=date(2026, 6, 15),
            entry_type='SALE',
            description='Entry in locked period',
            is_posted=True,
        )
        JournalEntryLine.objects.create(entry=entry, account=self.account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=entry, account=self.account_cr, credit=Decimal('100.00'))

        FiscalPeriod.objects.create(
            name='Locked Period',
            code='LOCKED-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status='LOCKED',
            is_locked=True,
        )
        with self.assertRaises(ValidationError):
            ReversalSafetyService.execute_reversal(
                entry_id=str(entry.id),
                reason='Valid reason for testing',
            )

"""Tests for Phase 21 — Fiscal Period Governance."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone

from accounting.models import (
    FiscalPeriod,
    FiscalPeriodCloseLog,
    Account,
    JournalEntry,
    JournalEntryLine,
    is_period_locked,
    get_open_period_for_date,
    get_period_for_date,
)
from accounting.services.period_closing import PeriodClosingService


class FiscalPeriodModelTest(TestCase):
    """Test FiscalPeriod model behavior."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.period = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
        )

    def test_open_period_can_modify(self):
        self.assertTrue(self.period.can_modify())
        self.assertTrue(self.period.can_post())
        self.assertTrue(self.period.can_reverse())

    def test_closed_period_cannot_modify(self):
        self.period.status = 'CLOSED'
        self.period.save()
        self.assertFalse(self.period.can_modify())
        self.assertFalse(self.period.can_post())
        self.assertFalse(self.period.can_reverse())

    def test_locked_period_cannot_modify(self):
        self.period.lock(user=self.user)
        self.assertFalse(self.period.can_modify())
        self.assertFalse(self.period.can_post())
        self.assertFalse(self.period.can_reverse())

    def test_soft_closed_period_cannot_modify(self):
        self.period.status = 'SOFT_CLOSED'
        self.period.save()
        self.assertFalse(self.period.can_modify())
        self.assertFalse(self.period.can_post())
        self.assertFalse(self.period.can_reverse())

    def test_lock_sets_timestamp(self):
        before = timezone.now()
        self.period.lock(user=self.user)
        self.period.refresh_from_db()
        self.assertTrue(self.period.is_locked)
        self.assertEqual(self.period.status, 'LOCKED')
        self.assertIsNotNone(self.period.locked_at)
        self.assertEqual(self.period.locked_by, self.user)

    def test_unlock_resets_fields(self):
        self.period.lock(user=self.user)
        self.period.unlock(user=self.user, reason='Testing unlock')
        self.period.refresh_from_db()
        self.assertFalse(self.period.is_locked)
        self.assertEqual(self.period.status, 'OPEN')

    def test_validate_date_range(self):
        period = FiscalPeriod(
            name='Invalid',
            code='INVALID',
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            period.full_clean()


class PeriodHelperFunctionsTest(TestCase):
    """Test period helper functions."""

    def setUp(self):
        self.open_period = FiscalPeriod.objects.create(
            name='Open Period',
            code='OPEN-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status='OPEN',
        )
        self.locked_period = FiscalPeriod.objects.create(
            name='Locked Period',
            code='LOCKED-2025',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            status='LOCKED',
            is_locked=True,
        )

    def test_is_period_locked_returns_true_for_locked_period(self):
        self.assertTrue(is_period_locked(date(2025, 6, 15)))

    def test_is_period_locked_returns_false_for_open_period(self):
        self.assertFalse(is_period_locked(date(2026, 6, 15)))

    def test_is_period_locked_returns_false_for_outside_period(self):
        self.assertFalse(is_period_locked(date(2024, 1, 1)))

    def test_get_open_period_for_date(self):
        period = get_open_period_for_date(date(2026, 6, 15))
        self.assertEqual(period, self.open_period)

    def test_get_period_for_date(self):
        period = get_period_for_date(date(2025, 6, 15))
        self.assertEqual(period, self.locked_period)


class PeriodClosingReadinessTest(TestCase):
    """Test period closing readiness checks."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.period = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
        )
        self.account_dr = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        self.account_cr = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE',
        )

    def test_empty_period_is_ready(self):
        readiness = PeriodClosingService.check_readiness(self.period)
        self.assertTrue(readiness.is_ready)
        self.assertEqual(len(readiness.blockers), 0)

    def test_unposted_journals_block_closing(self):
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Test sale',
            is_posted=False,
        )
        JournalEntryLine.objects.create(entry=entry, account=self.account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=entry, account=self.account_cr, credit=Decimal('100.00'))

        readiness = PeriodClosingService.check_readiness(self.period)
        self.assertFalse(readiness.is_ready)
        self.assertEqual(len(readiness.blockers), 1)
        self.assertEqual(readiness.blockers[0]['code'], 'UNPOSTED_JOURNALS')

    def test_posted_journals_allow_closing(self):
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Test sale',
            is_posted=True,
        )
        JournalEntryLine.objects.create(entry=entry, account=self.account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=entry, account=self.account_cr, credit=Decimal('100.00'))

        readiness = PeriodClosingService.check_readiness(self.period)
        self.assertTrue(readiness.is_ready)

    def test_trial_balance_mismatch_blocks_closing(self):
        entry1 = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Test sale 1',
            is_posted=True,
        )
        JournalEntryLine.objects.create(entry=entry1, account=self.account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=entry1, account=self.account_cr, credit=Decimal('100.00'))

        entry2 = JournalEntry.objects.create(
            entry_number='JE-202601-002-SALE',
            entry_date=date(2026, 2, 20),
            entry_type='SALE',
            description='Test sale 2',
            is_posted=True,
        )
        JournalEntryLine.objects.create(entry=entry2, account=self.account_dr, debit=Decimal('50.00'))
        JournalEntryLine.objects.create(entry=entry2, account=self.account_cr, credit=Decimal('40.00'))

        readiness = PeriodClosingService.check_readiness(self.period)
        self.assertFalse(readiness.is_ready)
        self.assertEqual(readiness.blockers[0]['code'], 'TRIAL_BALANCE_MISMATCH')


class PeriodClosingExecutionTest(TestCase):
    """Test period closing execution."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.period = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
        )

    def test_soft_close_requires_reason(self):
        with self.assertRaises(ValidationError):
            PeriodClosingService.soft_close(self.period, user=self.user, reason='')

    def test_soft_close_changes_status(self):
        result = PeriodClosingService.soft_close(
            self.period, user=self.user, reason='Testing soft close'
        )
        self.assertTrue(result['success'])
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, 'SOFT_CLOSED')

    def test_close_requires_reason(self):
        with self.assertRaises(ValidationError):
            PeriodClosingService.close_period(self.period, user=self.user, reason='')

    def test_close_changes_status(self):
        result = PeriodClosingService.close_period(
            self.period, user=self.user, reason='Testing close'
        )
        self.assertTrue(result['success'])
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, 'CLOSED')
        self.assertIsNotNone(self.period.closing_completed_at)
        self.assertEqual(self.period.closing_completed_by, self.user)

    def test_close_creates_audit_log(self):
        PeriodClosingService.close_period(
            self.period, user=self.user, reason='Testing close'
        )
        log = FiscalPeriodCloseLog.objects.get(period=self.period, action='CLOSE')
        self.assertEqual(log.reason, 'Testing close')
        self.assertEqual(log.performed_by, self.user)
        self.assertEqual(log.previous_status, 'OPEN')
        self.assertEqual(log.new_status, 'CLOSED')

    def test_lock_requires_closed_period(self):
        with self.assertRaises(ValidationError):
            PeriodClosingService.lock_period(
                self.period, user=self.user, reason='Testing lock'
            )

    def test_lock_after_close(self):
        PeriodClosingService.close_period(
            self.period, user=self.user, reason='Testing close'
        )
        result = PeriodClosingService.lock_period(
            self.period, user=self.user, reason='Testing lock'
        )
        self.assertTrue(result['success'])
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, 'LOCKED')

    def test_reopen_requires_reason(self):
        PeriodClosingService.close_period(
            self.period, user=self.user, reason='Testing close'
        )
        with self.assertRaises(ValidationError):
            PeriodClosingService.reopen_period(self.period, user=self.user, reason='')

    def test_reopen_changes_status(self):
        PeriodClosingService.close_period(
            self.period, user=self.user, reason='Testing close'
        )
        result = PeriodClosingService.reopen_period(
            self.period, user=self.user, reason='Need to add entries'
        )
        self.assertTrue(result['success'])
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, 'OPEN')

    def test_reopen_creates_audit_log(self):
        PeriodClosingService.close_period(
            self.period, user=self.user, reason='Testing close'
        )
        PeriodClosingService.reopen_period(
            self.period, user=self.user, reason='Need to add entries'
        )
        reopen_log = FiscalPeriodCloseLog.objects.get(period=self.period, action='REOPEN')
        self.assertEqual(reopen_log.reason, 'Need to add entries')
        self.assertEqual(reopen_log.previous_status, 'CLOSED')
        self.assertEqual(reopen_log.new_status, 'OPEN')

    def test_close_fails_with_blockers_unless_force(self):
        account_dr = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        account_cr = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE',
        )
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Unposted entry',
            is_posted=False,
        )
        JournalEntryLine.objects.create(entry=entry, account=account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=entry, account=account_cr, credit=Decimal('100.00'))

        with self.assertRaises(ValidationError):
            PeriodClosingService.close_period(
                self.period, user=self.user, reason='Testing close', force=False
            )

    def test_close_succeeds_with_force(self):
        account_dr = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        account_cr = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE',
        )
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-SALE',
            entry_date=date(2026, 2, 15),
            entry_type='SALE',
            description='Unposted entry',
            is_posted=False,
        )
        JournalEntryLine.objects.create(entry=entry, account=account_dr, debit=Decimal('100.00'))
        JournalEntryLine.objects.create(entry=entry, account=account_cr, credit=Decimal('100.00'))

        result = PeriodClosingService.close_period(
            self.period, user=self.user, reason='Force close', force=True
        )
        self.assertTrue(result['success'])
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, 'CLOSED')


class PeriodClosingEdgeCasesTest(TestCase):
    """Test edge cases in period closing."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_cannot_close_already_closed_period(self):
        period = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='CLOSED',
        )
        with self.assertRaises(ValidationError):
            PeriodClosingService.close_period(period, user=self.user, reason='Testing')

    def test_cannot_reopen_open_period(self):
        period = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
        )
        with self.assertRaises(ValidationError):
            PeriodClosingService.reopen_period(period, user=self.user, reason='Testing')

    def test_overlapping_periods_warning(self):
        period1 = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
        )
        period2 = FiscalPeriod.objects.create(
            name='Q1 Overlap',
            code='Q1-OVERLAP',
            start_date=date(2026, 3, 1),
            end_date=date(2026, 6, 30),
            status='OPEN',
        )

        readiness = PeriodClosingService.check_readiness(period1)
        self.assertTrue(any(w['code'] == 'OVERLAPPING_PERIODS' for w in readiness.warnings))

    def test_unresolved_reversals_block_closing(self):
        period = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
        )
        account = Account.objects.create(
            code='1001', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET',
        )
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-001-REV',
            entry_date=date(2026, 2, 15),
            entry_type='REVERSAL',
            description='Unposted reversal',
            is_posted=False,
        )
        JournalEntryLine.objects.create(entry=entry, account=account, debit=Decimal('100.00'))

        readiness = PeriodClosingService.check_readiness(period)
        self.assertFalse(readiness.is_ready)
        blocker_codes = [b['code'] for b in readiness.blockers]
        self.assertIn('UNPOSTED_JOURNALS', blocker_codes)

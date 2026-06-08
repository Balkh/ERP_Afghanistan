"""
Accounting Production Readiness Tests

Covers:
- Journal Engine: post, unpost, reverse with period lock enforcement
- Payroll Accounting: journal generation, debit/credit validation
- Period Locks: close, reopen, enforcement on post/unpost/reverse
- Account Registry: consistency, account lookup
- Accounting Integrations: sales, purchases, payments
"""
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounting.models import (
    Account, JournalEntry, JournalEntryLine, JournalEventLog,
    FiscalPeriod, FiscalPeriodCloseLog, is_period_locked, get_period_for_date,
)
from accounting.services.journal_engine import JournalEngine
from accounting.services.journal_validators import validate_lines, generate_entry_number
from accounting.services.account_hierarchy import AccountHierarchyService
from core.accounting_registry import ACC


class JournalEnginePostUnpostReverseTest(TransactionTestCase):
    """Test post, unpost, and reverse with period lock enforcement."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')

        # Create required accounts (use get_or_create to avoid conflicts)
        self.cash_account, _ = Account.objects.get_or_create(
            code='1000', defaults={'name': 'Cash', 'account_type': 'ASSET', 'is_active': True}
        )
        self.ar_account, _ = Account.objects.get_or_create(
            code='1200', defaults={'name': 'Accounts Receivable', 'account_type': 'ASSET', 'is_active': True}
        )
        self.revenue_account, _ = Account.objects.get_or_create(
            code='4100', defaults={'name': 'Revenue', 'account_type': 'REVENUE', 'is_active': True}
        )
        self.ap_account, _ = Account.objects.get_or_create(
            code='2100', defaults={'name': 'Accounts Payable', 'account_type': 'LIABILITY', 'is_active': True}
        )

        # Create an OPEN fiscal period covering today
        today = date.today()
        self.open_period = FiscalPeriod.objects.create(
            name='Open Period', code='OPEN-2026',
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=30),
            status='OPEN',
        )

        # Create a LOCKED fiscal period
        self.locked_period = FiscalPeriod.objects.create(
            name='Locked Period', code='LOCKED-2025',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            status='LOCKED',
        )

    def _create_unposted_entry(self, entry_date=None):
        """Helper to create an unposted journal entry."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=[
                {'account_code': '1000', 'debit': Decimal('100.00'), 'credit': Decimal('0.00'), 'description': 'Dr Cash'},
                {'account_code': '4100', 'debit': Decimal('0.00'), 'credit': Decimal('100.00'), 'description': 'Cr Revenue'},
            ],
            entry_date=entry_date or date.today(),
            created_by=self.user.id,
        )
        self.assertTrue(result['success'], f"Failed to create entry: {result.get('errors')}")
        return JournalEntry.objects.get(id=result['entry_id'])

    def test_post_entry_success(self):
        """Posting an unposted entry in an open period succeeds."""
        entry = self._create_unposted_entry()
        result = JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        self.assertTrue(result['success'], f"Post failed: {result.get('errors')}")
        entry.refresh_from_db()
        self.assertTrue(entry.is_posted)

    def test_post_entry_already_posted(self):
        """Posting an already-posted entry returns error."""
        entry = self._create_unposted_entry()
        JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        result = JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        self.assertFalse(result['success'])
        self.assertIn('already posted', result['errors'][0])

    def test_post_entry_blocked_by_locked_period(self):
        """Posting into a locked period is rejected."""
        # Create in open period, then force-update date to locked period (bypassing save)
        entry = self._create_unposted_entry()
        JournalEntry.objects.filter(id=entry.id).update(entry_date=date(2025, 6, 15))
        entry.refresh_from_db()
        result = JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        self.assertFalse(result['success'])
        self.assertIn('locked', result['errors'][0].lower())

    def test_unpost_entry_success(self):
        """Unposting a posted entry in an open period succeeds."""
        entry = self._create_unposted_entry()
        JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        result = JournalEngine.unpost_entry(entry.id, user_id=self.user.id)
        self.assertTrue(result['success'], f"Unpost failed: {result.get('errors')}")
        entry.refresh_from_db()
        self.assertFalse(entry.is_posted)

    def test_unpost_entry_blocked_by_locked_period(self):
        """Unposting in a locked period is rejected."""
        # Create and post in open period, then force-update date to locked period
        entry = self._create_unposted_entry()
        JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        JournalEntry.objects.filter(id=entry.id).update(entry_date=date(2025, 6, 15))
        entry.refresh_from_db()
        result = JournalEngine.unpost_entry(entry.id, user_id=self.user.id)
        self.assertFalse(result['success'])
        self.assertIn('locked', result['errors'][0].lower())

    def test_reverse_entry_success(self):
        """Reversing a posted entry creates a reversal entry."""
        entry = self._create_unposted_entry()
        JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        result = JournalEngine.reverse_entry(entry.id, reason='Test reversal', user_id=self.user.id)
        self.assertTrue(result['success'], f"Reverse failed: {result.get('errors')}")
        entry.refresh_from_db()
        self.assertTrue(entry.is_reversed)

    def test_reverse_entry_blocked_by_locked_period(self):
        """Reversing in a locked period is rejected."""
        # Create and post in open period, then force-update date to locked period
        entry = self._create_unposted_entry()
        JournalEngine.post_entry(entry.id, posted_by=self.user.id)
        JournalEntry.objects.filter(id=entry.id).update(entry_date=date(2025, 6, 15))
        entry.refresh_from_db()
        result = JournalEngine.reverse_entry(entry.id, reason='Test', user_id=self.user.id)
        self.assertFalse(result['success'])
        self.assertIn('locked', result['errors'][0].lower())

    def test_reverse_unposted_entry_fails(self):
        """Reversing an unposted entry fails."""
        entry = self._create_unposted_entry()
        result = JournalEngine.reverse_entry(entry.id, reason='Test', user_id=self.user.id)
        self.assertFalse(result['success'])

    def test_post_entry_balanced_check(self):
        """Posting an unbalanced entry fails."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Unbalanced',
            lines=[
                {'account_code': '1000', 'debit': Decimal('100.00'), 'credit': Decimal('0.00'), 'description': 'Dr'},
                {'account_code': '4100', 'debit': Decimal('0.00'), 'credit': Decimal('50.00'), 'description': 'Cr'},
            ],
            created_by=self.user.id,
        )
        # Validation should catch the imbalance
        self.assertFalse(result['success'])


class PeriodLockHelperTest(TestCase):
    """Test is_period_locked and get_period_for_date helpers."""

    def setUp(self):
        self.open_period = FiscalPeriod.objects.create(
            name='Open', code='OPEN', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), status='OPEN'
        )
        self.locked_period = FiscalPeriod.objects.create(
            name='Locked', code='LOCKED', start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), status='LOCKED'
        )
        self.closed_period = FiscalPeriod.objects.create(
            name='Closed', code='CLOSED', start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), status='CLOSED'
        )

    def test_is_period_locked_for_locked_period(self):
        result = is_period_locked(date(2025, 6, 15))
        self.assertIsNotNone(result)

    def test_is_period_locked_for_open_period(self):
        result = is_period_locked(date(2026, 6, 15))
        self.assertIsNone(result)

    def test_is_period_locked_for_closed_period(self):
        result = is_period_locked(date(2024, 6, 15))
        self.assertIsNotNone(result)

    def test_get_period_for_date_locked(self):
        period = get_period_for_date(date(2025, 6, 15))
        self.assertIsNotNone(period)
        self.assertEqual(period.code, 'LOCKED')

    def test_get_period_for_date_open(self):
        period = get_period_for_date(date(2026, 6, 15))
        self.assertIsNotNone(period)
        self.assertEqual(period.code, 'OPEN')


class AccountRegistryConsistencyTest(TestCase):
    """Test ACC registry consistency and account lookups."""

    def test_registry_ar_consistency(self):
        issues = ACC.validate()
        ar_issues = [i for i in issues if 'ar' in i.lower() or 'accounts_receivable' in i.lower()]
        self.assertEqual(len(ar_issues), 0, f"AR registry issues: {ar_issues}")

    def test_registry_ap_consistency(self):
        issues = ACC.validate()
        ap_issues = [i for i in issues if 'ap' in i.lower() or 'accounts_payable' in i.lower()]
        self.assertEqual(len(ap_issues), 0, f"AP registry issues: {ap_issues}")

    def test_registry_tax_no_collision(self):
        issues = ACC.validate()
        tax_issues = [i for i in issues if 'tax' in i.lower() and 'WARNING' in i]
        self.assertEqual(len(tax_issues), 0, f"Tax registry issues: {tax_issues}")

    def test_all_required_keys_exist(self):
        required_keys = [
            'ar', 'ap', 'cash', 'cash_on_hand', 'bank',
            'inventory', 'sales_revenue', 'sales_cogs',
            'tax_payable', 'tax_receivable',
            'payroll_salary', 'payroll_expense',
            'operating_expense',
            'inventory_gain', 'inventory_loss', 'inventory_write_off',
        ]
        for key in required_keys:
            code = ACC.get(key)
            self.assertIsNotNone(code, f"Registry key '{key}' not found")

    def test_registry_is_frozen(self):
        with self.assertRaises(RuntimeError):
            ACC.register('test_key', '9999', 'Test', 'ASSET')

    def test_registry_getitem(self):
        code = ACC['ar']
        self.assertEqual(code, '1200')

    def test_registry_resolve(self):
        code, name = ACC.resolve('ar')
        self.assertEqual(code, '1200')
        self.assertIn('Receivable', name)


class PayrollAccountingTest(TransactionTestCase):
    """Test payroll accounting integration uses JournalEngine correctly."""

    def setUp(self):
        self.user = User.objects.create_user('payroll_user', 'pay@test.com', 'pass123')

        # Create required accounts matching ACC registry
        Account.objects.get_or_create(code='7010', defaults={'name': 'Payroll Salary Expense', 'account_type': 'EXPENSE', 'is_active': True})
        Account.objects.get_or_create(code='1010', defaults={'name': 'Cash on Hand', 'account_type': 'ASSET', 'is_active': True})
        Account.objects.get_or_create(code='2120', defaults={'name': 'Tax Payable', 'account_type': 'LIABILITY', 'is_active': True})

        today = date.today()
        FiscalPeriod.objects.create(
            name='Current', code='CUR-2026',
            start_date=today - timedelta(days=30), end_date=today + timedelta(days=30),
            status='OPEN',
        )

    def test_validate_payroll_accounts(self):
        from payroll.services.accounting import PayrollAccountingService
        result = PayrollAccountingService.validate_payroll_accounts()
        self.assertTrue(all(result.values()), f"Missing accounts: {result}")

    def test_create_payroll_journal_entry_balanced(self):
        """Payroll journal entry must be balanced (Debit == Credit)."""
        from payroll.services.accounting import PayrollAccountingService

        mock_cycle = MagicMock()
        mock_cycle.status = 'APPROVED'
        mock_cycle.total_gross = Decimal('10000')
        mock_cycle.total_deductions = Decimal('500')
        mock_cycle.total_net = Decimal('9500')
        mock_cycle.name = 'June 2026 Payroll'
        mock_cycle.employee_count = 10
        mock_cycle.period_month = 6
        mock_cycle.period_year = 2026
        mock_cycle.end_date = date.today()

        result = PayrollAccountingService.create_payroll_journal_entry(mock_cycle, self.user)
        self.assertTrue(result['success'], f"Payroll entry failed: {result.get('errors')}")

        # Verify balance
        entry = JournalEntry.objects.get(id=result['entry_id'])
        self.assertTrue(entry.is_balanced, f"Entry unbalanced: Dr={entry.total_debit} Cr={entry.total_credit}")

    def test_create_payroll_journal_entry_auto_posted(self):
        """Payroll journal entry should be auto-posted."""
        from payroll.services.accounting import PayrollAccountingService

        mock_cycle = MagicMock()
        mock_cycle.status = 'APPROVED'
        mock_cycle.total_gross = Decimal('5000')
        mock_cycle.total_deductions = Decimal('0')
        mock_cycle.total_net = Decimal('5000')
        mock_cycle.name = 'Test Payroll'
        mock_cycle.employee_count = 5
        mock_cycle.period_month = 6
        mock_cycle.period_year = 2026
        mock_cycle.end_date = date.today()

        result = PayrollAccountingService.create_payroll_journal_entry(mock_cycle, self.user)
        entry = JournalEntry.objects.get(id=result['entry_id'])
        self.assertTrue(entry.is_posted)


class ValidationTest(TransactionTestCase):
    """Test journal entry validation rules."""

    def setUp(self):
        self.user = User.objects.create_user('validator', 'val@test.com', 'pass123')
        Account.objects.get_or_create(code='1000', defaults={'name': 'Cash', 'account_type': 'ASSET', 'is_active': True})
        Account.objects.get_or_create(code='4100', defaults={'name': 'Revenue', 'account_type': 'REVENUE', 'is_active': True})

    def test_validate_lines_requires_two_lines(self):
        errors = validate_lines([
            {'account_code': '1000', 'debit': 100, 'credit': 0},
        ])
        self.assertTrue(any('at least 2' in e for e in errors))

    def test_validate_lines_rejects_negative_debit(self):
        errors = validate_lines([
            {'account_code': '1000', 'debit': -100, 'credit': 0},
            {'account_code': '4100', 'debit': 0, 'credit': 100},
        ])
        self.assertTrue(any('negative' in e.lower() for e in errors))

    def test_validate_lines_rejects_both_debit_and_credit(self):
        errors = validate_lines([
            {'account_code': '1000', 'debit': 100, 'credit': 100},
            {'account_code': '4100', 'debit': 0, 'credit': 200},
        ])
        self.assertTrue(any('both' in e.lower() for e in errors))

    def test_validate_lines_rejects_unbalanced(self):
        errors = validate_lines([
            {'account_code': '1000', 'debit': Decimal('100'), 'credit': Decimal('0')},
            {'account_code': '4100', 'debit': Decimal('0'), 'credit': Decimal('50')},
        ])
        self.assertTrue(any('not balanced' in e.lower() for e in errors))

    def test_validate_lines_passes_balanced(self):
        errors = validate_lines([
            {'account_code': '1000', 'debit': Decimal('100'), 'credit': Decimal('0')},
            {'account_code': '4100', 'debit': Decimal('0'), 'credit': Decimal('100')},
        ])
        self.assertEqual(len(errors), 0)

    def test_generate_entry_number_format(self):
        num = generate_entry_number('SALE')
        self.assertTrue(num.startswith('JE-'))
        # Entry number format: JE-{YYYYMM}-{SEQ}-{TYPE}, type is truncated to 3 chars
        self.assertIn('SAL', num)

    def test_create_entry_validates_lines(self):
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test',
            lines=[
                {'account_code': '1000', 'debit': Decimal('100'), 'credit': Decimal('0')},
            ],
            created_by=self.user.id,
        )
        self.assertFalse(result['success'])


class AccountHierarchyTest(TestCase):
    """Test default chart code consistency with registry."""

    def test_default_chart_ar_code_matches_registry(self):
        """Default chart AR account code must match ACC['ar']."""
        ar_accounts = [a for a in AccountHierarchyService.DEFAULT_ACCOUNTS if a['name'] == 'Accounts Receivable']
        self.assertEqual(len(ar_accounts), 1)
        registry_code = ACC['ar']
        chart_code = ar_accounts[0]['code']
        self.assertEqual(chart_code, registry_code,
                         f"Default chart AR code {chart_code} != registry {registry_code}")

    def test_default_chart_ap_code_matches_registry(self):
        """Default chart AP account code must match ACC['ap']."""
        ap_accounts = [a for a in AccountHierarchyService.DEFAULT_ACCOUNTS if a['name'] == 'Accounts Payable']
        self.assertEqual(len(ap_accounts), 1)
        registry_code = ACC['ap']
        chart_code = ap_accounts[0]['code']
        self.assertEqual(chart_code, registry_code,
                         f"Default chart AP code {chart_code} != registry {registry_code}")

    def test_all_leaf_accounts_have_valid_types(self):
        for acc_data in AccountHierarchyService.DEFAULT_ACCOUNTS:
            self.assertIn(acc_data['type'], ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'],
                         f"Account {acc_data['code']} has invalid type: {acc_data['type']}")

"""
Comprehensive JournalEngine behavior tests - testing actual business logic.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine


class JournalEngineValidateLinesBehaviorTest(TransactionTestCase):
    """Test validate_lines actual behavior."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )
        self.inactive_account = Account.objects.create(
            code='9999', name='Inactive', account_type='ASSET', is_active=False
        )

    def test_validate_lines_rejects_unbalanced_entry(self):
        """Test that validate_lines returns error for unbalanced entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '50.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertTrue(any('not balanced' in e.lower() for e in errors))

    def test_validate_lines_accepts_balanced_entry(self):
        """Test that validate_lines accepts balanced entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertEqual(len(errors), 0)

    def test_validate_lines_rejects_single_line(self):
        """Test that validate_lines rejects single line."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertTrue(any('at least 2' in e.lower() for e in errors))

    def test_validate_lines_rejects_inactive_account(self):
        """Test that validate_lines rejects inactive account."""
        lines = [
            {'account_id': str(self.inactive_account.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertTrue(any('inactive' in e.lower() or 'not found' in e.lower() for e in errors))

    def test_validate_lines_rejects_duplicate_accounts(self):
        """Test that validate_lines rejects duplicate accounts."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.cash.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertTrue(any('multiple times' in e.lower() for e in errors))

    def test_validate_lines_rejects_negative_amounts(self):
        """Test that validate_lines rejects negative amounts."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '-100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertTrue(any('negative' in e.lower() for e in errors))


class JournalEngineCreateEntryBehaviorTest(TransactionTestCase):
    """Test create_entry actual behavior."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_create_entry_creates_journal_entry(self):
        """Test that create_entry creates a JournalEntry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        self.assertTrue(result['success'])
        self.assertTrue(JournalEntry.objects.filter(entry_number=result['entry_number']).exists())

    def test_create_entry_creates_entry_lines(self):
        """Test that create_entry creates JournalEntryLines."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        entry = JournalEntry.objects.get(id=result['entry_id'])
        self.assertEqual(entry.lines.count(), 2)

    def test_create_entry_returns_errors_for_invalid_lines(self):
        """Test that create_entry returns validation errors."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        self.assertFalse(result['success'])
        self.assertTrue(len(result['errors']) > 0)

    def test_create_entry_with_auto_post(self):
        """Test create_entry with auto_post=True."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines,
            auto_post=True
        )
        self.assertTrue(result['success'])
        entry = JournalEntry.objects.get(id=result['entry_id'])
        self.assertTrue(entry.is_posted)


class JournalEnginePostEntryBehaviorTest(TransactionTestCase):
    """Test post_entry actual behavior."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_post_entry_marks_entry_as_posted(self):
        """Test that post_entry marks entry as posted."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        entry_id = result['entry_id']
        
        post_result = JournalEngine.post_entry(entry_id)
        self.assertTrue(post_result['success'])
        
        entry = JournalEntry.objects.get(id=entry_id)
        self.assertTrue(entry.is_posted)

    def test_post_entry_updates_account_balance(self):
        """Test that post_entry updates account balance."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        cash = Account.objects.get(id=self.cash.id)
        self.assertEqual(cash.balance, Decimal('100.00'))
        
        revenue = Account.objects.get(id=self.revenue.id)
        self.assertEqual(revenue.balance, Decimal('100.00'))

    def test_post_entry_rejects_already_posted(self):
        """Test that post_entry rejects already posted entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        post_result = JournalEngine.post_entry(result['entry_id'])
        self.assertFalse(post_result['success'])
        self.assertTrue(any('already posted' in e.lower() for e in post_result['errors']))

    def test_post_entry_fails_for_nonexistent_entry(self):
        """Test post_entry fails for nonexistent entry."""
        result = JournalEngine.post_entry('99999999-9999-9999-9999-999999999999')
        self.assertFalse(result['success'])


class JournalEngineUnpostEntryBehaviorTest(TransactionTestCase):
    """Test unpost_entry actual behavior."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_unpost_entry_marks_entry_as_unposted(self):
        """Test that unpost_entry marks entry as unposted."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        unpost_result = JournalEngine.unpost_entry(result['entry_id'])
        self.assertTrue(unpost_result['success'])
        
        entry = JournalEntry.objects.get(id=result['entry_id'])
        self.assertFalse(entry.is_posted)

    def test_unpost_entry_resets_account_balance(self):
        """Test that unpost_entry resets account balance to zero."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        JournalEngine.unpost_entry(result['entry_id'])
        
        cash = Account.objects.get(id=self.cash.id)
        self.assertEqual(cash.balance, Decimal('0.00'))

    def test_unpost_entry_fails_for_unposted_entry(self):
        """Test unpost_entry fails for unposted entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        
        unpost_result = JournalEngine.unpost_entry(result['entry_id'])
        self.assertFalse(unpost_result['success'])
        self.assertTrue(any('not posted' in e.lower() for e in unpost_result['errors']))


class JournalEngineReverseEntryBehaviorTest(TransactionTestCase):
    """Test reverse_entry actual behavior."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_reverse_entry_creates_reversal_entry(self):
        """Test that reverse_entry creates a reversal entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Original entry',
            lines=lines
        )
        entry_id = result['entry_id']
        JournalEngine.post_entry(entry_id)
        
        reverse_result = JournalEngine.reverse_entry(entry_id, reason='Test reversal')
        self.assertTrue(reverse_result['success'])
        
        self.assertTrue(JournalEntry.objects.filter(entry_number__startswith='REV-').exists())

    def test_reverse_entry_swaps_debits_and_credits(self):
        """Test that reversal entry has swapped debits and credits."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Original entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        reverse_result = JournalEngine.reverse_entry(result['entry_id'])
        
        reverse_entry = JournalEntry.objects.get(id=reverse_result['entry_id'])
        cash_line = reverse_entry.lines.get(account_id=self.cash.id)
        self.assertEqual(cash_line.debit, Decimal('0.00'))
        self.assertEqual(cash_line.credit, Decimal('100.00'))

    def test_reverse_entry_fails_for_unposted_entry(self):
        """Test reverse_entry fails for unposted entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        
        reverse_result = JournalEngine.reverse_entry(result['entry_id'])
        self.assertFalse(reverse_result['success'])
        self.assertTrue(any('unposted' in e.lower() for e in reverse_result['errors']))


class JournalEngineRecalculateBalancesTest(TransactionTestCase):
    """Test recalculate_all_balances behavior."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_recalculate_all_balances_updates_all_accounts(self):
        """Test recalculate_all_balances updates all account balances."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '250.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '250.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        self.cash.refresh_from_db()
        self.revenue.refresh_from_db()
        self.assertEqual(self.cash.balance, Decimal('250.00'))
        self.assertEqual(self.revenue.balance, Decimal('250.00'))


class JournalEngineGetAccountLedgerTest(TransactionTestCase):
    """Test get_account_ledger behavior."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_get_account_ledger_returns_ledger_data(self):
        """Test get_account_ledger returns ledger data."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        ledger = JournalEngine.get_account_ledger(self.cash.id)
        self.assertEqual(ledger['account_code'], '1000')
        self.assertEqual(len(ledger['entries']), 1)

    def test_get_account_ledger_with_date_filter(self):
        """Test get_account_ledger with date filters."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        ledger = JournalEngine.get_account_ledger(
            self.cash.id,
            start_date=date.today() + timedelta(days=1)
        )
        self.assertEqual(len(ledger['entries']), 0)

    def test_get_account_ledger_running_balance(self):
        """Test get_account_ledger calculates running balance correctly."""
        lines1 = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result1 = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Entry 1',
            lines=lines1
        )
        JournalEngine.post_entry(result1['entry_id'])
        
        lines2 = [
            {'account_id': str(self.cash.id), 'debit': '50.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '50.00'}
        ]
        result2 = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Entry 2',
            lines=lines2
        )
        JournalEngine.post_entry(result2['entry_id'])
        
        ledger = JournalEngine.get_account_ledger(self.cash.id)
        entries = ledger['entries']
        self.assertEqual(entries[0]['running_balance'], Decimal('100.00'))
        self.assertEqual(entries[1]['running_balance'], Decimal('150.00'))


class JournalEngineDoubleEntryIntegrityTest(TransactionTestCase):
    """Test double-entry integrity - debits must equal credits."""

    def setUp(self):
        self.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        self.bank = Account.objects.create(
            code='1010', name='Bank', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_posted_entry_maintains_balance(self):
        """Test that posted entries maintain debit=credit balance."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '500.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '500.00'}
        ]
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=lines
        )
        JournalEngine.post_entry(result['entry_id'])
        
        entry = JournalEntry.objects.get(id=result['entry_id'])
        self.assertEqual(entry.total_debit, entry.total_credit)
        self.assertEqual(entry.total_debit, Decimal('500.00'))

    def test_multiple_entries_balance(self):
        """Test multiple entries maintain correct balances."""
        for i in range(3):
            lines = [
                {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
                {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
            ]
            result = JournalEngine.create_entry(
                entry_type='GENERAL',
                description=f'Entry {i}',
                lines=lines
            )
            JournalEngine.post_entry(result['entry_id'])
        
        cash = Account.objects.get(id=self.cash.id)
        self.assertEqual(cash.balance, Decimal('300.00'))
        
        revenue = Account.objects.get(id=self.revenue.id)
        self.assertEqual(revenue.balance, Decimal('300.00'))
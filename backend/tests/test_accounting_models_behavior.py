"""
Accounting model behavior tests.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase

from accounting.models import Account, JournalEntry, JournalEntryLine, Currency, ExchangeRate


class AccountModelTest(TestCase):
    """Test Account model."""

    def test_create_account(self):
        """Test creating an account."""
        acc = Account.objects.create(
            code='1000',
            name='Cash',
            account_type='ASSET',
            is_active=True
        )
        self.assertEqual(acc.name, 'Cash')
        self.assertEqual(acc.code, '1000')

    def test_account_str(self):
        """Test account string representation."""
        acc = Account.objects.create(code='1100', name='Bank', account_type='ASSET')
        self.assertIn('Bank', str(acc))

    def test_account_balance_default(self):
        """Test account balance defaults to zero."""
        acc = Account.objects.create(code='1200', name='Receivable', account_type='ASSET')
        self.assertEqual(acc.balance, Decimal('0'))

    def test_account_is_active_default(self):
        """Test account is_active defaults to True."""
        acc = Account.objects.create(code='1300', name='Test', account_type='ASSET')
        self.assertTrue(acc.is_active)


class JournalEntryModelTest(TestCase):
    """Test JournalEntry model."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET')
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE')

    def test_create_journal_entry(self):
        """Test creating a journal entry."""
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-0001',
            entry_date=date.today(),
            entry_type='GENERAL',
            description='Test entry',
            is_posted=False
        )
        self.assertEqual(entry.description, 'Test entry')

    def test_journal_entry_default_posted(self):
        """Test journal entry is_posted defaults to False."""
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-0002',
            entry_date=date.today(),
            entry_type='GENERAL',
            description='Test'
        )
        self.assertFalse(entry.is_posted)

    def test_journal_entry_total_debit_credit(self):
        """Test journal entry totals calculation."""
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-0003',
            entry_date=date.today(),
            entry_type='GENERAL',
            description='Test',
            is_posted=False
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.revenue,
            debit=Decimal('0.00'),
            credit=Decimal('100.00')
        )
        entry.refresh_from_db()
        self.assertEqual(entry.total_debit, Decimal('100.00'))
        self.assertEqual(entry.total_credit, Decimal('100.00'))
        self.assertTrue(entry.is_balanced)

    def test_journal_entry_unbalanced(self):
        """Test unbalanced journal entry."""
        entry = JournalEntry.objects.create(
            entry_number='JE-202601-0004',
            entry_date=date.today(),
            entry_type='GENERAL',
            description='Test'
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.revenue,
            debit=Decimal('0.00'),
            credit=Decimal('50.00')
        )
        entry.refresh_from_db()
        self.assertFalse(entry.is_balanced)


class JournalEntryLineModelTest(TestCase):
    """Test JournalEntryLine model."""

    def setUp(self):
        self.account = Account.objects.create(code='1000', name='Cash', account_type='ASSET')
        self.entry = JournalEntry.objects.create(
            entry_number='JE-202601-0005',
            entry_type='GENERAL',
            description='Test'
        )

    def setUp(self):
        self.account = Account.objects.create(code='1000', name='Cash', account_type='ASSET')
        self.entry = JournalEntry.objects.create(
            entry_number='JE-202601-0005',
            entry_date=date.today(),
            entry_type='GENERAL',
            description='Test'
        )

    def test_create_journal_entry_line(self):
        """Test creating a journal entry line."""
        line = JournalEntryLine.objects.create(
            entry=self.entry,
            account=self.account,
            debit=Decimal('50.00'),
            credit=Decimal('0.00')
        )
        self.assertEqual(line.debit, Decimal('50.00'))

    def test_journal_entry_line_debit_or_credit(self):
        """Test line has either debit or credit, not both."""
        line = JournalEntryLine.objects.create(
            entry=self.entry,
            account=self.account,
            debit=Decimal('50.00'),
            credit=Decimal('0.00')
        )
        self.assertTrue(line.debit > 0)
        self.assertEqual(line.credit, Decimal('0'))


class CurrencyModelTest(TestCase):
    """Test Currency model."""

    def test_create_currency(self):
        """Test creating a currency."""
        currency = Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            is_active=True
        )
        self.assertEqual(currency.code, 'USD')

    def test_currency_str(self):
        """Test currency string representation."""
        currency = Currency.objects.create(code='EUR', name='Euro', symbol='€')
        self.assertIn('EUR', str(currency))


class ExchangeRateModelTest(TestCase):
    """Test ExchangeRate model."""

    def setUp(self):
        self.usd = Currency.objects.create(code='USD', name='US Dollar', symbol='$')
        self.afn = Currency.objects.create(code='AFN', name='Afghani', symbol='؋')

    def test_create_exchange_rate(self):
        """Test creating an exchange rate."""
        rate = ExchangeRate.objects.create(
            from_currency=self.afn,
            to_currency=self.usd,
            rate=Decimal('0.014'),
            effective_date=date.today(),
            is_active=True
        )
        self.assertEqual(rate.rate, Decimal('0.014'))


class AccountHierarchyTest(TestCase):
    """Test account hierarchy relationships."""

    def test_account_with_parent(self):
        """Test account with parent relationship."""
        parent = Account.objects.create(code='1000', name='Assets', account_type='ASSET')
        child = Account.objects.create(
            code='1100',
            name='Cash',
            account_type='ASSET',
            parent=parent
        )
        self.assertEqual(child.parent, parent)

    def test_account_children(self):
        """Test account children relationship."""
        parent = Account.objects.create(code='1000', name='Assets', account_type='ASSET')
        Account.objects.create(code='1100', name='Cash', account_type='ASSET', parent=parent)
        Account.objects.create(code='1200', name='Bank', account_type='ASSET', parent=parent)
        self.assertEqual(parent.children.count(), 2)
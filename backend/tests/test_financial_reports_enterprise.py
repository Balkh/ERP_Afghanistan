"""
Enterprise financial report tests.
Tests trial balance, P&L, balance sheet, and ledger integrity.
"""

from decimal import Decimal
from django.test import TransactionTestCase
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine


class TrialBalanceEnterpriseTest(TransactionTestCase):
    """Test trial balance consistency and integrity."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='Accounts Receivable', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales Revenue', account_type='REVENUE', is_active=True)
        self.cogs = Account.objects.create(code='5000', name='COGS', account_type='EXPENSE', is_active=True)

    def test_trial_balance_empty_returns_structure(self):
        """Test trial balance returns proper structure when no entries."""
        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertIn('accounts', tb)
        self.assertIn('total_debit', tb)
        self.assertIn('total_credit', tb)

    def test_trial_balance_balanced_single_entry(self):
        """Test trial balance balances with single entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        result = JournalEngine.create_entry('SALE', 'Sale #1', lines)
        JournalEngine.post_entry(result['entry_id'])

        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertEqual(tb['total_debit'], tb['total_credit'])
        self.assertEqual(tb['total_debit'], Decimal('1000'))

    def test_trial_balance_multiple_entries(self):
        """Test trial balance with multiple entries."""
        lines1 = [
            {'account_id': str(self.cash.id), 'debit': '5000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '5000'},
        ]
        result1 = JournalEngine.create_entry('SALE', 'Sale #1', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        lines2 = [
            {'account_id': str(self.cash.id), 'debit': '3000', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '3000'},
        ]
        result2 = JournalEngine.create_entry('RECEIPT', 'Receipt #1', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertEqual(tb['total_debit'], tb['total_credit'])

    def test_trial_balance_excludes_unposted(self):
        """Test unposted entries don't appear in trial balance."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        result = JournalEngine.create_entry('SALE', 'Sale #1', lines)

        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        cash_row = next((a for a in tb['accounts'] if a['account_code'] == '1000'), None)
        if cash_row:
            self.assertEqual(cash_row['debit'], Decimal('0'))


class ProfitLossEnterpriseTest(TransactionTestCase):
    """Test P&L validation and revenue/expense aggregation."""

    def setUp(self):
        self.sales = Account.objects.create(code='4000', name='Sales Revenue', account_type='REVENUE', is_active=True)
        self.service = Account.objects.create(code='4100', name='Service Income', account_type='REVENUE', is_active=True)
        self.cogs = Account.objects.create(code='5000', name='COGS', account_type='EXPENSE', is_active=True)
        self.rent = Account.objects.create(code='5100', name='Rent Expense', account_type='EXPENSE', is_active=True)
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)

    def test_pnl_empty_returns_structure(self):
        """Test P&L returns proper structure when no data."""
        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertIn('revenue', pl)
        self.assertIn('expenses', pl)
        self.assertIn('net_income', pl)

    def test_pnl_single_revenue_entry(self):
        """Test P&L with single revenue entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '5000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '5000'},
        ]
        result = JournalEngine.create_entry('SALE', 'Sale #1', lines)
        JournalEngine.post_entry(result['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['total_revenue'], Decimal('5000'))

    def test_pnl_multiple_revenue_streams(self):
        """Test P&L aggregates multiple revenue accounts."""
        lines1 = [
            {'account_id': str(self.cash.id), 'debit': '3000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '3000'},
        ]
        result1 = JournalEngine.create_entry('SALE', 'Sale #1', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        lines2 = [
            {'account_id': str(self.cash.id), 'debit': '1500', 'credit': '0'},
            {'account_id': str(self.service.id), 'debit': '0', 'credit': '1500'},
        ]
        result2 = JournalEngine.create_entry('SERVICE', 'Service #1', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['total_revenue'], Decimal('4500'))

    def test_pnl_with_expenses(self):
        """Test P&L with revenue and expenses."""
        lines1 = [
            {'account_id': str(self.cash.id), 'debit': '5000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '5000'},
        ]
        result1 = JournalEngine.create_entry('SALE', 'Sale #1', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        lines2 = [
            {'account_id': str(self.cogs.id), 'debit': '2000', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '2000'},
        ]
        result2 = JournalEngine.create_entry('PURCHASE', 'Purchase #1', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['total_revenue'], Decimal('5000'))
        self.assertEqual(pl['total_expenses'], Decimal('2000'))
        self.assertEqual(pl['net_income'], Decimal('3000'))


class BalanceSheetEnterpriseTest(TransactionTestCase):
    """Test balance sheet integrity and account classification."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='Accounts Receivable', account_type='ASSET', is_active=True)
        self.ap = Account.objects.create(code='2000', name='Accounts Payable', account_type='LIABILITY', is_active=True)
        self.capital = Account.objects.create(code='3000', name='Owner Capital', account_type='EQUITY', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

    def test_bs_empty_returns_structure(self):
        """Test balance sheet returns proper structure when empty."""
        bs = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIn('assets', bs)
        self.assertIn('liabilities', bs)
        self.assertIn('equity', bs)

    def test_bs_with_assets(self):
        """Test balance sheet shows assets correctly."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '10000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '10000'},
        ]
        result = JournalEngine.create_entry('SALE', 'Sale #1', lines)
        JournalEngine.post_entry(result['entry_id'])

        bs = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIn('assets', bs)

    def test_bs_liabilities_present(self):
        """Test balance sheet includes liabilities section."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '5000', 'credit': '0'},
            {'account_id': str(self.ap.id), 'debit': '0', 'credit': '5000'},
        ]
        result = JournalEngine.create_entry('PURCHASE', 'Purchase #1', lines)
        JournalEngine.post_entry(result['entry_id'])

        bs = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIn('liabilities', bs)


class AccountLedgerEnterpriseTest(TransactionTestCase):
    """Test account ledger aggregation and correctness."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

    def test_ledger_empty_returns_structure(self):
        """Test ledger returns proper structure when no entries."""
        ledger = FinancialReportEngine.get_account_ledger(str(self.cash.id), timezone.now().date(), timezone.now().date())
        self.assertIn('account_code', ledger)
        self.assertIn('entries', ledger)
        self.assertIn('closing_balance', ledger)

    def test_ledger_with_entries(self):
        """Test ledger aggregates entries correctly."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '5000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '5000'},
        ]
        result = JournalEngine.create_entry('SALE', 'Sale #1', lines)
        JournalEngine.post_entry(result['entry_id'])

        ledger = FinancialReportEngine.get_account_ledger(str(self.cash.id), timezone.now().date(), timezone.now().date())
        self.assertGreater(len(ledger['entries']), 0)
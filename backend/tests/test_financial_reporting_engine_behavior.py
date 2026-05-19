"""
Financial Reporting Engine behavior tests.
"""

from decimal import Decimal
from django.test import TransactionTestCase
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine


class FinancialReportEngineTrialBalanceTest(TransactionTestCase):
    """Test Trial Balance report generation."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.bank = Account.objects.create(code='1100', name='Bank', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Sales Revenue', account_type='REVENUE', is_active=True)
        self.expense = Account.objects.create(code='5000', name='Operating Expense', account_type='EXPENSE', is_active=True)

    def test_trial_balance_returns_dict(self):
        """Test get_trial_balance returns dict structure."""
        result = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertIsInstance(result, dict)
        self.assertIn('accounts', result)

    def test_trial_balance_empty_when_no_data(self):
        """Test trial balance empty when no posted entries."""
        result = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertEqual(len(result['accounts']), 0)
        self.assertEqual(result['total_debit'], Decimal('0'))
        self.assertEqual(result['total_credit'], Decimal('0'))

    def test_trial_balance_single_entry(self):
        """Test trial balance with single posted entry."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '1000.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '1000.00'}
        ]
        result = JournalEngine.create_entry('SALE', 'Test sale', lines)
        JournalEngine.post_entry(result['entry_id'])

        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertTrue(len(tb['accounts']) > 0)
        self.assertEqual(tb['total_debit'], tb['total_credit'])

    def test_trial_balance_excludes_unposted(self):
        """Test trial balance excludes unposted entries."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '500.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '500.00'}
        ]
        JournalEngine.create_entry('SALE', 'Unposted', lines)

        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertEqual(len(tb['accounts']), 0)


class FinancialReportEngineProfitAndLossTest(TransactionTestCase):
    """Test Profit & Loss report generation."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)
        self.expense = Account.objects.create(code='5000', name='Expense', account_type='EXPENSE', is_active=True)

    def test_profit_loss_returns_dict(self):
        """Test get_profit_and_loss returns dict structure."""
        result = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertIsInstance(result, dict)
        self.assertIn('revenue', result)
        self.assertIn('expenses', result)

    def test_profit_loss_empty_when_no_data(self):
        """Test profit/loss empty when no data."""
        result = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(result['total_revenue'], Decimal('0'))
        self.assertEqual(result['total_expenses'], Decimal('0'))

    def test_profit_loss_with_revenue_only(self):
        """Test profit/loss with revenue entries."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '2000.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '2000.00'}
        ]
        result = JournalEngine.create_entry('SALE', 'Sale', lines)
        JournalEngine.post_entry(result['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['total_revenue'], Decimal('2000.00'))

    def test_profit_loss_with_expenses(self):
        """Test profit/loss with expense entries."""
        exp_lines = [
            {'account_id': str(self.expense.id), 'debit': '800.00', 'credit': '0.00'},
            {'account_id': str(self.cash.id), 'debit': '0.00', 'credit': '800.00'}
        ]
        result = JournalEngine.create_entry('EXPENSE', 'Expense', exp_lines)
        JournalEngine.post_entry(result['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['total_expenses'], Decimal('800.00'))

    def test_profit_loss_net_income_calculation(self):
        """Test net income calculation."""
        rev_lines = [
            {'account_id': str(self.cash.id), 'debit': '1000.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '1000.00'}
        ]
        r = JournalEngine.create_entry('SALE', 'Revenue', rev_lines)
        JournalEngine.post_entry(r['entry_id'])

        exp_lines = [
            {'account_id': str(self.expense.id), 'debit': '300.00', 'credit': '0.00'},
            {'account_id': str(self.cash.id), 'debit': '0.00', 'credit': '300.00'}
        ]
        e = JournalEngine.create_entry('EXPENSE', 'Expense', exp_lines)
        JournalEngine.post_entry(e['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['net_income'], Decimal('700.00'))


class FinancialReportEngineBalanceSheetTest(TransactionTestCase):
    """Test Balance Sheet report generation."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.equipment = Account.objects.create(code='1200', name='Equipment', account_type='ASSET', is_active=True)
        self.capital = Account.objects.create(code='3000', name='Capital', account_type='EQUITY', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)

    def test_balance_sheet_returns_dict(self):
        """Test get_balance_sheet returns dict structure."""
        result = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIsInstance(result, dict)
        self.assertIn('assets', result)
        self.assertIn('liabilities', result)
        self.assertIn('equity', result)

    def test_balance_sheet_empty_when_no_data(self):
        """Test balance sheet empty when no data."""
        result = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIn('assets', result)

    def test_balance_sheet_with_assets(self):
        """Test balance sheet shows assets."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '5000.00', 'credit': '0.00'},
            {'account_id': str(self.capital.id), 'debit': '0.00', 'credit': '5000.00'}
        ]
        result = JournalEngine.create_entry('GENERAL', 'Capital contribution', lines)
        JournalEngine.post_entry(result['entry_id'])

        bs = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIn('assets', bs)


class FinancialReportEngineCashFlowTest(TransactionTestCase):
    """Test Cash Flow Statement generation."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)

    def test_cash_flow_returns_dict(self):
        """Test get_cash_flow_statement returns dict structure."""
        result = FinancialReportEngine.get_cash_flow_statement(timezone.now().date(), timezone.now().date())
        self.assertIsInstance(result, dict)
        self.assertIn('operating_activities', result)
        self.assertIn('net_change_in_cash', result)

    def test_cash_flow_empty_when_no_data(self):
        """Test cash flow empty when no data."""
        result = FinancialReportEngine.get_cash_flow_statement(timezone.now().date(), timezone.now().date())
        self.assertEqual(result['net_change_in_cash'], Decimal('0'))


class FinancialReportEngineAccountLedgerTest(TransactionTestCase):
    """Test Account Ledger report generation."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)

    def test_account_ledger_returns_dict(self):
        """Test get_account_ledger returns dict structure."""
        result = FinancialReportEngine.get_account_ledger(self.cash.id, timezone.now().date(), timezone.now().date())
        self.assertIsInstance(result, dict)
        self.assertIn('account_code', result)

    def test_account_ledger_with_posted_entries(self):
        """Test account ledger shows posted entries."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry('SALE', 'Test', lines)
        JournalEngine.post_entry(result['entry_id'])

        ledger = FinancialReportEngine.get_account_ledger(self.cash.id, timezone.now().date(), timezone.now().date())
        self.assertEqual(len(ledger['entries']), 1)

    def test_account_ledger_opening_balance(self):
        """Test account ledger opening balance."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '500.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '500.00'}
        ]
        result = JournalEngine.create_entry('SALE', 'Test', lines)
        JournalEngine.post_entry(result['entry_id'])

        ledger = FinancialReportEngine.get_account_ledger(self.cash.id, timezone.now().date(), timezone.now().date())
        self.assertIn('opening_balance', ledger)
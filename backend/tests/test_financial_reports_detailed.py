"""
Additional Financial Report Engine Tests.

These tests focus on the financial report engine without complex dependencies.
"""

from decimal import Decimal
from django.test import TransactionTestCase
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine


class TrialBalanceDetailedTest(TransactionTestCase):
    """Detailed trial balance tests."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='1100', name='Bank', account_type='ASSET', is_active=True)
        self.r1 = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.e1 = Account.objects.create(code='5000', name='Rent', account_type='EXPENSE', is_active=True)
        self.e2 = Account.objects.create(code='5100', name='Salaries', account_type='EXPENSE', is_active=True)
        self.l1 = Account.objects.create(code='2000', name='Loan', account_type='LIABILITY', is_active=True)
        self.eq1 = Account.objects.create(code='3000', name='Capital', account_type='EQUITY', is_active=True)

    def test_trial_balance_zero_state(self):
        """Test trial balance at zero state."""
        result = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertEqual(result['total_debit'], Decimal('0'))
        self.assertEqual(result['total_credit'], Decimal('0'))

    def test_trial_balance_single_posted(self):
        """Test trial balance with one posted entry."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.r1.id), 'debit': '0', 'credit': '1000'}
        ]
        result = JournalEngine.create_entry('SALE', 'Sale 1', lines)
        JournalEngine.post_entry(result['entry_id'])

        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertTrue(tb['total_debit'] > 0)
        self.assertTrue(tb['total_credit'] > 0)

    def test_trial_balance_totals_equal(self):
        """Test debits equal credits."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.r1.id), 'debit': '0', 'credit': '500'}
        ]
        result = JournalEngine.create_entry('SALE', 'Sale 2', lines)
        JournalEngine.post_entry(result['entry_id'])

        tb = FinancialReportEngine.get_trial_balance(timezone.now().date())
        self.assertEqual(tb['total_debit'], tb['total_credit'])


class ProfitLossDetailedTest(TransactionTestCase):
    """Detailed profit & loss tests."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.rent = Account.objects.create(code='5000', name='Rent', account_type='EXPENSE', is_active=True)
        self.salary = Account.objects.create(code='5100', name='Salary', account_type='EXPENSE', is_active=True)

    def test_pl_zero_revenue(self):
        """Test P&L with zero revenue."""
        result = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(result['total_revenue'], Decimal('0'))

    def test_pl_with_multiple_revenue_entries(self):
        """Test P&L with multiple revenue entries."""
        for i in range(3):
            lines = [
                {'account_id': str(self.cash.id), 'debit': '200', 'credit': '0'},
                {'account_id': str(self.sales.id), 'debit': '0', 'credit': '200'}
            ]
            r = JournalEngine.create_entry('SALE', f'Sale {i}', lines)
            JournalEngine.post_entry(r['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['total_revenue'], Decimal('600'))

    def test_pl_with_expenses(self):
        """Test P&L with expenses."""
        exp_lines = [
            {'account_id': str(self.rent.id), 'debit': '100', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '100'}
        ]
        r = JournalEngine.create_entry('EXPENSE', 'Rent', exp_lines)
        JournalEngine.post_entry(r['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['total_expenses'], Decimal('100'))

    def test_pl_net_profit_calculation(self):
        """Test net profit = revenue - expenses."""
        rev = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'}
        ]
        r1 = JournalEngine.create_entry('SALE', 'Sales', rev)
        JournalEngine.post_entry(r1['entry_id'])

        exp = [
            {'account_id': str(self.rent.id), 'debit': '300', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '300'}
        ]
        r2 = JournalEngine.create_entry('EXPENSE', 'Exp', exp)
        JournalEngine.post_entry(r2['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertEqual(pl['net_income'], Decimal('700'))

    def test_pl_net_loss(self):
        """Test net loss when expenses > revenue."""
        exp = [
            {'account_id': str(self.rent.id), 'debit': '800', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '800'}
        ]
        r = JournalEngine.create_entry('EXPENSE', 'High expense', exp)
        JournalEngine.post_entry(r['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(timezone.now().date(), timezone.now().date())
        self.assertLess(pl['net_income'], Decimal('0'))


class BalanceSheetDetailedTest(TransactionTestCase):
    """Detailed balance sheet tests."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.equip = Account.objects.create(code='1200', name='Equipment', account_type='ASSET', is_active=True)
        self.ap = Account.objects.create(code='2100', name='AP', account_type='LIABILITY', is_active=True)
        self.capital = Account.objects.create(code='3000', name='Capital', account_type='EQUITY', is_active=True)
        self.retained = Account.objects.create(code='3100', name='Retained', account_type='EQUITY', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

    def test_bs_structure(self):
        """Test balance sheet has required structure."""
        result = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIn('assets', result)
        self.assertIn('liabilities', result)
        self.assertIn('equity', result)

    def test_bs_with_assets_and_equity(self):
        """Test BS with assets and equity."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '10000', 'credit': '0'},
            {'account_id': str(self.capital.id), 'debit': '0', 'credit': '10000'}
        ]
        r = JournalEngine.create_entry('GENERAL', 'Capital', lines)
        JournalEngine.post_entry(r['entry_id'])

        bs = FinancialReportEngine.get_balance_sheet(timezone.now().date())
        self.assertIn('assets', bs)


class CashFlowDetailedTest(TransactionTestCase):
    """Detailed cash flow tests."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.expense = Account.objects.create(code='5000', name='Expense', account_type='EXPENSE', is_active=True)

    def test_cf_structure(self):
        """Test cash flow has required structure."""
        result = FinancialReportEngine.get_cash_flow_statement(timezone.now().date(), timezone.now().date())
        self.assertIn('operating_activities', result)
        self.assertIn('net_change_in_cash', result)

    def test_cf_zero_state(self):
        """Test cash flow at zero state."""
        result = FinancialReportEngine.get_cash_flow_statement(timezone.now().date(), timezone.now().date())
        self.assertEqual(result['net_change_in_cash'], Decimal('0'))


class AccountLedgerDetailedTest(TransactionTestCase):
    """Detailed account ledger tests."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

    def test_ledger_structure(self):
        """Test ledger has required structure."""
        result = FinancialReportEngine.get_account_ledger(self.cash.id, timezone.now().date(), timezone.now().date())
        self.assertIn('account_code', result)
        self.assertIn('entries', result)

    def test_ledger_with_entries(self):
        """Test ledger with entries."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '500'}
        ]
        r = JournalEngine.create_entry('SALE', 'Sale', lines)
        JournalEngine.post_entry(r['entry_id'])

        ledger = FinancialReportEngine.get_account_ledger(self.cash.id, timezone.now().date(), timezone.now().date())
        self.assertEqual(len(ledger['entries']), 1)

    def test_ledger_running_balance(self):
        """Test ledger running balance calculation."""
        for i in range(3):
            lines = [
                {'account_id': str(self.cash.id), 'debit': str(100 + i*10), 'credit': '0'},
                {'account_id': str(self.sales.id), 'debit': '0', 'credit': str(100 + i*10)}
            ]
            r = JournalEngine.create_entry('SALE', f'Sale {i}', lines)
            JournalEngine.post_entry(r['entry_id'])

        ledger = FinancialReportEngine.get_account_ledger(self.cash.id, timezone.now().date(), timezone.now().date())
        entries = ledger['entries']
        self.assertEqual(entries[0]['running_balance'], Decimal('100'))
        self.assertEqual(entries[1]['running_balance'], Decimal('210'))
        self.assertEqual(entries[2]['running_balance'], Decimal('330'))
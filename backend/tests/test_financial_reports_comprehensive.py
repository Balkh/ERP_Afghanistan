"""
Comprehensive Financial Reports Tests
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db.models import Q

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.financial_reports import FinancialReportEngine


class TrialBalanceComprehensiveTests(TestCase):
    """Comprehensive trial balance tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.asset = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        cls.revenue = Account.objects.create(
            code='4000', name='Sales', account_type='REVENUE', is_active=True
        )
        cls.expense = Account.objects.create(
            code='5000', name='Expenses', account_type='EXPENSE', is_active=True
        )
        
    def test_trial_balance_empty(self):
        """Test trial balance with no entries."""
        result = FinancialReportEngine.get_trial_balance()
        self.assertEqual(result['report_type'], 'Trial Balance')
        self.assertIn('accounts', result)
        self.assertTrue(result['is_balanced'])
        
    def test_trial_balance_with_debit_and_credit(self):
        """Test trial balance with entries."""
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            description='Test Entry',
            is_posted=True,
            is_active=True
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.asset, debit=Decimal('100.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.revenue, debit=Decimal('0.00'), credit=Decimal('100.00')
        )
        
        result = FinancialReportEngine.get_trial_balance()
        self.assertEqual(result['total_debit'], Decimal('100.00'))
        self.assertEqual(result['total_credit'], Decimal('100.00'))
        
    def test_trial_balance_exclude_zero(self):
        """Test trial balance exclude zero balances."""
        result = FinancialReportEngine.get_trial_balance(include_zero=False)
        self.assertIn('accounts', result)
        
    def test_trial_balance_include_zero(self):
        """Test trial balance include zero balances."""
        result = FinancialReportEngine.get_trial_balance(include_zero=True)
        self.assertIn('accounts', result)
        
    def test_trial_balance_by_type(self):
        """Test trial balance by type grouping."""
        result = FinancialReportEngine.get_trial_balance()
        self.assertIn('by_type', result)


class ProfitAndLossComprehensiveTests(TestCase):
    """Comprehensive P&L tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.revenue = Account.objects.create(
            code='4000', name='Sales Revenue', account_type='REVENUE', is_active=True
        )
        cls.expense = Account.objects.create(
            code='5000', name='Rent Expense', account_type='EXPENSE', is_active=True
        )
        
    def test_profit_and_loss_empty(self):
        """Test P&L with no entries."""
        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        self.assertIn('revenue', result)
        self.assertIn('expenses', result)
        
    def test_profit_and_loss_with_data(self):
        """Test P&L with entries."""
        entry = JournalEntry.objects.create(
            entry_date=date.today() - timedelta(days=5),
            description='Sales',
            entry_number='JE-000001',
            is_posted=True,
            is_active=True
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.revenue, debit=Decimal('0.00'), credit=Decimal('500.00')
        )
        
        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        self.assertIn('net_income', result)
        
    def test_profit_and_loss_with_comparison(self):
        """Test P&L with comparison period."""
        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
            compare_start=date.today() - timedelta(days=90),
            compare_end=date.today() - timedelta(days=60)
        )
        self.assertIn('revenue', result)


class BalanceSheetComprehensiveTests(TestCase):
    """Comprehensive Balance Sheet tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.asset = Account.objects.create(
            code='1100', name='Accounts Receivable', account_type='ASSET', 
            account_category='CURRENT_ASSET', is_active=True
        )
        cls.liability = Account.objects.create(
            code='2000', name='Accounts Payable', account_type='LIABILITY',
            account_category='CURRENT_LIABILITY', is_active=True
        )
        cls.equity = Account.objects.create(
            code='3000', name='Capital', account_type='EQUITY', is_active=True
        )
        
    def test_balance_sheet_empty(self):
        """Test balance sheet with no entries."""
        result = FinancialReportEngine.get_balance_sheet()
        self.assertIn('assets', result)
        self.assertIn('liabilities', result)
        self.assertIn('equity', result)
        
    def test_balance_sheet_with_data(self):
        """Test balance sheet with entries."""
        entry = JournalEntry.objects.create(
            entry_date=date.today() - timedelta(days=10),
            description='AR Increase',
            is_posted=True,
            is_active=True
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.asset, debit=Decimal('1000.00'), credit=Decimal('0.00')
        )
        
        result = FinancialReportEngine.get_balance_sheet()
        self.assertIn('is_balanced', result)
        
    def test_balance_sheet_exclude_net_income(self):
        """Test balance sheet without net income."""
        result = FinancialReportEngine.get_balance_sheet(include_net_income=False)
        self.assertIn('assets', result)
        
    def test_balance_sheet_date_filter(self):
        """Test balance sheet with specific date."""
        result = FinancialReportEngine.get_balance_sheet(as_of_date=date.today())
        self.assertIn('as_of_date', result)


class CashFlowComprehensiveTests(TestCase):
    """Comprehensive Cash Flow tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        cls.revenue = Account.objects.create(
            code='4000', name='Sales', account_type='REVENUE', is_active=True
        )
        
    def test_cash_flow_empty(self):
        """Test cash flow with no entries."""
        result = FinancialReportEngine.get_cash_flow_statement(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        self.assertIn('operating_activities', result)
        self.assertIn('net_change_in_cash', result)
        
    def test_cash_flow_with_data(self):
        """Test cash flow with entries."""
        entry = JournalEntry.objects.create(
            entry_date=date.today() - timedelta(days=5),
            description='Sale',
            is_posted=True,
            is_active=True
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.cash, debit=Decimal('1000.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.revenue, debit=Decimal('0.00'), credit=Decimal('1000.00')
        )
        
        result = FinancialReportEngine.get_cash_flow_statement(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        self.assertIn('operating_activities', result)


class AccountLedgerComprehensiveTests(TestCase):
    """Comprehensive Account Ledger tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        
    def test_account_ledger_empty(self):
        """Test account ledger with no entries."""
        result = FinancialReportEngine.get_account_ledger(
            account_id=str(self.cash.id),
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        self.assertIn('account_code', result)
        
    def test_account_ledger_with_entries(self):
        """Test account ledger with entries."""
        entry = JournalEntry.objects.create(
            entry_date=date.today() - timedelta(days=5),
            description='Test Entry',
            is_posted=True,
            is_active=True
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.cash, debit=Decimal('500.00'), credit=Decimal('0.00')
        )
        
        result = FinancialReportEngine.get_account_ledger(
            account_id=str(self.cash.id),
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        self.assertIn('entries', result)


class AccountSummaryTests(TestCase):
    """Account Summary tests."""
    
    def test_account_summary_empty(self):
        """Test account summary with no data."""
        result = FinancialReportEngine.get_account_summary()
        self.assertIn('ASSET', result)
        
    def test_account_summary_with_date(self):
        """Test account summary with date filter."""
        result = FinancialReportEngine.get_account_summary(as_of_date=date.today())
        self.assertIn('ASSET', result)


class ARAgingTests(TestCase):
    """AR Aging tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.ar = Account.objects.create(
            code='1100', name='Accounts Receivable', account_type='ASSET',
            account_category='CURRENT_ASSET', is_active=True
        )
        
    def test_ar_aging_empty(self):
        """Test AR aging with no data."""
        result = FinancialReportEngine.get_ar_aging()
        self.assertIn('buckets', result)
        
    def test_ar_aging_with_custom_buckets(self):
        """Test AR aging with custom buckets."""
        buckets = [30, 60, 90]
        result = FinancialReportEngine.get_ar_aging(buckets=buckets)
        self.assertIn('buckets', result)


class APAgingTests(TestCase):
    """AP Aging tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.ap = Account.objects.create(
            code='2000', name='Accounts Payable', account_type='LIABILITY',
            account_category='CURRENT_LIABILITY', is_active=True
        )
        
    def test_ap_aging_empty(self):
        """Test AP aging with no data."""
        result = FinancialReportEngine.get_ap_aging()
        self.assertIn('buckets', result)
        
    def test_ap_aging_with_custom_buckets(self):
        """Test AP aging with custom buckets."""
        buckets = [30, 60, 90]
        result = FinancialReportEngine.get_ap_aging(buckets=buckets)
        self.assertIn('buckets', result)


class HelperMethodTests(TestCase):
    """Test private helper methods."""
    
    @classmethod
    def setUpTestData(cls):
        cls.account = Account.objects.create(
            code='1000', name='Test Account', account_type='ASSET', is_active=True
        )
        
    def test_get_account_change_exists(self):
        """Test _get_account_change method exists."""
        self.assertTrue(hasattr(FinancialReportEngine, '_get_account_change'))
        
    def test_get_account_change_returns_decimal(self):
        """Test _get_account_change returns decimal."""
        result = FinancialReportEngine._get_account_change(
            self.account,
            date.today() - timedelta(days=30),
            date.today()
        )
        self.assertIsInstance(result, Decimal)
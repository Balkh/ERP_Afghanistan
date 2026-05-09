"""
Comprehensive tests for Financial Report Engine.

Covers:
- Trial Balance report generation and balancing
- Profit & Loss with revenue, COGS, expenses, net income, and comparison
- Balance Sheet with assets, liabilities, equity, and net income inclusion
- Cash Flow Statement (operating, investing, financing activities)
- Account Ledger with running balance
- Account Summary by type
- AR/AP Aging reports with bucket classification
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from tests.base import BaseTestCase
from tests.factories import (
    AccountFactory,
    JournalEntryFactory,
    JournalEntryLineFactory,
    CustomerFactory,
    SupplierFactory,
    SalesInvoiceFactory,
    PurchaseInvoiceFactory,
)
from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.financial_reports import FinancialReportEngine


class TrialBalanceTests(BaseTestCase):
    """Tests for trial balance report generation."""

    def test_empty_trial_balance(self):
        """Trial balance with no journal entries returns zero totals."""
        result = FinancialReportEngine.get_trial_balance()
        self.assertEqual(result['total_debit'], Decimal('0.00'))
        self.assertEqual(result['total_credit'], Decimal('0.00'))
        self.assertTrue(result['is_balanced'])
        self.assertEqual(result['difference'], Decimal('0.00'))

    def test_trial_balance_with_entries(self):
        """Trial balance reflects posted journal entries."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('1000.00'),
        )

        result = FinancialReportEngine.get_trial_balance(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['total_debit'], Decimal('1000.00'))
        self.assertEqual(result['total_credit'], Decimal('1000.00'))
        self.assertTrue(result['is_balanced'])
        self.assertEqual(len(result['accounts']), 2)

    def test_trial_balance_excludes_unposted(self):
        """Unposted entries are excluded from trial balance."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=False,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('500.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('500.00'),
        )

        result = FinancialReportEngine.get_trial_balance(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['total_debit'], Decimal('0.00'))
        self.assertEqual(result['total_credit'], Decimal('0.00'))

    def test_trial_balance_excludes_inactive_accounts(self):
        """Inactive accounts are excluded from trial balance."""
        inactive = AccountFactory.create(
            code='9999',
            name='Inactive Account',
            account_type='ASSET',
            is_active=False,
        )
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=inactive,
            debit=Decimal('200.00'),
            credit=Decimal('0.00'),
        )

        result = FinancialReportEngine.get_trial_balance(as_of_date=date(2025, 1, 31))

        account_codes = [a['account_code'] for a in result['accounts']]
        self.assertNotIn('9999', account_codes)

    def test_trial_balance_date_filter(self):
        """Entries after as_of_date are excluded."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 3, 1),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('300.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('300.00'),
        )

        result = FinancialReportEngine.get_trial_balance(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['total_debit'], Decimal('0.00'))

    def test_trial_balance_balance_type_asset(self):
        """Asset accounts show correct balance type."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00'),
        )

        result = FinancialReportEngine.get_trial_balance(as_of_date=date(2025, 1, 31))

        cash_row = next(a for a in result['accounts'] if a['account_code'] == '1000')
        self.assertEqual(cash_row['balance_type'], 'DEBIT')
        self.assertEqual(cash_row['net_balance'], Decimal('1000.00'))

    def test_trial_balance_balance_type_liability(self):
        """Liability accounts show correct balance type."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_ap,
            debit=Decimal('0.00'),
            credit=Decimal('500.00'),
        )

        result = FinancialReportEngine.get_trial_balance(as_of_date=date(2025, 1, 31))

        ap_row = next(a for a in result['accounts'] if a['account_code'] == '2000')
        self.assertEqual(ap_row['balance_type'], 'CREDIT')
        self.assertEqual(ap_row['net_balance'], Decimal('500.00'))

    def test_trial_balance_include_zero(self):
        """Zero-balance accounts included when include_zero=True."""
        result = FinancialReportEngine.get_trial_balance(include_zero=True)
        self.assertTrue(len(result['accounts']) > 0)

    def test_trial_balance_grouped_by_type(self):
        """Accounts are grouped by account type."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('100.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('100.00'),
        )

        result = FinancialReportEngine.get_trial_balance(as_of_date=date(2025, 1, 31))

        self.assertIn('ASSET', result['by_type'])
        self.assertIn('REVENUE', result['by_type'])


class ProfitAndLossTests(BaseTestCase):
    """Tests for profit and loss report."""

    def _create_revenue_entry(self, amount, entry_date=None):
        """Helper to create a revenue journal entry."""
        if entry_date is None:
            entry_date = date(2025, 1, 15)
        entry = JournalEntryFactory.create(entry_date=entry_date, is_posted=True)
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_ar,
            debit=amount,
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=amount,
        )
        return entry

    def _create_expense_entry(self, amount, entry_date=None):
        """Helper to create an expense journal entry."""
        if entry_date is None:
            entry_date = date(2025, 1, 15)
        entry = JournalEntryFactory.create(entry_date=entry_date, is_posted=True)
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_expense,
            debit=amount,
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('0.00'),
            credit=amount,
        )
        return entry

    def _create_cogs_entry(self, amount, entry_date=None):
        """Helper to create a COGS journal entry."""
        if entry_date is None:
            entry_date = date(2025, 1, 15)
        entry = JournalEntryFactory.create(entry_date=entry_date, is_posted=True)
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cogs,
            debit=amount,
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_inventory,
            debit=Decimal('0.00'),
            credit=amount,
        )
        return entry

    def test_pnl_with_revenue_only(self):
        """P&L with only revenue shows correct totals."""
        self._create_revenue_entry(Decimal('5000.00'))

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['total_revenue'], Decimal('5000.00'))
        self.assertEqual(result['total_cogs'], Decimal('0.00'))
        self.assertEqual(result['total_expenses'], Decimal('0.00'))
        self.assertEqual(result['gross_profit'], Decimal('5000.00'))
        self.assertEqual(result['net_income'], Decimal('5000.00'))
        self.assertTrue(result['is_profitable'])

    def test_pnl_with_expenses(self):
        """P&L with revenue and expenses calculates net income correctly."""
        self._create_revenue_entry(Decimal('10000.00'))
        self._create_expense_entry(Decimal('3000.00'))

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['net_income'], Decimal('7000.00'))
        self.assertTrue(result['is_profitable'])

    def test_pnl_with_cogs(self):
        """P&L calculates gross profit correctly with COGS."""
        self._create_revenue_entry(Decimal('10000.00'))
        self._create_cogs_entry(Decimal('4000.00'))

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['gross_profit'], Decimal('6000.00'))
        self.assertEqual(result['total_cogs'], Decimal('4000.00'))

    def test_pnl_net_loss(self):
        """P&L shows loss when expenses exceed revenue."""
        self._create_revenue_entry(Decimal('2000.00'))
        self._create_expense_entry(Decimal('5000.00'))

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['net_income'], Decimal('-3000.00'))
        self.assertFalse(result['is_profitable'])

    def test_pnl_empty_period(self):
        """P&L for empty period returns zero totals."""
        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['total_revenue'], Decimal('0.00'))
        self.assertEqual(result['net_income'], Decimal('0.00'))
        self.assertFalse(result['is_profitable'])

    def test_pnl_comparison(self):
        """P&L includes prior period comparison when dates provided."""
        self._create_revenue_entry(Decimal('5000.00'), entry_date=date(2025, 1, 15))
        self._create_revenue_entry(Decimal('7000.00'), entry_date=date(2025, 2, 15))

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 28),
            compare_start=date(2025, 1, 1),
            compare_end=date(2025, 1, 31),
        )

        self.assertIsNotNone(result['comparison'])
        self.assertEqual(result['comparison']['total_revenue'], Decimal('5000.00'))
        self.assertEqual(result['comparison']['net_income'], Decimal('5000.00'))
        self.assertIn('revenue_growth_pct', result)

    def test_pnl_without_comparison(self):
        """P&L without comparison dates has no comparison data."""
        self._create_revenue_entry(Decimal('3000.00'))

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertIsNone(result.get('comparison'))

    def test_pnl_date_filter(self):
        """P&L only includes entries within the date range."""
        self._create_revenue_entry(Decimal('1000.00'), entry_date=date(2024, 12, 15))
        self._create_revenue_entry(Decimal('2000.00'), entry_date=date(2025, 1, 15))

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['total_revenue'], Decimal('2000.00'))

    def test_pnl_excludes_unposted(self):
        """P&L excludes unposted journal entries."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=False,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('9999.00'),
        )

        result = FinancialReportEngine.get_profit_and_loss(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['total_revenue'], Decimal('0.00'))


class BalanceSheetTests(BaseTestCase):
    """Tests for balance sheet report."""

    def test_empty_balance_sheet(self):
        """Balance sheet with no data shows zero totals."""
        result = FinancialReportEngine.get_balance_sheet(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['assets']['total'], Decimal('0.00'))
        self.assertEqual(result['liabilities']['total'], Decimal('0.00'))
        self.assertEqual(result['equity']['total'], Decimal('0.00'))
        self.assertTrue(result['is_balanced'])

    def test_balance_sheet_with_asset(self):
        """Balance sheet reflects asset entries."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('10000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_equity,
            debit=Decimal('0.00'),
            credit=Decimal('10000.00'),
        )

        result = FinancialReportEngine.get_balance_sheet(
            as_of_date=date(2025, 1, 31),
            include_net_income=False,
        )

        self.assertEqual(result['assets']['total'], Decimal('10000.00'))
        self.assertEqual(result['equity']['total'], Decimal('10000.00'))
        self.assertTrue(result['is_balanced'])

    def test_balance_sheet_with_liability(self):
        """Balance sheet includes liabilities."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_inventory,
            debit=Decimal('5000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_ap,
            debit=Decimal('0.00'),
            credit=Decimal('5000.00'),
        )

        result = FinancialReportEngine.get_balance_sheet(
            as_of_date=date(2025, 1, 31),
            include_net_income=False,
        )

        self.assertEqual(result['liabilities']['total'], Decimal('5000.00'))
        self.assertEqual(result['assets']['total'], Decimal('5000.00'))
        self.assertTrue(result['is_balanced'])

    def test_balance_sheet_includes_net_income(self):
        """Balance sheet includes current year net income in equity."""
        revenue_entry = JournalEntryFactory.create(
            entry_date=date(2025, 6, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=revenue_entry,
            account=self.account_cash,
            debit=Decimal('8000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=revenue_entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('8000.00'),
        )

        result = FinancialReportEngine.get_balance_sheet(
            as_of_date=date(2025, 6, 30),
            include_net_income=True,
        )

        self.assertEqual(result['assets']['total'], Decimal('8000.00'))
        total_le = result['total_liabilities_equity']
        self.assertEqual(total_le, Decimal('8000.00'))
        self.assertTrue(result['is_balanced'])

    def test_balance_sheet_without_net_income(self):
        """Balance sheet excludes net income when flag is False."""
        self._create_balanced_entry(
            date(2025, 3, 1),
            self.account_cash,
            self.account_equity,
            Decimal('3000.00'),
        )

        result = FinancialReportEngine.get_balance_sheet(
            as_of_date=date(2025, 3, 31),
            include_net_income=False,
        )

        equity_sections = [s['category'] for s in result['equity']['sections']]
        self.assertNotIn('NET_INCOME', equity_sections)

    def _create_balanced_entry(self, entry_date, debit_account, credit_account, amount):
        """Helper to create a balanced journal entry."""
        entry = JournalEntryFactory.create(entry_date=entry_date, is_posted=True)
        JournalEntryLineFactory.create(
            entry=entry,
            account=debit_account,
            debit=amount,
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=credit_account,
            debit=Decimal('0.00'),
            credit=amount,
        )

    def test_balance_sheet_date_filter(self):
        """Balance sheet only includes entries up to as_of_date."""
        self._create_balanced_entry(
            date(2025, 3, 1),
            self.account_cash,
            self.account_equity,
            Decimal('5000.00'),
        )

        result = FinancialReportEngine.get_balance_sheet(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['assets']['total'], Decimal('0.00'))

    def test_balance_sheet_excludes_inactive(self):
        """Balance sheet excludes inactive accounts."""
        inactive_asset = AccountFactory.create(
            code='1999',
            name='Inactive Asset',
            account_type='ASSET',
            account_category='CURRENT_ASSET',
            is_active=False,
        )
        self._create_balanced_entry(
            date(2025, 1, 15),
            inactive_asset,
            self.account_equity,
            Decimal('1000.00'),
        )

        result = FinancialReportEngine.get_balance_sheet(
            as_of_date=date(2025, 1, 31),
            include_net_income=False,
        )

        self.assertEqual(result['assets']['total'], Decimal('0.00'))

    def test_balance_sheet_excludes_unposted(self):
        """Balance sheet excludes unposted entries."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=False,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('7000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_equity,
            debit=Decimal('0.00'),
            credit=Decimal('7000.00'),
        )

        result = FinancialReportEngine.get_balance_sheet(
            as_of_date=date(2025, 1, 31),
            include_net_income=False,
        )

        self.assertEqual(result['assets']['total'], Decimal('0.00'))


class CashFlowStatementTests(BaseTestCase):
    """Tests for cash flow statement generation."""

    def test_empty_cash_flow(self):
        """Cash flow with no data returns zero totals."""
        result = FinancialReportEngine.get_cash_flow_statement(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['net_change_in_cash'], Decimal('0.00'))
        self.assertEqual(result['opening_cash_balance'], Decimal('0.00'))
        self.assertEqual(result['closing_cash_balance'], Decimal('0.00'))

    def test_cash_flow_operating_from_net_income(self):
        """Cash flow includes net income in operating activities."""
        revenue_entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=revenue_entry,
            account=self.account_cash,
            debit=Decimal('5000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=revenue_entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('5000.00'),
        )

        result = FinancialReportEngine.get_cash_flow_statement(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertEqual(result['operating_activities']['net_income'], Decimal('5000.00'))

    def test_cash_flow_working_capital_changes(self):
        """Cash flow includes working capital changes."""
        revenue_entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=revenue_entry,
            account=self.account_ar,
            debit=Decimal('3000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=revenue_entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('3000.00'),
        )

        result = FinancialReportEngine.get_cash_flow_statement(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertTrue(len(result['operating_activities']['working_capital_changes']) > 0)

    def test_cash_flow_structure(self):
        """Cash flow has correct report structure."""
        result = FinancialReportEngine.get_cash_flow_statement(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        self.assertIn('operating_activities', result)
        self.assertIn('investing_activities', result)
        self.assertIn('financing_activities', result)
        self.assertIn('net_change_in_cash', result)
        self.assertIn('opening_cash_balance', result)
        self.assertIn('closing_cash_balance', result)


class AccountLedgerTests(BaseTestCase):
    """Tests for account ledger report."""

    def test_ledger_account_not_found(self):
        """Ledger returns error for non-existent account."""
        result = FinancialReportEngine.get_account_ledger(str(uuid.uuid4()))
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Account not found')

    def test_ledger_empty_account(self):
        """Ledger for account with no entries shows zero balance."""
        result = FinancialReportEngine.get_account_ledger(self.account_cash.id)

        self.assertEqual(result['opening_balance'], Decimal('0.00'))
        self.assertEqual(result['closing_balance'], Decimal('0.00'))
        self.assertEqual(result['entry_count'], 0)
        self.assertEqual(len(result['entries']), 0)

    def test_ledger_with_entries(self):
        """Ledger shows entries with running balance."""
        entry1 = JournalEntryFactory.create(
            entry_date=date(2025, 1, 10),
            is_posted=True,
            entry_number='JE-001',
        )
        JournalEntryLineFactory.create(
            entry=entry1,
            account=self.account_cash,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00'),
        )

        entry2 = JournalEntryFactory.create(
            entry_date=date(2025, 1, 20),
            is_posted=True,
            entry_number='JE-002',
        )
        JournalEntryLineFactory.create(
            entry=entry2,
            account=self.account_cash,
            debit=Decimal('0.00'),
            credit=Decimal('300.00'),
        )

        result = FinancialReportEngine.get_account_ledger(self.account_cash.id)

        self.assertEqual(result['entry_count'], 2)
        self.assertEqual(result['closing_balance'], Decimal('700.00'))
        self.assertEqual(result['total_debit'], Decimal('1000.00'))
        self.assertEqual(result['total_credit'], Decimal('300.00'))

    def test_ledger_running_balance(self):
        """Ledger running balance is calculated correctly."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
            entry_number='JE-003',
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('500.00'),
            credit=Decimal('0.00'),
        )

        result = FinancialReportEngine.get_account_ledger(self.account_cash.id)

        self.assertEqual(result['entries'][0]['running_balance'], Decimal('500.00'))

    def test_ledger_with_date_range(self):
        """Ledger respects start and end date filters."""
        entry1 = JournalEntryFactory.create(
            entry_date=date(2025, 1, 10),
            is_posted=True,
            entry_number='JE-004',
        )
        JournalEntryLineFactory.create(
            entry=entry1,
            account=self.account_cash,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00'),
        )

        entry2 = JournalEntryFactory.create(
            entry_date=date(2025, 3, 10),
            is_posted=True,
            entry_number='JE-005',
        )
        JournalEntryLineFactory.create(
            entry=entry2,
            account=self.account_cash,
            debit=Decimal('500.00'),
            credit=Decimal('0.00'),
        )

        result = FinancialReportEngine.get_account_ledger(
            self.account_cash.id,
            start_date=date(2025, 2, 1),
            end_date=date(2025, 3, 31),
        )

        self.assertEqual(result['entry_count'], 1)
        self.assertEqual(result['opening_balance'], Decimal('1000.00'))

    def test_ledger_excludes_unposted(self):
        """Ledger excludes unposted entries."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=False,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('9999.00'),
            credit=Decimal('0.00'),
        )

        result = FinancialReportEngine.get_account_ledger(self.account_cash.id)

        self.assertEqual(result['entry_count'], 0)

    def test_ledger_entry_details(self):
        """Ledger entries contain all required fields."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
            entry_number='JE-006',
            entry_type='SALE',
            description='Test sale',
            reference='REF-001',
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('200.00'),
            credit=Decimal('0.00'),
            description='Cash received',
        )

        result = FinancialReportEngine.get_account_ledger(self.account_cash.id)

        ledger_entry = result['entries'][0]
        self.assertEqual(ledger_entry['entry_number'], 'JE-006')
        self.assertEqual(ledger_entry['entry_type'], 'SALE')
        self.assertEqual(ledger_entry['debit'], Decimal('200.00'))
        self.assertEqual(ledger_entry['credit'], Decimal('0.00'))


class AccountSummaryTests(BaseTestCase):
    """Tests for account summary report."""

    def test_summary_structure(self):
        """Account summary contains all account types."""
        result = FinancialReportEngine.get_account_summary(as_of_date=date(2025, 1, 31))

        self.assertIn('ASSET', result)
        self.assertIn('LIABILITY', result)
        self.assertIn('EQUITY', result)
        self.assertIn('REVENUE', result)
        self.assertIn('EXPENSE', result)

    def test_summary_account_count(self):
        """Account summary shows correct account counts."""
        result = FinancialReportEngine.get_account_summary(as_of_date=date(2025, 1, 31))

        self.assertGreaterEqual(result['ASSET']['account_count'], 1)

    def test_summary_with_entries(self):
        """Account summary reflects journal entry totals."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('2000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('2000.00'),
        )

        result = FinancialReportEngine.get_account_summary(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['ASSET']['total_debit'], Decimal('2000.00'))
        self.assertEqual(result['REVENUE']['total_credit'], Decimal('2000.00'))

    def test_summary_net_balance_asset(self):
        """Asset accounts have net_balance as debit - credit."""
        entry1 = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry1,
            account=self.account_cash,
            debit=Decimal('1500.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry1,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('1500.00'),
        )

        entry2 = JournalEntryFactory.create(
            entry_date=date(2025, 1, 20),
            is_posted=True,
        )
        JournalEntryLineFactory.create(
            entry=entry2,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('500.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry2,
            account=self.account_cash,
            debit=Decimal('0.00'),
            credit=Decimal('500.00'),
        )

        result = FinancialReportEngine.get_account_summary(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['ASSET']['net_balance'], Decimal('1000.00'))

    def test_summary_excludes_unposted(self):
        """Account summary excludes unposted entries."""
        entry = JournalEntryFactory.create(
            entry_date=date(2025, 1, 15),
            is_posted=False,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('8000.00'),
            credit=Decimal('0.00'),
        )

        result = FinancialReportEngine.get_account_summary(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['ASSET']['total_debit'], Decimal('0.00'))


class ARAgingTests(BaseTestCase):
    """Tests for Accounts Receivable aging report."""

    def test_ar_aging_empty(self):
        """AR aging with no customers returns empty."""
        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 0)
        self.assertEqual(result['totals']['total'], Decimal('0.00'))

    def test_ar_aging_current(self):
        """AR aging classifies current (not overdue) invoices correctly."""
        customer = CustomerFactory.create(name='Test Customer', code='C001')
        SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 2, 28),
        )

        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 1)
        self.assertEqual(result['aging_rows'][0]['current'], Decimal('1000.00'))
        self.assertEqual(result['totals']['current'], Decimal('1000.00'))

    def test_ar_aging_overdue_buckets(self):
        """AR aging classifies overdue invoices into correct buckets."""
        customer = CustomerFactory.create(name='Overdue Customer', code='C002')
        SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            total_amount=Decimal('500.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))

        row = result['aging_rows'][0]
        days = (date(2025, 1, 31) - date(2025, 1, 1)).days
        if days <= 30:
            self.assertEqual(row['age_1_30'], Decimal('500.00'))
        elif days <= 60:
            self.assertEqual(row['age_31_60'], Decimal('500.00'))

    def test_ar_aging_paid_invoices_excluded(self):
        """Fully paid invoices are excluded from AR aging."""
        customer = CustomerFactory.create(name='Paid Customer', code='C003')
        SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('1000.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 0)

    def test_ar_aging_inactive_customers_excluded(self):
        """Inactive customers are excluded from AR aging."""
        customer = CustomerFactory.create(
            name='Inactive Customer',
            code='C004',
            is_active=False,
        )
        SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            total_amount=Decimal('2000.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 0)

    def test_ar_aging_sorted_by_total(self):
        """AR aging rows are sorted by total descending."""
        c1 = CustomerFactory.create(name='Big Debtor', code='C010')
        c2 = CustomerFactory.create(name='Small Debtor', code='C011')
        SalesInvoiceFactory.create(
            customer=c1,
            status='DISPATCHED',
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 1, 1),
        )
        SalesInvoiceFactory.create(
            customer=c2,
            status='DISPATCHED',
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))

        self.assertGreaterEqual(result['aging_rows'][0]['total'], result['aging_rows'][1]['total'])

    def test_ar_aging_report_type(self):
        """AR aging report has correct report type."""
        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))
        self.assertEqual(result['report_type'], 'Accounts Receivable Aging')

    def test_ar_aging_partial_payment(self):
        """AR aging shows outstanding amount for partially paid invoices."""
        customer = CustomerFactory.create(name='Partial Customer', code='C005')
        SalesInvoiceFactory.create(
            customer=customer,
            status='PARTIAL_PAID',
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('400.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ar_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['totals']['total'], Decimal('600.00'))


class APAgingTests(BaseTestCase):
    """Tests for Accounts Payable aging report."""

    def test_ap_aging_empty(self):
        """AP aging with no suppliers returns empty."""
        result = FinancialReportEngine.get_ap_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 0)
        self.assertEqual(result['totals']['total'], Decimal('0.00'))

    def test_ap_aging_current(self):
        """AP aging classifies current (not overdue) invoices correctly."""
        supplier = SupplierFactory.create(name='Test Supplier', code='S001')
        PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='RECEIVED',
            total_amount=Decimal('2000.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 2, 28),
        )

        result = FinancialReportEngine.get_ap_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 1)
        self.assertEqual(result['aging_rows'][0]['current'], Decimal('2000.00'))

    def test_ap_aging_paid_invoices_excluded(self):
        """Fully paid invoices are excluded from AP aging."""
        supplier = SupplierFactory.create(name='Paid Supplier', code='S002')
        PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='RECEIVED',
            total_amount=Decimal('3000.00'),
            paid_amount=Decimal('3000.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ap_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 0)

    def test_ap_aging_inactive_suppliers_excluded(self):
        """Inactive suppliers are excluded from AP aging."""
        supplier = SupplierFactory.create(
            name='Inactive Supplier',
            code='S003',
            is_active=False,
        )
        PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='RECEIVED',
            total_amount=Decimal('1500.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ap_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 0)

    def test_ap_aging_partial_payment(self):
        """AP aging shows outstanding amount for partially paid invoices."""
        supplier = SupplierFactory.create(name='Partial Supplier', code='S004')
        PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='PARTIAL_PAID',
            total_amount=Decimal('2000.00'),
            paid_amount=Decimal('800.00'),
            due_date=date(2025, 1, 1),
        )

        result = FinancialReportEngine.get_ap_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(result['totals']['total'], Decimal('1200.00'))

    def test_ap_aging_report_type(self):
        """AP aging report has correct report type."""
        result = FinancialReportEngine.get_ap_aging(as_of_date=date(2025, 1, 31))
        self.assertEqual(result['report_type'], 'Accounts Payable Aging')

    def test_ap_aging_multiple_suppliers(self):
        """AP aging handles multiple suppliers correctly."""
        s1 = SupplierFactory.create(name='Supplier A', code='S010')
        s2 = SupplierFactory.create(name='Supplier B', code='S011')
        PurchaseInvoiceFactory.create(
            supplier=s1,
            status='RECEIVED',
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 1, 15),
        )
        PurchaseInvoiceFactory.create(
            supplier=s2,
            status='RECEIVED',
            total_amount=Decimal('3000.00'),
            paid_amount=Decimal('0.00'),
            due_date=date(2025, 1, 20),
        )

        result = FinancialReportEngine.get_ap_aging(as_of_date=date(2025, 1, 31))

        self.assertEqual(len(result['aging_rows']), 2)
        self.assertEqual(result['totals']['total'], Decimal('8000.00'))

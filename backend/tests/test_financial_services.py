"""
Simplified Financial Services Tests

Tests actual methods available in accounting services.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.account_hierarchy import AccountHierarchyService


class AccountHierarchyServiceSimpleTests(TestCase):
    """Test AccountHierarchyService methods that actually exist."""
    
    @classmethod
    def setUpTestData(cls):
        cls.root = Account.objects.create(
            code='1000', name='Assets', account_type='ASSET', is_active=True
        )
        cls.cash = Account.objects.create(
            code='1100', name='Cash', account_type='ASSET', parent=cls.root, is_active=True
        )
    
    def test_get_account_tree_returns_tree(self):
        """Test get_account_tree returns tree structure."""
        tree = AccountHierarchyService.get_account_tree()
        self.assertIsInstance(tree, list)
        
    def test_get_account_balance_accepts_id(self):
        """Test get_account_balance works with account ID."""
        balance = AccountHierarchyService.get_account_balance(self.cash.id)
        self.assertIsInstance(balance, Decimal)
        
    def test_get_ancestors_accepts_id(self):
        """Test get_ancestors works with account ID."""
        ancestors = AccountHierarchyService.get_ancestors(self.cash.id)
        self.assertIsInstance(ancestors, list)
        
    def test_get_children_accepts_id(self):
        """Test get_children works with account ID."""
        children = AccountHierarchyService.get_children(self.root.id)
        # Returns QuerySet, not list
        self.assertTrue(hasattr(children, 'filter'))
        
    def test_get_descendants_accepts_id(self):
        """Test get_descendants works with account ID."""
        descendants = AccountHierarchyService.get_descendants(self.root.id)
        self.assertIsInstance(descendants, list)
        
    def test_get_leaf_accounts_returns_queryset(self):
        """Test get_leaf_accounts returns accounts."""
        leaves = AccountHierarchyService.get_leaf_accounts()
        self.assertIsInstance(leaves, list)
        
    def test_get_accounts_by_type_accepts_type(self):
        """Test get_accounts_by_type filters."""
        assets = AccountHierarchyService.get_accounts_by_type('ASSET')
        # Returns QuerySet, not list
        self.assertTrue(hasattr(assets, 'filter'))
        
    def test_create_account_creates_new(self):
        """Test create_account creates new account."""
        new_account = AccountHierarchyService.create_account(
            code='9999', name='Test Account', account_type='ASSET'
        )
        self.assertIsNotNone(new_account)


class JournalEntryModelTests(TestCase):
    """Test JournalEntry model with correct field names."""
    
    @classmethod
    def setUpTestData(cls):
        cls.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        
    def test_create_journal_entry_with_entry_date(self):
        """Test creating journal entry with entry_date field."""
        entry = JournalEntry.objects.create(
            entry_number='JE-TEST-001',
            entry_date=date.today(),
            description='Test entry'
        )
        self.assertIsNotNone(entry)


class JournalEngineServiceTests(TestCase):
    """Test JournalEngine service methods."""
    
    @classmethod
    def setUpTestData(cls):
        cls.asset = Account.objects.create(
            code='1100', name='Cash', account_type='ASSET', is_active=True
        )
        
    def test_post_entry_method_exists(self):
        """Test post_entry method exists."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'post_entry'))
        
    def test_unpost_entry_method_exists(self):
        """Test unpost_entry method exists."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'unpost_entry'))
        
    def test_reverse_entry_method_exists(self):
        """Test reverse_entry method exists."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'reverse_entry'))
        
    def test_generate_entry_number_method_exists(self):
        """Test generate_entry_number method exists."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'generate_entry_number'))
        
    def test_update_account_balances_method_exists(self):
        """Test update_account_balances method exists."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'update_account_balances'))
        
    def test_recalculate_all_balances_method_exists(self):
        """Test recalculate_all_balances method exists."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'recalculate_all_balances'))
        
    def test_get_account_ledger_method_exists(self):
        """Test get_account_ledger method exists."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'get_account_ledger'))
        
    def test_get_account_ledger_returns_data(self):
        """Test get_account_ledger returns ledger data."""
        from accounting.services.journal_engine import JournalEngine
        result = JournalEngine.get_account_ledger(self.asset.id, date.today())
        self.assertIsInstance(result, dict)


class FinancialReportsServiceTests(TestCase):
    """Test Financial Reports service."""
    
    def test_financial_reports_module_exists(self):
        """Test financial_reports module exists."""
        from accounting.services import financial_reports
        self.assertIsNotNone(financial_reports)


class ReportExporterServiceTests(TestCase):
    """Test ReportExporter service."""
    
    def test_report_exporter_module_exists(self):
        """Test report_exporter module exists."""
        from accounting.services import report_exporter
        self.assertIsNotNone(report_exporter)


class TaxCalculatorServiceTests(TestCase):
    """Test TaxCalculator service."""
    
    def test_calculate_fixed_tax_method_exists(self):
        """Test calculate_fixed_tax method exists."""
        from accounting.services.tax_calculator import TaxCalculator
        self.assertTrue(hasattr(TaxCalculator, 'calculate_fixed_tax'))
        
    def test_calculate_percentage_tax_method_exists(self):
        """Test calculate_percentage_tax method exists."""
        from accounting.services.tax_calculator import TaxCalculator
        self.assertTrue(hasattr(TaxCalculator, 'calculate_percentage_tax'))
        
    def test_calculate_compound_tax_method_exists(self):
        """Test calculate_compound_tax method exists."""
        from accounting.services.tax_calculator import TaxCalculator
        self.assertTrue(hasattr(TaxCalculator, 'calculate_compound_tax'))


class DiscountCalculatorServiceTests(TestCase):
    """Test DiscountCalculator service."""
    
    def test_calculate_fixed_discount_method_exists(self):
        """Test calculate_fixed_discount method exists."""
        from accounting.services.discount_calculator import DiscountCalculator
        self.assertTrue(hasattr(DiscountCalculator, 'calculate_fixed_discount'))
        
    def test_calculate_percentage_discount_method_exists(self):
        """Test calculate_percentage_discount method exists."""
        from accounting.services.discount_calculator import DiscountCalculator
        self.assertTrue(hasattr(DiscountCalculator, 'calculate_percentage_discount'))


class InvoiceCalculatorServiceTests(TestCase):
    """Test InvoiceCalculator service."""
    
    def test_calculate_method_exists(self):
        """Test calculate method exists."""
        from accounting.services.invoice_calculator import InvoiceCalculator
        self.assertTrue(hasattr(InvoiceCalculator, 'calculate'))


class CurrencyConverterServiceTests(TestCase):
    """Test CurrencyConverter service."""
    
    def test_get_exchange_rate_method_exists(self):
        """Test get_exchange_rate method exists."""
        from accounting.services.currency_converter import CurrencyConverter
        self.assertTrue(hasattr(CurrencyConverter, 'get_exchange_rate'))
        
    def test_get_available_currencies_method_exists(self):
        """Test get_available_currencies method exists."""
        from accounting.services.currency_converter import CurrencyConverter
        self.assertTrue(hasattr(CurrencyConverter, 'get_available_currencies'))
        
    def test_get_available_currencies_returns_currencies(self):
        """Test get_available_currencies returns currencies."""
        from accounting.services.currency_converter import CurrencyConverter
        currencies = CurrencyConverter.get_available_currencies()
        self.assertIsInstance(currencies, (list, tuple))
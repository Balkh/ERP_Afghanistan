"""
Comprehensive Service and View Tests for remaining coverage.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine
from sales.models import Customer, SalesInvoice, SalesItem
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem
from inventory.models import Category, Unit, Product, Warehouse, Batch


class ServiceMethodTests(TransactionTestCase):
    """Test various service methods."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='2000', name='Payable', account_type='LIABILITY', is_active=True)

    def test_journal_entry_validation(self):
        """Test journal entry validation."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'},
            {'account_id': str(self.a2.id), 'debit': '0', 'credit': '100'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertEqual(len(errors), 0)

    def test_entry_number_generation(self):
        """Test entry number generation."""
        num = JournalEngine.generate_entry_number('TEST')
        self.assertIsInstance(num, str)
        self.assertIn('TES', num.upper())

    def test_account_ledger_query(self):
        """Test account ledger query."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.a2.id), 'debit': '0', 'credit': '500'}
        ]
        r = JournalEngine.create_entry('GENERAL', 'Test', lines)
        JournalEngine.post_entry(r['entry_id'])

        ledger = JournalEngine.get_account_ledger(self.a1.id)
        self.assertIn('entries', ledger)


class FullWorkflowTests(TransactionTestCase):
    """Test complete workflows."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)
        self.expense = Account.objects.create(code='5000', name='Expense', account_type='EXPENSE', is_active=True)
        self.ap = Account.objects.create(code='2000', name='AP', account_type='LIABILITY', is_active=True)

    def test_sales_workflow(self):
        """Test complete sales workflow."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.revenue.id), 'debit': '0', 'credit': '1000'}
        ]
        r = JournalEngine.create_entry('SALE', 'Invoice #1', lines)
        self.assertTrue(r['success'])

        post = JournalEngine.post_entry(r['entry_id'])
        self.assertTrue(post['success'])

    def test_purchase_workflow(self):
        """Test complete purchase workflow."""
        lines = [
            {'account_id': str(self.expense.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.ap.id), 'debit': '0', 'credit': '500'}
        ]
        r = JournalEngine.create_entry('PURCHASE', 'PO #1', lines)
        self.assertTrue(r['success'])

    def test_payment_workflow(self):
        """Test payment workflow."""
        inv_lines = [
            {'account_id': str(self.expense.id), 'debit': '300', 'credit': '0'},
            {'account_id': str(self.ap.id), 'debit': '0', 'credit': '300'}
        ]
        r1 = JournalEngine.create_entry('PURCHASE', 'PO', inv_lines)
        JournalEngine.post_entry(r1['entry_id'])

        pay_lines = [
            {'account_id': str(self.ap.id), 'debit': '300', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '300'}
        ]
        r2 = JournalEngine.create_entry('PAYMENT', 'Payment', pay_lines)
        self.assertTrue(r2['success'])


class ModelSimpleTests(TransactionTestCase):
    """Test simple model operations."""

    def test_category_creation(self):
        """Test category creation."""
        cat = Category.objects.create(name='Medicines', is_active=True)
        self.assertEqual(cat.name, 'Medicines')

    def test_unit_creation(self):
        """Test unit creation."""
        unit = Unit.objects.create(name='Piece', symbol='PCS', is_active=True)
        self.assertEqual(unit.symbol, 'PCS')

    def test_warehouse_creation(self):
        """Test warehouse creation."""
        wh = Warehouse.objects.create(name='Main WH', code='WH01', is_active=True)
        self.assertEqual(wh.code, 'WH01')

    def test_product_with_relations(self):
        """Test product with category and unit."""
        cat = Category.objects.create(name='Cat', is_active=True)
        unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        prod = Product.objects.create(name='P', sku='P', category=cat, unit=unit, is_active=True)
        self.assertEqual(prod.name, 'P')

    def test_batch_creation(self):
        """Test batch with full details."""
        cat = Category.objects.create(name='C', is_active=True)
        unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        prod = Product.objects.create(name='P', sku='P', category=cat, unit=unit, is_active=True)
        wh = Warehouse.objects.create(name='WH', code='WH', is_active=True)

        batch = Batch.objects.create(
            product=prod, batch_number='B1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(), location='WH', is_active=True
        )
        self.assertEqual(batch.remaining_quantity, Decimal('100'))


class ReportGenerationTests(TransactionTestCase):
    """Test report generation with various scenarios."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)
        self.expense = Account.objects.create(code='5000', name='Expense', account_type='EXPENSE', is_active=True)

    def test_multiple_date_ranges(self):
        """Test reports with different date ranges."""
        past = date.today() - timedelta(days=30)
        future = date.today() + timedelta(days=30)

        lines = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.revenue.id), 'debit': '0', 'credit': '1000'}
        ]
        r = JournalEngine.create_entry('SALE', 'Sale', lines)
        JournalEngine.post_entry(r['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(past, future)
        self.assertEqual(pl['total_revenue'], Decimal('1000'))

    def test_empty_date_range(self):
        """Test reports with no data in range."""
        future = date.today() + timedelta(days=365)
        pl = FinancialReportEngine.get_profit_and_loss(future, future)
        self.assertEqual(pl['total_revenue'], Decimal('0'))


class PermissionTests(TestCase):
    """Test permission checks."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='perms', password='test')
        self.client.force_login(self.user)

    def test_unauthenticated_access(self):
        """Test unauthenticated access."""
        self.client.logout()
        response = self.client.get('/api/accounting/accounts/')
        self.assertIn(response.status_code, [302, 401, 403])

    def test_authenticated_access(self):
        """Test authenticated access."""
        response = self.client.get('/api/accounting/accounts/')
        self.assertIn(response.status_code, [200, 403, 404])


class EdgeCaseTests(TransactionTestCase):
    """Test edge cases."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='A', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='2000', name='B', account_type='LIABILITY', is_active=True)

    def test_zero_amount_entry(self):
        """Test entry with zero amounts."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '0', 'credit': '0'},
            {'account_id': str(self.a2.id), 'debit': '0', 'credit': '0'}
        ]
        result = JournalEngine.create_entry('GENERAL', 'Zero', lines)
        self.assertFalse(result['success'])

    def test_unbalanced_entry_rejected(self):
        """Test unbalanced entry is rejected."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'},
            {'account_id': str(self.a2.id), 'debit': '0', 'credit': '50'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertGreater(len(errors), 0)
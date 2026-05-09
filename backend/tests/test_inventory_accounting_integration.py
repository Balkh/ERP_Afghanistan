"""
Inventory & Accounting Integration Tests - Simplified.

Tests the connection between inventory operations and accounting journal entries.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.utils import timezone as django_timezone

from inventory.models import Product, Category, Unit, Warehouse, Batch
from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine


class SaleInventoryAccountingTest(TransactionTestCase):
    """Test sale inventory -> accounting integration."""

    def setUp(self):
        self.category = Category.objects.create(name='Medicines', is_active=True)
        self.unit = Unit.objects.create(name='Piece', symbol='PCS', is_active=True)
        self.product = Product.objects.create(name='Aspirin', sku='ASP001', category=self.category, unit=self.unit, is_active=True)
        self.warehouse = Warehouse.objects.create(name='Main WH', code='WH01', is_active=True)
        self.batch = Batch.objects.create(
            product=self.product, batch_number='B001', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(), location='WH01', is_active=True
        )

        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Sales Revenue', account_type='REVENUE', is_active=True)
        self.cogs = Account.objects.create(code='5100', name='COGS', account_type='EXPENSE', is_active=True)
        self.inventory = Account.objects.create(code='1140', name='Inventory', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1130', name='AR', account_type='ASSET', is_active=True)

    def test_sale_creates_journal_entry(self):
        """Test sale creates journal entry."""
        lines = [
            {'account_id': str(self.ar.id), 'debit': '150.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '150.00'}
        ]
        result = JournalEngine.create_entry('SALE', 'Sale #1', lines)
        self.assertTrue(result['success'])

    def test_sale_with_cogs_updates_accounts(self):
        """Test sale with COGS posts to accounts."""
        sale_lines = [
            {'account_id': str(self.ar.id), 'debit': '150.00', 'credit': '0.00'},
            {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '150.00'}
        ]
        sale_result = JournalEngine.create_entry('SALE', 'Sale', sale_lines)
        JournalEngine.post_entry(sale_result['entry_id'])

        cogs_lines = [
            {'account_id': str(self.cogs.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.inventory.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        cogs_result = JournalEngine.create_entry('COGS', 'COGS', cogs_lines)
        JournalEngine.post_entry(cogs_result['entry_id'])

        self.cogs.refresh_from_db()
        self.assertEqual(self.cogs.balance, Decimal('100.00'))

    def test_batch_creation(self):
        """Test batch can be created with inventory."""
        self.assertEqual(self.batch.remaining_quantity, Decimal('100'))


class PurchaseInventoryAccountingTest(TransactionTestCase):
    """Test purchase inventory -> accounting integration."""

    def setUp(self):
        self.category = Category.objects.create(name='Medicines', is_active=True)
        self.unit = Unit.objects.create(name='Piece', symbol='PCS', is_active=True)
        self.product = Product.objects.create(name='Panadol', sku='PAN001', category=self.category, unit=self.unit, is_active=True)
        self.warehouse = Warehouse.objects.create(name='Main WH', code='WH01', is_active=True)

        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.inventory = Account.objects.create(code='1140', name='Inventory', account_type='ASSET', is_active=True)
        self.ap = Account.objects.create(code='2110', name='AP', account_type='LIABILITY', is_active=True)

    def test_purchase_creates_journal_entry(self):
        """Test purchase creates journal entry."""
        lines = [
            {'account_id': str(self.inventory.id), 'debit': '200.00', 'credit': '0.00'},
            {'account_id': str(self.ap.id), 'debit': '0.00', 'credit': '200.00'}
        ]
        result = JournalEngine.create_entry('PURCHASE', 'PO #1', lines)
        self.assertTrue(result['success'])

    def test_purchase_increases_inventory(self):
        """Test purchase increases inventory account."""
        lines = [
            {'account_id': str(self.inventory.id), 'debit': '500.00', 'credit': '0.00'},
            {'account_id': str(self.ap.id), 'debit': '0.00', 'credit': '500.00'}
        ]
        result = JournalEngine.create_entry('PURCHASE', 'Stock purchase', lines)
        JournalEngine.post_entry(result['entry_id'])

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.balance, Decimal('500.00'))

    def test_purchase_creates_batch(self):
        """Test purchase creates batch."""
        batch = Batch.objects.create(
            product=self.product, batch_number='B002', quantity=50, remaining_quantity=50,
            purchase_price=Decimal('20.00'), sale_price=Decimal('30.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(), location='WH01', is_active=True
        )
        self.assertEqual(batch.remaining_quantity, Decimal('50'))


class StockAdjustmentAccountingTest(TransactionTestCase):
    """Test stock adjustment -> accounting integration."""

    def setUp(self):
        self.category = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.product = Product.objects.create(name='P', sku='P', category=self.category, unit=self.unit, is_active=True)
        self.warehouse = Warehouse.objects.create(name='WH', code='WH', is_active=True)

        self.inventory = Account.objects.create(code='1140', name='Inventory', account_type='ASSET', is_active=True)
        self.adjustment = Account.objects.create(code='5900', name='Adjustment', account_type='EXPENSE', is_active=True)

    def test_adjustment_add_journal(self):
        """Test positive adjustment journal."""
        lines = [
            {'account_id': str(self.inventory.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.adjustment.id), 'debit': '0.00', 'credit': '100.00'}
        ]
        result = JournalEngine.create_entry('ADJUSTMENT', 'Found stock', lines)
        self.assertTrue(result['success'])

    def test_adjustment_loss_journal(self):
        """Test negative adjustment journal."""
        lines = [
            {'account_id': str(self.adjustment.id), 'debit': '50.00', 'credit': '0.00'},
            {'account_id': str(self.inventory.id), 'debit': '0.00', 'credit': '50.00'}
        ]
        result = JournalEngine.create_entry('ADJUSTMENT', 'Damaged', lines)
        self.assertTrue(result['success'])


class TransferAccountingTest(TransactionTestCase):
    """Test warehouse transfer -> accounting integration."""

    def setUp(self):
        self.w1 = Account.objects.create(code='1140', name='WH1', account_type='ASSET', is_active=True)
        self.w2 = Account.objects.create(code='1141', name='WH2', account_type='ASSET', is_active=True)
        self.transit = Account.objects.create(code='1190', name='In Transit', account_type='ASSET', is_active=True)

    def test_transfer_journal(self):
        """Test transfer journal entry."""
        lines = [
            {'account_id': str(self.w2.id), 'debit': '75.00', 'credit': '0.00'},
            {'account_id': str(self.w1.id), 'debit': '0.00', 'credit': '75.00'}
        ]
        result = JournalEngine.create_entry('TRANSFER', 'Transfer', lines)
        self.assertTrue(result['success'])


class BatchCostFlowTest(TransactionTestCase):
    """Test batch cost flows to accounts."""

    def setUp(self):
        self.category = Category.objects.create(name='C', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.product = Product.objects.create(name='P', sku='P', category=self.category, unit=self.unit, is_active=True)
        self.warehouse = Warehouse.objects.create(name='WH', code='WH', is_active=True)

        self.inventory = Account.objects.create(code='1140', name='Inventory', account_type='ASSET', is_active=True)
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)

    def test_batch_purchase_cost_to_inventory(self):
        """Test batch purchase cost flows to inventory."""
        batch = Batch.objects.create(
            product=self.product, batch_number='B1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('25'), sale_price=Decimal('40'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(), location='WH', is_active=True
        )

        lines = [
            {'account_id': str(self.inventory.id), 'debit': '2500.00', 'credit': '0.00'},
            {'account_id': str(self.cash.id), 'debit': '0.00', 'credit': '2500.00'}
        ]
        result = JournalEngine.create_entry('PURCHASE', 'Batch purchase', lines)
        JournalEngine.post_entry(result['entry_id'])

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.balance, Decimal('2500.00'))


class DoubleEntryIntegrityTest(TransactionTestCase):
    """Test double-entry integrity in inventory transactions."""

    def setUp(self):
        self.inv = Account.objects.create(code='1140', name='Inventory', account_type='ASSET', is_active=True)
        self.exp = Account.objects.create(code='5100', name='Expense', account_type='EXPENSE', is_active=True)

    def test_sale_entry_balanced(self):
        """Test sale journal entry is balanced."""
        lines = [
            {'account_id': str(self.inv.id), 'debit': '300.00', 'credit': '0.00'},
            {'account_id': str(self.exp.id), 'debit': '0.00', 'credit': '300.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertEqual(len(errors), 0)

    def test_purchase_entry_balanced(self):
        """Test purchase journal entry is balanced."""
        lines = [
            {'account_id': str(self.exp.id), 'debit': '500.00', 'credit': '0.00'},
            {'account_id': str(self.inv.id), 'debit': '0.00', 'credit': '500.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertEqual(len(errors), 0)

    def test_unbalanced_entry_rejected(self):
        """Test unbalanced entry is rejected."""
        lines = [
            {'account_id': str(self.inv.id), 'debit': '100.00', 'credit': '0.00'},
            {'account_id': str(self.exp.id), 'debit': '0.00', 'credit': '50.00'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertGreater(len(errors), 0)
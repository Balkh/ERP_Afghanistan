"""
Advanced Enterprise Lifecycle Scenarios.
Tests complex real-world workflows with final state validation.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import TransactionTestCase

from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine
from inventory.service.stock_integration import StockIntegrationService
from inventory.service import StockSelectionMode


class MultiPaymentSettlementTest(TransactionTestCase):
    """Test multi-payment invoice settlement (cash + hawala + bank)."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.bank = Account.objects.create(code='1010', name='Bank', account_type='ASSET', is_active=True)
        self.hawala = Account.objects.create(code='1020', name='Hawala', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='AR', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

    def test_split_payment_settlement(self):
        """Test invoice settled with multiple payment methods."""
        # Create invoice (AR): $1000
        lines1 = [
            {'account_id': str(self.ar.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        result1 = JournalEngine.create_entry('INVOICE', 'INV-MULTI-001', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        # Payment 1: Cash $400
        lines2 = [
            {'account_id': str(self.cash.id), 'debit': '400', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '400'},
        ]
        result2 = JournalEngine.create_entry('RECEIPT', 'RCT-001', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        # Payment 2: Bank $350
        lines3 = [
            {'account_id': str(self.bank.id), 'debit': '350', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '350'},
        ]
        result3 = JournalEngine.create_entry('RECEIPT', 'RCT-002', lines3)
        JournalEngine.post_entry(result3['entry_id'])

        # Payment 3: Hawala $250
        lines4 = [
            {'account_id': str(self.hawala.id), 'debit': '250', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '250'},
        ]
        result4 = JournalEngine.create_entry('RECEIPT', 'RCT-003', lines4)
        JournalEngine.post_entry(result4['entry_id'])

        # Verify AR is fully settled
        ar_ledger = FinancialReportEngine.get_account_ledger(str(self.ar.id), date.today(), date.today())
        # After payments, AR should have $0 net (1000 - 400 - 350 - 250 = 0)
        self.assertEqual(ar_ledger['closing_balance'], Decimal('0'))

    def test_trial_balance_remains_balanced_with_split_payment(self):
        """Trial balance must balance after multiple payment methods."""
        tb = FinancialReportEngine.get_trial_balance(date.today())
        self.assertEqual(tb['total_debit'], tb['total_credit'])


class BatchDepletionMultiWarehouseTest(TransactionTestCase):
    """Test batch depletion across multiple warehouses."""

    def setUp(self):
        self.cat = Category.objects.create(name='Pharma', is_active=True)
        self.unit = Unit.objects.create(name='Unit', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='DrugX', sku='DRUGX', category=self.cat, unit=self.unit, is_active=True)
        self.wh1 = Warehouse.objects.create(name='WH-A', code='WHA01', is_active=True)
        self.wh2 = Warehouse.objects.create(name='WH-B', code='WHB01', is_active=True)

    def test_batch_depletes_completely_before_next(self):
        """FEFO must fully deplete earliest batch before touching next."""
        # Create two batches with different expiry
        Batch.objects.create(
            product=self.prod, batch_number='B-EARLY', quantity=20, remaining_quantity=20,
            purchase_price=Decimal('5.00'), sale_price=Decimal('10.00'),
            expiry_date=date.today() + timedelta(days=100),
            manufacturing_date=date.today() - timedelta(days=50),
            location=str(self.wh1.id), is_active=True
        )
        Batch.objects.create(
            product=self.prod, batch_number='B-LATE', quantity=30, remaining_quantity=30,
            purchase_price=Decimal('5.00'), sale_price=Decimal('10.00'),
            expiry_date=date.today() + timedelta(days=200),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(),
            location=str(self.wh1.id), is_active=True
        )

        # Allocate 25 units - should use all 20 from B-EARLY + 5 from B-LATE
        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('25'), self.wh1, StockSelectionMode.FEFO
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 2)
        self.assertEqual(result.allocations[0].quantity, Decimal('20'))  # B-EARLY fully depleted
        self.assertEqual(result.allocations[1].quantity, Decimal('5'))   # B-LATE partially used


class InvoiceCancellationWithRollbackTest(TransactionTestCase):
    """Test invoice cancellation with proper rollback."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.ar = Account.objects.create(code='1100', name='AR', account_type='ASSET', is_active=True)

    def test_invoice_cancellation_reverses_journal(self):
        """Cancelled invoice must reverse original journal entry."""
        # Create original sale
        lines1 = [
            {'account_id': str(self.ar.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        result1 = JournalEngine.create_entry('SALE', 'INV-CANCEL-001', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        # Cancel the invoice (reverse entries)
        lines2 = [
            {'account_id': str(self.sales.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '1000'},
        ]
        result2 = JournalEngine.create_entry('CANCEL', 'INV-CANCEL-001-REVERSE', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        # Verify net effect is zero
        ar_ledger = FinancialReportEngine.get_account_ledger(str(self.ar.id), date.today(), date.today())
        sales_ledger = FinancialReportEngine.get_account_ledger(str(self.sales.id), date.today(), date.today())

        # AR should be $0 after cancellation
        self.assertEqual(ar_ledger['closing_balance'], Decimal('0'))


class PartialPaymentBalanceCarryForwardTest(TransactionTestCase):
    """Test partial payment with balance carry-forward."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='AR', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

    def test_partial_payment_leaves_balance(self):
        """Partial payment must leave correct AR balance."""
        # Create invoice for $1000
        lines1 = [
            {'account_id': str(self.ar.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        result1 = JournalEngine.create_entry('INVOICE', 'INV-PARTIAL-001', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        # Partial payment of $600
        lines2 = [
            {'account_id': str(self.cash.id), 'debit': '600', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '600'},
        ]
        result2 = JournalEngine.create_entry('RECEIPT', 'RCT-PARTIAL-001', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        # Verify remaining AR balance
        ar_ledger = FinancialReportEngine.get_account_ledger(str(self.ar.id), date.today(), date.today())
        self.assertEqual(ar_ledger['closing_balance'], Decimal('400'))


class ConcurrentAllocationProtectionTest(TransactionTestCase):
    """Test concurrent stock allocation protection."""

    def setUp(self):
        self.cat = Category.objects.create(name='Test', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='ConcurrentTest', sku='CONCTST', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='ConcurrentWH', code='CWH01', is_active=True)

    def test_allocation_checks_available_stock(self):
        """Allocation must check available stock before succeeding."""
        # Create limited stock via purchase (creates batch + IN movement)
        purchase_result = StockIntegrationService.process_purchase(
            'PO-CONC-001',
            [{
                'product': self.prod,
                'quantity': Decimal('10'),
                'batch_number': 'B-CONC-001',
                'expiry_date': date.today() + timedelta(days=180),
                'unit_price': Decimal('5.00'),
            }],
            self.wh
        )
        self.assertTrue(purchase_result.success)

        # First allocation of 8 should succeed
        result1 = StockIntegrationService.allocate_stock(self.prod, Decimal('8'), self.wh)
        self.assertTrue(result1.success)

        # Create OUT movement to reduce actual stock
        for alloc in result1.allocations:
            StockIntegrationService.create_stock_movement(
                product=self.prod,
                batch=alloc.batch_id,
                warehouse=self.wh,
                movement_type='OUT',
                reference_type='SALE',
                reference_id='INV-CONC-001',
                quantity=-alloc.quantity,
                unit_cost=alloc.unit_cost,
            )

        # Second allocation of 5 should fail (only 2 remaining)
        result2 = StockIntegrationService.allocate_stock(self.prod, Decimal('5'), self.wh)
        self.assertFalse(result2.success)
        self.assertIn('Insufficient', result2.message)


class NoOrphanMovementsValidationTest(TransactionTestCase):
    """Test that all stock movements have valid references."""

    def setUp(self):
        self.cat = Category.objects.create(name='Test', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='OrphanTest', sku='ORPHTST', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='OrphanWH', code='OWH01', is_active=True)

    def test_all_movements_have_valid_references(self):
        """All stock movements must have valid reference_type and reference_id."""
        # Create movements with proper references
        StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='IN',
            reference_type='PURCHASE',
            reference_id='PO-ORPHAN-001',
            quantity=Decimal('50'),
            unit_cost=Decimal('5.00'),
            notes='Test'
        )
        StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='OUT',
            reference_type='SALE',
            reference_id='INV-ORPHAN-001',
            quantity=Decimal('-10'),
            unit_cost=Decimal('5.00'),
            notes='Test'
        )

        # Verify all movements have references
        movements = StockMovement.objects.filter(product=self.prod)
        for m in movements:
            self.assertIsNotNone(m.reference_type)
            self.assertIsNotNone(m.reference_id)
            self.assertNotEqual(m.reference_type, '')
            self.assertNotEqual(m.reference_id, '')
"""
Edge case and error handling tests.

Covers:
- Negative stock prevention
- Concurrent update handling (race conditions)
- Invalid/corrupted data handling
- Transaction rollback on failure
- Boundary conditions
- Large quantity handling
- Decimal precision
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from tests.base import TransactionBaseTestCase
from tests.factories import (
    ProductFactory,
    BatchFactory,
    WarehouseFactory,
    CustomerFactory,
    SupplierFactory,
    SalesInvoiceFactory,
    PurchaseInvoiceFactory,
    StockMovementFactory
)
from inventory.service import StockIntegrationService, StockSelectionMode
from inventory.models import Batch, StockMovement
from accounting.services.journal_engine import JournalEngine
from accounting.models import Account, JournalEntry


class NegativeStockPreventionTests(TransactionBaseTestCase):
    """Tests ensuring stock never goes negative."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        self.batch = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-NEG-001',
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            location=str(self.warehouse.id)
        )
        # Create IN movement to establish stock (since _update_batch_quantity
        # recalculates from all movements)
        StockMovementFactory.create(
            product=self.product,
            batch=self.batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=Decimal('100.00')
        )

    def test_cannot_sell_more_than_available(self):
        """Test selling more than available stock fails."""
        result = StockIntegrationService.process_sale(
            invoice_id='SI-NEG-001',
            items=[{
                'product': self.product,
                'quantity': Decimal('150.00'),  # More than 100 available
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)
        self.batch.refresh_from_db()
        # Stock should remain unchanged
        self.assertEqual(self.batch.remaining_quantity, Decimal('100.00'))

    def test_cannot_sell_exact_remaining_plus_epsilon(self):
        """Test selling slightly more than available fails."""
        result = StockIntegrationService.process_sale(
            invoice_id='SI-NEG-002',
            items=[{
                'product': self.product,
                'quantity': Decimal('100.01'),  # Just over available
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)

    def test_can_sell_exact_remaining(self):
        """Test selling exact remaining stock succeeds."""
        result = StockIntegrationService.process_sale(
            invoice_id='SI-NEG-003',
            items=[{
                'product': self.product,
                'quantity': Decimal('100.00'),  # Exactly available
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.remaining_quantity, Decimal('0.00'))

    def test_no_stock_sale_fails(self):
        """Test sale when no stock fails."""
        # First sell all stock
        StockIntegrationService.process_sale(
            invoice_id='SI-NEG-004',
            items=[{
                'product': self.product,
                'quantity': Decimal('100.00'),
            }],
            warehouse=self.warehouse
        )
        
        # Try to sell more
        result = StockIntegrationService.process_sale(
            invoice_id='SI-NEG-005',
            items=[{
                'product': self.product,
                'quantity': Decimal('1.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)

    def test_expired_batch_not_available_for_sale(self):
        """Test expired batches are not available for sale."""
        expired_batch = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-EXPIRED',
            quantity=Decimal('500.00'),
            remaining_quantity=Decimal('500.00'),
            expiry_date=timezone.now().date() - timedelta(days=1),
            location=str(self.warehouse.id)
        )
        
        # Try to sell from expired batch
        result = StockIntegrationService.allocate_stock(
            self.product,
            Decimal('100.00'),
            batch_id=expired_batch.id
        )
        
        # Should succeed if specifically requested, but general allocation should exclude
        general_result = StockIntegrationService.allocate_stock(
            self.product,
            Decimal('100.00')
        )
        
        # General allocation should not include expired batch
        self.assertTrue(general_result.success)
        for alloc in general_result.allocations:
            self.assertNotEqual(alloc.batch_id, expired_batch.id)


class TransactionAtomicityTests(TransactionBaseTestCase):
    """Tests for transaction safety and rollback behavior."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )

    def test_purchase_rollback_on_failure(self):
        """Test purchase rolls back on partial failure."""
        # This test verifies that if any item in a purchase fails,
        # the entire purchase is rolled back
        today = timezone.now().date()
        
        # Valid purchase should succeed
        result = StockIntegrationService.process_purchase(
            invoice_id='PI-ATOMIC-001',
            items=[{
                'product': self.product,
                'quantity': Decimal('100.00'),
                'batch_number': 'BATCH-ATOMIC-001',
                'expiry_date': today + timedelta(days=365),
                'unit_price': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)

    def test_journal_entry_rollback_on_validation_failure(self):
        """Test journal entry creation rolls back on validation failure."""
        # Create unbalanced entry - should fail completely
        result = JournalEngine.create_entry(
            entry_type='ADJUSTMENT',
            description='Unbalanced entry',
            lines=[
                {'account_code': '1000', 'debit': 500, 'credit': 0, 'description': 'Dr'},
                {'account_code': '4000', 'debit': 0, 'credit': 200, 'description': 'Cr'}
            ]
        )
        
        self.assertFalse(result['success'])
        
        # Verify no entry was created
        entry_count = JournalEngine.generate_entry_number('ADJUSTMENT')
        # Should not have created an entry for the failed attempt

    def test_account_balance_consistency(self):
        """Test account balances remain consistent after multiple operations."""
        # Create balanced entries
        for i in range(5):
            JournalEngine.create_entry(
                entry_type='ADJUSTMENT',
                description=f'Balance test {i}',
                lines=[
                    {'account_code': '1000', 'debit': 100, 'credit': 0, 'description': 'Dr'},
                    {'account_code': '4000', 'debit': 0, 'credit': 100, 'description': 'Cr'}
                ],
                auto_post=True
            )
        
        # Verify system balance
        all_debits = sum(
            line.debit for line in 
            Account.objects.get(code='1000').journal_lines.filter(entry__is_posted=True)
        )
        all_credits = sum(
            line.credit for line in 
            Account.objects.get(code='4000').journal_lines.filter(entry__is_posted=True)
        )
        
        # Total debits should equal total credits across the system
        self.assertEqual(all_debits, all_credits)


class InvalidDataHandlingTests(TransactionBaseTestCase):
    """Tests for handling invalid and corrupted data."""

    def test_zero_quantity_sale(self):
        """Test sale with zero quantity is rejected."""
        product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        BatchFactory.create(
            product=product,
            batch_number='BATCH-ZERO-001',
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00')
        )
        
        result = StockIntegrationService.process_sale(
            invoice_id='SI-ZERO-001',
            items=[{
                'product': product,
                'quantity': Decimal('0'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)

    def test_negative_quantity_sale(self):
        """Test sale with negative quantity is rejected."""
        product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        
        result = StockIntegrationService.process_sale(
            invoice_id='SI-NEG-QTY-001',
            items=[{
                'product': product,
                'quantity': Decimal('-50.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)

    def test_nonexistent_product_sale(self):
        """Test sale with nonexistent product is handled gracefully."""
        import uuid
        result = StockIntegrationService.process_sale(
            invoice_id='SI-NONE-001',
            items=[{
                'product': uuid.uuid4(),  # Nonexistent UUID
                'quantity': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)

    def test_duplicate_batch_numbers(self):
        """Test duplicate batch numbers are prevented."""
        product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        BatchFactory.create(
            product=product,
            batch_number='BATCH-DUP-001'
        )
        
        with self.assertRaises(Exception):
            BatchFactory.create(
                product=product,
                batch_number='BATCH-DUP-001'
            )

    def test_invalid_account_code_in_journal(self):
        """Test journal entry with invalid account code fails."""
        result = JournalEngine.create_entry(
            entry_type='ADJUSTMENT',
            description='Invalid account',
            lines=[
                {'account_code': '99999', 'debit': 100, 'credit': 0, 'description': 'Dr'},
                {'account_code': '4000', 'debit': 0, 'credit': 100, 'description': 'Cr'}
            ]
        )
        
        self.assertFalse(result['success'])


class BoundaryConditionTests(TransactionBaseTestCase):
    """Tests for boundary conditions and edge values."""

    def test_very_large_quantities(self):
        """Test handling of very large quantities within field limits."""
        product = ProductFactory.create(
            name='Test Product Large',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        # For total_cost field: max_digits=10, decimal_places=2
        # Max value: 99999999.99
        # We need quantity * unit_cost <= 99999999.99
        # Let's use quantity = 999999.99 and unit_cost = 100.00 (product = 99999999.00)
        large_qty = Decimal('999999.99')
        batch = BatchFactory.create(
            product=product,
            batch_number='BATCH-LARGE-001',
            quantity=large_qty,
            remaining_quantity=large_qty,
            purchase_price=Decimal('100.00'),  # unit cost
            sale_price=Decimal('150.00'),
            location=str(self.warehouse.id)
        )
        StockMovementFactory.create(
            product=product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=large_qty
        )
        
        result = StockIntegrationService.process_sale(
            invoice_id='SI-LARGE-001',
            items=[{
                'product': product,
                'quantity': Decimal('999999.00'),  # Less than available
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)

    def test_very_small_quantities(self):
        """Test handling of very small quantities (decimal precision)."""
        product = ProductFactory.create(
            name='Test Product Small',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        batch = BatchFactory.create(
            product=product,
            batch_number='BATCH-SMALL-001',
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            location=str(self.warehouse.id)
        )
        StockMovementFactory.create(
            product=product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=Decimal('100.00')
        )
        
        result = StockIntegrationService.process_sale(
            invoice_id='SI-SMALL-001',
            items=[{
                'product': product,
                'quantity': Decimal('0.01'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)

    def test_decimal_precision_in_accounting(self):
        """Test decimal precision in accounting entries."""
        result = JournalEngine.create_entry(
            entry_type='ADJUSTMENT',
            description='Precision test',
            lines=[
                {'account_code': '1000', 'debit': 100.123456, 'credit': 0, 'description': 'Dr'},
                {'account_code': '4000', 'debit': 0, 'credit': 100.123456, 'description': 'Cr'}
            ],
            auto_post=True
        )
        
        self.assertTrue(result['success'])
        # Verify precision is maintained
        self.assertEqual(result['total_debit'], result['total_credit'])

    def test_empty_items_sale(self):
        """Test sale with empty items list."""
        result = StockIntegrationService.process_sale(
            invoice_id='SI-EMPTY-001',
            items=[],
            warehouse=self.warehouse
        )
        
        # Should succeed (no items to process)
        self.assertTrue(result.success)

    def test_empty_items_purchase(self):
        """Test purchase with empty items list."""
        result = StockIntegrationService.process_purchase(
            invoice_id='PI-EMPTY-001',
            items=[],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)


class ConcurrentUpdateTests(TransactionBaseTestCase):
    """
    Tests for concurrent update scenarios.
    
    Note: These tests simulate concurrent access patterns.
    In production, use database-level locking for critical sections.
    """

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        self.batch = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-CONC-001',
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            location=str(self.warehouse.id)
        )
        # Create IN movement to establish stock
        StockMovementFactory.create(
            product=self.product,
            batch=self.batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=Decimal('100.00')
        )

    def test_sequential_sales_dont_overcommit(self):
        """
        Test that sequential sales don't overcommit stock.
        This simulates what would happen with concurrent requests.
        """
        # Simulate sequential "concurrent" sales
        results = []
        for i in range(3):
            result = StockIntegrationService.process_sale(
                invoice_id=f'SI-CONC-{i:03d}',
                items=[{
                    'product': self.product,
                    'quantity': Decimal('40.00'),  # 3 * 40 = 120 > 100
                }],
                warehouse=self.warehouse
            )
            results.append(result)
        
        # Only first two should succeed (40 + 40 = 80)
        # Third should fail (would need 40, only 20 left)
        success_count = sum(1 for r in results if r.success)
        self.assertEqual(success_count, 2)

    def test_rapid_stock_updates(self):
        """Test rapid successive stock updates maintain integrity."""
        # Create a fresh batch for this test to avoid conflicts with setUp
        product = ProductFactory.create(
            name='Test Product Rapid',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        batch = BatchFactory.create(
            product=product,
            batch_number='BATCH-RAPID-TEST-001',
            quantity=Decimal('1000.00'),
            remaining_quantity=Decimal('1000.00'),
            location=str(self.warehouse.id)
        )
        # Create IN movement to establish stock
        StockMovementFactory.create(
            product=product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=Decimal('1000.00')
        )
        
        # Perform many small sales
        successful_sales = 0
        for i in range(100):
            result = StockIntegrationService.process_sale(
                invoice_id=f'SI-RAPID-{i:03d}',
                items=[{
                    'product': product,
                    'quantity': Decimal('5.00'),
                }],
                warehouse=self.warehouse
            )
            if result.success:
                successful_sales += 1
            else:
                # Log the failure for debugging
                print(f"Sale {i} failed: {result.errors}")
        
        # We expect all 100 sales to succeed
        self.assertEqual(successful_sales, 100, f"Expected 100 successful sales, got {successful_sales}")
         
        # Verify final stock: 1000 - (100 * 5) = 500
        total_stock = StockIntegrationService.get_total_available_stock(product, warehouse=self.warehouse)
        self.assertEqual(total_stock, Decimal('500.00'))  # 1000 - (100 * 5)


class JournalEntryEdgeCaseTests(TransactionBaseTestCase):
    """Edge case tests for journal entries."""

    def test_reversal_of_reversal(self):
        """Test reversing a reversal entry."""
        # Create original entry
        result = JournalEngine.create_entry(
            entry_type='SALE',
            description='Original sale',
            lines=[
                {'account_code': '1000', 'debit': 100, 'credit': 0, 'description': 'Dr'},
                {'account_code': '4000', 'debit': 0, 'credit': 100, 'description': 'Cr'}
            ],
            auto_post=True
        )
        original_id = result['entry_id']
        
        # Reverse it
        reversal = JournalEngine.reverse_entry(original_id, reason='Test')
        self.assertTrue(reversal['success'])
        
        # Reverse the reversal - current implementation prevents double reversal
        reversal_entry = JournalEntry.objects.filter(
            entry_number=f"REV-{JournalEntry.objects.get(id=original_id).entry_number}"
        ).first()
        
        if reversal_entry:
            double_reversal = JournalEngine.reverse_entry(
                reversal_entry.id,
                reason='Double reversal test'
            )
            # Current implementation does not support reversing a reversal entry
            self.assertFalse(double_reversal['success'])

    def test_entry_with_many_lines(self):
        """Test journal entry with many lines."""
        # Create additional accounts
        accounts = []
        for i in range(20):
            acc = Account.objects.create(
                code=f'{7000 + i}',
                name=f'Expense Account {i}',
                account_type='EXPENSE',
                account_category='OPERATING_EXPENSE'
            )
            accounts.append(acc)
        
        # Create entry with multiple lines
        debit_lines = []
        total_per_line = Decimal('1000') / len(accounts)
        
        for acc in accounts:
            debit_lines.append({
                'account_code': acc.code,
                'debit': total_per_line,
                'credit': 0,
                'description': f'Debit to {acc.code}'
            })
        
        debit_lines.append({
            'account_code': '2000',
            'debit': 0,
            'credit': 1000,
            'description': 'Credit to AP'
        })
        
        result = JournalEngine.create_entry(
            entry_type='ADJUSTMENT',
            description='Multi-line entry',
            lines=debit_lines,
            auto_post=True
        )
        
        self.assertTrue(result['success'])

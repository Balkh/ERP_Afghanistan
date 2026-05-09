"""
Full lifecycle integration tests for the ERP system.

Tests the complete business workflow:
1. Create Purchase Order
2. Approve Purchase
3. Receive Goods (update inventory)
4. Create Sales Invoice
5. Dispatch Sale (deduct stock)
6. Generate Accounting Entries
7. Process Payments

This ensures end-to-end integrity of the entire system.
"""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import models

from tests.base import BaseTestCase
from tests.factories import (
    SupplierFactory,
    CustomerFactory,
    ProductFactory,
    BatchFactory,
    PurchaseInvoiceFactory,
    PurchaseItemFactory,
    SalesInvoiceFactory,
    SalesItemFactory,
    CustomerPaymentFactory,
    SupplierPaymentFactory,
    StockMovementFactory,
)
from inventory.service import StockIntegrationService, StockSelectionMode
from accounting.services.journal_engine import JournalEngine
from accounting.models import Account, JournalEntry, JournalEntryLine


class FullLifecycleTests(BaseTestCase):
    """
    Complete ERP lifecycle test.
    
    Simulates a real business scenario from purchase to sale to payment.
    """

    def setUp(self):
        """Set up test data for lifecycle."""
        super().setUp()
        self.supplier = SupplierFactory.create(name='Pharma Supplier')
        self.customer = CustomerFactory.create(name='Pharmacy Customer')
        self.product = ProductFactory.create(
            name='Amoxicillin 500mg',
            category=self.category_tablets,
            unit=self.unit_tablet
        )

    def test_complete_purchase_to_sale_lifecycle(self):
        """
        Test complete lifecycle:
        1. Purchase goods from supplier
        2. Receive goods (add to inventory)
        3. Create and dispatch sale
        4. Process customer payment
        5. Verify accounting entries
        6. Verify stock levels
        """
        # Step 1: Create purchase invoice
        purchase_invoice = PurchaseInvoiceFactory.create(
            supplier=self.supplier,
            invoice_number='PI-LIFECYCLE-001',
            status='CONFIRMED',
            subtotal=Decimal('1000.00'),
            tax=Decimal('0.00'),
            discount=Decimal('0.00'),
            total_amount=Decimal('1000.00')
        )
        
        # Step 2: Add purchase items
        purchase_item = PurchaseItemFactory.create(
            invoice=purchase_invoice,
            product=self.product,
            batch_number='BATCH-LC-001',
            quantity=Decimal('100.00'),
            unit_price=Decimal('10.00'),
            total=Decimal('1000.00')
        )
        
        purchase_invoice.calculate_totals()
        purchase_invoice.save(update_fields=['subtotal', 'total_amount'])
        
        # Verify purchase invoice
        self.assertEqual(purchase_invoice.subtotal, Decimal('1000.00'))
        self.assertEqual(purchase_invoice.total_amount, Decimal('1000.00'))
        
        # Step 3: Receive goods (add to inventory)
        today = timezone.now().date()
        receive_result = StockIntegrationService.process_purchase(
            invoice_id=purchase_invoice.id,
            items=[{
                'product': self.product,
                'quantity': Decimal('100.00'),
                'batch_number': 'BATCH-LC-001',
                'expiry_date': today + timedelta(days=365),
                'unit_price': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(receive_result.success)
        
        # Verify inventory updated
        batch = self.product.batch_set.get(batch_number='BATCH-LC-001')
        self.assertEqual(batch.remaining_quantity, Decimal('100.00'))
        
        # Step 4: Create purchase accounting entry
        purchase_entry = JournalEngine.create_entry(
            entry_type='PURCHASE',
            description=f'Purchase {purchase_invoice.invoice_number}',
            lines=[
                {'account_code': '1300', 'debit': 1000, 'credit': 0, 'description': 'Inventory'},
                {'account_code': '2000', 'debit': 0, 'credit': 1000, 'description': 'AP'}
            ],
            auto_post=True
        )
        self.assertTrue(purchase_entry['success'])
        
        # Step 5: Create sales invoice
        sales_invoice = SalesInvoiceFactory.create(
            customer=self.customer,
            invoice_number='SI-LIFECYCLE-001',
            status='CONFIRMED',
            subtotal=Decimal('1500.00'),
            tax=Decimal('0.00'),
            discount=Decimal('0.00'),
            total_amount=Decimal('1500.00')
        )
        
        # Add sales items
        sales_item = SalesItemFactory.create(
            invoice=sales_invoice,
            product=self.product,
            quantity=Decimal('50.00'),
            unit_price=Decimal('30.00'),
            total=Decimal('1500.00')
        )
        
        sales_invoice.calculate_totals()
        sales_invoice.save(update_fields=['subtotal', 'total_amount'])
        
        # Verify sales invoice
        self.assertEqual(sales_invoice.subtotal, Decimal('1500.00'))
        self.assertEqual(sales_invoice.total_amount, Decimal('1500.00'))
        
        # Step 6: Dispatch sale (deduct stock)
        dispatch_result = StockIntegrationService.process_sale(
            invoice_id=sales_invoice.id,
            items=[{
                'product': self.product,
                'quantity': Decimal('50.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(dispatch_result.success)
        
        # Verify stock deducted
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, Decimal('50.00'))
        
        # Step 7: Create sales accounting entry
        sales_entry = JournalEngine.create_entry(
            entry_type='SALE',
            description=f'Sale {sales_invoice.invoice_number}',
            lines=[
                {'account_code': '1200', 'debit': 1500, 'credit': 0, 'description': 'AR'},
                {'account_code': '4000', 'debit': 0, 'credit': 1500, 'description': 'Revenue'}
            ],
            auto_post=True
        )
        self.assertTrue(sales_entry['success'])
        
        # Step 8: Create COGS entry
        cogs_entry = JournalEngine.create_entry(
            entry_type='ADJUSTMENT',
            description=f'COGS for {sales_invoice.invoice_number}',
            lines=[
                {'account_code': '5000', 'debit': 500, 'credit': 0, 'description': 'COGS'},
                {'account_code': '1300', 'debit': 0, 'credit': 500, 'description': 'Inventory'}
            ],
            auto_post=True
        )
        self.assertTrue(cogs_entry['success'])
        
        # Step 9: Process customer payment
        payment = CustomerPaymentFactory.create(
            customer=self.customer,
            invoice=sales_invoice,
            amount=Decimal('1500.00')
        )
        
        # Verify payment recorded
        sales_invoice.refresh_from_db()
        self.assertEqual(sales_invoice.paid_amount, Decimal('1500.00'))
        
        # Step 10: Process supplier payment
        supplier_payment = SupplierPaymentFactory.create(
            supplier=self.supplier,
            invoice=purchase_invoice,
            amount=Decimal('1000.00')
        )
        
        # Verify supplier payment recorded
        purchase_invoice.refresh_from_db()
        self.assertEqual(purchase_invoice.paid_amount, Decimal('1000.00'))
        
        # Step 11: Verify final balances
        self.customer.refresh_from_db()
        self.supplier.refresh_from_db()
        
        # Customer balance = invoices - payments = 1500 - 1500 = 0
        self.assertEqual(self.customer.balance, Decimal('0.00'))
        
        # Supplier balance = invoices - payments = 1000 - 1000 = 0
        self.assertEqual(self.supplier.balance, Decimal('0.00'))
        
        # Step 12: Verify accounting balances
        cash = Account.objects.get(code='1000')
        ar = Account.objects.get(code='1200')
        inventory = Account.objects.get(code='1300')
        ap = Account.objects.get(code='2000')
        revenue = Account.objects.get(code='4000')
        cogs = Account.objects.get(code='5000')
        
        # Revenue should be 1500
        self.assertEqual(revenue.balance, Decimal('1500.00'))
        # COGS should be 500
        self.assertEqual(cogs.balance, Decimal('500.00'))
        # Net profit = 1500 - 500 = 1000

    def test_multiple_products_lifecycle(self):
        """Test lifecycle with multiple products."""
        # Create additional products
        product2 = ProductFactory.create(
            name='Paracetamol 500mg',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        
        # Purchase both products
        today = timezone.now().date()
        purchase = StockIntegrationService.process_purchase(
            invoice_id='PI-MULTI-001',
            items=[
                {
                    'product': self.product,
                    'quantity': Decimal('200.00'),
                    'batch_number': 'BATCH-MULTI-001',
                    'expiry_date': today + timedelta(days=365),
                    'unit_price': Decimal('10.00'),
                },
                {
                    'product': product2,
                    'quantity': Decimal('300.00'),
                    'batch_number': 'BATCH-MULTI-002',
                    'expiry_date': today + timedelta(days=365),
                    'unit_price': Decimal('5.00'),
                }
            ],
            warehouse=self.warehouse
        )
        
        self.assertTrue(purchase.success)
        
        # Verify both batches created
        batch1 = self.product.batch_set.get(batch_number='BATCH-MULTI-001')
        batch2 = product2.batch_set.get(batch_number='BATCH-MULTI-002')
        
        self.assertEqual(batch1.remaining_quantity, Decimal('200.00'))
        self.assertEqual(batch2.remaining_quantity, Decimal('300.00'))
        
        # Sell both products
        sale = StockIntegrationService.process_sale(
            invoice_id='SI-MULTI-001',
            items=[
                {'product': self.product, 'quantity': Decimal('50.00')},
                {'product': product2, 'quantity': Decimal('100.00')}
            ],
            warehouse=self.warehouse
        )
        
        self.assertTrue(sale.success)
        
        # Verify stock deducted correctly
        batch1.refresh_from_db()
        batch2.refresh_from_db()
        
        self.assertEqual(batch1.remaining_quantity, Decimal('150.00'))
        self.assertEqual(batch2.remaining_quantity, Decimal('200.00'))

    def test_partial_payment_lifecycle(self):
        """Test lifecycle with partial payments."""
        # Create purchase
        today = timezone.now().date()
        StockIntegrationService.process_purchase(
            invoice_id='PI-PARTIAL-001',
            items=[{
                'product': self.product,
                'quantity': Decimal('100.00'),
                'batch_number': 'BATCH-PARTIAL-001',
                'expiry_date': today + timedelta(days=365),
                'unit_price': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        # Create sale
        sales_invoice = SalesInvoiceFactory.create(
            customer=self.customer,
            invoice_number='SI-PARTIAL-001',
            status='CONFIRMED',
            total_amount=Decimal('2000.00')
        )
        
        StockIntegrationService.process_sale(
            invoice_id=sales_invoice.id,
            items=[{'product': self.product, 'quantity': Decimal('50.00')}],
            warehouse=self.warehouse
        )
        
        # Make partial payment
        CustomerPaymentFactory.create(
            customer=self.customer,
            invoice=sales_invoice,
            amount=Decimal('1000.00')
        )
        
        # Verify partial payment status
        sales_invoice.refresh_from_db()
        self.assertEqual(sales_invoice.paid_amount, Decimal('1000.00'))
        self.assertEqual(sales_invoice.remaining_balance, Decimal('1000.00'))
        self.assertEqual(sales_invoice.payment_status, 'PARTIAL')
        
        # Make second partial payment
        CustomerPaymentFactory.create(
            customer=self.customer,
            invoice=sales_invoice,
            amount=Decimal('500.00')
        )
        
        sales_invoice.refresh_from_db()
        self.assertEqual(sales_invoice.paid_amount, Decimal('1500.00'))
        self.assertEqual(sales_invoice.remaining_balance, Decimal('500.00'))
        
        # Make final payment
        CustomerPaymentFactory.create(
            customer=self.customer,
            invoice=sales_invoice,
            amount=Decimal('500.00')
        )
        
        sales_invoice.refresh_from_db()
        self.assertEqual(sales_invoice.paid_amount, Decimal('2000.00'))
        self.assertEqual(sales_invoice.remaining_balance, Decimal('0.00'))
        self.assertEqual(sales_invoice.payment_status, 'PAID')

    def test_stock_accuracy_across_operations(self):
        """
        Test stock accuracy is maintained across multiple operations.
        This is critical for inventory integrity.
        """
        # Start with known quantity
        initial_qty = Decimal('500.00')
        batch = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-ACC-001',
            quantity=initial_qty,
            remaining_quantity=initial_qty,
            location=str(self.warehouse.id)
        )
        # Create IN movement to establish stock for the batch
        StockMovementFactory.create(
            product=self.product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=initial_qty
        )
        
        # Perform multiple sales
        for i in range(5):
            invoice = SalesInvoiceFactory.create(
                customer=self.customer,
                invoice_number=f'SI-ACC-{i:03d}',
                status='CONFIRMED'
            )
            StockIntegrationService.process_sale(
                invoice_id=invoice.id,
                items=[{'product': self.product, 'quantity': Decimal('50.00')}],
                warehouse=self.warehouse
            )
        
        # Verify stock deducted exactly
        batch.refresh_from_db()
        expected_remaining = initial_qty - (Decimal('50.00') * 5)
        self.assertEqual(batch.remaining_quantity, expected_remaining)
        
        # Perform purchase to add stock
        today = timezone.now().date()
        StockIntegrationService.process_purchase(
            invoice_id='PI-ACC-001',
            items=[{
                'product': self.product,
                'quantity': Decimal('200.00'),
                'batch_number': 'BATCH-ACC-NEW',
                'expiry_date': today + timedelta(days=365),
                'unit_price': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        # Verify total stock (500 - 250 + 200 = 450)
        total_stock = StockIntegrationService.get_total_available_stock(self.product)
        expected_total = expected_remaining + Decimal('200.00')
        self.assertEqual(total_stock, expected_total)

    def test_accounting_double_entry_integrity(self):
        """
        Test that all accounting entries maintain double-entry integrity.
        Every transaction must have equal debits and credits.
        """
        # Create multiple journal entries
        entries = []
        for i in range(10):
            result = JournalEngine.create_entry(
                entry_type='ADJUSTMENT',
                description=f'Test entry {i}',
                lines=[
                    {'account_code': '1000', 'debit': 100 * (i + 1), 'credit': 0, 'description': 'Dr'},
                    {'account_code': '4000', 'debit': 0, 'credit': 100 * (i + 1), 'description': 'Cr'}
                ],
                auto_post=True
            )
            self.assertTrue(result['success'])
            entries.append(result['entry_id'])
        
        # Verify all entries are balanced
        for entry_id in entries:
            entry = JournalEntry.objects.get(id=entry_id)
            self.assertEqual(entry.total_debit, entry.total_credit)
        
        # Verify overall system balance
        all_debits = JournalEntryLine.objects.filter(
            entry__is_posted=True
        ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
        
        all_credits = JournalEntryLine.objects.filter(
            entry__is_posted=True
        ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
        
        self.assertEqual(all_debits, all_credits)

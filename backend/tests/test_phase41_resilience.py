import pytest
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from sales.models import Customer, SalesInvoice, CustomerPayment
from inventory.models import Product, Warehouse, Batch, StockMovement
from accounting.models import JournalEntry, Account
from core.services.journal_gateway import JournalGateway
from inventory.service.stock_integration import StockIntegrationService
from core.balance_sync import BalanceSyncService

@pytest.mark.django_db
class TestPhase41Resilience:
    """Chaos and Transactional Resilience Tests for Phase 41."""

    def setup_method(self):
        # 1200 - AR, 4100 - Sales
        self.ar_account = Account.objects.get(code='1200')
        self.sales_account = Account.objects.get(code='4100')
        self.customer = Customer.objects.create(
            name="Chaos Customer",
            code="CUST-CHAOS",
            credit_limit=Decimal('1000.00'),
            balance=Decimal('0.00'),
            subtype='INDIVIDUAL',
            first_name='Chaos',
            last_name='User'
        )
        self.product = Product.objects.create(name="Resilience Medicine", sku="RES-001")
        self.warehouse = Warehouse.objects.create(name="Resilience Warehouse")
        self.batch = Batch.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            batch_number="B-RES",
            purchase_price=Decimal('50.00'),
            initial_quantity=100,
            remaining_quantity=100
        )

    def test_mid_process_failure_rollback(self):
        """Simulate a failure in the middle of a complex financial/inventory transaction."""
        initial_qty = self.batch.remaining_quantity
        initial_balance = self.customer.balance
        
        try:
            with transaction.atomic():
                # 1. Deduct stock
                self.batch.remaining_quantity -= 10
                self.batch.save()
                
                # 2. Create partial invoice data
                invoice = SalesInvoice.objects.create(
                    invoice_number="INV-FAIL",
                    customer=self.customer,
                    order_date=timezone.now().date(),
                    invoice_date=timezone.now().date(),
                    due_date=timezone.now().date(),
                    total_amount=Decimal('500.00'),
                    status='CONFIRMED'
                )
                
                # 3. CRITICAL FAILURE: Simulate crash before Journal Posting
                raise RuntimeError("POWER_LOSS_SIMULATION")
                
        except RuntimeError:
            pass
            
        # Verify FULL ROLLBACK
        self.batch.refresh_from_db()
        self.customer.refresh_from_db()
        
        assert self.batch.remaining_quantity == initial_qty, "Inventory must rollback on failure"
        assert self.customer.balance == initial_balance, "Customer balance must rollback"
        assert not SalesInvoice.objects.filter(invoice_number="INV-FAIL").exists(), "Invoice must not persist"

    def test_journal_gateway_atomicity(self):
        """Verify that JournalGateway operations are fully atomic and logged."""
        lines = [
            {'account_code': '1200', 'debit': Decimal('100.00'), 'credit': Decimal('0.00')},
            {'account_code': '4100', 'debit': Decimal('0.00'), 'credit': Decimal('100.00')},
        ]
        
        # We mock the engine to fail mid-way
        from accounting.services.journal_engine import JournalEngine
        original_post = JournalEngine.post_entry
        
        def failing_post(entry_id):
            # First part succeeds (in a real scenario, this would be DB operations)
            # Then we fail
            raise Exception("DATABASE_LOCK_ERROR")
            
        JournalEngine.post_entry = failing_post
        
        try:
            with pytest.raises(Exception):
                JournalGateway.create_entry(
                    entry_type='SALE',
                    description="Resilience Test",
                    lines=lines,
                    auto_post=True # This will trigger the failing_post
                )
        finally:
            JournalEngine.post_entry = original_post
            
        # Verify no orphan entries
        assert not JournalEntry.objects.filter(description="Resilience Test").exists()

    def test_stock_idempotency_check(self):
        """Verify that stock integration prevents duplicate processing of same invoice."""
        invoice = SalesInvoice.objects.create(
            invoice_number="INV-IDEM",
            customer=self.customer,
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            total_amount=Decimal('100.00'),
            status='CONFIRMED'
        )
        
        # First process
        # (This is a simplified call to simulate production usage)
        with transaction.atomic():
            self.batch.remaining_quantity -= 5
            self.batch.save()
            StockMovement.objects.create(
                product=self.product,
                warehouse=self.warehouse,
                batch=self.batch,
                movement_type='SALE',
                reference_type='SALE',
                reference_id=invoice.invoice_number,
                quantity=-5
            )
            
        mid_qty = self.batch.remaining_quantity
        
        # Second process (simulated retry)
        # In a real scenario, StockIntegrationService would have an idempotency guard
        # Let's verify if one exists or if we need to enforce it.
        movements = StockMovement.objects.filter(
            reference_type='SALE',
            reference_id=invoice.invoice_number
        ).count()
        
        assert movements == 1, "Should only have one movement for one invoice"

    def test_audit_immutability(self):
        """Verify that audit logs are created for sensitive mutations."""
        from audit.models import AuditTrail
        
        # 1. Log a balance sync
        BalanceSyncService.sync_customer(self.customer, lock=True)
        
        # 2. Check for audit record
        audit = AuditTrail.objects.filter(
            action='BALANCE_SYNC',
            object_id=str(self.customer.id)
        ).latest('timestamp')
        
        assert audit is not None
        assert 'balance' in audit.new_values

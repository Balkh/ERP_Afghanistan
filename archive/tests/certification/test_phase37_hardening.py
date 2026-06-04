import pytest
from decimal import Decimal
from django.db import transaction
from accounting.models import Account, JournalEntry
from inventory.models import Batch, Product, Warehouse, Category, Unit
from sales.models import SalesInvoice, Customer
from core.services.journal_gateway import JournalGateway
from core.services.financial_truth_engine import FinancialTruthEngine
from django.utils import timezone

@pytest.mark.django_db
class TestPhase37Hardening:
    """Tests for Phase 37 - Stability & Hardening."""

    def test_transaction_atomic_integrity(self):
        """Verify that partial failures in a transaction result in a full rollback."""
        # Setup
        customer = Customer.objects.create(name="Test Customer", balance=Decimal('0.00'))
        category = Category.objects.create(name="Test Category", is_active=True)
        unit = Unit.objects.create(name="Piece", symbol="PCS", is_active=True)
        product = Product.objects.create(
            name="Test Product", sku="HARDEN-001", barcode="BAR_HARDEN001",
            generic_name="Test Generic", brand_name="Test Brand",
            strength="500mg", form="Tablet", manufacturer="Test Mfg",
            category=category, unit=unit
        )
        warehouse = Warehouse.objects.create(name="Main Warehouse")
        batch = Batch.objects.create(
            product=product,
            warehouse=warehouse,
            batch_number="B001",
            purchase_price=Decimal('100.00'),
            initial_quantity=10,
            remaining_quantity=10
        )
        
        # Initial state
        initial_batch_qty = batch.remaining_quantity
        
        try:
            with transaction.atomic():
                # 1. Update batch (Operational change)
                batch.remaining_quantity -= 1
                batch.save()
                
                # 2. Simulate failure before accounting post
                raise ValueError("Simulated failure after operational change")
                
        except ValueError:
            pass
            
        # Verify rollback
        batch.refresh_from_db()
        assert batch.remaining_quantity == initial_batch_qty, "Batch quantity should have rolled back"

    def test_journal_gateway_mandatory_enforcement(self):
        """Verify that JournalGateway enforces balanced entries and valid accounts."""
        # 1200 - AR, 4100 - Sales
        ar_account = Account.objects.get(code='1200')
        sales_account = Account.objects.get(code='4100')
        
        lines = [
            {'account_id': ar_account.id, 'debit': Decimal('100.00'), 'credit': Decimal('0.00')},
            {'account_id': sales_account.id, 'debit': Decimal('0.00'), 'credit': Decimal('90.00')}, # UNBALANCED
        ]
        
        with pytest.raises(ValueError, match="Journal entry is not balanced"):
            JournalGateway.post_entry(
                entry_type='SALE',
                lines=lines,
                description="Unbalanced test"
            )

    def test_idempotency_simulation(self):
        """Verify that duplicate calls to critical services are handled or rejected."""
        # This is a placeholder for actual idempotency keys if implemented
        # For now, we verify that multiple posts of the same data create distinct entries (as expected)
        # OR we could implement a check in the service.
        pass

    def test_null_price_handling(self):
        """Verify that the system handles batches with missing or zero prices explicitly."""
        category = Category.objects.create(name="Free Category", is_active=True)
        unit = Unit.objects.create(name="Piece", symbol="PCS", is_active=True)
        product = Product.objects.create(
            name="Free Product", sku="FREE-001", barcode="BAR_FREE001",
            generic_name="Free Generic", brand_name="Free Brand",
            strength="250mg", form="Capsule", manufacturer="Free Mfg",
            category=category, unit=unit
        )
        warehouse = Warehouse.objects.create(name="Main Warehouse")
        batch = Batch.objects.create(
            product=product,
            warehouse=warehouse,
            batch_number="B-FREE",
            purchase_price=Decimal('0.00'), # Zero price
            initial_quantity=10,
            remaining_quantity=10
        )
        
        # Truth engine should handle zero price without crashing
        value = FinancialTruthEngine.get_batch_valuation(batch)
        assert value == Decimal('0.00')

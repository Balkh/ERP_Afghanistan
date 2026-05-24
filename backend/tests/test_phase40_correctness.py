import pytest
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from sales.models import Customer, SalesInvoice, CustomerPayment
from inventory.models import Product, Warehouse, Batch, StockMovement
from returns.models import ReturnOrder, ReturnItem
from accounting.models import Account, JournalEntry
from core.services.anomaly_detection import AnomalyDetectionEngine, AnomalyType
from hr.models import Employee

@pytest.mark.django_db
class TestPhase40Correctness:
    """Tests for Phase 40 — Correctness and Workflow Finalization."""

    def setup_method(self):
        # Setup common data
        self.customer = Customer.objects.create(
            name="Test Customer",
            code="CUST-40",
            credit_limit=Decimal('1000.00'),
            balance=Decimal('0.00'),
            subtype='INDIVIDUAL',
            first_name='Test',
            last_name='User'
        )
        self.product = Product.objects.create(name="Correctness Medicine", sku="CORR-001")
        self.warehouse = Warehouse.objects.create(name="Logic Warehouse")
        self.batch = Batch.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            batch_number="B40",
            purchase_price=Decimal('50.00'),
            initial_quantity=100,
            remaining_quantity=100
        )
        self.employee = Employee.objects.create(
            first_name="Admin",
            last_name="User",
            employee_id="EMP-001",
            status='ACTIVE'
        )

    def test_anomaly_engine_set_based_overpayment(self):
        """Verify set-based overpayment detection."""
        # Create an overpaid invoice
        invoice = SalesInvoice.objects.create(
            invoice_number="INV-OVER",
            customer=self.customer,
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('150.00'), # OVERPAID
            status='PAID'
        )
        
        anomalies = AnomalyDetectionEngine.detect_payment_anomalies()
        overpayment_anomalies = [a for a in anomalies if a['anomaly_type'] == AnomalyType.OVERPAYMENT_EDGE]
        
        assert len(overpayment_anomalies) > 0
        assert overpayment_anomalies[0]['entity_id'] == str(invoice.pk)
        assert Decimal(overpayment_anomalies[0]['amount']) == Decimal('50.00')

    def test_return_order_completed_state(self):
        """Verify ReturnOrder can transition to COMPLETED state (Fix for BUG-059)."""
        # Create a sale invoice
        invoice = SalesInvoice.objects.create(
            invoice_number="INV-RET",
            customer=self.customer,
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            total_amount=Decimal('200.00'),
            paid_amount=Decimal('200.00'),
            status='PAID'
        )
        
        # Create return order
        ret = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            total_amount=Decimal('50.00'),
            reason="Damaged"
        )
        
        # Mock items and approve
        ReturnItem.objects.create(
            return_order=ret,
            product=self.product,
            batch=self.batch,
            return_quantity=1,
            unit_price=Decimal('50.00'),
            total=Decimal('50.00')
        )
        
        # Mock _create_accounting_entries to avoid full engine dependency in this test
        ret._create_accounting_entries = lambda emp: None
        
        ret.approve(self.employee)
        assert ret.status == 'APPROVED'
        
        # Test COMPLETED state transition
        ret.complete(self.employee)
        assert ret.status == 'COMPLETED'
        
        # Verify invalid transition from COMPLETED to VOIDED
        with pytest.raises(Exception):
            ret.void(self.employee, reason="Too late")

    def test_anomaly_engine_credit_near_breach(self):
        """Verify optimized credit breach detection."""
        # Set balance near limit (90%)
        self.customer.balance = Decimal('900.00')
        self.customer.save()
        
        anomalies = AnomalyDetectionEngine.detect_invoice_anomalies()
        credit_anomalies = [a for a in anomalies if a['anomaly_type'] == AnomalyType.CREDIT_NEAR_BREACH]
        
        assert len(credit_anomalies) > 0
        assert credit_anomalies[0]['entity_id'] == str(self.customer.pk)
        assert "90.0%" in credit_anomalies[0]['explanation']

    def test_deterministic_fefo_order(self):
        """Verify that stock selection remains deterministic (Regression test for Phase 38/39)."""
        # Create another batch with same expiry
        batch2 = Batch.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            batch_number="B40-2",
            purchase_price=Decimal('50.00'),
            initial_quantity=100,
            remaining_quantity=100,
            expiry_date=self.batch.expiry_date
        )
        
        from inventory.service.stock_integration import StockIntegrationService, StockSelectionMode
        
        # Should always pick B40 before B40-2 if sorted by batch_number tie-breaker
        batches = StockIntegrationService._get_available_batches(
            self.product, self.warehouse, Decimal('10'), StockSelectionMode.FEFO
        )
        
        assert list(batches)[0].batch_number == "B40"
        assert list(batches)[1].batch_number == "B40-2"

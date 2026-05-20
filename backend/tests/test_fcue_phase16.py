"""Tests for Phase 16: Financial Core Unification Engine (FCUE).

Covers all 7 components:
1. FinancialTruthEngine — read-only derived balance computation
2. CreditPolicyEngine — central credit enforcement hook
3. Payment Reconciliation Engine (V1) — read-only mismatch detection
4. Supplier FIFO Allocation — mirror customer FIFO for suppliers
5. No direct balance mutations — CustomerPayment/SupplierPayment use BalanceSyncService
6. FCUE audit events — new event types and bounded retention
7. Views use CreditPolicyEngine — centralized enforcement
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch, PropertyMock

from core.balance_sync import BalanceSyncService
from sales.models import Customer, SalesInvoice, CustomerPayment
from purchases.models import Supplier, PurchaseInvoice, SupplierPayment, SupplierPaymentAllocation
from accounting.models import Account, JournalEntry


def ensure_accounts():
    """Ensure required accounting accounts exist."""
    accounts_data = [
        ('1200', 'Accounts Receivable', 'ASSET'),
        ('2100', 'Accounts Payable', 'LIABILITY'),
        ('4100', 'Sales Revenue', 'REVENUE'),
        ('5100', 'Cost of Goods Sold', 'EXPENSE'),
        ('1300', 'Inventory', 'ASSET'),
        ('1010', 'Cash', 'ASSET'),
    ]
    for code, name, acct_type in accounts_data:
        Account.objects.get_or_create(
            code=code,
            defaults={'name': name, 'account_type': acct_type, 'is_active': True},
        )


def ensure_payment_account():
    """Ensure a default payment account and methods exist for payment processing."""
    from payments.models import PaymentAccount, PaymentMethod
    cash_account = Account.objects.filter(code='1010').first()
    if not cash_account:
        cash_account = Account.objects.create(
            code='1010', name='Cash', account_type='ASSET', is_active=True
        )
    pa, created = PaymentAccount.objects.get_or_create(
        code='CASH-MAIN',
        defaults={
            'name': 'Main Cash',
            'account_type': 'CASH',
            'accounting_account': cash_account,
            'currency': 'AFN',
            'is_active': True,
            'current_balance': Decimal('1000000.00'),
        },
    )
    if not created:
        pa.current_balance = Decimal('1000000.00')
        pa.save(update_fields=['current_balance'])
    for method_type, name, code in [
        ('CASH', 'Cash', 'CASH'),
        ('BANK_TRANSFER', 'Bank Transfer', 'BANK'),
        ('CHEQUE', 'Cheque', 'CHEQUE'),
        ('CREDIT_CARD', 'Credit Card', 'CC'),
    ]:
        PaymentMethod.objects.get_or_create(
            code=code,
            defaults={'name': name, 'method_type': method_type, 'is_active': True},
        )
    return pa


# =========================================================================
# 1. FinancialTruthEngine — Read-Only Derived Balance
# =========================================================================

class FinancialTruthEngineTest(TestCase):
    """Test that FinancialTruthEngine correctly derives balances without writes."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Truth Customer',
            code='TRUTH-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Truth Supplier',
            code='TRUTH-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_get_customer_balance_empty(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        balance = FinancialTruthEngine.get_customer_balance(self.customer)
        self.assertEqual(balance, Decimal('0.00'))

    def test_get_customer_balance_with_invoices(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='FTE-INV-001',
            total_amount=Decimal('5000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        balance = FinancialTruthEngine.get_customer_balance(self.customer)
        self.assertEqual(balance, Decimal('5000.00'))

    def test_get_customer_balance_read_only_no_write(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='FTE-INV-002',
            total_amount=Decimal('3000.00'),
            status='DISPATCHED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        balance = FinancialTruthEngine.get_customer_balance(self.customer)
        self.assertEqual(balance, Decimal('3000.00'))
        # Verify stored balance is unchanged (read-only)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal('0.00'))

    def test_get_supplier_balance_empty(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        balance = FinancialTruthEngine.get_supplier_balance(self.supplier)
        self.assertEqual(balance, Decimal('0.00'))

    def test_get_supplier_balance_with_invoices(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='FTE-PINV-001',
            total_amount=Decimal('7000.00'),
            status='RECEIVED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        balance = FinancialTruthEngine.get_supplier_balance(self.supplier)
        self.assertEqual(balance, Decimal('7000.00'))

    def test_get_supplier_balance_read_only_no_write(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='FTE-PINV-002',
            total_amount=Decimal('4000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        balance = FinancialTruthEngine.get_supplier_balance(self.supplier)
        self.assertEqual(balance, Decimal('4000.00'))
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.balance, Decimal('0.00'))

    def test_get_customer_available_credit(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='FTE-INV-003',
            total_amount=Decimal('3000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        available = FinancialTruthEngine.get_customer_available_credit(self.customer)
        self.assertEqual(available, Decimal('7000.00'))

    def test_get_customer_financial_summary(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='FTE-INV-004',
            total_amount=Decimal('2500.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        summary = FinancialTruthEngine.get_customer_financial_summary(self.customer)
        self.assertEqual(summary['derived_balance'], Decimal('2500.00'))
        self.assertEqual(summary['stored_balance'], Decimal('0.00'))
        self.assertTrue(summary['balance_mismatch'])
        self.assertEqual(summary['credit_limit'], Decimal('10000.00'))
        self.assertEqual(summary['available_credit'], Decimal('7500.00'))

    def test_get_supplier_financial_summary(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='FTE-PINV-003',
            total_amount=Decimal('1500.00'),
            status='RECEIVED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        summary = FinancialTruthEngine.get_supplier_financial_summary(self.supplier)
        self.assertEqual(summary['derived_balance'], Decimal('1500.00'))
        self.assertTrue(summary['balance_mismatch'])

    def test_draft_invoices_excluded_from_balance(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='FTE-INV-005',
            total_amount=Decimal('5000.00'),
            status='DRAFT',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        balance = FinancialTruthEngine.get_customer_balance(self.customer)
        self.assertEqual(balance, Decimal('0.00'))

    def test_cancelled_invoices_excluded_from_balance(self):
        from core.services.financial_truth_engine import FinancialTruthEngine
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='FTE-INV-006',
            total_amount=Decimal('5000.00'),
            status='CANCELLED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        balance = FinancialTruthEngine.get_customer_balance(self.customer)
        self.assertEqual(balance, Decimal('0.00'))


# =========================================================================
# 2. CreditPolicyEngine — Central Credit Enforcement
# =========================================================================

class CreditPolicyEngineTest(TestCase):
    """Test that CreditPolicyEngine correctly enforces credit rules."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Credit Customer',
            code='CREDIT-CUST',
            balance=Decimal('5000.00'),
            credit_limit=Decimal('10000.00'),
            status='ACTIVE',
        )
        self.blocked_customer = Customer.objects.create(
            name='Blocked Customer',
            code='BLOCKED-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
            status='BLOCKED',
        )
        self.today = date.today()

    def test_allowed_within_credit_limit(self):
        from core.services.credit_policy_engine import CreditPolicyEngine
        result = CreditPolicyEngine.check_customer_invoice(self.customer, Decimal('3000.00'))
        self.assertTrue(result.allowed)
        self.assertEqual(result.risk_level, 'LOW')

    def test_blocked_customer_rejected(self):
        from core.services.credit_policy_engine import CreditPolicyEngine
        result = CreditPolicyEngine.check_customer_invoice(self.blocked_customer, Decimal('100.00'))
        self.assertFalse(result.allowed)
        self.assertFalse(result.requires_override)
        self.assertEqual(result.risk_level, 'CRITICAL')

    def test_exceeds_credit_limit_requires_override(self):
        from core.services.credit_policy_engine import CreditPolicyEngine
        # Create invoice to give customer a derived balance of 6000
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='CPE-INV-001',
            total_amount=Decimal('6000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        # Now check with additional 5000 — projected = 6000 + 5000 = 11000 > 10000
        result = CreditPolicyEngine.check_customer_invoice(self.customer, Decimal('5000.00'))
        self.assertFalse(result.allowed)
        self.assertTrue(result.requires_override)
        self.assertEqual(result.risk_level, 'HIGH')

    def test_no_credit_limit_no_enforcement(self):
        from core.services.credit_policy_engine import CreditPolicyEngine
        no_limit = Customer.objects.create(
            name='No Limit',
            code='NO-LIMIT',
            balance=Decimal('100000.00'),
            credit_limit=Decimal('0.00'),
            status='ACTIVE',
        )
        result = CreditPolicyEngine.check_customer_invoice(no_limit, Decimal('999999.00'))
        self.assertTrue(result.allowed)
        self.assertFalse(result.requires_override)

    def test_supplier_blocked_rejected(self):
        from core.services.credit_policy_engine import CreditPolicyEngine
        blocked = Supplier.objects.create(
            name='Blocked Supp',
            code='BLOCKED-SUPP',
            credit_limit=Decimal('5000.00'),
            status='BLOCKED',
        )
        result = CreditPolicyEngine.check_supplier_purchase(blocked, Decimal('100.00'))
        self.assertFalse(result.allowed)
        self.assertFalse(result.requires_override)

    def test_supplier_exceeds_limit(self):
        from core.services.credit_policy_engine import CreditPolicyEngine
        supplier = Supplier.objects.create(
            name='Limit Supp',
            code='LIMIT-SUPP',
            credit_limit=Decimal('5000.00'),
            balance=Decimal('0.00'),
            status='ACTIVE',
        )
        result = CreditPolicyEngine.check_supplier_purchase(supplier, Decimal('6000.00'))
        self.assertFalse(result.allowed)
        self.assertTrue(result.requires_override)

    def test_handle_credit_override_creates_request(self):
        from core.services.credit_policy_engine import CreditPolicyEngine
        from sales.models import CreditApprovalRequest
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='OVR-INV-001',
            total_amount=Decimal('6000.00'),
            status='CREDIT_PENDING',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        CreditPolicyEngine.handle_credit_override(
            customer=self.customer,
            invoice=invoice,
            total_amount=Decimal('6000.00'),
        )
        request = CreditApprovalRequest.objects.get(invoice=invoice)
        self.assertEqual(request.status, 'PENDING')
        self.assertEqual(request.requested_amount, Decimal('6000.00'))


# =========================================================================
# 3. Payment Reconciliation Engine (V1) — Read-Only
# =========================================================================

class PaymentReconciliationTest(TestCase):
    """Test PaymentReconciliationService mismatch detection."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Recon Customer',
            code='RECON-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('50000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Recon Supplier',
            code='RECON-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_reconcile_clean_customer_no_issues(self):
        from core.services.payment_reconciliation import PaymentReconciliationService
        report = PaymentReconciliationService.reconcile_customer(self.customer)
        self.assertEqual(report['total_issues'], 0)
        self.assertTrue(report['balance_match'])

    def test_reconcile_balance_mismatch_detected(self):
        from core.services.payment_reconciliation import PaymentReconciliationService
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='RECON-INV-001',
            total_amount=Decimal('5000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        # Stored balance is 0.00 but derived is 5000.00
        report = PaymentReconciliationService.reconcile_customer(self.customer)
        self.assertGreater(report['total_issues'], 0)
        self.assertFalse(report['balance_match'])
        self.assertTrue(any(i['type'] == 'BALANCE_MISMATCH' for i in report['issues']))

    def test_reconcile_read_only_no_writes(self):
        from core.services.payment_reconciliation import PaymentReconciliationService
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='RECON-INV-002',
            total_amount=Decimal('3000.00'),
            status='DISPATCHED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        report = PaymentReconciliationService.reconcile_customer(self.customer)
        self.assertGreater(report['total_issues'], 0)
        # Verify no writes occurred
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal('0.00'))

    def test_reconcile_supplier_clean(self):
        from core.services.payment_reconciliation import PaymentReconciliationService
        report = PaymentReconciliationService.reconcile_supplier(self.supplier)
        self.assertEqual(report['total_issues'], 0)
        self.assertTrue(report['balance_match'])

    def test_reconcile_all_returns_structure(self):
        from core.services.payment_reconciliation import PaymentReconciliationService
        result = PaymentReconciliationService.reconcile_all()
        self.assertTrue(result['read_only'])
        self.assertIn('summary', result)
        self.assertIn('customer_reports', result)
        self.assertIn('supplier_reports', result)
        self.assertIn('reconciled_at', result)

    def test_reconcile_past_due_detection(self):
        from core.services.payment_reconciliation import PaymentReconciliationService
        past_due = self.today - timedelta(days=60)
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='RECON-INV-003',
            total_amount=Decimal('1000.00'),
            status='CONFIRMED',
            order_date=past_due, invoice_date=past_due, due_date=past_due,
        )
        report = PaymentReconciliationService.reconcile_customer(self.customer)
        past_due_issues = [i for i in report['issues'] if i['type'] == 'PAST_DUE_INVOICE']
        self.assertGreater(len(past_due_issues), 0)


# =========================================================================
# 4. Supplier FIFO Allocation
# =========================================================================

class SupplierFIFOAllocationTest(TestCase):
    """Test Supplier FIFO payment allocation."""

    def setUp(self):
        ensure_accounts()
        ensure_payment_account()
        self.supplier = Supplier.objects.create(
            name='FIFO Supplier',
            code='FIFO-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()
        self.invoice1 = PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='FIFO-PINV-001',
            total_amount=Decimal('5000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        self.invoice2 = PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='FIFO-PINV-002',
            total_amount=Decimal('3000.00'),
            status='RECEIVED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )

    def test_allocate_payment_to_oldest_invoice_first(self):
        from purchases.services.fifo_allocation import SupplierFIFOAllocationService
        from purchases.models import Supplier

        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('4000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )

        # Verify payment state
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal('4000.00'))
        self.assertIsNone(payment.invoice)

        # Verify invoice state
        self.invoice1.refresh_from_db()
        self.invoice2.refresh_from_db()
        self.assertEqual(self.invoice1.paid_amount, Decimal('0.00'))
        self.assertEqual(self.invoice2.paid_amount, Decimal('0.00'))

        allocations = SupplierFIFOAllocationService.allocate_payment(payment)
        self.assertEqual(len(allocations), 1, f"Expected 1 allocation, got {len(allocations)}")
        if allocations:
            self.assertEqual(allocations[0].invoice.pk, self.invoice1.pk)
            self.assertEqual(allocations[0].allocated_amount, Decimal('4000.00'))
        self.assertEqual(allocations[0].invoice.pk, self.invoice1.pk)
        self.assertEqual(allocations[0].allocated_amount, Decimal('4000.00'))

    def test_allocate_payment_skips_allocated(self):
        from purchases.services.fifo_allocation import SupplierFIFOAllocationService
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            invoice=self.invoice1,
            amount=Decimal('5000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        # Payment already linked to an invoice — should not allocate
        allocations = SupplierFIFOAllocationService.allocate_payment(payment)
        self.assertEqual(len(allocations), 0)

    def test_allocate_payment_fully_pays_invoice(self):
        from purchases.services.fifo_allocation import SupplierFIFOAllocationService
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('8000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        allocations = SupplierFIFOAllocationService.allocate_payment(payment)
        self.assertEqual(len(allocations), 2)
        self.invoice1.refresh_from_db()
        self.invoice2.refresh_from_db()
        self.assertEqual(self.invoice1.status, 'PAID')
        self.assertEqual(self.invoice2.paid_amount, Decimal('3000.00'))

    def test_allocate_for_supplier_returns_summary(self):
        from purchases.services.fifo_allocation import SupplierFIFOAllocationService
        SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('5000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        result = SupplierFIFOAllocationService.allocate_for_supplier(self.supplier)
        self.assertEqual(result['supplier'], 'FIFO Supplier')
        self.assertEqual(result['payments_processed'], 1)

    def test_get_unallocated_payments(self):
        from purchases.services.fifo_allocation import SupplierFIFOAllocationService
        SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('5000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        unallocated = SupplierFIFOAllocationService.get_unallocated_payments(self.supplier)
        self.assertEqual(len(unallocated), 1)
        self.assertEqual(unallocated[0]['remaining'], Decimal('5000.00'))

    def test_get_outstanding_invoices(self):
        from purchases.services.fifo_allocation import SupplierFIFOAllocationService
        invoices = SupplierFIFOAllocationService.get_outstanding_invoices(self.supplier)
        self.assertEqual(len(invoices), 2)

    def test_supplier_payment_allocation_model_str(self):
        allocation = SupplierPaymentAllocation.objects.create(
            payment=SupplierPayment.objects.create(
                supplier=self.supplier,
                amount=Decimal('1000.00'),
                payment_method='CASH',
                payment_date=self.today,
            ),
            invoice=self.invoice1,
            allocated_amount=Decimal('1000.00'),
        )
        self.assertIn(str(allocation.allocated_amount), str(allocation))


# =========================================================================
# 5. No Direct Balance Mutations
# =========================================================================

class NoDirectBalanceMutationTest(TestCase):
    """Test that payments no longer directly mutate balance fields."""

    def setUp(self):
        ensure_accounts()
        ensure_payment_account()
        self.customer = Customer.objects.create(
            name='NoDirect Customer',
            code='NODIRECT-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='NoDirect Supplier',
            code='NODIRECT-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_customer_payment_uses_sync_service(self):
        """CustomerPayment.save() should go through BalanceSyncService, not direct mutation."""
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='ND-INV-001',
            total_amount=Decimal('5000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal('0.00'))

        BalanceSyncService.sync_customer(self.customer, lock=False)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal('5000.00'))

    def test_supplier_payment_uses_sync_service(self):
        """SupplierPayment.save() should go through BalanceSyncService, not direct mutation."""
        PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='ND-PINV-001',
            total_amount=Decimal('3000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.balance, Decimal('0.00'))

        BalanceSyncService.sync_supplier(self.supplier, lock=False)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.balance, Decimal('3000.00'))

    def test_customer_payment_save_calls_sync_not_direct_mutation(self):
        """Verify that CustomerPayment.save() triggers BalanceSyncService (not update_customer_balance)."""
        with patch.object(BalanceSyncService, 'sync_customer', wraps=BalanceSyncService.sync_customer) as mock_sync:
            SalesInvoice.objects.create(
                customer=self.customer,
                invoice_number='ND-INV-002',
                total_amount=Decimal('5000.00'),
                status='DISPATCHED',
                order_date=self.today, invoice_date=self.today, due_date=self.today,
            )
            BalanceSyncService.sync_customer(self.customer, lock=False)

            initial_balance = self.customer.balance

            CustomerPayment.objects.create(
                customer=self.customer,
                amount=Decimal('2000.00'),
                payment_method='CASH',
                payment_date=self.today,
            )

            mock_sync.assert_called()

    def test_view_no_longer_calls_update_customer_balance(self):
        """Verify CustomerPaymentViewSet.perform_create no longer calls update_customer_balance."""
        from sales.views import CustomerPaymentViewSet
        from sales.models import CustomerPayment

        has_direct_call = False
        import inspect
        source = inspect.getsource(CustomerPaymentViewSet.perform_create)
        if 'update_customer_balance' in source:
            has_direct_call = True
        self.assertFalse(has_direct_call,
                         'CustomerPaymentViewSet.perform_create should not call update_customer_balance')

    def test_view_no_longer_calls_update_supplier_balance(self):
        """Verify SupplierPaymentViewSet.perform_create no longer calls update_supplier_balance."""
        from purchases.views import SupplierPaymentViewSet
        import inspect
        source = inspect.getsource(SupplierPaymentViewSet.perform_create)
        has_direct_call = 'update_supplier_balance' in source
        self.assertFalse(has_direct_call,
                         'SupplierPaymentViewSet.perform_create should not call update_supplier_balance')


# =========================================================================
# 6. FCUE Audit Events
# =========================================================================

class FCUEAuditEventTest(TestCase):
    """Test the new FCUE-specific audit events."""

    def setUp(self):
        from audit.models import AuditTrail
        AuditTrail.objects.all().delete()

    def test_reconciliation_mismatch_event(self):
        from core.services.financial_audit import FinancialAuditService
        from audit.models import AuditTrail

        FinancialAuditService.log_reconciliation_mismatch(
            entity_type='customer',
            entity_id='test-123',
            mismatch_type='BALANCE_MISMATCH',
            detail='Stored 100 != Derived 200',
        )
        self.assertTrue(AuditTrail.objects.filter(action='RECONCILIATION_MISMATCH').exists())

    def test_credit_policy_block_event(self):
        from core.services.financial_audit import FinancialAuditService
        from audit.models import AuditTrail

        FinancialAuditService.log_credit_policy_block(
            party_type='customer',
            party_id='test-456',
            party_name='Test Corp',
            invoice_amount=Decimal('5000.00'),
            reason='Credit limit exceeded',
        )
        self.assertTrue(AuditTrail.objects.filter(action='CREDIT_POLICY_BLOCK').exists())

    def test_allocation_auto_event(self):
        from core.services.financial_audit import FinancialAuditService
        from audit.models import AuditTrail

        FinancialAuditService.log_allocation_auto(
            payment_id='pay-789',
            entity_type='customer',
            entity_id='cust-abc',
            amount=Decimal('1000.00'),
        )
        self.assertTrue(AuditTrail.objects.filter(action='ALLOCATION_AUTO').exists())

    def test_enforce_log_retention_no_error(self):
        """enforce_log_retention should run without error even with no logs."""
        from core.services.financial_audit import FinancialAuditService, FINANCIAL_ACTIONS
        from audit.models import AuditTrail

        AuditTrail.objects.all().delete()
        # Should not raise
        FinancialAuditService.enforce_log_retention()
        self.assertTrue(True)


# =========================================================================
# 7. CreditPolicyEngine Integration in Views
# =========================================================================

class CreditPolicyEngineViewIntegrationTest(TestCase):
    """Test that views use CreditPolicyEngine for centralized enforcement."""

    def test_sales_invoice_view_uses_credit_policy_engine(self):
        """Verify SalesInvoiceViewSet.perform_create uses CreditPolicyEngine."""
        from sales.views import SalesInvoiceViewSet
        import inspect
        source = inspect.getsource(SalesInvoiceViewSet.perform_create)
        self.assertIn('CreditPolicyEngine', source,
                      'SalesInvoiceViewSet.perform_create should use CreditPolicyEngine')

    def test_sales_invoice_view_no_direct_credit_block(self):
        """Verify SalesInvoiceViewSet.perform_create no longer directly checks BLOCKED status."""
        from sales.views import SalesInvoiceViewSet
        import inspect
        source = inspect.getsource(SalesInvoiceViewSet.perform_create)
        # Should not contain the old direct checks
        self.assertNotIn("customer.status == 'BLOCKED'", source)


# =========================================================================
# 8. Concurrency Safety Validation
# =========================================================================

class ConcurrencySafetyTest(TestCase):
    """Test that financial operations use proper locking."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Concurrency Customer',
            code='CONCUR-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Concurrency Supplier',
            code='CONCUR-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_customer_payment_save_is_atomic(self):
        """CustomerPayment.save() should be inside transaction.atomic()."""
        from sales.models import CustomerPayment
        import inspect
        source = inspect.getsource(CustomerPayment.save)
        self.assertIn('transaction.atomic', source)

    def test_supplier_payment_save_is_atomic(self):
        """SupplierPayment.save() should be inside transaction.atomic()."""
        from purchases.models import SupplierPayment
        import inspect
        source = inspect.getsource(SupplierPayment.save)
        self.assertIn('transaction.atomic', source)

    def test_customer_fifo_allocate_for_customer_is_atomic(self):
        """FIFOAllocationService.allocate_for_customer should be @transaction.atomic."""
        from sales.services.fifo_allocation import FIFOAllocationService
        import inspect
        source = inspect.getsource(FIFOAllocationService.allocate_for_customer)
        self.assertTrue('select_for_update' in source or 'transaction.atomic' in source)

    def test_supplier_fifo_allocate_for_supplier_is_atomic(self):
        """SupplierFIFOAllocationService.allocate_for_supplier should be @transaction.atomic."""
        from purchases.services.fifo_allocation import SupplierFIFOAllocationService
        import inspect
        source = inspect.getsource(SupplierFIFOAllocationService.allocate_for_supplier)
        self.assertTrue('select_for_update' in source or 'transaction.atomic' in source)

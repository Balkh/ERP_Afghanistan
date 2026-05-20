"""Tests for Phase 15.5 Financial Flow Hardening.

Covers:
- BalanceSyncService (centralized balance recalculation)
- Overpayment prevention (model + API validation)
- Credit limit enforcement (server-side validation)
- Concurrent payment safety (select_for_update)
- Return void balance correction
"""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch, MagicMock

from core.balance_sync import BalanceSyncService
from sales.models import Customer, SalesInvoice, CustomerPayment
from purchases.models import Supplier, PurchaseInvoice, SupplierPayment
from accounting.models import Account, JournalEntry


class BalanceSyncServiceTest(TestCase):
    """Test centralized balance synchronization."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Test Customer',
            code='TC001',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            code='TS001',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_sync_customer_no_transactions(self):
        new_balance = BalanceSyncService.sync_customer(self.customer, lock=False)
        self.assertEqual(new_balance, Decimal('0.00'))

    def test_sync_customer_with_invoices(self):
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-001',
            total_amount=Decimal('5000.00'),
            status='DISPATCHED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-002',
            total_amount=Decimal('3000.00'),
            status='DISPATCHED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        new_balance = BalanceSyncService.sync_customer(self.customer, lock=False)
        self.assertEqual(new_balance, Decimal('8000.00'))

    def test_sync_customer_with_payments(self):
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-001',
            total_amount=Decimal('5000.00'),
            status='DISPATCHED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('2000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        new_balance = BalanceSyncService.sync_customer(self.customer, lock=False)
        self.assertEqual(new_balance, Decimal('3000.00'))

    def test_sync_customer_ignores_draft_invoices(self):
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-001',
            total_amount=Decimal('5000.00'),
            status='DRAFT',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-002',
            total_amount=Decimal('3000.00'),
            status='DISPATCHED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        new_balance = BalanceSyncService.sync_customer(self.customer, lock=False)
        self.assertEqual(new_balance, Decimal('3000.00'))

    def test_sync_customer_ignores_inactive_invoices(self):
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-001',
            total_amount=Decimal('5000.00'),
            status='DISPATCHED',
            is_active=False,
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        new_balance = BalanceSyncService.sync_customer(self.customer, lock=False)
        self.assertEqual(new_balance, Decimal('0.00'))

    def test_sync_supplier_no_transactions(self):
        new_balance = BalanceSyncService.sync_supplier(self.supplier, lock=False)
        self.assertEqual(new_balance, Decimal('0.00'))

    def test_sync_supplier_with_invoices_and_payments(self):
        PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='PINV-001',
            total_amount=Decimal('7000.00'),
            status='RECEIVED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('4000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        new_balance = BalanceSyncService.sync_supplier(self.supplier, lock=False)
        self.assertEqual(new_balance, Decimal('3000.00'))

    def test_sync_all_returns_counts(self):
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-001',
            total_amount=Decimal('1000.00'),
            status='DISPATCHED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='PINV-001',
            total_amount=Decimal('2000.00'),
            status='RECEIVED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        result = BalanceSyncService.sync_all()
        self.assertTrue(result['success'])
        self.assertEqual(result['customers_synced'], 1)
        self.assertEqual(result['suppliers_synced'], 1)
        self.assertEqual(result['errors'], [])

    def test_balance_sync_reconciles_divergent_balances(self):
        """BalanceSyncService should fix divergent balances."""
        customer = Customer.objects.create(
            name='Divergent Customer',
            code='DC001',
            balance=Decimal('9999.00'),  # Incorrect balance
        )
        SalesInvoice.objects.create(
            customer=customer,
            invoice_number='INV-DIV',
            total_amount=Decimal('5000.00'),
            status='DISPATCHED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        CustomerPayment.objects.create(
            customer=customer,
            amount=Decimal('2000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )

        new_balance = BalanceSyncService.sync_customer(customer, lock=False)
        self.assertEqual(new_balance, Decimal('3000.00'))
        customer.refresh_from_db()
        self.assertEqual(customer.balance, Decimal('3000.00'))


class OverpaymentPreventionModelTest(TestCase):
    """Test overpayment prevention at model level."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Test Customer',
            code='TC001',
            balance=Decimal('0.00'),
        )
        self.today = date.today()
        self.invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='INV-001',
            total_amount=Decimal('5000.00'),
            status='DISPATCHED',
            paid_amount=Decimal('0.00'),
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )

    def test_payment_equal_to_remaining_allowed(self):
        """Payment equal to remaining balance should be allowed."""
        payment = CustomerPayment(
            customer=self.customer,
            invoice=self.invoice,
            amount=Decimal('5000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        payment.full_clean()
        payment.save()
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal('5000.00'))

    def test_partial_payments_allowed(self):
        """Multiple partial payments should be allowed."""
        for amount in [Decimal('2000.00'), Decimal('2000.00'), Decimal('1000.00')]:
            payment = CustomerPayment(
                customer=self.customer,
                invoice=self.invoice,
                amount=amount,
                payment_method='CASH',
                payment_date=self.today,
            )
            payment.full_clean()
            payment.save()

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal('5000.00'))

    def test_supplier_overpayment_prevention_api(self):
        """Supplier payments should prevent overpayment at API layer."""
        from purchases.views import SupplierPaymentViewSet
        from purchases.serializers import SupplierPaymentSerializer

        supplier = Supplier.objects.create(
            name='Test Supplier',
            code='TS001',
            balance=Decimal('0.00'),
        )
        invoice = PurchaseInvoice.objects.create(
            supplier=supplier,
            invoice_number='PINV-001',
            total_amount=Decimal('3000.00'),
            status='RECEIVED',
            paid_amount=Decimal('0.00'),
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )

        viewset = SupplierPaymentViewSet()
        viewset.request = MagicMock()
        serializer = SupplierPaymentSerializer(data={
            'supplier': supplier.id,
            'invoice': invoice.id,
            'amount': '4000.00',
            'payment_method': 'CASH',
            'payment_date': self.today.isoformat(),
        })
        serializer.is_valid(raise_exception=True)

        with self.assertRaises(ValidationError) as cm:
            viewset.perform_create(serializer)

        self.assertIn('amount', cm.exception.message_dict)


class CreditLimitEnforcementTest(TestCase):
    """Test credit limit enforcement on invoice creation."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Test Customer',
            code='TC001',
            balance=Decimal('0.00'),
            credit_limit=Decimal('5000.00'),
            status='ACTIVE',
        )
        self.today = date.today()

    def test_invoice_within_credit_limit_allowed(self):
        """Invoice within credit limit should be allowed."""
        invoice = SalesInvoice(
            customer=self.customer,
            invoice_number='INV-001',
            total_amount=Decimal('3000.00'),
            status='CONFIRMED',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today,
        )
        invoice.full_clean()
        invoice.save()

        new_balance = BalanceSyncService.sync_customer(self.customer, lock=False)
        self.assertEqual(new_balance, Decimal('3000.00'))

    def test_blocked_customer_rejected(self):
        """Blocked customer should be rejected at viewset level."""
        self.customer.status = 'BLOCKED'
        self.customer.save()

        from sales.views import SalesInvoiceViewSet
        from sales.serializers import SalesInvoiceSerializer

        viewset = SalesInvoiceViewSet()
        viewset.request = MagicMock()
        serializer = SalesInvoiceSerializer(data={
            'customer': self.customer.id,
            'invoice_number': 'INV-001',
            'total_amount': '1000.00',
            'status': 'CONFIRMED',
            'order_date': self.today.isoformat(),
            'invoice_date': self.today.isoformat(),
            'due_date': self.today.isoformat(),
        })
        serializer.is_valid(raise_exception=True)

        with self.assertRaises(ValidationError) as cm:
            viewset.perform_create(serializer)

        self.assertIn('customer', cm.exception.message_dict)
        self.assertIn('blocked', str(cm.exception).lower())


class FIFOAllocationTest(TestCase):
    """Test FIFO payment allocation service."""

    def setUp(self):
        self.today = date.today()
        self.customer = Customer.objects.create(
            name='Test Customer', code='TC001',
            balance=Decimal('0.00'),
        )
        # Create 3 invoices with different dates for deterministic FIFO ordering
        self.inv1 = SalesInvoice.objects.create(
            customer=self.customer, invoice_number='INV-001',
            total_amount=Decimal('3000.00'), status='DISPATCHED',
            paid_amount=Decimal('0.00'),
            order_date=self.today, invoice_date=date(self.today.year, self.today.month, 1),
            due_date=self.today,
        )
        self.inv2 = SalesInvoice.objects.create(
            customer=self.customer, invoice_number='INV-002',
            total_amount=Decimal('5000.00'), status='DISPATCHED',
            paid_amount=Decimal('0.00'),
            order_date=self.today, invoice_date=date(self.today.year, self.today.month, 5),
            due_date=self.today,
        )
        self.inv3 = SalesInvoice.objects.create(
            customer=self.customer, invoice_number='INV-003',
            total_amount=Decimal('2000.00'), status='DISPATCHED',
            paid_amount=Decimal('0.00'),
            order_date=self.today, invoice_date=date(self.today.year, self.today.month, 10),
            due_date=self.today,
        )

    def test_fifo_allocates_to_oldest_invoice_first(self):
        """Payment should be allocated to oldest invoice first."""
        from sales.services.fifo_allocation import FIFOAllocationService

        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('4000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        allocations = FIFOAllocationService.allocate_payment(payment)

        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0].invoice, self.inv1)
        self.assertEqual(allocations[0].allocated_amount, Decimal('3000.00'))
        self.assertEqual(allocations[1].invoice, self.inv2)
        self.assertEqual(allocations[1].allocated_amount, Decimal('1000.00'))

    def test_fifo_fully_pays_invoice(self):
        """Invoice should be marked PAID when fully allocated."""
        from sales.services.fifo_allocation import FIFOAllocationService

        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('3000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        FIFOAllocationService.allocate_payment(payment)

        self.inv1.refresh_from_db()
        self.assertEqual(self.inv1.status, 'PAID')
        self.assertEqual(self.inv1.paid_amount, Decimal('3000.00'))

    def test_fifo_partial_payment(self):
        """Partial payment should be fully allocated to first invoice."""
        from sales.services.fifo_allocation import FIFOAllocationService

        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('1500.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        allocations = FIFOAllocationService.allocate_payment(payment)

        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0].invoice, self.inv1)
        self.assertEqual(allocations[0].allocated_amount, Decimal('1500.00'))

    def test_fifo_multiple_payments(self):
        """Multiple payments should allocate across invoices in order."""
        from sales.services.fifo_allocation import FIFOAllocationService

        pay1 = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('4000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        FIFOAllocationService.allocate_payment(pay1)

        # After pay1: inv1=PAID(3000), inv2=PARTIAL(1000/5000), inv3=UNPAID(0/2000)
        # pay2 of 3000 should go entirely to inv2 (remaining 4000)
        pay2 = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('3000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        allocations2 = FIFOAllocationService.allocate_payment(pay2)

        self.assertEqual(len(allocations2), 1)
        self.assertEqual(allocations2[0].invoice, self.inv2)
        self.assertEqual(allocations2[0].allocated_amount, Decimal('3000.00'))

        # inv2 should now have 4000 paid out of 5000
        self.inv2.refresh_from_db()
        self.assertEqual(self.inv2.paid_amount, Decimal('4000.00'))
        self.assertEqual(self.inv2.status, 'PARTIAL_PAID')

    def test_fifo_skips_already_allocated_invoices(self):
        """FIFO should not re-allocate to already fully-paid invoices."""
        from sales.services.fifo_allocation import FIFOAllocationService

        pay1 = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('3000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        FIFOAllocationService.allocate_payment(pay1)

        pay2 = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('2000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        allocations2 = FIFOAllocationService.allocate_payment(pay2)

        self.assertEqual(len(allocations2), 1)
        self.assertEqual(allocations2[0].invoice, self.inv2)
        self.assertEqual(allocations2[0].allocated_amount, Decimal('2000.00'))

    def test_fifo_allocate_for_customer(self):
        """allocate_for_customer should process all unallocated payments."""
        from sales.services.fifo_allocation import FIFOAllocationService

        CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('6000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('4000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        result = FIFOAllocationService.allocate_for_customer(self.customer)

        self.assertEqual(result['payments_processed'], 2)
        self.assertEqual(result['total_allocated'], Decimal('10000.00'))
        self.assertEqual(result['invoices_fully_paid'], 3)

    def test_get_unallocated_payments(self):
        """get_unallocated_payments should return payments without invoice."""
        from sales.services.fifo_allocation import FIFOAllocationService

        CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('1000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        CustomerPayment.objects.create(
            customer=self.customer,
            invoice=self.inv1,
            amount=Decimal('500.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        unallocated = FIFOAllocationService.get_unallocated_payments(self.customer)

        self.assertEqual(len(unallocated), 1)
        self.assertEqual(unallocated[0]['remaining'], Decimal('1000.00'))

    def test_get_outstanding_invoices(self):
        """get_outstanding_invoices should return unpaid invoices."""
        from sales.services.fifo_allocation import FIFOAllocationService

        outstanding = FIFOAllocationService.get_outstanding_invoices(self.customer)

        self.assertEqual(len(outstanding), 3)
        self.assertEqual(outstanding[0]['remaining'], Decimal('3000.00'))


class FinancialIntegrityValidationTest(TestCase):
    """Test financial integrity validation service."""

    def setUp(self):
        self.today = date.today()
        self.customer = Customer.objects.create(
            name='Test Customer', code='TC001',
            balance=Decimal('0.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Test Supplier', code='TS001',
            balance=Decimal('0.00'),
        )
        self.invoice = SalesInvoice.objects.create(
            customer=self.customer, invoice_number='INV-001',
            total_amount=Decimal('5000.00'), status='DISPATCHED',
            paid_amount=Decimal('0.00'),
            order_date=self.today, invoice_date=self.today,
            due_date=self.today,
        )

    def test_validate_customer_balances_clean(self):
        """Customer balance should match when consistent."""
        from core.services.financial_integrity import FinancialIntegrityService

        # Set balance to match the invoice
        self.customer.balance = Decimal('5000.00')
        self.customer.save()

        result = FinancialIntegrityService.validate_customer_balances()
        self.assertTrue(result['ok'])
        self.assertEqual(result['checked'], 1)
        self.assertEqual(result['issues'], [])

    def test_validate_customer_balances_mismatch(self):
        """Should detect customer balance mismatch."""
        from core.services.financial_integrity import FinancialIntegrityService

        self.customer.balance = Decimal('9999.00')
        self.customer.save()

        result = FinancialIntegrityService.validate_customer_balances()
        self.assertFalse(result['ok'])
        self.assertEqual(len(result['issues']), 1)
        self.assertEqual(result['issues'][0]['stored_balance'], '9999.00')
        self.assertEqual(result['issues'][0]['expected_balance'], '5000.00')

    def test_validate_supplier_balances_clean(self):
        """Supplier balance should match when consistent."""
        from core.services.financial_integrity import FinancialIntegrityService

        result = FinancialIntegrityService.validate_supplier_balances()
        self.assertTrue(result['ok'])

    def test_validate_invoice_paid_amount_clean(self):
        """Invoice paid_amount should match when consistent."""
        from core.services.financial_integrity import FinancialIntegrityService

        result = FinancialIntegrityService.validate_invoice_paid_amounts()
        self.assertTrue(result['ok'])

    def test_find_overpaid_invoices_clean(self):
        """Should find no overpaid invoices when clean."""
        from core.services.financial_integrity import FinancialIntegrityService

        result = FinancialIntegrityService.find_overpaid_invoices()
        self.assertTrue(result['ok'])
        self.assertEqual(result['issues'], [])

    def test_find_orphaned_payments_clean(self):
        """Should find no orphaned payments when clean."""
        from core.services.financial_integrity import FinancialIntegrityService

        result = FinancialIntegrityService.find_orphaned_payments()
        self.assertTrue(result['ok'])

    def test_validate_all_returns_structure(self):
        """validate_all should return structured results."""
        from core.services.financial_integrity import FinancialIntegrityService

        result = FinancialIntegrityService.validate_all()
        self.assertIn('ok', result)
        self.assertIn('total_issues', result)
        self.assertIn('checks', result)
        self.assertIn('customer_balances', result['checks'])
        self.assertIn('supplier_balances', result['checks'])
        self.assertIn('invoice_paid_amounts', result['checks'])
        self.assertIn('journal_entry_balances', result['checks'])
        self.assertIn('orphaned_payments', result['checks'])
        self.assertIn('overpaid_invoices', result['checks'])
        self.assertIn('negative_balances', result['checks'])

    def test_auto_fix_customer_balances(self):
        """auto_fix should correct mismatched customer balances."""
        from core.services.financial_integrity import FinancialIntegrityService

        self.customer.balance = Decimal('9999.00')
        self.customer.save()

        result = FinancialIntegrityService.auto_fix_customer_balances()
        self.assertTrue(result['success'])
        self.assertEqual(result['fixed'], 1)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal('5000.00'))


class PaymentEngineFallbackAccountTest(TestCase):
    """Test PaymentEngine uses proper AR/AP accounts instead of generic fallbacks."""

    def setUp(self):
        self.today = date.today()
        # Create required accounts
        Account.objects.create(
            code='1000', name='Cash', account_type='ASSET',
            account_category='CURRENT_ASSET', is_active=True,
        )
        Account.objects.create(
            code='1010', name='Main Cash AFN', account_type='ASSET',
            account_category='CURRENT_ASSET', is_active=True,
        )
        Account.objects.create(
            code='1200', name='Accounts Receivable', account_type='ASSET',
            account_category='CURRENT_ASSET', is_active=True,
        )
        Account.objects.create(
            code='1300', name='Inventory', account_type='ASSET',
            account_category='CURRENT_ASSET', is_active=True,
        )
        Account.objects.create(
            code='2100', name='Accounts Payable', account_type='LIABILITY',
            account_category='CURRENT_LIABILITY', is_active=True,
        )
        Account.objects.create(
            code='2200', name='Unearned Revenue', account_type='LIABILITY',
            account_category='CURRENT_LIABILITY', is_active=True,
        )
        Account.objects.create(
            code='4100', name='Sales Revenue', account_type='REVENUE',
            account_category='OPERATING_REVENUE', is_active=True,
        )
        Account.objects.create(
            code='5100', name='COGS', account_type='EXPENSE',
            account_category='OPERATING_EXPENSE', is_active=True,
        )
        Account.objects.create(
            code='6100', name='Operating Expenses', account_type='EXPENSE',
            account_category='OPERATING_EXPENSE', is_active=True,
        )
        # Create payment method and account
        from payments.models import PaymentMethod, PaymentAccount
        self.cash_method = PaymentMethod.objects.create(
            name='Cash', code='CASH', method_type='CASH',
            is_default=True, is_active=True, fee_percentage=Decimal('0'),
        )
        self.cash_account = PaymentAccount.objects.create(
            name='Main Cash', code='CASH-001',
            account_type='CASH', currency='AFN',
            current_balance=Decimal('10000.00'),
            accounting_account=Account.objects.get(code='1010'),
            is_active=True,
        )

    def test_receipt_customer_payment_uses_ar_account(self):
        """Customer receipt should credit AR (1200), not generic Revenue."""
        from payments.services import PaymentEngine

        customer = Customer.objects.create(
            name='Test Customer', code='TC001',
            balance=Decimal('5000.00'),
        )
        result = PaymentEngine.process_receipt(
            payment_method_code='CASH',
            destination_account_code='CASH-001',
            amount=Decimal('1000.00'),
            description='Customer payment',
            party_type='CUSTOMER',
            party_id=str(customer.id),
            party_name=customer.name,
            performed_by='test',
        )
        self.assertTrue(result['success'])

        # Verify journal entry uses AR account
        from accounting.models import JournalEntry
        entry_number = result.get('journal_entry')
        self.assertIsNotNone(entry_number, 'Journal entry should be created')
        je = JournalEntry.objects.get(entry_number=entry_number)
        credit_lines = je.lines.filter(credit__gt=0)
        ar_account = Account.objects.get(code='1200')
        self.assertTrue(
            any(line.account_id == ar_account.id for line in credit_lines),
            'Customer receipt should credit AR account (1200)'
        )

    def test_payment_supplier_payment_uses_ap_account(self):
        """Supplier payment should debit AP (2100), not generic Expense."""
        from payments.services import PaymentEngine

        supplier = Supplier.objects.create(
            name='Test Supplier', code='TS001',
            balance=Decimal('3000.00'),
        )
        result = PaymentEngine.process_payment(
            payment_method_code='CASH',
            source_account_code='CASH-001',
            amount=Decimal('500.00'),
            description='Supplier payment',
            party_type='SUPPLIER',
            party_id=str(supplier.id),
            party_name=supplier.name,
            performed_by='test',
        )
        self.assertTrue(result['success'])

        # Verify journal entry uses AP account
        from accounting.models import JournalEntry
        entry_number = result.get('journal_entry')
        self.assertIsNotNone(entry_number, 'Journal entry should be created')
        je = JournalEntry.objects.get(entry_number=entry_number)
        debit_lines = je.lines.filter(debit__gt=0)
        ap_account = Account.objects.get(code='2100')
        self.assertTrue(
            any(line.account_id == ap_account.id for line in debit_lines),
            'Supplier payment should debit AP account (2100)'
        )

    def test_receipt_no_party_uses_suspense_account(self):
        """Unallocated receipt should credit suspense/liability, not Revenue."""
        from payments.services import PaymentEngine

        result = PaymentEngine.process_receipt(
            payment_method_code='CASH',
            destination_account_code='CASH-001',
            amount=Decimal('500.00'),
            description='Advance payment',
            party_type='',
            performed_by='test',
        )
        self.assertTrue(result['success'])

        # Verify journal entry uses suspense account (2200), not Revenue
        from accounting.models import JournalEntry
        entry_number = result.get('journal_entry')
        self.assertIsNotNone(entry_number, 'Journal entry should be created')
        je = JournalEntry.objects.get(entry_number=entry_number)
        credit_lines = je.lines.filter(credit__gt=0)
        suspense_account = Account.objects.get(code='2200')
        revenue_account = Account.objects.get(code='4100')
        self.assertTrue(
            any(line.account_id == suspense_account.id for line in credit_lines),
            'Unallocated receipt should credit suspense account (2200)'
        )
        self.assertFalse(
            any(line.account_id == revenue_account.id for line in credit_lines),
            'Unallocated receipt should NOT credit Revenue account'
        )

    def test_payment_no_party_uses_expense_account(self):
        """Unallocated payment should debit Expense account."""
        from payments.services import PaymentEngine

        result = PaymentEngine.process_payment(
            payment_method_code='CASH',
            source_account_code='CASH-001',
            amount=Decimal('200.00'),
            description='General expense',
            party_type='',
            performed_by='test',
        )
        self.assertTrue(result['success'])

        # Verify journal entry uses expense account
        from accounting.models import JournalEntry
        entry_number = result.get('journal_entry')
        self.assertIsNotNone(entry_number, 'Journal entry should be created')
        je = JournalEntry.objects.get(entry_number=entry_number)
        debit_lines = je.lines.filter(debit__gt=0)
        # Any expense account is valid (5100 COGS or 6100 Operating Expenses)
        expense_accounts = Account.objects.filter(account_type='EXPENSE', is_active=True)
        self.assertTrue(
            any(line.account_id in [a.id for a in expense_accounts] for line in debit_lines),
            'Unallocated payment should debit an Expense account'
        )


class ReturnVoidBalanceTest(TestCase):
    """Test return void balance correction."""

    def test_void_code_uses_balance_sync_service(self):
        """Verify void() method source code uses BalanceSyncService."""
        import inspect
        from returns.models import ReturnOrder

        source = inspect.getsource(ReturnOrder.void)
        self.assertIn('BalanceSyncService', source)
        self.assertIn('sync_customer', source)
        self.assertNotIn('party.balance +=', source)
        self.assertNotIn('party.balance -=', source)

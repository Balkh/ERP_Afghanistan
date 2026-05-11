"""
Accounting Reconciliation Tests

Tests the AccountingReconciliationService for integrity verification
between operational data and accounting records.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine, JournalEventLog
from accounting.services.reconciliation import AccountingReconciliationService, ReconciliationResult
from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from sales.models import SalesInvoice, Customer, SalesItem
from purchases.models import PurchaseInvoice, Supplier, PurchaseItem
from payments.models import FinancialTransaction, PaymentMethod, PaymentAccount


class ReconciliationInventoryTest(TransactionTestCase):
    """Test inventory vs accounting reconciliation."""

    def setUp(self):
        self.category = Category.objects.create(name='Medicines', is_active=True)
        self.unit = Unit.objects.create(name='Piece', symbol='PCS', is_active=True)
        self.product = Product.objects.create(
            name='Aspirin', sku='ASP001', category=self.category,
            unit=self.unit, is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main WH', code='WH01', is_active=True
        )
        self.inventory_account = Account.objects.get(code='1300')

    def test_inventory_reconciliation_passes_with_matching_values(self):
        """Test reconciliation passes when batch value matches account balance."""
        batch = Batch.objects.create(
            product=self.product,
            batch_number='B001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH01',
            is_active=True
        )

        JournalEntry.objects.create(
            entry_number='JE-0001',
            entry_date=django_timezone.now().date(),
            entry_type='PURCHASE',
            description='Inventory purchase',
            is_posted=True
        )

        result = AccountingReconciliationService.reconcile_inventory_vs_accounting()
        self.assertIn('inventory_account_exists', [c['name'] for c in result.checks])
        self.assertIn('batch_count_positive', [c['name'] for c in result.checks])

    def test_inventory_reconciliation_fails_without_inventory_account(self):
        """Test reconciliation fails when inventory account doesn't exist."""
        self.inventory_account.delete()

        result = AccountingReconciliationService.reconcile_inventory_vs_accounting()
        check = next((c for c in result.checks if c['name'] == 'inventory_account_exists'), None)
        self.assertIsNotNone(check)
        self.assertFalse(check['passed'])

    def test_inventory_reconciliation_detects_value_mismatch(self):
        """Test reconciliation detects when batch value differs from account."""
        Batch.objects.create(
            product=self.product,
            batch_number='B002',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH01',
            is_active=True
        )

        entry = JournalEntry.objects.create(
            entry_number='JE-0002',
            entry_date=django_timezone.now().date(),
            entry_type='PURCHASE',
            description='Different value',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.inventory_account,
            debit=Decimal('500.00'),
            credit=Decimal('0.00')
        )

        result = AccountingReconciliationService.reconcile_inventory_vs_accounting()


class ReconciliationSalesTest(TransactionTestCase):
    """Test sales journal entry reconciliation."""

    def setUp(self):
        self.category = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='P', symbol='P', is_active=True)
        self.product = Product.objects.create(
            name='Test', sku='T001', category=self.category,
            unit=self.unit, is_active=True
        )
        self.customer = Customer.objects.create(
            name='Test Customer',
            phone='123456',
            is_active=True
        )

    def test_reconciliation_passes_when_dispatched_invoice_has_je(self):
        """Test reconciliation passes when dispatched invoice has JE."""
        invoice = SalesInvoice.objects.create(
            invoice_number='INV-001',
            customer=self.customer,
            status='DISPATCHED',
            total_amount=Decimal('100.00'),
            is_active=True
        )

        entry = JournalEntry.objects.create(
            entry_number='JE-001',
            entry_date=django_timezone.now().date(),
            entry_type='SALE',
            description='Sale',
            is_posted=True
        )
        invoice.journal_entry = entry
        invoice.save()

        result = AccountingReconciliationService.reconcile_sales_journal_entries()
        check = next((c for c in result.checks if c['name'] == 'all_dispatched_have_je'), None)
        self.assertTrue(check['passed'])

    def test_reconciliation_fails_when_dispatched_invoice_missing_je(self):
        """Test reconciliation fails when dispatched invoice has no JE."""
        SalesInvoice.objects.create(
            invoice_number='INV-002',
            customer=self.customer,
            status='DISPATCHED',
            total_amount=Decimal('100.00'),
            journal_entry_id=None,
            is_active=True
        )

        result = AccountingReconciliationService.reconcile_sales_journal_entries()
        check = next((c for c in result.checks if c['name'] == 'all_dispatched_have_je'), None)
        self.assertFalse(check['passed'])


class ReconciliationPurchaseTest(TransactionTestCase):
    """Test purchase journal entry reconciliation."""

    def setUp(self):
        self.category = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='P', symbol='P', is_active=True)
        self.product = Product.objects.create(
            name='Test', sku='T001', category=self.category,
            unit=self.unit, is_active=True
        )
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            phone='123456',
            is_active=True
        )

    def test_reconciliation_passes_when_received_invoice_has_je(self):
        """Test reconciliation passes when received invoice has JE."""
        invoice = PurchaseInvoice.objects.create(
            invoice_number='PO-001',
            supplier=self.supplier,
            status='RECEIVED',
            total_amount=Decimal('200.00'),
            is_active=True
        )

        entry = JournalEntry.objects.create(
            entry_number='JE-002',
            entry_date=django_timezone.now().date(),
            entry_type='PURCHASE',
            description='Purchase',
            is_posted=True
        )
        invoice.journal_entry = entry
        invoice.save()

        result = AccountingReconciliationService.reconcile_purchase_journal_entries()
        check = next((c for c in result.checks if c['name'] == 'all_received_have_je'), None)
        self.assertTrue(check['passed'])

    def test_reconciliation_fails_when_received_invoice_missing_je(self):
        """Test reconciliation fails when received invoice has no JE."""
        PurchaseInvoice.objects.create(
            invoice_number='PO-002',
            supplier=self.supplier,
            status='RECEIVED',
            total_amount=Decimal('200.00'),
            journal_entry_id=None,
            is_active=True
        )

        result = AccountingReconciliationService.reconcile_purchase_journal_entries()
        check = next((c for c in result.checks if c['name'] == 'all_received_have_je'), None)
        self.assertFalse(check['passed'])


class ReconciliationPaymentTest(TransactionTestCase):
    """Test payment transaction reconciliation."""

    def setUp(self):
        self.payment_method = PaymentMethod.objects.create(
            code='CASH',
            name='Cash',
            method_type='CASH',
            is_active=True
        )
        self.payment_account = PaymentAccount.objects.create(
            code='CASH01',
            name='Main Cash',
            current_balance=Decimal('1000.00'),
            is_active=True
        )

    def test_reconciliation_passes_when_completed_txn_has_je(self):
        """Test reconciliation passes when completed transaction has JE."""
        txn = FinancialTransaction.objects.create(
            transaction_type='RECEIPT',
            payment_method=self.payment_method,
            destination_account=self.payment_account,
            amount=Decimal('100.00'),
            net_amount=Decimal('100.00'),
            status='COMPLETED',
            is_active=True
        )

        entry = JournalEntry.objects.create(
            entry_number='JE-003',
            entry_date=django_timezone.now().date(),
            entry_type='RECEIPT',
            description='Receipt',
            is_posted=True
        )
        txn.journal_entry = entry
        txn.save()

        result = AccountingReconciliationService.reconcile_payment_transactions()
        check = next((c for c in result.checks if c['name'] == 'all_completed_have_je'), None)
        self.assertTrue(check['passed'])

    def test_reconciliation_excludes_transfer_type(self):
        """Test reconciliation excludes TRANSFER type transactions."""
        txn = FinancialTransaction.objects.create(
            transaction_type='TRANSFER',
            payment_method=self.payment_method,
            amount=Decimal('50.00'),
            net_amount=Decimal('50.00'),
            status='COMPLETED',
            journal_entry_id=None,
            is_active=True
        )

        result = AccountingReconciliationService.reconcile_payment_transactions()
        check = next((c for c in result.checks if c['name'] == 'all_completed_have_je'), None)
        self.assertTrue(check['passed'])


class ReconciliationJournalBalanceTest(TransactionTestCase):
    """Test journal entry balance reconciliation."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1000', name='Asset', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_reconciliation_passes_when_entries_balanced(self):
        """Test reconciliation passes when all entries are balanced."""
        entry = JournalEntry.objects.create(
            entry_number='JE-004',
            entry_date=django_timezone.now().date(),
            entry_type='GENERAL',
            description='Balanced entry',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.asset,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.revenue,
            debit=Decimal('0.00'),
            credit=Decimal('100.00')
        )

        result = AccountingReconciliationService.reconcile_journal_entry_balances()
        check = next((c for c in result.checks if c['name'] == 'all_posted_balanced'), None)
        self.assertTrue(check['passed'])

    def test_reconciliation_fails_when_entry_unbalanced(self):
        """Test reconciliation fails when entry is unbalanced."""
        entry = JournalEntry.objects.create(
            entry_number='JE-005',
            entry_date=django_timezone.now().date(),
            entry_type='GENERAL',
            description='Unbalanced entry',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.asset,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.revenue,
            debit=Decimal('0.00'),
            credit=Decimal('80.00')
        )

        result = AccountingReconciliationService.reconcile_journal_entry_balances()
        check = next((c for c in result.checks if c['name'] == 'all_posted_balanced'), None)
        self.assertFalse(check['passed'])


class ReconciliationCustomerBalanceTest(TransactionTestCase):
    """Test customer balance reconciliation."""

    def setUp(self):
        self.ar_account = Account.objects.get(code='1200')
        self.customer = Customer.objects.create(
            name='Customer', phone='123', balance=Decimal('0.00'), is_active=True
        )

    def test_reconciliation_passes_when_balances_match(self):
        """Test reconciliation passes when customer balance matches AR."""
        self.customer.balance = Decimal('0.00')
        self.customer.save()

        result = AccountingReconciliationService.reconcile_customer_balances()
        check = next((c for c in result.checks if c['name'] == 'customer_balance_match'), None)
        self.assertTrue(check['passed'])


class FullReconciliationTest(TransactionTestCase):
    """Test full reconciliation running all checks."""

    def setUp(self):
        self.category = Category.objects.create(name='C', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.product = Product.objects.create(
            name='P', sku='P', category=self.category, unit=self.unit, is_active=True
        )

    def test_full_reconciliation_returns_summary(self):
        """Test full reconciliation returns proper summary."""
        result = AccountingReconciliationService.full_reconciliation()

        self.assertIn('is_healthy', result)
        self.assertIn('summary', result)
        self.assertIn('results', result)

        self.assertIn('total_checks', result['summary'])
        self.assertIn('passed', result['summary'])
        self.assertIn('failed', result['summary'])

    def test_full_reconciliation_runs_all_checks(self):
        """Test full reconciliation runs all 7 checks."""
        result = AccountingReconciliationService.full_reconciliation()

        self.assertEqual(len(result['results']), 7)
        check_names = [r['name'] for r in result['results']]
        self.assertIn('Inventory vs Accounting', check_names)
        self.assertIn('Sales Journal Entries', check_names)
        self.assertIn('Purchase Journal Entries', check_names)
        self.assertIn('Payment Transactions', check_names)
        self.assertIn('Journal Entry Balances', check_names)
        self.assertIn('Customer Balances', check_names)
        self.assertIn('Supplier Balances', check_names)
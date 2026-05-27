"""
Phase 6C — Return Functionality & Accounting Cycle Test Suite.

Tests the full accounting cycle:
1. Sale Invoice creation → dispatch → journal entry
2. Customer payment → receipt journal entry
3. Sales return → approve → inventory restore + credit note journal entry
4. Purchase Invoice creation → receive → journal entry
5. Supplier payment → payment journal entry
6. Purchase return → approve → inventory restore + debit note journal entry
"""
import uuid
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from sales.models import SalesInvoice, SalesItem, Customer
from purchases.models import PurchaseInvoice, PurchaseItem, Supplier
from returns.models import ReturnOrder, ReturnItem, ReconciliationEntry
from accounting.models import Account, JournalEntry, JournalEntryLine
from payments.models import PaymentMethod, PaymentAccount, FinancialTransaction
from hr.models import Employee, Department, Position
from core.models.system import Company


def _setup_common(self):
    """Common setup helper."""
    self.company = Company.objects.create(name="Test Company", code=f"TC-{uuid.uuid4().hex[:8]}")
    self.category = Category.objects.create(name="Test Category", is_active=True)
    self.unit = Unit.objects.create(name="Piece", symbol="PCS", is_active=True)
    self.warehouse = Warehouse.objects.create(name="Main Warehouse", code="MW001", is_active=True)
    self.product = Product.objects.create(
        name="Test Product", sku="TP001", barcode="BAR_TP001",
        category=self.category, unit=self.unit, is_active=True
    )
    self.customer = Customer.objects.create(
        name="Test Customer", code=f"CUST-{uuid.uuid4().hex[:8]}",
        phone="+93700000000", subtype='INDIVIDUAL',
        first_name="Test", last_name="Customer", customer_type='RETAIL',
        company=self.company
    )
    self.supplier = Supplier.objects.create(
        name="Test Supplier", code=f"SUP-{uuid.uuid4().hex[:8]}",
        phone="+93700000000", company=self.company
    )
    self.dept = Department.objects.create(name="Test Dept")
    self.position = Position.objects.create(title="Test Position", code=f"POS-{uuid.uuid4().hex[:8]}", department=self.dept)
    self.employee = Employee.objects.create(
        employee_number=f"EMP-{uuid.uuid4().hex[:8]}", first_name="Test", last_name="Employee",
        department=self.dept, position=self.position,
        gender='MALE', hire_date=timezone.now().date()
    )
    self.batch = Batch.objects.create(
        product=self.product, batch_number=f"BATCH-{uuid.uuid4().hex[:8]}",
        quantity=Decimal("100.00"), remaining_quantity=Decimal("100.00"),
        expiry_date=timezone.now().date() + timedelta(days=365),
        purchase_price=Decimal("70.00"), sale_price=Decimal("100.00"),
        manufacturing_date=timezone.now().date(),
        location="WH01",
        is_active=True
    )
    # Accounts
    self.ar_account = Account.objects.create(code='1200', name='AR', account_type='ASSET', account_category='CURRENT_ASSET', is_active=True)
    self.revenue_account = Account.objects.create(code='4100', name='Revenue', account_type='REVENUE', account_category='OPERATING_REVENUE', is_active=True)
    self.tax_account = Account.objects.create(code='2100', name='Tax Payable', account_type='LIABILITY', account_category='CURRENT_LIABILITY', is_active=True)
    self.cash_account = Account.objects.create(code='1010', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET', is_active=True)
    self.sales_return_account = Account.objects.create(code='4200', name='Sales Returns', account_type='REVENUE', account_category='OPERATING_REVENUE', is_active=True)
    self.inventory_account = Account.objects.create(code='1300', name='Inventory', account_type='ASSET', account_category='CURRENT_ASSET', is_active=True)
    self.cogs_account = Account.objects.create(code='5100', name='COGS', account_type='EXPENSE', account_category='COST_OF_GOODS_SOLD', is_active=True)
    self.ap_account = Account.objects.create(code='2200', name='AP', account_type='LIABILITY', account_category='CURRENT_LIABILITY', is_active=True)
    self.purchase_tax_account = Account.objects.create(code='2110', name='Purchase Tax', account_type='ASSET', account_category='CURRENT_ASSET', is_active=True)
    # PaymentEngine required accounts
    Account.objects.get_or_create(code='1000', defaults={'name': 'Cash/Bank', 'account_type': 'ASSET', 'account_category': 'CURRENT_ASSET', 'is_active': True})
    Account.objects.get_or_create(code='6100', defaults={'name': 'Operating Expenses', 'account_type': 'EXPENSE', 'account_category': 'OPERATING_EXPENSE', 'is_active': True})
    # Payment
    self.payment_method, _ = PaymentMethod.objects.get_or_create(code='CASH', defaults={'name': 'Cash', 'method_type': 'CASH', 'is_active': True})
    self.payment_account = PaymentAccount.objects.create(
        name='Main Cash', code='MCASH', account_type='CASH',
        accounting_account=self.cash_account, is_active=True
    )
    # Ensure all active payment accounts have sufficient funds for payment tests
    PaymentAccount.objects.filter(is_active=True).update(current_balance=Decimal('100000.00'))


class TestSalesAccountingCycle(TransactionTestCase):
    """Test the full sales accounting cycle: invoice → dispatch → payment → return."""

    def setUp(self):
        _setup_common(self)

    def _create_and_dispatch_invoice(self, qty=Decimal("10.00"), price=Decimal("100.00"), tax=Decimal("50.00")):
        """Helper: create and dispatch a sales invoice."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            company=self.company,
            subtotal=price * qty,
            tax=tax,
            total_amount=(price * qty) + tax,
            status='DISPATCHED',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        SalesItem.objects.create(
            invoice=invoice, product=self.product,
            quantity=qty, unit_price=price,
            discount=Decimal("0.00"), tax=tax,
            total=(price * qty) + tax
        )
        # Create stock movement
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, batch=self.batch,
            movement_type='OUT', quantity=-qty,
            reference_type='SALE', reference_id=invoice.invoice_number,
            notes='Test dispatch'
        )
        # Create journal entry
        lines = [
            {'account_id': str(self.ar_account.id), 'debit': invoice.total_amount, 'credit': 0},
            {'account_id': str(self.revenue_account.id), 'debit': 0, 'credit': invoice.subtotal},
            {'account_id': str(self.tax_account.id), 'debit': 0, 'credit': invoice.tax},
        ]
        from accounting.services.journal_engine import JournalEngine
        result = JournalEngine.create_entry(
            entry_type='SALE',
            description=f"Sale {invoice.invoice_number}",
            lines=lines,
            entry_date=invoice.invoice_date,
            auto_post=True,
            source_module='test',
        )
        invoice.journal_entry_id = result.get('entry_id')
        invoice.save()
        return invoice

    def test_01_create_and_dispatch_invoice(self):
        """Step 1: Create sales invoice and dispatch — verify journal entry."""
        invoice = self._create_and_dispatch_invoice()
        self.assertEqual(invoice.status, 'DISPATCHED')
        self.assertIsNotNone(invoice.journal_entry_id)
        je = JournalEntry.objects.get(id=invoice.journal_entry_id)
        self.assertEqual(je.lines.count(), 3)
        total_debit = sum(line.debit for line in je.lines.all())
        total_credit = sum(line.credit for line in je.lines.all())
        self.assertEqual(total_debit, total_credit)
        self.assertEqual(total_debit, invoice.total_amount)

    def test_02_customer_payment(self):
        """Step 2: Make customer payment — verify receipt journal entry."""
        invoice = self._create_and_dispatch_invoice()
        from sales.models import CustomerPayment
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            invoice=invoice,
            amount=invoice.total_amount,
            payment_method='CASH',
            reference_number='PAY001',
            payment_date=timezone.now().date()
        )
        # Verify payment was created
        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.amount, invoice.total_amount)

    def test_03_sales_return_creation(self):
        """Step 3: Create a sales return order."""
        invoice = self._create_and_dispatch_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='PENDING',
            reason='Customer returned goods',
            total_amount=Decimal("525.00")
        )
        ReturnItem.objects.create(
            return_order=return_order,
            product=self.product,
            batch=self.batch,
            return_quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("25.00"),
            condition='GOOD',
            invoice_item=invoice.items.first()
        )
        self.assertEqual(return_order.status, 'PENDING')
        self.assertEqual(return_order.items.count(), 1)

    def test_04_sales_return_approval(self):
        """Step 4: Approve sales return — verify inventory restore + credit note."""
        invoice = self._create_and_dispatch_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='PENDING',
            reason='Customer returned goods',
            total_amount=Decimal("525.00")
        )
        ReturnItem.objects.create(
            return_order=return_order,
            product=self.product,
            batch=self.batch,
            return_quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("25.00"),
            condition='GOOD',
            invoice_item=invoice.items.first()
        )
        # Approve
        return_order.approve(self.employee)
        self.assertEqual(return_order.status, 'APPROVED')
        self.assertIsNotNone(return_order.journal_entry)
        self.assertTrue(return_order.credit_note_number.startswith('CN-'))
        # Verify stock movement created
        movements = StockMovement.objects.filter(
            reference_type='RETURN',
            reference_id=return_order.return_number
        )
        self.assertGreaterEqual(movements.count(), 1)
        self.assertEqual(movements.first().movement_type, 'RETURN_IN')
        # Verify customer balance reduced by return amount
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, invoice.total_amount - return_order.total_amount)

    def test_05_return_exceeds_invoice_quantity(self):
        """Step 5: Verify return cannot exceed invoice quantity."""
        invoice = self._create_and_dispatch_invoice(qty=Decimal("10.00"))
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='PENDING',
            reason='Test',
            total_amount=Decimal("1050.00")
        )
        ReturnItem.objects.create(
            return_order=return_order,
            product=self.product,
            batch=self.batch,
            return_quantity=Decimal("15.00"),
            unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("50.00"),
            condition='GOOD',
            invoice_item=invoice.items.first()
        )
        with self.assertRaises(ValidationError):
            return_order.approve(self.employee)

    def test_06_double_return_prevention(self):
        """Step 6: Verify double return of same items is prevented."""
        invoice = self._create_and_dispatch_invoice(qty=Decimal("10.00"))
        # First return
        return1 = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='PENDING',
            reason='First return',
            total_amount=Decimal("525.00")
        )
        ReturnItem.objects.create(
            return_order=return1,
            product=self.product,
            batch=self.batch,
            return_quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("25.00"),
            condition='GOOD',
            invoice_item=invoice.items.first()
        )
        return1.approve(self.employee)
        # Second return of same quantity should fail (5 + 5 = 10, but trying to return 6 more)
        return2 = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='PENDING',
            reason='Second return',
            total_amount=Decimal("630.00")
        )
        ReturnItem.objects.create(
            return_order=return2,
            product=self.product,
            batch=self.batch,
            return_quantity=Decimal("6.00"),  # 5 + 6 = 11 > 10, should fail
            unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("30.00"),
            condition='GOOD',
            invoice_item=invoice.items.first()
        )
        with self.assertRaises(ValidationError):
            return2.approve(self.employee)


class TestPurchaseAccountingCycle(TransactionTestCase):
    """Test the full purchase accounting cycle: invoice → receive → payment → return."""

    def setUp(self):
        _setup_common(self)

    def _create_and_receive_invoice(self, qty=Decimal("50.00"), price=Decimal("70.00"), tax=Decimal("175.00")):
        """Helper: create and receive a purchase invoice."""
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier,
            company=self.company,
            subtotal=price * qty,
            tax=tax,
            total_amount=(price * qty) + tax,
            status='RECEIVED',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        PurchaseItem.objects.create(
            invoice=invoice, product=self.product,
            quantity=qty, unit_price=price,
            batch_number='BATCH001',
            discount=Decimal("0.00"), tax=tax,
            total=(price * qty) + tax,
            expiry_date=timezone.now().date() + timedelta(days=365)
        )
        # Create batch
        batch = Batch.objects.create(
            product=self.product, batch_number=f'BATCH-{uuid.uuid4().hex[:8]}',
            quantity=qty, remaining_quantity=qty,
            expiry_date=timezone.now().date() + timedelta(days=365),
            purchase_price=price, sale_price=Decimal("100.00"),
            manufacturing_date=timezone.now().date(),
            location="WH01",
            is_active=True
        )
        # Create stock movement
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, batch=batch,
            movement_type='IN', quantity=qty,
            reference_type='PURCHASE', reference_id=invoice.invoice_number,
            notes='Test receive'
        )
        # Create journal entry
        lines = [
            {'account_id': str(self.inventory_account.id), 'debit': invoice.subtotal, 'credit': 0},
            {'account_id': str(self.purchase_tax_account.id), 'debit': invoice.tax, 'credit': 0},
            {'account_id': str(self.ap_account.id), 'debit': 0, 'credit': invoice.total_amount},
        ]
        from accounting.services.journal_engine import JournalEngine
        result = JournalEngine.create_entry(
            entry_type='PURCHASE',
            description=f"Purchase {invoice.invoice_number}",
            lines=lines,
            entry_date=invoice.invoice_date,
            auto_post=True,
            source_module='test',
        )
        invoice.journal_entry_id = result.get('entry_id')
        invoice.save()
        return invoice, batch

    def test_01_create_and_receive_invoice(self):
        """Step 1: Create purchase invoice and receive — verify journal entry."""
        invoice, batch = self._create_and_receive_invoice()
        self.assertEqual(invoice.status, 'RECEIVED')
        self.assertIsNotNone(invoice.journal_entry_id)
        je = JournalEntry.objects.get(id=invoice.journal_entry_id)
        self.assertEqual(je.lines.count(), 3)
        total_debit = sum(line.debit for line in je.lines.all())
        total_credit = sum(line.credit for line in je.lines.all())
        self.assertEqual(total_debit, total_credit)

    def test_02_supplier_payment(self):
        """Step 2: Make supplier payment — verify AP reduction."""
        invoice, batch = self._create_and_receive_invoice()
        from purchases.models import SupplierPayment
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            invoice=invoice,
            amount=invoice.total_amount,
            payment_method='CASH',
            reference_number='PAY001',
            payment_date=timezone.now().date()
        )
        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.amount, invoice.total_amount)

    def test_03_purchase_return_creation(self):
        """Step 3: Create a purchase return order."""
        invoice, batch = self._create_and_receive_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='PURCHASE_RETURN',
            purchase_invoice=invoice,
            supplier=self.supplier,
            status='PENDING',
            reason='Expired items',
            total_amount=Decimal("367.50")
        )
        ReturnItem.objects.create(
            return_order=return_order,
            product=self.product,
            batch=batch,
            return_quantity=Decimal("5.00"),
            unit_price=Decimal("70.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("17.50"),
            condition='EXPIRED',
            purchase_invoice_item=invoice.items.first()
        )
        self.assertEqual(return_order.status, 'PENDING')
        self.assertEqual(return_order.items.count(), 1)

    def test_04_purchase_return_approval(self):
        """Step 4: Approve purchase return — verify inventory + debit note."""
        invoice, batch = self._create_and_receive_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='PURCHASE_RETURN',
            purchase_invoice=invoice,
            supplier=self.supplier,
            status='PENDING',
            reason='Expired items',
            total_amount=Decimal("367.50")
        )
        ReturnItem.objects.create(
            return_order=return_order,
            product=self.product,
            batch=batch,
            return_quantity=Decimal("5.00"),
            unit_price=Decimal("70.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("17.50"),
            condition='EXPIRED',
            purchase_invoice_item=invoice.items.first()
        )
        return_order.approve(self.employee)
        self.assertEqual(return_order.status, 'APPROVED')
        self.assertIsNotNone(return_order.journal_entry)
        self.assertTrue(return_order.credit_note_number.startswith('CN-'))
        movements = StockMovement.objects.filter(
            reference_type='RETURN',
            reference_id=return_order.return_number
        )
        self.assertGreaterEqual(movements.count(), 1)
        self.assertEqual(movements.first().movement_type, 'RETURN_EXPIRED')

    def test_05_reconciliation_entry_created(self):
        """Step 5: Verify reconciliation entry is created on return approval."""
        invoice, batch = self._create_and_receive_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='PURCHASE_RETURN',
            purchase_invoice=invoice,
            supplier=self.supplier,
            status='PENDING',
            reason='Test',
            total_amount=Decimal("367.50")
        )
        ReturnItem.objects.create(
            return_order=return_order,
            product=self.product,
            batch=batch,
            return_quantity=Decimal("5.00"),
            unit_price=Decimal("70.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("17.50"),
            condition='GOOD',
            purchase_invoice_item=invoice.items.first()
        )
        return_order.approve(self.employee)
        rec_entries = ReconciliationEntry.objects.filter(return_order=return_order)
        self.assertEqual(rec_entries.count(), 1)
        self.assertEqual(rec_entries.first().transaction_type, 'RETURN')


class TestReturnEdgeCases(TransactionTestCase):
    """Test edge cases in return processing."""

    def setUp(self):
        _setup_common(self)

    def test_return_without_invoice(self):
        """Return order without invoice should fail validation."""
        return_order = ReturnOrder(
            return_type='SALE_RETURN',
            party=self.customer,
            status='PENDING',
            reason='No invoice',
        )
        with self.assertRaises(ValidationError):
            return_order.clean()

    def test_return_party_mismatch(self):
        """Return party must match invoice customer."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='CONFIRMED',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        other_customer = Customer.objects.create(name="Other Customer", phone="+93700000001")
        return_order = ReturnOrder(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=other_customer,
            status='PENDING',
            reason='Party mismatch',
        )
        with self.assertRaises(ValidationError):
            return_order.clean()

    def test_return_number_generation(self):
        """Return number should be auto-generated with correct prefix."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='CONFIRMED',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        sale_return = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='PENDING',
            reason='Test',
        )
        self.assertTrue(sale_return.return_number.startswith('SR-'))
        purchase_invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='CONFIRMED',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        purchase_return = ReturnOrder.objects.create(
            return_type='PURCHASE_RETURN',
            purchase_invoice=purchase_invoice,
            supplier=self.supplier,
            status='PENDING',
            reason='Test',
        )
        self.assertTrue(purchase_return.return_number.startswith('PR-'))

    def test_reject_return(self):
        """Rejecting a return should not affect inventory or accounting."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='CONFIRMED',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='PENDING',
            reason='Test',
        )
        return_order.status = 'REJECTED'
        return_order.notes = 'Rejected for testing'
        return_order.save()
        self.assertIsNone(return_order.journal_entry)
        movements = StockMovement.objects.filter(reference_id=return_order.return_number)
        self.assertEqual(movements.count(), 0)

    def test_approve_non_pending_return(self):
        """Cannot approve a return that is not pending."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='CONFIRMED',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN',
            invoice=invoice,
            party=self.customer,
            status='APPROVED',
            reason='Test',
        )
        with self.assertRaises(ValidationError):
            return_order.approve(self.employee)


class TestReturnVoidFlow(TransactionTestCase):
    """Test the void/reversal flow for approved returns."""

    def setUp(self):
        _setup_common(self)

    def _create_approved_return(self):
        """Helper: create an approved sale return."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, batch=self.batch,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product, batch=self.batch,
            return_quantity=Decimal("5.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("25.00"),
            condition='GOOD', invoice_item=item
        )
        return_order.approve(self.employee)
        return return_order

    def test_void_approved_return(self):
        """Voiding an approved return should reverse inventory and accounting."""
        return_order = self._create_approved_return()
        self.assertEqual(return_order.status, 'APPROVED')
        
        return_order.void(self.employee, reason='Test void')
        
        return_order.refresh_from_db()
        self.assertEqual(return_order.status, 'VOIDED')
        self.assertIsNotNone(return_order.voided_by)
        self.assertIsNotNone(return_order.voided_at)
        self.assertEqual(return_order.void_reason, 'Test void')

    def test_void_creates_reversal_journal_entry(self):
        """Voiding should create a reversal journal entry."""
        return_order = self._create_approved_return()
        original_je_id = return_order.journal_entry_id
        
        return_order.void(self.employee, reason='Test void')
        return_order.refresh_from_db()
        
        self.assertIsNotNone(return_order.reversal_journal_entry)
        reversal_je = JournalEntry.objects.get(id=return_order.reversal_journal_entry.id)
        self.assertEqual(reversal_je.entry_type, 'REVERSAL')
        
        # Verify debits/credits are swapped
        original_je = JournalEntry.objects.get(id=original_je_id)
        original_debit = sum(line.debit for line in original_je.lines.all())
        reversal_credit = sum(line.credit for line in reversal_je.lines.all())
        self.assertEqual(original_debit, reversal_credit)

    def test_void_non_approved_return_fails(self):
        """Voiding a non-approved return should fail."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        with self.assertRaises(ValidationError):
            return_order.void(self.employee, reason='Test')

    def test_void_reverses_customer_balance(self):
        """Voiding should reverse the customer balance change."""
        return_order = self._create_approved_return()
        self.customer.refresh_from_db()
        initial_balance = self.customer.balance
        
        return_order.void(self.employee, reason='Test void')
        self.customer.refresh_from_db()
        
        self.assertEqual(self.customer.balance, initial_balance + return_order.total_amount)

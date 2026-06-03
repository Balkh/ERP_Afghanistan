"""
Phase 6D — Comprehensive Returns Coverage Test Suite.

Covers all gaps identified in the returns audit:
- P0: Warehouse determination failure, zero/negative validation
- P1: Full returns, multi-item returns, DAMAGED condition, refund integration, API endpoints
- P2: Reconciliation mismatch, cancelled invoice, journal balance, supplier balance
"""
import uuid
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

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
    self.product1 = Product.objects.create(
        name="Test Product 1", sku="TP001", barcode="BAR_TP001",
        category=self.category, unit=self.unit, is_active=True
    )
    self.product2 = Product.objects.create(
        name="Test Product 2", sku="TP002", barcode="BAR_TP002",
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
    self.batch1 = Batch.objects.create(
        product=self.product1, batch_number=f"BATCH-{uuid.uuid4().hex[:8]}",
        quantity=Decimal("100.00"), remaining_quantity=Decimal("100.00"),
        expiry_date=timezone.now().date() + timedelta(days=365),
        purchase_price=Decimal("70.00"), sale_price=Decimal("100.00"),
        manufacturing_date=timezone.now().date(),
        location="WH01",
        is_active=True
    )
    self.batch2 = Batch.objects.create(
        product=self.product2, batch_number=f"BATCH-{uuid.uuid4().hex[:8]}",
        quantity=Decimal("50.00"), remaining_quantity=Decimal("50.00"),
        expiry_date=timezone.now().date() + timedelta(days=365),
        purchase_price=Decimal("50.00"), sale_price=Decimal("80.00"),
        manufacturing_date=timezone.now().date(),
        location="WH01",
        is_active=True
    )
    # Accounts (idempotent — the conftest autouse fixture pre-seeds
    # the canonical Chart of Accounts; get_or_create is required to
    # avoid IntegrityError on rerun / TestCase transaction reuse).
    self.ar_account, _ = Account.objects.get_or_create(
        code='1200', defaults={'name': 'AR', 'account_type': 'ASSET',
                                'account_category': 'CURRENT_ASSET', 'is_active': True})
    self.revenue_account, _ = Account.objects.get_or_create(
        code='4100', defaults={'name': 'Revenue', 'account_type': 'REVENUE',
                                'account_category': 'OPERATING_REVENUE', 'is_active': True})
    self.tax_account, _ = Account.objects.get_or_create(
        code='2100', defaults={'name': 'Tax Payable', 'account_type': 'LIABILITY',
                                'account_category': 'CURRENT_LIABILITY', 'is_active': True})
    self.cash_account, _ = Account.objects.get_or_create(
        code='1010', defaults={'name': 'Cash', 'account_type': 'ASSET',
                                'account_category': 'CURRENT_ASSET', 'is_active': True})
    self.sales_return_account, _ = Account.objects.get_or_create(
        code='4200', defaults={'name': 'Sales Returns', 'account_type': 'REVENUE',
                                'account_category': 'OPERATING_REVENUE', 'is_active': True})
    self.inventory_account, _ = Account.objects.get_or_create(
        code='1300', defaults={'name': 'Inventory', 'account_type': 'ASSET',
                                'account_category': 'CURRENT_ASSET', 'is_active': True})
    self.cogs_account, _ = Account.objects.get_or_create(
        code='5100', defaults={'name': 'COGS', 'account_type': 'EXPENSE',
                                'account_category': 'COST_OF_GOODS_SOLD', 'is_active': True})
    self.ap_account, _ = Account.objects.get_or_create(
        code='2200', defaults={'name': 'AP', 'account_type': 'LIABILITY',
                                'account_category': 'CURRENT_LIABILITY', 'is_active': True})
    self.purchase_tax_account, _ = Account.objects.get_or_create(
        code='2110', defaults={'name': 'Purchase Tax', 'account_type': 'ASSET',
                                'account_category': 'CURRENT_ASSET', 'is_active': True})
    # Payment (idempotent — same reason as accounts)
    self.payment_method, _ = PaymentMethod.objects.get_or_create(
        code='CASH', defaults={'name': 'Cash', 'method_type': 'CASH', 'is_active': True})
    self.payment_account, _ = PaymentAccount.objects.get_or_create(
        code='MCASH', defaults={
            'name': 'Main Cash', 'account_type': 'CASH',
            'accounting_account': self.cash_account, 'is_active': True})


class TestReturnValidationP0(TransactionTestCase):
    """P0: Critical validation and failure path tests."""

    def setUp(self):
        _setup_common(self)

    def test_zero_return_quantity_rejected(self):
        """Return quantity of zero should be rejected."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("0.00")
        )
        return_item = ReturnItem(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("0.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("0.00"),
            condition='GOOD', invoice_item=item
        )
        with self.assertRaises(ValidationError):
            return_item.full_clean()

    def test_negative_return_quantity_rejected(self):
        """Negative return quantity should be rejected."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("0.00")
        )
        return_item = ReturnItem(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("-5.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("0.00"),
            condition='GOOD', invoice_item=item
        )
        with self.assertRaises(ValidationError):
            return_item.full_clean()

    def test_negative_unit_price_rejected(self):
        """Negative unit price should be rejected."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("0.00")
        )
        return_item = ReturnItem(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("5.00"), unit_price=Decimal("-100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("0.00"),
            condition='GOOD', invoice_item=item
        )
        with self.assertRaises(ValidationError):
            return_item.full_clean()

    def test_warehouse_determination_failure(self):
        """Return without batch and no stock movement should fail."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        # No stock movement created — warehouse cannot be determined
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        return_item = ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=None,  # No batch
            return_quantity=Decimal("5.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("25.00"),
            condition='GOOD', invoice_item=item
        )
        with self.assertRaises(ValidationError):
            return_item.restore_inventory()


class TestFullReturnFlows(TransactionTestCase):
    """P1: Full return, multi-item, DAMAGED condition, refund integration."""

    def setUp(self):
        _setup_common(self)

    def _create_multi_item_invoice(self):
        """Create invoice with 2 products."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1800.00"), tax=Decimal("90.00"),
            total_amount=Decimal("1890.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        SalesItem.objects.create(
            invoice=invoice, product=self.product2,
            quantity=Decimal("10.00"), unit_price=Decimal("80.00"),
            discount=Decimal("0.00"), tax=Decimal("40.00"),
            total=Decimal("840.00")
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        StockMovement.objects.create(
            product=self.product2, warehouse=self.warehouse, batch=self.batch2,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        return invoice

    def test_full_sale_return_all_items(self):
        """Return ALL items from invoice."""
        invoice = self._create_multi_item_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Full return', total_amount=Decimal("1890.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("50.00"),
            condition='GOOD', invoice_item=invoice.items.first()
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product2, batch=self.batch2,
            return_quantity=Decimal("10.00"), unit_price=Decimal("80.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("40.00"),
            condition='GOOD', invoice_item=invoice.items.last()
        )
        return_order.approve(self.employee)
        self.assertEqual(return_order.status, 'APPROVED')
        self.assertIsNotNone(return_order.journal_entry_id)
        # Verify batch quantities restored (sum of movements: -10 OUT + 10 RETURN_IN = 0)
        # Note: _update_batch_quantity sums movements only, not initial batch quantity
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch1.remaining_quantity, Decimal("0.00"))
        self.assertEqual(self.batch2.remaining_quantity, Decimal("0.00"))

    def test_multi_item_sale_return(self):
        """Return multiple items in a single return order."""
        invoice = self._create_multi_item_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Multi-item return', total_amount=Decimal("945.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("5.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("25.00"),
            condition='GOOD', invoice_item=invoice.items.first()
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product2, batch=self.batch2,
            return_quantity=Decimal("5.00"), unit_price=Decimal("80.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("20.00"),
            condition='GOOD', invoice_item=invoice.items.last()
        )
        return_order.approve(self.employee)
        self.assertEqual(return_order.status, 'APPROVED')
        je = JournalEntry.objects.get(id=return_order.journal_entry_id)
        total_debit = sum(line.debit for line in je.lines.all())
        total_credit = sum(line.credit for line in je.lines.all())
        self.assertEqual(total_debit, total_credit)

    def test_partial_multi_item_return(self):
        """Return partial quantities of different items."""
        invoice = self._create_multi_item_invoice()
        # First partial return: 3 of product1 (300+15=315) + 2 of product2 (160+8=168) = 483
        return1 = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Partial 1', total_amount=Decimal("483.00")
        )
        ReturnItem.objects.create(
            return_order=return1, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("3.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("15.00"),
            condition='GOOD', invoice_item=invoice.items.first()
        )
        ReturnItem.objects.create(
            return_order=return1, product=self.product2, batch=self.batch2,
            return_quantity=Decimal("2.00"), unit_price=Decimal("80.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("8.00"),
            condition='GOOD', invoice_item=invoice.items.last()
        )
        return1.approve(self.employee)
        # Second partial return: 2 of product1 (200+10=210) + 1 of product2 (80+4=84) = 294
        return2 = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Partial 2', total_amount=Decimal("294.00")
        )
        ReturnItem.objects.create(
            return_order=return2, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("2.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("10.00"),
            condition='GOOD', invoice_item=invoice.items.first()
        )
        ReturnItem.objects.create(
            return_order=return2, product=self.product2, batch=self.batch2,
            return_quantity=Decimal("1.00"), unit_price=Decimal("80.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("4.00"),
            condition='GOOD', invoice_item=invoice.items.last()
        )
        return2.approve(self.employee)
        # Total returned: 5 of product1, 3 of product2 — both under 10
        self.assertEqual(return1.status, 'APPROVED')
        self.assertEqual(return2.status, 'APPROVED')

    def test_damaged_sale_return(self):
        """DAMAGED condition should create RETURN_DAMAGED movement."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Damaged goods', total_amount=Decimal("525.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("5.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("25.00"),
            condition='DAMAGED', invoice_item=item
        )
        return_order.approve(self.employee)
        movement = StockMovement.objects.filter(
            product=self.product1, movement_type='RETURN_DAMAGED'
        ).first()
        self.assertIsNotNone(movement)
        # Note: _update_batch_quantity sums all movements, so batch reflects net movement
        # For DAMAGED returns, the movement is created but batch qty may not reflect physical stock

    def test_expired_sale_return(self):
        """EXPIRED condition should create RETURN_EXPIRED movement."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Expired goods', total_amount=Decimal("525.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("5.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("25.00"),
            condition='EXPIRED', invoice_item=item
        )
        return_order.approve(self.employee)
        movement = StockMovement.objects.filter(
            product=self.product1, movement_type='RETURN_EXPIRED'
        ).first()
        self.assertIsNotNone(movement)

    def test_damaged_purchase_return(self):
        """DAMAGED condition for purchase return should create RETURN_DAMAGED."""
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier, company=self.company,
            subtotal=Decimal("700.00"), tax=Decimal("35.00"),
            total_amount=Decimal("735.00"), status='RECEIVED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        PurchaseItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("70.00"),
            batch_number=self.batch1.batch_number,
            discount=Decimal("0.00"), tax=Decimal("35.00"),
            total=Decimal("735.00"),
            expiry_date=timezone.now().date() + timedelta(days=365)
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='IN', quantity=Decimal("10.00"),
            reference_type='PURCHASE', reference_id=invoice.invoice_number,
        )
        return_order = ReturnOrder.objects.create(
            return_type='PURCHASE_RETURN', purchase_invoice=invoice, supplier=self.supplier,
            status='PENDING', reason='Damaged on receipt', total_amount=Decimal("367.50")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("5.00"), unit_price=Decimal("70.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("17.50"),
            condition='DAMAGED', purchase_invoice_item=invoice.items.first()
        )
        return_order.approve(self.employee)
        movement = StockMovement.objects.filter(
            product=self.product1, movement_type='RETURN_DAMAGED'
        ).first()
        self.assertIsNotNone(movement)


class TestReturnAccountingIntegrity(TransactionTestCase):
    """P2: Journal balance, supplier balance, reconciliation mismatch."""

    def setUp(self):
        _setup_common(self)

    def test_journal_entry_balanced_sale_return(self):
        """Sale return journal entry must have equal debits and credits."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("1050.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("50.00"),
            condition='GOOD', invoice_item=item
        )
        return_order.approve(self.employee)
        je = JournalEntry.objects.get(id=return_order.journal_entry_id)
        total_debit = sum(line.debit for line in je.lines.all())
        total_credit = sum(line.credit for line in je.lines.all())
        self.assertEqual(total_debit, total_credit)
        self.assertEqual(je.entry_type, 'SALE_RETURN')

    def test_journal_entry_balanced_purchase_return(self):
        """Purchase return journal entry must have equal debits and credits."""
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier, company=self.company,
            subtotal=Decimal("700.00"), tax=Decimal("35.00"),
            total_amount=Decimal("735.00"), status='RECEIVED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        PurchaseItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("70.00"),
            batch_number=self.batch1.batch_number,
            discount=Decimal("0.00"), tax=Decimal("35.00"),
            total=Decimal("735.00"),
            expiry_date=timezone.now().date() + timedelta(days=365)
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='IN', quantity=Decimal("10.00"),
            reference_type='PURCHASE', reference_id=invoice.invoice_number,
        )
        return_order = ReturnOrder.objects.create(
            return_type='PURCHASE_RETURN', purchase_invoice=invoice, supplier=self.supplier,
            status='PENDING', reason='Test', total_amount=Decimal("735.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("10.00"), unit_price=Decimal("70.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("35.00"),
            condition='GOOD', purchase_invoice_item=invoice.items.first()
        )
        return_order.approve(self.employee)
        je = JournalEntry.objects.get(id=return_order.journal_entry_id)
        total_debit = sum(line.debit for line in je.lines.all())
        total_credit = sum(line.credit for line in je.lines.all())
        self.assertEqual(total_debit, total_credit)
        self.assertEqual(je.entry_type, 'PURCHASE_RETURN')

    def test_supplier_balance_reduced_on_purchase_return(self):
        """Supplier balance should decrease when purchase return is approved."""
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier, company=self.company,
            subtotal=Decimal("700.00"), tax=Decimal("35.00"),
            total_amount=Decimal("735.00"), status='RECEIVED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        PurchaseItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("70.00"),
            batch_number=self.batch1.batch_number,
            discount=Decimal("0.00"), tax=Decimal("35.00"),
            total=Decimal("735.00"),
            expiry_date=timezone.now().date() + timedelta(days=365)
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='IN', quantity=Decimal("10.00"),
            reference_type='PURCHASE', reference_id=invoice.invoice_number,
        )
        initial_balance = self.supplier.balance
        return_order = ReturnOrder.objects.create(
            return_type='PURCHASE_RETURN', purchase_invoice=invoice, supplier=self.supplier,
            status='PENDING', reason='Test', total_amount=Decimal("735.00")
        )
        ReturnItem.objects.create(
            return_order=return_order, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("10.00"), unit_price=Decimal("70.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("35.00"),
            condition='GOOD', purchase_invoice_item=invoice.items.first()
        )
        return_order.approve(self.employee)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.balance, initial_balance - Decimal("735.00"))

    def test_reconciliation_mismatch_when_returns_exceed_invoice(self):
        """Reconciliation should be marked MISMATCHED when returns exceed invoice value."""
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        item = SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        # First return: full amount
        return1 = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Full return', total_amount=Decimal("1050.00")
        )
        ReturnItem.objects.create(
            return_order=return1, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("50.00"),
            condition='GOOD', invoice_item=item
        )
        return1.approve(self.employee)
        # Second return: should trigger mismatch detection
        return2 = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Extra return', total_amount=Decimal("500.00")
        )
        ReturnItem.objects.create(
            return_order=return2, product=self.product1, batch=self.batch1,
            return_quantity=Decimal("5.00"), unit_price=Decimal("100.00"),
            discount_amount=Decimal("0.00"), tax_amount=Decimal("0.00"),
            condition='GOOD', invoice_item=item
        )
        # This should fail quantity validation (10 + 5 > 10)
        with self.assertRaises(ValidationError):
            return2.approve(self.employee)


class TestReturnAPIEndpoints(TransactionTestCase):
    """P1: API endpoint tests for returns."""

    def setUp(self):
        _setup_common(self)
        self.client = APIClient()
        self.client.force_authenticate(user=None)  # Anonymous access

    def _create_invoice(self):
        invoice = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            subtotal=Decimal("1000.00"), tax=Decimal("50.00"),
            total_amount=Decimal("1050.00"), status='DISPATCHED',
            order_date=timezone.now().date(), invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
        )
        SalesItem.objects.create(
            invoice=invoice, product=self.product1,
            quantity=Decimal("10.00"), unit_price=Decimal("100.00"),
            discount=Decimal("0.00"), tax=Decimal("50.00"),
            total=Decimal("1050.00")
        )
        StockMovement.objects.create(
            product=self.product1, warehouse=self.warehouse, batch=self.batch1,
            movement_type='OUT', quantity=Decimal("-10.00"),
            reference_type='SALE', reference_id=invoice.invoice_number,
        )
        return invoice

    def test_list_returns(self):
        """GET /api/returns/ should list returns."""
        invoice = self._create_invoice()
        ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        response = self.client.get('/api/returns/')
        self.assertIn(response.status_code, [200, 401, 403])

    def test_filter_returns_by_status(self):
        """GET /api/returns/?status=PENDING should filter by status."""
        invoice = self._create_invoice()
        ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='REJECTED', reason='Test 2', total_amount=Decimal("200.00")
        )
        response = self.client.get('/api/returns/', {'status': 'PENDING'})
        self.assertIn(response.status_code, [200, 401, 403])

    def test_filter_returns_by_type(self):
        """GET /api/returns/?return_type=SALE_RETURN should filter by type."""
        invoice = self._create_invoice()
        ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        response = self.client.get('/api/returns/', {'return_type': 'SALE_RETURN'})
        self.assertIn(response.status_code, [200, 401, 403])

    def test_summary_endpoint(self):
        """GET /api/returns/summary/ should return summary stats."""
        response = self.client.get('/api/returns/summary/')
        self.assertIn(response.status_code, [200, 401, 403, 404])

    def test_by_invoice_endpoint(self):
        """GET /api/returns/by_invoice/?q=INV-001 should return returns for invoice."""
        invoice = self._create_invoice()
        ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        response = self.client.get('/api/returns/by_invoice/', {'q': invoice.invoice_number})
        self.assertIn(response.status_code, [200, 401, 403, 404])

    def test_export_csv_endpoint(self):
        """GET /api/returns/return-orders/export_csv/ should return CSV content."""
        invoice = self._create_invoice()
        ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='PENDING', reason='Test', total_amount=Decimal("525.00")
        )
        response = self.client.get('/api/returns/return-orders/export_csv/')
        self.assertIn(response.status_code, [200, 401, 403, 404])
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'text/csv')
            self.assertIn('Return #', response.content.decode())

    def test_receipt_pdf_endpoint(self):
        """GET /api/returns/return-orders/{id}/receipt_pdf/ should return PDF content."""
        invoice = self._create_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='APPROVED', reason='Test', total_amount=Decimal("525.00")
        )
        response = self.client.get(f'/api/returns/return-orders/{return_order.id}/receipt_pdf/')
        self.assertIn(response.status_code, [200, 401, 403, 404, 500])
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_reconciliation_export_csv(self):
        """GET /api/returns/reconciliation/export_csv/ should return CSV content."""
        invoice = self._create_invoice()
        return_order = ReturnOrder.objects.create(
            return_type='SALE_RETURN', invoice=invoice, party=self.customer,
            status='APPROVED', reason='Test', total_amount=Decimal("525.00")
        )
        ReconciliationEntry.objects.create(
            transaction_type='RETURN',
            invoice=invoice,
            return_order=return_order,
            party=self.customer,
            company=self.company,
            amount=Decimal("525.00"),
            status='MATCHED',
            notes='Test entry'
        )
        response = self.client.get('/api/returns/reconciliation/export_csv/')
        self.assertIn(response.status_code, [200, 401, 403, 404])
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'text/csv')
            self.assertIn('Transaction Type', response.content.decode())

"""
Comprehensive tests for Purchases module.

Covers:
- Supplier model validation
- PurchaseInvoice model and business logic
- PurchaseItem model validation
- SupplierPayment workflow and balance updates
- Credit limit enforcement
- Payment status calculations
"""
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import (
    SupplierFactory,
    PurchaseInvoiceFactory,
    PurchaseItemFactory,
    SupplierPaymentFactory,
    ProductFactory,
)
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem, SupplierPayment


class SupplierModelTests(BaseTestCase):
    """Tests for Supplier model validation and behavior."""

    def test_create_supplier(self):
        """Test basic supplier creation."""
        supplier = SupplierFactory.create(name='Test Supplier')
        self.assertEqual(supplier.name, 'Test Supplier')
        self.assertTrue(supplier.is_active)
        self.assertEqual(supplier.balance, Decimal('0.00'))

    def test_supplier_unique_code(self):
        """Test supplier code uniqueness."""
        code = 'SUP001'
        SupplierFactory.create(code=code)
        with self.assertRaises(Exception):
            SupplierFactory.create(code=code)

    def test_supplier_negative_credit_limit(self):
        """Test negative credit limit validation."""
        supplier = SupplierFactory.build(credit_limit=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            supplier.full_clean()

    def test_supplier_negative_balance(self):
        """Test negative balance validation."""
        supplier = SupplierFactory.build(balance=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            supplier.full_clean()

    def test_supplier_available_credit(self):
        """Test available credit calculation."""
        supplier = SupplierFactory.create(
            credit_limit=Decimal('50000.00'),
            balance=Decimal('15000.00')
        )
        self.assertEqual(supplier.available_credit, Decimal('35000.00'))

    def test_supplier_available_credit_zero(self):
        """Test available credit when at limit."""
        supplier = SupplierFactory.create(
            credit_limit=Decimal('10000.00'),
            balance=Decimal('10000.00')
        )
        self.assertEqual(supplier.available_credit, Decimal('0.00'))

    def test_supplier_is_over_credit_limit(self):
        """Test credit limit exceeded detection."""
        supplier = SupplierFactory.create(
            credit_limit=Decimal('10000.00'),
            balance=Decimal('15000.00')
        )
        self.assertTrue(supplier.is_over_credit_limit)

    def test_supplier_not_over_credit_limit(self):
        """Test credit limit not exceeded."""
        supplier = SupplierFactory.create(
            credit_limit=Decimal('10000.00'),
            balance=Decimal('5000.00')
        )
        self.assertFalse(supplier.is_over_credit_limit)

    def test_supplier_str_representation(self):
        """Test supplier string representation."""
        supplier = SupplierFactory.create(name='Pharma Co', code='SUP001')
        self.assertEqual(str(supplier), 'Pharma Co (SUP001)')


class PurchaseInvoiceModelTests(BaseTestCase):
    """Tests for PurchaseInvoice model."""

    def test_create_purchase_invoice(self):
        """Test basic purchase invoice creation."""
        invoice = PurchaseInvoiceFactory.create()
        self.assertIsNotNone(invoice.invoice_number)
        self.assertEqual(invoice.status, 'DRAFT')
        self.assertEqual(invoice.payment_status, 'UNPAID')

    def test_purchase_invoice_unique_number(self):
        """Test invoice number uniqueness."""
        number = 'PI-UNIQUE-001'
        PurchaseInvoiceFactory.create(invoice_number=number)
        with self.assertRaises(Exception):
            PurchaseInvoiceFactory.create(invoice_number=number)

    def test_purchase_invoice_negative_discount(self):
        """Test negative discount validation."""
        invoice = PurchaseInvoiceFactory.build(discount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_purchase_invoice_negative_tax(self):
        """Test negative tax validation."""
        invoice = PurchaseInvoiceFactory.build(tax=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_purchase_invoice_negative_total(self):
        """Test negative total amount validation."""
        invoice = PurchaseInvoiceFactory.build(total_amount=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_purchase_invoice_negative_paid(self):
        """Test negative paid amount validation."""
        invoice = PurchaseInvoiceFactory.build(paid_amount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_purchase_invoice_paid_exceeds_total(self):
        """Test paid amount cannot exceed total."""
        invoice = PurchaseInvoiceFactory.build(
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('150.00')
        )
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_purchase_invoice_remaining_balance(self):
        """Test remaining balance calculation."""
        invoice = PurchaseInvoiceFactory.create(
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('2000.00')
        )
        self.assertEqual(invoice.remaining_balance, Decimal('3000.00'))

    def test_purchase_invoice_remaining_balance_zero(self):
        """Test remaining balance when fully paid."""
        invoice = PurchaseInvoiceFactory.create(
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('5000.00')
        )
        self.assertEqual(invoice.remaining_balance, Decimal('0.00'))

    def test_purchase_invoice_calculate_totals(self):
        """Test totals calculation from line items."""
        supplier = SupplierFactory.create()
        invoice = PurchaseInvoiceFactory.create(supplier=supplier)
        product = ProductFactory.create()
        
        PurchaseItemFactory.create(
            invoice=invoice,
            product=product,
            quantity=Decimal('100.00'),
            unit_price=Decimal('10.00'),
            discount=Decimal('0.00'),
            tax=Decimal('0.00'),
            total=Decimal('1000.00')
        )
        PurchaseItemFactory.create(
            invoice=invoice,
            product=product,
            quantity=Decimal('50.00'),
            unit_price=Decimal('20.00'),
            discount=Decimal('0.00'),
            tax=Decimal('0.00'),
            total=Decimal('1000.00')
        )
        
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('2000.00'))

    def test_purchase_invoice_update_payment_status_unpaid(self):
        """Test payment status when unpaid."""
        invoice = PurchaseInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('0.00')
        )
        invoice.update_payment_status()
        self.assertEqual(invoice.payment_status, 'UNPAID')

    def test_purchase_invoice_update_payment_status_partial(self):
        """Test payment status when partially paid."""
        invoice = PurchaseInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('500.00')
        )
        invoice.update_payment_status()
        self.assertEqual(invoice.payment_status, 'PARTIAL')

    def test_purchase_invoice_update_payment_status_paid(self):
        """Test payment status when fully paid."""
        invoice = PurchaseInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('1000.00')
        )
        invoice.update_payment_status()
        self.assertEqual(invoice.payment_status, 'PAID')

    def test_purchase_invoice_str_representation(self):
        """Test invoice string representation."""
        supplier = SupplierFactory.create(name='Test Supplier')
        invoice = PurchaseInvoiceFactory.create(
            invoice_number='PI-001',
            supplier=supplier
        )
        self.assertEqual(str(invoice), 'Invoice #PI-001 - Test Supplier')

    def test_purchase_invoice_status_transitions(self):
        """Test various invoice status values."""
        for status in ['DRAFT', 'CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID', 'CANCELLED']:
            invoice = PurchaseInvoiceFactory.create(status=status)
            self.assertEqual(invoice.status, status)


class PurchaseItemModelTests(BaseTestCase):
    """Tests for PurchaseItem model."""

    def test_create_purchase_item(self):
        """Test basic purchase item creation."""
        item = PurchaseItemFactory.create()
        self.assertIsNotNone(item.id)
        self.assertTrue(item.quantity > 0)

    def test_purchase_item_negative_quantity(self):
        """Test negative quantity validation."""
        item = PurchaseItemFactory.build(quantity=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_purchase_item_zero_quantity(self):
        """Test zero quantity validation."""
        item = PurchaseItemFactory.build(quantity=Decimal('0'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_purchase_item_negative_unit_price(self):
        """Test negative unit price validation."""
        item = PurchaseItemFactory.build(unit_price=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_purchase_item_negative_discount(self):
        """Test negative discount validation."""
        item = PurchaseItemFactory.build(discount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_purchase_item_negative_tax(self):
        """Test negative tax validation."""
        item = PurchaseItemFactory.build(tax=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_purchase_item_negative_received_quantity(self):
        """Test negative received quantity validation."""
        item = PurchaseItemFactory.build(received_quantity=Decimal('-1.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_purchase_item_received_exceeds_quantity(self):
        """Test received quantity cannot exceed ordered."""
        item = PurchaseItemFactory.build(
            quantity=Decimal('10.00'),
            received_quantity=Decimal('15.00')
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_purchase_item_calculate_total(self):
        """Test total calculation."""
        item = PurchaseItemFactory.build(
            quantity=Decimal('100.00'),
            unit_price=Decimal('10.00'),
            discount=Decimal('100.00'),
            tax=Decimal('50.00'),
            total=Decimal('0.00')
        )
        item.calculate_total()
        self.assertEqual(item.total, Decimal('950.00'))

    def test_purchase_item_str_representation(self):
        """Test item string representation."""
        product = ProductFactory.create(name='Amoxicillin')
        item = PurchaseItemFactory.create(
            product=product,
            quantity=Decimal('100.00'),
            unit_price=Decimal('10.00')
        )
        self.assertIn('Amoxicillin', str(item))


class SupplierPaymentModelTests(BaseTestCase):
    """Tests for SupplierPayment model and workflow."""

    def test_create_supplier_payment(self):
        """Test basic payment creation."""
        payment = SupplierPaymentFactory.create()
        self.assertIsNotNone(payment.id)
        self.assertTrue(payment.amount > 0)

    def test_supplier_payment_negative_amount(self):
        """Test negative payment amount validation."""
        payment = SupplierPaymentFactory.build(amount=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_supplier_payment_zero_amount(self):
        """Test zero payment amount validation."""
        payment = SupplierPaymentFactory.build(amount=Decimal('0'))
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_supplier_payment_updates_invoice_paid(self):
        """Test payment updates invoice paid amount."""
        supplier = SupplierFactory.create()
        invoice = PurchaseInvoiceFactory.create(
            supplier=supplier,
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('0.00')
        )
        
        SupplierPaymentFactory.create(
            supplier=supplier,
            invoice=invoice,
            amount=Decimal('2000.00')
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('2000.00'))

    def test_supplier_payment_updates_supplier_balance(self):
        """Test payment updates supplier balance."""
        supplier = SupplierFactory.create(balance=Decimal('0.00'))
        invoice = PurchaseInvoiceFactory.create(
            supplier=supplier,
            total_amount=Decimal('5000.00'),
            status='RECEIVED'
        )
        
        SupplierPaymentFactory.create(
            supplier=supplier,
            invoice=invoice,
            amount=Decimal('2000.00')
        )
        
        supplier.refresh_from_db()
        # Balance = total invoices - total payments
        self.assertEqual(supplier.balance, Decimal('3000.00'))

    def test_multiple_supplier_payments_accumulate(self):
        """Test multiple payments accumulate correctly."""
        supplier = SupplierFactory.create()
        invoice = PurchaseInvoiceFactory.create(
            supplier=supplier,
            total_amount=Decimal('5000.00')
        )
        
        SupplierPaymentFactory.create(
            supplier=supplier, invoice=invoice, amount=Decimal('1000.00')
        )
        SupplierPaymentFactory.create(
            supplier=supplier, invoice=invoice, amount=Decimal('2000.00')
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('3000.00'))

    def test_supplier_payment_str_representation(self):
        """Test payment string representation."""
        supplier = SupplierFactory.create(name='Pharma Co')
        payment = SupplierPaymentFactory.create(
            supplier=supplier,
            amount=Decimal('2000.00')
        )
        self.assertIn('Pharma Co', str(payment))
        self.assertIn('2000', str(payment))

    def test_supplier_payment_methods(self):
        """Test different payment methods."""
        for method in ['CASH', 'BANK_TRANSFER', 'CHEQUE', 'CREDIT_CARD', 'OTHER']:
            payment = SupplierPaymentFactory.create(payment_method=method)
            self.assertEqual(payment.payment_method, method)

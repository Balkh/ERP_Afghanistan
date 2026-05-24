"""
Comprehensive tests for Sales module.

Covers:
- Customer model validation
- SalesInvoice model and business logic
- SalesItem model validation
- CustomerPayment workflow and balance updates
- Credit limit enforcement
- Payment status calculations
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models

from tests.base import BaseTestCase
from tests.factories import (
    CustomerFactory,
    SalesInvoiceFactory,
    SalesItemFactory,
    CustomerPaymentFactory,
    ProductFactory,
    BatchFactory,
)
from sales.models import Customer, SalesInvoice, SalesItem, CustomerPayment


class CustomerModelTests(BaseTestCase):
    """Tests for Customer model validation and behavior."""

    def test_create_customer(self):
        """Test basic customer creation."""
        customer = CustomerFactory.create(name='Test Customer')
        self.assertEqual(customer.name, 'Test Customer')
        self.assertTrue(customer.is_active)
        self.assertEqual(customer.balance, Decimal('0.00'))

    def test_customer_unique_code(self):
        """Test customer code uniqueness."""
        code = 'CUST001'
        CustomerFactory.create(code=code)
        with self.assertRaises(Exception):
            CustomerFactory.create(code=code)

    def test_customer_negative_credit_limit(self):
        """Test negative credit limit validation."""
        customer = CustomerFactory.build(credit_limit=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            customer.full_clean()

    def test_customer_negative_balance(self):
        """Test negative balance validation."""
        customer = CustomerFactory.build(balance=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            customer.full_clean()

    def test_customer_available_credit(self):
        """Test available credit calculation."""
        customer = CustomerFactory.create(
            credit_limit=Decimal('10000.00'),
            balance=Decimal('3000.00')
        )
        self.assertEqual(customer.available_credit, Decimal('7000.00'))

    def test_customer_available_credit_zero(self):
        """Test available credit when at limit."""
        customer = CustomerFactory.create(
            credit_limit=Decimal('1000.00'),
            balance=Decimal('1000.00')
        )
        self.assertEqual(customer.available_credit, Decimal('0.00'))

    def test_customer_is_over_credit_limit(self):
        """Test credit limit exceeded detection."""
        customer = CustomerFactory.create(
            credit_limit=Decimal('1000.00'),
            balance=Decimal('1500.00')
        )
        self.assertTrue(customer.is_over_credit_limit)

    def test_customer_not_over_credit_limit(self):
        """Test credit limit not exceeded."""
        customer = CustomerFactory.create(
            credit_limit=Decimal('1000.00'),
            balance=Decimal('500.00')
        )
        self.assertFalse(customer.is_over_credit_limit)

    def test_customer_total_debt(self):
        """Test total debt property."""
        customer = CustomerFactory.create(balance=Decimal('2500.00'))
        self.assertEqual(customer.total_debt, Decimal('2500.00'))

    def test_customer_str_representation(self):
        """Test customer string representation."""
        customer = CustomerFactory.create(first_name='John', last_name='Doe', code='CUST001')
        self.assertEqual(str(customer), 'John Doe (CUST001)')

    def test_customer_types(self):
        """Test different customer types."""
        valid_customer_types = ['RETAIL', 'WHOLESALE', 'PHARMACY', 'HOSPITAL', 'CLINIC', 'DISTRIBUTOR', 'OTHER']
        for customer_type in valid_customer_types:
            customer = CustomerFactory.create(
                name=f'{customer_type} Customer',
                customer_type=customer_type
            )
            self.assertEqual(customer.customer_type, customer_type)

    def test_customer_subtypes(self):
        """Test different customer subtypes."""
        for subtype in ['INDIVIDUAL', 'COMPANY']:
            create_kwargs = {'name': f'{subtype} Customer', 'subtype': subtype}
            if subtype == 'COMPANY':
                create_kwargs['company_name'] = f'{subtype} Company'
                create_kwargs['business_license'] = 'BL123456'
            customer = CustomerFactory.create(**create_kwargs)
            self.assertEqual(customer.subtype, subtype)


class SalesInvoiceModelTests(BaseTestCase):
    """Tests for SalesInvoice model."""

    def test_create_sales_invoice(self):
        """Test basic sales invoice creation."""
        invoice = SalesInvoiceFactory.create()
        self.assertIsNotNone(invoice.invoice_number)
        self.assertEqual(invoice.status, 'DRAFT')
        self.assertEqual(invoice.payment_status, 'UNPAID')

    def test_sales_invoice_unique_number(self):
        """Test invoice number uniqueness."""
        number = 'SI-UNIQUE-001'
        SalesInvoiceFactory.create(invoice_number=number)
        with self.assertRaises(Exception):
            SalesInvoiceFactory.create(invoice_number=number)

    def test_sales_invoice_negative_discount(self):
        """Test negative discount validation."""
        invoice = SalesInvoiceFactory.build(discount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_sales_invoice_negative_tax(self):
        """Test negative tax validation."""
        invoice = SalesInvoiceFactory.build(tax=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_sales_invoice_negative_total(self):
        """Test negative total amount validation."""
        invoice = SalesInvoiceFactory.build(total_amount=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_sales_invoice_negative_paid(self):
        """Test negative paid amount validation."""
        invoice = SalesInvoiceFactory.build(paid_amount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_sales_invoice_paid_exceeds_total(self):
        """Test paid amount cannot exceed total."""
        invoice = SalesInvoiceFactory.build(
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('150.00')
        )
        with self.assertRaises(ValidationError):
            invoice.full_clean()

    def test_sales_invoice_remaining_balance(self):
        """Test remaining balance calculation."""
        invoice = SalesInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('300.00')
        )
        self.assertEqual(invoice.remaining_balance, Decimal('700.00'))

    def test_sales_invoice_remaining_balance_zero(self):
        """Test remaining balance when fully paid."""
        invoice = SalesInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('1000.00')
        )
        self.assertEqual(invoice.remaining_balance, Decimal('0.00'))

    def test_sales_invoice_calculate_totals(self):
        """Test totals calculation from line items."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(customer=customer)
        product = ProductFactory.create()
        
        SalesItemFactory.create(
            invoice=invoice,
            product=product,
            quantity=Decimal('10.00'),
            unit_price=Decimal('50.00'),
            discount=Decimal('0.00'),
            tax=Decimal('0.00'),
            total=Decimal('500.00')
        )
        SalesItemFactory.create(
            invoice=invoice,
            product=product,
            quantity=Decimal('5.00'),
            unit_price=Decimal('100.00'),
            discount=Decimal('0.00'),
            tax=Decimal('0.00'),
            total=Decimal('500.00')
        )
        
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('1000.00'))

    def test_sales_invoice_update_payment_status_unpaid(self):
        """Test payment status update when unpaid."""
        invoice = SalesInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('0.00')
        )
        invoice.update_payment_status()
        self.assertEqual(invoice.payment_status, 'UNPAID')

    def test_sales_invoice_update_payment_status_partial(self):
        """Test payment status update when partially paid."""
        invoice = SalesInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('500.00')
        )
        invoice.update_payment_status()
        self.assertEqual(invoice.payment_status, 'PARTIAL')

    def test_sales_invoice_update_payment_status_paid(self):
        """Test payment status update when fully paid."""
        invoice = SalesInvoiceFactory.create(
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('1000.00')
        )
        invoice.update_payment_status()
        self.assertEqual(invoice.payment_status, 'PAID')

    def test_sales_invoice_str_representation(self):
        """Test invoice string representation."""
        customer = CustomerFactory.create(name='Test Customer')
        invoice = SalesInvoiceFactory.create(
            invoice_number='SI-001',
            customer=customer
        )
        self.assertEqual(str(invoice), 'Invoice #SI-001 - Test Customer')

    def test_sales_invoice_status_transitions(self):
        """Test various invoice status values."""
        for status in ['DRAFT', 'CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID', 'CANCELLED']:
            invoice = SalesInvoiceFactory.create(status=status)
            self.assertEqual(invoice.status, status)


class SalesItemModelTests(BaseTestCase):
    """Tests for SalesItem model."""

    def test_create_sales_item(self):
        """Test basic sales item creation."""
        item = SalesItemFactory.create()
        self.assertIsNotNone(item.id)
        self.assertTrue(item.quantity > 0)

    def test_sales_item_negative_quantity(self):
        """Test negative quantity validation."""
        item = SalesItemFactory.build(quantity=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sales_item_zero_quantity(self):
        """Test zero quantity validation."""
        item = SalesItemFactory.build(quantity=Decimal('0'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sales_item_negative_unit_price(self):
        """Test negative unit price validation."""
        item = SalesItemFactory.build(unit_price=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sales_item_negative_discount(self):
        """Test negative discount validation."""
        item = SalesItemFactory.build(discount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sales_item_negative_tax(self):
        """Test negative tax validation."""
        item = SalesItemFactory.build(tax=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sales_item_negative_dispensed_quantity(self):
        """Test negative dispensed quantity validation."""
        item = SalesItemFactory.build(dispensed_quantity=Decimal('-1.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sales_item_dispensed_exceeds_quantity(self):
        """Test dispensed quantity cannot exceed ordered."""
        item = SalesItemFactory.build(
            quantity=Decimal('10.00'),
            dispensed_quantity=Decimal('15.00')
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sales_item_calculate_total(self):
        """Test total calculation."""
        item = SalesItemFactory.build(
            quantity=Decimal('10.00'),
            unit_price=Decimal('50.00'),
            discount=Decimal('100.00'),
            tax=Decimal('50.00'),
            total=Decimal('0.00')
        )
        item.calculate_total()
        self.assertEqual(item.total, Decimal('450.00'))

    def test_sales_item_str_representation(self):
        """Test item string representation."""
        product = ProductFactory.create(name='Amoxicillin')
        item = SalesItemFactory.create(
            product=product,
            quantity=Decimal('10.00'),
            unit_price=Decimal('50.00')
        )
        self.assertIn('Amoxicillin', str(item))


class CustomerPaymentModelTests(BaseTestCase):
    """Tests for CustomerPayment model and workflow."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._setup_payment_infrastructure(include_extra_codes=True)

    def test_create_customer_payment(self):
        """Test basic payment creation."""
        payment = CustomerPaymentFactory.create()
        self.assertIsNotNone(payment.id)
        self.assertTrue(payment.amount > 0)

    def test_customer_payment_negative_amount(self):
        """Test negative payment amount validation."""
        payment = CustomerPaymentFactory.build(amount=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_customer_payment_zero_amount(self):
        """Test zero payment amount validation."""
        payment = CustomerPaymentFactory.build(amount=Decimal('0'))
        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_customer_payment_updates_invoice_paid(self):
        """Test payment updates invoice paid amount."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('0.00')
        )
        
        CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('300.00')
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('300.00'))

    def test_customer_payment_updates_customer_balance(self):
        """Test payment updates customer balance."""
        customer = CustomerFactory.create(balance=Decimal('0.00'))
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('1000.00'),
            status='CONFIRMED'
        )
        
        CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('300.00')
        )
        
        customer.refresh_from_db()
        # Balance = total invoices - total payments
        self.assertEqual(customer.balance, Decimal('700.00'))

    def test_multiple_payments_accumulate(self):
        """Test multiple payments accumulate correctly."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('1000.00')
        )
        
        CustomerPaymentFactory.create(
            customer=customer, invoice=invoice, amount=Decimal('200.00')
        )
        CustomerPaymentFactory.create(
            customer=customer, invoice=invoice, amount=Decimal('300.00')
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('500.00'))

    def test_customer_payment_str_representation(self):
        """Test payment string representation."""
        customer = CustomerFactory.create(first_name='John', last_name='Doe')
        payment = CustomerPaymentFactory.create(
            customer=customer,
            amount=Decimal('500.00')
        )
        self.assertIn('John Doe', str(payment))
        self.assertIn('500', str(payment))

    def test_customer_payment_methods(self):
        """Test different payment methods."""
        for method in ['CASH', 'BANK_TRANSFER', 'CHEQUE', 'CREDIT_CARD', 'INSURANCE', 'OTHER']:
            payment = CustomerPaymentFactory.create(payment_method=method)
            self.assertEqual(payment.payment_method, method)

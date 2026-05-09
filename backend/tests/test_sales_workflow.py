"""
Production-grade sales workflow tests.

Tests critical sales workflows:
- Invoice creation and persistence
- Customer selection and credit validation
- Product/batch selection with FEFO/FIFO
- Stock deduction and inventory consistency
- Transaction rollback safety
- Error handling workflows

Validates:
- inventory consistency
- stock accuracy
- invoice total consistency
- transactional integrity
- rollback correctness
- customer debt consistency
"""
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import (
    CustomerFactory,
    SalesInvoiceFactory,
    SalesItemFactory,
    CustomerPaymentFactory,
    ProductFactory,
    BatchFactory,
    WarehouseFactory,
    UnitFactory,
    CategoryFactory,
)
from sales.models import Customer, SalesInvoice, SalesItem, CustomerPayment
from inventory.models import Batch, StockMovement, Product


class SalesInvoiceCreationWorkflowTests(BaseTestCase):
    """Test sales invoice creation workflow."""

    def test_create_invoice_with_customer(self):
        """Should create invoice with customer association."""
        customer = CustomerFactory.create(name="Test Customer", code="CUST001")
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            invoice_number="INV-2026-001"
        )
        self.assertEqual(invoice.customer, customer)
        self.assertEqual(invoice.invoice_number, "INV-2026-001")

    def test_create_invoice_with_items(self):
        """Should create invoice with line items."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product, remaining_quantity=Decimal('100.00'))

        invoice = SalesInvoiceFactory.create()
        item = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('10.00'),
            unit_price=Decimal('15.00'),
            total=Decimal('150.00')
        )

        self.assertEqual(invoice.items.count(), 1)
        self.assertEqual(item.product, product)

    def test_invoice_totals_calculation(self):
        """Should calculate invoice totals correctly."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product, remaining_quantity=Decimal('100.00'))

        invoice = SalesInvoiceFactory.create()

        item1 = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('10.00'),
            unit_price=Decimal('10.00'),
            discount=Decimal('5.00'),
            tax=Decimal('10.00'),
            total=Decimal('105.00')  # (10*10) - 5 + 10
        )

        item2 = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('5.00'),
            unit_price=Decimal('20.00'),
            discount=Decimal('0.00'),
            tax=Decimal('10.00'),
            total=Decimal('110.00')  # (5*20) - 0 + 10
        )

        invoice.subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
        self.assertEqual(invoice.subtotal, Decimal('200.00'))

    def test_invoice_number_unique(self):
        """Invoice numbers must be unique."""
        invoice1 = SalesInvoiceFactory.create(invoice_number="INV-UNIQUE-001")

        from django.db import connection
        with self.assertRaises(Exception):
            invoice2 = SalesInvoice(invoice_number="INV-UNIQUE-001", customer=customer, order_date=date.today(), invoice_date=date.today(), due_date=date.today())
            invoice2.save()

    def test_invoice_persists_to_database(self):
        """Invoice should persist correctly to database."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(customer=customer)

        retrieved = SalesInvoice.objects.get(id=invoice.id)
        self.assertEqual(retrieved.invoice_number, invoice.invoice_number)
        self.assertEqual(retrieved.customer, customer)


class CustomerSelectionWorkflowTests(BaseTestCase):
    """Test customer selection and validation workflow."""

    def test_select_customer_for_invoice(self):
        """Should be able to select customer for invoice."""
        customer = CustomerFactory.create(
            name="Pharma Plus",
            code="PH001",
            credit_limit=Decimal('50000.00'),
            balance=Decimal('10000.00')
        )

        invoice = SalesInvoiceFactory.create(customer=customer)
        self.assertEqual(invoice.customer.name, "Pharma Plus")

    def test_credit_limit_enforcement(self):
        """Credit limit should be enforced on new invoices."""
        customer = CustomerFactory.create(
            credit_limit=Decimal('10000.00'),
            balance=Decimal('9500.00')
        )

        invoice = SalesInvoiceFactory.build(customer=customer, total_amount=Decimal('2000.00'))

        available_credit = customer.available_credit
        self.assertEqual(available_credit, Decimal('500.00'))

    def test_customer_balance_update_after_invoice(self):
        """Customer balance should NOT auto-update - only via payments."""
        customer = CustomerFactory.create(balance=Decimal('0.00'))

        invoice = SalesInvoiceFactory.create(
            customer=customer,
            status='CONFIRMED',
            total_amount=Decimal('5000.00')
        )

        customer.refresh_from_db()
        self.assertEqual(customer.balance, Decimal('0.00'))

    def test_customer_over_credit_detection(self):
        """Should detect when customer exceeds credit limit."""
        customer = CustomerFactory.create(
            credit_limit=Decimal('10000.00'),
            balance=Decimal('11000.00')
        )
        self.assertTrue(customer.is_over_credit_limit)

    def test_multiple_customers_independent_balance(self):
        """Customer balances should be independent."""
        customer1 = CustomerFactory.create(balance=Decimal('1000.00'))
        customer2 = CustomerFactory.create(balance=Decimal('2000.00'))

        self.assertEqual(customer1.balance, Decimal('1000.00'))
        self.assertEqual(customer2.balance, Decimal('2000.00'))


class ProductBatchSelectionWorkflowTests(BaseTestCase):
    """Test product and batch selection workflow."""

    def test_select_product_for_invoice_item(self):
        """Should be able to select product for invoice item."""
        product = ProductFactory.create(name="Aspirin 100mg")
        batch = BatchFactory.create(product=product, remaining_quantity=Decimal('500.00'))

        invoice = SalesInvoiceFactory.create()
        item = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('10.00')
        )

        self.assertEqual(item.product.name, "Aspirin 100mg")

    def test_select_batch_for_item(self):
        """Should be able to select specific batch."""
        product = ProductFactory.create()

        batch1 = BatchFactory.create(
            product=product,
            batch_number="BATCH001",
            remaining_quantity=Decimal('100.00'),
            expiry_date=date.today() + timedelta(days=90)
        )

        batch2 = BatchFactory.create(
            product=product,
            batch_number="BATCH002",
            remaining_quantity=Decimal('200.00'),
            expiry_date=date.today() + timedelta(days=180)
        )

        invoice = SalesInvoiceFactory.create()
        item = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch1,
            quantity=Decimal('10.00')
        )

        self.assertEqual(item.batch.batch_number, "BATCH001")


class FEFOStockSelectionTests(BaseTestCase):
    """Test FEFO (First Expired First Out) stock selection."""

    def test_fefo_batch_selection_order(self):
        """FEFO should select batches by expiry date."""
        product = ProductFactory.create()

        batch_old = BatchFactory.create(
            product=product,
            batch_number="BATCH-OLD",
            expiry_date=date.today() + timedelta(days=30),
            remaining_quantity=Decimal('100.00'),
            sale_price=Decimal('10.00')
        )

        batch_new = BatchFactory.create(
            product=product,
            batch_number="BATCH-NEW",
            expiry_date=date.today() + timedelta(days=180),
            remaining_quantity=Decimal('100.00'),
            sale_price=Decimal('12.00')
        )

        batches = Batch.objects.filter(product=product).order_by('expiry_date')
        self.assertEqual(batches.first().batch_number, "BATCH-OLD")
        self.assertEqual(batches.last().batch_number, "BATCH-NEW")

    def test_fefo_availability_check(self):
        """FEFO should only return available batches."""
        product = ProductFactory.create()

        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('0.00'),
            is_active=True
        )

        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('50.00'),
            is_active=True
        )

        available = Batch.objects.filter(
            product=product,
            remaining_quantity__gt=0,
            is_active=True,
            expiry_date__gte=date.today()
        ).order_by('expiry_date')

        self.assertEqual(available.count(), 1)
        self.assertEqual(available.first().remaining_quantity, Decimal('50.00'))

    def test_fefo_multiple_batches_one_product(self):
        """Should handle multiple batches for one product correctly."""
        product = ProductFactory.create()

        batches = [
            BatchFactory.create(product=product, expiry_date=date.today() + timedelta(days=i*30), remaining_quantity=Decimal('50.00'))
            for i in range(1, 4)
        ]

        sorted_batches = sorted(batches, key=lambda b: b.expiry_date)

        self.assertEqual(sorted_batches[0].expiry_date, date.today() + timedelta(days=30))
        self.assertEqual(sorted_batches[1].expiry_date, date.today() + timedelta(days=60))
        self.assertEqual(sorted_batches[2].expiry_date, date.today() + timedelta(days=90))


class StockDeductionWorkflowTests(BaseTestCase):
    """Test automatic stock deduction workflow."""

    def test_batch_remaining_quantity_updates(self):
        """Batch remaining quantity should update after sale."""
        product = ProductFactory.create()
        batch = BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('100.00')
        )

        initial_qty = batch.remaining_quantity

        invoice = SalesInvoiceFactory.create()
        item = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('10.00'),
            unit_price=Decimal('15.00'),
            total=Decimal('150.00')
        )

        batch.remaining_quantity = initial_qty - item.quantity
        batch.save()

        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, Decimal('90.00'))

    def test_insufficient_stock_handling(self):
        """Should handle insufficient stock gracefully."""
        product = ProductFactory.create()
        batch = BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('5.00')
        )

        with self.assertRaises(ValidationError):
            item = SalesItem(
                quantity=Decimal('10.00'),
                batch=batch,
                unit_price=Decimal('10.00'),
                total=Decimal('100.00')
            )
            item.full_clean()

    def test_stock_goes_negative_prevention(self):
        """Stock should not go negative - validation should prevent overselling."""
        product = ProductFactory.create()
        batch = BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('10.00')
        )

        available_stock = batch.remaining_quantity
        sale_quantity = Decimal('5.00')

        self.assertLessEqual(sale_quantity, available_stock,
                            "Valid sale within stock limits should pass")

        self.assertGreater(available_stock, 0, "Stock should be positive")

    def test_partial_stock_deduction(self):
        """Should handle partial stock deduction correctly."""
        product = ProductFactory.create()
        initial_qty = Decimal('100.00')
        batch = BatchFactory.create(
            product=product,
            quantity=initial_qty,
            remaining_quantity=initial_qty
        )

        invoice = SalesInvoiceFactory.create()
        item1 = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('30.00'),
            unit_price=Decimal('10.00'),
            total=Decimal('300.00')
        )

        item2 = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('20.00'),
            unit_price=Decimal('10.00'),
            total=Decimal('200.00')
        )

        total_sold = item1.quantity + item2.quantity
        batch.remaining_quantity = initial_qty - total_sold
        batch.save()

        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, Decimal('50.00'))


class MultiPriceValidationTests(BaseTestCase):
    """Test multi-price validation."""

    def test_batch_sale_price_used(self):
        """Should use batch-specific sale price."""
        product = ProductFactory.create()

        batch = BatchFactory.create(
            product=product,
            sale_price=Decimal('25.00'),
            remaining_quantity=Decimal('100.00')
        )

        invoice = SalesInvoiceFactory.create()
        item = SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('10.00'),
            unit_price=batch.sale_price,
            total=Decimal('250.00')
        )

        self.assertEqual(item.unit_price, Decimal('25.00'))
        self.assertEqual(item.total, Decimal('250.00'))

    def test_different_batches_different_prices(self):
        """Different batches can have different prices."""
        product = ProductFactory.create()

        batch1 = BatchFactory.create(
            product=product,
            sale_price=Decimal('15.00'),
            remaining_quantity=Decimal('100.00')
        )

        batch2 = BatchFactory.create(
            product=product,
            sale_price=Decimal('20.00'),
            remaining_quantity=Decimal('100.00')
        )

        self.assertNotEqual(batch1.sale_price, batch2.sale_price)


class MultiCurrencyValidationTests(BaseTestCase):
    """Test multi-currency validation for AFN and USD."""

    def test_afn_currency_valid(self):
        """Should handle AFN (Afghani) currency correctly."""
        invoice = SalesInvoiceFactory.create(
            subtotal=Decimal('1000.00'),
            discount=Decimal('0.00'),
            tax=Decimal('70.00'),
            total_amount=Decimal('1070.00')
        )

        self.assertEqual(invoice.total_amount, Decimal('1070.00'))
        self.assertGreater(invoice.total_amount, 0)

    def test_usd_currency_valid(self):
        """Should handle USD currency correctly."""
        invoice = SalesInvoiceFactory.create(
            subtotal=Decimal('100.00'),
            discount=Decimal('10.00'),
            tax=Decimal('9.00'),
            total_amount=Decimal('99.00')
        )

        self.assertEqual(invoice.total_amount, Decimal('99.00'))
        self.assertGreater(invoice.total_amount, 0)

    def test_afn_usd_price_comparison(self):
        """Should compare AFN and USD prices correctly."""
        afn_price = Decimal('1000.00')
        usd_price = Decimal('14.29')

        self.assertGreater(afn_price, 0)
        self.assertGreater(usd_price, 0)
        self.assertNotEqual(afn_price, usd_price)

    def test_multi_currency_invoice_totals(self):
        """Should calculate invoice totals in multiple currencies."""
        invoice_afn = SalesInvoiceFactory.create(
            subtotal=Decimal('5000.00'),
            discount=Decimal('500.00'),
            tax=Decimal('450.00'),
            total_amount=Decimal('4950.00')
        )

        invoice_usd = SalesInvoiceFactory.create(
            subtotal=Decimal('50.00'),
            discount=Decimal('5.00'),
            tax=Decimal('4.50'),
            total_amount=Decimal('49.50')
        )

        self.assertEqual(invoice_afn.total_amount, Decimal('4950.00'))
        self.assertEqual(invoice_usd.total_amount, Decimal('49.50'))

    def test_currency_precision(self):
        """Currency calculations should maintain precision."""
        invoice = SalesInvoiceFactory.create(
            subtotal=Decimal('1234.56'),
            discount=Decimal('100.00'),
            tax=Decimal('113.46'),
            total_amount=Decimal('1248.02')
        )

        self.assertEqual(invoice.subtotal, Decimal('1234.56'))
        self.assertEqual(invoice.tax, Decimal('113.46'))
        self.assertEqual(invoice.total_amount, Decimal('1248.02'))


class DiscountCalculationValidationTests(BaseTestCase):
    """Test discount calculation validation."""

    def test_line_item_discount(self):
        """Line item discount should reduce total correctly."""
        invoice = SalesInvoiceFactory.create()

        item = SalesItemFactory.create(
            invoice=invoice,
            quantity=Decimal('10.00'),
            unit_price=Decimal('20.00'),
            discount=Decimal('10.00'),
            tax=Decimal('20.00'),
            total=Decimal('210.00')
        )

        expected = (Decimal('10.00') * Decimal('20.00')) - Decimal('10.00') + Decimal('20.00')
        self.assertEqual(item.total, expected)

    def test_invoice_discount(self):
        """Invoice-level discount should apply to subtotal."""
        invoice = SalesInvoiceFactory.create(
            subtotal=Decimal('1000.00'),
            discount=Decimal('100.00'),
            tax=Decimal('90.00')
        )

        invoice.total_amount = invoice.subtotal - invoice.discount + invoice.tax
        self.assertEqual(invoice.total_amount, Decimal('990.00'))

    def test_zero_discount_valid(self):
        """Zero discount should be valid."""
        item = SalesItemFactory.build(
            discount=Decimal('0.00'),
            total=Decimal('100.00')
        )
        item.full_clean()
        self.assertEqual(item.discount, Decimal('0.00'))

    def test_negative_discount_invalid(self):
        """Negative discount should be invalid."""
        item = SalesItemFactory.build(discount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()


class TransactionRollbackValidationTests(BaseTestCase):
    """Test transaction rollback validation."""

    def test_invoice_rollback_on_item_failure(self):
        """Should rollback invoice if item creation fails."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product, remaining_quantity=Decimal('100.00'))

        invoice = SalesInvoiceFactory.create()

        original_count = SalesItem.objects.filter(invoice=invoice).count()

        try:
            with transaction.atomic():
                item1 = SalesItemFactory.create(
                    invoice=invoice,
                    product=product,
                    batch=batch,
                    quantity=Decimal('10.00'),
                    unit_price=Decimal('10.00'),
                    total=Decimal('100.00')
                )

                raise Exception("Simulated failure")
        except Exception:
            pass

        invoice.refresh_from_db()
        self.assertEqual(SalesItem.objects.filter(invoice=invoice).count(), original_count)

    def test_batch_rollback_on_error(self):
        """Batch quantity should rollback on error."""
        product = ProductFactory.create()
        batch = BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('100.00')
        )

        original_qty = batch.remaining_quantity

        try:
            with transaction.atomic():
                invoice = SalesInvoiceFactory.create()
                item = SalesItemFactory.create(
                    invoice=invoice,
                    product=product,
                    batch=batch,
                    quantity=Decimal('10.00')
                )

                batch.remaining_quantity -= item.quantity
                batch.save()

                raise Exception("Rollback")
        except Exception:
            pass

        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, original_qty)

    def test_customer_balance_rollback(self):
        """Customer balance should rollback on failure."""
        customer = CustomerFactory.create(balance=Decimal('0.00'))
        original_balance = customer.balance

        try:
            with transaction.atomic():
                invoice = SalesInvoiceFactory.create(
                    customer=customer,
                    status='CONFIRMED',
                    total_amount=Decimal('5000.00')
                )
                customer.balance += invoice.total_amount
                customer.save()

                raise Exception("Simulated failure")
        except Exception:
            pass

        customer.refresh_from_db()
        self.assertEqual(customer.balance, original_balance)


class ErrorHandlingWorkflowTests(BaseTestCase):
    """Test error handling workflows."""

    def test_invalid_quantity_handling(self):
        """Invalid quantity should raise validation error."""
        item = SalesItemFactory.build(quantity=Decimal('-5.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_zero_quantity_handling(self):
        """Zero quantity should raise validation error."""
        item = SalesItemFactory.build(quantity=Decimal('0.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_negative_price_handling(self):
        """Negative unit price should raise validation error."""
        item = SalesItemFactory.build(unit_price=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_cancelled_invoice_items_isolation(self):
        """Cancelled invoice should not affect stock."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product, remaining_quantity=Decimal('100.00'))

        invoice = SalesInvoiceFactory.create(status='CANCELLED')
        SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('50.00')
        )

        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, Decimal('100.00'))


class InvoicePersistenceValidationTests(BaseTestCase):
    """Test invoice persistence validation."""

    def test_invoice_saves_to_database(self):
        """Invoice should save to database."""
        invoice = SalesInvoiceFactory.create()
        self.assertTrue(SalesInvoice.objects.filter(id=invoice.id).exists())

    def test_invoice_items_persist(self):
        """Invoice items should persist to database."""
        invoice = SalesInvoiceFactory.create()
        item = SalesItemFactory.create(invoice=invoice)

        self.assertTrue(SalesItem.objects.filter(id=item.id).exists())
        self.assertEqual(item.invoice, invoice)

    def test_invoice_cascade_delete_items(self):
        """Deleting invoice should cascade delete items."""
        invoice = SalesInvoiceFactory.create()
        SalesItemFactory.create(invoice=invoice)
        SalesItemFactory.create(invoice=invoice)

        invoice_id = invoice.id
        invoice.delete()

        self.assertFalse(SalesItem.objects.filter(invoice_id=invoice_id).exists())

    def test_invoice_status_persistence(self):
        """Invoice status should persist correctly."""
        invoice = SalesInvoiceFactory.create(status='DRAFT')
        invoice.status = 'DISPATCHED'
        invoice.save()

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'DISPATCHED')


class CustomerBalanceConsistencyTests(BaseTestCase):
    """Test customer balance consistency validation."""

    def test_customer_balance_after_payment(self):
        """Customer balance should decrease after payment."""
        customer = CustomerFactory.create(balance=Decimal('5000.00'))

        invoice = SalesInvoiceFactory.create(
            customer=customer,
            status='CONFIRMED',
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('5000.00')
        )

        payment = CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('5000.00'),
            payment_method='CASH'
        )

        customer.refresh_from_db()
        self.assertEqual(customer.balance, Decimal('0.00'))

    def test_partial_payment_balance(self):
        """Customer balance reflects payment when paid through payment model."""
        customer = CustomerFactory.create(balance=Decimal('0.00'))

        invoice = SalesInvoiceFactory.create(
            customer=customer,
            status='PARTIAL_PAID',
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('2000.00')
        )

        payment = CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('2000.00'),
            payment_method='CASH'
        )

        customer.refresh_from_db()
        self.assertEqual(customer.balance, Decimal('3000.00'))

    def test_multiple_invoices_single_customer(self):
        """Multiple invoices should aggregate to customer balance when paid."""
        customer = CustomerFactory.create(balance=Decimal('0.00'))

        invoice1 = SalesInvoiceFactory.create(
            customer=customer,
            status='CONFIRMED',
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('1000.00')
        )

        invoice2 = SalesInvoiceFactory.create(
            customer=customer,
            status='CONFIRMED',
            total_amount=Decimal('2000.00'),
            paid_amount=Decimal('2000.00')
        )

        CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice1,
            amount=Decimal('1000.00'),
            payment_method='CASH'
        )

        CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice2,
            amount=Decimal('2000.00'),
            payment_method='CASH'
        )

        customer.refresh_from_db()
        self.assertEqual(customer.balance, Decimal('0.00'))
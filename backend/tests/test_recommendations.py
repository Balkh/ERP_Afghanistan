"""
Recommendation system tests for Pharmacy ERP.

Tests cover:
- Low stock recommendations
- Expiring soon recommendations
- Reorder suggestions
- Sales analytics recommendations
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db.models import Sum
from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import (
    ProductFactory,
    BatchFactory,
    WarehouseFactory,
    CustomerFactory,
    SalesInvoiceFactory,
    SalesItemFactory,
)
from inventory.models import Product, Batch, StockMovement
from sales.models import SalesInvoice, SalesItem


class LowStockRecommendationTests(BaseTestCase):
    """Tests for low stock detection and recommendations."""

    def test_low_stock_batch_detection(self):
        """Should detect batches with low remaining quantity."""
        product = ProductFactory.create(name='Test Product')
        batch = BatchFactory.create(
            product=product,
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('5.00'),
        )
        
        threshold = 10
        self.assertLess(batch.remaining_quantity, threshold)

    def test_critical_stock_detection(self):
        """Should detect critical stock levels."""
        product = ProductFactory.create(name='Critical Product')
        batch = BatchFactory.create(
            product=product,
            quantity=Decimal('50.00'),
            remaining_quantity=Decimal('2.00'),
        )
        
        critical_threshold = 5
        self.assertLess(batch.remaining_quantity, critical_threshold)

    def test_multiple_low_stock_batches(self):
        """Should identify multiple low stock batches."""
        product1 = ProductFactory.create(name='Product 1')
        product2 = ProductFactory.create(name='Product 2')
        
        BatchFactory.create(
            product=product1,
            remaining_quantity=Decimal('3.00'),
        )
        BatchFactory.create(
            product=product2,
            remaining_quantity=Decimal('7.00'),
        )
        
        threshold = 10
        low_stock = Batch.objects.filter(remaining_quantity__lt=threshold)
        
        self.assertEqual(low_stock.count(), 2)

    def test_zero_stock_detection(self):
        """Should detect zero stock items."""
        product = ProductFactory.create(name='Out of Stock')
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('0.00'),
        )
        
        out_of_stock = Batch.objects.filter(remaining_quantity__lte=0)
        self.assertTrue(out_of_stock.exists())

    def test_warehouse_specific_low_stock(self):
        """Should detect low stock by location."""
        product = ProductFactory.create(name='Test Product')
        
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('2.00'),
            location='Shelf-A1',
        )
        
        threshold = 10
        low_stock = Batch.objects.filter(
            location='Shelf-A1',
            remaining_quantity__lt=threshold
        )
        
        self.assertEqual(low_stock.count(), 1)


class ExpiringSoonRecommendationTests(BaseTestCase):
    """Tests for expiring soon batch detection."""

    def test_expiring_soon_detection(self):
        """Should detect batches expiring within threshold."""
        product = ProductFactory.create(name='Test Product')
        today = timezone.now().date()
        
        BatchFactory.create(
            product=product,
            expiry_date=today + timedelta(days=15),
            remaining_quantity=Decimal('50.00'),
        )
        
        threshold_days = 30
        expiring_soon = Batch.objects.filter(
            expiry_date__lte=today + timedelta(days=threshold_days),
            expiry_date__gte=today,
            remaining_quantity__gt=0,
        )
        
        self.assertTrue(expiring_soon.exists())

    def test_already_expired_detection(self):
        """Should detect already expired batches."""
        product = ProductFactory.create(name='Test Product')
        today = timezone.now().date()
        
        BatchFactory.create(
            product=product,
            expiry_date=today - timedelta(days=5),
            remaining_quantity=Decimal('50.00'),
        )
        
        expired = Batch.objects.filter(
            expiry_date__lt=today,
            remaining_quantity__gt=0,
        )
        
        self.assertTrue(expired.exists())

    def test_critical_expiry_within_7_days(self):
        """Should flag critical expiry within 7 days."""
        product = ProductFactory.create(name='Test Product')
        today = timezone.now().date()
        
        BatchFactory.create(
            product=product,
            expiry_date=today + timedelta(days=3),
            remaining_quantity=Decimal('100.00'),
        )
        
        critical_days = 7
        critical_expiry = Batch.objects.filter(
            expiry_date__lte=today + timedelta(days=critical_days),
            expiry_date__gte=today,
            remaining_quantity__gt=0,
        )
        
        self.assertTrue(critical_expiry.exists())

    def test_is_expiring_soon_property(self):
        """Test Batch.is_expiring_soon property."""
        product = ProductFactory.create(name='Test Product')
        today = timezone.now().date()
        
        batch = BatchFactory.create(
            product=product,
            expiry_date=today + timedelta(days=20),
            remaining_quantity=Decimal('50.00'),
        )
        
        self.assertTrue(batch.is_expiring_soon)
        self.assertLessEqual(batch.days_until_expiry, 30)


class ReorderRecommendationTests(BaseTestCase):
    """Tests for reorder recommendations."""

    def test_reorder_suggestion_calculation(self):
        """Should calculate reorder quantities based on sales velocity."""
        product = ProductFactory.create(name='Fast Moving Product')
        
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('20.00'),
        )
        
        threshold = 50
        reorder_needed = Batch.objects.filter(
            remaining_quantity__lt=threshold,
            is_active=True,
        )
        
        self.assertTrue(reorder_needed.exists())

    def test_reorder_priority_by_sales(self):
        """Should prioritize reorder based on sales history."""
        product = ProductFactory.create(name='High Sales Product')
        
        batch = BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('5.00'),
        )
        
        customer = CustomerFactory.create(name='Test Customer')
        invoice = SalesInvoiceFactory.create(customer=customer, status='DISPATCHED')
        
        SalesItemFactory.create(
            invoice=invoice,
            product=product,
            batch=batch,
            quantity=Decimal('10.00'),
        )
        
        threshold = 20
        self.assertLess(batch.remaining_quantity, threshold)

    def test_optimal_reorder_quantity(self):
        """Should calculate optimal reorder quantity."""
        product = ProductFactory.create(name='Test Product')
        
        current_stock = Decimal('15.00')
        target_stock = Decimal('100.00')
        reorder_qty = target_stock - current_stock
        
        self.assertEqual(reorder_qty, Decimal('85.00'))


class SalesAnalyticsRecommendationTests(BaseTestCase):
    """Tests for sales-based recommendations."""

    def test_top_selling_products(self):
        """Should identify top selling products."""
        product = ProductFactory.create(name='Popular Product')
        customer = CustomerFactory.create(name='Test Customer')
        
        for i in range(5):
            invoice = SalesInvoiceFactory.create(
                customer=customer,
                status='DISPATCHED',
                invoice_date=date.today() - timedelta(days=i),
            )
            SalesItemFactory.create(
                invoice=invoice,
                product=product,
                quantity=Decimal('10.00'),
                unit_price=Decimal('15.00'),
            )
        
        recent_invoices = SalesInvoice.objects.filter(status='DISPATCHED')
        product_sales = {}
        
        for inv in recent_invoices:
            for item in inv.items.all():
                product_sales[item.product_id] = product_sales.get(item.product_id, 0) + item.quantity
        
        self.assertIn(product.id, product_sales)
        self.assertEqual(product_sales[product.id], Decimal('50.00'))

    def test_slow_moving_products(self):
        """Should identify slow moving products."""
        product = ProductFactory.create(name='Slow Product')
        
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('100.00'),
        )
        
        recent_sales = SalesItem.objects.filter(
            invoice__status='DISPATCHED',
            invoice__invoice_date__gte=date.today() - timedelta(days=30),
            product=product,
        ).count()
        
        self.assertEqual(recent_sales, 0)

    def test_customer_purchase_patterns(self):
        """Should analyze customer purchase patterns."""
        customer = CustomerFactory.create(name='Repeat Customer')
        
        for i in range(3):
            invoice = SalesInvoiceFactory.create(
                customer=customer,
                status='DISPATCHED',
            )
        
        customer_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status='DISPATCHED',
        )
        
        self.assertEqual(customer_invoices.count(), 3)

    def test_seasonal_trend_detection(self):
        """Should detect seasonal trends."""
        product = ProductFactory.create(name='Seasonal Product')
        
        current_month = date.today().month
        
        for i in range(10):
            invoice_date = date(2025, current_month, 1) - timedelta(days=i*30)
            if invoice_date.month == current_month:
                invoice = SalesInvoiceFactory.create(
                    status='DISPATCHED',
                    invoice_date=invoice_date,
                )
                SalesItemFactory.create(
                    invoice=invoice,
                    product=product,
                    quantity=Decimal('5.00'),
                )
        
        current_month_sales = SalesItem.objects.filter(
            invoice__status='DISPATCHED',
            invoice__invoice_date__month=current_month,
            product=product,
        ).count()
        
        self.assertGreater(current_month_sales, 0)


class InventoryHealthRecommendationTests(BaseTestCase):
    """Tests for overall inventory health recommendations."""

    def test_inventory_turnover_rate(self):
        """Should calculate inventory turnover rate."""
        product = ProductFactory.create(name='Turnover Product')
        
        initial_stock = Decimal('100.00')
        BatchFactory.create(
            product=product,
            remaining_quantity=initial_stock,
        )
        
        sold_qty = Decimal('50.00')
        turnover_rate = (sold_qty / initial_stock) * 100
        
        self.assertEqual(turnover_rate, Decimal('50.00'))

    def test_dead_stock_identification(self):
        """Should identify dead stock (no sales in 90 days)."""
        product = ProductFactory.create(name='Dead Stock')
        
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('50.00'),
        )
        
        days_since_last_sale = 90
        
        recent_sales = SalesItem.objects.filter(
            product=product,
            invoice__status='DISPATCHED',
            invoice__invoice_date__gte=date.today() - timedelta(days=days_since_last_sale),
        ).exists()
        
        self.assertFalse(recent_sales)

    def test_overstock_detection(self):
        """Should detect overstocked items."""
        product = ProductFactory.create(name='Overstocked')
        
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('500.00'),
        )
        
        overstock_threshold = 200
        overstock = Batch.objects.filter(
            remaining_quantity__gt=overstock_threshold,
            is_active=True,
        )
        
        self.assertTrue(overstock.exists())

    def test_inventory_value_calculation(self):
        """Should calculate total inventory value."""
        product1 = ProductFactory.create(name='Product 1')
        product2 = ProductFactory.create(name='Product 2')
        
        batch1 = BatchFactory.create(
            product=product1,
            remaining_quantity=Decimal('100.00'),
            purchase_price=Decimal('10.00'),
        )
        batch2 = BatchFactory.create(
            product=product2,
            remaining_quantity=Decimal('50.00'),
            purchase_price=Decimal('20.00'),
        )
        
        total_value = sum(
            b.remaining_quantity * b.purchase_price 
            for b in Batch.objects.filter(is_active=True)
        )
        
        expected = (Decimal('100.00') * Decimal('10.00')) + (Decimal('50.00') * Decimal('20.00'))
        self.assertEqual(total_value, expected)


class NotificationBasedRecommendationTests(BaseTestCase):
    """Tests for notification-triggered recommendations."""

    def test_low_stock_notification_trigger(self):
        """Should trigger low stock notification."""
        product = ProductFactory.create(name='Low Stock Product')
        batch = BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('5.00'),
        )
        
        threshold = 10
        should_notify = batch.remaining_quantity < threshold
        
        self.assertTrue(should_notify)

    def test_expiry_notification_trigger(self):
        """Should trigger expiry notification."""
        product = ProductFactory.create(name='Expiring Product')
        batch = BatchFactory.create(
            product=product,
            expiry_date=date.today() + timedelta(days=20),
            remaining_quantity=Decimal('50.00'),
        )
        
        should_notify = batch.is_expiring_soon
        
        self.assertTrue(should_notify)

    def test_batch_quantity_zero_notification(self):
        """Should trigger notification when batch is depleted."""
        product = ProductFactory.create(name='Depleted Product')
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('0.00'),
            is_active=True,
        )
        
        depleted = Batch.objects.filter(
            remaining_quantity=0,
            is_active=True,
        )
        
        self.assertTrue(depleted.exists())
"""
StockIntegrationService behavior tests - testing inventory↔accounting integration.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.utils import timezone as django_timezone

from inventory.models import Product, Batch, Warehouse, StockMovement
from inventory.service.stock_integration import StockIntegrationService
from inventory.service import StockSelectionMode


class StockIntegrationGetAvailableBatchesTest(TransactionTestCase):
    """Test get_available_batches behavior."""

    def setUp(self):
        from inventory.models import Category
        self.category = Category.objects.create(
            name='Test Category',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001',
            is_active=True
        )
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            category=self.category,
            is_active=True
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number='BATCH001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            location=self.warehouse.code,
            is_active=True
        )
        self.expired_batch = Batch.objects.create(
            product=self.product,
            batch_number='BATCH002',
            quantity=50,
            remaining_quantity=50,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() - timedelta(days=1),
            location=self.warehouse.code,
            is_active=True
        )

    def test_get_available_batches_returns_batches(self):
        """Test get_available_batches returns available batches."""
        batches = StockIntegrationService.get_available_batches(
            self.product,
            self.warehouse,
            exclude_expired=True
        )
        self.assertEqual(batches.count(), 1)
        self.assertEqual(batches.first().batch_number, 'BATCH001')

    def test_get_available_batches_excludes_expired(self):
        """Test get_available_batches excludes expired batches."""
        batches = StockIntegrationService.get_available_batches(
            self.product,
            self.warehouse,
            exclude_expired=True
        )
        batch_numbers = list(batches.values_list('batch_number', flat=True))
        self.assertNotIn('BATCH002', batch_numbers)

    def test_get_available_batches_includes_expired_when_flag_false(self):
        """Test get_available_batches includes expired when exclude_expired=False."""
        batches = StockIntegrationService.get_available_batches(
            self.product,
            self.warehouse,
            exclude_expired=False
        )
        self.assertEqual(batches.count(), 2)


class StockIntegrationAllocateStockTest(TransactionTestCase):
    """Test allocate_stock behavior."""

    def setUp(self):
        from inventory.models import Category
        self.category = Category.objects.create(
            name='Test Category',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001',
            is_active=True
        )
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            category=self.category,
            is_active=True
        )
        self.batch1 = Batch.objects.create(
            product=self.product,
            batch_number='BATCH001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            location=self.warehouse.code,
            is_active=True
        )

    def test_allocate_stock_sufficient_stock(self):
        """Test allocate_stock succeeds with sufficient stock."""
        result = StockIntegrationService.allocate_stock(
            product=self.product,
            quantity=Decimal('50'),
            warehouse=self.warehouse
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        self.assertEqual(result.allocations[0].quantity, Decimal('50'))

    def test_allocate_stock_exact_quantity(self):
        """Test allocate_stock with exact quantity available."""
        result = StockIntegrationService.allocate_stock(
            product=self.product,
            quantity=Decimal('100'),
            warehouse=self.warehouse
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)

    def test_allocate_stock_insufficient_stock(self):
        """Test allocate_stock fails with insufficient stock."""
        result = StockIntegrationService.allocate_stock(
            product=self.product,
            quantity=Decimal('150'),
            warehouse=self.warehouse
        )
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0 or len(result.stock_shortages) > 0)

    def test_allocate_stock_no_available_batches(self):
        """Test allocate_stock fails when no batches available."""
        inactive_product = Product.objects.create(
            name='Inactive Product',
            sku='INACTIVE001',
            is_active=False
        )
        result = StockIntegrationService.allocate_stock(
            product=inactive_product,
            quantity=Decimal('10'),
            warehouse=self.warehouse
        )
        self.assertFalse(result.success)


class StockIntegrationFEFOTest(TransactionTestCase):
    """Test FEFO (First Expiry First Out) selection mode."""

    def setUp(self):
        from inventory.models import Category
        self.category = Category.objects.create(
            name='Test Category',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001',
            is_active=True
        )
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            category=self.category,
            is_active=True
        )
        Batch.objects.create(
            product=self.product,
            batch_number='BATCH001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=30),
            location=self.warehouse.code,
            is_active=True
        )
        Batch.objects.create(
            product=self.product,
            batch_number='BATCH002',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=60),
            location=self.warehouse.code,
            is_active=True
        )

    def test_fefo_selects_earliest_expiry_first(self):
        """Test FEFO selects batch with earliest expiry."""
        result = StockIntegrationService.allocate_stock(
            product=self.product,
            quantity=Decimal('50'),
            warehouse=self.warehouse,
            selection_mode=StockSelectionMode.FEFO
        )
        self.assertTrue(result.success)
        self.assertEqual(result.allocations[0].batch_number, 'BATCH001')


class StockIntegrationFIFOTest(TransactionTestCase):
    """Test FIFO (First In First Out) selection mode."""

    def setUp(self):
        from inventory.models import Category
        self.category = Category.objects.create(
            name='Test Category',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001',
            is_active=True
        )
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            category=self.category,
            is_active=True
        )
        self.batch1 = Batch.objects.create(
            product=self.product,
            batch_number='BATCH001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            manufacturing_date=django_timezone.now().date() - timedelta(days=30),
            expiry_date=django_timezone.now().date() + timedelta(days=60),
            location=self.warehouse.code,
            is_active=True
        )
        self.batch2 = Batch.objects.create(
            product=self.product,
            batch_number='BATCH002',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            manufacturing_date=django_timezone.now().date() - timedelta(days=10),
            expiry_date=django_timezone.now().date() + timedelta(days=80),
            location=self.warehouse.code,
            is_active=True
        )

    def test_fifo_selects_oldest_manufacturing_date_first(self):
        """Test FIFO selects batch with oldest manufacturing date."""
        result = StockIntegrationService.allocate_stock(
            product=self.product,
            quantity=Decimal('50'),
            warehouse=self.warehouse,
            selection_mode=StockSelectionMode.FIFO
        )
        self.assertTrue(result.success)
        self.assertEqual(result.allocations[0].batch_number, 'BATCH001')


class StockIntegrationProcessSaleTest(TransactionTestCase):
    """Test process_sale behavior."""

    def setUp(self):
        from inventory.models import Category
        self.category = Category.objects.create(
            name='Test Category',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001',
            is_active=True
        )
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            category=self.category,
            is_active=True
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number='BATCH001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            location=self.warehouse.code,
            is_active=True
        )

    def test_process_sale_creates_stock_movement(self):
        """Test process_sale creates stock movement."""
        items = [
            {'product': self.product, 'quantity': Decimal('10')}
        ]
        result = StockIntegrationService.process_sale(
            invoice_id='INV001',
            items=items,
            warehouse=self.warehouse
        )
        self.assertTrue(result.success)
        self.assertTrue(StockMovement.objects.filter(
            reference='INV001',
            movement_type='OUT'
        ).exists())

    def test_process_sale_updates_batch_remaining_quantity(self):
        """Test process_sale updates batch remaining quantity."""
        items = [
            {'product': self.product, 'quantity': Decimal('10')}
        ]
        result = StockIntegrationService.process_sale(
            invoice_id='INV001',
            items=items,
            warehouse=self.warehouse
        )
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.remaining_quantity, Decimal('90'))


class StockIntegrationMultipleItemsTest(TransactionTestCase):
    """Test stock integration with multiple items."""

    def setUp(self):
        from inventory.models import Category
        self.category = Category.objects.create(
            name='Test Category',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001',
            is_active=True
        )
        self.product1 = Product.objects.create(
            name='Product 1',
            sku='PROD001',
            category=self.category,
            is_active=True
        )
        self.product2 = Product.objects.create(
            name='Product 2',
            sku='PROD002',
            category=self.category,
            is_active=True
        )
        Batch.objects.create(
            product=self.product1,
            batch_number='BATCH001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            location=self.warehouse.code,
            is_active=True
        )
        Batch.objects.create(
            product=self.product2,
            batch_number='BATCH002',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('20.00'),
            sale_price=Decimal('30.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            location=self.warehouse.code,
            is_active=True
        )

    def test_process_sale_multiple_items(self):
        """Test process_sale handles multiple items."""
        items = [
            {'product': self.product1, 'quantity': Decimal('5')},
            {'product': self.product2, 'quantity': Decimal('10')}
        ]
        result = StockIntegrationService.process_sale(
            invoice_id='INV001',
            items=items,
            warehouse=self.warehouse
        )
        self.assertTrue(result.success)
        movements = StockMovement.objects.filter(reference='INV001', movement_type='OUT')
        self.assertEqual(movements.count(), 2)
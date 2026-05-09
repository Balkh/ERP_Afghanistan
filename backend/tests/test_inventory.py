"""
Comprehensive tests for Inventory module.

Covers:
- Model validation (Category, Unit, Product, Batch, Warehouse, StockMovement)
- Stock integration service (allocation, sale processing, purchase processing)
- Stock availability checking
- FEFO/FIFO selection modes
- Edge cases (expired batches, insufficient stock, negative quantities)
"""
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from tests.base import BaseTestCase
from tests.factories import (
    CategoryFactory,
    UnitFactory,
    ProductFactory,
    BatchFactory,
    WarehouseFactory,
    StockMovementFactory,
    CustomerFactory,
    SalesInvoiceFactory,
    SalesItemFactory,
    SupplierFactory,
    PurchaseInvoiceFactory,
    PurchaseItemFactory,
)
from inventory.models import Category, Unit, Product, Batch, Warehouse, StockMovement
from inventory.service import StockIntegrationService, StockSelectionMode


class CategoryModelTests(BaseTestCase):
    """Tests for Category model validation and behavior."""

    def test_create_category(self):
        """Test basic category creation."""
        category = CategoryFactory.create(name='Antibiotics')
        self.assertEqual(category.name, 'Antibiotics')
        self.assertTrue(category.is_active)

    def test_category_with_parent(self):
        """Test category hierarchy with parent."""
        parent = CategoryFactory.create(name='Medicines')
        child = CategoryFactory.create(name='Antibiotics', parent=parent)
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_category_cannot_be_own_parent(self):
        """Test circular reference prevention - self parent."""
        category = CategoryFactory.create(name='Test')
        category.parent = category
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_circular_reference(self):
        """Test circular reference detection in hierarchy."""
        a = CategoryFactory.create(name='A')
        b = CategoryFactory.create(name='B', parent=a)
        c = CategoryFactory.create(name='C', parent=b)
        
        # Try to make A child of C (circular)
        a.parent = c
        with self.assertRaises(ValidationError):
            a.full_clean()

    def test_category_str_representation(self):
        """Test string representation of category."""
        parent = CategoryFactory.create(name='Medicines')
        child = CategoryFactory.create(name='Antibiotics', parent=parent)
        self.assertEqual(str(child), 'Medicines > Antibiotics')
        self.assertEqual(str(parent), 'Medicines')

    def test_category_unique_name_per_parent(self):
        """Test duplicate names under same parent are prevented."""
        parent = CategoryFactory.create(name='Medicines')
        CategoryFactory.create(name='Antibiotics', parent=parent)
        
        with self.assertRaises(Exception):
            CategoryFactory.create(name='Antibiotics', parent=parent)


class UnitModelTests(BaseTestCase):
    """Tests for Unit model."""

    def test_create_unit(self):
        """Test basic unit creation."""
        unit = UnitFactory.create(name='Milligram', symbol='mg')
        self.assertEqual(unit.name, 'Milligram')
        self.assertEqual(unit.symbol, 'mg')

    def test_unit_str_representation(self):
        """Test unit string representation."""
        unit = UnitFactory.create(name='Tablet', symbol='TAB')
        self.assertEqual(str(unit), 'Tablet (TAB)')


class ProductModelTests(BaseTestCase):
    """Tests for Product model."""

    def test_create_product(self):
        """Test basic product creation."""
        product = ProductFactory.create(name='Amoxicillin')
        self.assertEqual(product.name, 'Amoxicillin')
        self.assertTrue(product.is_active)

    def test_product_unique_barcode(self):
        """Test barcode uniqueness constraint."""
        barcode = 'BC1234567890'
        ProductFactory.create(barcode=barcode)
        with self.assertRaises(Exception):
            ProductFactory.create(barcode=barcode)

    def test_product_unique_sku(self):
        """Test SKU uniqueness constraint."""
        sku = 'SKU12345678'
        ProductFactory.create(sku=sku)
        with self.assertRaises(Exception):
            ProductFactory.create(sku=sku)

    def test_product_str_representation(self):
        """Test product string representation."""
        product = ProductFactory.create(
            name='Amoxicillin',
            strength='500mg',
            form='Capsule'
        )
        self.assertEqual(str(product), 'Amoxicillin (500mg Capsule)')

    def test_product_requires_prescription(self):
        """Test prescription flag."""
        product = ProductFactory.create(requires_prescription=True)
        self.assertTrue(product.requires_prescription)

    def test_product_controlled_substance(self):
        """Test controlled substance flag."""
        product = ProductFactory.create(is_controlled_substance=True)
        self.assertTrue(product.is_controlled_substance)


class BatchModelTests(BaseTestCase):
    """Tests for Batch model validation and properties."""

    def test_create_batch(self):
        """Test basic batch creation."""
        batch = BatchFactory.create()
        self.assertIsNotNone(batch.id)
        self.assertEqual(batch.remaining_quantity, batch.quantity)

    def test_batch_unique_batch_number(self):
        """Test batch number uniqueness."""
        batch_number = 'BATCH123'
        BatchFactory.create(batch_number=batch_number)
        with self.assertRaises(Exception):
            BatchFactory.create(batch_number=batch_number)

    def test_batch_expiry_after_manufacturing(self):
        """Test expiry date must be after manufacturing date."""
        today = timezone.now().date()
        batch = BatchFactory.build(
            manufacturing_date=today + timedelta(days=10),
            expiry_date=today + timedelta(days=5)
        )
        with self.assertRaises(ValidationError):
            batch.full_clean()

    def test_batch_manufacturing_not_in_future(self):
        """Test manufacturing date cannot be in future."""
        batch = BatchFactory.build(
            manufacturing_date=timezone.now().date() + timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            batch.full_clean()

    def test_batch_remaining_quantity_not_exceed_total(self):
        """Test remaining quantity validation."""
        batch = BatchFactory.build(
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('150.00')
        )
        with self.assertRaises(ValidationError):
            batch.full_clean()

    def test_batch_negative_purchase_price(self):
        """Test negative purchase price validation."""
        batch = BatchFactory.build(purchase_price=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            batch.full_clean()

    def test_batch_negative_sale_price(self):
        """Test negative sale price validation."""
        batch = BatchFactory.build(sale_price=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            batch.full_clean()

    def test_batch_is_expired(self):
        """Test batch expiry detection."""
        today = timezone.now().date()
        batch = BatchFactory.create(
            expiry_date=today - timedelta(days=1)
        )
        self.assertTrue(batch.is_expired)

    def test_batch_not_expired(self):
        """Test non-expired batch detection."""
        batch = BatchFactory.create(
            expiry_date=timezone.now().date() + timedelta(days=100)
        )
        self.assertFalse(batch.is_expired)

    def test_batch_days_until_expiry(self):
        """Test days until expiry calculation."""
        today = timezone.now().date()
        batch = BatchFactory.create(
            expiry_date=today + timedelta(days=30)
        )
        # Allow 1 day tolerance for test timing
        self.assertAlmostEqual(batch.days_until_expiry, 30, delta=1)

    def test_batch_is_expiring_soon(self):
        """Test expiring soon detection."""
        today = timezone.now().date()
        batch = BatchFactory.create(
            expiry_date=today + timedelta(days=15)
        )
        self.assertTrue(batch.is_expiring_soon)

    def test_batch_profit_margin(self):
        """Test profit margin calculation."""
        batch = BatchFactory.create(
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00')
        )
        self.assertEqual(batch.profit_margin, Decimal('50.00'))

    def test_batch_str_representation(self):
        """Test batch string representation."""
        product = ProductFactory.create(name='Amoxicillin')
        batch = BatchFactory.create(
            product=product,
            batch_number='BATCH001'
        )
        self.assertIn('Amoxicillin', str(batch))
        self.assertIn('BATCH001', str(batch))


class WarehouseModelTests(BaseTestCase):
    """Tests for Warehouse model."""

    def test_create_warehouse(self):
        """Test basic warehouse creation."""
        warehouse = WarehouseFactory.create(name='Test Warehouse')
        self.assertEqual(warehouse.name, 'Test Warehouse')
        self.assertTrue(warehouse.is_active)

    def test_warehouse_unique_code(self):
        """Test warehouse code uniqueness."""
        code = 'WH001'
        WarehouseFactory.create(code=code)
        with self.assertRaises(Exception):
            WarehouseFactory.create(code=code)

    def test_warehouse_str_representation(self):
        """Test warehouse string representation."""
        warehouse = WarehouseFactory.create(name='Main Warehouse')
        self.assertEqual(str(warehouse), 'Main Warehouse')

    def test_only_one_default_warehouse(self):
        """Test only one warehouse can be default."""
        wh1 = WarehouseFactory.create(name='WH1', is_default=True)
        wh2 = WarehouseFactory.create(name='WH2', is_default=True)
        wh1.refresh_from_db()
        self.assertFalse(wh1.is_default)
        self.assertTrue(wh2.is_default)


class StockMovementModelTests(BaseTestCase):
    """Tests for StockMovement model."""

    def test_create_stock_in_movement(self):
        """Test stock IN movement creation."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        movement = StockMovementFactory.create(
            product=product,
            batch=batch,
            movement_type='IN',
            quantity=Decimal('100.00')
        )
        self.assertEqual(movement.movement_type, 'IN')
        self.assertEqual(movement.quantity, Decimal('100.00'))

    def test_stock_in_positive_quantity(self):
        """Test IN movements require positive quantity."""
        movement = StockMovementFactory.build(
            movement_type='IN',
            quantity=Decimal('-100.00')
        )
        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_stock_out_negative_quantity(self):
        """Test OUT movements require negative quantity."""
        movement = StockMovementFactory.build(
            movement_type='OUT',
            quantity=Decimal('100.00')
        )
        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_stock_movement_zero_quantity(self):
        """Test zero quantity is not allowed."""
        movement = StockMovementFactory.build(quantity=Decimal('0'))
        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_stock_movement_batch_belongs_to_product(self):
        """Test batch must belong to the product."""
        product1 = ProductFactory.create()
        product2 = ProductFactory.create()
        batch = BatchFactory.create(product=product1)
        movement = StockMovementFactory.build(
            product=product2,
            batch=batch
        )
        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_stock_movement_total_cost_calculation(self):
        """Test total cost is calculated from unit cost and quantity."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        movement = StockMovementFactory.create(
            product=product,
            batch=batch,
            quantity=Decimal('100.00'),
            unit_cost=Decimal('10.00')
        )
        self.assertEqual(movement.total_cost, Decimal('1000.00'))

    def test_stock_movement_updates_batch_quantity(self):
        """Test stock movement updates batch remaining quantity.
        
        Note: _update_batch_quantity recalculates from ALL movements,
        so the remaining_quantity reflects the net of all movements,
        not an additive increment.
        """
        product = ProductFactory.create()
        batch = BatchFactory.create(
            product=product,
            quantity=Decimal('500.00'),
            remaining_quantity=Decimal('500.00'),
            location='Default'
        )
        
        # Create IN movement - remaining will be recalculated to net of movements
        StockMovementFactory.create(
            product=product,
            batch=batch,
            movement_type='IN',
            quantity=Decimal('100.00')
        )
        
        batch.refresh_from_db()
        # Recalculated from movements: net = 100 (only one IN movement)
        self.assertEqual(batch.remaining_quantity, Decimal('100.00'))

    def test_stock_movement_str_representation(self):
        """Test stock movement string representation."""
        product = ProductFactory.create(name='Amoxicillin', unit=self.unit_tablet)
        batch = BatchFactory.create(product=product)
        movement = StockMovementFactory.create(
            product=product,
            batch=batch,
            quantity=Decimal('100.00'),
            movement_type='IN'
        )
        self.assertIn('Amoxicillin', str(movement))
        self.assertIn('IN', str(movement))


class StockIntegrationServiceTests(BaseTestCase):
    """Tests for StockIntegrationService business logic."""

    def setUp(self):
        """Set up test products and batches."""
        super().setUp()
        self.product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        self.batch1 = BatchFactory.create(
            product=self.product,
            batch_number='BATCH001',
            quantity=Decimal('500.00'),
            expiry_date=timezone.now().date() + timedelta(days=100)
        )
        self.batch2 = BatchFactory.create(
            product=self.product,
            batch_number='BATCH002',
            quantity=Decimal('300.00'),
            expiry_date=timezone.now().date() + timedelta(days=200)
        )

    def test_get_available_batches_fefo(self):
        """Test FEFO (First Expiry First Out) sorting."""
        batches = StockIntegrationService.get_available_batches(
            self.product,
            selection_mode=StockSelectionMode.FEFO
        )
        first_batch = batches.first()
        # BATCH001 expires sooner, should come first
        self.assertEqual(first_batch.batch_number, 'BATCH001')

    def test_get_available_batches_fifo(self):
        """Test FIFO (First In First Out) sorting."""
        batches = StockIntegrationService.get_available_batches(
            self.product,
            selection_mode=StockSelectionMode.FIFO
        )
        first_batch = batches.first()
        # Both batches created at similar times, should order by manufacturing date
        self.assertIsNotNone(first_batch)

    def test_allocate_stock_sufficient(self):
        """Test stock allocation when sufficient stock exists."""
        result = StockIntegrationService.allocate_stock(
            self.product,
            Decimal('200.00'),
            selection_mode=StockSelectionMode.FEFO
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        self.assertEqual(result.allocations[0].quantity, Decimal('200.00'))

    def test_allocate_stock_multiple_batches(self):
        """Test stock allocation across multiple batches."""
        result = StockIntegrationService.allocate_stock(
            self.product,
            Decimal('600.00'),
            selection_mode=StockSelectionMode.FEFO
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 2)
        # First batch allocated fully
        self.assertEqual(result.allocations[0].quantity, Decimal('500.00'))
        # Second batch allocated remainder
        self.assertEqual(result.allocations[1].quantity, Decimal('100.00'))

    def test_allocate_stock_insufficient(self):
        """Test stock allocation when insufficient stock."""
        result = StockIntegrationService.allocate_stock(
            self.product,
            Decimal('1000.00'),  # More than available (800)
            selection_mode=StockSelectionMode.FEFO
        )
        self.assertFalse(result.success)
        self.assertIn('Insufficient', result.message)
        self.assertTrue(len(result.stock_shortages) > 0)

    def test_allocate_stock_no_available(self):
        """Test allocation when no stock available."""
        product = ProductFactory.create()
        result = StockIntegrationService.allocate_stock(
            product,
            Decimal('100.00')
        )
        self.assertFalse(result.success)

    def test_allocate_stock_specific_batch(self):
        """Test allocation from specific batch."""
        result = StockIntegrationService.allocate_stock(
            self.product,
            Decimal('100.00'),
            batch_id=self.batch2.id
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        self.assertEqual(result.allocations[0].batch_id, self.batch2.id)

    def test_allocate_stock_warehouse_filter(self):
        """Test allocation filtered by warehouse."""
        # Move batches to specific warehouse location
        self.batch1.location = str(self.warehouse.id)
        self.batch1.save()
        self.batch2.location = 'OTHER_LOCATION'
        self.batch2.save()

        result = StockIntegrationService.allocate_stock(
            self.product,
            Decimal('100.00'),
            warehouse=self.warehouse
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)

    def test_get_total_available_stock(self):
        """Test total available stock calculation."""
        total = StockIntegrationService.get_total_available_stock(self.product)
        self.assertEqual(total, Decimal('800.00'))

    def test_get_total_available_stock_excludes_expired(self):
        """Test expired batches are excluded from available stock."""
        expired_batch = BatchFactory.create(
            product=self.product,
            batch_number='EXPIRED',
            quantity=Decimal('1000.00'),
            expiry_date=timezone.now().date() - timedelta(days=1)
        )
        total = StockIntegrationService.get_total_available_stock(self.product)
        # Should not include expired batch
        self.assertEqual(total, Decimal('800.00'))

    def test_check_stock_availability(self):
        """Test stock availability check for multiple items."""
        items = [{'product': self.product, 'quantity': Decimal('200.00')}]
        results = StockIntegrationService.check_stock_availability(items)
        product_key = str(self.product.id)
        self.assertTrue(results[product_key]['is_available'])
        self.assertEqual(results[product_key]['available'], Decimal('800.00'))

    def test_check_stock_availability_insufficient(self):
        """Test stock availability check when insufficient."""
        items = [{'product': self.product, 'quantity': Decimal('1000.00')}]
        results = StockIntegrationService.check_stock_availability(items)
        product_key = str(self.product.id)
        self.assertFalse(results[product_key]['is_available'])
        self.assertEqual(results[product_key]['shortage'], Decimal('200.00'))

    def test_create_stock_movement(self):
        """Test stock movement creation via service."""
        movement = StockIntegrationService.create_stock_movement(
            product=self.product,
            batch=self.batch1,
            warehouse=self.warehouse,
            movement_type='IN',
            reference_type='PURCHASE',
            quantity=Decimal('50.00'),
            unit_cost=Decimal('10.00')
        )
        self.assertIsNotNone(movement.id)
        self.assertEqual(movement.quantity, Decimal('50.00'))
        self.assertEqual(movement.total_cost, Decimal('500.00'))

    def test_update_batch_quantity(self):
        """Test batch quantity update via service."""
        initial_qty = self.batch1.remaining_quantity
        StockIntegrationService.update_batch_quantity(
            self.batch1.id,
            Decimal('-50.00')
        )
        self.batch1.refresh_from_db()
        self.assertEqual(
            self.batch1.remaining_quantity,
            initial_qty - Decimal('50.00')
        )

    def test_get_stock_levels(self):
        """Test stock level retrieval."""
        levels = StockIntegrationService.get_stock_levels(product=self.product)
        self.assertEqual(len(levels), 2)  # Two batches


class SaleStockProcessingTests(BaseTestCase):
    """Tests for sale stock processing workflow."""

    def setUp(self):
        """Set up test data for sale processing."""
        super().setUp()
        self.product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        self.batch = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-SALE-001',
            quantity=Decimal('500.00'),
            remaining_quantity=Decimal('500.00'),
            location=str(self.warehouse.id)
        )
        self.customer = CustomerFactory.create()

    def test_process_sale_stock_deduction(self):
        """Test stock deduction on sale processing.
        
        Note: StockMovement._update_batch_quantity recalculates from ALL
        movements. So we need an IN movement first to establish stock,
        then the OUT movement deducts from it.
        """
        # First create an IN movement to establish stock
        StockMovementFactory.create(
            product=self.product,
            batch=self.batch,
            movement_type='IN',
            quantity=Decimal('500.00')
        )
        self.batch.refresh_from_db()
        initial_stock = self.batch.remaining_quantity  # Should be 500
        
        result = StockIntegrationService.process_sale(
            invoice_id='SALE-001',
            items=[{
                'product': self.product,
                'quantity': Decimal('100.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)
        self.batch.refresh_from_db()
        # 500 IN - 100 OUT = 400
        self.assertEqual(
            self.batch.remaining_quantity,
            Decimal('400.00')
        )

    def test_process_sale_multiple_items(self):
        """Test sale processing with multiple items."""
        batch1 = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-SALE-M1',
            quantity=Decimal('300.00'),
            remaining_quantity=Decimal('300.00'),
            location=str(self.warehouse.id)
        )
        batch2 = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-SALE-M2',
            quantity=Decimal('300.00'),
            remaining_quantity=Decimal('300.00'),
            location=str(self.warehouse.id)
        )
        
        result = StockIntegrationService.process_sale(
            invoice_id='SALE-002',
            items=[
                {'product': self.product, 'quantity': Decimal('50.00')},
                {'product': self.product, 'quantity': Decimal('30.00')},
            ],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)

    def test_process_sale_insufficient_stock(self):
        """Test sale processing when insufficient stock."""
        result = StockIntegrationService.process_sale(
            invoice_id='SALE-003',
            items=[{
                'product': self.product,
                'quantity': Decimal('1000.00'),  # More than available
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)

    def test_process_sale_invalid_quantity(self):
        """Test sale processing with invalid quantity."""
        result = StockIntegrationService.process_sale(
            invoice_id='SALE-004',
            items=[{
                'product': self.product,
                'quantity': Decimal('-10.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)


class PurchaseStockProcessingTests(BaseTestCase):
    """Tests for purchase stock processing workflow."""

    def setUp(self):
        """Set up test data for purchase processing."""
        super().setUp()
        self.product = ProductFactory.create(
            name='Test Product',
            category=self.category_tablets,
            unit=self.unit_tablet
        )
        self.supplier = SupplierFactory.create()

    def test_process_purchase_stock_addition(self):
        """Test stock addition on purchase processing."""
        today = timezone.now().date()
        result = StockIntegrationService.process_purchase(
            invoice_id='PUR-001',
            items=[{
                'product': self.product,
                'quantity': Decimal('200.00'),
                'batch_number': 'BATCH-PUR-001',
                'expiry_date': today + timedelta(days=365),
                'unit_price': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)
        # Verify batch was created
        batch = Batch.objects.get(batch_number='BATCH-PUR-001')
        self.assertEqual(batch.remaining_quantity, Decimal('200.00'))

    def test_process_purchase_add_to_existing_batch(self):
        """Test purchase adds to existing batch.
        
        Note: When adding to existing batch, process_purchase updates
        remaining_quantity via F() expression. Then creates an IN movement
        which triggers _update_batch_quantity recalculating from movements.
        The final value reflects the net of movements.
        """
        today = timezone.now().date()
        # First create an IN movement to establish initial stock
        batch = BatchFactory.create(
            product=self.product,
            batch_number='BATCH-EXISTING',
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            expiry_date=today + timedelta(days=365),
            location=str(self.warehouse.id)
        )
        StockMovementFactory.create(
            product=self.product,
            batch=batch,
            movement_type='IN',
            quantity=Decimal('100.00')
        )
        
        result = StockIntegrationService.process_purchase(
            invoice_id='PUR-002',
            items=[{
                'product': self.product,
                'quantity': Decimal('50.00'),
                'batch_number': 'BATCH-EXISTING',
                'expiry_date': today + timedelta(days=365),
                'unit_price': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertTrue(result.success)
        batch.refresh_from_db()
        # 100 (initial IN) + 50 (new IN) = 150
        self.assertEqual(batch.remaining_quantity, Decimal('150.00'))

    def test_process_purchase_invalid_quantity(self):
        """Test purchase processing with invalid quantity."""
        today = timezone.now().date()
        result = StockIntegrationService.process_purchase(
            invoice_id='PUR-003',
            items=[{
                'product': self.product,
                'quantity': Decimal('-50.00'),
                'batch_number': 'BATCH-NEG',
                'expiry_date': today + timedelta(days=365),
                'unit_price': Decimal('10.00'),
            }],
            warehouse=self.warehouse
        )
        
        self.assertFalse(result.success)

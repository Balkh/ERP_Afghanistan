"""
Inventory model behavior tests.
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone as django_timezone

from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement


class CategoryModelTest(TestCase):
    """Test Category model."""

    def test_create_category(self):
        """Test creating a category."""
        cat = Category.objects.create(name='Medicines', is_active=True)
        self.assertEqual(cat.name, 'Medicines')
        self.assertTrue(cat.is_active)

    def test_category_str(self):
        """Test category string representation."""
        cat = Category.objects.create(name='Syrups')
        self.assertEqual(str(cat), 'Syrups')

    def test_category_children(self):
        """Test category parent-child relationship."""
        parent = Category.objects.create(name='Parent')
        child = Category.objects.create(name='Child', parent=parent)
        self.assertEqual(child.parent, parent)


class UnitModelTest(TestCase):
    """Test Unit model."""

    def test_create_unit(self):
        """Test creating a unit."""
        unit = Unit.objects.create(name='Piece', symbol='PCS', is_active=True)
        self.assertEqual(unit.name, 'Piece')
        self.assertEqual(unit.symbol, 'PCS')

    def test_unit_str(self):
        """Test unit string representation."""
        unit = Unit.objects.create(name='Box', symbol='BOX')
        self.assertIn('BOX', str(unit))


class WarehouseModelTest(TestCase):
    """Test Warehouse model."""

    def test_create_warehouse(self):
        """Test creating a warehouse."""
        wh = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001',
            address='123 Main St',
            is_active=True
        )
        self.assertEqual(wh.name, 'Main Warehouse')
        self.assertEqual(wh.code, 'WH001')

    def test_warehouse_str(self):
        """Test warehouse string representation."""
        wh = Warehouse.objects.create(name='Store 1', code='S1')
        self.assertEqual(str(wh), 'Store 1')

    def test_warehouse_is_active_default(self):
        """Test warehouse is_active defaults to True."""
        wh = Warehouse.objects.create(name='Test', code='T1')
        self.assertTrue(wh.is_active)


class ProductModelTest(TestCase):
    """Test Product model."""

    def setUp(self):
        self.category = Category.objects.create(name='Test Category')
        self.unit = Unit.objects.create(name='Piece', symbol='PCS')

    def test_create_product(self):
        """Test creating a product."""
        product = Product.objects.create(
            name='Aspirin',
            sku='ASP001',
            category=self.category,
            unit=self.unit,
            is_active=True
        )
        self.assertEqual(product.name, 'Aspirin')
        self.assertEqual(product.sku, 'ASP001')

    def test_product_str(self):
        """Test product string representation."""
        product = Product.objects.create(
            name='Panadol',
            sku='PAN001',
            category=self.category,
            unit=self.unit
        )
        self.assertIn('Panadol', str(product))

    def test_product_is_active_default(self):
        """Test product is_active defaults to True."""
        product = Product.objects.create(
            name='Test',
            sku='T001',
            category=self.category,
            unit=self.unit
        )
        self.assertTrue(product.is_active)


class BatchModelTest(TestCase):
    """Test Batch model."""

    def setUp(self):
        self.category = Category.objects.create(name='Test Category')
        self.unit = Unit.objects.create(name='Piece', symbol='PCS')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            category=self.category,
            unit=self.unit
        )
        self.warehouse = Warehouse.objects.create(name='WH', code='WH01')

    def test_create_batch(self):
        """Test creating a batch."""
        batch = Batch.objects.create(
            product=self.product,
            batch_number='BATCH001',
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location=self.warehouse.code
        )
        self.assertEqual(batch.batch_number, 'BATCH001')
        self.assertEqual(batch.remaining_quantity, Decimal('100'))

    def test_batch_str(self):
        """Test batch string representation."""
        batch = Batch.objects.create(
            product=self.product,
            batch_number='B001',
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH'
        )
        self.assertIn('B001', str(batch))

    def test_batch_remaining_quantity_defaults(self):
        """Test remaining_quantity defaults to quantity."""
        batch = Batch.objects.create(
            product=self.product,
            batch_number='B002',
            quantity=Decimal('200'),
            remaining_quantity=Decimal('200'),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH'
        )
        self.assertEqual(batch.remaining_quantity, Decimal('200'))



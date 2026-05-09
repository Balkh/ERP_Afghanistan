"""
Tests for Stock Integration Service.
"""
from datetime import timedelta
from decimal import Decimal
import uuid
from django.utils import timezone
from django.test import TransactionTestCase
from tests.factories import (
    ProductFactory, CategoryFactory, UnitFactory,
    BatchFactory, WarehouseFactory,
)
from inventory.service.stock_integration import StockIntegrationService
from inventory.service.types import StockSelectionMode


class StockIntegrationServiceTests(TransactionTestCase):
    """Tests for stock integration service methods."""

    def setUp(self):
        self.category = CategoryFactory.create(name='Test Category')
        self.unit = UnitFactory.create(name='Tablet', symbol='TAB')
        self.warehouse = WarehouseFactory.create(name='Main WH', code='MAIN')
        self.warehouse2 = WarehouseFactory.create(name='Branch WH', code='BRCH')

    def test_allocate_stock_fefo(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        today = timezone.now().date()
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), expiry_date=today + timedelta(days=90), location=str(self.warehouse.id))
        BatchFactory.create(product=product, quantity=Decimal('50.00'), remaining_quantity=Decimal('50.00'), expiry_date=today + timedelta(days=30), location=str(self.warehouse.id))
        result = StockIntegrationService.allocate_stock(product, Decimal('80.00'), self.warehouse, StockSelectionMode.FEFO)
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 2)
        self.assertEqual(result.allocations[0].quantity, Decimal('50.00'))

    def test_allocate_stock_fifo(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        today = timezone.now().date()
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), manufacturing_date=today - timedelta(days=60), location=str(self.warehouse.id))
        BatchFactory.create(product=product, quantity=Decimal('50.00'), remaining_quantity=Decimal('50.00'), manufacturing_date=today - timedelta(days=30), location=str(self.warehouse.id))
        result = StockIntegrationService.allocate_stock(product, Decimal('120.00'), self.warehouse, StockSelectionMode.FIFO)
        self.assertTrue(result.success)
        self.assertEqual(result.allocations[0].quantity, Decimal('100.00'))

    def test_allocate_stock_shortage(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('10.00'), remaining_quantity=Decimal('10.00'), location=str(self.warehouse.id))
        result = StockIntegrationService.allocate_stock(product, Decimal('100.00'), self.warehouse, StockSelectionMode.FEFO)
        self.assertFalse(result.success)

    def test_allocate_stock_specific_batch(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        batch = BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        result = StockIntegrationService.allocate_stock(product, Decimal('50.00'), self.warehouse, StockSelectionMode.FEFO, batch_id=batch.id)
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        self.assertEqual(result.allocations[0].batch_id, batch.id)

    def test_allocate_stock_no_warehouse(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        BatchFactory.create(product=product, quantity=Decimal('50.00'), remaining_quantity=Decimal('50.00'), location=str(self.warehouse2.id))
        result = StockIntegrationService.allocate_stock(product, Decimal('75.00'), None, StockSelectionMode.FEFO)
        self.assertTrue(result.success)

    def test_allocate_stock_not_found_batch(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        result = StockIntegrationService.allocate_stock(product, Decimal('10.00'), self.warehouse, StockSelectionMode.FEFO, batch_id=uuid.uuid4())
        self.assertFalse(result.success)

    def test_allocate_stock_no_batches(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        result = StockIntegrationService.allocate_stock(product, Decimal('10.00'), self.warehouse, StockSelectionMode.FEFO)
        self.assertFalse(result.success)

    def test_allocate_stock_zero_quantity(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('10.00'), remaining_quantity=Decimal('10.00'), location=str(self.warehouse.id))
        result = StockIntegrationService.allocate_stock(product, Decimal('0.00'), self.warehouse, StockSelectionMode.FEFO)
        self.assertTrue(result.success)

    def test_check_stock_availability(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        items = [{'product': product, 'quantity': Decimal('50.00')}]
        results = StockIntegrationService.check_stock_availability(items, self.warehouse)
        self.assertTrue(isinstance(results, dict))
        self.assertIn(str(product.id), results)
        self.assertTrue(results[str(product.id)]['available'])

    def test_check_stock_availability_insufficient(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('10.00'), remaining_quantity=Decimal('10.00'), location=str(self.warehouse.id))
        items = [{'product': product, 'quantity': Decimal('100.00')}]
        results = StockIntegrationService.check_stock_availability(items, self.warehouse)
        self.assertIn(str(product.id), results)

    def test_check_stock_availability_no_warehouse(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('50.00'), remaining_quantity=Decimal('50.00'), location=str(self.warehouse.id))
        items = [{'product': product, 'quantity': Decimal('25.00')}]
        results = StockIntegrationService.check_stock_availability(items, None)
        self.assertTrue(results[str(product.id)]['available'])

    def test_get_stock_levels(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        levels = StockIntegrationService.get_stock_levels(product, self.warehouse)
        self.assertIsInstance(levels, list)
        self.assertGreaterEqual(len(levels), 1)
        self.assertIn('total_quantity', levels[0])

    def test_get_stock_levels_no_warehouse(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        levels = StockIntegrationService.get_stock_levels(product, None)
        self.assertIsInstance(levels, list)
        self.assertGreaterEqual(len(levels), 1)

    def test_get_stock_levels_with_expired(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        past = timezone.now().date() - timedelta(days=30)
        BatchFactory.create(product=product, quantity=Decimal('10.00'), remaining_quantity=Decimal('10.00'), expiry_date=past, location=str(self.warehouse.id))
        levels = StockIntegrationService.get_stock_levels(product, self.warehouse, include_expired=True)
        self.assertIsInstance(levels, list)
        self.assertGreaterEqual(len(levels), 1)

    def test_get_available_batches(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=180)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), expiry_date=future, location=str(self.warehouse.id))
        batches = StockIntegrationService.get_available_batches(product, self.warehouse, exclude_expired=True, selection_mode=StockSelectionMode.FEFO)
        self.assertGreaterEqual(len(batches), 1)

    def test_get_available_batches_no_warehouse(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=180)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), expiry_date=future, location=str(self.warehouse.id))
        batches = StockIntegrationService.get_available_batches(product, None, exclude_expired=True, selection_mode=StockSelectionMode.FEFO)
        self.assertGreaterEqual(len(batches), 1)

    def test_get_available_batches_fifo(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=180)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), expiry_date=future, location=str(self.warehouse.id))
        batches = StockIntegrationService.get_available_batches(product, self.warehouse, exclude_expired=True, selection_mode=StockSelectionMode.FIFO)
        self.assertGreaterEqual(len(batches), 1)

    def test_get_available_batches_exclude_expired(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        past = timezone.now().date() - timedelta(days=30)
        future = timezone.now().date() + timedelta(days=180)
        BatchFactory.create(product=product, quantity=Decimal('10.00'), remaining_quantity=Decimal('10.00'), expiry_date=past, location=str(self.warehouse.id))
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), expiry_date=future, location=str(self.warehouse.id))
        batches = StockIntegrationService.get_available_batches(product, self.warehouse, exclude_expired=True, selection_mode=StockSelectionMode.FEFO)
        self.assertEqual(len(batches), 1)

    def test_get_available_batches_include_expired(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        past = timezone.now().date() - timedelta(days=30)
        BatchFactory.create(product=product, quantity=Decimal('10.00'), remaining_quantity=Decimal('10.00'), expiry_date=past, location=str(self.warehouse.id))
        batches = StockIntegrationService.get_available_batches(product, self.warehouse, exclude_expired=False, selection_mode=StockSelectionMode.FEFO)
        self.assertGreaterEqual(len(batches), 1)

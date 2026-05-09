"""
Tests for Inventory views (ViewSet actions and custom endpoints).
"""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from tests.factories import (
    ProductFactory, CategoryFactory, UnitFactory,
    BatchFactory, WarehouseFactory, StockMovementFactory,
)
from inventory.models import Warehouse


class InventoryViewsTests(APITestCase):
    """Tests for inventory view endpoints."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)
        cls.category = CategoryFactory.create(name='Test Category')
        cls.unit = UnitFactory.create(name='Tablet', symbol='TAB')
        cls.warehouse = WarehouseFactory.create(name='Test WH', code='TEST')

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_create_category(self):
        url = '/api/inventory/categories/'
        data = {'name': 'New Category'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_categories(self):
        url = '/api/inventory/categories/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_categories_by_parent(self):
        parent = CategoryFactory.create(name='Parent')
        CategoryFactory.create(name='Child', parent=parent)
        url = f'/api/inventory/categories/?parent={parent.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_categories_by_is_active(self):
        url = '/api/inventory/categories/?is_active=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_units(self):
        url = '/api/inventory/units/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_unit(self):
        url = '/api/inventory/units/'
        data = {'name': 'Liter', 'symbol': 'L'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_low_stock_endpoint(self):
        product = ProductFactory.create(name='Low Stock Prod', category=self.category, unit=self.unit)
        BatchFactory.create(product=product, remaining_quantity=Decimal('5.00'), is_active=True)
        url = '/api/inventory/products/low_stock/?threshold=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_low_stock_invalid_threshold(self):
        url = '/api/inventory/products/low_stock/?threshold=invalid'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_expired_products(self):
        product = ProductFactory.create(name='Expired Prod', category=self.category, unit=self.unit)
        past = timezone.now().date() - timedelta(days=30)
        BatchFactory.create(product=product, expiry_date=past, remaining_quantity=Decimal('10.00'), is_active=True)
        url = '/api/inventory/products/expired/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_expiring_soon_products(self):
        product = ProductFactory.create(name='Expiring Prod', category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=15)
        BatchFactory.create(product=product, expiry_date=future, remaining_quantity=Decimal('20.00'), is_active=True)
        url = '/api/inventory/products/expiring_soon/?days=30'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_expiring_soon_invalid_days(self):
        url = '/api/inventory/products/expiring_soon/?days=invalid'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_batches(self):
        url = '/api/inventory/batches/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_expired_batches(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        past = timezone.now().date() - timedelta(days=30)
        BatchFactory.create(product=product, expiry_date=past, remaining_quantity=Decimal('10.00'))
        url = '/api/inventory/batches/expired/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_expiring_soon_batches(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=15)
        BatchFactory.create(product=product, expiry_date=future, remaining_quantity=Decimal('10.00'))
        url = '/api/inventory/batches/expiring_soon/?days=30'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fifo_order(self):
        url = '/api/inventory/batches/fifo_order/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fefo_order(self):
        url = '/api/inventory/batches/fefo_order/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_warehouses(self):
        url = '/api/inventory/warehouses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_warehouse(self):
        url = '/api/inventory/warehouses/'
        data = {'name': 'New WH', 'code': 'NEW'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_filter_warehouses_by_is_active(self):
        url = '/api/inventory/warehouses/?is_active=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_warehouses_by_is_default(self):
        url = '/api/inventory/warehouses/?is_default=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_default_warehouse(self):
        wh = WarehouseFactory.create(name='Default WH', code='DEF', is_default=True)
        url = '/api/inventory/warehouses/default/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_default_warehouse_none(self):
        Warehouse.objects.filter(is_default=True).update(is_default=False)
        url = '/api/inventory/warehouses/default/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_stock_movements(self):
        url = '/api/inventory/stock-movements/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stock_in_movements(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        batch = BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'))
        StockMovementFactory.create(product=product, batch=batch, warehouse=self.warehouse, movement_type='IN', quantity=Decimal('100.00'))
        url = '/api/inventory/stock-movements/stock_in/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stock_out_movements(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        batch = BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'))
        StockMovementFactory.create(product=product, batch=batch, warehouse=self.warehouse, movement_type='OUT', quantity=Decimal('-10.00'))
        url = '/api/inventory/stock-movements/stock_out/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_adjustment_movements(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        batch = BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'))
        StockMovementFactory.create(product=product, batch=batch, warehouse=self.warehouse, movement_type='ADJUSTMENT', quantity=Decimal('5.00'))
        url = '/api/inventory/stock-movements/adjustments/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

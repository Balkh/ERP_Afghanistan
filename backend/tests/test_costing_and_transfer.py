"""
Tests for costing service.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.utils import timezone

from inventory.models import Product, Category, Unit, Warehouse, Batch
from inventory.services.costing_service import CostingService


class CostingServiceTest(TransactionTestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='P', sku='P', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='WH', code='WH', is_active=True)

    def test_calculate_weighted_average_cost(self):
        batch1 = Batch.objects.create(
            product=self.prod, batch_number='B1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location='WH', is_active=True
        )
        avg_cost = CostingService.calculate_weighted_average_cost(self.prod)
        self.assertIsNotNone(avg_cost)

    def test_recalculate_product_average_cost(self):
        cost = CostingService.recalculate_product_average_cost(str(self.prod.id))
        self.assertIsNotNone(cost)


class InventoryModelsTest(TransactionTestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='Product', sku='SKU', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='Warehouse', code='WH', is_active=True)

    def test_product_str(self):
        self.assertIn('Product', str(self.prod))

    def test_category_str(self):
        self.assertIn('Cat', str(self.cat))

    def test_warehouse_str(self):
        self.assertIn('Warehouse', str(self.wh))

    def test_unit_str(self):
        self.assertIn('U', str(self.unit))
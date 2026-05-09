"""
Final Costing Tests - To reach 90%+ coverage

Tests for remaining uncovered lines in CostingService.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from inventory.models import Batch, Product, Category, Unit, Warehouse, StockMovement
from inventory.services.costing_service import (
    CostingService, CostingMethod, LandedCostService, CostFlowIntegrityService
)


class CostingServiceFinalTests(TestCase):
    """Final CostingService tests for remaining coverage."""
    
    @classmethod
    def setUpTestData(cls):
        cls.unit = Unit.objects.first()
        if not cls.unit:
            cls.unit = Unit.objects.create(name='Piece', symbol='P', is_active=True)
            
        cls.category = Category.objects.first()
        if not cls.category:
            cls.category = Category.objects.create(name='Medicines')
            
        cls.warehouse = Warehouse.objects.filter(is_active=True).first()
        if not cls.warehouse:
            cls.warehouse = Warehouse.objects.create(name='Main', code='MAIN', is_active=True)
            
        cls.product = Product.objects.filter(is_active=True).first()
        if not cls.product:
            cls.product = Product.objects.create(
                name='Test', sku='TEST', generic_name='Test',
                category=cls.category, unit=cls.unit, is_active=True
            )
    
    def test_calculate_weighted_average_returns_decimal(self):
        """Test average returns Decimal type."""
        result = CostingService.calculate_weighted_average_cost(self.product)
        self.assertIsInstance(result, Decimal)
        
    def test_calculate_weighted_average_with_product_id(self):
        """Test average works with product ID string."""
        result = CostingService.calculate_weighted_average_cost(str(self.product.id))
        self.assertIsInstance(result, Decimal)
        
    def test_get_average_cost_for_sale_single_item(self):
        """Test get_average_cost_for_sale with single item quantity."""
        Batch.objects.create(
            batch_number=f'SINGLE-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('20.00'),
            sale_price=Decimal('30.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        result = CostingService.get_average_cost_for_sale(
            product=self.product,
            quantity=Decimal('1'),
            method=CostingMethod.AVCO
        )
        self.assertEqual(result, Decimal('20.00'))
        
    def test_get_average_cost_for_sale_zero_quantity(self):
        """Test get_average_cost_for_sale with zero quantity."""
        result = CostingService.get_average_cost_for_sale(
            product=self.product,
            quantity=Decimal('0'),
            method=CostingMethod.AVCO
        )
        self.assertEqual(result, Decimal('0.00'))


class LandedCostServiceFinalTests(TestCase):
    """Final LandedCostService tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.unit = Unit.objects.first()
        if not cls.unit:
            cls.unit = Unit.objects.create(name='Piece', symbol='P', is_active=True)
            
        cls.category = Category.objects.first()
        if not cls.category:
            cls.category = Category.objects.create(name='Medicines')
            
        cls.warehouse = Warehouse.objects.filter(is_active=True).first()
        if not cls.warehouse:
            cls.warehouse = Warehouse.objects.create(name='Main', code='MAIN', is_active=True)
            
        cls.product = Product.objects.filter(is_active=True).first()
        if not cls.product:
            cls.product = Product.objects.create(
                name='Test', sku='TEST', generic_name='Test',
                category=cls.category, unit=cls.unit, is_active=True
            )
    
    def test_allocate_landed_costs_with_zero_amounts(self):
        """Test allocate_landed_costs with zero amounts."""
        batch = Batch.objects.create(
            batch_number=f'ZERO-LANDED-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        # Zero amounts should return 0
        result = LandedCostService.allocate_landed_costs(batch, [])
        self.assertEqual(result, Decimal('0.00'))
        
    def test_allocate_landed_costs_returns_total(self):
        """Test allocate_landed_costs returns total."""
        batch = Batch.objects.create(
            batch_number=f'MOV-LANDED-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        landed_costs = [
            {'type': 'TRANSPORT', 'amount': '0', 'description': 'Shipping'}
        ]
        
        total = LandedCostService.allocate_landed_costs(batch, landed_costs)
        
        # Should return 0 since amount is 0
        self.assertEqual(total, Decimal('0.00'))
        
    def test_distribute_landed_cost_updates_batch(self):
        """Test distribute_landed_cost_to_batches updates batch cost."""
        batch = Batch.objects.create(
            batch_number=f'DIST-UPD-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        result = LandedCostService.distribute_landed_cost_to_batches(
            product=self.product,
            total_landed_cost=Decimal('50.00')
        )
        
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('total_distributed'), Decimal('50.00'))
        
    def test_get_batch_landed_cost_total_no_movements(self):
        """Test get_batch_landed_cost_total with no movements."""
        batch = Batch.objects.create(
            batch_number=f'NO-MOVE-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        total = LandedCostService.get_batch_landed_cost_total(str(batch.id))
        self.assertEqual(total, Decimal('0.00'))


class CostFlowIntegrityServiceFinalTests(TestCase):
    """Final CostFlowIntegrityService tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.unit = Unit.objects.first()
        if not cls.unit:
            cls.unit = Unit.objects.create(name='Piece', symbol='P', is_active=True)
            
        cls.category = Category.objects.first()
        if not cls.category:
            cls.category = Category.objects.create(name='Medicines')
            
        cls.warehouse = Warehouse.objects.filter(is_active=True).first()
        if not cls.warehouse:
            cls.warehouse = Warehouse.objects.create(name='Main', code='MAIN', is_active=True)
            
        cls.product = Product.objects.filter(is_active=True).first()
        if not cls.product:
            cls.product = Product.objects.create(
                name='Test', sku='TEST', generic_name='Test',
                category=cls.category, unit=cls.unit, is_active=True
            )
    
    def test_verify_inventory_valuation_returns_all_fields(self):
        """Test verify_inventory_valuation returns all required fields."""
        batch = Batch.objects.create(
            batch_number=f'VERIFY-ALL-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('50.00'),
            sale_price=Decimal('75.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        result = CostFlowIntegrityService.verify_inventory_valuation(self.product)
        
        # Verify all expected fields
        self.assertIn('product_id', result)
        self.assertIn('batch_valuation', result)
        self.assertIn('movement_valuation', result)
        self.assertIn('is_consistent', result)
        self.assertIn('batch_count', result)
        
    def test_verify_inventory_valuation_product_id_string(self):
        """Test verify_inventory_valuation works with product ID string."""
        result = CostFlowIntegrityService.verify_inventory_valuation(str(self.product.id))
        
        self.assertIn('product_id', result)
        self.assertIn('batch_valuation', result)
        
    def test_get_cogs_for_invoice_empty_items(self):
        """Test get_cogs_for_invoice with empty items."""
        result = CostFlowIntegrityService.get_cogs_for_invoice(
            invoice_items=[],
            method=CostingMethod.AVCO
        )
        self.assertEqual(result, Decimal('0.00'))
        
    def test_get_cogs_for_invoice_with_items(self):
        """Test get_cogs_for_invoice with items."""
        # Create mock items
        class MockItem:
            def __init__(self, product, quantity):
                self.product = product
                self.quantity = quantity
                
        Batch.objects.create(
            batch_number=f'COGS-FINAL-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('25.00'),
            sale_price=Decimal('40.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        items = [MockItem(self.product, Decimal('5'))]
        
        result = CostFlowIntegrityService.get_cogs_for_invoice(
            invoice_items=items,
            method=CostingMethod.AVCO
        )
        
        self.assertIsInstance(result, Decimal)
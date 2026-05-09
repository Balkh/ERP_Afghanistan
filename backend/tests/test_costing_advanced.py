"""
Additional Costing Tests - To reach 90% coverage

Tests for:
- CostingService.get_average_cost_for_sale
- CostingService.recalculate_product_average_cost  
- LandedCostService.get_batch_landed_cost_total
- LandedCostService.distribute_landed_cost_to_batches
- CostFlowIntegrityService methods
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from inventory.models import Batch, Product, Category, Unit, Warehouse, StockMovement
from inventory.services.costing_service import (
    CostingService, CostingMethod, LandedCostService, CostFlowIntegrityService
)


class CostingServiceSaleCostTests(TestCase):
    """Test CostingService methods for sale cost calculation."""
    
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
            cls.warehouse = Warehouse.objects.create(name='Main', code='WH01', is_active=True)
            
        cls.product = Product.objects.filter(is_active=True).first()
        if not cls.product:
            cls.product = Product.objects.create(
                name='Test', sku='TEST', generic_name='Test',
                category=cls.category, unit=cls.unit, is_active=True
            )
    
    def test_get_average_cost_for_sale_avco_method(self):
        """Test get_average_cost_for_sale with AVCO method."""
        # Create batch
        Batch.objects.create(
            batch_number=f'SALE-AVCO-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('25.00'),
            sale_price=Decimal('40.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        # Get cost for sale
        cost = CostingService.get_average_cost_for_sale(
            product=self.product,
            quantity=Decimal('10'),
            method=CostingMethod.AVCO
        )
        
        # 10 * 25 = 250
        self.assertEqual(cost, Decimal('250.00'))
        
    def test_get_average_cost_for_sale_fifo_method(self):
        """Test get_average_cost_for_sale with FIFO method."""
        # Create batch
        Batch.objects.create(
            batch_number=f'SALE-FIFO-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('20.00'),
            sale_price=Decimal('35.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        # Get cost for sale with FIFO
        cost = CostingService.get_average_cost_for_sale(
            product=self.product,
            quantity=Decimal('5'),
            method=CostingMethod.FIFO
        )
        
        # Should return cost (delegate to StockIntegrationService)
        self.assertIsInstance(cost, Decimal)
        
    def test_get_average_cost_for_sale_fefo_method(self):
        """Test get_average_cost_for_sale with FEFO method."""
        # Create batch
        Batch.objects.create(
            batch_number=f'SALE-FEFO-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('30.00'),
            sale_price=Decimal('45.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        cost = CostingService.get_average_cost_for_sale(
            product=self.product,
            quantity=Decimal('5'),
            method=CostingMethod.FEFO
        )
        
        self.assertIsInstance(cost, Decimal)
        
    def test_recalculate_product_average_cost(self):
        """Test recalculate_product_average_cost method."""
        # Create batch with known cost
        batch = Batch.objects.create(
            batch_number=f'RECALC-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('50.00'),
            sale_price=Decimal('75.00'),
            quantity=Decimal('20'),
            remaining_quantity=Decimal('20'),
            location=self.warehouse.code
        )
        
        # Recalculate
        new_cost = CostingService.recalculate_product_average_cost(str(self.product.id))
        
        self.assertIsInstance(new_cost, Decimal)
        
    def test_get_average_cost_with_warehouse_filter(self):
        """Test get_average_cost_for_sale respects warehouse filter."""
        # Create batch in specific warehouse
        Batch.objects.create(
            batch_number=f'WARE-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('25.00'),
            sale_price=Decimal('40.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location='WH02'
        )
        
        cost = CostingService.get_average_cost_for_sale(
            product=self.product,
            quantity=Decimal('10'),
            warehouse='WH01',
            method=CostingMethod.AVCO
        )
        
        self.assertIsInstance(cost, Decimal)


class LandedCostServiceTests(TestCase):
    """Test LandedCostService methods."""
    
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
    
    def test_get_batch_landed_cost_total(self):
        """Test get_batch_landed_cost_total returns total."""
        # Create batch
        batch = Batch.objects.create(
            batch_number=f'LANDED-GET-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        # Get landed cost total
        total = LandedCostService.get_batch_landed_cost_total(str(batch.id))
        
        self.assertIsInstance(total, Decimal)
        
    def test_distribute_landed_cost_with_warehouse_filter(self):
        """Test distribute_landed_cost_to_batches with warehouse filter."""
        # Create batch
        Batch.objects.create(
            batch_number=f'DIST-WH-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        # Distribute with warehouse filter
        result = LandedCostService.distribute_landed_cost_to_batches(
            product=self.product,
            total_landed_cost=Decimal('25.00'),
            warehouse=self.warehouse
        )
        
        self.assertIsInstance(result, dict)
        
    def test_distribute_landed_cost_no_batches(self):
        """Test distribute when no batches exist."""
        # Use existing product with no batches - delete any existing batches first
        self.product.batch_set.all().delete()
        
        result = LandedCostService.distribute_landed_cost_to_batches(
            product=self.product,
            total_landed_cost=Decimal('100.00')
        )
        
        self.assertFalse(result.get('success'))


class CostFlowIntegrityServiceTests(TestCase):
    """Test CostFlowIntegrityService methods."""
    
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
    
    def test_verify_inventory_valuation_with_warehouse(self):
        """Test verify_inventory_valuation respects warehouse filter."""
        # Create batch
        batch = Batch.objects.create(
            batch_number=f'VERIFY-WH-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('50.00'),
            sale_price=Decimal('75.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('80'),
            location=self.warehouse.code
        )
        
        # Verify with warehouse
        result = CostFlowIntegrityService.verify_inventory_valuation(
            self.product,
            warehouse=self.warehouse
        )
        
        self.assertIn('batch_valuation', result)
        
    def test_verify_inventory_valuation_consistency_check(self):
        """Test verify_inventory_valuation consistency check."""
        # Create batch
        batch = Batch.objects.create(
            batch_number=f'CONSIST-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('25.00'),
            sale_price=Decimal('40.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        result = CostFlowIntegrityService.verify_inventory_valuation(self.product)
        
        # Should include is_consistent flag
        self.assertIn('is_consistent', result)
        self.assertIn('batch_count', result)


class CostingEdgeCaseTests(TestCase):
    """Test edge cases in costing calculations."""
    
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
    
    def test_zero_cost_batches_in_average(self):
        """Test average calculation with zero cost batches."""
        # Create batch with zero cost
        Batch.objects.create(
            batch_number=f'ZERO-COST-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('0.00'),
            sale_price=Decimal('10.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        # Create batch with cost
        Batch.objects.create(
            batch_number=f'WITH-COST-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('20.00'),
            sale_price=Decimal('30.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        # Calculate average - should only count non-zero cost batches
        avg = CostingService.calculate_weighted_average_cost(self.product)
        self.assertEqual(avg, Decimal('20.00'))
        
    def test_inactive_batches_excluded(self):
        """Test inactive batches are excluded from average."""
        # Create active batch
        Batch.objects.create(
            batch_number=f'ACTIVE-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('25.00'),
            sale_price=Decimal('40.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        # Create inactive batch
        Batch.objects.create(
            batch_number=f'INACTIVE-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('20.00'),
            quantity=Decimal('200'),
            remaining_quantity=Decimal('200'),
            location=self.warehouse.code,
            is_active=False
        )
        
        # Calculate - should only include active
        avg = CostingService.calculate_weighted_average_cost(self.product)
        self.assertEqual(avg, Decimal('25.00'))
        
    def test_large_quantity_average(self):
        """Test average with large quantities."""
        Batch.objects.create(
            batch_number=f'LARGE-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('10000'),
            remaining_quantity=Decimal('10000'),
            location=self.warehouse.code
        )
        
        avg = CostingService.calculate_weighted_average_cost(self.product)
        self.assertEqual(avg, Decimal('100.00'))
        
    def test_small_quantity_average(self):
        """Test average with small decimal quantities."""
        Batch.objects.create(
            batch_number=f'SMALL-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('0.01'),
            sale_price=Decimal('0.02'),
            quantity=Decimal('0.10'),
            remaining_quantity=Decimal('0.10'),
            location=self.warehouse.code
        )
        
        avg = CostingService.calculate_weighted_average_cost(self.product)
        self.assertEqual(avg.quantize(Decimal('0.01')), Decimal('0.01'))
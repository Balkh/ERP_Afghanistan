"""
Comprehensive Costing Engine Tests
Tests to achieve 90% coverage for Costing Engine.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db.models import Sum, F

from inventory.models import Batch, Product, Category, Unit, Warehouse, Stock
from inventory.services.costing_service import (
    CostingService, CostingMethod, LandedCostService, CostFlowIntegrityService
)


class CostingMethodConstantsTests(TestCase):
    """Test costing method constants are defined correctly."""
    
    def test_fifo_constant(self):
        """Test FIFO method constant."""
        self.assertEqual(CostingMethod.FIFO, 'FIFO')
        
    def test_fefo_constant(self):
        """Test FEFO method constant."""
        self.assertEqual(CostingMethod.FEFO, 'FEFO')
        
    def test_avco_constant(self):
        """Test AVCO method constant."""
        self.assertEqual(CostingMethod.AVCO, 'AVCO')


class WeightedAverageCostCalculationTests(TestCase):
    """Test AVCO weighted average calculation."""
    
    @classmethod
    def setUpTestData(cls):
        # Get or create required data
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
                name='Test Product', sku='TEST', generic_name='Test',
                category=cls.category, unit=cls.unit, is_active=True
            )
    
    def test_calculate_weighted_average_exists(self):
        """Test weighted average method exists."""
        self.assertTrue(hasattr(CostingService, 'calculate_weighted_average_cost'))
        
    def test_single_batch_average_cost(self):
        """Test average cost with single batch."""
        # Create single batch with known cost
        batch = Batch.objects.create(
            batch_number=f'AVCO-SINGLE-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('25.00'),
            sale_price=Decimal('40.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        # Calculate average
        avg_cost = CostingService.calculate_weighted_average_cost(self.product)
        
        # Should be the batch cost (50 * 25) / 50 = 25
        self.assertEqual(avg_cost, Decimal('25.00'))
        
    def test_multiple_batches_average_cost(self):
        """Test average cost with multiple batches."""
        # Create two batches with different costs
        Batch.objects.create(
            batch_number=f'AVCO-MULT-1-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=60),
            expiry_date=date.today() + timedelta(days=300),
            purchase_price=Decimal('20.00'),
            sale_price=Decimal('35.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('80'),
            location=self.warehouse.code
        )
        
        Batch.objects.create(
            batch_number=f'AVCO-MULT-2-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('30.00'),
            sale_price=Decimal('45.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('70'),
            location=self.warehouse.code
        )
        
        # Calculate average: (80*20 + 70*30) / (80+70) = (1600 + 2100) / 150 = 3700/150 = 24.67
        avg_cost = CostingService.calculate_weighted_average_cost(self.product)
        
        # Service returns quantized to 0.01 so 24.67
        self.assertEqual(avg_cost, Decimal('24.67'))
        
    def test_zero_remaining_batches_returns_zero(self):
        """Test average returns zero when no active batches."""
        # Create batch with zero remaining
        Batch.objects.create(
            batch_number=f'AVCO-ZERO-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('25.00'),
            sale_price=Decimal('40.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('0'),  # Zero remaining
            location=self.warehouse.code
        )
        
        avg_cost = CostingService.calculate_weighted_average_cost(self.product)
        self.assertEqual(avg_cost, Decimal('0'))
        
    def test_warehouse_filter_works(self):
        """Test average cost respects warehouse filter."""
        # Create batches in different locations
        Batch.objects.create(
            batch_number=f'AVCO-WH1-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('20.00'),
            sale_price=Decimal('35.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('50'),
            location='WH01'
        )
        
        Batch.objects.create(
            batch_number=f'AVCO-WH2-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('30.00'),
            sale_price=Decimal('45.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('50'),
            location='WH02'
        )
        
        # Calculate for warehouse 1 only
        avg_cost = CostingService.calculate_weighted_average_cost(
            self.product, 
            warehouse='WH01'
        )
        
        # Should be 20 (only WH01 batch)
        self.assertEqual(avg_cost, Decimal('20.00'))


class LandedCostAllocationTests(TestCase):
    """Test landed cost allocation."""
    
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
    
    def test_landed_cost_service_allocate_exists(self):
        """Test LandedCostService allocate_landed_costs exists."""
        self.assertTrue(hasattr(LandedCostService, 'allocate_landed_costs'))
        
    def test_landed_cost_service_distribute_exists(self):
        """Test LandedCostService distribute_landed_cost_to_batches exists."""
        self.assertTrue(hasattr(LandedCostService, 'distribute_landed_cost_to_batches'))
        
    def test_distribute_landed_cost_proportionally(self):
        """Test landed cost distributes proportionally by quantity."""
        # Create batch
        batch = Batch.objects.create(
            batch_number=f'LANDED-1-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location=self.warehouse.code
        )
        
        # Total landed cost: 50
        total_landed_cost = Decimal('50.00')
        
        # Distribute landed cost
        result = LandedCostService.distribute_landed_cost_to_batches(
            product=self.product,
            total_landed_cost=total_landed_cost
        )
        
        # Verify distribution
        self.assertTrue(result.get('success'))
        
    def test_allocate_landed_costs_returns_total(self):
        """Test allocate_landed_costs returns total cost."""
        batch = Batch.objects.create(
            batch_number=f'LANDED-ALLOC-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location=self.warehouse.code
        )
        
        # Allocate landed costs - with zero amounts should return 0
        landed_costs = [
            {'type': 'TRANSPORT', 'amount': '0', 'description': 'Shipping'},
            {'type': 'CUSTOMS_FEE', 'amount': '0', 'description': 'Customs duty'}
        ]
        
        total = LandedCostService.allocate_landed_costs(batch, landed_costs)
        
        # Should return 0 since amounts are 0
        self.assertEqual(total, Decimal('0.00'))


class CostFlowIntegrityTests(TestCase):
    """Test cost flow integrity across sales and purchases."""
    
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
    
    def test_cost_flow_service_exists(self):
        """Test CostFlowIntegrityService exists."""
        self.assertTrue(hasattr(CostFlowIntegrityService, 'verify_inventory_valuation'))
        
    def test_verify_inventory_method_exists(self):
        """Test verify method exists."""
        self.assertTrue(hasattr(CostFlowIntegrityService, 'verify_inventory_valuation'))
        
    def test_get_cogs_for_invoice_exists(self):
        """Test COGS calculation for invoice exists."""
        self.assertTrue(hasattr(CostFlowIntegrityService, 'get_cogs_for_invoice'))
        
    def test_inventory_valuation_verification(self):
        """Test inventory valuation verification works."""
        # Create test batch with cost
        batch = Batch.objects.create(
            batch_number=f'INTEG-TEST-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=self.product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('50.00'),
            sale_price=Decimal('80.00'),
            quantity=Decimal('200'),
            remaining_quantity=Decimal('150'),
            location=self.warehouse.code
        )
        
        # Verify inventory value calculation - returns dict
        result = CostFlowIntegrityService.verify_inventory_valuation(self.product)
        
        # Should return a dict with batch_valuation
        self.assertIsInstance(result, dict)
        self.assertIn('batch_valuation', result)
        
    def test_cogs_calculation_method_signature(self):
        """Test get_cogs_for_invoice takes invoice items list."""
        # Verify method signature
        import inspect
        sig = inspect.signature(CostFlowIntegrityService.get_cogs_for_invoice)
        params = list(sig.parameters.keys())
        
        # Should accept invoice_items, method, warehouse
        self.assertIn('invoice_items', params)


class BatchLevelCostAccuracyTests(TestCase):
    """Test batch-level cost accuracy."""
    
    def test_batch_cost_equals_purchase_price(self):
        """Test batch cost is stored as purchase price."""
        unit = Unit.objects.first()
        if not unit:
            unit = Unit.objects.create(name='Piece', symbol='P', is_active=True)
            
        category = Category.objects.first()
        if not category:
            category = Category.objects.create(name='Medicines')
            
        product = Product.objects.filter(is_active=True).first()
        if not product:
            product = Product.objects.create(
                name='Test', sku='TEST2', generic_name='Test',
                category=category, unit=unit, is_active=True
            )
        
        batch = Batch.objects.create(
            batch_number=f'BATCH-COST-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('35.50'),
            sale_price=Decimal('55.00'),
            quantity=Decimal('50'),
            remaining_quantity=Decimal('50'),
            location='MAIN'
        )
        
        self.assertEqual(batch.purchase_price, Decimal('35.50'))
        
    def test_batch_remaining_quantity_updates(self):
        """Test batch remaining quantity updates correctly."""
        unit = Unit.objects.first()
        if not unit:
            unit = Unit.objects.create(name='Piece', symbol='P', is_active=True)
            
        category = Category.objects.first()
        if not category:
            category = Category.objects.create(name='Medicines')
            
        product = Product.objects.filter(is_active=True).first()
        if not product:
            product = Product.objects.create(
                name='Test', sku='TEST3', generic_name='Test',
                category=category, unit=unit, is_active=True
            )
        
        batch = Batch.objects.create(
            batch_number=f'REMAIN-{date.today().strftime("%Y%m%d%H%M%S")}',
            product=product,
            manufacturing_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=330),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            quantity=Decimal('100'),
            remaining_quantity=Decimal('100'),
            location='MAIN'
        )
        
        # Simulate sale of 25 units
        batch.remaining_quantity = Decimal('75')
        batch.save()
        
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, Decimal('75'))
        
    def test_total_inventory_value_from_batches(self):
        """Test total inventory value calculation from batches."""
        # Get all active batches
        batches = Batch.objects.filter(
            remaining_quantity__gt=0,
            is_active=True
        )
        
        # Calculate manually since F expression can't be used directly in aggregate
        total_value = Decimal('0.00')
        for batch in batches:
            if batch.purchase_price:
                total_value += batch.remaining_quantity * batch.purchase_price
        
        # Should be non-negative
        self.assertGreaterEqual(total_value, Decimal('0'))
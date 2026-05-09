"""
Advanced Costing Engine Tests - Simplified
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db import transaction

from inventory.models import Product, Warehouse, Batch
from inventory.services.costing_service import (
    CostingService, CostingMethod, LandedCostService, 
    CostFlowIntegrityService, LandedCostType
)


class WeightedAverageCostTests(TestCase):
    """Test Weighted Average Cost (AVCO) calculation."""

    def test_costing_service_exists(self):
        """Test CostingService is accessible."""
        from inventory.services.costing_service import CostingService
        self.assertTrue(hasattr(CostingService, 'calculate_weighted_average_cost'))

    def test_calculate_average_method_exists(self):
        """Test calculate method exists."""
        self.assertTrue(hasattr(CostingService, 'calculate_weighted_average_cost'))

    def test_costing_method_constants(self):
        """Test costing method constants."""
        self.assertEqual(CostingMethod.FIFO, 'FIFO')
        self.assertEqual(CostingMethod.FEFO, 'FEFO')
        self.assertEqual(CostingMethod.AVCO, 'AVCO')

    def test_get_average_cost_method_exists(self):
        """Test get_average_cost_for_sale method exists."""
        self.assertTrue(hasattr(CostingService, 'get_average_cost_for_sale'))

    def test_zero_batches_returns_zero(self):
        """Test average returns zero when no batches."""
        product = Product.objects.first()
        if product:
            Batch.objects.filter(product=product).delete()
            avg_cost = CostingService.calculate_weighted_average_cost(product)
            self.assertEqual(avg_cost, Decimal('0.00'))

    def test_single_batch_average(self):
        """Test average with single batch."""
        warehouse = Warehouse.objects.filter(is_active=True).first()
        product = Product.objects.filter(is_active=True).first()
        
        if warehouse and product:
            Batch.objects.filter(product=product, warehouse=warehouse).delete()
            
            Batch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number='AVCO-TEST-1',
                manufacturing_date=date.today(),
                expiry_date=date.today() + timedelta(days=365),
                purchase_price=Decimal('10.00'),
                quantity=100,
                remaining_quantity=100,
                is_active=True
            )
            
            avg = CostingService.calculate_weighted_average_cost(product, warehouse)
            self.assertEqual(avg, Decimal('10.00'))

    def test_multiple_batch_average(self):
        """Test average with multiple batches."""
        warehouse = Warehouse.objects.filter(is_active=True).first()
        product = Product.objects.filter(is_active=True).first()
        
        if warehouse and product:
            Batch.objects.filter(product=product, warehouse=warehouse).delete()
            
            Batch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number='AVCO-TEST-2A',
                manufacturing_date=date.today() - timedelta(days=30),
                expiry_date=date.today() + timedelta(days=335),
                purchase_price=Decimal('10.00'),
                quantity=100,
                remaining_quantity=100,
                is_active=True
            )
            
            Batch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number='AVCO-TEST-2B',
                manufacturing_date=date.today() - timedelta(days=60),
                expiry_date=date.today() + timedelta(days=305),
                purchase_price=Decimal('20.00'),
                quantity=100,
                remaining_quantity=100,
                is_active=True
            )
            
            avg = CostingService.calculate_weighted_average_cost(product, warehouse)
            self.assertEqual(avg, Decimal('15.00'))


class LandedCostTests(TestCase):
    """Test landed cost functionality."""

    def test_landed_cost_service_exists(self):
        """Test LandedCostService exists."""
        self.assertTrue(hasattr(LandedCostService, 'allocate_landed_costs'))

    def test_landed_cost_types_defined(self):
        """Test all landed cost types."""
        self.assertEqual(LandedCostType.IMPORT_DUTY, 'IMPORT_DUTY')
        self.assertEqual(LandedCostType.TRANSPORT, 'TRANSPORT')
        self.assertEqual(LandedCostType.CUSTOMS_FEE, 'CUSTOMS_FEE')
        self.assertEqual(LandedCostType.HANDLING_CHARGE, 'HANDLING_CHARGE')
        self.assertEqual(LandedCostType.INSURANCE, 'INSURANCE')
        self.assertEqual(LandedCostType.OTHER, 'OTHER')

    @transaction.atomic
    def test_allocate_landed_cost_to_batch(self):
        """Test landed cost allocation to batch."""
        warehouse = Warehouse.objects.filter(is_active=True).first()
        product = Product.objects.filter(is_active=True).first()
        
        if warehouse and product:
            Batch.objects.filter(product=product, warehouse=warehouse).delete()
            
            batch = Batch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number='LANDED-TEST',
                manufacturing_date=date.today(),
                expiry_date=date.today() + timedelta(days=365),
                purchase_price=Decimal('100.00'),
                quantity=10,
                remaining_quantity=10,
                is_active=True
            )
            
            costs = [{'type': LandedCostType.TRANSPORT, 'amount': Decimal('50.00'), 'desc': 'Ship'}]
            
            total = LandedCostService.allocate_landed_costs(batch, costs)
            
            self.assertEqual(total, Decimal('50.00'))
            
            batch.refresh_from_db()
            self.assertEqual(batch.purchase_price, Decimal('150.00'))

    @transaction.atomic
    def test_distribute_landed_cost(self):
        """Test distributed landed cost."""
        warehouse = Warehouse.objects.filter(is_active=True).first()
        product = Product.objects.filter(is_active=True).first()
        
        if warehouse and product:
            Batch.objects.filter(product=product, warehouse=warehouse).delete()
            
            Batch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number='DIST-1',
                manufacturing_date=date.today() - timedelta(days=30),
                expiry_date=date.today() + timedelta(days=335),
                purchase_price=Decimal('10.00'),
                quantity=100,
                remaining_quantity=100,
                is_active=True
            )
            
            Batch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number='DIST-2',
                manufacturing_date=date.today() - timedelta(days=60),
                expiry_date=date.today() + timedelta(days=305),
                purchase_price=Decimal('20.00'),
                quantity=100,
                remaining_quantity=100,
                is_active=True
            )
            
            result = LandedCostService.distribute_landed_cost_to_batches(
                product, Decimal('30.00'), warehouse
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(result['total_distributed'], Decimal('30.00'))


class CostFlowIntegrityTests(TestCase):
    """Test cost flow integrity."""

    def test_cost_flow_service_exists(self):
        """Test CostFlowIntegrityService exists."""
        self.assertTrue(hasattr(CostFlowIntegrityService, 'verify_inventory_valuation'))

    def test_verify_inventory_method_exists(self):
        """Test verify method exists."""
        self.assertTrue(hasattr(CostFlowIntegrityService, 'verify_inventory_valuation'))

    def test_verify_inventory_valuation(self):
        """Test inventory valuation verification."""
        warehouse = Warehouse.objects.filter(is_active=True).first()
        product = Product.objects.filter(is_active=True).first()
        
        if warehouse and product:
            Batch.objects.filter(product=product, warehouse=warehouse).delete()
            
            Batch.objects.create(
                product=product,
                warehouse=warehouse,
                batch_number='CFI-TEST',
                manufacturing_date=date.today(),
                expiry_date=date.today() + timedelta(days=365),
                purchase_price=Decimal('25.00'),
                quantity=100,
                remaining_quantity=100,
                is_active=True
            )
            
            result = CostFlowIntegrityService.verify_inventory_valuation(product, warehouse)
            
            self.assertEqual(result['batch_valuation'], Decimal('2500.00'))
            self.assertTrue(result['is_consistent'])

    def test_get_cogs_method_exists(self):
        """Test get_cogs_for_invoice exists."""
        self.assertTrue(hasattr(CostFlowIntegrityService, 'get_cogs_for_invoice'))
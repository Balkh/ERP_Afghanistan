"""
Enterprise tests for StockIntegrationService - Complete.
Tests: FEFO/FIFO allocation, warehouse isolation, transactional safety, inventory valuation.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase

from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from inventory.service.stock_integration import StockIntegrationService
from inventory.service import StockSelectionMode


class StockFEFOAllocationTest(TransactionTestCase):
    """Test First Expiry First Out allocation - enterprise critical."""

    def setUp(self):
        self.cat = Category.objects.create(name='Medicines', is_active=True)
        self.unit = Unit.objects.create(name='Box', symbol='BX', is_active=True)
        self.prod = Product.objects.create(name='Panadol Extra', sku='PANEXTRA', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='Main Pharmacy', code='PH01', is_active=True)

    def test_fefo_selects_earliest_expiry(self):
        """FEFO must select batch with earliest expiry date."""
        # Create batch expiring LATER
        Batch.objects.create(
            product=self.prod, batch_number='B-LATE', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('8.00'), sale_price=Decimal('12.00'),
            expiry_date=date.today() + timedelta(days=400),
            manufacturing_date=date.today() - timedelta(days=30),
            location=str(self.wh.id), is_active=True
        )
        # Create batch expiring EARLIER (should be selected first)
        Batch.objects.create(
            product=self.prod, batch_number='B-EARLY', quantity=80, remaining_quantity=80,
            purchase_price=Decimal('8.00'), sale_price=Decimal('12.00'),
            expiry_date=date.today() + timedelta(days=100),
            manufacturing_date=date.today() - timedelta(days=60),
            location=str(self.wh.id), is_active=True
        )

        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('50'), self.wh, StockSelectionMode.FEFO
        )
        self.assertTrue(result.success)
        self.assertEqual(result.allocations[0].batch_number, 'B-EARLY')

    def test_fefo_partial_allocation_multiple_batches(self):
        """FEFO should split allocation across multiple batches when first is insufficient."""
        Batch.objects.create(
            product=self.prod, batch_number='B001', quantity=30, remaining_quantity=30,
            purchase_price=Decimal('5.00'), sale_price=Decimal('8.00'),
            expiry_date=date.today() + timedelta(days=150),
            manufacturing_date=date.today(),
            location=str(self.wh.id), is_active=True
        )
        Batch.objects.create(
            product=self.prod, batch_number='B002', quantity=50, remaining_quantity=50,
            purchase_price=Decimal('5.00'), sale_price=Decimal('8.00'),
            expiry_date=date.today() + timedelta(days=200),
            manufacturing_date=date.today(),
            location=str(self.wh.id), is_active=True
        )

        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('70'), self.wh, StockSelectionMode.FEFO
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 2)
        self.assertEqual(result.allocations[0].quantity, Decimal('30'))
        self.assertEqual(result.allocations[1].quantity, Decimal('40'))


class StockFIFOAllocationTest(TransactionTestCase):
    """Test First In First Out allocation."""

    def setUp(self):
        self.cat = Category.objects.create(name='Syrups', is_active=True)
        self.unit = Unit.objects.create(name='Bottle', symbol='BTL', is_active=True)
        self.prod = Product.objects.create(name='Benadryl Syrup', sku='BENSYRUP', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='Store Room', code='SR01', is_active=True)

    def test_fifo_selects_oldest_manufacturing(self):
        """FIFO must select batch with earliest manufacturing date."""
        # Create newer batch
        Batch.objects.create(
            product=self.prod, batch_number='B-NEW', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
            expiry_date=date.today() + timedelta(days=300),
            manufacturing_date=date.today(),
            location=str(self.wh.id), is_active=True
        )
        # Create older batch (should be selected first)
        Batch.objects.create(
            product=self.prod, batch_number='B-OLD', quantity=80, remaining_quantity=80,
            purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
            expiry_date=date.today() + timedelta(days=350),
            manufacturing_date=date.today() - timedelta(days=90),
            location=str(self.wh.id), is_active=True
        )

        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('50'), self.wh, StockSelectionMode.FIFO
        )
        self.assertTrue(result.success)
        self.assertEqual(result.allocations[0].batch_number, 'B-OLD')


class StockWarehouseIsolationTest(TransactionTestCase):
    """Test warehouse isolation - critical for multi-warehouse safety."""

    def setUp(self):
        self.cat = Category.objects.create(name='General', is_active=True)
        self.unit = Unit.objects.create(name='Pack', symbol='PK', is_active=True)
        self.prod = Product.objects.create(name='Generic Drug', sku='GENDRUG', category=self.cat, unit=self.unit, is_active=True)
        self.wh1 = Warehouse.objects.create(name='Warehouse A', code='WA01', is_active=True)
        self.wh2 = Warehouse.objects.create(name='Warehouse B', code='WB01', is_active=True)

    def test_allocation_respects_warehouse(self):
        """Stock allocation must only use batches from specified warehouse."""
        Batch.objects.create(
            product=self.prod, batch_number='B-WA1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('5.00'), sale_price=Decimal('8.00'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=date.today(),
            location=str(self.wh1.id), is_active=True
        )
        Batch.objects.create(
            product=self.prod, batch_number='B-WB1', quantity=50, remaining_quantity=50,
            purchase_price=Decimal('5.00'), sale_price=Decimal('8.00'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=date.today(),
            location=str(self.wh2.id), is_active=True
        )

        # Allocate from warehouse A only
        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('80'), self.wh1
        )
        self.assertTrue(result.success)
        self.assertEqual(result.allocations[0].batch_number, 'B-WA1')

    def test_allocation_fails_when_insufficient_in_warehouse(self):
        """Allocation must fail when stock is insufficient in specified warehouse."""
        Batch.objects.create(
            product=self.prod, batch_number='B-WA2', quantity=30, remaining_quantity=30,
            purchase_price=Decimal('5.00'), sale_price=Decimal('8.00'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=date.today(),
            location=str(self.wh1.id), is_active=True
        )

        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('100'), self.wh1
        )
        self.assertFalse(result.success)
        self.assertIn('Insufficient', result.message)


class StockInsufficiencyTest(TransactionTestCase):
    """Test allocation with insufficient stock - transactional safety."""

    def setUp(self):
        self.cat = Category.objects.create(name='Test', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='Test Product', sku='TESTPROD', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='TestWH', code='TW01', is_active=True)

    def test_allocation_fails_with_shortage_details(self):
        """Allocation must fail with accurate shortage information."""
        Batch.objects.create(
            product=self.prod, batch_number='B-SMALL', quantity=25, remaining_quantity=25,
            purchase_price=Decimal('3.00'), sale_price=Decimal('5.00'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=date.today(),
            location=str(self.wh.id), is_active=True
        )

        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('100'), self.wh
        )
        self.assertFalse(result.success)
        self.assertTrue(len(result.stock_shortages) > 0)
        self.assertEqual(result.stock_shortages[0]['shortage'], Decimal('75'))


class StockMovementCreationTest(TransactionTestCase):
    """Test stock movement creation for audit trail."""

    def setUp(self):
        self.cat = Category.objects.create(name='Cream', is_active=True)
        self.unit = Unit.objects.create(name='Tube', symbol='TUB', is_active=True)
        self.prod = Product.objects.create(name='Hydrocortisone', sku='HYDCRT', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='Dispensing', code='DP01', is_active=True)

    def test_create_movement_in_creates_audit_trail(self):
        """Stock IN movement creates proper audit trail."""
        movement = StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='IN',
            reference_type='PURCHASE',
            reference_id='PO-2024-001',
            quantity=Decimal('100'),
            unit_cost=Decimal('5.50'),
            notes='Purchase order received'
        )
        self.assertIsNotNone(movement.id)
        self.assertEqual(movement.movement_type, 'IN')
        self.assertEqual(movement.reference_type, 'PURCHASE')
        self.assertEqual(movement.quantity, Decimal('100'))

    def test_create_movement_out_creates_audit_trail(self):
        """Stock OUT movement creates proper audit trail."""
        movement = StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='OUT',
            reference_type='SALE',
            reference_id='INV-2024-001',
            quantity=Decimal('-10'),
            unit_cost=Decimal('5.50'),
            notes='Sales invoice fulfilled'
        )
        self.assertIsNotNone(movement.id)
        self.assertEqual(movement.movement_type, 'OUT')
        self.assertEqual(movement.reference_type, 'SALE')

    def test_movement_links_to_correct_warehouse(self):
        """Stock movement links to correct warehouse."""
        movement = StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='IN',
            reference_type='PURCHASE',
            reference_id='PO-001',
            quantity=Decimal('50'),
            unit_cost=Decimal('5.00'),
            notes='Test'
        )
        self.assertEqual(str(movement.warehouse), str(self.wh))


class StockValuationTest(TransactionTestCase):
    """Test inventory valuation consistency."""

    def setUp(self):
        self.cat = Category.objects.create(name='Tablets', is_active=True)
        self.unit = Unit.objects.create(name='Box', symbol='BX', is_active=True)
        self.prod = Product.objects.create(name='Antibiotic', sku='ABT500', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='Pharmacy', code='PH01', is_active=True)

    def test_inventory_valuation_uses_purchase_price(self):
        """Inventory valuation must use purchase price from batch."""
        Batch.objects.create(
            product=self.prod, batch_number='B-VAL1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('7.50'), sale_price=Decimal('12.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(),
            location=str(self.wh.id), is_active=True
        )

        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('10'), self.wh
        )
        self.assertTrue(result.success)
        self.assertEqual(result.allocations[0].unit_cost, Decimal('7.50'))

    def test_total_available_stock_calculation(self):
        """Total available stock sums all batch quantities correctly."""
        Batch.objects.create(
            product=self.prod, batch_number='B-VAL2', quantity=150, remaining_quantity=150,
            purchase_price=Decimal('7.50'), sale_price=Decimal('12.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(),
            location=str(self.wh.id), is_active=True
        )
        Batch.objects.create(
            product=self.prod, batch_number='B-VAL3', quantity=75, remaining_quantity=75,
            purchase_price=Decimal('7.50'), sale_price=Decimal('12.00'),
            expiry_date=date.today() + timedelta(days=400),
            manufacturing_date=date.today(),
            location=str(self.wh.id), is_active=True
        )

        total = StockIntegrationService.get_total_available_stock(self.prod, self.wh)
        self.assertEqual(total, Decimal('225'))
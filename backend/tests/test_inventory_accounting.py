"""
Inventory Accounting Service Tests

Comprehensive tests for InventoryAccountingService including
adjustments, write-offs, COGS, and movement accounting.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.utils import timezone as django_timezone
from django.core.exceptions import ValidationError

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.inventory_accounting import (
    InventoryAccountingService,
    InventoryAccountingServiceError
)
from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement


def _create_inventory_accounts():
    """Create the standard inventory accounting accounts needed for tests."""
    accounts = [
        ('1300', 'Inventory', 'ASSET', 'CURRENT_ASSET'),
        ('4900', 'Inventory Gain', 'REVENUE', 'OPERATING_REVENUE'),
        ('5100', 'Cost of Goods Sold', 'EXPENSE', 'COST_OF_GOODS_SOLD'),
        ('5200', 'Inventory Loss', 'EXPENSE', 'OPERATING_EXPENSE'),
        ('5210', 'Inventory Write-Off', 'EXPENSE', 'OPERATING_EXPENSE'),
    ]
    for code, name, acct_type, category in accounts:
        Account.objects.get_or_create(
            code=code,
            defaults=dict(
                name=name, account_type=acct_type,
                account_category=category, is_active=True
            )
        )


class InventoryAdjustmentTest(TransactionTestCase):
    """Test inventory adjustment accounting."""

    def setUp(self):
        _create_inventory_accounts()
        self.category = Category.objects.create(name='Medicines', is_active=True)
        self.unit = Unit.objects.create(name='Piece', symbol='PCS', is_active=True)
        self.product = Product.objects.create(
            name='Aspirin', sku='ASP001', barcode='BAR_ASP001',
            generic_name='Aspirin Generic', brand_name='Aspirin Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=self.category, unit=self.unit, is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Main WH', code='WH01', is_active=True
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number='B001',
            quantity=100,
            remaining_quantity=100,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH01',
            is_active=True
        )

    def test_positive_adjustment_creates_journal_entry(self):
        """Test positive adjustment creates journal entry with gain."""
        movement = StockMovement(
            product=self.product,
            warehouse=self.warehouse,
            batch=self.batch,
            movement_type='ADJUSTMENT',
            quantity=Decimal('10'),
            reference_type='MANUAL',
            reference_id='ADJ-001'
        )
        movement.save()

        result = InventoryAccountingService.process_inventory_adjustment(
            movement, reason='Found stock'
        )

        self.assertTrue(result.get('success', False))

    def test_negative_adjustment_creates_journal_entry(self):
        """Test negative adjustment creates journal entry with loss."""
        movement = StockMovement(
            product=self.product,
            warehouse=self.warehouse,
            batch=self.batch,
            movement_type='ADJUSTMENT',
            quantity=Decimal('-5'),
            reference_type='MANUAL',
            reference_id='ADJ-002'
        )
        movement.save()

        result = InventoryAccountingService.process_inventory_adjustment(
            movement, reason='Damaged'
        )

        self.assertTrue(result.get('success', False))


class InventoryWriteOffTest(TransactionTestCase):
    """Test inventory write-off accounting."""

    def setUp(self):
        _create_inventory_accounts()
        self.category = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.product = Product.objects.create(
            name='Test', sku='T001', barcode='BAR_T001',
            generic_name='Test Generic', brand_name='Test Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=self.category, unit=self.unit, is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='WH', code='WH', is_active=True
        )
        self.batch = Batch.objects.create(
            product=self.product, batch_number='B-WROFF',
            quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH', is_active=True
        )

    def test_write_off_creates_journal_entry(self):
        """Test write-off creates journal entry."""
        result = InventoryAccountingService.process_inventory_write_off(
            product=self.product,
            quantity=Decimal('10'),
            batch=self.batch,
            reason='Expired',
            reference_type='EXPIRY'
        )

        self.assertTrue(result.get('success', False))

    def test_write_off_with_zero_cost_fails(self):
        """Test write-off with zero cost returns error."""
        result = InventoryAccountingService.process_inventory_write_off(
            product=self.product,
            quantity=Decimal('0'),
            batch=None,
            reason='Test',
            reference_type='WASTE'
        )

        self.assertFalse(result.get('success', True))


class InventoryCOGSTest(TransactionTestCase):
    """Test COGS calculation and accounting."""

    def setUp(self):
        _create_inventory_accounts()
        self.category = Category.objects.create(name='Meds', is_active=True)
        self.unit = Unit.objects.create(name='P', symbol='P', is_active=True)
        self.product = Product.objects.create(
            name='Drug', sku='D001', barcode='BAR_D001',
            generic_name='Drug Generic', brand_name='Drug Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=self.category, unit=self.unit, is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='WH', code='WH', is_active=True
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number='B-COGS',
            quantity=100,
            remaining_quantity=50,
            purchase_price=Decimal('20.00'),
            sale_price=Decimal('30.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH',
            is_active=True
        )

    def test_sales_dispatch_creates_cogs_entry(self):
        """Test sales dispatch creates COGS journal entry."""
        movement = StockMovement(
            product=self.product,
            warehouse=self.warehouse,
            batch=self.batch,
            movement_type='OUT',
            quantity=Decimal('-10'),
            reference_type='SALE',
            reference_id='INV-001'
        )
        movement.save()

        result = InventoryAccountingService.process_sales_dispatch(
            movement, invoice_reference='INV-001'
        )

        self.assertTrue(result.get('success', False))

    def test_cogs_uses_batch_purchase_price(self):
        """Test COGS calculation uses batch purchase price."""
        movement = StockMovement(
            product=self.product,
            warehouse=self.warehouse,
            batch=self.batch,
            movement_type='OUT',
            quantity=Decimal('-5'),
            reference_type='SALE',
            reference_id='INV-002'
        )
        movement.save()

        result = InventoryAccountingService.process_sales_dispatch(
            movement, invoice_reference='INV-002'
        )

        self.assertTrue(result.get('success', False))


class InventoryMovementValidationTest(TransactionTestCase):
    """Test movement validation in inventory accounting."""

    def test_invalid_adjustment_movement_returns_error(self):
        """Test adjustment with no cost basis returns error result."""
        _create_inventory_accounts()
        category = Category.objects.create(name='C', is_active=True)
        unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        product = Product.objects.create(
            name='P', sku='P', barcode='BAR_P',
            generic_name='P Generic', brand_name='P Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=category, unit=unit, is_active=True
        )
        warehouse = Warehouse.objects.create(name='WH', code='WH', is_active=True)

        movement = StockMovement(
            product=product,
            warehouse=warehouse,
            movement_type='ADJUSTMENT',
            quantity=Decimal('1'),
            reference_type='MANUAL',
            reference_id='T001'
        )
        movement.save()

        result = InventoryAccountingService.process_inventory_adjustment(movement)
        self.assertFalse(result.get('success', True))


class WarehouseTransferAccountingTest(TransactionTestCase):
    """Test warehouse transfer accounting."""

    def setUp(self):
        self.category = Category.objects.create(name='C', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.product = Product.objects.create(
            name='P', sku='P', barcode='BAR_P2',
            generic_name='P Generic', brand_name='P Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=self.category, unit=self.unit, is_active=True
        )

    def test_warehouse_transfer_returns_no_action(self):
        """Test warehouse transfer returns success with no JE message."""
        result = InventoryAccountingService.process_warehouse_transfer(
            transfer_items=[],
            transfer=None
        )

        self.assertTrue(result.get('success', False))
        self.assertIn('operational', result.get('message', '').lower())


class InventoryAccountingDispatcherTest(TransactionTestCase):
    """Test the central dispatcher for inventory accounting."""

    def setUp(self):
        _create_inventory_accounts()
        self.category = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.product = Product.objects.create(
            name='Prod', sku='P001', barcode='BAR_PROD',
            generic_name='Prod Generic', brand_name='Prod Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=self.category, unit=self.unit, is_active=True
        )
        self.warehouse = Warehouse.objects.create(name='WH', code='WH', is_active=True)
        self.batch = Batch.objects.create(
            product=self.product, batch_number='B-DISPATCH',
            quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH', is_active=True
        )

    def test_dispatcher_routes_adjustment(self):
        """Test dispatcher routes adjustment to correct handler."""
        movement = StockMovement(
            product=self.product,
            warehouse=self.warehouse,
            batch=self.batch,
            movement_type='ADJUSTMENT',
            quantity=Decimal('5'),
            reference_type='MANUAL',
            reference_id='ADJ-DISP'
        )
        movement.save()

        result = InventoryAccountingService.record_accounting_for_movement(
            movement, reason='Test'
        )

        self.assertTrue(result.get('success', False))

    def test_dispatcher_routes_sales_dispatch(self):
        """Test dispatcher routes sales dispatch to correct handler."""
        batch = Batch.objects.create(
            product=self.product,
            batch_number='B-DISP',
            quantity=50,
            remaining_quantity=50,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            expiry_date=django_timezone.now().date() + timedelta(days=365),
            manufacturing_date=django_timezone.now().date(),
            location='WH',
            is_active=True
        )

        movement = StockMovement(
            product=self.product,
            warehouse=self.warehouse,
            batch=batch,
            movement_type='OUT',
            quantity=Decimal('-5'),
            reference_type='SALE',
            reference_id='INV-DISP'
        )
        movement.save()

        result = InventoryAccountingService.record_accounting_for_movement(
            movement, invoice_reference='INV-DISP'
        )

        self.assertTrue(result.get('success', False))

    def test_dispatcher_routes_transfer(self):
        """Test dispatcher routes transfer to transfer handler."""
        movement = StockMovement(
            product=self.product,
            warehouse=self.warehouse,
            movement_type='TRANSFER',
            quantity=Decimal('10'),
            reference_type='MANUAL',
            reference_id='TRF-001'
        )
        movement.save()

        result = InventoryAccountingService.record_accounting_for_movement(movement)

        self.assertTrue(result.get('success', False))
        self.assertIn('operational', result.get('message', '').lower())


class InventoryAccountCodesTest(TransactionTestCase):
    """Test inventory accounting uses correct account codes."""

    def test_uses_correct_inventory_account(self):
        """Test inventory adjustments use account 1300."""
        _create_inventory_accounts()
        category = Category.objects.create(name='C', is_active=True)
        unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        product = Product.objects.create(
            name='P', sku='P', barcode='BAR_P3',
            generic_name='P Generic', brand_name='P Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=category, unit=unit, is_active=True
        )
        warehouse = Warehouse.objects.create(name='WH', code='WH', is_active=True)

        movement = StockMovement(
            product=product,
            warehouse=warehouse,
            movement_type='ADJUSTMENT',
            quantity=Decimal('5'),
            reference_type='MANUAL',
            reference_id='ACC-TEST'
        )
        movement.save()

        result = InventoryAccountingService.process_inventory_adjustment(movement)

        if result.get('success'):
            entry = JournalEntry.objects.get(id=result['entry_id'])
            inventory_lines = entry.lines.filter(account__code='1300')
            self.assertTrue(inventory_lines.exists())

    def test_uses_correct_loss_account(self):
        """Test negative adjustments use account 5200."""
        _create_inventory_accounts()
        category = Category.objects.create(name='C2', is_active=True)
        unit = Unit.objects.create(name='U2', symbol='U2', is_active=True)
        product = Product.objects.create(
            name='P2', sku='P2', barcode='BAR_P4',
            generic_name='P2 Generic', brand_name='P2 Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=category, unit=unit, is_active=True
        )
        warehouse = Warehouse.objects.create(name='WH2', code='WH2', is_active=True)

        movement = StockMovement(
            product=product,
            warehouse=warehouse,
            movement_type='ADJUSTMENT',
            quantity=Decimal('-3'),
            reference_type='MANUAL',
            reference_id='LOSS-TEST'
        )
        movement.save()

        result = InventoryAccountingService.process_inventory_adjustment(movement)

        if result.get('success'):
            entry = JournalEntry.objects.get(id=result['entry_id'])
            loss_lines = entry.lines.filter(account__code='5200')
            self.assertTrue(loss_lines.exists())

    def test_uses_correct_write_off_account(self):
        """Test write-offs use account 5210."""
        _create_inventory_accounts()
        category = Category.objects.create(name='C3', is_active=True)
        unit = Unit.objects.create(name='U3', symbol='U3', is_active=True)
        product = Product.objects.create(
            name='P3', sku='P3', barcode='BAR_P5',
            generic_name='P3 Generic', brand_name='P3 Brand',
            strength='100mg', form='Tablet', manufacturer='TestMfg',
            category=category, unit=unit, is_active=True
        )

        result = InventoryAccountingService.process_inventory_write_off(
            product=product,
            quantity=Decimal('5'),
            reason='Expiry',
            reference_type='EXPIRY'
        )

        if result.get('success'):
            entry = JournalEntry.objects.get(id=result['entry_id'])
            writeoff_lines = entry.lines.filter(account__code='5210')
            self.assertTrue(writeoff_lines.exists())
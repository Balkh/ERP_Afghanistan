"""
Tests for Warehouse Transfer feature (Phase 5).
"""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from inventory.models import Warehouse, Product, Batch, WarehouseTransfer, WarehouseTransferItem
from inventory.service.transfer_service import process_transfer

User = get_user_model()


class WarehouseTransferTests(APITestCase):
    """Tests for the warehouse transfer functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='transferuser',
            password='TransferPass123!'
        )
        # Create warehouses
        self.source = Warehouse.objects.create(
            name='Source Warehouse',
            code='SRC001',
            is_default=False
        )
        self.destination = Warehouse.objects.create(
            name='Destination Warehouse',
            code='DST001',
            is_default=False
        )
        # Create product
        from inventory.models import Category, Unit
        self.category = Category.objects.create(name='Test Category')
        self.unit = Unit.objects.create(name='Tablet', symbol='TAB')
        self.product = Product.objects.create(
            name='Test Product',
            generic_name='Test Generic',
            brand_name='Test Brand',
            category=self.category,
            unit=self.unit,
            strength='500mg',
            form='Tablet',
            manufacturer='Test Mfg',
            barcode='TEST123',
            sku='TEST-SKU',
            is_active=True
        )
        # Create batch in source warehouse
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number='BATCH-001',
            manufacturing_date=timezone.now().date() - timedelta(days=30),
            expiry_date=timezone.now().date() + timedelta(days=365),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            location=str(self.source.id),
            is_active=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_transfer(self):
        """Test creating a warehouse transfer."""
        transfer = WarehouseTransfer.objects.create(
            transfer_number='TRF-001',
            source_warehouse=self.source,
            destination_warehouse=self.destination,
            status='PENDING',
            transfer_date=timezone.now().date(),
            created_by=self.user
        )
        self.assertEqual(transfer.status, 'PENDING')
        self.assertEqual(transfer.source_warehouse, self.source)
        self.assertEqual(transfer.destination_warehouse, self.destination)

    def test_transfer_cannot_have_same_source_and_dest(self):
        """Test transfer fails if source and destination are the same."""
        transfer = WarehouseTransfer(
            transfer_number='TRF-002',
            source_warehouse=self.source,
            destination_warehouse=self.source,  # Same warehouse
            status='PENDING',
            transfer_date=timezone.now().date(),
            created_by=self.user
        )
        with self.assertRaises(Exception):
            transfer.save()

    def test_process_transfer_success(self):
        """Test successful transfer processing."""
        # Create transfer
        transfer = WarehouseTransfer.objects.create(
            transfer_number='TRF-003',
            source_warehouse=self.source,
            destination_warehouse=self.destination,
            status='PENDING',
            transfer_date=timezone.now().date(),
            created_by=self.user
        )
        # Add item
        item = WarehouseTransferItem.objects.create(
            transfer=transfer,
            product=self.product,
            batch=self.batch,
            quantity=Decimal('50.00')
        )
        # Process transfer
        result = process_transfer(
            transfer_id=transfer.id,
            items=[{
                'product': self.product.id,
                'quantity': Decimal('50.00'),
                'batch_id': self.batch.id
            }]
        )
        self.assertTrue(result.success)
        
        # After transferring 50 from 100, remaining should be 50
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.remaining_quantity, Decimal('50.00'))
        
        # Check transfer status updated to COMPLETED
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, 'COMPLETED')

    def test_process_transfer_insufficient_stock(self):
        """Test transfer fails with insufficient stock."""
        transfer = WarehouseTransfer.objects.create(
            transfer_number='TRF-004',
            source_warehouse=self.source,
            destination_warehouse=self.destination,
            status='PENDING',
            transfer_date=timezone.now().date(),
            created_by=self.user
        )
        result = process_transfer(
            transfer_id=transfer.id,
            items=[{
                'product': self.product.id,
                'quantity': Decimal('999.00'),  # More than available
                'batch_id': self.batch.id
            }]
        )
        self.assertFalse(result.success)
        self.assertIn('Insufficient stock', ' '.join(result.errors))

    def test_transfer_item_str(self):
        """Test string representation of transfer item."""
        transfer = WarehouseTransfer.objects.create(
            transfer_number='TRF-005',
            source_warehouse=self.source,
            destination_warehouse=self.destination,
            status='PENDING',
            transfer_date=timezone.now().date(),
            created_by=self.user
        )
        item = WarehouseTransferItem.objects.create(
            transfer=transfer,
            product=self.product,
            batch=self.batch,
            quantity=Decimal('25.00')
        )
        self.assertIn('TRF-005', str(item))
        self.assertIn(self.product.name, str(item))

    def test_transfer_status_choices(self):
        """Test transfer status field accepts valid choices."""
        for status_choice, _ in WarehouseTransfer.STATUS_CHOICES:
            transfer = WarehouseTransfer.objects.create(
                transfer_number=f'TRF-{status_choice}',
                source_warehouse=self.source,
                destination_warehouse=self.destination,
                status=status_choice,
                transfer_date=timezone.now().date(),
                created_by=self.user
            )
            self.assertEqual(transfer.status, status_choice)
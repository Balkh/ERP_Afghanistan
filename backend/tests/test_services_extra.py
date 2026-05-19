"""
Additional services tests to target low-coverage areas.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import TransactionTestCase

from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from inventory.service.stock_integration import StockIntegrationService
from accounting.models import Account
from accounting.services.journal_engine import JournalEngine


class StockIntegrationServiceTest(TransactionTestCase):
    """Test StockIntegrationService methods."""

    def setUp(self):
        self.cat = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='P', sku='P', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='WH', code='WH', is_active=True)

    def test_stock_integration_service_exists(self):
        """Test StockIntegrationService exists."""
        self.assertTrue(hasattr(StockIntegrationService, 'get_available_batches'))

    def test_stock_integration_allocate_exists(self):
        """Test allocate_stock method exists."""
        self.assertTrue(hasattr(StockIntegrationService, 'allocate_stock'))


class JournalEngineAdditionalTest(TransactionTestCase):
    """Additional JournalEngine tests."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='2000', name='Payable', account_type='LIABILITY', is_active=True)

    def test_validate_lines_balanced(self):
        """Test validate_lines accepts balanced entry."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'},
            {'account_id': str(self.a2.id), 'debit': '0', 'credit': '100'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertEqual(len(errors), 0)

    def test_validate_lines_unbalanced(self):
        """Test validate_lines rejects unbalanced entry."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'},
            {'account_id': str(self.a2.id), 'debit': '0', 'credit': '75'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertGreater(len(errors), 0)

    def test_validate_lines_single_line(self):
        """Test validate_lines rejects single line."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'}
        ]
        errors = JournalEngine.validate_lines(lines)
        self.assertGreater(len(errors), 0)


class StockMovementTypeTest(TransactionTestCase):
    """Test stock movement type operations."""

    def setUp(self):
        self.cat = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='P', sku='P', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='WH', code='WH', is_active=True)
        self.batch = Batch.objects.create(
            product=self.prod, batch_number='B1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location='WH', is_active=True
        )

    def test_batch_quantity_update(self):
        """Test batch quantity update."""
        self.batch.remaining_quantity = Decimal('75')
        self.batch.save()
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.remaining_quantity, Decimal('75'))

    def test_multiple_batches_query(self):
        """Test multiple batches can be queried."""
        Batch.objects.create(
            product=self.prod, batch_number='B2', quantity=50, remaining_quantity=50,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location='WH', is_active=True
        )

        batches = Batch.objects.filter(product=self.prod, is_active=True)
        self.assertEqual(batches.count(), 2)
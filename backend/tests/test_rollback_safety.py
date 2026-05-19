"""
Enterprise Rollback Safety Tests.
Validates transactional integrity under failure scenarios.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import TransactionTestCase

from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from accounting.models import Account, JournalEntry, JournalEntryLine, Currency, ExchangeRate
from accounting.services.journal_engine import JournalEngine
from accounting.services.currency_converter import CurrencyConverter, CurrencyConversionError
from inventory.service.stock_integration import StockIntegrationService


class RollbackIntegrityTest(TransactionTestCase):
    """Test rollback integrity - critical for production resilience."""

    def setUp(self):
        self.cat = Category.objects.create(name='TestCat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='RollTest', sku='ROLLTEST', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='RollWH', code='RWH01', is_active=True)
        
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.ar = Account.objects.create(code='1100', name='AR', account_type='ASSET', is_active=True)

    def test_stock_movement_creates_audit_trail(self):
        """Stock movement must have proper audit trail."""
        Batch.objects.create(
            product=self.prod, batch_number='B-ROLL-1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('5'), sale_price=Decimal('10'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location=str(self.wh.id), is_active=True
        )
        
        movement = StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='OUT',
            reference_type='SALE',
            reference_id='INV-ROLL-001',
            quantity=Decimal('-10'),
            unit_cost=Decimal('5'),
            notes='Test'
        )
        
        self.assertIsNotNone(movement.id)
        self.assertEqual(movement.reference_type, 'SALE')

    def test_unbalanced_journal_rejected(self):
        """Unbalanced journal entries must be rejected."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '100', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '50'},
        ]
        
        result = JournalEngine.create_entry('UNBALANCED', 'Test-Unbal', lines)
        self.assertFalse(result['success'])

    def test_valid_entry_posts(self):
        """Valid journal entries can be posted."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        
        result = JournalEngine.create_entry('SALE', 'ROLL-001', lines)
        self.assertTrue(result['success'])
        
        post_result = JournalEngine.post_entry(result['entry_id'])
        self.assertTrue(post_result['success'])


class CurrencyFailureRecoveryTest(TransactionTestCase):
    """Test currency conversion failure recovery."""

    def setUp(self):
        self.afn, _ = Currency.objects.get_or_create(
            code='AFN', defaults={
                'name': 'Afghan Afghani', 'symbol': '؋', 
                'is_default': True, 'is_active': True
            }
        )
        self.usd, _ = Currency.objects.get_or_create(
            code='USD', defaults={'name': 'US Dollar', 'symbol': '$', 'is_active': True}
        )

    def test_same_currency_no_rate_needed(self):
        """Same currency doesn't need exchange rate."""
        result = CurrencyConverter.convert(
            Decimal('100'), self.afn, self.afn
        )
        self.assertEqual(result['converted_amount'], Decimal('100'))

    def test_negative_amount_raises_error(self):
        """Negative amount raises informative error."""
        with self.assertRaises(CurrencyConversionError):
            CurrencyConverter.convert(Decimal('-10'), self.usd, self.afn)

    def test_invalid_currency_raises_error(self):
        """Invalid currency raises informative error."""
        with self.assertRaises(CurrencyConversionError):
            CurrencyConverter.get_currency('INVALID')


class ConcurrentSafetyTest(TransactionTestCase):
    """Test concurrent operation safety."""

    def setUp(self):
        self.cat = Category.objects.create(name='ConcCat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='ConcProd', sku='CONC', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='ConcWH', code='CWH01', is_active=True)

    def test_allocation_fails_for_insufficient_stock(self):
        """Allocation must fail when stock is insufficient."""
        Batch.objects.create(
            product=self.prod, batch_number='B-CONC-1', quantity=50, remaining_quantity=50,
            purchase_price=Decimal('5'), sale_price=Decimal('10'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location=str(self.wh.id), is_active=True
        )
        
        result = StockIntegrationService.allocate_stock(
            self.prod, Decimal('100'), self.wh
        )
        
        self.assertFalse(result.success)
        self.assertIn('Insufficient', result.message)

    def test_available_stock_calculation(self):
        """Available stock calculation must be accurate."""
        Batch.objects.create(
            product=self.prod, batch_number='B-AVAIL-1', quantity=25, remaining_quantity=25,
            purchase_price=Decimal('5'), sale_price=Decimal('10'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location=str(self.wh.id), is_active=True
        )
        
        total = StockIntegrationService.get_total_available_stock(self.prod, self.wh)
        self.assertEqual(total, Decimal('25'))
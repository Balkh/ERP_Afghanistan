"""
Quick service coverage tests for remaining gaps.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine
from accounting.services.tax_calculator import TaxCalculator
from accounting.services.discount_calculator import DiscountCalculator
from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement


class QuickServiceTest(TransactionTestCase):
    """Quick service tests for coverage."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='2000', name='Payable', account_type='LIABILITY', is_active=True)
        self.r1 = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)

    def test_multiple_entries_trial_balance(self):
        """Test trial balance with multiple entries."""
        for i in range(5):
            lines = [
                {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'},
                {'account_id': str(self.r1.id), 'debit': '0', 'credit': '100'}
            ]
            r = JournalEngine.create_entry('SALE', f'Sale {i}', lines)
            JournalEngine.post_entry(r['entry_id'])

        tb = FinancialReportEngine.get_trial_balance(date.today())
        self.assertEqual(tb['total_debit'], Decimal('500'))

    def test_multiple_expenses_pl(self):
        """Test P&L with multiple expense types."""
        exp1 = Account.objects.create(code='5000', name='Rent', account_type='EXPENSE', is_active=True)
        exp2 = Account.objects.create(code='5100', name='Salary', account_type='EXPENSE', is_active=True)

        lines1 = [
            {'account_id': str(exp1.id), 'debit': '200', 'credit': '0'},
            {'account_id': str(self.a1.id), 'debit': '0', 'credit': '200'}
        ]
        JournalEngine.create_entry('EXPENSE', 'Rent', lines1)
        JournalEngine.post_entry(JournalEngine.create_entry('EXPENSE', 'Rent', lines1)['entry_id'])

        lines2 = [
            {'account_id': str(exp2.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.a1.id), 'debit': '0', 'credit': '500'}
        ]
        JournalEngine.create_entry('EXPENSE', 'Salary', lines2)
        JournalEngine.post_entry(JournalEngine.create_entry('EXPENSE', 'Salary', lines2)['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(date.today(), date.today())
        self.assertEqual(pl['total_expenses'], Decimal('700'))

    def test_tax_calculator_combined(self):
        """Test tax calculator with multiple items."""
        items = [
            {'quantity': Decimal('2'), 'unit_price': Decimal('100'), 'tax_rate': Decimal('10')},
            {'quantity': Decimal('1'), 'unit_price': Decimal('50'), 'tax_rate': Decimal('5')}
        ]
        total_tax, updated = TaxCalculator.calculate_item_level_taxes(items)
        self.assertEqual(total_tax, Decimal('22.50'))

    def test_discount_calculator_combined(self):
        """Test discount calculator with multiple items."""
        items = [
            {'quantity': Decimal('2'), 'unit_price': Decimal('100'), 'discount_type': 'percentage', 'discount_value': Decimal('10')},
            {'quantity': Decimal('1'), 'unit_price': Decimal('50'), 'discount_type': 'fixed', 'discount_value': Decimal('5')}
        ]
        total_discount, updated = DiscountCalculator.calculate_item_level_discounts(items)
        self.assertIsInstance(total_discount, Decimal)


class InventoryStockTest(TransactionTestCase):
    """Test inventory stock operations."""

    def setUp(self):
        self.cat = Category.objects.create(name='Cat', is_active=True)
        self.unit = Unit.objects.create(name='U', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='P', sku='P', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='WH', code='WH', is_active=True)

    def test_batch_operations(self):
        """Test batch quantity operations."""
        batch = Batch.objects.create(
            product=self.prod, batch_number='B1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(), location='WH', is_active=True
        )

        self.assertEqual(batch.remaining_quantity, Decimal('100'))

        batch.remaining_quantity = Decimal('80')
        batch.save()
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, Decimal('80'))

    def test_multiple_batches_same_product(self):
        """Test multiple batches for same product."""
        Batch.objects.create(
            product=self.prod, batch_number='B1', quantity=50, remaining_quantity=50,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(), location='WH', is_active=True
        )

        Batch.objects.create(
            product=self.prod, batch_number='B2', quantity=75, remaining_quantity=75,
            purchase_price=Decimal('12'), sale_price=Decimal('18'),
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=date.today(), location='WH', is_active=True
        )

        batches = Batch.objects.filter(product=self.prod, is_active=True)
        self.assertEqual(batches.count(), 2)


class AccountBalanceTest(TransactionTestCase):
    """Test account balance calculations."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='2000', name='Payable', account_type='LIABILITY', is_active=True)

    def test_sequential_posting(self):
        """Test sequential posting to same account."""
        for i in range(3):
            lines = [
                {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'},
                {'account_id': str(self.a2.id), 'debit': '0', 'credit': '100'}
            ]
            r = JournalEngine.create_entry('GENERAL', f'Entry {i}', lines)
            JournalEngine.post_entry(r['entry_id'])

        self.a1.refresh_from_db()
        self.assertEqual(self.a1.balance, Decimal('300'))

    def test_reversal_impact(self):
        """Test entry reversal impact on balance."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '200', 'credit': '0'},
            {'account_id': str(self.a2.id), 'debit': '0', 'credit': '200'}
        ]
        r = JournalEngine.create_entry('GENERAL', 'Original', lines)
        JournalEngine.post_entry(r['entry_id'])

        self.a1.refresh_from_db()
        self.assertEqual(self.a1.balance, Decimal('200'))

        reversal = JournalEngine.reverse_entry(r['entry_id'], 'Test reversal')
        JournalEngine.post_entry(reversal['entry_id'])

        self.a1.refresh_from_db()
        self.assertEqual(self.a1.balance, Decimal('0'))
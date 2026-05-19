"""
Additional inventory and accounting tests.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.utils import timezone

from inventory.models import Product, Category, Unit, Warehouse, Batch
from accounting.models import Account
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine


class InventoryAdvancedTest(TransactionTestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Cat2', is_active=True)
        self.unit = Unit.objects.create(name='U2', symbol='U2', is_active=True)
        self.prod = Product.objects.create(name='P2', sku='P2', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='WHX', code='WHX', is_active=True)

    def test_batch_creation_full(self):
        batch = Batch.objects.create(
            product=self.prod, batch_number='BX1', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location='WHX', is_active=True
        )
        self.assertEqual(batch.remaining_quantity, Decimal('100'))

    def test_multiple_warehouses(self):
        wh2 = Warehouse.objects.create(name='WHY', code='WHY', is_active=True)
        self.assertEqual(Warehouse.objects.count(), 2)


class AccountingAdvancedTest(TransactionTestCase):
    def setUp(self):
        self.a1 = Account.objects.create(code='1100', name='Cash2', account_type='ASSET', is_active=True)
        self.a3 = Account.objects.create(code='4100', name='Sales2', account_type='REVENUE', is_active=True)

    def test_journal_entry_creation(self):
        lines = [
            {'account_id': str(self.a1.id), 'debit': '100', 'credit': '0'},
            {'account_id': str(self.a3.id), 'debit': '0', 'credit': '100'},
        ]
        result = JournalEngine.create_entry('SALE', 'Sale X', lines)
        self.assertTrue(result['success'])


class ReportAdvancedTest(TransactionTestCase):
    def test_trial_balance_structure(self):
        tb = FinancialReportEngine.get_trial_balance(date.today())
        self.assertIn('accounts', tb)

    def test_pnl_structure(self):
        pl = FinancialReportEngine.get_profit_and_loss(date.today(), date.today())
        self.assertIn('revenue', pl)
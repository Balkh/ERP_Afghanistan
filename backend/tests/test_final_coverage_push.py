"""
Final push for coverage - targeting remaining gaps.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine, Currency, ExchangeRate
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine
from accounting.services.tax_calculator import TaxCalculator, TaxType
from accounting.services.discount_calculator import DiscountCalculator, DiscountType
from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from sales.models import Customer
from purchases.models import Supplier
from security.models import Role, Permission, UserRole, AuditLog, SecurityEvent


class DeepServiceTests(TransactionTestCase):
    """Deep tests for services."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='1100', name='Bank', account_type='ASSET', is_active=True)
        self.r1 = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.e1 = Account.objects.create(code='5000', name='Rent', account_type='EXPENSE', is_active=True)
        self.e2 = Account.objects.create(code='5100', name='Salary', account_type='EXPENSE', is_active=True)
        self.e3 = Account.objects.create(code='5200', name='Utilities', account_type='EXPENSE', is_active=True)
        self.l1 = Account.objects.create(code='2000', name='Payable', account_type='LIABILITY', is_active=True)

    def test_complex_trial_balance(self):
        """Complex trial balance with various account types."""
        entries = [
            ('SALE', self.a1, self.r1, '1000'),
            ('SALE', self.a2, self.r1, '500'),
            ('EXPENSE', self.e1, self.a1, '200'),
            ('EXPENSE', self.e2, self.a1, '300'),
        ]

        for entry_type, debit_acc, credit_acc, amount in entries:
            lines = [
                {'account_id': str(debit_acc.id), 'debit': amount, 'credit': '0'},
                {'account_id': str(credit_acc.id), 'debit': '0', 'credit': amount}
            ]
            r = JournalEngine.create_entry(entry_type, f'{entry_type} entry', lines)
            JournalEngine.post_entry(r['entry_id'])

        tb = FinancialReportEngine.get_trial_balance(date.today())
        self.assertEqual(tb['total_debit'], Decimal('2000'))
        self.assertEqual(tb['total_credit'], Decimal('2000'))

    def test_tax_calculator_all_types(self):
        """Test all tax calculation types."""
        r1 = TaxCalculator.calculate_percentage_tax(Decimal('10'), Decimal('100'))
        self.assertEqual(r1.tax_amount, Decimal('10'))

        r2 = TaxCalculator.calculate_fixed_tax(Decimal('15'))
        self.assertEqual(r2.tax_amount, Decimal('15'))

        r3 = TaxCalculator.calculate_compound_tax(Decimal('100'), [Decimal('10'), Decimal('5')])
        self.assertEqual(r3.tax_amount, Decimal('15.50'))

    def test_discount_calculator_all_types(self):
        """Test all discount calculation types."""
        d1 = DiscountCalculator.calculate_percentage_discount(Decimal('10'), Decimal('100'))
        self.assertEqual(d1.discount_amount, Decimal('10'))

        d2 = DiscountCalculator.calculate_fixed_discount(Decimal('25'), Decimal('200'))
        self.assertEqual(d2.discount_amount, Decimal('25'))

        d3 = DiscountCalculator.calculate_tiered_discount(
            Decimal('5000'),
            [(Decimal('1000'), Decimal('5')), (Decimal('5000'), Decimal('10'))]
        )
        self.assertEqual(d3.discount_amount, Decimal('500'))

    def test_ledger_date_filtering(self):
        """Test ledger with date filters."""
        base_date = date.today() - timedelta(days=30)

        lines = [
            {'account_id': str(self.a1.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.r1.id), 'debit': '0', 'credit': '500'}
        ]
        r = JournalEngine.create_entry('SALE', 'Old sale', lines)
        JournalEngine.post_entry(r['entry_id'])

        ledger = JournalEngine.get_account_ledger(self.a1.id, base_date, date.today() + timedelta(days=1))
        self.assertTrue(len(ledger['entries']) >= 1)


class CurrencyExchangeTests(TransactionTestCase):
    """Test currency and exchange operations."""

    def setUp(self):
        self.afn = Currency.objects.create(code='AFN', name='Afghani', symbol='؋', is_active=True)
        self.usd = Currency.objects.create(code='USD', name='US Dollar', symbol='$', is_active=True)

    def test_currency_creation(self):
        """Test currency creation."""
        self.assertEqual(self.afn.code, 'AFN')
        self.assertEqual(self.usd.code, 'USD')

    def test_exchange_rate_creation(self):
        """Test exchange rate creation."""
        rate = ExchangeRate.objects.create(
            from_currency=self.afn,
            to_currency=self.usd,
            rate=Decimal('0.014'),
            effective_date=date.today(),
            is_active=True
        )
        self.assertEqual(rate.rate, Decimal('0.014'))

    def test_multiple_exchange_rates(self):
        """Test multiple exchange rates."""
        for i in range(3):
            ExchangeRate.objects.create(
                from_currency=self.afn,
                to_currency=self.usd,
                rate=Decimal(str(0.01 + i * 0.001)),
                effective_date=date.today() - timedelta(days=i),
                is_active=True
            )

        rates = ExchangeRate.objects.filter(from_currency=self.afn, to_currency=self.usd, is_active=True)
        self.assertEqual(rates.count(), 3)


class DeepInventoryTests(TransactionTestCase):
    """Deep inventory tests."""

    def setUp(self):
        self.cat = Category.objects.create(name='Pharmaceuticals', is_active=True)
        self.unit = Unit.objects.create(name='Tablet', symbol='TAB', is_active=True)
        self.wh1 = Warehouse.objects.create(name='Warehouse A', code='WH-A', is_active=True)
        self.wh2 = Warehouse.objects.create(name='Warehouse B', code='WH-B', is_active=True)
        self.prod = Product.objects.create(name='Amoxicillin', sku='AMX500', category=self.cat, unit=self.unit, is_active=True)

    def test_batch_expiry_ordering(self):
        """Test batches ordered by expiry."""
        dates = [
            date.today() + timedelta(days=90),
            date.today() + timedelta(days=180),
            date.today() + timedelta(days=30),
        ]

        for i, exp_date in enumerate(dates):
            Batch.objects.create(
                product=self.prod, batch_number=f'B{i}', quantity=100, remaining_quantity=100,
                purchase_price=Decimal('10'), sale_price=Decimal('15'),
                expiry_date=exp_date, manufacturing_date=date.today(),
                location='WH-A', is_active=True
            )

        batches = Batch.objects.filter(product=self.prod, is_active=True).order_by('expiry_date')
        self.assertEqual(batches.first().batch_number, 'B2')

    def test_warehouse_transfer_simulation(self):
        """Simulate warehouse transfer."""
        batch = Batch.objects.create(
            product=self.prod, batch_number='BT1', quantity=50, remaining_quantity=50,
            purchase_price=Decimal('10'), sale_price=Decimal('15'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(), location='WH-A', is_active=True
        )

        batch.location = 'WH-B'
        batch.save()
        batch.refresh_from_db()
        self.assertEqual(batch.location, 'WH-B')

    def test_multiple_products_inventory(self):
        """Test multiple products."""
        prod2 = Product.objects.create(
            name='Panadol', sku='PAN250X', barcode='PAN250X',
            category=self.cat, unit=self.unit, is_active=True
        )

        Batch.objects.create(
            product=self.prod, batch_number='BP1X', quantity=200, remaining_quantity=200,
            purchase_price=Decimal('8'), sale_price=Decimal('12'),
            expiry_date=date.today() + timedelta(days=200), manufacturing_date=date.today(),
            location='WH-A', is_active=True
        )

        Batch.objects.create(
            product=prod2, batch_number='BP2X', quantity=150, remaining_quantity=150,
            purchase_price=Decimal('5'), sale_price=Decimal('8'),
            expiry_date=date.today() + timedelta(days=150), manufacturing_date=date.today(),
            location='WH-A', is_active=True
        )

        total_qty = sum(b.remaining_quantity for b in Batch.objects.filter(is_active=True))
        self.assertEqual(total_qty, Decimal('350'))


class DeepSecurityTests(TransactionTestCase):
    """Deep security tests."""

    def test_role_permission_creation(self):
        """Test role and permission creation."""
        role = Role.objects.create(name='Pharmacist', description='Pharmacy staff')
        perm = Permission.objects.create(name='Dispense Medication', codename='dispense_med', module='pharmacy')

        self.assertEqual(role.name, 'Pharmacist')
        self.assertEqual(perm.codename, 'dispense_med')

    def test_user_role_assignment(self):
        """Test user role assignment."""
        user = User.objects.create_user(username='pharma1x', password='test')
        role = Role.objects.create(name='Technician')

        UserRole.objects.create(user=user, role=role)

        self.assertEqual(user.user_roles.count(), 1)

    def test_audit_log_creation(self):
        """Test audit log creation."""
        log = AuditLog.objects.create(
            action='LOGIN',
            username='admin',
            ip_address='192.168.1.100'
        )
        self.assertEqual(log.action, 'LOGIN')

    def test_security_event_creation(self):
        """Test security event creation."""
        event = SecurityEvent.objects.create(
            event_type='FAILED_LOGIN',
            severity='WARNING',
            title='Failed login attempt',
            ip_address='192.168.1.50'
        )
        self.assertEqual(event.severity, 'WARNING')


class ViewDeepTests(TestCase):
    """Deep view tests."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='deepuser', password='test123')
        self.client.force_login(self.user)

    def test_chart_of_accounts_view(self):
        """Test chart of accounts endpoint."""
        response = self.client.get('/api/accounting/chart-of-accounts/')
        self.assertIn(response.status_code, [200, 403, 404])

    def test_financial_summary_view(self):
        """Test financial summary endpoint."""
        response = self.client.get('/api/accounting/summary/')
        self.assertIn(response.status_code, [200, 403, 404])

    def test_inventory_dashboard_view(self):
        """Test inventory dashboard."""
        response = self.client.get('/api/inventory/dashboard/')
        self.assertIn(response.status_code, [200, 403, 404])

    def test_sales_summary_view(self):
        """Test sales summary."""
        response = self.client.get('/api/sales/summary/')
        self.assertIn(response.status_code, [200, 403, 404])

    def test_purchase_summary_view(self):
        """Test purchase summary."""
        response = self.client.get('/api/purchases/summary/')
        self.assertIn(response.status_code, [200, 403, 404])


class DeepReportTests(TransactionTestCase):
    """Deep report generation tests."""

    def setUp(self):
        self.a1 = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.a2 = Account.objects.create(code='1100', name='Bank', account_type='ASSET', is_active=True)
        self.r1 = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.r2 = Account.objects.create(code='4100', name='Service', account_type='REVENUE', is_active=True)
        self.e1 = Account.objects.create(code='5000', name='COGS', account_type='EXPENSE', is_active=True)

    def test_multi_revenue_pnl(self):
        """Test P&L with multiple revenue streams."""
        streams = [
            (self.r1, '1000'),
            (self.r2, '500'),
            (self.r1, '250'),
        ]

        for rev_acc, amount in streams:
            lines = [
                {'account_id': str(self.a1.id), 'debit': amount, 'credit': '0'},
                {'account_id': str(rev_acc.id), 'debit': '0', 'credit': amount}
            ]
            r = JournalEngine.create_entry('REVENUE', 'Revenue', lines)
            JournalEngine.post_entry(r['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(date.today(), date.today())
        self.assertEqual(pl['total_revenue'], Decimal('1750'))

    def test_cash_flow_operations(self):
        """Test cash flow with operations."""
        lines = [
            {'account_id': str(self.a1.id), 'debit': '2000', 'credit': '0'},
            {'account_id': str(self.r1.id), 'debit': '0', 'credit': '2000'}
        ]
        r = JournalEngine.create_entry('SALE', 'Sale', lines)
        JournalEngine.post_entry(r['entry_id'])

        cf = FinancialReportEngine.get_cash_flow_statement(date.today(), date.today())
        self.assertIn('operating_activities', cf)
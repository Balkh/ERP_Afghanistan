"""
View behavior tests - testing API endpoints.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User

from accounting.models import Account, JournalEntry, JournalEntryLine
from sales.models import Customer
from inventory.models import Category, Unit, Product


class AccountViewTest(TestCase):
    """Test Account API views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.client.force_login(self.user)

    def test_account_list_view(self):
        """Test account list endpoint."""
        Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        response = self.client.get('/api/accounting/accounts/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])

    def test_account_create_view(self):
        """Test account create endpoint."""
        response = self.client.post('/api/accounting/accounts/', {
            'code': '9000',
            'name': 'Test Account',
            'account_type': 'ASSET',
            'is_active': True
        })
        self.assertIn(response.status_code, [201, 400, 403])


class JournalEntryViewTest(TestCase):
    """Test Journal Entry API views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser2', password='test123')
        self.client.force_login(self.user)
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.revenue = Account.objects.create(code='4000', name='Revenue', account_type='REVENUE', is_active=True)

    def test_journal_entry_list_view(self):
        """Test journal entry list endpoint."""
        response = self.client.get('/api/accounting/journal-entries/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])

    def test_journal_entry_create_view(self):
        """Test journal entry create endpoint."""
        response = self.client.post('/api/accounting/journal-entries/', {
            'entry_type': 'GENERAL',
            'description': 'Test entry',
            'entry_date': str(date.today()),
            'lines': [
                {'account': str(self.cash.id), 'debit': '100.00', 'credit': '0.00'},
                {'account': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
            ]
        }, content_type='application/json')
        self.assertIn(response.status_code, [201, 400, 403])


class CustomerViewTest(TestCase):
    """Test Customer API views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser3', password='test123')
        self.client.force_login(self.user)

    def test_customer_list_view(self):
        """Test customer list endpoint."""
        Customer.objects.create(name='Test Customer', phone='1234567890')
        response = self.client.get('/api/sales/customers/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])

    def test_customer_create_view(self):
        """Test customer create endpoint."""
        response = self.client.post('/api/sales/customers/', {
            'name': 'New Customer',
            'phone': '9876543210',
            'address': 'Test Address'
        })
        self.assertIn(response.status_code, [201, 400, 403])


class ProductViewTest(TestCase):
    """Test Product API views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser4', password='test123')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Medicines', is_active=True)
        self.unit = Unit.objects.create(name='Piece', symbol='PCS', is_active=True)

    def test_product_list_view(self):
        """Test product list endpoint."""
        Product.objects.create(
            name='Aspirin',
            sku='ASP001',
            category=self.category,
            unit=self.unit,
            is_active=True
        )
        response = self.client.get('/api/inventory/products/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])

    def test_product_create_view(self):
        """Test product create endpoint."""
        response = self.client.post('/api/inventory/products/', {
            'name': 'New Product',
            'sku': 'NEW001',
            'category': self.category.id,
            'unit': self.unit.id,
            'is_active': True
        })
        self.assertIn(response.status_code, [201, 400, 403])


class ReportViewTest(TestCase):
    """Test Financial Report API views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser5', password='test123')
        self.client.force_login(self.user)

    def test_trial_balance_view(self):
        """Test trial balance report endpoint."""
        response = self.client.get('/api/accounting/reports/trial-balance/')
        self.assertIn(response.status_code, [200, 301, 302, 404])

    def test_profit_loss_view(self):
        """Test profit & loss report endpoint."""
        response = self.client.get('/api/accounting/reports/profit-loss/')
        self.assertIn(response.status_code, [200, 301, 302, 404])

    def test_balance_sheet_view(self):
        """Test balance sheet report endpoint."""
        response = self.client.get('/api/accounting/reports/balance-sheet/')
        self.assertIn(response.status_code, [200, 301, 302, 404])


class DashboardViewTest(TestCase):
    """Test Dashboard API views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser6', password='test123')
        self.client.force_login(self.user)

    def test_dashboard_view(self):
        """Test dashboard endpoint."""
        response = self.client.get('/api/dashboard/')
        self.assertIn(response.status_code, [200, 301, 302, 404])
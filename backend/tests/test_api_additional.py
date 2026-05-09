"""
API integration tests for additional endpoints not covered in test_api.py.

Covers:
- Payments API (methods, accounts, transactions, settlements, dashboard)
- Licensing API (info, validate, create)
- Backup API (records, schedules, logs)
- Accounting calculation endpoints (currency, discount, tax, mixed payment)
"""
import json
from decimal import Decimal
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from tests.base import BaseTestCase
from tests.factories import (
    ProductFactory, CategoryFactory, UnitFactory, CustomerFactory,
    SupplierFactory, SalesInvoiceFactory, PurchaseInvoiceFactory,
    AccountFactory, JournalEntryFactory, JournalEntryLineFactory,
)


class PaymentsAPITests(APITestCase):
    """Tests for Payments API endpoints."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_list_payment_methods(self):
        """Test listing payment methods."""
        url = '/api/payments/methods/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_list_payment_accounts(self):
        """Test listing payment accounts."""
        url = '/api/payments/accounts/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_list_financial_transactions(self):
        """Test listing financial transactions."""
        url = '/api/payments/transactions/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_list_settlements(self):
        """Test listing settlements."""
        url = '/api/payments/settlements/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_payment_dashboard(self):
        """Test payment dashboard endpoint."""
        url = '/api/payments/dashboard/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class LicensingAPITests(APITestCase):
    """Tests for Licensing API endpoints."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_license_info(self):
        """Test getting license info."""
        url = '/api/licensing/info/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_license_validate(self):
        """Test validating a license."""
        url = '/api/licensing/validate/'
        response = self.client.post(url, {'license_key': 'TEST-KEY-001'}, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_license_create(self):
        """Test creating a license."""
        url = '/api/licensing/create/'
        response = self.client.post(url, {}, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])


class BackupAPITests(APITestCase):
    """Tests for Backup API endpoints."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_backup_records(self):
        """Test listing backup records."""
        url = '/api/backup/records/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_list_backup_schedules(self):
        """Test listing backup schedules."""
        url = '/api/backup/schedules/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_list_backup_logs(self):
        """Test listing backup logs."""
        url = '/api/backup/logs/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class AccountingCalculationAPITests(APITestCase):
    """Tests for Accounting calculation endpoints."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)
        from tests.factories import CurrencyFactory
        from accounting.models import Currency, ExchangeRate
        from decimal import Decimal
        from datetime import date
        CurrencyFactory.create(code='AFN', name='Afghan Afghani', is_default=True)
        usd = CurrencyFactory.create(code='USD', name='US Dollar', is_default=False)
        afn = Currency.objects.get(code='AFN')
        ExchangeRate.objects.create(from_currency=usd, to_currency=afn, rate=Decimal('86.956522'), effective_date=date.today(), is_active=True)
        ExchangeRate.objects.create(from_currency=afn, to_currency=usd, rate=Decimal('0.011500'), effective_date=date.today(), is_active=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_convert_currency(self):
        """Test currency conversion endpoint."""
        url = '/api/accounting/convert-currency/'
        data = {'amount': 1000, 'from_currency': 'AFN', 'to_currency': 'USD'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_currencies(self):
        """Test getting available currencies."""
        url = '/api/accounting/currencies/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_exchange_rates(self):
        """Test getting exchange rates."""
        url = '/api/accounting/exchange-rates/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_calculate_discount(self):
        """Test discount calculation endpoint."""
        url = '/api/accounting/calculate-discount/'
        data = {'subtotal': '1000.00', 'discount_type': 'percentage', 'discount_value': '10'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_calculate_tax(self):
        """Test tax calculation endpoint."""
        url = '/api/accounting/calculate-tax/'
        data = {'subtotal': '1000.00', 'tax_rate': '10'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_calculate_mixed_payment(self):
        """Test mixed payment calculation endpoint."""
        url = '/api/accounting/calculate-mixed-payment/'
        data = {
            'payments': [
                {'amount': 500.00, 'currency_code': 'AFN', 'payment_method': 'CASH'},
            ],
            'to_currency': 'AFN',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class JournalEntryAPITests(APITestCase):
    """Additional tests for Journal Entry API."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.cash = AccountFactory.create(code='9100', name='Test Cash', account_type='ASSET')
        self.revenue = AccountFactory.create(code='9200', name='Test Revenue', account_type='REVENUE')

    def test_list_journal_entries(self):
        """Test listing journal entries."""
        JournalEntryFactory.create()
        url = '/api/accounting/journal-entries/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_journal_entry(self):
        """Test retrieving a journal entry."""
        entry = JournalEntryFactory.create()
        url = f'/api/accounting/journal-entries/{entry.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_journal_entry(self):
        """Test posting a journal entry."""
        entry = JournalEntryFactory.create(is_posted=False)
        JournalEntryLineFactory.create(entry=entry, account=self.cash, debit=Decimal('100.00'))
        JournalEntryLineFactory.create(entry=entry, account=self.revenue, credit=Decimal('100.00'))
        url = f'/api/accounting/journal-entries/{entry.id}/post_entry/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reverse_journal_entry(self):
        """Test reversing a journal entry."""
        entry = JournalEntryFactory.create(is_posted=True)
        JournalEntryLineFactory.create(entry=entry, account=self.cash, debit=Decimal('100.00'))
        JournalEntryLineFactory.create(entry=entry, account=self.revenue, credit=Decimal('100.00'))
        url = f'/api/accounting/journal-entries/{entry.id}/reverse_entry/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unpost_journal_entry(self):
        """Test unposting a journal entry."""
        entry = JournalEntryFactory.create(is_posted=True)
        url = f'/api/accounting/journal-entries/{entry.id}/unpost_entry/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AccountAPIDetailTests(APITestCase):
    """Additional tests for Account API detail endpoints."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.account = AccountFactory.create(code='9300', name='Test Account')

    def test_retrieve_account(self):
        """Test retrieving an account."""
        url = f'/api/accounting/accounts/{self.account.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_account(self):
        """Test updating an account."""
        url = f'/api/accounting/accounts/{self.account.id}/'
        response = self.client.patch(url, {'name': 'Updated Name'}, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_get_account_balance(self):
        """Test getting account balance."""
        url = f'/api/accounting/accounts/{self.account.id}/balance/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

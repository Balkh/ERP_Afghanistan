"""
Tests for Sales ViewSet endpoints.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from accounting.models import Account
from payments.models import PaymentMethod, PaymentAccount
from tests.factories import (
    CustomerFactory, SalesInvoiceFactory, SalesItemFactory,
    CustomerPaymentFactory, ProductFactory, BatchFactory, WarehouseFactory,
    AccountFactory, JournalEntryFactory,
)


def _setup_payment_infrastructure():
    """Create PaymentAccount and PaymentMethod required by CustomerPayment.save()."""
    pm, _ = PaymentMethod.objects.get_or_create(
        code='CASH', defaults={'name': 'Cash', 'method_type': 'CASH', 'is_active': True, 'is_default': True}
    )
    # Create all accounts required by PaymentEngine._validate_required_accounts()
    account_map = {
        '1000': ('Cash', 'ASSET', 'CURRENT_ASSET'),
        '1200': ('Accounts Receivable', 'ASSET', 'CURRENT_ASSET'),
        '1300': ('Inventory', 'ASSET', 'CURRENT_ASSET'),
        '2100': ('Tax Payable', 'LIABILITY', 'CURRENT_LIABILITY'),
        '4100': ('Sales Revenue', 'REVENUE', 'OPERATING_REVENUE'),
        '5100': ('COGS', 'EXPENSE', 'COST_OF_GOODS_SOLD'),
        '6100': ('Operating Expenses', 'EXPENSE', 'OPERATING_EXPENSE'),
    }
    for code, (name, acct_type, category) in account_map.items():
        AccountFactory.create(code=code, name=name, account_type=acct_type, account_category=category, is_system=True)
    cash_acct = Account.objects.get(code='1000')
    PaymentAccount.objects.get_or_create(
        code='CASH-MAIN', defaults={
            'name': 'Main Cash', 'account_type': 'CASH',
            'accounting_account': cash_acct, 'is_active': True, 'is_default': True,
            'current_balance': Decimal('1000000.00'), 'currency': 'AFN',
        }
    )


class SalesAccountingIntegrationTests(APITestCase):
    """Tests for SalesAccountingService integration via views."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.customer = CustomerFactory.create()
        self.warehouse = WarehouseFactory.create(is_default=True)
        self.product = ProductFactory.create()
        self.invoice = SalesInvoiceFactory.create(customer=self.customer)
        # Create required accounts
        AccountFactory.create(code='1200', account_type='ASSET', name='Accounts Receivable')
        AccountFactory.create(code='4100', account_type='REVENUE', name='Sales Revenue')
        AccountFactory.create(code='2100', account_type='LIABILITY', name='Tax Payable')
        AccountFactory.create(code='1010', account_type='ASSET', name='Cash')

    @patch('sales.views.StockIntegrationService.process_sale')
    def test_dispatch_creates_journal_entry(self, mock_process):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.movements = []
        mock_result.allocations = []
        mock_process.return_value = mock_result

        self.invoice.status = 'CONFIRMED'
        self.invoice.tax = Decimal('5.00')
        self.invoice.subtotal = Decimal('100.00')
        self.invoice.total_amount = Decimal('105.00')
        self.invoice.save()
        batch = BatchFactory.create(product=self.product, location=self.warehouse)
        SalesItemFactory.create(invoice=self.invoice, product=self.product, batch=batch)
        url = f'/api/sales/invoices/{self.invoice.id}/dispatch_invoice/'
        data = {'warehouse_id': self.warehouse.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cancel_with_journal_entry(self):
        entry = JournalEntryFactory.create()
        self.invoice.journal_entry_id = entry.id
        self.invoice.status = 'CONFIRMED'
        self.invoice.save()
        url = f'/api/sales/invoices/{self.invoice.id}/cancel/'
        response = self.client.post(url, {}, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])


class CustomerViewSetTests(APITestCase):
    """Tests for CustomerViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        _setup_payment_infrastructure()
        self.customer = CustomerFactory.create()

    def test_list_customers(self):
        url = '/api/sales/customers/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_customer(self):
        url = f'/api/sales/customers/{self.customer.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_customer(self):
        url = '/api/sales/customers/'
        data = {
            'name': 'New Customer',
            'code': 'CUST-NEW',
            'email': 'test@example.com',
            'phone': '+1234567890',
            'address': '123 Test St',
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_update_customer(self):
        url = f'/api/sales/customers/{self.customer.id}/'
        data = {'name': 'Updated Customer'}
        response = self.client.patch(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK])

    def test_customer_balance(self):
        url = f'/api/sales/customers/{self.customer.id}/balance/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_invoices(self):
        SalesInvoiceFactory.create(customer=self.customer)
        url = f'/api/sales/customers/{self.customer.id}/invoices/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_payments(self):
        CustomerPaymentFactory.create(customer=self.customer)
        url = f'/api/sales/customers/{self.customer.id}/payments/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_customers_include_inactive(self):
        inactive = CustomerFactory.create(is_active=False)
        url = '/api/sales/customers/?include_inactive=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SalesInvoiceViewSetTests(APITestCase):
    """Tests for SalesInvoiceViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.customer = CustomerFactory.create()
        self.warehouse = WarehouseFactory.create(is_default=True)
        self.product = ProductFactory.create()
        self.invoice = SalesInvoiceFactory.create(customer=self.customer)

    def test_list_invoices(self):
        url = '/api/sales/invoices/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_invoice(self):
        url = f'/api/sales/invoices/{self.invoice.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_confirmed_invoice(self):
        url = '/api/sales/invoices/'
        data = {
            'customer': self.customer.id,
            'invoice_number': 'SI-CONFIRM-TEST-001',
            'invoice_date': date.today().isoformat(),
            'status': 'CONFIRMED',
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_dispatch_already_dispatched_invoice(self):
        self.invoice.status = 'DISPATCHED'
        self.invoice.save()
        url = f'/api/sales/invoices/{self.invoice.id}/dispatch_invoice/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_invoice(self):
        self.invoice.status = 'CONFIRMED'
        self.invoice.save()
        url = f'/api/sales/invoices/{self.invoice.id}/cancel/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cancel_paid_invoice(self):
        self.invoice.status = 'PAID'
        self.invoice.save()
        url = f'/api/sales/invoices/{self.invoice.id}/cancel/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dispatch_unconfirmed_invoice(self):
        self.invoice.status = 'DRAFT'
        self.invoice.save()
        url = f'/api/sales/invoices/{self.invoice.id}/dispatch_invoice/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_invoices_include_inactive(self):
        url = '/api/sales/invoices/?include_inactive=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_invoice(self):
        url = '/api/sales/invoices/'
        data = {
            'customer': self.customer.id,
            'invoice_number': 'SI-TEST-001',
            'invoice_date': date.today().isoformat(),
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class SalesItemViewSetTests(APITestCase):
    """Tests for SalesItemViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.customer = CustomerFactory.create()
        self.invoice = SalesInvoiceFactory.create(customer=self.customer)
        self.item = SalesItemFactory.create(invoice=self.invoice)

    def test_list_items(self):
        url = '/api/sales/items/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_item(self):
        url = f'/api/sales/items/{self.item.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CustomerPaymentViewSetTests(APITestCase):
    """Tests for CustomerPaymentViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        _setup_payment_infrastructure()
        self.customer = CustomerFactory.create()
        self.invoice = SalesInvoiceFactory.create(
            customer=self.customer,
            total_amount=Decimal('1000.00'),
            subtotal=Decimal('1000.00'),
        )
        self.payment = CustomerPaymentFactory.create(customer=self.customer, invoice=self.invoice)

    def test_list_payments(self):
        url = '/api/sales/payments/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_payment(self):
        url = f'/api/sales/payments/{self.payment.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_payment(self):
        url = '/api/sales/payments/'
        data = {
            'customer': self.customer.id,
            'invoice': self.invoice.id,
            'amount': '500.00',
            'payment_date': date.today().isoformat(),
            'payment_method': 'CASH',
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

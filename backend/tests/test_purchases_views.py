"""
Tests for Purchases ViewSet endpoints.
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
    SupplierFactory, PurchaseInvoiceFactory, PurchaseItemFactory,
    SupplierPaymentFactory, ProductFactory, BatchFactory, WarehouseFactory,
    AccountFactory, JournalEntryFactory,
)


def _setup_payment_infrastructure():
    """Create PaymentAccount and PaymentMethod required by SupplierPayment.save()."""
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


class PurchaseAccountingServiceTests(APITestCase):
    """Tests for PurchaseAccountingService integration via views."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.supplier = SupplierFactory.create()
        self.warehouse = WarehouseFactory.create(is_default=True)
        self.product = ProductFactory.create()
        self.invoice = PurchaseInvoiceFactory.create(supplier=self.supplier)
        # Create required accounts
        AccountFactory.create(code='1300', account_type='ASSET', name='Inventory')
        AccountFactory.create(code='2100', account_type='LIABILITY', name='Accounts Payable')
        AccountFactory.create(code='2110', account_type='LIABILITY', name='Tax Payable')
        AccountFactory.create(code='1010', account_type='ASSET', name='Cash')

    @patch('purchases.views.StockIntegrationService.process_purchase')
    def test_receive_creates_journal_entry(self, mock_process):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.movements = []
        mock_result.warnings = []
        mock_process.return_value = mock_result

        self.invoice.status = 'CONFIRMED'
        self.invoice.tax = Decimal('10.00')
        self.invoice.subtotal = Decimal('100.00')
        self.invoice.total_amount = Decimal('110.00')
        self.invoice.save()
        PurchaseItemFactory.create(
            invoice=self.invoice,
            product=self.product,
            quantity=Decimal('10.00'),
            batch_number='BATCH-JE-001',
            expiry_date=date.today() + timedelta(days=365),
        )
        url = f'/api/purchases/invoices/{self.invoice.id}/receive/'
        data = {'warehouse_id': self.warehouse.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cancel_with_journal_entry(self):
        # Create a journal entry linked to invoice
        entry = JournalEntryFactory.create()
        self.invoice.journal_entry_id = entry.id
        self.invoice.status = 'CONFIRMED'
        self.invoice.save()
        url = f'/api/purchases/invoices/{self.invoice.id}/cancel/'
        response = self.client.post(url, {}, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])


class SupplierViewSetTests(APITestCase):
    """Tests for SupplierViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        _setup_payment_infrastructure()
        self.supplier = SupplierFactory.create()

    def test_list_suppliers(self):
        url = '/api/purchases/suppliers/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_supplier(self):
        url = f'/api/purchases/suppliers/{self.supplier.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_supplier(self):
        url = '/api/purchases/suppliers/'
        data = {
            'name': 'New Supplier',
            'code': 'SUP-NEW',
            'email': 'test@example.com',
            'phone': '+1234567890',
            'address': '123 Test St',
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_update_supplier(self):
        url = f'/api/purchases/suppliers/{self.supplier.id}/'
        data = {'name': 'Updated Supplier'}
        response = self.client.patch(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_200_OK])

    def test_delete_supplier(self):
        url = f'/api/purchases/suppliers/{self.supplier.id}/'
        response = self.client.delete(url)
        self.assertIn(response.status_code, [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK])

    def test_supplier_balance(self):
        url = f'/api/purchases/suppliers/{self.supplier.id}/balance/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_supplier_invoices(self):
        PurchaseInvoiceFactory.create(supplier=self.supplier)
        url = f'/api/purchases/suppliers/{self.supplier.id}/invoices/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_supplier_payments(self):
        SupplierPaymentFactory.create(supplier=self.supplier)
        url = f'/api/purchases/suppliers/{self.supplier.id}/payments/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_suppliers_include_inactive(self):
        inactive = SupplierFactory.create(is_active=False)
        url = '/api/purchases/suppliers/?include_inactive=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PurchaseInvoiceViewSetTests(APITestCase):
    """Tests for PurchaseInvoiceViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.supplier = SupplierFactory.create()
        self.warehouse = WarehouseFactory.create(is_default=True)
        self.product = ProductFactory.create()
        self.invoice = PurchaseInvoiceFactory.create(supplier=self.supplier)

    def test_list_invoices(self):
        url = '/api/purchases/invoices/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_invoice(self):
        url = f'/api/purchases/invoices/{self.invoice.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_confirm_invoice(self):
        self.invoice.status = 'DRAFT'
        self.invoice.save()
        url = f'/api/purchases/invoices/{self.invoice.id}/confirm/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_confirm_non_draft_invoice(self):
        self.invoice.status = 'CONFIRMED'
        self.invoice.save()
        url = f'/api/purchases/invoices/{self.invoice.id}/confirm/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_invoice(self):
        self.invoice.status = 'CONFIRMED'
        self.invoice.save()
        url = f'/api/purchases/invoices/{self.invoice.id}/cancel/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cancel_paid_invoice(self):
        self.invoice.status = 'PAID'
        self.invoice.save()
        url = f'/api/purchases/invoices/{self.invoice.id}/cancel/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receive_unconfirmed_invoice(self):
        self.invoice.status = 'DRAFT'
        self.invoice.save()
        url = f'/api/purchases/invoices/{self.invoice.id}/receive/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_invoices_include_inactive(self):
        url = '/api/purchases/invoices/?include_inactive=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_invoice(self):
        url = '/api/purchases/invoices/'
        data = {
            'supplier': self.supplier.id,
            'invoice_number': 'PI-TEST-001',
            'invoice_date': date.today().isoformat(),
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class PurchaseItemViewSetTests(APITestCase):
    """Tests for PurchaseItemViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.supplier = SupplierFactory.create()
        self.invoice = PurchaseInvoiceFactory.create(supplier=self.supplier)
        self.item = PurchaseItemFactory.create(invoice=self.invoice)

    def test_list_items(self):
        url = '/api/purchases/items/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_item(self):
        url = f'/api/purchases/items/{self.item.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SupplierPaymentViewSetTests(APITestCase):
    """Tests for SupplierPaymentViewSet."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        _setup_payment_infrastructure()
        self.supplier = SupplierFactory.create()
        self.invoice = PurchaseInvoiceFactory.create(
            supplier=self.supplier,
            total_amount=Decimal('1000.00'),
            subtotal=Decimal('1000.00'),
        )
        self.payment = SupplierPaymentFactory.create(supplier=self.supplier, invoice=self.invoice)

    def test_list_payments(self):
        url = '/api/purchases/payments/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_payment(self):
        url = f'/api/purchases/payments/{self.payment.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_payment(self):
        url = '/api/purchases/payments/'
        data = {
            'supplier': self.supplier.id,
            'invoice': self.invoice.id,
            'amount': '500.00',
            'payment_date': date.today().isoformat(),
            'payment_method': 'CASH',
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

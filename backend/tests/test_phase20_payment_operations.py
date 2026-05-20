"""Tests for Phase 20: Financial Operations Cohesion — Payment Operations API."""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User

from sales.models import Customer, SalesInvoice, CustomerPayment, PaymentAllocation
from purchases.models import Supplier, PurchaseInvoice, SupplierPayment, SupplierPaymentAllocation
from payments.models import PaymentMethod, PaymentAccount
from accounting.models import Account


def ensure_accounts():
    """Ensure required accounting accounts exist."""
    accounts_data = [
        ('1200', 'Accounts Receivable', 'ASSET'),
        ('2100', 'Accounts Payable', 'LIABILITY'),
        ('4100', 'Sales Revenue', 'REVENUE'),
        ('1010', 'Cash', 'ASSET'),
    ]
    for code, name, acct_type in accounts_data:
        Account.objects.get_or_create(
            code=code,
            defaults={'name': name, 'account_type': acct_type, 'is_active': True},
        )


def ensure_payment_infrastructure():
    """Ensure payment methods and accounts exist."""
    from payments.models import PaymentMethod, PaymentAccount
    cash_account = Account.objects.filter(code='1010').first()
    if not cash_account:
        cash_account = Account.objects.create(
            code='1010', name='Cash', account_type='ASSET', is_active=True
        )
    pa, created = PaymentAccount.objects.get_or_create(
        code='CASH-MAIN',
        defaults={
            'name': 'Main Cash',
            'account_type': 'CASH',
            'accounting_account': cash_account,
            'currency': 'AFN',
            'is_active': True,
            'current_balance': Decimal('1000000.00'),
        },
    )
    if not created:
        pa.current_balance = Decimal('1000000.00')
        pa.save(update_fields=['current_balance'])
    for method_type, name, code in [
        ('CASH', 'Cash', 'CASH'),
        ('BANK_TRANSFER', 'Bank Transfer', 'BANK'),
        ('CHEQUE', 'Cheque', 'CHEQUE'),
    ]:
        PaymentMethod.objects.get_or_create(
            code=code,
            defaults={'name': name, 'method_type': method_type, 'is_active': True},
        )
    return pa


class PaymentOperationsAPITest(TestCase):
    """Test Phase 20 Payment Operations API endpoints."""

    def setUp(self):
        ensure_accounts()
        ensure_payment_infrastructure()
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user.is_superuser = True
        self.user.save(update_fields=['is_superuser'])
        self.client.force_authenticate(user=self.user)

        # Override permission classes for all views
        from rest_framework.views import APIView
        self._old_check_permissions = APIView.check_permissions
        APIView.check_permissions = lambda self, request: None

        self.customer = Customer.objects.create(
            name='Test Customer',
            code='TEST-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            code='TEST-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

        self.invoice1 = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='PO-INV-001',
            total_amount=Decimal('5000.00'),
            status='CONFIRMED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )
        self.invoice2 = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='PO-INV-002',
            total_amount=Decimal('3000.00'),
            status='DISPATCHED',
            order_date=self.today, invoice_date=self.today, due_date=self.today,
        )

    def tearDown(self):
        """Restore permission checking to avoid leaking to other tests."""
        from rest_framework.views import APIView
        APIView.check_permissions = self._old_check_permissions

    def test_customer_payment_workspace_returns_structure(self):
        """Customer payment workspace returns complete operational data."""
        url = reverse('payment-operations-customer-payment-workspace', kwargs={'customer_id': str(self.customer.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIn('customer', data)
        self.assertIn('outstanding_invoices', data)
        self.assertIn('unallocated_payments', data)
        self.assertIn('recent_payments', data)
        self.assertIn('allocation_summary', data)
        self.assertIn('derived_balance', data['customer'])

    def test_customer_payment_workspace_not_found(self):
        """Returns 404 for non-existent customer."""
        url = reverse('payment-operations-customer-payment-workspace', kwargs={'customer_id': '00000000-0000-0000-0000-000000000000'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_supplier_payment_workspace_returns_structure(self):
        """Supplier payment workspace returns complete operational data."""
        url = reverse('payment-operations-supplier-payment-workspace', kwargs={'supplier_id': str(self.supplier.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIn('supplier', data)
        self.assertIn('outstanding_invoices', data)
        self.assertIn('unallocated_payments', data)
        self.assertIn('recent_payments', data)
        self.assertIn('allocation_summary', data)

    def test_list_payment_methods(self):
        """Returns active payment methods."""
        url = reverse('payment-operations-list-payment-methods')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        methods = response.json()['data']
        self.assertIsInstance(methods, list)
        self.assertGreater(len(methods), 0)

    def test_list_payment_accounts(self):
        """Returns active payment accounts."""
        url = reverse('payment-operations-list-payment-accounts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        accounts = response.json()['data']
        self.assertIsInstance(accounts, list)
        self.assertGreater(len(accounts), 0)

    def test_validate_mixed_payment_valid(self):
        """Valid mixed payment split passes validation."""
        url = reverse('payment-operations-validate-mixed-payment')
        response = self.client.post(url, {
            'total_amount': '1000.00',
            'splits': [
                {'payment_method_code': 'CASH', 'amount': '600.00', 'payment_account_code': 'CASH-MAIN'},
                {'payment_method_code': 'BANK', 'amount': '400.00', 'payment_account_code': 'CASH-MAIN'},
            ],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertTrue(data['is_valid'])
        self.assertEqual(data['difference'], '0.00')

    def test_validate_mixed_payment_invalid_amount(self):
        """Mismatched split total fails validation."""
        url = reverse('payment-operations-validate-mixed-payment')
        response = self.client.post(url, {
            'total_amount': '1000.00',
            'splits': [
                {'payment_method_code': 'CASH', 'amount': '500.00', 'payment_account_code': 'CASH-MAIN'},
            ],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertFalse(data['is_valid'])
        self.assertEqual(len(data['errors']), 1)

    def test_payment_anomalies_returns_structure(self):
        """Payment anomalies endpoint returns structured detection results."""
        url = reverse('payment-operations-payment-anomalies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIn('anomalies', data)
        self.assertIn('total_count', data)
        self.assertIn('by_severity', data)

    def test_customer_payment_trace_returns_structure(self):
        """Payment trace returns allocation history."""
        url = reverse('payment-operations-customer-payment-trace', kwargs={'customer_id': str(self.customer.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIn('customer_id', data)
        self.assertIn('customer_name', data)
        self.assertIn('payment_trace', data)
        self.assertIn('total_payments', data)

    def test_supplier_payment_trace_returns_structure(self):
        """Supplier payment trace returns allocation history."""
        url = reverse('payment-operations-supplier-payment-trace', kwargs={'supplier_id': str(self.supplier.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIn('supplier_id', data)
        self.assertIn('supplier_name', data)
        self.assertIn('payment_trace', data)

    def test_process_customer_payment_invalid_amount(self):
        """Rejects payment with zero or negative amount."""
        url = reverse('payment-operations-process-customer-payment')
        response = self.client.post(url, {
            'customer_id': str(self.customer.id),
            'amount': '0',
            'payment_method': 'CASH',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_process_customer_payment_not_found(self):
        """Rejects payment for non-existent customer."""
        url = reverse('payment-operations-process-customer-payment')
        response = self.client.post(url, {
            'customer_id': '00000000-0000-0000-0000-000000000000',
            'amount': '100.00',
            'payment_method': 'CASH',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_process_supplier_payment_invalid_amount(self):
        """Rejects supplier payment with zero or negative amount."""
        url = reverse('payment-operations-process-supplier-payment')
        response = self.client.post(url, {
            'supplier_id': str(self.supplier.id),
            'amount': '0',
            'payment_method': 'CASH',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_allocate_customer_unallocated(self):
        """FIFO allocation endpoint returns results."""
        url = reverse('payment-operations-allocate-customer-unallocated', kwargs={'customer_id': str(self.customer.id)})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIn('payments_processed', data)
        self.assertIn('total_allocated', data)

    def test_allocate_supplier_unallocated(self):
        """Supplier FIFO allocation endpoint returns results."""
        url = reverse('payment-operations-allocate-supplier-unallocated', kwargs={'supplier_id': str(self.supplier.id)})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertIn('payments_processed', data)
        self.assertIn('total_allocated', data)

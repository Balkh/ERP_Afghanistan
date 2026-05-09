"""
Tests for payments models.
"""

from decimal import Decimal
from django.test import TransactionTestCase

from accounting.models import Account
from payments.models import PaymentMethod, PaymentAccount, FinancialTransaction


class PaymentMethodTest(TransactionTestCase):
    def setUp(self):
        self.method = PaymentMethod.objects.create(
            name='Cash', code='CASH', method_type='CASH', is_active=True
        )

    def test_payment_method_str(self):
        self.assertIn('Cash', str(self.method))

    def test_payment_method_active(self):
        self.assertTrue(self.method.is_active)

    def test_payment_method_code(self):
        self.assertEqual(self.method.code, 'CASH')


class PaymentAccountTest(TransactionTestCase):
    def setUp(self):
        self.account = Account.objects.create(
            code='1000', name='Cash Account', account_type='ASSET', is_active=True
        )
        self.payment_acc = PaymentAccount.objects.create(
            name='Main Cash', code='MC', account_type='CASH',
            accounting_account=self.account, is_active=True
        )

    def test_payment_account_str(self):
        self.assertIn('Main Cash', str(self.payment_acc))

    def test_payment_account_code(self):
        self.assertEqual(self.payment_acc.code, 'MC')


class FinancialTransactionTest(TransactionTestCase):
    def setUp(self):
        self.method = PaymentMethod.objects.create(
            name='Bank', code='BANK2', method_type='BANK_TRANSFER', is_active=True
        )

    def test_payment_method_creation(self):
        self.assertIsNotNone(self.method.id)
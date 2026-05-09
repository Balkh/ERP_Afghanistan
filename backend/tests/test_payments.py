"""
Tests for Payments module.

Covers:
- PaymentMethod model
- PaymentAccount model
- FinancialTransaction processing
- PaymentEngine services (receipts, payments, transfers, refunds)
- Settlement tracking
"""

from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from tests.base import BaseTestCase, TransactionBaseTestCase
from tests.factories import (
    PaymentMethodFactory,
    PaymentAccountFactory,
    FinancialTransactionFactory,
    CustomerFactory,
    SupplierFactory,
)


class PaymentMethodModelTests(BaseTestCase):
    """Tests for PaymentMethod model."""
    
    def test_create_payment_method(self):
        """Test basic payment method creation."""
        method = PaymentMethodFactory.create(
            name='Test Cash',
            code='TEST_CASH',
            method_type='CASH'
        )
        self.assertEqual(method.name, 'Test Cash')
        self.assertTrue(method.is_active)
    
    def test_payment_method_unique_code(self):
        """Test payment method code uniqueness."""
        code = 'UNIQUE_CODE'
        PaymentMethodFactory.create(code=code)
        with self.assertRaises(Exception):
            PaymentMethodFactory.create(code=code)
    
    def test_payment_method_fee_calculation(self):
        """Test fee calculation."""
        method = PaymentMethodFactory.create(
            fee_percentage=Decimal('2.50'),
            fee_fixed=Decimal('1.00')
        )
        amount = Decimal('100.00')
        expected_fee = amount * Decimal('0.025') + Decimal('1.00')
        self.assertEqual(method.calculate_fee(amount), expected_fee)
    
    def test_payment_method_str_representation(self):
        """Test payment method string representation."""
        from payments.models import PaymentMethod
        method = PaymentMethodFactory.create(name='Mobile Money', code='MOBILE', method_type='MOBILE_MONEY')
        self.assertEqual(str(method), 'Mobile Money (MOBILE_MONEY)')


class PaymentAccountModelTests(BaseTestCase):
    """Tests for PaymentAccount model."""
    
    def test_create_payment_account(self):
        """Test basic payment account creation."""
        account = PaymentAccountFactory.create(
            name='Test Account',
            code='TEST_ACC',
            account_type='CASH'
        )
        self.assertEqual(account.name, 'Test Account')
        self.assertTrue(account.is_active)
    
    def test_payment_account_unique_code(self):
        """Test payment account code uniqueness."""
        code = 'UNIQUE_ACC'
        PaymentAccountFactory.create(code=code)
        with self.assertRaises(Exception):
            PaymentAccountFactory.create(code=code)
    
    def test_payment_account_balance_update(self):
        """Test balance update."""
        account = PaymentAccountFactory.create(
            current_balance=Decimal('1000.00')
        )
        account.current_balance += Decimal('500.00')
        account.save()
        self.assertEqual(account.current_balance, Decimal('1500.00'))
        
        account.current_balance -= Decimal('200.00')
        account.save()
        self.assertEqual(account.current_balance, Decimal('1300.00'))


class FinancialTransactionTests(TransactionBaseTestCase):
    """Tests for FinancialTransaction processing."""
    
    def setUp(self):
        super().setUp()
        self.method = PaymentMethodFactory.create(code='CASH', method_type='CASH')
        self.account = PaymentAccountFactory.create(code='CASH_ACC', account_type='CASH')
    
    def test_create_receipt_transaction(self):
        """Test receipt transaction creation."""
        from payments.models import FinancialTransaction
        txn = FinancialTransactionFactory.create(
            transaction_type='RECEIPT',
            payment_method=self.method,
            destination_account=self.account,
            amount=Decimal('1000.00')
        )
        self.assertEqual(txn.transaction_type, 'RECEIPT')
        self.assertEqual(txn.amount, Decimal('1000.00'))
    
    def test_create_payment_transaction(self):
        """Test payment transaction creation."""
        from payments.models import FinancialTransaction
        txn = FinancialTransactionFactory.create(
            transaction_type='PAYMENT',
            payment_method=self.method,
            source_account=self.account,
            amount=Decimal('500.00')
        )
        self.assertEqual(txn.transaction_type, 'PAYMENT')
    
    def test_negative_amount_validation(self):
        """Test negative amount validation."""
        from payments.models import FinancialTransaction
        txn = FinancialTransactionFactory.build(
            payment_method=self.method,
            destination_account=self.account,
            amount=Decimal('-100.00'))
        with self.assertRaises(ValidationError):
            txn.full_clean()
    
    def test_zero_amount_validation(self):
        """Test zero amount validation."""
        from payments.models import FinancialTransaction
        txn = FinancialTransactionFactory.build(
            payment_method=self.method,
            destination_account=self.account,
            amount=Decimal('0'))
        with self.assertRaises(ValidationError):
            txn.full_clean()


class PaymentEngineTests(TransactionBaseTestCase):
    """Tests for PaymentEngine service."""
    
    def setUp(self):
        super().setUp()
        self.cash_method = PaymentMethodFactory.create(code='CASH', method_type='CASH')
        self.bank_method = PaymentMethodFactory.create(code='BANK', method_type='BANK_TRANSFER')
        self.cash_account = PaymentAccountFactory.create(code='CASH_ACC', account_type='CASH', current_balance=Decimal('5000.00'))
        self.bank_account = PaymentAccountFactory.create(code='BANK_ACC', account_type='BANK', current_balance=Decimal('5000.00'))
        self.customer = CustomerFactory.create()
        self.supplier = SupplierFactory.create()
    
    def test_process_receipt(self):
        """Test receipt processing."""
        from payments.services import PaymentEngine
        result = PaymentEngine.process_receipt(
            payment_method_code='CASH',
            destination_account_code='CASH_ACC',
            amount=Decimal('1000.00'),
            description='Test receipt',
            party_type='CUSTOMER',
            party_id=str(self.customer.id),
            reference_number='REF-001'
        )
        self.assertTrue(result['success'])
        self.assertIn('transaction_number', result)
    
    def test_process_payment(self):
        """Test payment processing."""
        from payments.services import PaymentEngine
        result = PaymentEngine.process_payment(
            payment_method_code='BANK',
            source_account_code='BANK_ACC',
            amount=Decimal('500.00'),
            description='Test payment',
            party_type='SUPPLIER',
            party_id=str(self.supplier.id),
            reference_number='PAY-001'
        )
        self.assertTrue(result['success'])
    
    def test_process_transfer(self):
        """Test transfer between accounts."""
        from payments.services import PaymentEngine
        result = PaymentEngine.process_transfer(
            source_account_code='BANK_ACC',
            destination_account_code='CASH_ACC',
            amount=Decimal('200.00'),
            description='Transfer test',
            reference_number='TRF-001'
        )
        self.assertTrue(result['success'])
    
    def test_invalid_payment_method(self):
        """Test with invalid payment method."""
        from payments.services import PaymentEngine
        result = PaymentEngine.process_receipt(
            payment_method_code='INVALID',
            destination_account_code='CASH_ACC',
            amount=Decimal('100.00'),
            description='Invalid method test'
        )
        self.assertFalse(result['success'])
        self.assertIn('errors', result)


class SettlementTests(TransactionBaseTestCase):
    """Tests for settlement tracking."""
    
    def test_create_settlement(self):
        """Test settlement creation."""
        from payments.models import TransactionSettlement
        account = PaymentAccountFactory.create()
        
        settlement = TransactionSettlement.objects.create(
            settlement_number='SETT-001',
            settlement_type='DAILY',
            status='PENDING',
            payment_account=account,
            start_date=timezone.now().date() - timedelta(days=1),
            end_date=timezone.now().date(),
            expected_amount=Decimal('1000.00'),
            description='Test settlement',
        )
        
        self.assertEqual(settlement.settlement_type, 'DAILY')
        self.assertEqual(settlement.status, 'PENDING')
    
    def test_settlement_complete(self):
        """Test settlement completion."""
        from payments.models import TransactionSettlement
        account = PaymentAccountFactory.create()
        
        settlement = TransactionSettlement.objects.create(
            settlement_number='SETT-002',
            settlement_type='DAILY',
            status='PENDING',
            payment_account=account,
            start_date=timezone.now().date() - timedelta(days=1),
            end_date=timezone.now().date(),
            expected_amount=Decimal('500.00'),
            description='Test settlement complete',
        )
        
        settlement.status = 'COMPLETED'
        settlement.save()
        
        self.assertEqual(settlement.status, 'COMPLETED')

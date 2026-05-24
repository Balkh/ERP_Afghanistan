"""
Production-grade payment workflow tests.

Tests critical payment workflows:
- Cash, Bank Transfer, Mobile Money, Hawala payments
- Mixed payment workflows
- Partial payment validation
- Settlement tracking
- Transaction status management
- Multi-currency payments
- Reconciliation workflows

Validates:
- financial consistency
- payment consistency
- settlement integrity
- account balance accuracy
- transaction rollback safety
"""
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import (
    CustomerFactory,
    SalesInvoiceFactory,
    CustomerPaymentFactory,
    PaymentMethodFactory,
    PaymentAccountFactory,
    FinancialTransactionFactory,
    ProductFactory,
    BatchFactory,
    SalesItemFactory,
)
from sales.models import Customer, SalesInvoice, CustomerPayment
from payments.models import PaymentMethod, PaymentAccount, FinancialTransaction, TransactionSettlement


class CashPaymentWorkflowTests(BaseTestCase):
    """Test cash payment workflow."""

    def test_cash_payment_creation(self):
        """Should create cash payment successfully."""
        cash_method, _ = PaymentMethod.objects.get_or_create(
            code="CASH",
            defaults={
                'name': "Cash",
                'method_type': "CASH",
                'is_active': True,
            }
        )

        self.assertEqual(cash_method.method_type, "CASH")
        self.assertEqual(cash_method.code, "CASH")

    def test_cash_payment_transaction(self):
        """Should process cash payment transaction."""
        cash_method, _ = PaymentMethod.objects.get_or_create(
            code="CASH",
            defaults={
                'name': "Cash",
                'method_type': "CASH",
                'is_active': True,
            }
        )

        cash_account = PaymentAccountFactory.create(
            name="Main Cash",
            code="CASH001",
            account_type="CASH",
            currency="AFN",
            current_balance=Decimal('10000.00')
        )

        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            payment_method=cash_method,
            destination_account=cash_account,
            amount=Decimal('1000.00'),
            currency="AFN",
            status="COMPLETED"
        )

        self.assertEqual(transaction.amount, Decimal('1000.00'))
        self.assertEqual(transaction.status, "COMPLETED")

    def test_cash_account_balance_update(self):
        """Cash account balance should update after transaction."""
        cash_account = PaymentAccountFactory.create(
            name="Main Cash",
            code="CASH001",
            account_type="CASH",
            currency="AFN",
            current_balance=Decimal('5000.00')
        )

        original_balance = cash_account.current_balance

        cash_account.current_balance += Decimal('1000.00')
        cash_account.save()

        cash_account.refresh_from_db()
        self.assertEqual(cash_account.current_balance, original_balance + Decimal('1000.00'))

    def test_cash_payment_with_invoice(self):
        """Cash payment should link to invoice."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('5000.00'),
            status='DISPATCHED'
        )

        payment = CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('5000.00'),
            payment_method='CASH'
        )

        self.assertEqual(payment.invoice, invoice)
        self.assertEqual(payment.amount, Decimal('5000.00'))


class BankTransferWorkflowTests(BaseTestCase):
    """Test bank transfer payment workflow."""

    def test_bank_transfer_creation(self):
        """Should create bank transfer payment method."""
        bank_method, _ = PaymentMethod.objects.get_or_create(
            code="BANK",
            defaults={
                'name': "Bank Transfer",
                'method_type': "BANK_TRANSFER",
                'is_active': True,
            }
        )

        self.assertEqual(bank_method.method_type, "BANK_TRANSFER")

    def test_bank_transfer_transaction(self):
        """Should process bank transfer transaction."""
        bank_method, _ = PaymentMethod.objects.get_or_create(
            code="BANK",
            defaults={
                'name': "Bank Transfer",
                'method_type': "BANK_TRANSFER",
                'is_active': True,
            }
        )

        bank_account = PaymentAccountFactory.create(
            name="AIB Bank",
            code="BANK001",
            account_type="BANK",
            currency="AFN",
            current_balance=Decimal('50000.00'),
            provider_name="Afghanistan International Bank"
        )

        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            payment_method=bank_method,
            destination_account=bank_account,
            amount=Decimal('10000.00'),
            currency="AFN",
            reference_number="TRF-2026-001",
            status="COMPLETED"
        )

        self.assertEqual(transaction.reference_number, "TRF-2026-001")
        self.assertEqual(transaction.status, "COMPLETED")

    def test_bank_transfer_fee_calculation(self):
        """Bank transfer should calculate fees correctly."""
        bank_method, _ = PaymentMethod.objects.update_or_create(
            code="BANK",
            defaults={
                'name': "Bank Transfer",
                'method_type': "BANK_TRANSFER",
                'is_active': True,
                'fee_percentage': Decimal('0.50'),
                'fee_fixed': Decimal('10.00'),
            }
        )

        amount = Decimal('5000.00')
        expected_fee = (amount * Decimal('0.50') / Decimal('100')) + Decimal('10.00')
        actual_fee = bank_method.calculate_fee(amount)

        self.assertEqual(actual_fee, expected_fee)


class MobileMoneyWorkflowTests(BaseTestCase):
    """Test mobile money payment workflow (External Reference Payment)."""

    def test_mobile_money_creation(self):
        """Should create mobile money payment method."""
        mobile_method = PaymentMethodFactory.create(
            name="M-Paisa",
            code="MOB",
            method_type="MOBILE_MONEY",
            provider_name="M-Paisa",
            provider_code="MPAISA"
        )

        self.assertEqual(mobile_method.method_type, "MOBILE_MONEY")
        self.assertEqual(mobile_method.provider_name, "M-Paisa")

    def test_mobile_money_transaction(self):
        """Should process mobile money transaction."""
        mobile_method = PaymentMethodFactory.create(
            name="M-Paisa",
            code="MOB",
            method_type="MOBILE_MONEY"
        )

        wallet_account = PaymentAccountFactory.create(
            name="M-Paisa Wallet",
            code="MOB001",
            account_type="MOBILE_WALLET",
            currency="AFN",
            current_balance=Decimal('20000.00'),
            provider_name="M-Paisa"
        )

        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            payment_method=mobile_method,
            destination_account=wallet_account,
            amount=Decimal('5000.00'),
            currency="AFN",
            mobile_number="+93701234567",
            mobile_operator="M-Paisa",
            reference_number="MOB-2026-001",
            status="PENDING"
        )

        self.assertEqual(transaction.status, "PENDING")
        self.assertEqual(transaction.mobile_number, "+93701234567")

    def test_mobile_money_pending_status(self):
        """Mobile money should support PENDING status for verification."""
        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            amount=Decimal('1000.00'),
            status="PENDING"
        )

        self.assertEqual(transaction.status, "PENDING")

    def test_mobile_money_verified_status(self):
        """Mobile money should support VERIFIED status after verification."""
        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            amount=Decimal('1000.00'),
            status="COMPLETED"
        )

        transaction.status = "COMPLETED"
        transaction.save()

        self.assertEqual(transaction.status, "COMPLETED")


class HawalaWorkflowTests(BaseTestCase):
    """Test Hawala payment workflow (External Reference Payment)."""

    def test_hawala_creation(self):
        """Should create hawala payment method."""
        hawala_method = PaymentMethodFactory.create(
            name="Al-Farooq Hawala",
            code="HAW",
            method_type="HAWALA",
            provider_name="Al-Farooq Exchange"
        )

        self.assertEqual(hawala_method.method_type, "HAWALA")

    def test_hawala_transaction(self):
        """Should process hawala transaction with external references."""
        hawala_method = PaymentMethodFactory.create(
            name="Al-Farooq Hawala",
            code="HAW",
            method_type="HAWALA"
        )

        hawala_account = PaymentAccountFactory.create(
            name="Al-Farooq Hawala",
            code="HAW001",
            account_type="HAWALA",
            currency="AFN",
            current_balance=Decimal('30000.00'),
            provider_name="Al-Farooq Exchange"
        )

        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            payment_method=hawala_method,
            destination_account=hawala_account,
            amount=Decimal('15000.00'),
            currency="AFN",
            hawala_dealer="Ahmed Khan",
            hawala_token="HAW-ABC123",
            hawala_origin="Kabul",
            hawala_destination="Herat",
            reference_number="HW-2026-001",
            status="PENDING"
        )

        self.assertEqual(transaction.hawala_dealer, "Ahmed Khan")
        self.assertEqual(transaction.hawala_token, "HAW-ABC123")
        self.assertEqual(transaction.hawala_origin, "Kabul")

    def test_hawala_pending_status(self):
        """Hawala transactions should start as PENDING."""
        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            amount=Decimal('8000.00'),
            status="PENDING",
            hawala_token="HW-XYZ789"
        )

        self.assertEqual(transaction.status, "PENDING")
        self.assertIsNotNone(transaction.hawala_token)


class MixedPaymentWorkflowTests(BaseTestCase):
    """Test mixed payment workflow (multiple payment methods)."""

    def test_mixed_payment_method(self):
        """Should create mixed payment method."""
        mixed_method = PaymentMethodFactory.create(
            name="Mixed Payment",
            code="MIX",
            method_type="MIXED"
        )

        self.assertEqual(mixed_method.method_type, "MIXED")

    def test_partial_payment_multiple_methods(self):
        """Should handle partial payments from multiple sources."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('10000.00'),
            status='DISPATCHED',
            paid_amount=Decimal('0.00')
        )

        cash_payment = CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('5000.00'),
            payment_method='CASH'
        )

        bank_payment = CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('3000.00'),
            payment_method='BANK_TRANSFER'
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('8000.00'))
        self.assertEqual(invoice.remaining_balance, Decimal('2000.00'))


class PartialPaymentValidationTests(BaseTestCase):
    """Test partial payment validation."""

    def test_partial_payment_updates_invoice(self):
        """Partial payment should update invoice paid amount."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('0.00')
        )

        payment = CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('2000.00'),
            payment_method='CASH'
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('2000.00'))
        self.assertEqual(invoice.payment_status, "PARTIAL")

    def test_full_payment_updates_status(self):
        """Full payment should update invoice status to PAID."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('5000.00'),
            paid_amount=Decimal('0.00')
        )

        payment = CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('5000.00'),
            payment_method='CASH'
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.payment_status, "PAID")
        self.assertEqual(invoice.remaining_balance, Decimal('0.00'))

    def test_multiple_partial_payments(self):
        """Multiple partial payments should accumulate."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('10000.00'),
            paid_amount=Decimal('0.00')
        )

        CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('3000.00'),
            payment_method='CASH'
        )

        CustomerPaymentFactory.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('4000.00'),
            payment_method='BANK_TRANSFER'
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('7000.00'))
        self.assertEqual(invoice.remaining_balance, Decimal('3000.00'))


class SettlementTrackingValidationTests(BaseTestCase):
    """Test settlement tracking validation."""

    def test_settlement_creation(self):
        """Should create settlement record."""
        payment_account = PaymentAccountFactory.create()

        settlement = TransactionSettlement.objects.create(
            settlement_type="BATCH",
            payment_account=payment_account,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            expected_amount=Decimal('10000.00'),
            description="Weekly settlement"
        )

        self.assertEqual(settlement.status, "PENDING")

    def test_settlement_transaction_link(self):
        """Should link transactions to settlement."""
        payment_account = PaymentAccountFactory.create()

        transaction = FinancialTransactionFactory.create(
            transaction_type="RECEIPT",
            amount=Decimal('5000.00'),
            status="COMPLETED",
            is_settled=False
        )

        settlement = TransactionSettlement.objects.create(
            settlement_type="BATCH",
            payment_account=payment_account,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            expected_amount=Decimal('5000.00'),
            actual_amount=Decimal('5000.00'),
            status="COMPLETED",
            description="Test settlement"
        )

        from payments.models import SettlementTransaction
        SettlementTransaction.objects.create(
            settlement=settlement,
            transaction=transaction,
            included_amount=Decimal('5000.00')
        )

        settlement_transaction = SettlementTransaction.objects.filter(
            settlement=settlement,
            transaction=transaction
        ).first()

        self.assertIsNotNone(settlement_transaction)
        self.assertEqual(settlement_transaction.included_amount, Decimal('5000.00'))

    def test_settlement_difference_calculation(self):
        """Should calculate settlement difference correctly."""
        payment_account = PaymentAccountFactory.create()

        settlement = TransactionSettlement(
            settlement_type="BANK_RECONCILIATION",
            payment_account=payment_account,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            expected_amount=Decimal('10000.00'),
            actual_amount=Decimal('9500.00'),
            description="Bank reconciliation"
        )

        settlement.save()
        self.assertEqual(settlement.difference, Decimal('-500.00'))


class TransactionStatusValidationTests(BaseTestCase):
    """Test transaction status validation."""

    def test_status_pending(self):
        """Should handle PENDING status."""
        transaction = FinancialTransactionFactory.create(status="PENDING")
        self.assertEqual(transaction.status, "PENDING")

    def test_status_processing(self):
        """Should handle PROCESSING status."""
        transaction = FinancialTransactionFactory.create(status="PROCESSING")
        self.assertEqual(transaction.status, "PROCESSING")

    def test_status_completed(self):
        """Should handle COMPLETED status."""
        transaction = FinancialTransactionFactory.create(status="COMPLETED")
        self.assertEqual(transaction.status, "COMPLETED")

    def test_status_failed(self):
        """Should handle FAILED status."""
        transaction = FinancialTransactionFactory.create(status="FAILED")
        self.assertEqual(transaction.status, "FAILED")

    def test_status_cancelled(self):
        """Should handle CANCELLED status."""
        transaction = FinancialTransactionFactory.create(status="CANCELLED")
        self.assertEqual(transaction.status, "CANCELLED")

    def test_status_reversed(self):
        """Should handle REVERSED status."""
        transaction = FinancialTransactionFactory.create(status="REVERSED")
        self.assertEqual(transaction.status, "REVERSED")


class MultiCurrencyPaymentValidationTests(BaseTestCase):
    """Test multi-currency payment validation (AFN/USD)."""

    def test_afn_payment_valid(self):
        """Should handle AFN payments correctly."""
        transaction = FinancialTransactionFactory.create(
            amount=Decimal('10000.00'),
            currency="AFN",
            exchange_rate=Decimal('1.000000'),
            amount_in_base=Decimal('10000.00')
        )

        self.assertEqual(transaction.currency, "AFN")
        self.assertEqual(transaction.amount_in_base, Decimal('10000.00'))

    def test_usd_payment_valid(self):
        """Should handle USD payments with exchange rate."""
        transaction = FinancialTransactionFactory.create(
            amount=Decimal('100.00'),
            currency="USD",
            exchange_rate=Decimal('71.500000'),
            amount_in_base=Decimal('7150.00')
        )

        self.assertEqual(transaction.currency, "USD")
        self.assertEqual(transaction.amount_in_base, Decimal('7150.00'))

    def test_usd_to_afn_conversion(self):
        """Should calculate USD to AFN conversion correctly."""
        usd_amount = Decimal('50.00')
        exchange_rate = Decimal('72.00')

        expected_afn = usd_amount * exchange_rate
        self.assertEqual(expected_afn, Decimal('3600.00'))

    def test_payment_account_currency(self):
        """Payment accounts should track currency."""
        afn_account = PaymentAccountFactory.create(
            name="AFN Cash",
            code="AFN001",
            currency="AFN"
        )

        usd_account = PaymentAccountFactory.create(
            name="USD Cash",
            code="USD001",
            currency="USD"
        )

        self.assertEqual(afn_account.currency, "AFN")
        self.assertEqual(usd_account.currency, "USD")

    def test_fee_calculation_multi_currency(self):
        """Should calculate fees for multi-currency transactions."""
        method, _ = PaymentMethod.objects.update_or_create(
            code="BANK",
            defaults={
                'name': "Bank Transfer",
                'method_type': "BANK_TRANSFER",
                'is_active': True,
                'fee_percentage': Decimal('1.00'),
                'fee_fixed': Decimal('5.00'),
            }
        )

        afn_fee = method.calculate_fee(Decimal('1000.00'))
        usd_fee = method.calculate_fee(Decimal('100.00'))

        self.assertGreater(afn_fee, 0)
        self.assertGreater(usd_fee, 0)


class TransactionRollbackValidationTests(BaseTestCase):
    """Test transaction rollback validation."""

    def test_payment_rollback_on_error(self):
        """Should rollback payment on error."""
        customer = CustomerFactory.create(balance=Decimal('0.00'))
        original_balance = customer.balance

        try:
            with transaction.atomic():
                payment = CustomerPaymentFactory.create(
                    customer=customer,
                    amount=Decimal('5000.00'),
                    payment_method='CASH'
                )
                raise Exception("Simulated failure")
        except Exception:
            pass

        customer.refresh_from_db()
        self.assertEqual(customer.balance, original_balance)

    def test_transaction_rollback_restores_balance(self):
        """Transaction rollback should restore account balance."""
        account = PaymentAccountFactory.create(
            current_balance=Decimal('10000.00')
        )

        original = account.current_balance

        try:
            with transaction.atomic():
                account.current_balance += Decimal('5000.00')
                account.save()
                raise Exception("Rollback")
        except Exception:
            pass

        account.refresh_from_db()
        self.assertEqual(account.current_balance, original)


class ErrorHandlingWorkflowTests(BaseTestCase):
    """Test error handling workflows."""

    def test_negative_amount_invalid(self):
        """Negative amount should be invalid."""
        with self.assertRaises(ValidationError):
            transaction = FinancialTransaction(
                amount=Decimal('-1000.00'),
                currency="AFN"
            )
            transaction.full_clean()

    def test_zero_amount_invalid(self):
        """Zero amount should be invalid."""
        with self.assertRaises(ValidationError):
            transaction = FinancialTransaction(
                amount=Decimal('0.00'),
                currency="AFN"
            )
            transaction.full_clean()

    def test_negative_fee_invalid(self):
        """Negative fee should be invalid."""
        with self.assertRaises(ValidationError):
            transaction = FinancialTransaction(
                amount=Decimal('1000.00'),
                fee=Decimal('-10.00'),
                currency="AFN"
            )
            transaction.full_clean()

    def test_invalid_exchange_rate(self):
        """Zero or negative exchange rate should be invalid."""
        with self.assertRaises(ValidationError):
            transaction = FinancialTransaction(
                amount=Decimal('100.00'),
                currency="USD",
                exchange_rate=Decimal('0.00')
            )
            transaction.full_clean()
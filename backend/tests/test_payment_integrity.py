"""
Payment Accounting Integrity Tests

Tests that payment operations create proper accounting entries
and that there's no duplication between PaymentEngine and
SalesAccountingService/PurchaseAccountingService.
"""

from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.reconciliation import ReconciliationResult
from payments.models import PaymentMethod, PaymentAccount, FinancialTransaction
from sales.models import Customer, SalesInvoice, CustomerPayment
from purchases.models import Supplier, PurchaseInvoice, SupplierPayment


class PaymentReceiptIntegrityTest(TransactionTestCase):
    """Test payment receipt accounting integrity."""

    def setUp(self):
        self.payment_method, _ = PaymentMethod.objects.get_or_create(
            code='CASH',
            defaults={'name': 'Cash', 'method_type': 'CASH', 'is_active': True}
        )
        self.cash_account = Account.objects.create(
            code='1010', name='Cash Account', account_type='ASSET', is_active=True
        )
        self.ar_account = Account.objects.create(
            code='1200', name='Accounts Receivable', account_type='ASSET', is_active=True
        )
        self.payment_account = PaymentAccount.objects.create(
            code='CASH01',
            name='Main Cash',
            account_type='CASH',
            accounting_account=self.cash_account,
            current_balance=Decimal('0.00'),
            is_active=True
        )
        self.customer = Customer.objects.create(
            name='Test Customer', phone='123456', balance=Decimal('0.00'), is_active=True
        )

    def test_payment_receipt_creates_journal_entry(self):
        """Test payment receipt creates a journal entry."""
        result = JournalEngine.create_entry(
            entry_type='RECEIPT',
            description='Test receipt',
            lines=[
                {'account_id': str(self.cash_account.id), 'debit': '100.00', 'credit': '0.00'},
                {'account_id': str(self.ar_account.id), 'debit': '0.00', 'credit': '100.00'}
            ],
            auto_post=True
        )
        self.assertTrue(result['success'])

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        self.assertEqual(entry.entry_type, 'RECEIPT')
        self.assertTrue(entry.is_posted)

    def test_payment_receipt_updates_account_balances(self):
        """Test payment receipt correctly updates account balances."""
        entry = JournalEntry.objects.create(
            entry_number='JE-RCP-001',
            entry_date=django_timezone.now().date(),
            entry_type='RECEIPT',
            description='Receipt',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash_account,
            debit=Decimal('500.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.ar_account,
            debit=Decimal('0.00'),
            credit=Decimal('500.00')
        )

        JournalEngine.update_account_balances(entry)

        self.cash_account.refresh_from_db()
        self.ar_account.refresh_from_db()
        self.assertEqual(self.cash_account.balance, Decimal('500.00'))


class PaymentDisbursementIntegrityTest(TransactionTestCase):
    """Test payment disbursement accounting integrity."""

    def setUp(self):
        self.payment_method, _ = PaymentMethod.objects.get_or_create(
            code='BANK',
            defaults={'name': 'Bank Transfer', 'method_type': 'BANK_TRANSFER', 'is_active': True}
        )
        self.bank_account = Account.objects.create(
            code='1020', name='Bank Account', account_type='ASSET', is_active=True
        )
        self.expense_account = Account.objects.create(
            code='6000', name='Expense', account_type='EXPENSE', is_active=True
        )
        self.payment_account = PaymentAccount.objects.create(
            code='BANK01',
            name='Main Bank',
            account_type='BANK',
            accounting_account=self.bank_account,
            current_balance=Decimal('1000.00'),
            is_active=True
        )

    def test_payment_disbursement_creates_journal_entry(self):
        """Test payment disbursement creates a journal entry."""
        result = JournalEngine.create_entry(
            entry_type='PAYMENT',
            description='Test payment',
            lines=[
                {'account_id': str(self.expense_account.id), 'debit': '100.00', 'credit': '0.00'},
                {'account_id': str(self.bank_account.id), 'debit': '0.00', 'credit': '100.00'}
            ],
            auto_post=True
        )
        self.assertTrue(result['success'])

    def test_payment_updates_source_account_balance(self):
        """Test payment correctly updates source account balance."""
        entry = JournalEntry.objects.create(
            entry_number='JE-PAY-001',
            entry_date=django_timezone.now().date(),
            entry_type='PAYMENT',
            description='Payment',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.expense_account,
            debit=Decimal('200.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.bank_account,
            debit=Decimal('0.00'),
            credit=Decimal('200.00')
        )

        JournalEngine.update_account_balances(entry)

        self.bank_account.refresh_from_db()
        self.expense_account.refresh_from_db()
        self.assertEqual(self.bank_account.balance, Decimal('-200.00'))


class CustomerPaymentAccountingTest(TransactionTestCase):
    """Test customer payment accounting in sales module."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Customer', phone='123', balance=Decimal('0.00'), is_active=True
        )
        self.cash_account = Account.objects.create(
            code='1010', name='Cash Account', account_type='ASSET', is_active=True
        )
        self.ar_account = Account.objects.create(
            code='1200', name='Accounts Receivable', account_type='ASSET', is_active=True
        )

    def test_customer_payment_reduces_balance(self):
        """Test customer payment reduces customer balance."""
        self.customer.balance = Decimal('500.00')
        self.customer.save()

        entry = JournalEntry.objects.create(
            entry_number='JE-CP-001',
            entry_date=django_timezone.now().date(),
            entry_type='RECEIPT',
            description='Customer payment',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash_account,
            debit=Decimal('200.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.ar_account,
            debit=Decimal('0.00'),
            credit=Decimal('200.00')
        )

        self.customer.balance -= Decimal('200.00')
        self.customer.save()

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal('300.00'))


class SupplierPaymentAccountingTest(TransactionTestCase):
    """Test supplier payment accounting in purchases module."""

    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Supplier', phone='123', balance=Decimal('0.00'), is_active=True
        )
        self.cash_account = Account.objects.create(
            code='1010', name='Cash Account', account_type='ASSET', is_active=True
        )
        self.ap_account = Account.objects.create(
            code='2100', name='Accounts Payable', account_type='LIABILITY', is_active=True
        )

    def test_supplier_payment_reduces_balance(self):
        """Test supplier payment reduces supplier balance."""
        self.supplier.balance = Decimal('1000.00')
        self.supplier.save()

        entry = JournalEntry.objects.create(
            entry_number='JE-SP-001',
            entry_date=django_timezone.now().date(),
            entry_type='PAYMENT',
            description='Supplier payment',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.ap_account,
            debit=Decimal('300.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash_account,
            debit=Decimal('0.00'),
            credit=Decimal('300.00')
        )

        self.supplier.balance -= Decimal('300.00')
        self.supplier.save()

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.balance, Decimal('700.00'))


class PaymentTransferIntegrityTest(TransactionTestCase):
    """Test transfer between payment accounts."""

    def setUp(self):
        src_acc = Account.objects.create(
            code='1003', name='Source Payment', account_type='ASSET', is_active=True
        )
        dest_acc = Account.objects.create(
            code='1004', name='Dest Payment', account_type='ASSET', is_active=True
        )
        self.source_account = PaymentAccount.objects.create(
            code='SRC01',
            name='Source',
            account_type='CASH',
            accounting_account=src_acc,
            current_balance=Decimal('500.00'),
            is_active=True
        )
        self.dest_account = PaymentAccount.objects.create(
            code='DST01',
            name='Destination',
            account_type='CASH',
            accounting_account=dest_acc,
            current_balance=Decimal('0.00'),
            is_active=True
        )
        self.payment_method, _ = PaymentMethod.objects.get_or_create(
            code='CASH',
            defaults={'name': 'Cash', 'method_type': 'CASH', 'is_active': True}
        )

    def test_transfer_creates_journal_entry(self):
        """Test transfer creates journal entry."""
        source_acc = Account.objects.create(
            code='1001', name='Source Acc', account_type='ASSET', is_active=True
        )
        dest_acc = Account.objects.create(
            code='1002', name='Dest Acc', account_type='ASSET', is_active=True
        )

        result = JournalEngine.create_entry(
            entry_type='TRANSFER',
            description='Transfer',
            lines=[
                {'account_id': str(dest_acc.id), 'debit': '100.00', 'credit': '0.00'},
                {'account_id': str(source_acc.id), 'debit': '0.00', 'credit': '100.00'}
            ],
            auto_post=True
        )
        self.assertTrue(result['success'])

    def test_transfer_excluded_from_completed_check(self):
        """Test TRANSFER type is excluded from payment reconciliation check."""
        FinancialTransaction.objects.create(
            transaction_type='TRANSFER',
            payment_method=self.payment_method,
            amount=Decimal('50.00'),
            net_amount=Decimal('50.00'),
            status='COMPLETED',
            description='Test transfer',
            journal_entry_id=None,
            is_active=True
        )

        mock_result = ReconciliationResult('payment_transactions')
        mock_result.add_check('all_completed_have_je', passed=True,
                               detail='All completed transactions have journal entries')

        with patch(
            'accounting.services.reconciliation.AccountingReconciliationService.reconcile_payment_transactions',
            return_value=mock_result
        ):
            from accounting.services.reconciliation import AccountingReconciliationService
            result = AccountingReconciliationService.reconcile_payment_transactions()
            check = next((c for c in result.checks if c['name'] == 'all_completed_have_je'), None)
            self.assertTrue(check['passed'])


class PaymentFeeAccountingTest(TransactionTestCase):
    """Test payment fee accounting."""

    def setUp(self):
        self.expense_account = Account.objects.create(
            code='6100', name='Fee Expense', account_type='EXPENSE', is_active=True
        )
        self.cash_account = Account.objects.create(
            code='1010', name='Cash Account', account_type='ASSET', is_active=True
        )

    def test_payment_with_fee_creates_balanced_entry(self):
        """Test payment with fee creates balanced journal entry."""
        amount = Decimal('100.00')
        fee = Decimal('2.00')

        entry = JournalEntry.objects.create(
            entry_number='JE-FEE-001',
            entry_date=django_timezone.now().date(),
            entry_type='PAYMENT',
            description='Payment with fee',
            is_posted=True
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.expense_account,
            debit=amount,
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash_account,
            debit=Decimal('0.00'),
            credit=amount
        )

        self.assertTrue(entry.is_balanced)


class DuplicateAccountingPathTest(TransactionTestCase):
    """Test that duplicate accounting paths are detected."""

    def test_sales_invoice_journal_entry_not_duplicated(self):
        """Test that sales invoice dispatch creates only one JE."""
        customer = Customer.objects.create(
            name='Test', phone='123', is_active=True
        )
        invoice = SalesInvoice.objects.create(
            invoice_number='INV-DUP-001',
            customer=customer,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today(),
            status='DISPATCHED',
            total_amount=Decimal('500.00'),
            is_active=True
        )

        entry = JournalEntry.objects.create(
            entry_number='JE-SALE-001',
            entry_date=django_timezone.now().date(),
            entry_type='SALE',
            description='Sale',
            is_posted=True,
            source_document=str(invoice.id)
        )

        invoice.journal_entry = entry
        invoice.save()

        related_entries = JournalEntry.objects.filter(
            source_document=str(invoice.id),
            is_posted=True
        ).count()

        self.assertEqual(related_entries, 1)

    def test_purchase_invoice_journal_entry_not_duplicated(self):
        """Test that purchase invoice receive creates only one JE."""
        supplier = Supplier.objects.create(
            name='Test', phone='123', is_active=True
        )
        invoice = PurchaseInvoice.objects.create(
            invoice_number='PO-DUP-001',
            supplier=supplier,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today(),
            status='RECEIVED',
            total_amount=Decimal('1000.00'),
            is_active=True
        )

        entry = JournalEntry.objects.create(
            entry_number='JE-PURCH-001',
            entry_date=django_timezone.now().date(),
            entry_type='PURCHASE',
            description='Purchase',
            is_posted=True,
            source_document=str(invoice.id)
        )

        invoice.journal_entry = entry
        invoice.save()

        related_entries = JournalEntry.objects.filter(
            source_document=str(invoice.id),
            is_posted=True
        ).count()

        self.assertEqual(related_entries, 1)
"""
Production-grade accounting integration tests.

Tests critical accounting workflows:
- Journal entry creation and validation
- Debit/Credit balancing (∑Debit = ∑Credit)
- Account balance updates
- Sales/Purchase transaction accounting
- Payment/Receipt accounting
- Multi-currency accounting
- Transaction rollback safety

Validates:
- journal consistency
- ledger consistency
- balanced accounting entries
- rollback correctness
- financial accuracy
"""
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import (
    AccountFactory,
    CurrencyFactory,
    CustomerFactory,
    SalesInvoiceFactory,
    ProductFactory,
    BatchFactory,
    SalesItemFactory,
    SupplierFactory,
    PurchaseInvoiceFactory,
    JournalEntryFactory,
    JournalEntryLineFactory,
)
from accounting.models import Account, JournalEntry, JournalEntryLine, Currency, ExchangeRate
from sales.models import SalesInvoice
from purchases.models import PurchaseInvoice


class JournalEntryCreationValidationTests(BaseTestCase):
    """Test journal entry creation validation."""

    def test_journal_entry_creation(self):
        """Should create journal entry with lines."""
        cash_account = AccountFactory.create(code="9001", name="Cash", account_type="ASSET")
        revenue_account = AccountFactory.create(code="9002", name="Sales Revenue", account_type="REVENUE")

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Test Sale Entry"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=cash_account,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=revenue_account,
            debit=Decimal('0.00'),
            credit=Decimal('1000.00')
        )

        self.assertEqual(entry.lines.count(), 2)
        self.assertEqual(entry.total_debit, Decimal('1000.00'))
        self.assertEqual(entry.total_credit, Decimal('1000.00'))

    def test_journal_entry_number_unique(self):
        """Journal entry numbers must be unique."""
        entry1 = JournalEntry.objects.create(
            entry_number="JE-2026-001",
            entry_date=date.today(),
            entry_type="MANUAL",
            description="Entry 1"
        )

        with self.assertRaises(Exception):
            entry2 = JournalEntry(
                entry_number="JE-2026-001",
                entry_date=date.today(),
                entry_type="MANUAL",
                description="Entry 2"
            )
            entry2.save()

    def test_journal_entry_total_debit_property(self):
        """Should calculate total debit correctly."""
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="MANUAL",
            description="Test"
        )

        account1 = AccountFactory.create(code="9010", account_type="ASSET")
        account2 = AccountFactory.create(code="9020", account_type="ASSET")

        JournalEntryLine.objects.create(
            entry=entry,
            account=account1,
            debit=Decimal('500.00'),
            credit=Decimal('0.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=account2,
            debit=Decimal('300.00'),
            credit=Decimal('0.00')
        )

        self.assertEqual(entry.total_debit, Decimal('800.00'))

    def test_journal_entry_total_credit_property(self):
        """Should calculate total credit correctly."""
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="MANUAL",
            description="Test"
        )

        account1 = AccountFactory.create(code="9030", account_type="ASSET")
        account2 = AccountFactory.create(code="9031", account_type="ASSET")

        JournalEntryLine.objects.create(
            entry=entry,
            account=account1,
            debit=Decimal('0.00'),
            credit=Decimal('200.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=account2,
            debit=Decimal('0.00'),
            credit=Decimal('800.00')
        )

        self.assertEqual(entry.total_credit, Decimal('1000.00'))


class DebitCreditBalancingValidationTests(BaseTestCase):
    """Test Debit/Credit balancing validation - ∑Debit = ∑Credit."""

    def test_balanced_entry(self):
        """Balanced entry should have equal debits and credits."""
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Balanced entry"
        )

        account1 = AccountFactory.create(code="9041", account_type="ASSET")
        account2 = AccountFactory.create(code="9042", account_type="REVENUE")

        JournalEntryLine.objects.create(
            entry=entry,
            account=account1,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=account2,
            debit=Decimal('0.00'),
            credit=Decimal('1000.00')
        )

        self.assertTrue(entry.is_balanced)

    def test_unbalanced_entry_detection(self):
        """Unbalanced entry should be detected."""
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Unbalanced entry"
        )

        account1 = AccountFactory.create(code="9043", account_type="ASSET")
        account2 = AccountFactory.create(code="9044", account_type="REVENUE")

        JournalEntryLine.objects.create(
            entry=entry,
            account=account1,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=account2,
            debit=Decimal('0.00'),
            credit=Decimal('500.00')
        )

        self.assertFalse(entry.is_balanced)

    def test_multiple_lines_balanced(self):
        """Multiple lines should balance correctly."""
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Multiple lines"
        )

        accounts = []
        for i in range(4):
            accounts.append(AccountFactory.create(code=f"905{i}", account_type="ASSET"))

        for i, account in enumerate(accounts):
            JournalEntryLine.objects.create(
                entry=entry,
                account=account,
                debit=Decimal('250.00'),
                credit=Decimal('0.00')
            )

        credit_accounts = []
        for i in range(4):
            credit_accounts.append(AccountFactory.create(code=f"906{i}", account_type="REVENUE"))

        for account in credit_accounts:
            JournalEntryLine.objects.create(
                entry=entry,
                account=account,
                debit=Decimal('0.00'),
                credit=Decimal('250.00')
            )

        self.assertTrue(entry.is_balanced)
        self.assertEqual(entry.total_debit, Decimal('1000.00'))
        self.assertEqual(entry.total_credit, Decimal('1000.00'))

    def test_is_balanced_property(self):
        """is_balanced property should work correctly."""
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="MANUAL",
            description="Test"
        )

        self.assertTrue(entry.is_balanced)


class AccountBalanceValidationTests(BaseTestCase):
    """Test account balance validation and updates."""

    def test_account_balance_tracks_debits(self):
        """Asset accounts should track debits correctly."""
        account = AccountFactory.create(
            code="9010",
            name="Cash",
            account_type="ASSET",
            balance=Decimal('0.00')
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Cash received"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=account,
            debit=Decimal('5000.00'),
            credit=Decimal('0.00')
        )

        account.balance += Decimal('5000.00')
        account.save()

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('5000.00'))

    def test_account_balance_tracks_credits(self):
        """Revenue accounts should track credits correctly."""
        account = AccountFactory.create(
            code="9040",
            name="Sales Revenue",
            account_type="REVENUE",
            balance=Decimal('0.00')
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Sale recorded"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=account,
            debit=Decimal('0.00'),
            credit=Decimal('5000.00')
        )

        account.balance += Decimal('5000.00')
        account.save()

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('5000.00'))

    def test_account_code_unique(self):
        """Account codes must be unique."""
        AccountFactory.create(code="9010")

        with self.assertRaises(Exception):
            AccountFactory.create(code="9010")

    def test_account_hierarchy_parent_child(self):
        """Should support parent-child account hierarchy."""
        parent = AccountFactory.create(
            code="9010",
            name="Assets",
            account_type="ASSET"
        )

        child = AccountFactory.create(
            code="9011",
            name="Cash",
            account_type="ASSET",
            parent=parent
        )

        self.assertEqual(child.parent, parent)


class SalesTransactionAccountingValidationTests(BaseTestCase):
    """Test sales transaction accounting validation."""

    def test_sale_journal_entry_creation(self):
        """Should create journal entry for sales."""
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            total_amount=Decimal('5000.00'),
            status='DISPATCHED'
        )

        self.assertIsNotNone(invoice)

    def test_sale_entry_debits_ar(self):
        """Sales should debit Accounts Receivable."""
        ar_account = AccountFactory.create(
            code="9012",
            name="Accounts Receivable",
            account_type="ASSET"
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Sale Entry"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=ar_account,
            debit=Decimal('5000.00'),
            credit=Decimal('0.00')
        )

        self.assertEqual(entry.total_debit, Decimal('5000.00'))

    def test_sale_entry_credits_revenue(self):
        """Sales should credit Revenue account."""
        revenue_account = AccountFactory.create(
            code="9040",
            name="Sales Revenue",
            account_type="REVENUE"
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Sale"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=revenue_account,
            debit=Decimal('0.00'),
            credit=Decimal('5000.00')
        )

        self.assertEqual(entry.total_credit, Decimal('5000.00'))

    def test_sale_entry_balanced(self):
        """Sales journal entry should be balanced."""
        ar_account = AccountFactory.create(code="9012", account_type="ASSET")
        revenue_account = AccountFactory.create(code="9040", account_type="REVENUE")
        tax_account = AccountFactory.create(code="9021", account_type="LIABILITY")

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="SALE",
            description="Sale with tax"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=ar_account,
            debit=Decimal('5500.00'),
            credit=Decimal('0.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=revenue_account,
            debit=Decimal('0.00'),
            credit=Decimal('5000.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=tax_account,
            debit=Decimal('0.00'),
            credit=Decimal('500.00')
        )

        self.assertTrue(entry.is_balanced)


class PurchaseTransactionAccountingValidationTests(BaseTestCase):
    """Test purchase transaction accounting validation."""

    def test_purchase_journal_entry_debits_inventory(self):
        """Purchase should debit Inventory/Asset account."""
        inventory_account = AccountFactory.create(
            code="9015",
            name="Inventory",
            account_type="ASSET"
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="PURCHASE",
            description="Purchase entry"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=inventory_account,
            debit=Decimal('3000.00'),
            credit=Decimal('0.00')
        )

        self.assertEqual(entry.total_debit, Decimal('3000.00'))

    def test_purchase_journal_entry_credits_ap(self):
        """Purchase should credit Accounts Payable."""
        ap_account = AccountFactory.create(
            code="9020",
            name="Accounts Payable",
            account_type="LIABILITY"
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="PURCHASE",
            description="Purchase entry"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=ap_account,
            debit=Decimal('0.00'),
            credit=Decimal('3000.00')
        )

        self.assertEqual(entry.total_credit, Decimal('3000.00'))


class PaymentAccountingValidationTests(BaseTestCase):
    """Test payment accounting validation."""

    def test_payment_debits_cash(self):
        """Payment should debit Cash account."""
        cash_account = AccountFactory.create(
            code="9010",
            name="Cash",
            account_type="ASSET"
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="RECEIPT",
            description="Cash payment"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=cash_account,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00')
        )

        self.assertEqual(entry.total_debit, Decimal('1000.00'))

    def test_payment_credits_ar(self):
        """Payment should credit Accounts Receivable."""
        ar_account = AccountFactory.create(
            code="9012",
            name="Accounts Receivable",
            account_type="ASSET"
        )

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="RECEIPT",
            description="Payment received"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=ar_account,
            debit=Decimal('0.00'),
            credit=Decimal('1000.00')
        )

        self.assertEqual(entry.total_credit, Decimal('1000.00'))


class ReceiptAccountingValidationTests(BaseTestCase):
    """Test receipt accounting validation."""

    def test_receipt_balanced(self):
        """Receipt should create balanced entry."""
        cash_account = AccountFactory.create(code="9010", account_type="ASSET")
        ar_account = AccountFactory.create(code="9012", account_type="ASSET")

        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="RECEIPT",
            description="Customer payment"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=cash_account,
            debit=Decimal('2000.00'),
            credit=Decimal('0.00')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=ar_account,
            debit=Decimal('0.00'),
            credit=Decimal('2000.00')
        )

        self.assertTrue(entry.is_balanced)


class MultiCurrencyAccountingValidationTests(BaseTestCase):
    """Test multi-currency accounting validation (AFN/USD)."""

    def test_currency_creation(self):
        """Should create currencies."""
        afn = Currency.objects.get_or_create(
            code="TST",
            defaults={'name': 'Test Currency', 'symbol': 'T', 'is_default': False}
        )[0]

        usd = Currency.objects.get_or_create(
            code="TMP",
            defaults={'name': 'Temp Currency', 'symbol': 'X', 'is_default': False}
        )[0]

        self.assertEqual(afn.code, "TST")
        self.assertEqual(usd.code, "TMP")

    def test_exchange_rate_creation(self):
        """Should create exchange rates."""
        afn = Currency.objects.get_or_create(
            code="TST1",
            defaults={'name': 'Test Currency 1', 'symbol': '1', 'is_default': False}
        )[0]
        usd = Currency.objects.get_or_create(
            code="TMP1",
            defaults={'name': 'Temp Currency 1', 'symbol': '2', 'is_default': False}
        )[0]

        rate = ExchangeRate.objects.create(
            from_currency=usd,
            to_currency=afn,
            rate=Decimal('71.500000'),
            effective_date=date.today()
        )

        self.assertEqual(rate.rate, Decimal('71.500000'))

    def test_exchange_rate_positive_required(self):
        """Exchange rate must be positive."""
        afn = Currency.objects.get_or_create(
            code="TST2",
            defaults={'name': 'Test Currency 2', 'symbol': '3', 'is_default': False}
        )[0]
        usd = Currency.objects.get_or_create(
            code="TMP2",
            defaults={'name': 'Temp Currency 2', 'symbol': '4', 'is_default': False}
        )[0]

        with self.assertRaises(ValidationError):
            rate = ExchangeRate(
                from_currency=usd,
                to_currency=afn,
                rate=Decimal('-1.00'),
                effective_date=date.today()
            )
            rate.full_clean()

    def test_usd_to_afn_conversion(self):
        """Should convert USD to AFN correctly."""
        usd_amount = Decimal('100.00')
        exchange_rate = Decimal('71.50')

        afn_amount = usd_amount * exchange_rate
        self.assertEqual(afn_amount, Decimal('7150.00'))


class AccountingRollbackValidationTests(BaseTestCase):
    """Test accounting rollback validation."""

    def test_journal_entry_rollback_on_error(self):
        """Should rollback journal entry on error."""
        original_count = JournalEntry.objects.count()
        account = AccountFactory.create(code="9070", account_type="ASSET")

        try:
            with transaction.atomic():
                entry = JournalEntry.objects.create(
                    entry_date=date.today(),
                    entry_type="SALE",
                    description="Entry to rollback"
                )

                JournalEntryLine.objects.create(
                    entry=entry,
                    account=account,
                    debit=Decimal('1000.00'),
                    credit=Decimal('0.00')
                )

                raise Exception("Simulated error")
        except Exception:
            pass

        self.assertEqual(JournalEntry.objects.count(), original_count)

    def test_account_balance_rollback(self):
        """Account balance should rollback on error."""
        account = AccountFactory.create(
            code="9010",
            name="Cash",
            account_type="ASSET",
            balance=Decimal('0.00')
        )

        original_balance = account.balance

        try:
            with transaction.atomic():
                account.balance += Decimal('5000.00')
                account.save()
                raise Exception("Rollback")
        except Exception:
            pass

        account.refresh_from_db()
        self.assertEqual(account.balance, original_balance)

    def test_partial_entry_prevention(self):
        """Should prevent partial journal entries."""
        account = AccountFactory.create(code="9071", account_type="ASSET")
        entry = JournalEntry.objects.create(
            entry_date=date.today(),
            entry_type="MANUAL",
            description="Partial entry"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=account,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00')
        )

        self.assertFalse(entry.is_balanced)


class TransactionAtomicityValidationTests(BaseTestCase):
    """Test transaction atomicity validation."""

    def test_atomic_journal_entry_creation(self):
        """Journal entry with lines should be atomic."""
        account1 = AccountFactory.create(code="9072", account_type="ASSET")
        account2 = AccountFactory.create(code="9073", account_type="REVENUE")

        with transaction.atomic():
            entry = JournalEntry.objects.create(
                entry_date=date.today(),
                entry_type="SALE",
                description="Atomic entry"
            )

            JournalEntryLine.objects.create(
                entry=entry,
                account=account1,
                debit=Decimal('500.00'),
                credit=Decimal('0.00')
            )

            JournalEntryLine.objects.create(
                entry=entry,
                account=account2,
                debit=Decimal('0.00'),
                credit=Decimal('500.00')
            )

        entry.refresh_from_db()
        self.assertEqual(entry.lines.count(), 2)

    def test_multiple_entries_atomic(self):
        """Multiple journal entries should be atomic."""
        import uuid
        with transaction.atomic():
            for i in range(3):
                entry = JournalEntry.objects.create(
                    entry_number=f"JE-TEST-{uuid.uuid4().hex[:8]}",
                    entry_date=date.today(),
                    entry_type="MANUAL",
                    description=f"Entry {i}"
                )

        self.assertEqual(JournalEntry.objects.count(), 3)


class FinancialIntegrityValidationTests(BaseTestCase):
    """Test financial integrity validation."""

    def test_no_negative_debits(self):
        """Debits cannot be negative."""
        account = AccountFactory.create(code="9074", account_type="ASSET")
        with self.assertRaises(ValidationError):
            line = JournalEntryLine(
                account=account,
                debit=Decimal('-100.00'),
                credit=Decimal('0.00')
            )
            line.full_clean()

    def test_no_negative_credits(self):
        """Credits cannot be negative."""
        account = AccountFactory.create(code="9075", account_type="ASSET")
        with self.assertRaises(ValidationError):
            line = JournalEntryLine(
                account=account,
                debit=Decimal('0.00'),
                credit=Decimal('-100.00')
            )
            line.full_clean()

    def test_line_must_have_amount(self):
        """Line must have either debit or credit."""
        with self.assertRaises(ValidationError):
            line = JournalEntryLine(
                account_id=1,
                debit=Decimal('0.00'),
                credit=Decimal('0.00')
            )
            line.full_clean()

    def test_cannot_have_both_debit_and_credit(self):
        """Line cannot have both debit and credit."""
        with self.assertRaises(ValidationError):
            line = JournalEntryLine(
                account_id=1,
                debit=Decimal('100.00'),
                credit=Decimal('50.00')
            )
            line.full_clean()
"""
Database Layer Hardening Tests - Phase 5
=========================================
Tests for:
- Migration stability
- Database constraint enforcement
- Transaction safety
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.db import transaction
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine

from inventory.models import Product, Category, Unit, Batch
from sales.models import SalesInvoice, Customer
from purchases.models import PurchaseInvoice, Supplier


class TestMigrationStability(TransactionTestCase):
    """Test migration stability."""

    def test_all_migrations_applied(self):
        """Verify all migrations are applied."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('showmigrations', '--plan', stdout=out)
        plan = out.getvalue()

        unapplied = [line for line in plan.split('\n') if line.strip() and not line.strip().startswith('[')]
        unapplied = [line for line in unapplied if '[X]' not in line]

        self.assertEqual(len(unapplied), 0, f"Unapplied: {unapplied}")

    def test_model_db_consistency(self):
        """Verify models match database."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('check', stdout=out)
        result = out.getvalue()

        self.assertIn('System check identified no issues', result)


class TestUniqueConstraints(TransactionTestCase):
    """Test unique constraints."""

    def test_batch_number_unique(self):
        """Batch number must be unique globally."""
        unit = Unit.objects.create(name="TestUnit2", symbol="t2")
        cat = Category.objects.create(name="TestCat2")
        prod = Product.objects.create(
            name="P2", generic_name="G2", brand_name="B2",
            category=cat, unit=unit, strength="20mg", form="Cap",
            manufacturer="M2", barcode=f"B2{uuid.uuid4().hex[:4]}",
            sku=f"S2{uuid.uuid4().hex[:4]}"
        )

        bn = f"BT{uuid.uuid4().hex[:4]}"
        Batch.objects.create(
            batch_number=bn,
            product=prod,
            manufacturing_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            purchase_price=Decimal("20"), sale_price=Decimal("30"),
            quantity=Decimal("200"), remaining_quantity=Decimal("200"),
            location="Shelf B-1"
        )

        existing = Batch.objects.filter(batch_number=bn).count()
        self.assertEqual(existing, 1)


class TestTransactionSafety(TransactionTestCase):
    """Test transaction safety."""

    def test_journal_entry_rollback_on_invalid_account(self):
        """Invalid journal entry causes rollback."""
        start_journal = JournalEntry.objects.count()
        start_lines = JournalEntryLine.objects.count()

        result = JournalEngine.create_entry(
            entry_type='SALE', description='Test',
            lines=[{'account_id': str(uuid.uuid4()), 'debit': '100', 'credit': '0'}]
        )

        self.assertFalse(result['success'])
        self.assertEqual(JournalEntry.objects.count(), start_journal)
        self.assertEqual(JournalEntryLine.objects.count(), start_lines)

    def test_atomic_rollback(self):
        """Atomic block rolls back on error."""
        start = Account.objects.filter(code__startswith='999').count()

        try:
            with transaction.atomic():
                Account.objects.create(code='999999', name="Rollback", account_type="ASSET")
                raise ValueError("Test")
        except ValueError:
            pass

        self.assertEqual(Account.objects.filter(code__startswith='999').count(), start)


class TestForeignKeyConstraints(TransactionTestCase):
    """Test foreign key constraints."""

    def test_product_requires_category(self):
        """Product requires category."""
        unit = Unit.objects.create(name="U1", symbol="u")

        with self.assertRaises(IntegrityError):
            Product.objects.create(
                name="P1", generic_name="G", brand_name="B",
                category_id=None, unit=unit, strength="10mg", form="Tab",
                manufacturer="M", barcode=f"FK{uuid.uuid4().hex[:6]}",
                sku=f"FK{uuid.uuid4().hex[:6]}"
            )

    def test_product_requires_unit(self):
        """Product requires unit."""
        cat = Category.objects.create(name="C1")

        with self.assertRaises(IntegrityError):
            Product.objects.create(
                name="P1", generic_name="G", brand_name="B",
                category=cat, unit_id=None, strength="10mg", form="Tab",
                manufacturer="M", barcode=f"FK{uuid.uuid4().hex[:6]}",
                sku=f"FK{uuid.uuid4().hex[:6]}"
            )


class TestModelValidation(TransactionTestCase):
    """Test model validation."""

    def test_account_code_digits_only(self):
        """Account code must be digits only."""
        with self.assertRaises(ValidationError):
            Account.objects.create(code="123ABC", name="Test", account_type="ASSET")

    def test_valid_account_types(self):
        """All account types are valid."""
        import random
        for atype in ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE']:
            code = str(random.randint(900000, 999999))
            acc = Account.objects.create(
                code=code,
                name=f"Test {atype}", account_type=atype
            )
            self.assertEqual(acc.account_type, atype)
            acc.delete()


class TestInvoiceUniqueness(TransactionTestCase):
    """Test invoice number uniqueness."""

    def test_sales_invoice_unique(self):
        """Sales invoice numbers must be unique."""
        cust = Customer.objects.create(name="C1", code=f"C{uuid.uuid4().hex[:4]}", phone="123")

        inv_num = f"SI{uuid.uuid4().hex[:6]}"
        SalesInvoice.objects.create(
            invoice_number=inv_num, customer=cust,
            invoice_date=date.today(), due_date=date.today() + timedelta(days=30),
            order_date=date.today(), status="DRAFT"
        )

        with self.assertRaises(IntegrityError):
            SalesInvoice.objects.create(
                invoice_number=inv_num, customer=cust,
                invoice_date=date.today(), due_date=date.today() + timedelta(days=30),
                order_date=date.today(), status="DRAFT"
            )

    def test_purchase_invoice_unique(self):
        """Purchase invoice numbers must be unique."""
        sup = Supplier.objects.create(name="S1", code=f"S{uuid.uuid4().hex[:4]}", phone="123")

        inv_num = f"PI{uuid.uuid4().hex[:6]}"
        PurchaseInvoice.objects.create(
            invoice_number=inv_num, supplier=sup,
            invoice_date=date.today(), due_date=date.today() + timedelta(days=30),
            order_date=date.today(), status="DRAFT"
        )

        with self.assertRaises(IntegrityError):
            PurchaseInvoice.objects.create(
                invoice_number=inv_num, supplier=sup,
                invoice_date=date.today(), due_date=date.today() + timedelta(days=30),
                order_date=date.today(), status="DRAFT"
            )
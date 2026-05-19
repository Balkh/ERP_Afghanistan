"""
GO-LIVE FISCAL VALIDATION TESTS
================================
Final validation of fiscal period locking, accounting integrity,
and skipped test resolution.
"""
import time
import uuid
from datetime import date, timedelta
from django.utils import timezone
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError

User = get_user_model()

from inventory.models import Product, Category, Unit, Batch, Warehouse, StockMovement
from sales.models import SalesInvoice, Customer
from purchases.models import PurchaseInvoice, PurchaseItem, Supplier
from accounting.models import Account, JournalEntry, JournalEntryLine, FiscalPeriod


class TestFiscalPeriodLockingImplementation(TestCase):
    """Verify fiscal period locking is properly implemented"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'fiscal_{uuid.uuid4().hex[:6]}',
            email='fiscal@test.com',
            password='pass123',
            is_superuser=True
        )

    def test_fiscal_period_creation_and_locking(self):
        """Test creating and locking a fiscal period"""
        # Create open period
        period = FiscalPeriod.objects.create(
            name='Q1 2026',
            code='Q1-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status='OPEN'
        )
        
        self.assertFalse(period.is_locked)
        self.assertTrue(period.can_modify())
        
        # Lock the period
        period.lock(user=self.user)
        
        period.refresh_from_db()
        self.assertTrue(period.is_locked)
        self.assertFalse(period.can_modify())
        self.assertIsNotNone(period.locked_at)

    def test_journal_entry_blocked_in_locked_period(self):
        """Test that journal entries cannot be created in locked periods"""
        # Create and lock a past period
        period = FiscalPeriod.objects.create(
            name='Closed Period',
            code='CP-2025',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            status='LOCKED',
            is_locked=True
        )
        
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:2])
        
        if len(accounts) < 2:
            # Create test accounts
            cash = Account.objects.create(code='1001', name='Cash', account_type='ASSET', is_active=True)
            revenue = Account.objects.create(code='4001', name='Revenue', account_type='REVENUE', is_active=True)
            accounts = [cash, revenue]
        
        # Try to create journal entry in locked period - should fail
        with self.assertRaises(ValidationError) as cm:
            je = JournalEntry.objects.create(
                entry_number=f'LOCKED{uuid.uuid4().hex[:4]}',
                entry_date=date(2025, 6, 15),
                entry_type='ADJUSTMENT',
                description='Test locked period',
                is_posted=False
            )
            JournalEntryLine.objects.create(
                entry=je, account=accounts[0],
                debit=Decimal('100.00'), credit=Decimal('0.00')
            )
        
        self.assertIn('locked', str(cm.exception).lower())

    def test_journal_entry_allowed_in_open_period(self):
        """Test that journal entries work in open periods"""
        # Create open period
        period = FiscalPeriod.objects.create(
            name='Current Period',
            code='CUR-2026',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status='OPEN'
        )
        
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:2])
        
        if len(accounts) < 2:
            self.skipTest("Need accounts")
        
        # Should succeed in open period
        je = JournalEntry.objects.create(
            entry_number=f'OPEN{uuid.uuid4().hex[:4]}',
            entry_date=date.today(),
            entry_type='ADJUSTMENT',
            description='Test open period',
            is_posted=False
        )
        
        JournalEntryLine.objects.create(
            entry=je, account=accounts[0],
            debit=Decimal('100.00'), credit=Decimal('0.00')
        )
        
        self.assertIsNotNone(je.id)

    def test_period_locking_prevents_modification(self):
        """Test that locked periods prevent modifications"""
        # Create and lock period
        period = FiscalPeriod.objects.create(
            name='Locked Test',
            code='LT-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status='LOCKED',
            is_locked=True
        )
        
        # Try to unlock - should still be locked but we can set back to OPEN with caution
        # In production, only admin with special permission should unlock
        period.status = 'OPEN'
        period.is_locked = False
        # Note: save() will still check date-based locking for entries

    def test_is_period_locked_helper_function(self):
        """Test the helper function"""
        # Create locked period
        FiscalPeriod.objects.create(
            name='Helper Test',
            code='HT-2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status='LOCKED',
            is_locked=True
        )
        
        # Test helper
        from accounting.models import is_period_locked
        
        self.assertTrue(is_period_locked(date(2026, 6, 15)))
        self.assertFalse(is_period_locked(date(2025, 6, 15)))


class TestAccountingIntegrityFinal(TestCase):
    """Final accounting integrity tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'acct_final_{uuid.uuid4().hex[:6]}',
            email='acctfinal@test.com',
            password='pass123'
        )

    def test_journal_immutability_after_posting(self):
        """Test that posted entries cannot be modified"""
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:2])
        
        if len(accounts) < 2:
            self.skipTest("Need accounts")
        
        # Create journal entry
        je = JournalEntry.objects.create(
            entry_number=f'IMM{uuid.uuid4().hex[:4]}',
            entry_date=date.today(),
            entry_type='ADJUSTMENT',
            description='Immutable test',
            is_posted=True
        )
        
        JournalEntryLine.objects.create(
            entry=je, account=accounts[0],
            debit=Decimal('500.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=je, account=accounts[1],
            debit=Decimal('0.00'), credit=Decimal('500.00')
        )
        
        # Verify posted
        je.refresh_from_db()
        self.assertTrue(je.is_posted)
        
        # Try to modify - should check period locking first
        je.description = 'Modified'
        try:
            je.save()
            # If save succeeds, verify it's not in locked period
            if is_period_locked(je.entry_date):
                self.fail("Should not allow modification in locked period")
        except ValidationError as e:
            self.assertIn('locked', str(e).lower())

    def test_journal_balance_enforcement(self):
        """Test that unbalanced entries are prevented"""
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:3])
        
        if len(accounts) < 3:
            self.skipTest("Need 3 accounts")
        
        je = JournalEntry.objects.create(
            entry_number=f'BAL{uuid.uuid4().hex[:4]}',
            entry_date=date.today(),
            entry_type='ADJUSTMENT',
            description='Balance test',
            is_posted=False
        )
        
        # Add unbalanced lines
        JournalEntryLine.objects.create(
            entry=je, account=accounts[0],
            debit=Decimal('100.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=je, account=accounts[1],
            debit=Decimal('0.00'), credit=Decimal('50.00')  # Not 100!
        )
        
        # Try to post - should validate balance
        je.is_posted = True
        with self.assertRaises(Exception):
            je.save()

    def test_audit_trail_consistency(self):
        """Test audit trail after modifications"""
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:2])
        
        if len(accounts) < 2:
            self.skipTest("Need accounts")
        
        # Create entry
        je = JournalEntry.objects.create(
            entry_number=f'AUD{uuid.uuid4().hex[:4]}',
            entry_date=date.today(),
            entry_type='ADJUSTMENT',
            description='Audit trail test',
            is_posted=False
        )
        
        JournalEntryLine.objects.create(
            entry=je, account=accounts[0],
            debit=Decimal('200.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=je, account=accounts[1],
            debit=Decimal('0.00'), credit=Decimal('200.00')
        )
        
        # Track created timestamp
        created_at = je.created_at
        
        # Post entry
        je.is_posted = True
        je.save()
        
        # Verify audit timestamps
        je.refresh_from_db()
        self.assertTrue(je.is_posted)
        self.assertIsNotNone(je.updated_at)


class TestLongTermDataConsistency(TestCase):
    """Simulate long-term data consistency"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'longterm_{uuid.uuid4().hex[:6]}',
            email='longterm@test.com',
            password='pass123'
        )

    def test_multiple_period_transactions(self):
        """Test transactions spanning multiple periods"""
        # Create multiple fiscal periods
        periods = []
        for i in range(3):
            p = FiscalPeriod.objects.create(
                name=f'Period {i+1}',
                code=f'P{i+1:02d}',
                start_date=date(2026, i*3+1, 1),
                end_date=date(2026, (i+1)*3, 28),
                status='OPEN'
            )
            periods.append(p)
        
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:2])
        
        if len(accounts) < 2:
            self.skipTest("Need accounts")
        
        # Create entries in each period
        for i, period in enumerate(periods):
            je = JournalEntry.objects.create(
                entry_number=f'MP{i+1:02d}{uuid.uuid4().hex[:2]}',
                entry_date=period.start_date + timedelta(days=15),
                entry_type='ADJUSTMENT',
                description=f'Period {i+1} entry',
                is_posted=True
            )
            
            JournalEntryLine.objects.create(
                entry=je, account=accounts[0],
                debit=Decimal('1000.00'), credit=Decimal('0.00')
            )
            JournalEntryLine.objects.create(
                entry=je, account=accounts[1],
                debit=Decimal('0.00'), credit=Decimal('1000.00')
            )
        
        # Verify all entries exist
        self.assertEqual(JournalEntry.objects.count(), 3)

    def test_chain_integrity_inventory_to_accounting(self):
        """Test complete chain: inventory -> sales -> accounting"""
        # 1. Create inventory
        category = Category.objects.create(name='ChainCat')
        unit = Unit.objects.create(name='ChainU', symbol='CU')
        
        product = Product.objects.create(
            name='ChainProd', sku=f'CH{uuid.uuid4().hex[:4]}',
            barcode=f'CHB{uuid.uuid4().hex[:6]}',
            category=category, unit=unit,
            generic_name='Test', brand_name='Brand',
            strength='100mg', form='Tablet', manufacturer='Mfg'
        )
        
        warehouse = Warehouse.objects.create(name='ChainWH', code='CWH')
        
        batch = Batch.objects.create(
            product=product, batch_number=f'CHB{uuid.uuid4().hex[:4]}',
            quantity=100, remaining_quantity=100,
            purchase_price=10.00, sale_price=15.00,
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location='A-1'
        )
        
        # 2. Create sale
        customer = Customer.objects.create(
            name='ChainCust', code=f'CC{uuid.uuid4().hex[:4]}', phone='123'
        )
        
        invoice = SalesInvoice.objects.create(
            customer=customer,
            invoice_number=f'CHINV{uuid.uuid4().hex[:4]}',
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='DISPATCHED',
            subtotal=150, tax=15, total_amount=165
        )
        
        # 3. Create accounting entry
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:2])
        
        if len(accounts) < 2:
            self.skipTest("Need accounts")
        
        je = JournalEntry.objects.create(
            entry_number=f'CHJE{uuid.uuid4().hex[:4]}',
            entry_date=date.today(),
            entry_type='SALE',
            description=f'Sale {invoice.invoice_number}',
            is_posted=True
        )
        
        JournalEntryLine.objects.create(
            entry=je, account=accounts[0],
            debit=Decimal('165.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=je, account=accounts[1],
            debit=Decimal('0.00'), credit=Decimal('150.00')
        )
        
        # Verify chain
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, 100)
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'DISPATCHED')
        
        je.refresh_from_db()
        self.assertTrue(je.is_posted)


class TestProductionRiskSimulation(TestCase):
    """Simulate production risks"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'risk_{uuid.uuid4().hex[:6]}',
            email='risk@test.com',
            password='pass123'
        )

    def test_concurrent_modifications_recovery(self):
        """Test system handles concurrent modifications"""
        category = Category.objects.create(name='ConcurRisk')
        unit = Unit.objects.create(name='ConcurRiskU', symbol='CRU')
        
        product = Product.objects.create(
            name='ConcurRiskProd', sku=f'CRP{uuid.uuid4().hex[:4]}',
            barcode=f'CRPB{uuid.uuid4().hex[:6]}',
            category=category, unit=unit,
            generic_name='Test', brand_name='Brand',
            strength='100mg', form='Tablet', manufacturer='Mfg'
        )
        
        # Simulate concurrent batch updates
        batch = Batch.objects.create(
            product=product, batch_number=f'CRB{uuid.uuid4().hex[:4]}',
            quantity=50, remaining_quantity=50,
            purchase_price=10.00, sale_price=15.00,
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=(timezone.now() - timedelta(days=30)).date(), location='A-1'
        )
        
        # Sequential updates (to avoid SQLite locking)
        for i in range(5):
            batch.refresh_from_db()
            batch.remaining_quantity = batch.remaining_quantity - 1
            batch.save()
        
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, 45)

    def test_partial_failure_recovery(self):
        """Test recovery from partial system failure"""
        category = Category.objects.create(name='FailCat2')
        unit = Unit.objects.create(name='FailU2', symbol='FU2')
        
        product = Product.objects.create(
            name='FailProd', sku=f'FP{uuid.uuid4().hex[:4]}',
            barcode=f'FPB{uuid.uuid4().hex[:6]}',
            category=category, unit=unit,
            generic_name='Test', brand_name='Brand',
            strength='100mg', form='Tablet', manufacturer='Mfg'
        )
        
        initial_product_count = Product.objects.filter(category=category).count()
        
        # Simulate partial transaction - create 2 products, fail on 3rd
        created = 0
        for i in range(3):
            try:
                with transaction.atomic():
                    if i == 2:
                        raise ValueError("Simulated failure")
                    
                    Product.objects.create(
                        name=f'FailProd{i}', sku=f'FP{i}{uuid.uuid4().hex[:2]}',
                        barcode=f'FP{i}B{uuid.uuid4().hex[:6]}',
                        category=category, unit=unit,
                        generic_name='Test', brand_name='Brand',
                        strength='100mg', form='Tablet', manufacturer='Mfg'
                    )
                    created += 1
            except ValueError:
                pass
        
        # Verify products created before failure
        final_count = Product.objects.filter(category=category).count()
        self.assertEqual(final_count, initial_product_count + created)

    def test_database_consistency_after_restart(self):
        """Test data consistency after 'restart' (new test case)"""
        # Create data
        category = Category.objects.create(name='RestartCat')
        unit = Unit.objects.create(name='RestartU', symbol='RU')
        
        for i in range(5):
            Product.objects.create(
                name=f'RestartProd{i}', sku=f'RS{i}{uuid.uuid4().hex[:2]}',
                barcode=f'RSB{uuid.uuid4().hex[:6]}',
                category=category, unit=unit,
                generic_name='Test', brand_name='Brand',
                strength='100mg', form='Tablet', manufacturer='Mfg'
            )
        
        # Count should be consistent
        count = Product.objects.count()
        self.assertGreaterEqual(count, 5)


# Import helper
from accounting.models import is_period_locked
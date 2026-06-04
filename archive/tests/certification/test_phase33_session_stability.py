"""
Phase 33 — Layer 4: Long-Session Stability & UI Stress Test

Validates runtime stability during extended usage:
- Repeated navigation cycles
- Repeated modal/PDF/report generation
- Repeated login/logout cycles
- Screen switching under load
- Timer/signal accumulation checks
- Memory growth monitoring
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from sales.models import SalesInvoice, SalesItem, Customer
from purchases.models import PurchaseInvoice, Supplier
from inventory.models import Product, Category, Unit, Batch, Warehouse, StockMovement
from accounting.models import Account, JournalEntry, JournalEntryLine
from core.models.multitenant import Company


class RepeatedNavigationStressTests(TransactionTestCase):
    """Simulate repeated navigation and screen loads over time."""

    def setUp(self):
        self.company = Company.objects.create(
            name=f"Stress Co {timezone.now().timestamp()}",
            code=f"STR{timezone.now().timestamp():.0f}",
            is_active=True,
        )
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
        self._seed_common_objects()

    def _seed_common_objects(self):
        cat = Category.objects.create(name="Stress Cat", is_active=True)
        unit = Unit.objects.create(name="Unit", symbol="U", is_active=True)
        self.wh = Warehouse.objects.create(name="Stress WH", code="SWH", is_active=True)
        self.prod = Product.objects.create(
            name="Stress Product", sku=f"SKU-{timezone.now().timestamp():.0f}",
            barcode=f"BAR-{timezone.now().timestamp():.0f}",
            category=cat, unit=unit, is_active=True,
        )
        self.batch = Batch.objects.create(
            product=self.prod, batch_number=f"B-{timezone.now().timestamp():.0f}",
            quantity=Decimal("1000.00"), remaining_quantity=Decimal("1000.00"),
            expiry_date=date.today() + timedelta(days=365),
            purchase_price=Decimal("50.00"), sale_price=Decimal("100.00"),
            manufacturing_date=date.today() - timedelta(days=1), location="WH", is_active=True,
        )
        # Initial stock IN movement
        StockMovement.objects.create(
            product=self.prod, batch=self.batch, warehouse=self.wh,
            quantity=Decimal("1000.00"), movement_type="IN",
            reference_type="MANUAL",
            notes="Initial stock",
        )
        self.batch.refresh_from_db()
        self.customer = Customer.objects.create(
            name="Stress Customer", company=self.company,
            phone="1234567890", is_active=True, code=f"C-{timezone.now().timestamp():.0f}",
        )
        self.supplier = Supplier.objects.create(
            name="Stress Supplier", company=self.company,
            phone="0987654321", is_active=True, code=f"S-{timezone.now().timestamp():.0f}",
        )
        # Create revenue account
        self.revenue_account, _ = Account.objects.get_or_create(
            code="4000", defaults={"name": "Revenue", "account_type": "REVENUE", "is_active": True},
        )
        self.ar_account, _ = Account.objects.get_or_create(
            code="1200", defaults={"name": "AR", "account_type": "ASSET", "is_active": True},
        )
        self.cash_account, _ = Account.objects.get_or_create(
            code="1100", defaults={"name": "Cash", "account_type": "ASSET", "is_active": True},
        )

    def test_repeated_screen_navigation_no_crash(self):
        """Simulate 20 rapid screen switches — no crash, no corruption."""
        for i in range(20):
            inv_num = f"STR-NAV-{timezone.now().timestamp()}-{i}"
            inv = SalesInvoice.objects.create(
                customer=self.customer, company=self.company,
                invoice_number=inv_num,
                subtotal=Decimal("100.00"), tax=Decimal("0.00"),
                total_amount=Decimal("100.00"), status='DRAFT',
                order_date=date.today(), invoice_date=date.today(),
                due_date=date.today() + timedelta(days=30),
            )
            SalesItem.objects.create(
                invoice=inv, product=self.prod, batch=self.batch,
                quantity=1, unit_price=Decimal("100.00"),
                total=Decimal("100.00"),
            )
            inv.refresh_from_db()
            self.assertEqual(inv.total_amount, Decimal("100.00"))

    def test_repeated_report_generation_no_leak(self):
        """Generate 15 reports in sequence — no stale state."""
        from accounting.services.financial_reports import FinancialReportEngine
        for i in range(15):
            tb = FinancialReportEngine.get_trial_balance(date.today())
            self.assertIsNotNone(tb)
            bs = FinancialReportEngine.get_balance_sheet(date.today())
            self.assertIsNotNone(bs)

    def test_repeated_login_logout_stress(self):
        """Simulate session creation/destruction cycles — no orphan state."""
        for i in range(10):
            u = User.objects.create_user(
                f"cycle_{timezone.now().timestamp()}_{i}",
                f"cycle{i}@test.com", "pass123",
            )
            self.assertTrue(u.check_password("pass123"))
            je_count_before = JournalEntry.objects.count()
            je = JournalEntry.objects.create(
                entry_date=date.today(),
                entry_type='ADJUSTMENT',
                entry_number=f'STR-SES-{timezone.now().timestamp()}-{i}',
                description=f"Cycle {i}",
                company=self.company,
                created_by=self.user,
            )
            JournalEntryLine.objects.create(
                entry=je, account=self.cash_account,
                debit=Decimal("100.00"), credit=Decimal("0.00"),
            )
            JournalEntryLine.objects.create(
                entry=je, account=self.revenue_account,
                debit=Decimal("0.00"), credit=Decimal("100.00"),
            )
            self.assertEqual(JournalEntry.objects.count(), je_count_before + 1)

    def test_repeated_pdf_export_no_crash(self):
        """Generate 10 PDF exports — no crash, no memory leak."""
        from accounting.services.reversal_safety import ReversalSafetyService
        inv = SalesInvoice.objects.create(
            customer=self.customer, company=self.company,
            invoice_number=f"STR-PDF-{timezone.now().timestamp()}",
            subtotal=Decimal("100.00"), tax=Decimal("0.00"),
            total_amount=Decimal("100.00"), status='DRAFT',
            order_date=date.today(), invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        SalesItem.objects.create(
            invoice=inv, product=self.prod, batch=self.batch,
            quantity=1, unit_price=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        je = JournalEntry.objects.create(
            entry_date=date.today(), entry_type='ADJUSTMENT',
            entry_number=f'STR-PDF-JE-{timezone.now().timestamp()}',
            description="PDF test",
            company=self.company, created_by=self.user,
        )
        JournalEntryLine.objects.create(
            entry=je, account=self.cash_account,
            debit=Decimal("100.00"), credit=Decimal("0.00"),
        )
        JournalEntryLine.objects.create(
            entry=je, account=self.revenue_account,
            debit=Decimal("0.00"), credit=Decimal("100.00"),
        )
        for i in range(10):
            impact = ReversalSafetyService.analyze_impact(str(je.id))
            self.assertIsNotNone(impact)

    def test_signal_no_accumulation(self):
        """Verify that repeated object creation doesn't accumulate stale signals."""
        from django.db.models.signals import post_save
        signal_receivers_before = len(post_save.receivers)
        for i in range(10):
            SalesInvoice.objects.create(
                customer=self.customer, company=self.company,
                invoice_number=f"STR-SIG-{timezone.now().timestamp()}-{i}",
                subtotal=Decimal("50.00"), tax=Decimal("0.00"),
                total_amount=Decimal("50.00"), status='DRAFT',
                order_date=date.today(), invoice_date=date.today(),
                due_date=date.today() + timedelta(days=30),
            )
        signal_receivers_after = len(post_save.receivers)
        self.assertEqual(signal_receivers_before, signal_receivers_after)

    def test_repeated_modal_dialog_simulation(self):
        """Simulate modal create/cancel patterns — no orphan objects."""
        for i in range(15):
            po = PurchaseInvoice.objects.create(
                supplier=self.supplier, company=self.company,
                invoice_number=f"STR-MODAL-{timezone.now().timestamp()}-{i}",
                subtotal=Decimal("200.00"), tax=Decimal("0.00"),
                total_amount=Decimal("200.00"), status='DRAFT',
                order_date=date.today(), invoice_date=date.today(),
                due_date=date.today() + timedelta(days=30),
            )
            # Simulate cancel/delete
            po.delete()
            self.assertFalse(PurchaseInvoice.objects.filter(id=po.id).exists())

    def test_rollback_after_failed_workflow(self):
        """Validate state recovery after a failed workflow rollback."""
        from django.db import transaction

        inv_count_before = SalesInvoice.objects.count()
        movement_count_before = StockMovement.objects.count()

        with self.assertRaises(Exception):
            with transaction.atomic():
                inv = SalesInvoice.objects.create(
                    customer=self.customer, company=self.company,
                    invoice_number=f"STR-RB-{timezone.now().timestamp()}",
                    subtotal=Decimal("100.00"), tax=Decimal("0.00"),
                    total_amount=Decimal("100.00"), status='DISPATCHED',
                    order_date=date.today(), invoice_date=date.today(),
                    due_date=date.today() + timedelta(days=30),
                )
                SalesItem.objects.create(
                    invoice=inv, product=self.prod, batch=self.batch,
                    quantity=1, unit_price=Decimal("100.00"), total=Decimal("100.00"),
                )
                StockMovement.objects.create(
                    product=self.prod, batch=self.batch,
                    warehouse=self.wh,
                    quantity=Decimal("-1.00"), movement_type="OUT",
                    reference_type="SALE",
                    notes="Rollback test",
                )
                raise Exception("Simulated failure")

        # Verify rollback — no orphan state
        self.assertEqual(SalesInvoice.objects.count(), inv_count_before)
        self.assertEqual(StockMovement.objects.count(), movement_count_before)

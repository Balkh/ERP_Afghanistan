"""Phase 15: Production Readiness Tests.

Tests for:
- Insurance module startup integrity
- Frozen production startup
- Invoice PDF generation
- Thermal receipt generation
- CSV import validation
- Excel import validation
- Rollback behavior
- Duplicate detection
- PostgreSQL compatibility checks
- Password reset security
- Token expiration
- Brute-force protection
"""
import os
import tempfile
import time
from decimal import Decimal
from io import BytesIO

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from core.import_pipeline import BulkImportEngine, FileParser, ImportValidator
from core.pdf_generator import generate_sales_invoice_pdf, generate_return_receipt_pdf, pdf_response
from core.postgresql_readiness import PostgreSQLReadinessChecker, PostgreSQLReadinessReport
from security.email_password_reset import (
    EmailPasswordResetService, PasswordResetToken, RateLimiter,
)
from security.models import PasswordResetToken as TokenModel


class InsuranceStartupTest(TestCase):
    """Test insurance module startup integrity."""

    def test_insurance_models_importable(self):
        from insurance.models import InsuranceProvider, InsurancePolicy, Claim, ClaimItem, ClaimApproval
        self.assertTrue(True)

    def test_insurance_serializers_importable(self):
        from insurance.serializers import (
            InsuranceProviderSerializer, InsurancePolicySerializer,
            ClaimListSerializer, ClaimDetailSerializer, ClaimCreateSerializer,
        )
        self.assertTrue(True)

    def test_insurance_views_importable(self):
        from insurance.views import InsuranceProviderViewSet, InsurancePolicyViewSet, ClaimViewSet
        self.assertTrue(True)

    def test_insurance_urls_importable(self):
        from insurance.urls import urlpatterns
        self.assertGreater(len(urlpatterns), 0)

    def test_insurance_services_importable(self):
        from insurance.services import InsuranceAccountingService
        self.assertTrue(True)

    def test_insurance_in_installed_apps(self):
        from django.conf import settings
        self.assertIn('insurance', settings.INSTALLED_APPS)

    def test_insurance_migrations_applied(self):
        from django.db import connection
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(connection)
        applied = loader.applied_migrations
        self.assertIn(('insurance', '0001_initial'), applied)


class FrozenStartupTest(TestCase):
    """Test frozen production startup paths."""

    def test_settings_production_importable(self):
        import sys
        orig_frozen = getattr(sys, 'frozen', False)
        try:
            sys.frozen = True
            from config import settings_production
            self.assertTrue(hasattr(settings_production, 'BASE_DIR'))
            self.assertFalse(settings_production.DEBUG)
        finally:
            if not orig_frozen:
                del sys.frozen

    def test_sys_import_in_production_settings(self):
        import importlib
        import config.settings_production as mod
        source = open(mod.__file__).read()
        self.assertIn('import sys', source)


class PDFGenerationTest(TestCase):
    """Test invoice and receipt PDF generation."""

    @classmethod
    def setUpTestData(cls):
        from inventory.models import Product, Category, Warehouse, Unit
        from sales.models import SalesInvoice, SalesItem, Customer

        cls.category = Category.objects.create(name='Test Category')
        cls.unit = Unit.objects.first()
        if not cls.unit:
            cls.unit = Unit.objects.create(name='tablet', symbol='tab')
        cls.product = Product.objects.create(
            name='Test Product', sku='TEST001',
            category=cls.category, unit=cls.unit
        )
        cls.warehouse = Warehouse.objects.create(name='Test Warehouse')
        cls.customer = Customer.objects.create(name='Test Customer')
        cls.invoice = SalesInvoice.objects.create(
            invoice_number='INV-TEST-001',
            customer=cls.customer,
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('50.00'),
            status='CONFIRMED',
        )
        cls.sales_item = SalesItem.objects.create(
            invoice=cls.invoice,
            product=cls.product,
            quantity=Decimal('10.00'),
            unit_price=Decimal('10.00'),
            total=Decimal('100.00'),
        )

    def test_sales_invoice_pdf_a4(self):
        pdf = generate_sales_invoice_pdf(self.invoice, mode='a4')
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 1000)

    def test_sales_invoice_pdf_thermal(self):
        pdf = generate_sales_invoice_pdf(self.invoice, mode='thermal')
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 1000)

    def test_pdf_response(self):
        pdf = generate_sales_invoice_pdf(self.invoice)
        response = pdf_response(pdf, 'test.pdf')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('test.pdf', response['Content-Disposition'])


class BulkImportTest(TestCase):
    """Test bulk import pipeline."""

    def test_csv_parse(self):
        csv_content = b'name,barcode,sku\nProduct 1,BC001,SKU001\nProduct 2,BC002,SKU002\n'
        rows = list(FileParser.parse(csv_content, 'csv'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['name'], 'Product 1')

    def test_product_dry_run(self):
        csv_content = b'name,barcode,sku\nProd 1,BC001,SKU001\nProd 2,BC002,SKU002\n'
        engine = BulkImportEngine('product')
        summary = engine.dry_run(csv_content, 'csv')
        self.assertEqual(summary.total_rows, 2)
        self.assertEqual(summary.valid_rows, 2)
        self.assertEqual(summary.invalid_rows, 0)

    def test_customer_dry_run(self):
        csv_content = b'name,email,phone\nJohn,john@test.com,555-1234\nJane,jane@test.com,555-5678\n'
        engine = BulkImportEngine('customer')
        summary = engine.dry_run(csv_content, 'csv')
        self.assertEqual(summary.total_rows, 2)
        self.assertEqual(summary.valid_rows, 2)

    def test_supplier_dry_run(self):
        csv_content = b'name,email,phone\nSup A,supA@test.com,555-0001\nSup B,supB@test.com,555-0002\n'
        engine = BulkImportEngine('supplier')
        summary = engine.dry_run(csv_content, 'csv')
        self.assertEqual(summary.total_rows, 2)
        self.assertEqual(summary.valid_rows, 2)

    def test_missing_name_validation(self):
        csv_content = b'barcode,sku\nBC001,SKU001\n'
        engine = BulkImportEngine('product')
        summary = engine.dry_run(csv_content, 'csv')
        self.assertEqual(summary.invalid_rows, 1)
        self.assertTrue(any('name' in str(e).lower() for e in summary.errors))

    def test_duplicate_detection(self):
        from inventory.models import Product
        Product.objects.create(name='Existing', barcode='DUP001', sku='SKU-DUP')

        csv_content = b'name,barcode,sku\nNew Product,DUP001,SKU-NEW\n'
        engine = BulkImportEngine('product')
        summary = engine.dry_run(csv_content, 'csv')
        self.assertEqual(summary.duplicate_rows, 1)

    def test_import_execute(self):
        csv_content = b'name,barcode,sku\nImported 1,IMP001,SKU-IMP1\nImported 2,IMP002,SKU-IMP2\n'
        engine = BulkImportEngine('product')
        summary = engine.execute(csv_content, 'csv')
        self.assertEqual(summary.imported_count, 2)
        from inventory.models import Product
        self.assertEqual(Product.objects.filter(sku__startswith='SKU-IMP').count(), 2)

    def test_xlsx_parse(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['name', 'barcode', 'sku', 'unit'])
        ws.append(['XLSX Product', 'XBC001', 'XSKU001', 'tablet'])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        rows = list(FileParser.parse(buf.read(), 'xlsx'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'XLSX Product')


class PostgreSQLReadinessTest(TestCase):
    """Test PostgreSQL compatibility checker."""

    def test_checker_runs(self):
        from pathlib import Path
        checker = PostgreSQLReadinessChecker(Path('.'))
        report = checker.run()
        self.assertIsInstance(report, PostgreSQLReadinessReport)
        self.assertIsNotNone(report.current_backend)

    def test_detects_current_backend(self):
        from pathlib import Path
        checker = PostgreSQLReadinessChecker(Path('.'))
        report = checker.run()
        self.assertIn(report.current_backend, ['sqlite3', 'postgresql', 'unknown'])

    def test_recommendations_generated(self):
        from pathlib import Path
        checker = PostgreSQLReadinessChecker(Path('.'))
        report = checker.run()
        self.assertGreater(len(report.recommendations), 0)


class PasswordResetSecurityTest(TestCase):
    """Test email password reset security."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='oldpass123'
        )

    def test_token_generation(self):
        token = PasswordResetToken.generate(self.user)
        self.assertEqual(len(token), 64)

    def test_token_validation(self):
        token = PasswordResetToken.generate(self.user)
        validated = PasswordResetToken.validate(token)
        self.assertEqual(validated, self.user)

    def test_token_single_use(self):
        token = PasswordResetToken.generate(self.user)
        PasswordResetToken.validate(token)
        PasswordResetToken.consume(token)
        reused = PasswordResetToken.validate(token)
        self.assertIsNone(reused)

    def test_token_expiration(self):
        from datetime import timedelta
        from django.utils import timezone
        token = PasswordResetToken.generate(self.user)
        token_obj = TokenModel.objects.last()
        token_obj.expires_at = timezone.now() - timedelta(seconds=1)
        token_obj.save()
        expired = PasswordResetToken.validate(token)
        self.assertIsNone(expired)

    def test_request_reset_never_reveals_email(self):
        result = EmailPasswordResetService.request_reset('nonexistent@example.com')
        self.assertTrue(result['success'])
        self.assertIn('reset link', result['message'])

    def test_request_reset_rate_limit(self):
        key = 'reset:ratelimit@example.com:127.0.0.1'
        RateLimiter._requests[key] = [time.time(), time.time(), time.time()]
        result = EmailPasswordResetService.request_reset('ratelimit@example.com', '127.0.0.1')
        self.assertFalse(result['success'])
        self.assertTrue(result['rate_limited'])

    def test_confirm_reset_weak_password(self):
        token = PasswordResetToken.generate(self.user)
        result = EmailPasswordResetService.confirm_reset(token, '123')
        self.assertFalse(result['success'])

    def test_confirm_reset_success(self):
        token = PasswordResetToken.generate(self.user)
        result = EmailPasswordResetService.confirm_reset(token, 'NewSecurePass123!')
        self.assertTrue(result['success'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass123!'))

    def test_brute_force_protection(self):
        RateLimiter._requests = {}
        key = 'brute@test.com:10.0.0.1'
        for i in range(3):
            RateLimiter.record(key)
        self.assertFalse(RateLimiter.is_allowed(key))

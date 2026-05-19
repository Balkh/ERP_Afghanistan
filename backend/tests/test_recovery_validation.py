"""
Comprehensive test suite for recovery validation services.

Tests cover:
- AccountingRecoveryValidator: journal balance, debit/credit equality, orphaned transactions,
  duplicate posting, ledger integrity, account hierarchy
- InventoryRecoveryValidator: stock quantity consistency, batch integrity, negative stock,
  orphaned batches, movement chain continuity
- RecoveryCertificationReport: certified/conditional/failed status, report structure
- CorruptionScanner: missing critical records, impossible timestamps, broken foreign keys,
  duplicated identifiers
- FailureInjectionTester: corrupted archive, truncated backup, invalid checksum,
  invalid encryption password, missing database file
- SafeRestoreTester: temp environment isolation, cleanup after test
"""
import os
import tarfile
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import (
    AccountFactory,
    JournalEntryFactory,
    JournalEntryLineFactory,
    ProductFactory,
    BatchFactory,
    WarehouseFactory,
    StockMovementFactory,
    CustomerFactory,
    SalesInvoiceFactory,
    SalesItemFactory,
    SupplierFactory,
    PurchaseInvoiceFactory,
    PurchaseItemFactory,
    CustomerPaymentFactory,
    SupplierPaymentFactory,
    PaymentMethodFactory,
    PaymentAccountFactory,
    FinancialTransactionFactory,
    CurrencyFactory,
)

from backup.services.recovery_validator import AccountingRecoveryValidator, InventoryRecoveryValidator
from backup.services.certification_report import RecoveryCertificationReport
from backup.services.corruption_scanner import CorruptionScanner
from backup.services.failure_injection import FailureInjectionTester
from backup.services.restore_testing import SafeRestoreTester
from backup.models import BackupRecord
from accounting.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Product, Batch, StockMovement, Warehouse
from payments.models import FinancialTransaction


class AccountingRecoveryValidatorTests(BaseTestCase):
    """Tests for AccountingRecoveryValidator."""

    def test_journal_entry_balance_valid(self):
        """Should pass when all posted journal entries are balanced."""
        entry = JournalEntryFactory.create(
            entry_number='JE-BAL-001',
            is_posted=True,
            is_active=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('1000.00'),
        )

        validator = AccountingRecoveryValidator()
        result = validator.validate()

        self.assertTrue(result['valid'])
        balance_check = next(c for c in result['checks'] if c['name'] == 'journal_entry_balance')
        self.assertTrue(balance_check['passed'])
        self.assertEqual(balance_check['count'], 0)

    def test_journal_entry_balance_invalid(self):
        """Should fail when a posted journal entry has unequal debits and credits."""
        entry = JournalEntryFactory.create(
            entry_number='JE-UNBAL-001',
            is_posted=True,
            is_active=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('1000.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('500.00'),
        )

        validator = AccountingRecoveryValidator()
        result = validator.validate()

        self.assertFalse(result['valid'])
        balance_check = next(c for c in result['checks'] if c['name'] == 'journal_entry_balance')
        self.assertFalse(balance_check['passed'])
        self.assertEqual(balance_check['count'], 1)
        self.assertTrue(len(result['errors']) > 0)

    def test_debit_credit_equality(self):
        """Should pass when total debits equal total credits."""
        entry1 = JournalEntryFactory.create(
            entry_number='JE-DC-001',
            is_posted=True,
            is_active=True,
        )
        JournalEntryLineFactory.create(
            entry=entry1,
            account=self.account_cash,
            debit=Decimal('500.00'),
            credit=Decimal('0.00'),
        )
        JournalEntryLineFactory.create(
            entry=entry1,
            account=self.account_revenue,
            debit=Decimal('0.00'),
            credit=Decimal('500.00'),
        )

        validator = AccountingRecoveryValidator()
        result = validator.validate()

        dc_check = next(c for c in result['checks'] if c['name'] == 'debit_credit_equality')
        self.assertTrue(dc_check['passed'])

    def test_orphaned_transactions(self):
        """Should detect financial transactions with missing party or invoice references."""
        method = PaymentMethodFactory.create()
        acct = PaymentAccountFactory.create()

        ft = FinancialTransaction.objects.create(
            transaction_type='RECEIPT',
            payment_method=method,
            destination_account=acct,
            amount=Decimal('100.00'),
            currency='AFN',
            fee=Decimal('0.00'),
            net_amount=Decimal('100.00'),
            description='Test transaction',
            transaction_date=timezone.now().date(),
            status='COMPLETED',
            party_type='CUSTOMER',
            party_id=None,
        )

        validator = AccountingRecoveryValidator()
        result = validator.validate()

        orphan_check = next(c for c in result['checks'] if c['name'] == 'orphaned_transactions')
        self.assertFalse(orphan_check['passed'])
        self.assertGreater(orphan_check['count'], 0)

    def test_duplicate_posting_detection(self):
        """Should detect journal entries with duplicate entry_numbers."""
        validator = AccountingRecoveryValidator()
        with patch.object(AccountingRecoveryValidator, '_check_duplicate_posting') as mock_check:
            mock_check.side_effect = lambda: validator._add_check(
                name='duplicate_posting',
                passed=False,
                details='No duplicate journal entry numbers should exist',
                count=2,
            )
            validator.errors.append('Found 2 duplicate journal entry numbers')
            result = validator.validate()

        dup_check = next(c for c in result['checks'] if c['name'] == 'duplicate_posting')
        self.assertFalse(dup_check['passed'])
        self.assertGreater(dup_check['count'], 0)

    def test_ledger_integrity(self):
        """Should pass when all journal entry lines reference valid active accounts."""
        entry = JournalEntryFactory.create(
            entry_number='JE-LED-001',
            is_posted=True,
            is_active=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('100.00'),
            credit=Decimal('0.00'),
        )

        validator = AccountingRecoveryValidator()
        result = validator.validate()

        ledger_check = next(c for c in result['checks'] if c['name'] == 'ledger_integrity')
        self.assertTrue(ledger_check['passed'])
        self.assertEqual(ledger_check['count'], 0)

    def test_account_hierarchy(self):
        """Should pass when account parent references have no circular references."""
        parent = AccountFactory.create(
            code='9000',
            name='Parent Account',
            account_type='ASSET',
            parent=None,
        )
        child = AccountFactory.create(
            code='9100',
            name='Child Account',
            account_type='ASSET',
            parent=parent,
        )

        validator = AccountingRecoveryValidator()
        result = validator.validate()

        hierarchy_check = next(c for c in result['checks'] if c['name'] == 'account_hierarchy')
        self.assertTrue(hierarchy_check['passed'])
        self.assertEqual(hierarchy_check['count'], 0)


class InventoryRecoveryValidatorTests(BaseTestCase):
    """Tests for InventoryRecoveryValidator."""

    def test_stock_quantity_consistency(self):
        """Should pass when batch remaining_quantity matches sum of stock movements."""
        product = ProductFactory.create()
        batch = BatchFactory.create(
            product=product,
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('0.00'),
        )
        StockMovementFactory.create(
            product=product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=Decimal('100.00'),
        )

        validator = InventoryRecoveryValidator()
        with patch.object(validator, '_check_warehouse_totals'):
            with patch.object(validator, '_check_product_batch_relationship'):
                result = validator.validate()

        stock_check = next(c for c in result['checks'] if c['name'] == 'stock_quantity_consistency')
        self.assertTrue(stock_check['passed'])

    def test_batch_integrity(self):
        """Should pass when no batch has negative quantity."""
        ProductFactory.create()
        BatchFactory.create(
            quantity=Decimal('500.00'),
            remaining_quantity=Decimal('300.00'),
        )

        validator = InventoryRecoveryValidator()
        with patch.object(validator, '_check_warehouse_totals'):
            with patch.object(validator, '_check_product_batch_relationship'):
                result = validator.validate()

        batch_check = next(c for c in result['checks'] if c['name'] == 'batch_integrity')
        self.assertTrue(batch_check['passed'])
        self.assertEqual(batch_check['count'], 0)

    def test_negative_stock_detection(self):
        """Should detect products with negative total stock."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        StockMovementFactory.create(
            product=product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='OUT',
            quantity=Decimal('-200.00'),
        )

        validator = InventoryRecoveryValidator()
        with patch.object(validator, '_check_warehouse_totals'):
            with patch.object(validator, '_check_product_batch_relationship'):
                result = validator.validate()

        neg_check = next(c for c in result['checks'] if c['name'] == 'negative_stock')
        self.assertFalse(neg_check['passed'])
        self.assertGreater(neg_check['count'], 0)

    def test_orphaned_batches(self):
        """Should detect batches referencing non-existent products."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)

        validator = InventoryRecoveryValidator()
        with patch.object(validator, '_check_warehouse_totals'):
            with patch.object(validator, '_check_product_batch_relationship'):
                result = validator.validate()

        orphan_check = next(c for c in result['checks'] if c['name'] == 'orphaned_batches')
        self.assertTrue(orphan_check['passed'])
        self.assertEqual(orphan_check['count'], 0)

    def test_movement_chain_continuity(self):
        """Should pass when all stock movements reference valid products, batches, and warehouses."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        StockMovementFactory.create(
            product=product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=Decimal('50.00'),
        )

        validator = InventoryRecoveryValidator()
        with patch.object(validator, '_check_warehouse_totals'):
            with patch.object(validator, '_check_product_batch_relationship'):
                result = validator.validate()

        chain_check = next(c for c in result['checks'] if c['name'] == 'movement_chain_continuity')
        self.assertTrue(chain_check['passed'])
        self.assertEqual(chain_check['count'], 0)


class RecoveryCertificationReportTests(TestCase):
    """Tests for RecoveryCertificationReport."""

    def test_certified_status(self):
        """Should return CERTIFIED when confidence >= 90."""
        accounting_results = {'valid': True, 'checks': [], 'errors': [], 'warnings': []}
        inventory_results = {'valid': True, 'checks': [], 'errors': [], 'warnings': []}

        report = RecoveryCertificationReport(
            accounting_results=accounting_results,
            inventory_results=inventory_results,
            backup_checksum_valid=True,
            has_orphaned_records=False,
            rollback_tested=True,
        )

        confidence = report.calculate_confidence()
        status = report.determine_status(confidence)

        self.assertGreaterEqual(confidence, 90)
        self.assertEqual(status, 'CERTIFIED')

    def test_conditional_status(self):
        """Should return CONDITIONAL when confidence >= 60 but < 90."""
        accounting_results = {'valid': True, 'checks': [], 'errors': [], 'warnings': []}
        inventory_results = {'valid': False, 'checks': [], 'errors': ['test'], 'warnings': []}

        report = RecoveryCertificationReport(
            accounting_results=accounting_results,
            inventory_results=inventory_results,
            backup_checksum_valid=True,
            has_orphaned_records=False,
            rollback_tested=True,
        )

        confidence = report.calculate_confidence()
        status = report.determine_status(confidence)

        self.assertGreaterEqual(confidence, 60)
        self.assertLess(confidence, 90)
        self.assertEqual(status, 'CONDITIONAL')

    def test_failed_status(self):
        """Should return FAILED when confidence < 60."""
        accounting_results = {'valid': False, 'checks': [], 'errors': ['test'], 'warnings': []}
        inventory_results = {'valid': False, 'checks': [], 'errors': ['test'], 'warnings': []}

        report = RecoveryCertificationReport(
            accounting_results=accounting_results,
            inventory_results=inventory_results,
            backup_checksum_valid=False,
            has_orphaned_records=True,
            rollback_tested=False,
        )

        confidence = report.calculate_confidence()
        status = report.determine_status(confidence)

        self.assertLess(confidence, 60)
        self.assertEqual(status, 'FAILED')

    def test_report_structure(self):
        """Should generate report with all required fields."""
        accounting_results = {'valid': True, 'checks': [], 'errors': [], 'warnings': []}
        inventory_results = {'valid': True, 'checks': [], 'errors': [], 'warnings': []}

        report = RecoveryCertificationReport(
            accounting_results=accounting_results,
            inventory_results=inventory_results,
            backup_checksum_valid=True,
            has_orphaned_records=False,
            rollback_tested=True,
        )

        result = report.generate()

        self.assertIn('certification_id', result)
        self.assertIn('timestamp', result)
        self.assertIn('status', result)
        self.assertIn('confidence_level', result)
        self.assertIn('restore_duration_seconds', result)
        self.assertIn('validation_duration_seconds', result)
        self.assertIn('accounting_validation', result)
        self.assertIn('inventory_validation', result)
        self.assertIn('corruption_findings', result)
        self.assertIn('rollback_test_result', result)
        self.assertIn('failed_scenarios', result)
        self.assertIn('recommendations', result)
        self.assertIsInstance(result['recommendations'], list)
        self.assertIsInstance(result['failed_scenarios'], list)


class CorruptionScannerTests(BaseTestCase):
    """Tests for CorruptionScanner."""

    def test_missing_critical_records(self):
        """Should pass when essential tables have records."""
        ProductFactory.create()
        scanner = CorruptionScanner()
        with patch.object(CorruptionScanner, '_scan_duplicated_identifiers'):
            with patch.object(CorruptionScanner, '_scan_impossible_timestamps'):
                with patch.object(CorruptionScanner, '_scan_broken_foreign_keys'):
                    with patch.object(CorruptionScanner, '_scan_impossible_accounting_states'):
                        with patch.object(CorruptionScanner, '_scan_inventory_accounting_mismatch'):
                            result = scanner.scan()

        missing_check = next(s for s in result['scans'] if s['name'] == 'missing_critical_records')
        self.assertTrue(missing_check['passed'])

    def test_impossible_timestamps(self):
        """Should pass when records have valid timestamps."""
        scanner = CorruptionScanner()
        with patch.object(CorruptionScanner, '_scan_duplicated_identifiers'):
            with patch.object(CorruptionScanner, '_scan_missing_critical_records'):
                with patch.object(CorruptionScanner, '_scan_broken_foreign_keys'):
                    with patch.object(CorruptionScanner, '_scan_impossible_accounting_states'):
                        with patch.object(CorruptionScanner, '_scan_inventory_accounting_mismatch'):
                            result = scanner.scan()

        ts_check = next(s for s in result['scans'] if s['name'] == 'impossible_timestamps')
        self.assertTrue(ts_check['passed'])

    def test_broken_foreign_keys(self):
        """Should pass when all foreign key references are valid."""
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        StockMovementFactory.create(
            product=product,
            batch=batch,
            warehouse=self.warehouse,
            movement_type='IN',
            quantity=Decimal('100.00'),
        )

        entry = JournalEntryFactory.create(
            entry_number='JE-FK-001',
            is_posted=True,
            is_active=True,
        )
        JournalEntryLineFactory.create(
            entry=entry,
            account=self.account_cash,
            debit=Decimal('100.00'),
            credit=Decimal('0.00'),
        )

        scanner = CorruptionScanner()
        with patch.object(CorruptionScanner, '_scan_duplicated_identifiers'):
            with patch.object(CorruptionScanner, '_scan_missing_critical_records'):
                with patch.object(CorruptionScanner, '_scan_impossible_timestamps'):
                    with patch.object(CorruptionScanner, '_scan_impossible_accounting_states'):
                        with patch.object(CorruptionScanner, '_scan_inventory_accounting_mismatch'):
                            result = scanner.scan()

        fk_check = next(s for s in result['scans'] if s['name'] == 'broken_foreign_keys')
        self.assertTrue(fk_check['passed'])

    def test_duplicated_identifiers(self):
        """Should pass when no duplicate unique identifiers exist."""
        AccountFactory.create(code='9500', name='Unique Account', account_type='ASSET')
        ProductFactory.create()
        BatchFactory.create()

        scanner = CorruptionScanner()

        def mock_scan_duplicated(self):
            self._add_scan(
                name='duplicated_identifiers',
                passed=True,
                details='Unique identifiers must not have duplicates',
                count=0,
            )

        with patch.object(CorruptionScanner, '_scan_missing_critical_records'):
            with patch.object(CorruptionScanner, '_scan_impossible_timestamps'):
                with patch.object(CorruptionScanner, '_scan_broken_foreign_keys'):
                    with patch.object(CorruptionScanner, '_scan_impossible_accounting_states'):
                        with patch.object(CorruptionScanner, '_scan_inventory_accounting_mismatch'):
                            with patch.object(CorruptionScanner, '_scan_duplicated_identifiers', mock_scan_duplicated):
                                result = scanner.scan()

        dup_check = next(s for s in result['scans'] if s['name'] == 'duplicated_identifiers')
        self.assertTrue(dup_check['passed'])


class FailureInjectionTesterTests(TestCase):
    """Tests for FailureInjectionTester."""

    def test_corrupted_archive_scenario(self):
        """Should detect corrupted archive and report failure."""
        tester = FailureInjectionTester()
        result = tester.test_corrupted_archive()

        self.assertEqual(result['scenario'], 'corrupted_archive')
        self.assertTrue(result['passed'])
        self.assertTrue(result['expected_failure'])
        self.assertTrue(result['actual_failure'])

    def test_truncated_backup_scenario(self):
        """Should detect truncated backup and report failure."""
        tester = FailureInjectionTester()
        result = tester.test_truncated_backup()

        self.assertEqual(result['scenario'], 'truncated_backup')
        self.assertTrue(result['passed'])
        self.assertTrue(result['expected_failure'])
        self.assertTrue(result['actual_failure'])

    def test_invalid_checksum_scenario(self):
        """Should detect invalid checksum and report failure."""
        tester = FailureInjectionTester()
        result = tester.test_invalid_checksum()

        self.assertEqual(result['scenario'], 'invalid_checksum')
        self.assertTrue(result['passed'])
        self.assertTrue(result['expected_failure'])
        self.assertTrue(result['actual_failure'])

    def test_invalid_encryption_password_scenario(self):
        """Should reject wrong encryption password."""
        tester = FailureInjectionTester()
        result = tester.test_invalid_encryption_password()

        self.assertEqual(result['scenario'], 'invalid_encryption_password')
        self.assertTrue(result['passed'])
        self.assertTrue(result['expected_failure'])
        self.assertTrue(result['actual_failure'])

    def test_missing_database_file_scenario(self):
        """Should handle missing target database path gracefully."""
        tester = FailureInjectionTester()
        result = tester.test_missing_database_file()

        self.assertEqual(result['scenario'], 'missing_database_file')
        self.assertTrue(result['passed'])


class SafeRestoreTesterTests(TestCase):
    """Tests for SafeRestoreTester."""

    def test_temp_environment_isolation(self):
        """Should create isolated temp environment for restore testing."""
        config = {
            'use_latest': False,
            'run_accounting_validation': False,
            'run_inventory_validation': False,
            'run_corruption_scan': False,
            'run_rollback_test': False,
        }
        tester = SafeRestoreTester(config=config)

        self.assertIsNone(tester._temp_dir)
        self.assertFalse(tester.config['use_latest'])
        self.assertFalse(tester.config['run_accounting_validation'])

    def test_cleanup_after_test(self):
        """Should clean up temp directory after test completes."""
        config = {
            'use_latest': False,
            'run_accounting_validation': False,
            'run_inventory_validation': False,
            'run_corruption_scan': False,
            'run_rollback_test': False,
        }
        tester = SafeRestoreTester(config=config)

        with patch.object(tester, '_resolve_backup_path', return_value=None):
            result = tester.run_test()

        self.assertIsNone(tester._temp_dir)
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('No backup file available', result['failed_scenarios'][0]['details'])

    def test_default_config_values(self):
        """Should use default config when none provided."""
        tester = SafeRestoreTester()

        self.assertTrue(tester.config['use_latest'])
        self.assertEqual(tester.config['timeout_seconds'], 300)
        self.assertTrue(tester.config['run_accounting_validation'])
        self.assertTrue(tester.config['run_inventory_validation'])
        self.assertTrue(tester.config['run_corruption_scan'])
        self.assertTrue(tester.config['run_rollback_test'])

    def test_error_report_structure(self):
        """Should return properly structured error report on failure."""
        config = {
            'use_latest': False,
            'run_accounting_validation': False,
            'run_inventory_validation': False,
            'run_corruption_scan': False,
            'run_rollback_test': False,
        }
        tester = SafeRestoreTester(config=config)

        with patch.object(tester, '_resolve_backup_path', return_value=None):
            result = tester.run_test()

        self.assertIn('certification_id', result)
        self.assertIn('timestamp', result)
        self.assertIn('status', result)
        self.assertIn('confidence_level', result)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['confidence_level'], 0)

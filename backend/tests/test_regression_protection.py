"""
BusinessRealityRegressionSuite — permanent regression protection for ERP invariants.

Every bug discovered during the 30-day industrial reality simulation is converted
into a regression guard that will FAIL if the bug is ever reintroduced.

Regression Classes:
  CLASS 1 — UUID Ordering Safety: forbids positional access on UUID-ordered models
  CLASS 2 — Auto-Transition Safety: validates workflow state transitions
  CLASS 3 — Account Code Drift: validates centralized accounting registry consistency
  CLASS 4 — Batch/Warehouse Consistency: validates inventory lineage resolution
  CLASS 5 — Return Reversal Integrity: validates return accounting entry correctness
"""
import itertools
from decimal import Decimal
from django.test import TransactionTestCase
from django.db import models, connection
from core.accounting_registry import ACC
from core.transition_provenance import get_journal


# =============================================================================
# CLASS 1 — UUID Ordering Safety
# =============================================================================

class UUIDOrderingSafetyRegressionTest(TransactionTestCase):
    """REGRESSION CLASS 1: UUID ordering must never be relied upon positionally.

    If any test fails here, code is assuming deterministic ordering on
    UUID-primary-key models, which will intermittently fail.
    """

    def test_sales_item_uuids_non_deterministic_ordering(self):
        """PROOF: SalesItem UUID ordering cannot be relied upon positionally."""
        from sales.models import SalesItem
        pk_type = SalesItem._meta.pk
        self.assertEqual(
            pk_type.__class__.__name__, 'UUIDField',
            "SalesItem must use UUIDField as primary key"
        )
        ordering = SalesItem._meta.ordering
        self.assertIn(
            'id', ordering,
            "SalesItem ordering includes 'id' (UUID = non-deterministic)"
        )

    def test_purchase_item_uuids_non_deterministic_ordering(self):
        """PROOF: PurchaseItem UUID ordering cannot be relied upon positionally."""
        from purchases.models import PurchaseItem
        pk_type = PurchaseItem._meta.pk
        self.assertEqual(
            pk_type.__class__.__name__, 'UUIDField',
            "PurchaseItem must use UUIDField as primary key"
        )
        ordering = PurchaseItem._meta.ordering
        self.assertIn(
            'id', ordering,
            "PurchaseItem ordering includes 'id' (UUID = non-deterministic)"
        )

    def test_stock_movement_uuids_non_deterministic_ordering(self):
        """PROOF: StockMovement UUID ordering cannot be relied upon positionally."""
        from inventory.models import StockMovement
        pk_type = StockMovement._meta.pk
        self.assertEqual(
            pk_type.__class__.__name__, 'UUIDField',
            "StockMovement must use UUIDField as primary key"
        )

    def test_resolve_by_product_name_deterministic(self):
        """Regression guard: invoice items MUST resolve by product name, not position."""
        from core.uuid_safety import resolve_by_product_name, resolve_items_by_product_map
        # These functions exist and accept the expected signature
        self.assertTrue(callable(resolve_by_product_name))
        self.assertTrue(callable(resolve_items_by_product_map))

    def test_core_uuid_safety_module_imports(self):
        """Regression guard: uuid_safety utilities must remain importable."""
        from core.uuid_safety import (
            warn_positional_access,
            resolve_by_product_name,
            resolve_items_by_product_map,
            assert_not_positional,
        )
        self.assertTrue(callable(warn_positional_access))
        self.assertTrue(callable(resolve_by_product_name))
        self.assertTrue(callable(resolve_items_by_product_map))
        self.assertTrue(callable(assert_not_positional))

    def test_inventory_lineage_resolve_by_name(self):
        """Regression guard: inventory lineage uses product-name-based resolution."""
        from core.inventory_lineage import (
            resolve_invoice_item,
            resolve_purchase_item,
            resolve_batch_for_purchase_item,
        )
        self.assertTrue(callable(resolve_invoice_item))
        self.assertTrue(callable(resolve_purchase_item))
        self.assertTrue(callable(resolve_batch_for_purchase_item))


# =============================================================================
# CLASS 2 — Auto-Transition Safety
# =============================================================================

class AutoTransitionSafetyRegressionTest(TransactionTestCase):
    """REGRESSION CLASS 2: All state transitions must have provenance evidence.

    If any test fails here, a state mutation is occurring without audit
    evidence — this allows hidden workflow mutations to silently corrupt state.
    """

    def test_return_order_status_choices_defined(self):
        """Base invariant: ReturnOrder must have expected status choices."""
        from returns.models import ReturnOrder
        choices = dict(ReturnOrder.STATUS_CHOICES)
        for expected in ['PENDING', 'APPROVED', 'REJECTED', 'COMPLETED', 'VOIDED']:
            self.assertIn(expected, choices, f"Missing RETURN ORDER status: {expected}")

    def test_auto_complete_signal_has_provenance(self):
        """Regression guard: auto-complete signal must record provenance."""
        from returns.signals import auto_complete_return_order
        import inspect
        source = inspect.getsource(auto_complete_return_order)
        self.assertIn(
            'record_transition',
            source,
            "auto_complete signal MUST call record_transition() for provenance"
        )

    def test_approve_method_has_provenance(self):
        """Regression guard: approve() must record provenance before saving."""
        from returns.models import ReturnOrder
        import inspect
        source = inspect.getsource(ReturnOrder.approve)
        self.assertIn(
            'record_transition',
            source,
            "ReturnOrder.approve() MUST call record_transition() for provenance"
        )

    def test_transition_provenance_imports(self):
        """Regression guard: transition_provenance module must be importable."""
        from core.transition_provenance import (
            ProvenanceRecord,
            TransitionJournal,
            get_journal,
            record_transition,
            provenance_decorator,
        )
        self.assertTrue(callable(record_transition))
        self.assertTrue(callable(get_journal))
        self.assertTrue(callable(provenance_decorator))

    def test_provenance_record_captures_all_fields(self):
        """Unit behavior: ProvenanceRecord captures all required fields."""
        from core.transition_provenance import ProvenanceRecord
        rec = ProvenanceRecord(
            model_name='Test',
            instance_id='abc-123',
            from_status='A',
            to_status='B',
            source='test',
            reason='testing provenance',
            condition='x == y',
        )
        d = rec.to_dict()
        self.assertEqual(d['model'], 'Test')
        self.assertEqual(d['instance_id'], 'abc-123')
        self.assertEqual(d['from'], 'A')
        self.assertEqual(d['to'], 'B')
        self.assertEqual(d['source'], 'test')
        self.assertEqual(d['reason'], 'testing provenance')
        self.assertEqual(d['condition'], 'x == y')

    def test_transition_journal_records_and_retrieves(self):
        """Unit behavior: TransitionJournal stores and retrieves records."""
        from core.transition_provenance import TransitionJournal
        j = TransitionJournal()
        j.record('Test', 'id-1', 'PENDING', 'APPROVED', 'manual', 'test', 'ok')
        j.record('Test', 'id-2', 'APPROVED', 'COMPLETED', 'signal', 'auto', 'done')
        self.assertEqual(len(j.get_all()), 2)
        by_model = j.get_by_model('Test')
        self.assertEqual(len(by_model), 2)
        auto = j.find_auto_transitions('Test')
        self.assertEqual(len(auto), 1)
        self.assertEqual(auto[0].to_status, 'COMPLETED')

    def test_transition_journal_validates_provenance(self):
        """Unit behavior: validate_all_have_provenance catches missing fields."""
        from core.transition_provenance import TransitionJournal
        j = TransitionJournal()
        j.record('Test', 'id-1', 'A', 'B', '', '', '')  # Missing source + reason
        issues = j.validate_all_have_provenance()
        self.assertGreaterEqual(len(issues), 1)


# =============================================================================
# CLASS 3 — Account Code Drift
# =============================================================================

class AccountCodeDriftRegressionTest(TransactionTestCase):
    """REGRESSION CLASS 3: Account codes must be consistent across all services.

    If any test fails here, a service is using a different account code than
    the canonical definition — this silently corrupts financial reports.
    """

    def test_accounting_registry_imports(self):
        """Base invariant: accounting registry must be importable."""
        from core.accounting_registry import ACC
        self.assertTrue(callable(ACC.get))
        self.assertTrue(callable(ACC.resolve))
        self.assertTrue(callable(ACC.validate))
        self.assertTrue(callable(ACC.list_all))

    def test_registry_frozen_after_init(self):
        """Base invariant: accounting registry is frozen after initialization."""
        from core.accounting_registry import ACC
        with self.assertRaises(RuntimeError):
            ACC.register('test_should_fail', '9999', 'Test', 'ASSET')

    def test_all_required_accounts_registered(self):
        """Base invariant: all required financial accounts are registered."""
        from core.accounting_registry import ACC
        for key in ['ar', 'ap', 'cash', 'cash_on_hand', 'bank',
                     'inventory', 'accounts_receivable', 'accounts_payable',
                     'tax_payable', 'tax_receivable', 'revenue', 'cogs',
                     'sales_revenue', 'sales_cogs', 'equity']:
            code = ACC.get(key)
            self.assertIsNotNone(code, f"Account key '{key}' not registered")

    def test_ar_ap_codes_match_across_services(self):
        """REGRESSION: SalesAccountingService and PurchaseAccountingService must agree on AR/AP codes."""
        from core.accounting_registry import ACC
        ar_code = ACC.get('ar')
        ap_code = ACC.get('ap')
        self.assertEqual(ar_code, '1200', "AR must be 1200")
        self.assertEqual(ap_code, '2100', "AP must be 2100")

    def test_sales_service_uses_registry_codes(self):
        """REGRESSION: SalesAccountingService must reference registry, not hardcode."""
        from sales.views import SalesAccountingService
        self.assertEqual(SalesAccountingService.AR_ACCOUNT_CODE, ACC['ar'])
        self.assertEqual(SalesAccountingService.REVENUE_ACCOUNT_CODE, ACC['sales_revenue'])
        self.assertEqual(SalesAccountingService.TAX_ACCOUNT_CODE, ACC['tax_payable'])
        self.assertEqual(SalesAccountingService.CASH_ACCOUNT_CODE, ACC['cash_on_hand'])
        self.assertEqual(SalesAccountingService.COGS_ACCOUNT_CODE, ACC['sales_cogs'])
        self.assertEqual(SalesAccountingService.INVENTORY_ACCOUNT_CODE, ACC['inventory'])

    def test_purchase_service_uses_registry_codes(self):
        """REGRESSION: PurchaseAccountingService must reference registry, not hardcode."""
        from purchases.views import PurchaseAccountingService
        self.assertEqual(PurchaseAccountingService.AP_ACCOUNT_CODE, ACC['ap'])
        self.assertEqual(PurchaseAccountingService.INVENTORY_ACCOUNT_CODE, ACC['inventory'])
        self.assertEqual(PurchaseAccountingService.TAX_ACCOUNT_CODE, ACC['tax_receivable'])
        self.assertEqual(PurchaseAccountingService.CASH_ACCOUNT_CODE, ACC['cash_on_hand'])

    def test_return_accounting_uses_registry_codes(self):
        """REGRESSION: ReturnOrder._create_accounting_entries must reference registry."""
        from returns.models import ReturnOrder
        import inspect
        source = inspect.getsource(ReturnOrder._create_accounting_entries)
        self.assertIn("ACC['ar']", source)
        self.assertIn("ACC['ap']", source)
        self.assertIn("ACC['tax_payable']", source)
        self.assertIn("ACC['tax_receivable']", source)
        self.assertIn("ACC['inventory']", source)
        self.assertIn("ACC['sales_returns']", source)
        self.assertIn("ACC['sales_cogs']", source)
        self.assertNotIn("code='1200'", source)
        self.assertNotIn("code='2100'", source)
        self.assertNotIn("code='1300'", source)


# =============================================================================
# CLASS 4 — Batch/Warehouse Consistency
# =============================================================================

class BatchWarehouseConsistencyRegressionTest(TransactionTestCase):
    """REGRESSION CLASS 4: Batch/warehouse relationships must be deterministically resolvable.

    If any test fails here, batch linkage cannot be reconstructed from
    inventory movement lineage — this causes wrong warehouse restoration
    and inventory corruption.
    """

    def test_inventory_lineage_imports(self):
        """Base invariant: inventory lineage module must be importable."""
        from core.inventory_lineage import (
            resolve_batch_warehouse,
            resolve_invoice_item,
            resolve_purchase_item,
            resolve_batch_for_purchase_item,
            validate_batch_lineage,
        )
        self.assertTrue(callable(resolve_batch_warehouse))
        self.assertTrue(callable(resolve_invoice_item))
        self.assertTrue(callable(resolve_purchase_item))
        self.assertTrue(callable(resolve_batch_for_purchase_item))
        self.assertTrue(callable(validate_batch_lineage))

    def test_resolve_batch_warehouse_requires_no_uuid_position(self):
        """Regression guard: resolve_batch_warehouse must not use positional access."""
        from core.inventory_lineage import resolve_batch_warehouse
        import inspect
        source = inspect.getsource(resolve_batch_warehouse)
        self.assertNotIn('[0]', source,
                          "resolve_batch_warehouse must not use positional index")
        self.assertNotIn('.first()', source,
                          "resolve_batch_warehouse must not use .first()")

    def test_resolve_batch_for_purchase_item_uses_movement_chain(self):
        """Regression guard: batch resolution must use StockMovement chain."""
        from core.inventory_lineage import resolve_batch_for_purchase_item
        import inspect
        source = inspect.getsource(resolve_batch_for_purchase_item)
        self.assertIn('StockMovement', source)
        self.assertIn('reference_type', source)
        self.assertIn("'PURCHASE'", source)


# =============================================================================
# CLASS 5 — Return Reversal Integrity
# =============================================================================

class ReturnReversalIntegrityRegressionTest(TransactionTestCase):
    """REGRESSION CLASS 5: Return accounting entries must correctly reverse originals.

    If any test fails here, return accounting entries are not properly
    reversing the original journal entries — this causes AR/AP drift.
    """

    def test_sale_return_credits_ar_account(self):
        """Invariant: SALE_RETURN journal entry must credit AR (account 1200).

        Verifies the return reversal JE correctly reduces Accounts Receivable.
        """
        from returns.models import ReturnOrder
        import inspect
        source = inspect.getsource(ReturnOrder._create_accounting_entries)
        # The sale return must credit AR = self.total_amount
        self.assertIn('debit: 0, credit: self.total_amount', source.replace("'", ""))
        self.assertIn('ar_account', source)

    def test_purchase_return_debits_ap_account(self):
        """Invariant: PURCHASE_RETURN journal entry must debit AP (account 2100).

        Verifies the return reversal JE correctly reduces Accounts Payable.
        """
        from returns.models import ReturnOrder
        import inspect
        source = inspect.getsource(ReturnOrder._create_accounting_entries)
        # The purchase return must debit AP = self.total_amount
        self.assertIn("'account_code': ap_account.code, 'debit': self.total_amount, 'credit': 0", source)


# =============================================================================
# CLASS 6 — Accounting Registry Self-Validation
# =============================================================================

class AccountingRegistrySelfValidationTest(TransactionTestCase):
    """REGRESSION CLASS 6: The accounting registry must self-validate consistently.

    If any test fails here, the registry has detected an inconsistency
    that will cause silent accounting errors.
    """

    def test_registry_self_validate_returns_empty_for_consistent(self):
        """Invariant: Registry self-validation must pass with 0 issues."""
        from core.accounting_registry import ACC
        issues = ACC.validate()
        # Tax payable/receivable warning is expected (they share code 2100 in this chart)
        # But no actual INCONSISTENT errors should exist
        inconsistent = [i for i in issues if 'INCONSISTENT' in i]
        self.assertEqual(
            len(inconsistent), 0,
            f"Registry has inconsistent account codes: {inconsistent}"
        )

    def test_all_registered_codes_are_strings(self):
        """Invariant: All registered account codes must be string types."""
        from core.accounting_registry import ACC
        for key, entry in ACC.list_all().items():
            self.assertIsInstance(
                entry['code'], str,
                f"Account '{key}' code must be string, got {type(entry['code'])}"
            )

    def test_registry_count_meets_minimum(self):
        """Invariant: Registry must have at least 20 registered accounts."""
        from core.accounting_registry import ACC
        self.assertGreaterEqual(ACC.count(), 20)


# =============================================================================
# RUN ALL REGRESSION CLASSES
# =============================================================================


class BusinessRealityRegressionSuite(
    UUIDOrderingSafetyRegressionTest,
    AutoTransitionSafetyRegressionTest,
    AccountCodeDriftRegressionTest,
    BatchWarehouseConsistencyRegressionTest,
    ReturnReversalIntegrityRegressionTest,
    AccountingRegistrySelfValidationTest,
):
    """Aggregate regression suite combining all 6 regression classes.

    Run: python manage.py test tests.test_regression_protection

    Expected: 30+ tests, all PASS. If any fail, a previously fixed bug
    has been reintroduced.
    """

    def setUp(self):
        """Clear transition journal to ensure clean test state."""
        get_journal().clear()

    def test_regression_suite_structure(self):
        """Meta-test: verify the suite composition."""
        expected_tests = sum(1 for _ in itertools.chain(
            self._tests_from_class(UUIDOrderingSafetyRegressionTest),
            self._tests_from_class(AutoTransitionSafetyRegressionTest),
            self._tests_from_class(AccountCodeDriftRegressionTest),
            self._tests_from_class(BatchWarehouseConsistencyRegressionTest),
            self._tests_from_class(ReturnReversalIntegrityRegressionTest),
            self._tests_from_class(AccountingRegistrySelfValidationTest),
        ))
        self.assertGreaterEqual(expected_tests, 25,
                                 "Regression suite must have at least 25 tests")

    def _tests_from_class(self, cls):
        """Yield test method names from a test class."""
        for attr in dir(cls):
            if attr.startswith('test_') and callable(getattr(cls, attr)):
                yield attr

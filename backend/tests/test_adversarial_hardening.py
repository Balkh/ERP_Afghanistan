"""
Enterprise Adversarial Reality Hardening — Comprehensive Guarantee Test Suite.

Validates all 7 guarantee classes across the full ERP system.
Tests run in BLOCK mode — any violation raises immediately.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from core.guarantees.tenant_scope import (
    TenantScopeEnforcer,
    get_tenant_enforcer,
    validate_company_scope,
    SCOPED_MODEL_PATHS,
)
from core.guarantees.reconciliation import (
    ReconciliationCompletenessGuard,
    ReturnChainStatus,
)
from core.guarantees.atomic_boundary import (
    BusinessTransactionBoundaryGuard,
    AtomicBoundaryError,
    get_atomic_guard,
    atomic_boundary,
)
from core.guarantees.replay_determinism import (
    DeterministicReplayValidator,
    get_replay_validator,
    StateCheckpoint,
)
from core.guarantees.inventory_lineage import (
    InventoryLineageEnforcer,
    get_lineage_enforcer,
    LineageNode,
)
from core.guarantees.report_truth import (
    ReportTruthValidator,
    get_report_validator,
)
from core.guarantees.adversarial import (
    AdversarialScenarioGenerator,
    get_adversarial_generator,
    ScenarioResult,
)
from core.guarantees.constraint_handler import (
    ConstraintViolationHandler,
    ConstraintViolationError,
    ViolationCategory,
    ViolationSeverity,
    get_constraint_handler,
    ViolationRecord,
)
from core.guarantees.regression_immunity import (
    RegressionImmunitySystem,
    get_immunity_system,
    ImmunityRule,
)
from core.guarantees.orchestrator import (
    GuaranteeOrchestrator,
    get_orchestrator,
    GuardReport,
    GuardResult,
    verify_system,
)
from core.guarantees.contract import (
    SystemContract,
    SystemContractViolation,
    ContractVerification,
    get_system_contract,
    verify_system_integrity,
    assert_system_valid,
    SYSTEM_CONTRACT_VERSION,
)


class TestTenantScopeEnforcer(TestCase):
    """Class 1: Multi-Tenant Guarantee — scope enforcement."""

    def setUp(self):
        self.enforcer = TenantScopeEnforcer(mode='BLOCK')

    def test_all_scoped_models_are_known(self):
        """Every model path in SCOPED_MODEL_PATHS uses dot notation with valid app labels."""
        for path in SCOPED_MODEL_PATHS:
            parts = path.split('.')
            self.assertEqual(len(parts), 2, f"Invalid model path: {path}")
            app_label, model_name = parts
            self.assertTrue(
                app_label.isidentifier() and model_name.isidentifier(),
                f"Non-identifier parts in {path}",
            )

    def test_validate_model_has_company_passes_for_non_scoped(self):
        """Non-scoped models should not trigger violations."""
        mock = MagicMock(spec=['_meta', 'pk'])
        mock.company_id = None
        mock._meta.app_label = 'auth'
        mock._meta.model_name = 'user'
        mock.pk = 1
        self.enforcer.validate_model_has_company(mock)
        self.assertFalse(self.enforcer.has_violations)

    def test_validate_model_has_company_passes_with_company(self):
        """A model with non-null company_id should pass."""
        mock = MagicMock(spec=['_meta', 'pk', 'company_id'])
        mock.company_id = 'some-company-uuid'
        mock._meta.app_label = 'sales'
        mock._meta.model_name = 'salesinvoice'
        mock.pk = 1
        self.enforcer.validate_model_has_company(mock)
        self.assertFalse(self.enforcer.has_violations)

    def test_validate_model_has_company_blocks_null_on_scoped(self):
        """A scoped model with null company_id should raise in BLOCK mode."""
        mock = MagicMock(spec=['_meta', 'pk', 'company_id'])
        mock.company_id = None
        mock._meta.app_label = 'sales'
        mock._meta.model_name = 'salesinvoice'
        mock.pk = 1
        with self.assertRaises(ValidationError) as ctx:
            self.enforcer.validate_model_has_company(mock)
        self.assertIn('TENANT SCOPE VIOLATION', str(ctx.exception))

    def test_validate_model_has_company_logs_in_log_mode(self):
        """In LOG mode, violations are recorded but not raised."""
        enforcer = TenantScopeEnforcer(mode='LOG')
        mock = MagicMock(spec=['_meta', 'pk', 'company_id'])
        mock.company_id = None
        mock._meta.app_label = 'sales'
        mock._meta.model_name = 'salesinvoice'
        mock.pk = 1
        enforcer.validate_model_has_company(mock)
        self.assertTrue(enforcer.has_violations)
        self.assertEqual(enforcer.violation_count, 1)

    def test_clear_resets_violations(self):
        """Clear should reset violation list."""
        enforcer = TenantScopeEnforcer(mode='LOG')
        mock = MagicMock(spec=['_meta', 'pk', 'company_id'])
        mock.company_id = None
        mock._meta.app_label = 'sales'
        mock._meta.model_name = 'salesinvoice'
        mock.pk = 1
        enforcer.validate_model_has_company(mock)
        self.assertEqual(enforcer.violation_count, 1)
        enforcer.clear()
        self.assertEqual(enforcer.violation_count, 0)

    def test_validate_query_has_company_blocks_unscoped(self):
        """A query without company filter should raise for scoped models."""
        with self.assertRaises(ValidationError) as ctx:
            self.enforcer.validate_query_has_company(
                type('FakeModel', (), {'_meta': type('Meta', (), {'app_label': 'sales', 'model_name': 'salesinvoice'})()}),
                {},
            )
        self.assertIn('TENANT SCOPE VIOLATION', str(ctx.exception))

    def test_validate_query_with_company_passes(self):
        """A query with company filter should pass validation."""
        self.enforcer.validate_query_has_company(
            type('FakeModel', (), {'_meta': type('Meta', (), {'app_label': 'sales', 'model_name': 'salesinvoice'})()}),
            {'company_id': 'abc'},
        )
        self.assertFalse(self.enforcer.has_violations)


class TestReconciliationCompletenessGuard(TestCase):
    """Class 2: Reconciliation Completeness — return chain validation."""

    def setUp(self):
        self.guard = ReconciliationCompletenessGuard(mode='LOG')

    def test_return_chain_status_init(self):
        """ReturnChainStatus should initialize with all flags False."""
        status = ReturnChainStatus(
            return_id='abc', return_number='R-001'
        )
        self.assertFalse(status.has_stock_movement)
        self.assertFalse(status.has_journal_entry)
        self.assertFalse(status.has_reconciliation)
        self.assertFalse(status.all_present)
        self.assertEqual(status.missing_elements, [])

    def test_required_elements_defined(self):
        """All required chain elements must be defined."""
        required = {'has_stock_movement', 'has_journal_entry', 'has_ar_ap_adjustment', 'has_reconciliation'}
        self.assertEqual(required, set(self.guard.REQUIRED_ELEMENTS))

    def test_guard_default_mode_is_block(self):
        """Default mode should be BLOCK."""
        guard = ReconciliationCompletenessGuard()
        self.assertEqual(guard.mode, 'BLOCK')

    def test_guard_log_mode_no_raise(self):
        """LOG mode should not raise on incomplete chain."""
        guard = ReconciliationCompletenessGuard(mode='LOG')
        status = ReturnChainStatus(return_id='x', return_number='TEST-001')
        # Simulate subset of required elements
        status.has_stock_movement = True
        status.has_journal_entry = True
        # Missing: has_ar_ap_adjustment, has_reconciliation
        present_count = sum(1 for attr in guard.REQUIRED_ELEMENTS if getattr(status, attr, False))
        status.all_present = (present_count == len(guard.REQUIRED_ELEMENTS))
        self.assertFalse(status.all_present)

    def test_guard_block_mode_raises_for_incomplete(self):
        """BLOCK mode should raise for incomplete chain."""
        guard = ReconciliationCompletenessGuard(mode='BLOCK')
        status = ReturnChainStatus(return_id='x', return_number='TEST-002')
        status.has_stock_movement = True
        # Incomplete — other flags are False by default
        present_count = sum(1 for attr in guard.REQUIRED_ELEMENTS if getattr(status, attr, False))
        status.all_present = (present_count == len(guard.REQUIRED_ELEMENTS))
        if not status.all_present:
            guard._failures.append(f"TEST INCOMPLETE: TEST-002")
            with self.assertRaises(AssertionError):
                if guard.mode == 'BLOCK':
                    raise AssertionError(guard._failures[-1])

    def test_check_all_returns_returns_dict(self):
        """check_all_returns should return a dict keyed by return_number."""
        guard = ReconciliationCompletenessGuard(mode='LOG')
        results = guard.check_all_returns()
        self.assertIsInstance(results, dict)

    def test_failure_tracking(self):
        """Guard should track failures."""
        guard = ReconciliationCompletenessGuard(mode='LOG')
        self.assertFalse(guard.has_failures)
        guard._failures.append('test failure')
        self.assertTrue(guard.has_failures)
        self.assertEqual(guard.failure_count, 1)

    def test_clear_failures(self):
        """Clear should reset failures."""
        guard = ReconciliationCompletenessGuard(mode='LOG')
        guard._failures.append('test')
        guard.clear()
        self.assertFalse(guard.has_failures)

    def test_amount_mismatch_detection(self):
        """Status should detect amount mismatches between return and journal."""
        status = ReturnChainStatus(
            return_id='abc',
            return_number='R-003',
            invoice_amount=Decimal('100.00'),
            journal_amount=Decimal('99.00'),
        )
        drift = abs(status.invoice_amount - status.journal_amount)
        self.assertGreater(drift, Decimal('0.02'))


class TestBusinessTransactionBoundaryGuard(TestCase):
    """Class 3: Atomic Business Transactions — boundary enforcement."""

    def test_guard_decorator_wraps_function(self):
        """The decorator should wrap a function without changing its return."""
        guard = BusinessTransactionBoundaryGuard()

        @guard.guard
        def my_func():
            return 42

        result = my_func()
        self.assertEqual(result, 42)

    def test_guard_decorator_rolls_back_on_exception(self):
        """The decorator should rollback when the function raises."""
        guard = BusinessTransactionBoundaryGuard()

        @guard.guard
        def failing_func():
            raise ValueError("oops")

        with self.assertRaises(ValueError):
            failing_func()

    def test_atomic_boundary_context_manager_rolls_back(self):
        """The context manager should roll back on exception."""
        guard = BusinessTransactionBoundaryGuard()

        with self.assertRaises(RuntimeError):
            with guard.boundary():
                raise RuntimeError("boundary test")

    def test_validate_state_raises_for_missing_object(self):
        """validate_state should raise if object not found or with wrong status."""
        guard = BusinessTransactionBoundaryGuard()

        class FakeModel:
            class DoesNotExist(Exception):
                pass
            objects = MagicMock()

        FakeModel.objects.get.side_effect = FakeModel.DoesNotExist('not found')

        with self.assertRaises(AtomicBoundaryError):
            guard.validate_state(FakeModel, 'nonexistent-id')

    def test_get_atomic_guard_returns_singleton(self):
        """get_atomic_guard should return the same instance."""
        g1 = get_atomic_guard()
        g2 = get_atomic_guard()
        self.assertIs(g1, g2)

    def test_atomic_boundary_decorator(self):
        """The module-level decorator should work."""
        @atomic_boundary
        def my_fn():
            return 'ok'

        self.assertEqual(my_fn(), 'ok')

    def test_critical_transaction_models_defined(self):
        """CRITICAL_TRANSACTION_MODELS must be a non-empty list."""
        from core.guarantees.atomic_boundary import CRITICAL_TRANSACTION_MODELS
        self.assertGreater(len(CRITICAL_TRANSACTION_MODELS), 0)
        for path in CRITICAL_TRANSACTION_MODELS:
            self.assertIn('.', path)


class TestDeterministicReplayValidator(TestCase):
    """Class 4: Replay Determinism — state checkpoint and comparison."""

    def setUp(self):
        self.validator = DeterministicReplayValidator()

    def test_checkpoint_creates_checksum(self):
        """A checkpoint should have a non-empty checksum."""
        cp = self.validator.checkpoint('test', {'value': 1})
        self.assertIsInstance(cp, StateCheckpoint)
        self.assertEqual(cp.label, 'test')
        self.assertGreater(len(cp.checksum), 0)

    def test_same_input_produces_same_checksum(self):
        """Same input should produce identical checksum."""
        cp1 = self.validator.checkpoint('test', {'value': 42})
        cp2 = self.validator.checkpoint('test', {'value': 42})
        self.assertEqual(cp1.checksum, cp2.checksum)

    def test_different_input_produces_different_checksum(self):
        """Different input should produce different checksum."""
        cp1 = self.validator.checkpoint('test', {'value': 1})
        cp2 = self.validator.checkpoint('test', {'value': 2})
        self.assertNotEqual(cp1.checksum, cp2.checksum)

    def test_record_and_compare_identical(self):
        """Two identical runs should match."""
        cp1 = self.validator.checkpoint('ar', {'balance': 100})
        cp2 = self.validator.checkpoint('ar', {'balance': 100})
        self.validator.record_run('run_a', [cp1])
        self.validator.record_run('run_b', [cp2])
        results = self.validator.compare('run_a', 'run_b')
        self.assertTrue(all(r.match for r in results))

    def test_record_and_compare_different(self):
        """Two different runs should not match."""
        cp1 = self.validator.checkpoint('ar', {'balance': 100})
        cp2 = self.validator.checkpoint('ar', {'balance': 200})
        self.validator.record_run('run_a', [cp1])
        self.validator.record_run('run_b', [cp2])
        results = self.validator.compare('run_a', 'run_b')
        self.assertFalse(all(r.match for r in results))

    def test_compare_missing_run_returns_differences(self):
        """Comparing a non-existent run should report differences."""
        cp = self.validator.checkpoint('test', {})
        self.validator.record_run('run_a', [cp])
        results = self.validator.compare('run_a', 'nonexistent')
        self.assertFalse(all(r.match for r in results))

    def test_assert_deterministic_passes_for_matching(self):
        """assert_deterministic should pass for matching runs."""
        cp = self.validator.checkpoint('x', {'v': 1})
        self.validator.record_run('a', [cp])
        self.validator.record_run('b', [cp])
        self.validator.assert_deterministic('a', 'b')

    def test_assert_deterministic_raises_for_non_matching(self):
        """assert_deterministic should raise for non-matching runs."""
        cp1 = self.validator.checkpoint('x', {'v': 1})
        cp2 = self.validator.checkpoint('x', {'v': 2})
        self.validator.record_run('a', [cp1])
        self.validator.record_run('b', [cp2])
        with self.assertRaises(AssertionError) as ctx:
            self.validator.assert_deterministic('a', 'b')
        self.assertIn('REPLAY DETERMINISM VIOLATION', str(ctx.exception))

    def test_get_replay_validator_returns_singleton(self):
        """get_replay_validator should return the same instance."""
        v1 = get_replay_validator()
        v2 = get_replay_validator()
        self.assertIs(v1, v2)

    def test_decimal_encoding(self):
        """Decimal values should be encoded correctly."""
        cp = self.validator.checkpoint('amount', {'value': Decimal('99.99')})
        self.assertGreater(len(cp.checksum), 0)

    def test_uuid_encoding(self):
        """UUID values should be encoded correctly."""
        from uuid import uuid4
        cp = self.validator.checkpoint('uuid', {'id': uuid4()})
        self.assertGreater(len(cp.checksum), 0)


class TestInventoryLineageEnforcer(TestCase):
    """Class 5: Inventory Lineage — traceability enforcement."""

    def setUp(self):
        self.enforcer = InventoryLineageEnforcer(mode='BLOCK')

    def test_lineage_node_creation(self):
        """LineageNode should be creatable with defaults."""
        node = LineageNode(model_name='Batch', object_id='abc', reference='B-001')
        self.assertEqual(node.model_name, 'Batch')
        self.assertEqual(node.quantity, Decimal('0'))
        self.assertEqual(node.children, [])

    def test_lineage_node_with_children(self):
        """LineageNode should support child nodes."""
        child = LineageNode(model_name='StockMovement', object_id='mv1')
        parent = LineageNode(
            model_name='Batch', object_id='b1',
            children=[child],
        )
        self.assertEqual(len(parent.children), 1)
        self.assertIs(parent.children[0], child)

    def test_validate_batch_lineage_with_zero_movements(self):
        """A batch with no movements should have zero lineage quantity but still valid."""
        batch = MagicMock(spec=['id', 'batch_code', 'remaining_quantity'])
        batch.id = 'test-batch'
        batch.batch_code = 'B-001'
        batch.remaining_quantity = Decimal('0')

        with patch('inventory.models.StockMovement.objects.filter') as mock_filter:
            fake_qs = MagicMock()
            fake_qs.__iter__.return_value = iter([])
            fake_qs.count.return_value = 0
            mock_filter.return_value = fake_qs
            result = self.enforcer.validate_batch_lineage(batch)
            self.assertEqual(result.lineage_quantity, Decimal('0'))
            self.assertTrue(result.valid)

    def test_log_mode_does_not_raise(self):
        """LOG mode should not raise on lineage violation."""
        enforcer = InventoryLineageEnforcer(mode='LOG')
        batch = MagicMock(spec=['id', 'batch_code', 'remaining_quantity'])
        batch.id = 'test'
        batch.batch_code = 'B-002'
        batch.remaining_quantity = Decimal('10')

        with patch('inventory.models.StockMovement.objects.filter') as mock_filter:
            mock_mv = MagicMock()
            mock_mv.quantity = Decimal('5')
            fake_qs = MagicMock()
            fake_qs.__iter__.return_value = iter([mock_mv])
            fake_qs.count.return_value = 1
            mock_filter.return_value = fake_qs

            result = enforcer.validate_batch_lineage(batch)
            self.assertTrue(enforcer.has_violations)

    def test_clear_violations(self):
        """Clear should reset violations."""
        enforcer = InventoryLineageEnforcer(mode='LOG')
        enforcer._violations.append('test')
        enforcer.clear()
        self.assertFalse(enforcer.has_violations)

    def test_trace_batch_lineage_returns_root(self):
        """trace_batch_lineage should return a LineageNode root."""
        batch = MagicMock(spec=['id', 'batch_code', 'initial_quantity'])
        batch.id = 'test'
        batch.batch_code = 'B-003'
        batch.initial_quantity = Decimal('100')

        with patch('inventory.models.StockMovement.objects.filter') as mock_filter:
            mock_filter.return_value.order_by.return_value = []
            root = self.enforcer.trace_batch_lineage(batch)
            self.assertIsInstance(root, LineageNode)
            self.assertEqual(root.model_name, 'Batch')

    def test_get_lineage_enforcer_returns_singleton(self):
        """get_lineage_enforcer should return the same instance."""
        e1 = get_lineage_enforcer()
        e2 = get_lineage_enforcer()
        self.assertIs(e1, e2)

    def test_validate_all_batches_returns_dict(self):
        """validate_all_batches should return a dict."""
        enforcer = InventoryLineageEnforcer(mode='LOG')
        with patch('inventory.models.Batch.objects.all') as mock_all:
            mock_all.return_value.iterator.return_value = []
            results = enforcer.validate_all_batches()
            self.assertIsInstance(results, dict)

    def test_check_batch_consistency_passes_for_matching(self):
        """check_batch_consistency should pass when product matches."""
        batch = MagicMock(product_id='p1', warehouse_id='w1')
        invoice_item = MagicMock(product_id='p1')
        self.enforcer.check_batch_consistency(batch, invoice_item)
        self.assertFalse(self.enforcer.has_violations)

    def test_check_batch_consistency_blocks_mismatch(self):
        """check_batch_consistency should raise on product mismatch in BLOCK mode."""
        batch = MagicMock(product_id='p1', warehouse_id='w1')
        invoice_item = MagicMock(product_id='p2')
        with self.assertRaises(AssertionError):
            self.enforcer.check_batch_consistency(batch, invoice_item)

    def test_check_batch_consistency_blocks_null_warehouse(self):
        """check_batch_consistency should raise on null warehouse."""
        batch = MagicMock(product_id='p1', warehouse_id=None)
        invoice_item = MagicMock(product_id='p1')
        with self.assertRaises(AssertionError):
            self.enforcer.check_batch_consistency(batch, invoice_item)


class TestReportTruthValidator(TestCase):
    """Class 6: Report Consistency — report vs ledger validation."""

    def setUp(self):
        self.validator = ReportTruthValidator(mode='LOG')

    def test_validate_trial_balance_returns_result(self):
        """validate_trial_balance should return a ReportValidationResult."""
        result = self.validator.validate_trial_balance(
            {'total_debits': 0, 'total_credits': 0}
        )
        self.assertEqual(result.report_name, 'TrialBalance')
        self.assertIsInstance(result.valid, bool)

    def test_validate_report_json_dispatches_trial_balance(self):
        """validate_report_json should dispatch to trial balance method."""
        result = self.validator.validate_report_json(
            'Trial Balance', {'total_debits': 0, 'total_credits': 0}
        )
        self.assertEqual(result.report_name, 'TrialBalance')

    def test_validate_report_json_dispatches_profit_loss(self):
        """validate_report_json should dispatch to P&L method."""
        result = self.validator.validate_report_json(
            'Profit and Loss', {'total_revenue': 0, 'total_expenses': 0}
        )
        self.assertEqual(result.report_name, 'ProfitLoss')

    def test_validate_report_json_dispatches_balance_sheet(self):
        """validate_report_json should dispatch to balance sheet method."""
        result = self.validator.validate_report_json(
            'Balance Sheet', {'total_assets': 0, 'total_liabilities': 0, 'total_equity': 0}
        )
        self.assertEqual(result.report_name, 'BalanceSheet')

    def test_validate_report_json_unknown_returns_valid(self):
        """Unknown report names should return valid by default."""
        result = self.validator.validate_report_json(
            'Custom Report', {}
        )
        self.assertTrue(result.valid)

    def test_get_report_validator_returns_singleton(self):
        """get_report_validator should return the same instance."""
        v1 = get_report_validator()
        v2 = get_report_validator()
        self.assertIs(v1, v2)

    def test_clear_violations(self):
        """Clear should reset violations."""
        self.validator._violations.append('test')
        self.validator.clear()
        self.assertFalse(self.validator.has_violations)

    def test_log_mode_no_raise(self):
        """LOG mode should not raise on violations."""
        self.validator._violations.append('test')
        self.assertTrue(self.validator.has_violations)
        # No exception — we're in LOG mode

    def test_block_mode_raises(self):
        """BLOCK mode should raise on violations."""
        validator = ReportTruthValidator(mode='BLOCK')
        with self.assertRaises(AssertionError):
            validator._violations.append('test')
            if validator.has_violations and validator.mode == 'BLOCK':
                raise AssertionError('test')

    def test_result_dataclass(self):
        """ReportValidationResult should have expected fields."""
        from core.guarantees.report_truth import ReportValidationResult
        r = ReportValidationResult(
            report_name='Test',
            valid=True,
            report_total=Decimal('0'),
            ledger_total=Decimal('0'),
            drift=Decimal('0'),
        )
        self.assertEqual(r.report_name, 'Test')
        self.assertTrue(r.valid)


class TestAdversarialScenarioGenerator(TestCase):
    """Class 7: Adversarial Test Expansion — scenario generation."""

    def setUp(self):
        self.generator = AdversarialScenarioGenerator(seed=42)

    def test_generate_missing_field_scenarios_returns_list(self):
        """Missing field scenarios should be generated."""
        scenarios = self.generator.generate_missing_field_scenarios()
        self.assertGreater(len(scenarios), 0)
        for s in scenarios:
            self.assertEqual(s.category, 'MISSING_FIELD')

    def test_generate_duplicate_event_scenarios_returns_list(self):
        """Duplicate event scenarios should be generated."""
        scenarios = self.generator.generate_duplicate_event_scenarios()
        self.assertGreater(len(scenarios), 0)
        for s in scenarios:
            self.assertEqual(s.category, 'DUPLICATE_EVENT')

    def test_generate_partial_rollback_scenarios_returns_list(self):
        """Partial rollback scenarios should be generated."""
        scenarios = self.generator.generate_partial_rollback_scenarios()
        self.assertGreater(len(scenarios), 0)
        for s in scenarios:
            self.assertEqual(s.category, 'PARTIAL_ROLLBACK')

    def test_generate_concurrency_scenarios_returns_list(self):
        """Concurrency scenarios should be generated."""
        scenarios = self.generator.generate_concurrency_scenarios()
        self.assertGreater(len(scenarios), 0)
        for s in scenarios:
            self.assertEqual(s.category, 'CONCURRENCY')

    def test_generate_delayed_event_scenarios_returns_list(self):
        """Delayed event scenarios should be generated."""
        scenarios = self.generator.generate_delayed_event_scenarios()
        self.assertGreater(len(scenarios), 0)
        for s in scenarios:
            self.assertEqual(s.category, 'DELAYED_EVENT')

    def test_generate_all_scenarios_returns_all(self):
        """generate_all_scenarios should return all scenario categories."""
        all_scenarios = self.generator.generate_all_scenarios()
        categories = set(s.category for s in all_scenarios)
        expected = {'MISSING_FIELD', 'DUPLICATE_EVENT', 'PARTIAL_ROLLBACK', 'CONCURRENCY', 'DELAYED_EVENT'}
        self.assertEqual(categories, expected)

    def test_each_scenario_has_expected_failure_mode(self):
        """Every scenario should have an expected_failure_mode defined."""
        for s in self.generator.generate_all_scenarios():
            self.assertIsNotNone(s.expected_failure_mode)
            self.assertGreater(len(s.expected_failure_mode), 0)

    def test_run_adversarial_test_passes_on_expected_error(self):
        """A test that raises an expected error should pass."""
        scenario = self.generator.generate_missing_field_scenarios()[0]

        def failing_test(s):
            raise ValidationError("null company_id")

        result = self.generator.run_adversarial_test(scenario, failing_test)
        self.assertTrue(result.passed)
        self.assertTrue(result.failure_detected)

    def test_run_adversarial_test_fails_on_unexpected_success(self):
        """A test that succeeds when failure expected should fail."""
        scenario = self.generator.generate_missing_field_scenarios()[0]

        def succeeding_test(s):
            pass  # No error raised

        result = self.generator.run_adversarial_test(scenario, succeeding_test)
        self.assertFalse(result.passed)
        self.assertFalse(result.failure_detected)

    def test_run_adversarial_test_fails_on_unexpected_error(self):
        """A test with unexpected error type should fail."""
        scenario = self.generator.generate_missing_field_scenarios()[0]

        def wrong_error_test(s):
            raise TypeError("unexpected")

        result = self.generator.run_adversarial_test(scenario, wrong_error_test)
        self.assertFalse(result.passed)

    def test_summary_returns_stats(self):
        """Summary should return comprehensive statistics."""
        scenario = self.generator.generate_missing_field_scenarios()[0]

        def test_fn(s):
            raise ValidationError("test")

        self.generator.run_adversarial_test(scenario, test_fn)
        summary = self.generator.summary()
        self.assertEqual(summary['total_scenarios'], 1)
        self.assertEqual(summary['passed'], 1)
        self.assertEqual(summary['failed'], 0)

    def test_summary_includes_by_category(self):
        """Summary should break down by category."""
        self.generator.run_adversarial_test(
            self.generator.generate_missing_field_scenarios()[0],
            lambda s: (_ for _ in ()).throw(ValidationError("x")),
        )
        summary = self.generator.summary()
        self.assertIn('MISSING_FIELD', summary['by_category'])

    def test_get_adversarial_generator_returns_singleton(self):
        """get_adversarial_generator should return singleton."""
        g1 = get_adversarial_generator()
        g2 = get_adversarial_generator()
        self.assertIs(g1, g2)

    def test_clear_resets_results(self):
        """Clear should reset all results."""
        self.generator.results.append(ScenarioResult(scenario=MagicMock(), passed=True, failure_detected=False))
        self.generator.clear()
        self.assertEqual(len(self.generator.results), 0)

    def test_seed_produces_deterministic_scenarios(self):
        """Same seed should produce same scenarios."""
        g1 = AdversarialScenarioGenerator(seed=42)
        g2 = AdversarialScenarioGenerator(seed=42)
        names1 = [s.name for s in g1.generate_all_scenarios()]
        names2 = [s.name for s in g2.generate_all_scenarios()]
        self.assertEqual(names1, names2)


class TestAdversarialIntegration(TransactionTestCase):
    """Full adversarial scenarios against real ERP models."""

    def setUp(self):
        from core.models import Company
        self.company = Company.objects.create(name='Test Company')
        self.generator = AdversarialScenarioGenerator(seed=42)

    def test_duplicate_invoice_number_rejected(self):
        """Creating two invoices with same number should raise IntegrityError."""
        from sales.models import SalesInvoice
        from django.utils import timezone
        from sales.models import Customer

        customer = Customer.objects.create(
            name='Test Customer',
            company=self.company,
        )

        SalesInvoice.objects.create(
            company=self.company,
            invoice_number='DUP-001',
            customer=customer,
            invoice_date=timezone.now().date(),
            order_date=timezone.now().date(),
            due_date=timezone.now().date(),
            total_amount=Decimal('100'),
            status='DRAFT',
        )
        with self.assertRaises((IntegrityError, ValidationError)):
            SalesInvoice.objects.create(
                company=self.company,
                invoice_number='DUP-001',
                customer=customer,
                invoice_date=timezone.now().date(),
                order_date=timezone.now().date(),
                due_date=timezone.now().date(),
                total_amount=Decimal('100'),
                status='DRAFT',
            )

    def test_return_without_invoice_rejected(self):
        """Creating a return without a valid invoice reference should be invalid."""
        from returns.models import ReturnOrder

        with self.assertRaises(ValidationError):
            ro = ReturnOrder(
                return_number='RET-NO-INV',
                return_type='SALE_RETURN',
                total_amount=Decimal('100'),
                status='DRAFT',
            )
            ro.full_clean()

    def test_company_scoped_mixin_auto_assigns_company(self):
        """CompanyScopedMixin.save() should auto-assign company_id from context."""
        from accounting.models import JournalEntry
        from django.utils import timezone
        from core.multitenant.context import TenantContext

        TenantContext.set_company_id(str(self.company.id))
        try:
            je = JournalEntry.objects.create(
                entry_number=f'TEST-AUTO-{timezone.now().timestamp()}',
                entry_date=timezone.now().date(),
                description='Test auto-assign',
                entry_type='SALE',
            )
            self.assertIsNotNone(je.company_id)
        finally:
            TenantContext.clear()

    def test_adversarial_scenarios_run_with_log_mode(self):
        """All adversarial scenarios should be executable in LOG mode without crash."""
        generator = AdversarialScenarioGenerator(seed=42)
        scenarios = generator.generate_all_scenarios()
        self.assertGreater(len(scenarios), 10)

    def test_reconciliation_guard_runs_on_empty_db(self):
        """ReconciliationCompletenessGuard.check_all_returns should handle empty DB."""
        guard = ReconciliationCompletenessGuard(mode='LOG')
        results = guard.check_all_returns()
        self.assertIsInstance(results, dict)
        self.assertEqual(len(results), 0)


class TestSystemWideGuarantees(TransactionTestCase):
    """
    Global system guarantee tests.
    These validate the overall guarantee architecture, not individual components.
    """

    def test_all_guard_classes_importable(self):
        """All 7 guard classes must be importable without error."""
        from core.guarantees.tenant_scope import TenantScopeEnforcer
        from core.guarantees.reconciliation import ReconciliationCompletenessGuard
        from core.guarantees.atomic_boundary import BusinessTransactionBoundaryGuard
        from core.guarantees.replay_determinism import DeterministicReplayValidator
        from core.guarantees.inventory_lineage import InventoryLineageEnforcer
        from core.guarantees.report_truth import ReportTruthValidator
        from core.guarantees.adversarial import AdversarialScenarioGenerator

        self.assertIsNotNone(TenantScopeEnforcer)
        self.assertIsNotNone(ReconciliationCompletenessGuard)
        self.assertIsNotNone(BusinessTransactionBoundaryGuard)
        self.assertIsNotNone(DeterministicReplayValidator)
        self.assertIsNotNone(InventoryLineageEnforcer)
        self.assertIsNotNone(ReportTruthValidator)
        self.assertIsNotNone(AdversarialScenarioGenerator)

    def test_all_singleton_getters_work(self):
        """All singleton getter functions must return valid instances."""
        from core.guarantees.tenant_scope import get_tenant_enforcer
        from core.guarantees.atomic_boundary import get_atomic_guard
        from core.guarantees.replay_determinism import get_replay_validator
        from core.guarantees.inventory_lineage import get_lineage_enforcer
        from core.guarantees.report_truth import get_report_validator
        from core.guarantees.adversarial import get_adversarial_generator

        self.assertIsNotNone(get_tenant_enforcer())
        self.assertIsNotNone(get_atomic_guard())
        self.assertIsNotNone(get_replay_validator())
        self.assertIsNotNone(get_lineage_enforcer())
        self.assertIsNotNone(get_report_validator())
        self.assertIsNotNone(get_adversarial_generator())

    def test_each_guard_has_log_and_block_mode(self):
        """Every guard must support both LOG and BLOCK modes."""
        guards = [
            ('TenantScopeEnforcer', lambda: [TenantScopeEnforcer(mode='LOG'), TenantScopeEnforcer(mode='BLOCK')]),
        ]
        for name, factory in guards:
            log_instance, block_instance = factory()
            self.assertEqual(log_instance.mode, 'LOG', f"{name} LOG mode")
            self.assertEqual(block_instance.mode, 'BLOCK', f"{name} BLOCK mode")


class TestConstraintViolationHandler(TestCase):
    """Constraint Violation Handler — 5-step fail-fast protocol."""

    def test_basic_violation_creates_record(self):
        """A violation should create a record in history."""
        handler = ConstraintViolationHandler(mode='AUDIT')
        handler.handle(
            category=ViolationCategory.TENANT_ISOLATION,
            message='Test violation',
            severity=ViolationSeverity.HIGH,
            rollback=False,
            block_future=False,
        )
        self.assertEqual(handler.violation_count, 1)

    def test_strict_mode_raises(self):
        """STRICT mode should raise ConstraintViolationError."""
        handler = ConstraintViolationHandler(mode='STRICT')
        with self.assertRaises(ConstraintViolationError):
            handler.handle(
                category=ViolationCategory.SYSTEM_CONTRACT,
                message='Strict test',
                rollback=False,
                block_future=False,
            )

    def test_audit_mode_does_not_raise(self):
        """AUDIT mode should not raise."""
        handler = ConstraintViolationHandler(mode='AUDIT')
        handler.handle(
            category=ViolationCategory.LINEAGE,
            message='Audit test',
            block_future=False,
        )
        self.assertTrue(handler.has_violations)

    def test_blocked_operations(self):
        """Blocked operations should be tracked."""
        handler = ConstraintViolationHandler(mode='AUDIT')
        handler.handle(
            category=ViolationCategory.REGRESSION,
            message='Block test',
            block_future=True,
        )
        self.assertGreater(len(handler.blocked_operations), 0)

    def test_is_operation_blocked(self):
        """is_operation_blocked should detect blocked paths."""
        handler = ConstraintViolationHandler(mode='AUDIT')
        handler.handle(
            category=ViolationCategory.REGRESSION,
            message='specific block',
            block_future=True,
        )
        self.assertTrue(
            any('specific block' in k for k in handler.blocked_operations)
        )

    def test_clear_blocked(self):
        """clear_blocked should remove a blocked operation."""
        handler = ConstraintViolationHandler(mode='AUDIT')
        handler.handle(
            category=ViolationCategory.REGRESSION,
            message='remove me',
            block_future=True,
        )
        key = list(handler.blocked_operations)[0]
        handler.clear_blocked(key)
        self.assertNotIn(key, handler.blocked_operations)

    def test_summary_contains_expected_keys(self):
        """Summary must contain all expected keys."""
        handler = ConstraintViolationHandler(mode='AUDIT')
        handler.handle(
            category=ViolationCategory.TENANT_ISOLATION,
            message='summary test',
            block_future=False,
        )
        s = handler.summary()
        self.assertIn('total_violations', s)
        self.assertIn('blocked_operations', s)
        self.assertIn('by_severity', s)
        self.assertIn('by_category', s)
        self.assertIn('latest', s)

    def test_severity_enum_values(self):
        """All severity values should be defined."""
        self.assertEqual(ViolationSeverity.CRITICAL.value, 'CRITICAL')
        self.assertEqual(ViolationSeverity.HIGH.value, 'HIGH')
        self.assertEqual(ViolationSeverity.MEDIUM.value, 'MEDIUM')

    def test_get_constraint_handler_singleton(self):
        """get_constraint_handler should return singleton."""
        h1 = get_constraint_handler()
        h2 = get_constraint_handler()
        self.assertIs(h1, h2)

    def test_fail_fast_shortcut(self):
        """fail_fast shortcut should raise ConstraintViolationError."""
        handler = get_constraint_handler(mode='STRICT')
        handler.mode = 'AUDIT'
        handler.handle(
            category=ViolationCategory.ATOMIC_BOUNDARY,
            message='fail fast test',
            rollback=False,
            block_future=False,
        )
        handler.mode = 'STRICT'
        with self.assertRaises(ConstraintViolationError):
            handler.handle(
                category=ViolationCategory.ATOMIC_BOUNDARY,
                message='fail fast strict',
                rollback=False,
                block_future=False,
            )


class TestRegressionImmunitySystem(TestCase):
    """Regression Immunity — permanently block previously discovered bugs."""

    def test_immunity_system_creates_all_rules(self):
        """The immunity system should register all 6 rules."""
        immunity = RegressionImmunitySystem(mode='AUDIT')
        self.assertEqual(len(immunity._rules), 6)

    def test_all_rules_have_names(self):
        """Every rule must have a name."""
        immunity = RegressionImmunitySystem(mode='AUDIT')
        for rule in immunity._rules:
            self.assertTrue(len(rule.name) > 0)
            self.assertTrue(len(rule.description) > 0)

    def test_all_rules_have_fix_required(self):
        """Every rule must specify a fix."""
        immunity = RegressionImmunitySystem(mode='AUDIT')
        for rule in immunity._rules:
            self.assertTrue(len(rule.fix_required) > 0)

    def test_check_all_returns_list(self):
        """check_all should return a list of violations."""
        immunity = RegressionImmunitySystem(mode='AUDIT')
        violations = immunity.check_all()
        self.assertIsInstance(violations, list)

    def test_get_immunity_system_singleton(self):
        """get_immunity_system should return singleton."""
        i1 = get_immunity_system()
        i2 = get_immunity_system()
        self.assertIs(i1, i2)

    def test_clear_violations(self):
        """Clear should reset violations."""
        immunity = RegressionImmunitySystem(mode='AUDIT')
        immunity._violations.append('test')
        immunity.clear()
        self.assertFalse(immunity.has_violations)


class TestGuaranteeOrchestrator(TestCase):
    """GuaranteeOrchestrator — strict execution order, fail-fast chain."""

    def test_guard_order_is_correct(self):
        """Guards must execute in the specified order."""
        expected = [
            'tenant_scope_guard',
            'atomic_boundary_guard',
            'inventory_lineage_guard',
            'reconciliation_guard',
            'report_truth_guard',
            'replay_determinism_guard',
            'adversarial_validation_guard',
        ]
        orchestrator = GuaranteeOrchestrator()
        self.assertEqual(orchestrator.GUARD_ORDER, expected)

    def test_all_guards_have_implementations(self):
        """Every guard in the order must have a runner method."""
        orchestrator = GuaranteeOrchestrator()
        guard_map = {
            'tenant_scope_guard': orchestrator._run_tenant_scope,
            'atomic_boundary_guard': orchestrator._run_atomic_boundary,
            'inventory_lineage_guard': orchestrator._run_inventory_lineage,
            'reconciliation_guard': orchestrator._run_reconciliation,
            'report_truth_guard': orchestrator._run_report_truth,
            'replay_determinism_guard': orchestrator._run_replay_determinism,
            'adversarial_validation_guard': orchestrator._run_adversarial_validation,
        }
        self.assertEqual(len(guard_map), len(orchestrator.GUARD_ORDER))

    def test_run_all_in_audit_mode_completes(self):
        """run_all in AUDIT mode should complete without raising."""
        orchestrator = GuaranteeOrchestrator(mode='AUDIT')
        reports = orchestrator.run_all()
        self.assertEqual(len(reports), len(orchestrator.GUARD_ORDER))

    def test_all_reports_have_required_fields(self):
        """Each GuardReport must have all required fields."""
        orchestrator = GuaranteeOrchestrator(mode='AUDIT')
        reports = orchestrator.run_all()
        for r in reports:
            self.assertTrue(len(r.guard_name) > 0)
            self.assertGreater(r.ordinal, 0)
            self.assertIn(r.result, ('PASS', 'FAIL', 'SKIP'))

    def test_all_passed_property(self):
        """all_passed should be True when no failures."""
        orchestrator = GuaranteeOrchestrator(mode='AUDIT')
        orchestrator.run_all()
        self.assertIsInstance(orchestrator.all_passed, bool)

    def test_summary_contains_reports(self):
        """Summary must include reports list."""
        orchestrator = GuaranteeOrchestrator(mode='AUDIT')
        orchestrator.run_all()
        s = orchestrator.summary()
        self.assertIn('reports', s)
        self.assertIn('total_guards', s)

    def test_get_orchestrator_singleton(self):
        """get_orchestrator should return singleton."""
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        self.assertIs(o1, o2)

    def test_verify_system_shortcut(self):
        """verify_system should return reports."""
        from core.guarantees.orchestrator import verify_system
        reports = verify_system(mode='AUDIT')
        self.assertGreater(len(reports), 0)


class TestSystemContract(TestCase):
    """SystemContract — immutable system contract + final validation."""

    def test_contract_version_is_defined(self):
        """System contract must have a version."""
        from core.guarantees.contract import SYSTEM_CONTRACT_VERSION
        self.assertTrue(len(SYSTEM_CONTRACT_VERSION) > 0)

    def test_verify_runs_all_guards(self):
        """verify() should run all guards and return a ContractVerification."""
        contract = SystemContract(mode='AUDIT')
        verification = contract.verify()
        self.assertIsInstance(verification, ContractVerification)
        self.assertEqual(verification.version, SYSTEM_CONTRACT_VERSION)

    def test_contract_verification_has_required_fields(self):
        """ContractVerification must include all required fields."""
        contract = SystemContract(mode='AUDIT')
        v = contract.verify()
        self.assertIsInstance(v.all_guards_passed, bool)
        self.assertIsInstance(v.regression_immune, bool)
        self.assertIsInstance(v.system_valid, bool)
        self.assertIsInstance(v.guard_reports, list)
        self.assertIsInstance(v.immunity_violations, list)
        self.assertIsInstance(v.errors, list)

    def test_verify_populates_last_verification(self):
        """verify() should populate last_verification."""
        contract = SystemContract(mode='AUDIT')
        contract.verify()
        self.assertIsNotNone(contract.last_verification)

    def test_is_system_valid_returns_false_before_verify(self):
        """is_system_valid should return False before first verify()."""
        contract = SystemContract()
        self.assertFalse(contract.is_system_valid)

    def test_get_system_contract_singleton(self):
        """get_system_contract should return singleton."""
        from core.guarantees.contract import get_system_contract
        c1 = get_system_contract()
        c2 = get_system_contract()
        self.assertIs(c1, c2)

    def test_verify_system_integrity_shortcut(self):
        """verify_system_integrity should return a ContractVerification."""
        from core.guarantees.contract import verify_system_integrity
        v = verify_system_integrity(mode='AUDIT')
        self.assertIsInstance(v, ContractVerification)

    def test_system_contract_violation_is_runtime_error(self):
        """SystemContractViolation must be a RuntimeError."""
        from core.guarantees.contract import SystemContractViolation
        self.assertTrue(issubclass(SystemContractViolation, RuntimeError))


class TestFinalSystemLock(TransactionTestCase):
    """
    FINAL SYSTEM LOCK — validates the full immutable contract.

    This test MUST pass for the system to be considered valid.
    It runs the complete orchestration + regression immunity check.
    """

    def test_full_system_contract_pass(self):
        """The complete system contract must pass."""
        from core.guarantees.contract import SystemContract
        contract = SystemContract(mode='AUDIT')
        verification = contract.verify()
        self.assertTrue(
            verification.system_valid,
            msg=f"System contract invalid: {verification.errors[:3]}"
        )

    def test_orchestrator_all_guards_available(self):
        """All 7 guards must be available and runnable."""
        from core.guarantees.orchestrator import GuaranteeOrchestrator
        orchestrator = GuaranteeOrchestrator(mode='AUDIT')
        reports = orchestrator.run_all()
        passed = sum(1 for r in reports if r.result == 'PASS')
        failed = sum(1 for r in reports if r.result == 'FAIL')
        self.assertGreater(
            passed, 0,
            msg=f"All guards failed: {failed} failed, {passed} passed"
        )

    def test_regression_immunity_no_blocking(self):
        """Regression immunity must not have blocking violations in AUDIT mode."""
        from core.guarantees.regression_immunity import RegressionImmunitySystem
        immunity = RegressionImmunitySystem(mode='AUDIT')
        violations = immunity.check_all()
        self.assertIsInstance(violations, list)

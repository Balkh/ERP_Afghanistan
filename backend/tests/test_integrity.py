import time
from datetime import datetime, timezone

from django.db import models, connection
from django.test import TestCase

from core.integrity.engine import IntegrityEngine, integrity_guard, require_integrity
from core.integrity.freeze import ImmutableIntegrityLedger, SystemFreezeKillSwitch
from core.integrity.gate import PreWriteValidationGate
from core.integrity.models import (
    DriftResult,
    FreezeState,
    IntegrityEvent,
    IntegrityLevel,
    OperationType,
    ValidationResult,
    VerificationResult,
)
from core.integrity.controller import (
    AutoRollbackEngine,
    PostWriteVerificationLayer,
    TransactionIntegrityController,
)
from core.integrity.detector import RealTimeDriftDetector


class TestValidationResult(TestCase):
    def test_allow_creates_passing_result(self):
        r = ValidationResult.allow()
        self.assertTrue(r.allowed)

    def test_allow_with_reason(self):
        r = ValidationResult.allow("Custom allowed")
        self.assertEqual(r.reason, "Custom allowed")

    def test_block_creates_failing_result(self):
        r = ValidationResult.block("Blocked")
        self.assertFalse(r.allowed)
        self.assertEqual(r.reason, "Blocked")

    def test_block_with_blocked_by(self):
        r = ValidationResult.block("Denied", "policy_xyz")
        self.assertEqual(r.blocked_by, "policy_xyz")


class TestVerificationResult(TestCase):
    def test_clean_passes(self):
        r = VerificationResult.clean()
        self.assertTrue(r.passed)

    def test_failed_with_violations(self):
        r = VerificationResult.failed(
            fk_violations=[{"table": "x", "rowid": 1}],
            orphans=3,
        )
        self.assertFalse(r.passed)
        self.assertEqual(len(r.fk_violations), 1)
        self.assertEqual(r.orphan_count, 3)


class TestDriftResult(TestCase):
    def test_stable_no_drift(self):
        r = DriftResult.stable("abc", "abc")
        self.assertFalse(r.has_drifted)
        self.assertEqual(r.baseline_hash, "abc")

    def test_drift_detected(self):
        r = DriftResult.drift_detected("abc", "def", "schema changed")
        self.assertTrue(r.has_drifted)
        self.assertEqual(r.details, "schema changed")


class TestIntegrityEvent(TestCase):
    def test_timestamp_is_set(self):
        e = IntegrityEvent()
        self.assertIsNotNone(e.timestamp)

    def test_defaults(self):
        e = IntegrityEvent()
        self.assertFalse(e.rolled_back)
        self.assertFalse(e.frozen)


class TestPreWriteValidationGate(TestCase):
    def setUp(self):
        self.gate = PreWriteValidationGate.get_instance()
        self.gate.clear_rules()

    def test_block_system_table_prefix(self):
        class FakeModel:
            class _meta:
                db_table = "django_session"
                label_lower = "django.session"
                fields = []
        result = self.gate.validate_write(FakeModel, OperationType.CREATE, {})
        self.assertFalse(result.allowed)
        self.assertIn("System table", result.reason)

    def test_block_system_model_label(self):
        class FakeModel:
            class _meta:
                db_table = "sessions_session"
                label_lower = "sessions.session"
                fields = []
        result = self.gate.validate_write(FakeModel, OperationType.CREATE, {})
        self.assertFalse(result.allowed)
        self.assertEqual(result.blocked_by, "model_whitelist")

    def test_allow_operational_model(self):
        from inventory.models import Product

        result = self.gate.validate_write(Product, OperationType.UPDATE, {"name": "test"})
        self.assertTrue(result.allowed)

    def test_block_delete_operation(self):
        from inventory.models import Product

        result = self.gate.validate_write(Product, OperationType.DELETE, {})
        self.assertFalse(result.allowed)
        self.assertEqual(result.blocked_by, "operation_safety")

    def test_block_unknown_fields(self):
        from inventory.models import Product

        result = self.gate.validate_write(
            Product, OperationType.CREATE, {"nonexistent_field": "value"}
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.blocked_by, "schema_compliance")

    def test_custom_rule_registration(self):
        call_count = [0]

        def my_rule(ctx):
            call_count[0] += 1
            return (True, "custom allowed")

        self.gate.register_rule("test_rule", my_rule, "Test rule")
        from inventory.models import Product

        result = self.gate.validate_write(Product, OperationType.CREATE, {"name": "x"})
        self.assertTrue(result.allowed)
        self.assertGreater(call_count[0], 0)

    def test_custom_rule_can_block(self):
        def blocking_rule(ctx):
            return (False, "Custom block")

        self.gate.register_rule("block_rule", blocking_rule, "Blocking rule")
        from inventory.models import Product

        result = self.gate.validate_write(Product, OperationType.CREATE, {"name": "x"})
        self.assertFalse(result.allowed)
        self.assertEqual(result.blocked_by, "block_rule")

    def test_validate_bulk(self):
        from inventory.models import Product, Warehouse, Category

        operations = [
            {"model_class": Product, "operation_type": OperationType.CREATE, "data": {"name": "p1"}},
            {"model_class": Warehouse, "operation_type": OperationType.DELETE, "data": {}},
        ]
        results = self.gate.validate_bulk(operations)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].allowed)
        self.assertFalse(results[1].allowed)


class TestTransactionIntegrityController(TestCase):
    def setUp(self):
        self.controller = TransactionIntegrityController.get_instance()
        self.verifier = PostWriteVerificationLayer.get_instance()
        self.rollback = AutoRollbackEngine.get_instance()
        self.controller.configure(self.verifier, self.rollback)
        self.rollback.clear_failure_log()

    def test_execute_successful(self):
        result = self.controller.execute_atomic(
            operation_fn=lambda: 42,
            model_class=None,
            verify_after=False,
        )
        self.assertTrue(result.get("success"))
        self.assertEqual(result["result"], 42)

    def test_execute_rolls_back_on_exception(self):
        def failing():
            raise ValueError("Intentional failure")

        result = self.controller.execute_atomic(failing, None, verify_after=False)
        self.assertFalse(result.get("success"))
        self.assertIn("Intentional failure", result.get("error", ""))

    def test_execute_logs_rollback(self):
        def failing():
            raise RuntimeError("Roll me back")

        self.controller.execute_atomic(failing, None, verify_after=False)
        self.assertGreater(self.rollback.failure_count(), 0)


class TestPostWriteVerificationLayer(TestCase):
    def setUp(self):
        self.verifier = PostWriteVerificationLayer.get_instance()

    def test_verify_fk_integrity_clean(self):
        violations = self.verifier.verify_fk_integrity()
        self.assertEqual(len(violations), 0)

    def test_verify_model_clean_on_operational_model(self):
        from inventory.models import Product
        result = self.verifier.verify_model(Product)
        self.assertTrue(result.passed)


class TestAutoRollbackEngine(TestCase):
    def setUp(self):
        self.rollback = AutoRollbackEngine.get_instance()
        self.rollback.clear_failure_log()

    def test_trigger_rollback_logs(self):
        entry = self.rollback.trigger_rollback("Test failure", "test_op", "test_model")
        self.assertTrue(entry["rolled_back"])
        self.assertEqual(entry["action"], "ROLLBACK")

    def test_failure_count(self):
        self.rollback.trigger_rollback("Fail 1")
        self.rollback.trigger_rollback("Fail 2")
        self.assertEqual(self.rollback.failure_count(), 2)

    def test_get_failure_log(self):
        self.rollback.trigger_rollback("Fail A")
        log = self.rollback.get_failure_log()
        self.assertEqual(len(log), 1)

    def test_clear_failure_log(self):
        self.rollback.trigger_rollback("Fail")
        self.rollback.clear_failure_log()
        self.assertEqual(self.rollback.failure_count(), 0)


class TestSystemFreezeKillSwitch(TestCase):
    def setUp(self):
        self.freeze = SystemFreezeKillSwitch.get_instance()
        if self.freeze.is_frozen():
            self.freeze.unfreeze("test")

    def test_initial_state_unfrozen(self):
        state = self.freeze.get_state()
        self.assertEqual(state["state"], FreezeState.UNFROZEN.value)

    def test_freeze_changes_state(self):
        result = self.freeze.freeze("Test freeze", "test_user")
        self.assertEqual(result["state"], FreezeState.FROZEN.value)
        self.assertEqual(result["reason"], "Test freeze")
        self.assertEqual(result["frozen_by"], "test_user")

    def test_is_frozen_returns_true(self):
        self.freeze.freeze("Testing")
        self.assertTrue(self.freeze.is_frozen())
        self.freeze.unfreeze("test")

    def test_unfreeze_requires_approval(self):
        self.freeze.freeze("Frozen")
        result = self.freeze.unfreeze(approver="")
        self.assertIn("error", result)
        self.assertFalse(result.get("unfrozen", False))
        self.freeze.unfreeze("admin")

    def test_unfreeze_with_approver(self):
        self.freeze.freeze("Frozen")
        result = self.freeze.unfreeze("admin", "Approved unfreeze")
        self.assertTrue(result["unfrozen"])
        self.assertFalse(self.freeze.is_frozen())

    def test_require_unfrozen_blocks_when_frozen(self):
        self.freeze.freeze("Blocked")
        block = self.freeze.require_unfrozen()
        self.assertIsNotNone(block)
        self.assertFalse(block["allowed"])
        self.freeze.unfreeze("admin")

    def test_require_unfrozen_passes_when_unfrozen(self):
        self.freeze.unfreeze("admin")
        block = self.freeze.require_unfrozen()
        self.assertIsNone(block)

    def test_permanent_freeze(self):
        result = self.freeze.permanent_freeze("Permanent")
        self.assertEqual(result["state"], FreezeState.PERMANENT_FREEZE.value)
        self.assertTrue(self.freeze.is_frozen())

    def test_set_approval_required(self):
        self.freeze.set_approval_required(False)
        self.freeze.freeze("Quick")
        result = self.freeze.unfreeze()
        self.assertTrue(result["unfrozen"])
        self.freeze.set_approval_required(True)


class TestImmutableIntegrityLedger(TestCase):
    def setUp(self):
        self.ledger = ImmutableIntegrityLedger.get_instance()
        self.ledger.clear()

    def test_log_event_increases_count(self):
        count = self.ledger.log_event(IntegrityEvent(operation_type="test"))
        self.assertEqual(count, 1)

    def test_log_convenience_method(self):
        count = self.ledger.log(
            operation_type="create",
            model_class="test.Product",
            validation_result="ALLOWED",
            verification_result="PASS",
        )
        self.assertEqual(count, 1)

    def test_get_events(self):
        self.ledger.log(operation_type="op1")
        self.ledger.log(operation_type="op2")
        events = self.ledger.get_events(limit=10)
        self.assertEqual(len(events), 2)

    def test_get_recent(self):
        for i in range(5):
            self.ledger.log(operation_type=f"op{i}")
        recent = self.ledger.get_recent(3)
        self.assertEqual(len(recent), 3)

    def test_count(self):
        self.ledger.log(operation_type="a")
        self.ledger.log(operation_type="b")
        self.assertEqual(self.ledger.count(), 2)

    def test_clear(self):
        self.ledger.log(operation_type="x")
        self.ledger.clear()
        self.assertEqual(self.ledger.count(), 0)

    def test_get_summary(self):
        self.ledger.log(operation_type="ok", verification_result="PASS")
        self.ledger.log(
            operation_type="fail",
            verification_result="FAIL",
            rolled_back=True,
        )
        self.ledger.log(
            operation_type="blocked",
            validation_result="BLOCKED",
        )
        summary = self.ledger.get_summary()
        self.assertEqual(summary["total_events"], 3)
        self.assertEqual(summary["rollbacks"], 1)
        self.assertEqual(summary["failures"], 2)

    def test_max_events(self):
        for i in range(10001):
            self.ledger.log(operation_type=f"ev{i}")
        self.assertLessEqual(self.ledger.count(), 10000)


class TestRealTimeDriftDetector(TestCase):
    def setUp(self):
        self.detector = RealTimeDriftDetector.get_instance()

    def test_compute_schema_hash_returns_string(self):
        h = self.detector.compute_schema_hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_compute_table_registry_hash_returns_string(self):
        h = self.detector.compute_table_registry_hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_compute_governance_hash_returns_string(self):
        h = self.detector.compute_governance_hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_compute_full_hash_returns_dict(self):
        h = self.detector.compute_full_hash()
        self.assertIn("schema", h)
        self.assertIn("table_registry", h)
        self.assertIn("governance", h)
        self.assertEqual(len(h["schema"]), 64)

    def test_capture_baseline_returns_hash(self):
        baseline = self.detector.capture_baseline()
        self.assertIn("schema", baseline)
        self.assertIsNotNone(self.detector.get_baseline())

    def test_detect_drift_no_drift_after_baseline(self):
        self.detector.capture_baseline()
        drift = self.detector.detect_drift()
        self.assertFalse(drift.has_drifted)

    def test_detect_drift_stable_on_repeat(self):
        self.detector.capture_baseline()
        drift1 = self.detector.detect_drift()
        drift2 = self.detector.detect_drift()
        self.assertEqual(drift1.has_drifted, drift2.has_drifted)


class TestIntegrityEngine(TestCase):
    def setUp(self):
        self.engine = IntegrityEngine.get_instance()
        self.engine.configure()
        self.engine.enable()
        self.ledger = ImmutableIntegrityLedger.get_instance()
        self.ledger.clear()
        self.freeze = SystemFreezeKillSwitch.get_instance()
        if self.freeze.is_frozen():
            self.freeze.unfreeze("test")
        self.detector = RealTimeDriftDetector.get_instance()
        self.detector.capture_baseline()

    def test_enforce_operation_success(self):
        def add(a, b):
            return a + b

        from inventory.models import Product
        result = self.engine.enforce_operation(
            operation_fn=lambda: add(40, 2),
            model_class=Product,
            operation_type=OperationType.UPDATE,
            data={"name": "test"},
            verify_after=False,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 42)

    def test_enforce_operation_blocks_system_model(self):
        def harmless():
            return "done"

        class FakeSystemModel:
            class _meta:
                db_table = "django_migrations"
                label_lower = "django.migrations"
                fields = []

        result = self.engine.enforce_operation(
            operation_fn=harmless,
            model_class=FakeSystemModel,
            operation_type=OperationType.CREATE,
            data={},
            verify_after=False,
        )
        self.assertFalse(result["success"])

    def test_enforce_operation_blocks_when_frozen(self):
        self.freeze.freeze("Testing freeze")

        def harmless():
            return "done"

        from inventory.models import Product
        result = self.engine.enforce_operation(
            operation_fn=harmless,
            model_class=Product,
            operation_type=OperationType.UPDATE,
            data={"name": "x"},
            verify_after=False,
        )
        self.assertFalse(result["success"])
        self.assertIn("frozen", result.get("error", ""))
        self.freeze.unfreeze("admin")

    def test_disable_skips_integrity(self):
        self.engine.disable()

        from inventory.models import Product

        def harmless():
            return "bypassed"

        result = self.engine.enforce_operation(
            operation_fn=harmless,
            model_class=Product,
            operation_type=OperationType.CREATE,
            data={"name": "x"},
        )
        self.assertTrue(result["success"])
        self.assertTrue(result.get("integrity_skipped", False))
        self.engine.enable()

    def test_ledger_logs_successful_operation(self):
        from inventory.models import Product

        self.engine.enforce_operation(
            operation_fn=lambda: "ok",
            model_class=Product,
            operation_type=OperationType.UPDATE,
            data={"name": "test"},
            verify_after=False,
        )
        self.assertGreater(self.ledger.count(), 0)

    def test_drift_captured_in_baseline(self):
        baseline = self.detector.get_baseline()
        self.assertIsNotNone(baseline)
        self.assertIn("schema", baseline)


class TestIntegrityGuardDecorator(TestCase):
    def setUp(self):
        self.engine = IntegrityEngine.get_instance()
        self.engine.configure()
        self.engine.enable()

    def test_integrity_guard_blocks_system_write(self):
        @integrity_guard(operation_type=OperationType.CREATE)
        def write_something():
            return "written"

        from inventory.models import Product
        result = IntegrityEngine.get_instance().enforce_operation(
            operation_fn=write_something,
            model_class=Product,
            operation_type=OperationType.CREATE,
            data={},
            verify_after=False,
        )
        self.assertTrue(result.get("success", False))

    def test_require_integrity_decorator(self):
        call_count = [0]

        @require_integrity
        def business_op():
            call_count[0] += 1
            return "done"

        result = business_op()
        self.assertEqual(result, "done")
        self.assertEqual(call_count[0], 1)


class TestIntegrityEventModel(TestCase):
    def test_event_fields(self):
        e = IntegrityEvent(
            operation_type="create",
            model_class="inventory.Product",
            validation_result="ALLOWED",
            verification_result="PASS",
            failure_reason="",
            system_hash="abc123",
            rolled_back=False,
            frozen=False,
        )
        self.assertEqual(e.operation_type, "create")
        self.assertEqual(e.model_class, "inventory.Product")
        self.assertEqual(e.validation_result, "ALLOWED")
        self.assertEqual(e.verification_result, "PASS")
        self.assertEqual(e.system_hash, "abc123")


class TestSingletonPatterns(TestCase):
    def test_gate_singleton(self):
        g1 = PreWriteValidationGate.get_instance()
        g2 = PreWriteValidationGate.get_instance()
        self.assertIs(g1, g2)

    def test_controller_singleton(self):
        c1 = TransactionIntegrityController.get_instance()
        c2 = TransactionIntegrityController.get_instance()
        self.assertIs(c1, c2)

    def test_verifier_singleton(self):
        v1 = PostWriteVerificationLayer.get_instance()
        v2 = PostWriteVerificationLayer.get_instance()
        self.assertIs(v1, v2)

    def test_rollback_singleton(self):
        r1 = AutoRollbackEngine.get_instance()
        r2 = AutoRollbackEngine.get_instance()
        self.assertIs(r1, r2)

    def test_detector_singleton(self):
        d1 = RealTimeDriftDetector.get_instance()
        d2 = RealTimeDriftDetector.get_instance()
        self.assertIs(d1, d2)

    def test_freeze_singleton(self):
        f1 = SystemFreezeKillSwitch.get_instance()
        f2 = SystemFreezeKillSwitch.get_instance()
        self.assertIs(f1, f2)

    def test_ledger_singleton(self):
        l1 = ImmutableIntegrityLedger.get_instance()
        l2 = ImmutableIntegrityLedger.get_instance()
        self.assertIs(l1, l2)

    def test_engine_singleton(self):
        e1 = IntegrityEngine.get_instance()
        e2 = IntegrityEngine.get_instance()
        self.assertIs(e1, e2)


class TestOperationTypeEnum(TestCase):
    def test_all_types_present(self):
        expected = {
            "CREATE", "UPDATE", "DELETE",
            "BULK_CREATE", "BULK_UPDATE", "BULK_DELETE",
            "RAW_SQL",
        }
        actual = {t.name for t in OperationType}
        self.assertEqual(actual, expected)

    def test_values_match_strings(self):
        self.assertEqual(OperationType.CREATE.value, "create")
        self.assertEqual(OperationType.DELETE.value, "delete")
        self.assertEqual(OperationType.RAW_SQL.value, "raw_sql")


class TestFreezeStateEnum(TestCase):
    def test_all_states_present(self):
        expected = {"UNFROZEN", "FROZEN", "THAWING", "PERMANENT_FREEZE"}
        actual = {s.name for s in FreezeState}
        self.assertEqual(actual, expected)


class TestIntegrityLevelEnum(TestCase):
    def test_all_levels_present(self):
        expected = {
            "VALIDATION_FAIL", "FK_VIOLATION", "SCHEMA_DRIFT",
            "UNKNOWN_STATE", "PARTIAL_WRITE", "CLEAN",
        }
        actual = {l.name for l in IntegrityLevel}
        self.assertEqual(actual, expected)


class TestVerificationEdgeCases(TestCase):
    def setUp(self):
        self.verifier = PostWriteVerificationLayer.get_instance()

    def test_no_invalid_aggregates_on_clean_model(self):
        from inventory.models import Product
        issues = self.verifier.verify_no_invalid_aggregates(Product)
        self.assertEqual(len(issues), 0)

    def test_no_broken_refs_on_clean_model(self):
        from inventory.models import Product
        broken = self.verifier.verify_no_broken_refs(Product)
        self.assertEqual(len(broken), 0)

    def test_no_orphans_on_clean_model(self):
        from inventory.models import Product
        orphans = self.verifier.verify_no_orphans(Product)
        self.assertEqual(orphans, 0)


class TestIntegrityEngineEndToEnd(TestCase):
    def setUp(self):
        self.engine = IntegrityEngine.get_instance()
        self.engine.configure()
        self.engine.enable()
        self.freeze = SystemFreezeKillSwitch.get_instance()
        if self.freeze.is_frozen():
            self.freeze.unfreeze("test")
        self.ledger = ImmutableIntegrityLedger.get_instance()
        self.ledger.clear()
        self.detector = RealTimeDriftDetector.get_instance()
        self.detector.capture_baseline()

    def test_full_enforce_prevent_invalid_write(self):
        from inventory.models import Product

        def bad_write():
            return "written"

        result = self.engine.enforce_operation(
            operation_fn=bad_write,
            model_class=Product,
            operation_type=OperationType.DELETE,
            data={"name": "x"},
            verify_after=False,
        )
        self.assertFalse(result["success"])
        self.assertIn("blocked", result.get("error", "").lower())

    def test_full_enforce_allows_clean_write(self):
        def clean_write():
            return 42

        from inventory.models import Product
        result = self.engine.enforce_operation(
            operation_fn=clean_write,
            model_class=Product,
            operation_type=OperationType.UPDATE,
            data={"name": "test_product"},
            verify_after=False,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 42)

    def test_engine_drift_detection(self):
        drift = self.detector.detect_drift()
        self.assertIsNotNone(drift)

    def test_ledger_has_events_after_operations(self):
        from inventory.models import Product

        self.engine.enforce_operation(
            operation_fn=lambda: 1,
            model_class=Product,
            operation_type=OperationType.UPDATE,
            data={"name": "p1"},
            verify_after=False,
        )
        self.engine.enforce_operation(
            operation_fn=lambda: 2,
            model_class=Product,
            operation_type=OperationType.UPDATE,
            data={"name": "p2"},
            verify_after=False,
        )
        self.assertGreaterEqual(self.ledger.count(), 2)

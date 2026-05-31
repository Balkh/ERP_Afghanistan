from django.test import TestCase
from core.runner.event_reliability import (
    RetryHandler, RetryPolicy, DeadLetterQueue, DeadLetterRecord,
    IdempotencyChecker,
)
from core.runner.concurrency import (
    AtomicCounter, ThreadSafeEventBusProxy, thread_safe_singleton,
)
from core.runner.integrity_ext import (
    RuntimeConsistencyValidator, FinancialIntegrityValidator,
    RuntimeConsistencyResult, FinancialIntegrityResult,
)
from core.runner.accounting_harden import (
    DailyTrialBalanceValidator, LedgerDriftMonitor, StrictDoubleEntryEnforcer,
    TrialBalanceReport, LedgerDriftRecord,
)
from core.runner.self_heal_ext import (
    RemediationOrchestrator, ReplayBasedCorrector, StructuredRemediation,
    RemediationStrategy,
)
from core.runner.failure_isolation import (
    ModuleCircuitBreaker, CascadingFailurePreventer, CircuitState,
)
from core.runner.hardened_engine import HardenedCRunnerEngine
from core.runner.workload_generator import BusinessEvent
from core.runner.models import FailureCategory
from core.runner.modules import CModuleID


# =============================================================================
# Concurrency Hardening
# =============================================================================

class TestAtomicCounter(TestCase):

    def test_initial_value(self):
        c = AtomicCounter(5)
        self.assertEqual(c.value, 5)

    def test_increment(self):
        c = AtomicCounter()
        c.increment()
        self.assertEqual(c.value, 1)

    def test_increment_by_delta(self):
        c = AtomicCounter()
        c.increment(5)
        self.assertEqual(c.value, 5)

    def test_decrement(self):
        c = AtomicCounter(10)
        c.decrement(3)
        self.assertEqual(c.value, 7)

    def test_reset(self):
        c = AtomicCounter(100)
        c.reset(0)
        self.assertEqual(c.value, 0)

    def test_consecutive_increments(self):
        c = AtomicCounter()
        for _ in range(10):
            c.increment()
        self.assertEqual(c.value, 10)


class TestThreadSafeEventBusProxy(TestCase):

    def test_proxy_creation(self):
        proxy = ThreadSafeEventBusProxy(None)
        self.assertIsNotNone(proxy)

    def test_publish_returns_id(self):
        class FakeBus:
            def publish(self, *a, **kw):
                return "test-id"
        proxy = ThreadSafeEventBusProxy(FakeBus())
        result = proxy.publish("test", {})
        self.assertEqual(result, "test-id")

    def test_subscribe_no_error(self):
        class FakeBus:
            def subscribe(self, *a, **kw):
                pass
        proxy = ThreadSafeEventBusProxy(FakeBus())
        proxy.subscribe("test", lambda e: None)

    def test_process_next_empty(self):
        class FakeBus:
            def process_next(self):
                return None
        proxy = ThreadSafeEventBusProxy(FakeBus())
        self.assertIsNone(proxy.process_next())

    def test_clear_no_error(self):
        class FakeBus:
            def clear(self):
                pass
        proxy = ThreadSafeEventBusProxy(FakeBus())
        proxy.clear()


# =============================================================================
# Event Reliability
# =============================================================================

class TestRetryPolicy(TestCase):

    def test_defaults(self):
        p = RetryPolicy()
        self.assertEqual(p.max_attempts, 3)
        self.assertEqual(p.base_delay_seconds, 0.1)

    def test_custom(self):
        p = RetryPolicy(max_attempts=5, backoff_factor=3.0)
        self.assertEqual(p.max_attempts, 5)
        self.assertEqual(p.backoff_factor, 3.0)


class TestRetryHandler(TestCase):

    def test_success_first_attempt(self):
        handler = RetryHandler()
        event = BusinessEvent(CModuleID.C5_SALES, "test", {})
        calls = []
        def executor(e):
            calls.append(1)
            return True
        result = handler.execute(event, executor)
        self.assertTrue(result)
        self.assertEqual(len(calls), 1)

    def test_failure_all_attempts(self):
        handler = RetryHandler(RetryPolicy(max_attempts=3, base_delay_seconds=0.01))
        event = BusinessEvent(CModuleID.C5_SALES, "fail", {})
        calls = []
        def executor(e):
            calls.append(1)
            return False
        result = handler.execute(event, executor)
        self.assertFalse(result)
        self.assertEqual(len(calls), 3)

    def test_success_on_retry(self):
        handler = RetryHandler(RetryPolicy(max_attempts=3, base_delay_seconds=0.01))
        event = BusinessEvent(CModuleID.C5_SALES, "retry", {})
        attempt_count = 0
        def executor(e):
            nonlocal attempt_count
            attempt_count += 1
            return attempt_count >= 2
        result = handler.execute(event, executor)
        self.assertTrue(result)

    def test_retry_count_tracks(self):
        handler = RetryHandler(RetryPolicy(max_attempts=2, base_delay_seconds=0.01))
        event = BusinessEvent(CModuleID.C5_SALES, "count", {})
        handler.execute(event, lambda e: False)
        self.assertEqual(handler.retry_count, 1)


class TestDeadLetterQueue(TestCase):

    def test_enqueue_and_size(self):
        dlq = DeadLetterQueue(max_size=100)
        dlq.enqueue(DeadLetterRecord(
            event=BusinessEvent(CModuleID.C5_SALES, "test", {}),
            error="test error", attempts=1, timestamp="now",
        ))
        self.assertEqual(dlq.size, 1)

    def test_peek_returns_records(self):
        dlq = DeadLetterQueue()
        dlq.enqueue(DeadLetterRecord(
            event=BusinessEvent(CModuleID.C5_SALES, "t", {}),
            error="e", attempts=1, timestamp="n",
        ))
        records = dlq.peek(1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].error, "e")

    def test_clear(self):
        dlq = DeadLetterQueue()
        dlq.enqueue(DeadLetterRecord(
            event=BusinessEvent(CModuleID.C5_SALES, "t", {}),
            error="e", attempts=1, timestamp="n",
        ))
        dlq.clear()
        self.assertEqual(dlq.size, 0)

    def test_replay_all_success(self):
        dlq = DeadLetterQueue()
        for i in range(3):
            dlq.enqueue(DeadLetterRecord(
                event=BusinessEvent(CModuleID.C5_SALES, f"t{i}", {}),
                error="e", attempts=1, timestamp="n",
            ))
        replayed = dlq.replay(lambda r: True)
        self.assertEqual(replayed, 3)
        self.assertEqual(dlq.size, 0)

    def test_replay_partial_failure(self):
        dlq = DeadLetterQueue()
        dlq.enqueue(DeadLetterRecord(
            event=BusinessEvent(CModuleID.C5_SALES, "ok", {}),
            error="e", attempts=1, timestamp="n",
        ))
        dlq.enqueue(DeadLetterRecord(
            event=BusinessEvent(CModuleID.C5_SALES, "fail", {}),
            error="e", attempts=1, timestamp="n",
        ))
        replayed = dlq.replay(lambda r: r.event.event_type == "ok")
        self.assertEqual(replayed, 1)
        self.assertEqual(dlq.size, 1)


class TestIdempotencyChecker(TestCase):

    def test_duplicate_detection(self):
        checker = IdempotencyChecker()
        event = BusinessEvent(CModuleID.C5_SALES, "create_sale", {"customer_id": 1})
        self.assertFalse(checker.is_duplicate(event))
        checker.mark_seen(event)
        self.assertTrue(checker.is_duplicate(event))

    def test_different_events_not_duplicates(self):
        checker = IdempotencyChecker()
        e1 = BusinessEvent(CModuleID.C5_SALES, "create_sale", {"customer_id": 1})
        e2 = BusinessEvent(CModuleID.C5_SALES, "create_sale", {"customer_id": 2})
        checker.mark_seen(e1)
        self.assertFalse(checker.is_duplicate(e2))

    def test_clear_resets(self):
        checker = IdempotencyChecker()
        event = BusinessEvent(CModuleID.C5_SALES, "test", {})
        checker.mark_seen(event)
        checker.clear()
        self.assertFalse(checker.is_duplicate(event))


# =============================================================================
# Integrity Extensions
# =============================================================================

class TestRuntimeConsistencyResult(TestCase):

    def test_create(self):
        r = RuntimeConsistencyResult(module="test", check="fk", passed=True, detail="ok")
        self.assertTrue(r.passed)
        self.assertEqual(r.check, "fk")


class TestFinancialIntegrityResult(TestCase):

    def test_create(self):
        r = FinancialIntegrityResult(check="debits", passed=False, detail="err")
        self.assertFalse(r.passed)
        self.assertEqual(r.imbalance, "0.00")


# =============================================================================
# Accounting Hardening
# =============================================================================

class TestTrialBalanceReport(TestCase):

    def test_defaults(self):
        r = TrialBalanceReport(day=1)
        self.assertEqual(r.day, 1)
        self.assertTrue(r.balanced)
        self.assertEqual(len(r.entries), 0)

    def test_with_entries(self):
        from core.runner.accounting_harden import TrialBalanceEntry
        r = TrialBalanceReport(day=5)
        r.entries.append(TrialBalanceEntry("1000", "Cash", 100.0, 0.0, 100.0))
        r.total_debits = 100.0
        r.total_credits = 100.0
        self.assertEqual(len(r.entries), 1)
        self.assertEqual(r.total_debits, 100.0)


class TestLedgerDriftRecord(TestCase):

    def test_create(self):
        r = LedgerDriftRecord(drift_type="imbalance", module="c2", detail="drift")
        self.assertEqual(r.drift_type, "imbalance")
        self.assertEqual(r.severity, "medium")

    def test_critical_severity(self):
        r = LedgerDriftRecord(drift_type="error", module="c2", detail="", severity="critical")
        self.assertEqual(r.severity, "critical")


class TestStrictDoubleEntryEnforcer(TestCase):

    def test_enforce_returns_dict(self):
        enforcer = StrictDoubleEntryEnforcer()
        result = enforcer.enforce()
        self.assertIn("enforced", result)
        self.assertIn("balanced", result)


# =============================================================================
# Self-Healing Extensions
# =============================================================================

class TestRemediationStrategy(TestCase):

    def test_all_strategies_present(self):
        self.assertIn(RemediationStrategy.RETRY, RemediationStrategy)
        self.assertIn(RemediationStrategy.ROLLBACK, RemediationStrategy)
        self.assertIn(RemediationStrategy.RECONCILE, RemediationStrategy)
        self.assertIn(RemediationStrategy.SKIP, RemediationStrategy)
        self.assertIn(RemediationStrategy.ISOLATE, RemediationStrategy)
        self.assertIn(RemediationStrategy.HALT, RemediationStrategy)


class TestRemediationOrchestrator(TestCase):

    def setUp(self):
        self.orch = RemediationOrchestrator()

    def test_remediate_returns_action(self):
        from core.runner.models import FailureCategory
        action = self.orch.remediate(
            "c5_sales", FailureCategory.TRANSACTION_FAILURE,
            "timeout", lambda: True,
        )
        self.assertIsNotNone(action)
        self.assertTrue(action.success)

    def test_remediate_tracks_history(self):
        from core.runner.models import FailureCategory
        self.orch.remediate("c2", FailureCategory.LEDGER_IMBALANCE, "drift", lambda: True)
        self.assertEqual(len(self.orch._history), 1)

    def test_report_returns_stats(self):
        from core.runner.models import FailureCategory
        self.orch.remediate("c5", FailureCategory.TRANSACTION_FAILURE, "err", lambda: True)
        report = self.orch.report()
        self.assertIn("total_remediations", report)
        self.assertEqual(report["total_remediations"], 1)

    def test_escalation_to_isolate(self):
        from core.runner.models import FailureCategory
        for _ in range(3):
            self.orch.remediate("c5", FailureCategory.TRANSACTION_FAILURE, "err", lambda: False)
        report = self.orch.report()
        self.assertGreaterEqual(report["total_remediations"], 3)

    def test_escalation_to_halt(self):
        from core.runner.models import FailureCategory
        for _ in range(5):
            self.orch.remediate("c5", FailureCategory.TRANSACTION_FAILURE, "err", lambda: False)
        report = self.orch.report()
        self.assertIn("HALT", report["by_strategy"])


class TestReplayBasedCorrector(TestCase):

    def setUp(self):
        self.corrector = ReplayBasedCorrector()

    def test_initial_state(self):
        self.assertEqual(self.corrector.total_corrections, 0)

    def test_correct_from_replay_with_empty_buffer(self):
        class EmptyBuffer:
            def get_sequence(self, *a, **kw):
                return []
        count = self.corrector.correct_from_replay(EmptyBuffer(), 1, lambda e: True)
        self.assertEqual(count, 0)

    def test_correct_from_replay_with_events(self):
        class FakeBuffer:
            def get_sequence(self, start, end):
                return [{"event_type": "test", "payload": {}}]
        count = self.corrector.correct_from_replay(FakeBuffer(), 1, lambda e: True)
        self.assertEqual(count, 1)

    def test_successful_corrections_count(self):
        class FakeBuffer:
            def get_sequence(self, start, end):
                return [{"event_type": "ok"}, {"event_type": "fail"}]
        self.corrector.correct_from_replay(FakeBuffer(), 1, lambda e: e["event_type"] == "ok")
        self.assertEqual(self.corrector.successful_corrections, 1)


# =============================================================================
# Failure Isolation
# =============================================================================

class TestCircuitState(TestCase):

    def test_all_states(self):
        self.assertIn(CircuitState.CLOSED, CircuitState)
        self.assertIn(CircuitState.OPEN, CircuitState)
        self.assertIn(CircuitState.HALF_OPEN, CircuitState)


class TestModuleCircuitBreaker(TestCase):

    def setUp(self):
        self.breaker = ModuleCircuitBreaker("test_module", failure_threshold=2)

    def test_initial_state_closed(self):
        self.assertEqual(self.breaker.state_name, "CLOSED")

    def test_allowed_by_default(self):
        self.assertTrue(self.breaker.is_allowed)

    def test_opens_after_threshold(self):
        self.breaker.record_failure("err1")
        self.breaker.record_failure("err2")
        self.assertEqual(self.breaker.state_name, "OPEN")
        self.assertFalse(self.breaker.is_allowed)

    def test_below_threshold_stays_closed(self):
        self.breaker.record_failure("err1")
        self.assertEqual(self.breaker.state_name, "CLOSED")
        self.assertTrue(self.breaker.is_allowed)

    def test_record_success_after_failure(self):
        self.breaker.record_failure("err")
        self.breaker.record_success()
        self.assertEqual(self.breaker.failure_count, 0)

    def test_reset(self):
        self.breaker.record_failure("err1")
        self.breaker.record_failure("err2")
        self.breaker.reset()
        self.assertEqual(self.breaker.state_name, "CLOSED")
        self.assertEqual(self.breaker.failure_count, 0)


class TestCascadingFailurePreventer(TestCase):

    def setUp(self):
        self.preventer = CascadingFailurePreventer()

    def test_register_module(self):
        self.preventer.register_module("c5_sales", ["c6_inventory", "c2_accounting"])
        status = self.preventer.get_status()
        self.assertIn("c5_sales", status["breakers"])

    def test_module_allowed_by_default(self):
        self.preventer.register_module("c5_sales")
        self.assertTrue(self.preventer.is_module_allowed("c5_sales"))

    def test_unregistered_module_allowed(self):
        self.assertTrue(self.preventer.is_module_allowed("unknown"))

    def test_blocked_after_failures(self):
        self.preventer.register_module("c5_sales", [])
        for _ in range(3):
            self.preventer.record_failure("c5_sales", "err")
        self.assertFalse(self.preventer.is_module_allowed("c5_sales"))

    def test_cascade_to_dependents(self):
        self.preventer.register_module("c6_inventory", [])
        self.preventer.register_module("c5_sales", ["c6_inventory"])
        self.preventer.record_failure("c6_inventory", "err")
        self.preventer.record_failure("c6_inventory", "err")
        self.preventer.record_failure("c6_inventory", "err")
        # c6 is blocked
        self.assertFalse(self.preventer.is_module_allowed("c6_inventory"))

    def test_get_blocked_modules(self):
        self.preventer.register_module("c5_sales", [])
        for _ in range(3):
            self.preventer.record_failure("c5_sales", "err")
        blocked = self.preventer.get_blocked_modules()
        self.assertIn("c5_sales", blocked)

    def test_reset_module(self):
        self.preventer.register_module("c5_sales", [])
        for _ in range(3):
            self.preventer.record_failure("c5_sales", "err")
        self.preventer.reset_module("c5_sales")
        self.assertTrue(self.preventer.is_module_allowed("c5_sales"))

    def test_reset_all(self):
        self.preventer.register_module("c5_sales", [])
        self.preventer.register_module("c4_procurement", [])
        for _ in range(3):
            self.preventer.record_failure("c5_sales", "err")
        self.preventer.reset_all()
        self.assertTrue(self.preventer.is_module_allowed("c5_sales"))
        self.assertTrue(self.preventer.is_module_allowed("c4_procurement"))

    def test_quarantine_tracking(self):
        self.preventer.register_module("c5_sales", [])
        for _ in range(3):
            self.preventer.record_failure("c5_sales", "err")
        status = self.preventer.get_status()
        self.assertIn("c5_sales", status["quarantine"])

    def test_record_success_removes_from_quarantine(self):
        self.preventer.register_module("c5_sales", [])
        for _ in range(3):
            self.preventer.record_failure("c5_sales", "err")
        self.preventer.record_success("c5_sales")
        status = self.preventer.get_status()
        self.assertNotIn("c5_sales", status["quarantine"])


# =============================================================================
# Hardened Engine
# =============================================================================

class TestHardenedCRunnerEngine(TestCase):

    def setUp(self):
        self.engine = HardenedCRunnerEngine()

    def test_initializes_all_components(self):
        self.assertIsNotNone(self.engine.retry_handler)
        self.assertIsNotNone(self.engine.dead_letter_queue)
        self.assertIsNotNone(self.engine.idempotency_checker)
        self.assertIsNotNone(self.engine.runtime_validator)
        self.assertIsNotNone(self.engine.financial_validator)
        self.assertIsNotNone(self.engine.trial_balance)
        self.assertIsNotNone(self.engine.drift_monitor)
        self.assertIsNotNone(self.engine.double_entry_enforcer)
        self.assertIsNotNone(self.engine.remediation_orch)
        self.assertIsNotNone(self.engine.replay_corrector)
        self.assertIsNotNone(self.engine.failure_preventer)

    def test_register_modules(self):
        self.engine.register_modules()
        status = self.engine.failure_preventer.get_status()
        self.assertGreater(len(status["breakers"]), 0)

    def test_register_modules_has_c5_sales(self):
        self.engine.register_modules()
        status = self.engine.failure_preventer.get_status()
        self.assertIn("c5_sales", status["breakers"])

    def test_register_modules_has_c2_accounting(self):
        self.engine.register_modules()
        status = self.engine.failure_preventer.get_status()
        self.assertIn("c2_accounting", status["breakers"])

    def test_get_hardening_status_returns_all_keys(self):
        status = self.engine.get_hardening_status()
        self.assertIn("dead_letter_queue_size", status)
        self.assertIn("retry_log_count", status)
        self.assertIn("idempotency_cache", status)
        self.assertIn("remediation", status)
        self.assertIn("failure_isolation", status)
        self.assertIn("trial_balance_enabled", status)
        self.assertIn("drift_monitor_enabled", status)
        self.assertIn("double_entry_enforcer", status)

    def test_hardening_is_inherited_from_crunner(self):
        self.assertTrue(hasattr(self.engine, 'validate_architecture'))
        self.assertTrue(hasattr(self.engine, 'configure'))
        self.assertTrue(hasattr(self.engine, 'get_report'))

    def test_validation_layer_returns_all_fields(self):
        result = self.engine.run_validation_layer(1)
        self.assertIn("runtime", result)
        self.assertIn("financial", result)
        self.assertIn("trial_balance", result)
        self.assertIn("drift", result)
        self.assertIn("double_entry", result)
        self.assertIn("all_passed", result)

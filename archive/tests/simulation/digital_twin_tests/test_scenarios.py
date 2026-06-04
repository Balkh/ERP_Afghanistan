import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from simulation.digital_twin.scenarios.base import BaseScenario
from simulation.digital_twin.scenarios.core_business import (
    InvoicePostingScenario,
    TaxMismatchScenario,
    DiscountMiscalculationScenario,
    DuplicateJournalEntryScenario,
    PartialPaymentFailureScenario,
    FIFOValidationScenario,
    NegativeStockAttemptScenario,
    BatchCorruptionScenario,
    ConcurrentStockDeductionScenario,
    FullReturnScenario,
    PartialReturnScenario,
    ReturnAfterPeriodLockScenario,
    TaxRevenueReversalMismatchScenario,
    DuplicateReturnProcessingScenario,
    InventoryReCreditFailureScenario,
)
from simulation.digital_twin.scenarios.failure_modes import (
    ConcurrencyStormScenario,
    PartialCascadeFailureScenario,
    SilentFailureInjectionScenario,
    DataCorruptionInjectionScenario,
    ReplayDivergenceScenario,
    QueueBacklogPressureScenario,
)
from simulation.digital_twin.scenarios.time_scenarios import (
    SLAViolationScenario,
    WorkflowStarvationScenario,
    ReconciliationDriftScenario,
    PaymentTimeoutScenario,
    QueueOverloadScenario,
)
from simulation.digital_twin.scenarios.external_scenarios import (
    BankingTimeoutScenario,
    PaymentSplitScenario,
    SupplierDelayScenario,
    CreditDowntimeScenario,
    TaxDowntimeScenario,
)


def _make_engine():
    engine = MagicMock()
    engine.event_bus = MagicMock()
    engine.clock.now.return_value = datetime(2024, 1, 1, 0, 0, 0)
    engine.metrics.snapshot.return_value = {"ticks_executed": 5}
    engine.sla_monitor = MagicMock()
    engine.sla_monitor.get_violations.return_value = []
    return engine


class TestBaseScenario(unittest.TestCase):

    def test_abstract_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            BaseScenario("test", "generic")

    def test_abstract_methods_raise_notimplemented(self):
        class IncompleteScenario(BaseScenario):
            def setup(self, engine): pass
            def execute(self, engine): return {}

        with self.assertRaises(TypeError):
            IncompleteScenario("inc", "test")

    def test_get_name_and_type(self):
        class ConcreteScenario(BaseScenario):
            def setup(self, engine): pass
            def execute(self, engine): return {"scenario": self._name, "ticks_executed": 0}
            def teardown(self, engine): return {}

        s = ConcreteScenario("test_scenario", "test_type", {"key": "val"})
        self.assertEqual(s.get_name(), "test_scenario")
        self.assertEqual(s.get_type(), "test_type")

    def test_verify_with_passing_matrix(self):
        class ConcreteScenario(BaseScenario):
            def setup(self, engine): pass
            def execute(self, engine): return {"scenario": self._name, "ticks_executed": 0}
            def teardown(self, engine): return {}

        s = ConcreteScenario("verify_test", "test")
        s._collected_state = {"key": "val"}
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": ["check1"], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["passed"])
        self.assertEqual(result["checks"], ["check1"])
        self.assertEqual(result["violations"], [])

    def test_verify_with_violations(self):
        class ConcreteScenario(BaseScenario):
            def setup(self, engine): pass
            def execute(self, engine): return {"scenario": self._name, "ticks_executed": 0}
            def teardown(self, engine): return {}

        s = ConcreteScenario("verify_fail", "test")
        s._collected_state = {"key": "val"}
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": ["c1"], "violations": ["v1"]}
        result = s.verify(matrix)
        self.assertFalse(result["passed"])

    def test_verify_with_exception_safe(self):
        class ConcreteScenario(BaseScenario):
            def setup(self, engine): pass
            def execute(self, engine): return {"scenario": self._name, "ticks_executed": 0}
            def teardown(self, engine): return {}

        s = ConcreteScenario("verify_exc", "test")
        matrix = MagicMock()
        matrix.validate_all.side_effect = RuntimeError("fail")
        result = s.verify(matrix)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["violations"]), 1)


class TestInvoicePostingScenario(unittest.TestCase):

    def test_execute_publishes_event_and_runs_ticks(self):
        engine = _make_engine()
        s = InvoicePostingScenario()
        result = s.execute(engine)
        self.assertEqual(result["scenario"], "invoice_posting")
        self.assertEqual(result["ticks_executed"], 5)
        engine.event_bus.publish.assert_called_with(
            "sales_triggered",
            engine.clock.now(),
            {"scenario": "invoice_posting", "type": "invoice"},
        )
        self.assertEqual(engine.execute_tick.call_count, 5)

    def test_teardown_collects_state(self):
        engine = _make_engine()
        engine.event_bus.history = []
        s = InvoicePostingScenario()
        s._events_published = 1
        result = s.teardown(engine)
        self.assertEqual(result["expected_count"], 1)

    def test_execute_exception_safe(self):
        engine = _make_engine()
        engine.execute_tick.side_effect = RuntimeError("boom")
        s = InvoicePostingScenario()
        result = s.execute(engine)
        self.assertTrue(result.get("error"))


class TestTaxMismatchScenario(unittest.TestCase):

    def test_execute_injects_mismatch(self):
        engine = _make_engine()
        s = TaxMismatchScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 5)

    def test_verify_reports_mismatch(self):
        engine = _make_engine()
        s = TaxMismatchScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["mismatch_detected"])


class TestDuplicateJournalEntryScenario(unittest.TestCase):

    def test_execute_publishes_duplicate(self):
        engine = _make_engine()
        s = DuplicateJournalEntryScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 5)
        self.assertEqual(engine.event_bus.publish.call_count, 2)

    def test_verify_block_activated(self):
        engine = _make_engine()
        s = DuplicateJournalEntryScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["block_activated"])


class TestFIFOValidationScenario(unittest.TestCase):

    def test_execute_sequential_flow(self):
        engine = _make_engine()
        s = FIFOValidationScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 10)
        self.assertEqual(engine.event_bus.publish.call_count, 4)
        self.assertEqual(engine.execute_tick.call_count, 10)

    def test_teardown_reports_completion(self):
        engine = _make_engine()
        s = FIFOValidationScenario()
        s.execute(engine)
        result = s.teardown(engine)
        self.assertTrue(result["fifo_flow_completed"])


class TestConcurrentStockDeductionScenario(unittest.TestCase):

    def test_execute_ten_events(self):
        engine = _make_engine()
        s = ConcurrentStockDeductionScenario()
        result = s.execute(engine)
        self.assertEqual(result["concurrent_events"], 10)
        self.assertEqual(result["ticks_executed"], 5)
        self.assertEqual(engine.event_bus.publish.call_count, 10)

    def test_teardown_checks_consistency(self):
        engine = _make_engine()
        engine.event_bus.history = []
        s = ConcurrentStockDeductionScenario()
        s.execute(engine)
        result = s.teardown(engine)
        self.assertIn("consistency", result)
        self.assertEqual(result["expected"], 10)


class TestFullReturnScenario(unittest.TestCase):

    def test_execute_return_flow(self):
        engine = _make_engine()
        s = FullReturnScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 8)
        engine.event_bus.publish.assert_called_with(
            "return_triggered",
            engine.clock.now(),
            {"scenario": "full_return", "invoice_ref": "INV-001", "type": "full", "reason": "damaged"},
        )

    def test_teardown_marks_complete(self):
        engine = _make_engine()
        s = FullReturnScenario()
        s.execute(engine)
        result = s.teardown(engine)
        self.assertTrue(result["return_completed"])


class TestConcurrencyStormScenario(unittest.TestCase):

    def test_execute_100_events(self):
        engine = _make_engine()
        s = ConcurrencyStormScenario()
        result = s.execute(engine)
        self.assertEqual(result["events_injected"], 100)
        self.assertEqual(result["ticks_executed"], 5)
        self.assertEqual(engine.event_bus.publish.call_count, 100)

    def test_teardown_measures_throughput(self):
        engine = _make_engine()
        engine.event_bus.history = []
        s = ConcurrencyStormScenario()
        s._event_count = 100
        result = s.teardown(engine)
        self.assertIn("throughput", result)
        self.assertIn("error_count", result)


class TestSLAViolationScenario(unittest.TestCase):

    def test_execute_tracks_violations(self):
        engine = _make_engine()
        engine.sla_monitor.start = MagicMock()
        engine.sla_monitor.stop = MagicMock(return_value=5)
        engine.sla_monitor.get_violations.return_value = [{"operation": "invoice_processing"}]
        s = SLAViolationScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 10)

    def test_teardown_reports_violations(self):
        engine = _make_engine()
        engine.sla_monitor = MagicMock()
        engine.sla_monitor.get_violations.return_value = [{"op": "test"}]
        s = SLAViolationScenario()
        s._violations = [{"operation": "invoice_processing", "elapsed": 5, "sla_ticks": 2}]
        result = s.teardown(engine)
        self.assertGreater(result["violations"], 0)


class TestWorkflowStarvationScenario(unittest.TestCase):

    def test_execute_delayed_workflow(self):
        engine = _make_engine()
        s = WorkflowStarvationScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 15)
        self.assertEqual(engine.event_bus.publish.call_count, 2)

    def test_verify_degradation(self):
        engine = _make_engine()
        s = WorkflowStarvationScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["degradation_detected"])


class TestBankingTimeoutScenario(unittest.TestCase):

    def test_execute_timeout_flow(self):
        engine = _make_engine()
        s = BankingTimeoutScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 10)
        engine.event_bus.publish.assert_called_with(
            "banking_api_call",
            engine.clock.now(),
            {"scenario": "banking_timeout", "operation": "payment", "timeout": True},
        )

    def test_verify_retry_and_compensation(self):
        engine = _make_engine()
        s = BankingTimeoutScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["retry_triggered"])
        self.assertTrue(result["compensation_triggered"])


class TestExternalScenarios(unittest.TestCase):

    def test_payment_split_verify(self):
        engine = _make_engine()
        s = PaymentSplitScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["split_handled"])

    def test_supplier_delay_verify(self):
        engine = _make_engine()
        s = SupplierDelayScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["pending_state_detected"])

    def test_credit_downtime_verify(self):
        engine = _make_engine()
        s = CreditDowntimeScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["fallback_activated"])

    def test_tax_downtime_verify(self):
        engine = _make_engine()
        s = TaxDowntimeScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["deferred_posting"])


class TestInventoryScenarios(unittest.TestCase):

    def test_negative_stock_verify(self):
        engine = _make_engine()
        s = NegativeStockAttemptScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["negative_stock_blocked"])

    def test_batch_corruption_verify(self):
        engine = _make_engine()
        s = BatchCorruptionScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["corruption_detected"])


class TestReturnScenarios(unittest.TestCase):

    def test_partial_return_verify(self):
        engine = _make_engine()
        s = PartialReturnScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["prorated_reversal"])

    def test_return_after_lock_verify(self):
        engine = _make_engine()
        s = ReturnAfterPeriodLockScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["rejected"])

    def test_tax_reversal_mismatch_verify(self):
        engine = _make_engine()
        s = TaxRevenueReversalMismatchScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["mismatch_detected"])

    def test_duplicate_return_verify(self):
        engine = _make_engine()
        s = DuplicateReturnProcessingScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["duplicate_detected"])

    def test_inventory_recredit_failure_verify(self):
        engine = _make_engine()
        s = InventoryReCreditFailureScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["compensation_triggered"])


class TestFailureModesScenarios(unittest.TestCase):

    def test_partial_cascade_failure_execute(self):
        engine = _make_engine()
        s = PartialCascadeFailureScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 10)
        self.assertEqual(engine.event_bus.publish.call_count, 3)

    def test_partial_cascade_teardown(self):
        engine = _make_engine()
        s = PartialCascadeFailureScenario()
        s._cascade_steps = ["inventory_fail", "accounting_fail", "payment_fail"]
        result = s.teardown(engine)
        self.assertEqual(result["steps_executed"], 3)

    def test_silent_failure_execute(self):
        engine = _make_engine()
        s = SilentFailureInjectionScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 5)

    def test_data_corruption_execute(self):
        engine = _make_engine()
        s = DataCorruptionInjectionScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 5)

    def test_replay_divergence_execute(self):
        engine = _make_engine()
        s = ReplayDivergenceScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 15)

    def test_queue_backlog_execute(self):
        engine = _make_engine()
        s = QueueBacklogPressureScenario()
        result = s.execute(engine)
        self.assertEqual(result["events_injected"], 200)
        self.assertEqual(engine.event_bus.publish.call_count, 200)


class TestTimeScenarios(unittest.TestCase):

    def test_reconciliation_drift_verify(self):
        engine = _make_engine()
        s = ReconciliationDriftScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["drift_alert"])

    def test_payment_timeout_verify(self):
        engine = _make_engine()
        s = PaymentTimeoutScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["compensation_triggered"])

    def test_queue_overload_verify(self):
        engine = _make_engine()
        s = QueueOverloadScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["starvation_detected"])


class TestScenarioExceptionSafety(unittest.TestCase):

    def _check_scenario_exception_safe(self, scenario_cls, engine_attr=None):
        engine = _make_engine()
        if engine_attr:
            setattr(engine, engine_attr, None)
        s = scenario_cls()
        try:
            s.setup(engine)
            result = s.execute(engine)
            self.assertIn("scenario", result)
            s.teardown(engine)
        except Exception:
            self.fail(f"{scenario_cls.__name__} raised unexpected exception")

    def test_all_scenarios_exception_safe(self):
        classes = [
            InvoicePostingScenario, TaxMismatchScenario,
            DiscountMiscalculationScenario, DuplicateJournalEntryScenario,
            PartialPaymentFailureScenario, FIFOValidationScenario,
            NegativeStockAttemptScenario, BatchCorruptionScenario,
            ConcurrentStockDeductionScenario, FullReturnScenario,
            PartialReturnScenario, ReturnAfterPeriodLockScenario,
            TaxRevenueReversalMismatchScenario, DuplicateReturnProcessingScenario,
            InventoryReCreditFailureScenario,
            ConcurrencyStormScenario, PartialCascadeFailureScenario,
            SilentFailureInjectionScenario, DataCorruptionInjectionScenario,
            ReplayDivergenceScenario, QueueBacklogPressureScenario,
            SLAViolationScenario, WorkflowStarvationScenario,
            ReconciliationDriftScenario, PaymentTimeoutScenario,
            QueueOverloadScenario,
            BankingTimeoutScenario, PaymentSplitScenario,
            SupplierDelayScenario, CreditDowntimeScenario,
            TaxDowntimeScenario,
        ]
        for cls in classes:
            with self.subTest(cls.__name__):
                self._check_scenario_exception_safe(cls)


class TestSetupAndTeardownCycle(unittest.TestCase):

    def test_full_cycle_resets_state(self):
        engine = _make_engine()
        s = InvoicePostingScenario()
        s.setup(engine)
        self.assertEqual(s._events_published, 0)
        s.execute(engine)
        self.assertGreater(s._events_published, 0)
        s.setup(engine)
        self.assertEqual(s._events_published, 0)

    def test_teardown_after_setup_no_execute(self):
        engine = _make_engine()
        s = DiscountMiscalculationScenario()
        s.setup(engine)
        result = s.teardown(engine)
        self.assertIn("mismatch_detected", result)


class TestPartialPaymentFailureScenario(unittest.TestCase):

    def test_verify_compensation(self):
        engine = _make_engine()
        s = PartialPaymentFailureScenario()
        s.execute(engine)
        s.teardown(engine)
        matrix = MagicMock()
        matrix.validate_all.return_value = {"checks": [], "violations": []}
        result = s.verify(matrix)
        self.assertTrue(result["compensation_triggered"])


class TestTaxDowntimeScenario(unittest.TestCase):

    def test_execute_defers_posting(self):
        engine = _make_engine()
        s = TaxDowntimeScenario()
        result = s.execute(engine)
        self.assertEqual(result["ticks_executed"], 10)
        calls = [c[0][0] for c in engine.event_bus.publish.call_args_list]
        self.assertIn("tax_api_call", calls)
        self.assertIn("tax_deferred_posting", calls)


if __name__ == "__main__":
    unittest.main()

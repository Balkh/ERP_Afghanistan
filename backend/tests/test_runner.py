from django.test import TestCase
from core.runner.modules import (
    CModuleID, MODULE_REGISTRY, validate_module_dag, get_execution_order,
)
from core.runner.models import (
    DayState, DayResult, RunState, RunStatus, WorkloadConfig, FailureCategory,
)
from core.runner.workload_generator import generate_daily_events, BusinessEvent
from core.runner.validator import DailyValidator, CheckResult, ValidationReport
from core.runner.self_healer import SelfHealer, HealAction
from core.runner.snapshot_manager import SnapshotManager
from core.runner.engine import CRunnerEngine
from datetime import date
import json


class TestModuleDefinitions(TestCase):

    def test_all_10_modules_registered(self):
        self.assertEqual(len(MODULE_REGISTRY), 10)

    def test_module_labels_present(self):
        for mid, mod in MODULE_REGISTRY.items():
            self.assertTrue(mod.label)
            self.assertTrue(mod.django_app)
            self.assertTrue(mod.description)

    def test_c9_depends_on_all(self):
        c9 = MODULE_REGISTRY[CModuleID.C9_FRONTEND]
        self.assertGreater(len(c9.requires), 5)

    def test_c10_depends_on_all(self):
        c10 = MODULE_REGISTRY[CModuleID.C10_BACKUP]
        self.assertGreater(len(c10.requires), 5)

    def test_dag_no_errors(self):
        errors = validate_module_dag()
        self.assertEqual(errors, [])

    def test_c1_has_no_dependencies(self):
        c1 = MODULE_REGISTRY[CModuleID.C1_COMPANY]
        self.assertEqual(c1.requires, [])

    def test_c6_requires_only_c1(self):
        c6 = MODULE_REGISTRY[CModuleID.C6_INVENTORY]
        self.assertIn(CModuleID.C1_COMPANY, c6.requires)

    def test_execution_order_is_topological(self):
        order = get_execution_order()
        positions = {mid: i for i, mid in enumerate(order)}
        for mid in order:
            mod = MODULE_REGISTRY[mid]
            for req in mod.requires:
                self.assertLess(
                    positions[req], positions[mid],
                    f"{mid.value} must come after {req.value}",
                )

    def test_execution_order_starts_with_c1(self):
        order = get_execution_order()
        self.assertEqual(order[0], CModuleID.C1_COMPANY)

    def test_execution_order_contains_all_10(self):
        order = get_execution_order()
        self.assertEqual(len(order), 10)

    def test_validate_architecture(self):
        engine = CRunnerEngine.get_instance()
        arch = engine.validate_architecture()
        self.assertTrue(arch["dag_valid"])
        self.assertEqual(arch["module_count"], 10)
        self.assertEqual(len(arch["execution_order"]), 10)


class TestCRunnerEngine(TestCase):

    def setUp(self):
        self.engine = CRunnerEngine.get_instance()

    def test_engine_is_singleton(self):
        e2 = CRunnerEngine.get_instance()
        self.assertIs(self.engine, e2)

    def test_default_config(self):
        self.assertEqual(self.engine.state.config.daily_sales_min, 3)

    def test_configure_sets_params(self):
        self.engine.configure(seed=99, daily_sales_max=20)
        self.assertEqual(self.engine.state.config.seed, 99)
        self.assertEqual(self.engine.state.config.daily_sales_max, 20)

    def test_configure_start_end(self):
        self.engine.configure(start_day=5, end_day=10)
        self.assertEqual(self.engine.state.start_day, 5)
        self.assertEqual(self.engine.state.end_day, 10)

    def test_initial_status_is_initializing(self):
        self.engine.state.status = RunStatus.INITIALIZING
        self.assertEqual(self.engine.state.status, RunStatus.INITIALIZING)

    def test_validate_architecture_returns_all_keys(self):
        arch = self.engine.validate_architecture()
        self.assertIn("dag_valid", arch)
        self.assertIn("execution_order", arch)
        self.assertIn("modules", arch)

    def test_get_report_before_run(self):
        report = self.engine.get_report()
        self.assertIn("run_id", report)
        self.assertIn("status", report)


class TestWorkloadGenerator(TestCase):

    def setUp(self):
        self.config = WorkloadConfig(seed=42)
        self.sim_date = date(2026, 1, 1)
        self.existing = {
            "customer_ids": [1, 2, 3],
            "product_ids": [10, 20, 30],
            "supplier_ids": [100, 200],
            "warehouse_ids": [1],
            "employee_ids": [1000],
        }

    def test_generates_events_for_day_1(self):
        events = generate_daily_events(1, self.sim_date, self.config, self.existing)
        self.assertGreater(len(events), 0)

    def test_includes_sales_events(self):
        events = generate_daily_events(1, self.sim_date, self.config, self.existing)
        sales = [e for e in events if e.module.value == "c5_sales"]
        self.assertGreater(len(sales), 0)

    def test_includes_purchase_events(self):
        events = generate_daily_events(1, self.sim_date, self.config, self.existing)
        purchases = [e for e in events if e.module.value == "c4_procurement"]
        self.assertGreater(len(purchases), 0)

    def test_deterministic_output(self):
        e1 = generate_daily_events(5, self.sim_date, self.config, self.existing)
        e2 = generate_daily_events(5, self.sim_date, self.config, self.existing)
        self.assertEqual(len(e1), len(e2))

    def test_different_seed_different_output(self):
        cfg2 = WorkloadConfig(seed=999)
        e1 = generate_daily_events(1, self.sim_date, self.config, self.existing)
        e2 = generate_daily_events(1, self.sim_date, cfg2, self.existing)
        self.assertNotEqual(len(e1), len(e2))

    def test_payroll_event_on_day_30(self):
        events = generate_daily_events(30, self.sim_date, self.config, self.existing)
        payroll = [e for e in events if e.event_type == "run_payroll"]
        self.assertEqual(len(payroll), 1)

    def test_month_end_close_on_day_30(self):
        events = generate_daily_events(30, self.sim_date, self.config, self.existing)
        close = [e for e in events if e.event_type == "month_end_close"]
        self.assertEqual(len(close), 1)

    def test_backup_event_on_day_7(self):
        events = generate_daily_events(7, self.sim_date, self.config, self.existing)
        backup = [e for e in events if e.event_type == "daily_snapshot"]
        self.assertEqual(len(backup), 1)

    def test_report_event_on_day_15(self):
        events = generate_daily_events(15, self.sim_date, self.config, self.existing)
        reports = [e for e in events if e.event_type == "generate_reports"]
        self.assertEqual(len(reports), 1)

    def test_events_have_priorities(self):
        events = generate_daily_events(1, self.sim_date, self.config, self.existing)
        for e in events:
            self.assertIn(e.priority, [1, 2, 3, 4, 5])

    def test_return_event_possible(self):
        events = generate_daily_events(1, self.sim_date, self.config, self.existing)
        returns = [e for e in events if e.event_type == "create_return"]
        self.assertGreaterEqual(len(returns), 0)

    def test_sale_items_have_required_fields(self):
        events = generate_daily_events(1, self.sim_date, self.config, self.existing)
        for e in events:
            if e.event_type == "create_sale":
                self.assertIn("customer_id", e.payload)
                self.assertIn("items", e.payload)

    def test_purchase_items_have_required_fields(self):
        events = generate_daily_events(1, self.sim_date, self.config, self.existing)
        for e in events:
            if e.event_type == "create_purchase":
                self.assertIn("supplier_id", e.payload)
                self.assertIn("items", e.payload)


class TestDailyValidator(TestCase):

    def setUp(self):
        self.validator = DailyValidator(day=1)

    def test_validation_report_has_all_passed(self):
        report = self.validator.run_all()
        self.assertIsInstance(report, ValidationReport)

    def test_check_result_to_dict(self):
        result = CheckResult("test_check", CModuleID.C2_ACCOUNTING, True, "OK")
        d = result.to_dict()
        self.assertEqual(d["check"], "test_check")
        self.assertEqual(d["passed"], True)

    def test_report_to_dict(self):
        report = ValidationReport(day=1)
        report.add(CheckResult("c1", CModuleID.C1_COMPANY, True))
        report.add(CheckResult("c2", CModuleID.C2_ACCOUNTING, False, "Failed", "high"))
        d = report.to_dict()
        self.assertEqual(d["day"], 1)
        self.assertEqual(d["total_checks"], 2)
        self.assertEqual(d["passed"], 1)

    def test_high_severity_failure_flags_all_passed(self):
        report = ValidationReport(day=1)
        report.add(CheckResult("fail", None, False, "Bad", "high"))
        self.assertFalse(report.all_passed)

    def test_low_severity_failure_does_not_flag(self):
        report = ValidationReport(day=1)
        report.add(CheckResult("fail", None, False, "Minor", "low"))
        self.assertTrue(report.all_passed)


class TestSelfHealer(TestCase):

    def setUp(self):
        self.healer = SelfHealer()

    def test_none_check_returns_none(self):
        action = self.healer.heal("test_module", None)
        self.assertIsNone(action)

    def test_passed_check_gets_classified(self):
        check = CheckResult("fk_integrity", None, False, "FK violation", "high")
        action = self.healer.heal("test_module", check)
        self.assertIsNotNone(action)

    def test_data_integrity_heals(self):
        check = CheckResult("fk_integrity", CModuleID.C6_INVENTORY, False, "Violation", "high")
        action = self.healer.heal("inventory", check)
        self.assertIsNotNone(action)

    def test_heal_ledger_imbalance(self):
        check = CheckResult("double_entry_balance", CModuleID.C2_ACCOUNTING, False, "Imbalance", "critical")
        action = self.healer.heal("accounting", check)
        self.assertIsNotNone(action)

    def test_heal_inventory_imbalance(self):
        check = CheckResult("inventory_non_negative", CModuleID.C6_INVENTORY, False, "Negative batch", "high")
        action = self.healer.heal("inventory", check)
        self.assertIsNotNone(action)

    def test_heal_tracks_actions(self):
        check = CheckResult("fk_test", None, False, "Test", "high")
        self.healer.heal("mod", check)
        self.assertEqual(len(self.healer.actions), 1)

    def test_classify_balance_check(self):
        check = CheckResult("balance_check", None, False)
        cat = self.healer._classify(check)
        self.assertEqual(cat, FailureCategory.LEDGER_IMBALANCE)

    def test_classify_inventory_check(self):
        check = CheckResult("inventory_check", None, False)
        cat = self.healer._classify(check)
        self.assertEqual(cat, FailureCategory.INVENTORY_IMBALANCE)

    def test_classify_fk_check(self):
        check = CheckResult("fk_integrity", None, False)
        cat = self.healer._classify(check)
        self.assertEqual(cat, FailureCategory.DATA_INTEGRITY)

    def test_heal_action_dataclass(self):
        action = HealAction(
            category=FailureCategory.DATA_INTEGRITY,
            strategy="retry",
            detail="Retried",
            success=True,
        )
        self.assertTrue(action.success)
        self.assertEqual(action.strategy, "retry")


class TestSnapshotManager(TestCase):

    def setUp(self):
        self.sm = SnapshotManager()

    def test_take_snapshot_returns_record(self):
        record = self.sm.take_snapshot(1, "Day_1")
        self.assertEqual(record.day, 1)
        self.assertEqual(record.label, "Day_1")

    def test_snapshot_has_checksum(self):
        record = self.sm.take_snapshot(5)
        self.assertTrue(len(record.checksum) > 0)

    def test_snapshot_has_row_counts(self):
        record = self.sm.take_snapshot(1)
        self.assertIsInstance(record.table_row_counts, dict)

    def test_get_snapshot_returns_none_for_missing(self):
        result = self.sm.get_snapshot(999)
        self.assertIsNone(result)

    def test_get_snapshot_returns_record(self):
        self.sm.take_snapshot(10, "test")
        record = self.sm.get_snapshot(10)
        self.assertIsNotNone(record)
        if record:
            self.assertEqual(record.day, 10)

    def test_list_snapshots(self):
        self.sm.take_snapshot(1)
        self.sm.take_snapshot(5)
        snapshots = self.sm.list_snapshots()
        self.assertIn(1, snapshots)
        self.assertIn(5, snapshots)

    def test_verify_snapshot_no_record(self):
        self.assertFalse(self.sm.verify_snapshot(999))


class TestDayState(TestCase):

    def test_defaults(self):
        ds = DayState(day=1, sim_date=date(2026, 1, 1))
        self.assertEqual(ds.day, 1)
        self.assertEqual(ds.events_dispatched, 0)
        self.assertEqual(ds.events_succeeded, 0)
        self.assertEqual(ds.events_failed, 0)

    def test_custom_values(self):
        ds = DayState(
            day=5,
            sim_date=date(2026, 1, 5),
            events_dispatched=10,
            events_succeeded=8,
            events_failed=2,
            result=DayResult.PASS,
        )
        self.assertEqual(ds.day, 5)
        self.assertEqual(ds.events_dispatched, 10)

    def test_to_dict_via_engine(self):
        engine = CRunnerEngine.get_instance()
        ds = DayState(day=1, sim_date=date(2026, 1, 1), result=DayResult.PASS)
        d = engine._day_result_to_str(ds)
        self.assertEqual(d["result"], "PASS")


class TestRunState(TestCase):

    def test_defaults(self):
        rs = RunState()
        self.assertEqual(rs.status, RunStatus.INITIALIZING)
        self.assertEqual(rs.start_day, 1)
        self.assertEqual(rs.end_day, 60)
        self.assertEqual(len(rs.days), 0)

    def test_config(self):
        rs = RunState(config=WorkloadConfig(seed=77))
        self.assertEqual(rs.config.seed, 77)

    def test_aggregation(self):
        rs = RunState(
            total_events_dispatched=100,
            total_events_succeeded=95,
            total_events_failed=5,
        )
        self.assertEqual(rs.total_events_dispatched, 100)


class TestWorkloadConfig(TestCase):

    def test_defaults(self):
        cfg = WorkloadConfig()
        self.assertEqual(cfg.daily_sales_min, 3)
        self.assertEqual(cfg.daily_sales_max, 15)
        self.assertEqual(cfg.seed, 42)
        self.assertEqual(cfg.payroll_day, 30)
        self.assertEqual(cfg.month_end_close_day, 30)

    def test_custom_values(self):
        cfg = WorkloadConfig(seed=123, daily_sales_max=5)
        self.assertEqual(cfg.seed, 123)
        self.assertEqual(cfg.daily_sales_max, 5)


class TestBusinessEvent(TestCase):

    def test_create_event(self):
        event = BusinessEvent(
            module=CModuleID.C5_SALES,
            event_type="create_sale",
            payload={"customer_id": 1},
        )
        self.assertEqual(event.module, CModuleID.C5_SALES)
        self.assertEqual(event.event_type, "create_sale")
        self.assertEqual(event.payload["customer_id"], 1)
        self.assertEqual(event.priority, 2)

    def test_custom_priority(self):
        event = BusinessEvent(
            module=CModuleID.C10_BACKUP,
            event_type="daily_snapshot",
            payload={},
            priority=5,
        )
        self.assertEqual(event.priority, 5)


class TestDayResultEnum(TestCase):

    def test_all_values_present(self):
        self.assertIn(DayResult.PASS, DayResult)
        self.assertIn(DayResult.PASS_WITH_SELF_HEAL, DayResult)
        self.assertIn(DayResult.FAIL_HALT, DayResult)
        self.assertIn(DayResult.FAIL_ISOLATE, DayResult)


class TestFailureCategory(TestCase):

    def test_all_categories(self):
        self.assertIn(FailureCategory.DATA_INTEGRITY, FailureCategory)
        self.assertIn(FailureCategory.LEDGER_IMBALANCE, FailureCategory)
        self.assertIn(FailureCategory.INVENTORY_IMBALANCE, FailureCategory)
        self.assertIn(FailureCategory.CONCURRENCY_ISSUE, FailureCategory)

    def test_values(self):
        self.assertEqual(FailureCategory.DATA_INTEGRITY.value, "data_integrity")
        self.assertEqual(FailureCategory.LEDGER_IMBALANCE.value, "ledger_imbalance")

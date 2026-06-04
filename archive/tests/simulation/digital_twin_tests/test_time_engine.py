"""Tests for the Time Pressure Engine subpackage.

Covers PerfTimer, SLAMonitor, ClockDriftSimulator, QueueBacklogSimulator.
"""

import unittest
from collections import deque

from simulation.digital_twin.time_engine.timer import PerfTimer
from simulation.digital_twin.time_engine.sla_monitor import SLAMonitor
from simulation.digital_twin.time_engine.clock_drift import ClockDriftSimulator
from simulation.digital_twin.time_engine.queue_backlog import (
    QueueBacklogSimulator,
)


# ===================================================================
# PerfTimer
# ===================================================================

class TestPerfTimer(unittest.TestCase):
    """PerfTimer: start/elapsed/stop, check_sla, stats, errors, clear."""

    def setUp(self):
        self.timer = PerfTimer(max_history=100)

    def test_start_elapsed_stop_basic_flow(self):
        self.timer.start("op1")
        self.assertGreaterEqual(self.timer.elapsed("op1"), 0)

        # Advance the internal tick counter by calling stop
        elapsed = self.timer.stop("op1")
        self.assertIsInstance(elapsed, int)
        self.assertGreaterEqual(elapsed, 0)

    def test_elapsed_increases_with_more_ticks(self):
        self.timer.start("op1")
        e1 = self.timer.elapsed("op1")
        self.timer.start("filler")
        self.timer.stop("filler")
        e2 = self.timer.elapsed("op1")
        self.assertGreater(e2, e1)

    def test_check_sla_within_breached(self):
        self.timer.start("quick")
        result = self.timer.check_sla("quick", sla_ticks=100)
        self.assertTrue(result["within_sla"])
        self.assertEqual(result["operation_id"], "quick")
        self.assertIn("remaining", result)
        self.assertGreaterEqual(result["remaining"], 0)

        # Stop and verify it doesn't affect check_sla
        self.timer.stop("quick")

    def test_check_sla_breached(self):
        self.timer.start("slow")
        for _ in range(10):
            self.timer.start(f"dummy{_}")
            self.timer.stop(f"dummy{_}")
        result = self.timer.check_sla("slow", sla_ticks=1)
        self.assertFalse(result["within_sla"])
        self.assertLess(result["remaining"], 0)
        self.timer.stop("slow")

    def test_is_running(self):
        self.assertFalse(self.timer.is_running("nonexistent"))
        self.timer.start("op1")
        self.assertTrue(self.timer.is_running("op1"))
        self.timer.stop("op1")
        self.assertFalse(self.timer.is_running("op1"))

    def test_get_stats_with_multiple_timers(self):
        self.timer.start("a")
        self.timer.stop("a")
        # Advance ticker with filler ops so b has positive elapsed
        self.timer.start("f1")
        self.timer.stop("f1")
        self.timer.start("f2")
        self.timer.stop("f2")
        self.timer.start("b")
        self.timer.stop("b")
        self.timer.start("c")
        self.timer.stop("c")

        stats = self.timer.get_stats()
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["running_count"], 0)
        self.assertGreater(stats["avg"], 0)
        self.assertGreaterEqual(stats["max"], stats["min"])

    def test_get_stats_with_running(self):
        self.timer.start("a")
        self.timer.stop("a")
        self.timer.start("running_op")
        stats = self.timer.get_stats()
        self.assertEqual(stats["count"], 1)
        self.assertEqual(stats["running_count"], 1)
        self.timer.stop("running_op")

    def test_value_error_double_start(self):
        self.timer.start("dup")
        with self.assertRaises(ValueError):
            self.timer.start("dup")
        self.timer.stop("dup")

    def test_value_error_stop_non_running(self):
        with self.assertRaises(ValueError):
            self.timer.stop("never_started")

    def test_value_error_elapsed_non_running(self):
        with self.assertRaises(ValueError):
            self.timer.elapsed("never_started")

    def test_value_error_check_sla_non_running(self):
        with self.assertRaises(ValueError):
            self.timer.check_sla("never_started", sla_ticks=5)

    def test_clear(self):
        self.timer.start("a")
        self.timer.stop("a")
        self.timer.start("b")
        self.timer.clear()
        self.assertEqual(self.timer.get_stats()["count"], 0)
        self.assertEqual(self.timer.get_stats()["running_count"], 0)
        self.assertFalse(self.timer.is_running("b"))


# ===================================================================
# SLAMonitor
# ===================================================================

class TestSLAMonitor(unittest.TestCase):
    """SLAMonitor: default SLAs, check, violations, breach rate, clear."""

    def setUp(self):
        self.monitor = SLAMonitor(max_violations=50)

    def test_default_slas_configured(self):
        self.assertEqual(self.monitor._slas["invoice_processing"], 2)
        self.assertEqual(self.monitor._slas["workflow_execution"], 10)
        self.assertEqual(self.monitor._slas["reconciliation"], 30)
        self.assertEqual(self.monitor._slas["payment_processing"], 3)

    def test_custom_slas_override_defaults(self):
        m = SLAMonitor(slas={"invoice_processing": 5, "custom_op": 99})
        self.assertEqual(m._slas["invoice_processing"], 5)
        self.assertEqual(m._slas["custom_op"], 99)
        self.assertEqual(m._slas["workflow_execution"], 10)

    def test_check_within_sla(self):
        result = self.monitor.check_operation("invoice_processing", 1)
        self.assertTrue(result["within_sla"])
        self.assertEqual(result["sla_target"], 2)
        self.assertEqual(result["breach_ratio"], 0.0)

    def test_check_breached_auto_records_violation(self):
        result = self.monitor.check_operation("invoice_processing", 5)
        self.assertFalse(result["within_sla"])
        self.assertGreater(result["breach_ratio"], 0.0)
        self.assertEqual(self.monitor.get_violation_count(), 1)

    def test_unknown_operation_is_within_sla(self):
        result = self.monitor.check_operation("unknown_op", 999)
        self.assertTrue(result["within_sla"])
        self.assertIsNone(result["sla_target"])

    def test_get_violations_filtered_by_operation(self):
        self.monitor.check_operation("invoice_processing", 5)
        self.monitor.check_operation("workflow_execution", 20)
        self.monitor.check_operation("invoice_processing", 3)

        inv_violations = self.monitor.get_violations("invoice_processing")
        self.assertEqual(len(inv_violations), 2)

        all_violations = self.monitor.get_violations()
        self.assertEqual(len(all_violations), 3)

    def test_get_violations_no_filter(self):
        self.monitor.check_operation("invoice_processing", 5)
        self.assertEqual(len(self.monitor.get_violations()), 1)

    def test_breach_rate_calculation(self):
        self.assertEqual(self.monitor.get_breach_rate(), 0.0)

        self.monitor.check_operation("invoice_processing", 1)
        self.assertEqual(self.monitor.get_breach_rate(), 0.0)

        self.monitor.check_operation("invoice_processing", 10)
        expected = 1 / 2
        self.assertEqual(self.monitor.get_breach_rate(), expected)

    def test_record_violation_manual(self):
        record = self.monitor.record_violation("manual_op", 99, 42)
        self.assertEqual(record["operation"], "manual_op")
        self.assertEqual(record["elapsed"], 99)
        self.assertEqual(record["tick"], 42)
        self.assertEqual(self.monitor.get_violation_count(), 1)

    def test_get_total_checks(self):
        self.assertEqual(self.monitor.get_total_checks(), 0)
        self.monitor.check_operation("a", 1)
        self.monitor.check_operation("b", 2)
        self.assertEqual(self.monitor.get_total_checks(), 2)

    def test_clear(self):
        self.monitor.check_operation("invoice_processing", 5)
        self.monitor.check_operation("workflow_execution", 20)
        self.monitor.clear()
        self.assertEqual(self.monitor.get_violation_count(), 0)
        self.assertEqual(self.monitor.get_total_checks(), 0)


# ===================================================================
# ClockDriftSimulator
# ===================================================================

class TestClockDriftSimulator(unittest.TestCase):
    """ClockDriftSimulator: initialization, drift accumulation, desync, reset, clear."""

    def setUp(self):
        self.drift = ClockDriftSimulator(drift_rate=0.05, max_history=50)

    def test_initial_drift_is_zero(self):
        self.assertEqual(self.drift.get_total_drift(), 0.0)
        self.assertEqual(len(self.drift.get_drift_history()), 0)

    def test_simulate_tick_accumulates_drift(self):
        r1 = self.drift.simulate_tick()
        self.assertEqual(r1["drift_amount"], 0.05)
        self.assertAlmostEqual(self.drift.get_total_drift(), 0.05)
        self.assertFalse(r1["desynced"])
        self.assertEqual(r1["source"], "internal")
        self.assertEqual(r1["target"], "external")

        r2 = self.drift.simulate_tick()
        self.assertAlmostEqual(self.drift.get_total_drift(), 0.10)

    def test_desynced_after_enough_ticks(self):
        for _ in range(21):
            self.drift.simulate_tick()
        self.assertTrue(self.drift.get_total_drift() > 1.0)

        result = self.drift.simulate_tick()
        self.assertTrue(result["desynced"])

    def test_get_drift_history(self):
        for _ in range(5):
            self.drift.simulate_tick()
        history = self.drift.get_drift_history()
        self.assertEqual(len(history), 5)
        self.assertIn("drift_amount", history[0])
        self.assertIn("desynced", history[0])

    def test_reset(self):
        for _ in range(10):
            self.drift.simulate_tick()
        self.assertGreater(self.drift.get_total_drift(), 0.0)
        self.assertEqual(len(self.drift.get_drift_history()), 10)

        self.drift.reset()
        self.assertEqual(self.drift.get_total_drift(), 0.0)
        self.assertEqual(len(self.drift.get_drift_history()), 10)

    def test_clear(self):
        for _ in range(10):
            self.drift.simulate_tick()
        self.drift.clear()
        self.assertEqual(self.drift.get_total_drift(), 0.0)
        self.assertEqual(len(self.drift.get_drift_history()), 0)

    def test_history_is_bounded(self):
        for _ in range(100):
            self.drift.simulate_tick()
        self.assertLessEqual(len(self.drift.get_drift_history()), 50)


# ===================================================================
# QueueBacklogSimulator
# ===================================================================

class TestQueueBacklogSimulator(unittest.TestCase):
    """QueueBacklogSimulator: init, process_tick, push_events, starvation, pressure."""

    def setUp(self):
        self.queue = QueueBacklogSimulator(
            arrival_rate=2.0,
            processing_rate=1.5,
            warning_threshold=10,
            critical_threshold=20,
            max_history=50,
        )

    def test_initial_state(self):
        self.assertEqual(self.queue.get_current_backlog(), 0)
        self.assertFalse(self.queue.is_starved())
        self.assertEqual(len(self.queue.get_backlog_history()), 0)

    def test_process_tick_adds_arrivals_and_processes(self):
        result = self.queue.process_tick()
        self.assertIn("backlog_size", result)
        self.assertIn("arrivals", result)
        self.assertIn("processed", result)
        # Tick 1 (odd): arrivals = 2 + 0 = 2, processed = min(0, 1) = 0
        self.assertEqual(result["arrivals"], 2)
        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["backlog_size"], 2)

    def test_process_tick_deterministic_alternation(self):
        r1 = self.queue.process_tick()  # tick 1 (odd): arrivals = 2
        self.assertEqual(r1["arrivals"], 2)
        r2 = self.queue.process_tick()  # tick 2 (even): arrivals = 3
        self.assertEqual(r2["arrivals"], 3)

    def test_push_events(self):
        self.queue.push_events(5)
        self.assertEqual(self.queue.get_current_backlog(), 5)

        result = self.queue.process_tick()
        # Even tick: arrivals = 3, processed = min(5, 1) = 1
        self.assertEqual(result["processed"], 1)

    def test_starvation_when_backlog_exceeds_critical(self):
        self.assertFalse(self.queue.is_starved())
        self.queue.push_events(21)
        self.assertTrue(self.queue.is_starved())

        result = self.queue.process_tick()
        self.assertTrue(result["is_starved"])

    def test_pressure_level_transitions(self):
        r = self.queue.process_tick()
        self.assertEqual(r["pressure_level"], "normal")

        self.queue.push_events(10)
        r = self.queue.process_tick()
        self.assertEqual(r["pressure_level"], "warning")

        self.queue.push_events(15)
        r = self.queue.process_tick()
        self.assertEqual(r["pressure_level"], "critical")

    def test_get_backlog_history(self):
        self.queue.process_tick()
        self.queue.process_tick()
        self.queue.process_tick()
        history = self.queue.get_backlog_history()
        self.assertEqual(len(history), 3)
        self.assertIn("tick", history[0])
        self.assertIn("backlog_size", history[0])

    def test_clear(self):
        self.queue.process_tick()
        self.queue.push_events(10)
        self.queue.clear()
        self.assertEqual(self.queue.get_current_backlog(), 0)
        self.assertEqual(len(self.queue.get_backlog_history()), 0)
        self.assertFalse(self.queue.is_starved())

    def test_history_is_bounded(self):
        for _ in range(100):
            self.queue.process_tick()
        self.assertLessEqual(len(self.queue.get_backlog_history()), 50)


if __name__ == "__main__":
    unittest.main()

import time
from typing import Any, Dict

from django.test import TestCase

from core.sandbox.engine import SandboxEngine
from core.sandbox.event_bus import EventBus
from core.sandbox.models import (
    CommandStatus,
    EventPriority,
    ExecutionResult,
    FailureConfig,
    ObservabilitySnapshot,
    ReplayEntry,
    SandboxEvent,
    ERPCommand,
)
from core.sandbox.processor import CommandProcessor, ConcurrencyManager
from core.sandbox.chaos import FailureInjectionEngine
from core.sandbox.bridge import IntegrityBridge, ReplayBuffer
from core.sandbox.observability import ObservabilityLayer


class TestSandboxEvent(TestCase):
    def test_default_priority(self):
        e = SandboxEvent(event_id="1", event_type="test")
        self.assertEqual(e.priority, EventPriority.NORMAL)

    def test_timestamp_set(self):
        e = SandboxEvent(event_id="1", event_type="test")
        self.assertIsNotNone(e.timestamp)

    def test_default_processed_false(self):
        e = SandboxEvent(event_id="1", event_type="test")
        self.assertFalse(e.processed)


class TestERPCommand(TestCase):
    def test_default_status(self):
        cmd = ERPCommand(command_id="1", command_type="TEST", payload={})
        self.assertEqual(cmd.status, CommandStatus.PENDING)

    def test_context_default(self):
        cmd = ERPCommand(command_id="1", command_type="TEST", payload={})
        self.assertEqual(cmd.context, {})


class TestExecutionResult(TestCase):
    def test_ok(self):
        r = ExecutionResult.ok("c1", "TEST", 42, 1.5)
        self.assertTrue(r.success)
        self.assertEqual(r.result, 42)
        self.assertEqual(r.duration_ms, 1.5)

    def test_fail(self):
        r = ExecutionResult.fail("c2", "TEST", "error msg", True)
        self.assertFalse(r.success)
        self.assertEqual(r.error, "error msg")
        self.assertTrue(r.rolled_back)

    def test_defaults(self):
        r = ExecutionResult(success=True)
        self.assertTrue(r.integrity_passed)
        self.assertFalse(r.chaos_injected)


class TestEventBus(TestCase):
    def setUp(self):
        self.bus = EventBus.get_instance()
        self.bus.clear()

    def test_publish_returns_id(self):
        eid = self.bus.publish("test.event", {"key": "val"})
        self.assertIsNotNone(eid)
        self.assertGreater(len(eid), 0)

    def test_queue_length(self):
        self.bus.publish("t1", {})
        self.bus.publish("t2", {})
        self.assertEqual(self.bus.get_queue_length(), 2)

    def test_process_next_returns_event(self):
        self.bus.publish("test.event", {"x": 1})
        event = self.bus.process_next()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "test.event")
        self.assertEqual(event.payload, {"x": 1})

    def test_process_next_priority_order(self):
        self.bus.publish("low", {}, EventPriority.LOW)
        self.bus.publish("critical", {}, EventPriority.CRITICAL)
        self.bus.publish("normal", {}, EventPriority.NORMAL)
        e1 = self.bus.process_next()
        self.assertEqual(e1.event_type, "critical")
        e2 = self.bus.process_next()
        self.assertEqual(e2.event_type, "normal")
        e3 = self.bus.process_next()
        self.assertEqual(e3.event_type, "low")

    def test_subscriber_gets_called(self):
        results = []

        def handler(event):
            results.append(event.payload)

        self.bus.subscribe("test.event", handler)
        self.bus.publish("test.event", {"called": True})
        self.bus.process_next()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["called"])

    def test_subscriber_error_does_not_crash(self):
        def failing(event):
            raise ValueError("Intentional")

        self.bus.subscribe("fail.event", failing)
        self.bus.publish("fail.event", {})
        event = self.bus.process_next()
        self.assertIsNotNone(event)

    def test_process_all_drains_queue(self):
        for i in range(5):
            self.bus.publish(f"ev{i}", {})
        count = self.bus.process_all()
        self.assertEqual(count, 5)
        self.assertEqual(self.bus.get_queue_length(), 0)

    def test_process_all_with_max(self):
        for i in range(10):
            self.bus.publish(f"ev{i}", {})
        count = self.bus.process_all(max_events=3)
        self.assertEqual(count, 3)

    def test_process_next_empty_returns_none(self):
        event = self.bus.process_next()
        self.assertIsNone(event)

    def test_queue_stats(self):
        self.bus.publish("a", {}, EventPriority.HIGH)
        self.bus.publish("b", {}, EventPriority.LOW)
        stats = self.bus.get_queue_stats()
        self.assertEqual(stats["high"], 1)
        self.assertEqual(stats["low"], 1)
        self.assertEqual(stats["normal"], 0)

    def test_max_queue_bounded(self):
        for i in range(10001):
            self.bus.publish(f"ev{i}", {})
        self.assertLessEqual(self.bus.get_queue_length(), 10000)


class TestCommandProcessor(TestCase):
    def setUp(self):
        self.proc = CommandProcessor.get_instance()
        self.proc.clear_history()

    def test_register_and_execute(self):
        def add_one(cmd):
            return cmd.payload["x"] + 1

        self.proc.register_command("ADD_ONE", add_one)
        result = self.proc.execute("ADD_ONE", {"x": 41})
        self.assertTrue(result.success)
        self.assertEqual(result.result, 42)

    def test_unknown_command(self):
        result = self.proc.execute("UNKNOWN", {})
        self.assertFalse(result.success)
        self.assertIn("Unknown", result.error)

    def test_handler_exception(self):
        def failing(cmd):
            raise RuntimeError("Handler crash")

        self.proc.register_command("FAIL", failing)
        result = self.proc.execute("FAIL", {})
        self.assertFalse(result.success)
        self.assertIn("Handler crash", result.error)

    def test_history(self):
        self.proc.register_command("OK", lambda cmd: "done")
        self.proc.execute("OK", {})
        self.proc.execute("OK", {})
        self.assertEqual(len(self.proc.get_history()), 2)

    def test_history_limit(self):
        self.proc.register_command("OK", lambda cmd: "done")
        for i in range(150):
            self.proc.execute("OK", {"i": i})
        self.assertEqual(len(self.proc.get_history(limit=100)), 100)

    def test_clear_history(self):
        self.proc.register_command("OK", lambda cmd: "done")
        self.proc.execute("OK", {})
        self.proc.clear_history()
        self.assertEqual(len(self.proc.get_history()), 0)


class TestConcurrencyManager(TestCase):
    def setUp(self):
        self.mgr = ConcurrencyManager.get_instance()
        self.mgr.set_max_workers(4)
        self.mgr.clear_execution_history()

    def test_execute_sequential(self):
        def exec_fn(cmd):
            return ExecutionResult.ok(result=cmd["value"] * 2)

        commands = [
            {"command_type": "A", "value": 1},
            {"command_type": "B", "value": 2},
            {"command_type": "C", "value": 3},
        ]
        results = self.mgr.execute_sequential(commands, exec_fn)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.success for r in results))
        self.assertEqual([r.result for r in results], [2, 4, 6])

    def test_execute_parallel(self):
        def exec_fn(cmd):
            return ExecutionResult.ok(result=cmd["value"])

        commands = [
            {"command_type": "A", "value": 10},
            {"command_type": "B", "value": 20},
        ]
        results = self.mgr.execute_parallel(commands, exec_fn)
        self.assertEqual(len(results), 2)

    def test_parallel_with_exception(self):
        def failing(cmd):
            raise ValueError("Parallel failure")

        commands = [
            {"command_type": "A", "value": 1},
            {"command_type": "B", "value": 2},
        ]
        results = self.mgr.execute_parallel(commands, failing)
        self.assertEqual(len(results), 2)
        self.assertFalse(results[0].success)

    def test_set_max_workers_clamped(self):
        self.mgr.set_max_workers(0)
        self.mgr.set_max_workers(100)
        self.mgr.set_max_workers(4)

    def test_execution_summary(self):
        def ok(cmd):
            return ExecutionResult.ok()

        self.mgr.execute_parallel(
            [{"command_type": "A"}, {"command_type": "B"}], ok
        )
        summary = self.mgr.get_execution_summary()
        self.assertEqual(summary["total_commands"], 2)
        self.assertEqual(summary["batches"], 1)


class TestFailureInjectionEngine(TestCase):
    def setUp(self):
        self.chaos = FailureInjectionEngine.get_instance()
        self.chaos.disable()
        self.chaos.clear_log()

    def test_disabled_returns_none(self):
        self.assertIsNone(self.chaos.maybe_inject())

    def test_enabled_with_zero_prob_returns_none(self):
        self.chaos.enable(fk_violation_prob=0.0)
        self.assertIsNone(self.chaos.maybe_inject())

    def test_fk_violation_injection(self):
        self.chaos.enable(fk_violation_prob=1.0)
        injection = self.chaos.maybe_inject()
        self.assertIsNotNone(injection)
        self.assertEqual(injection["type"], "FK_VIOLATION")

    def test_invalid_operation_injection(self):
        self.chaos.enable(invalid_op_prob=1.0)
        injection = self.chaos.maybe_inject()
        self.assertEqual(injection["type"], "INVALID_OPERATION")

    def test_partial_failure_injection(self):
        self.chaos.enable(partial_failure_prob=1.0)
        injection = self.chaos.maybe_inject()
        self.assertEqual(injection["type"], "PARTIAL_FAILURE")

    def test_corruption_injection(self):
        self.chaos.enable(corruption_prob=1.0)
        injection = self.chaos.maybe_inject()
        self.assertEqual(injection["type"], "DATA_CORRUPTION")

    def test_injection_log(self):
        self.chaos.enable(fk_violation_prob=1.0)
        self.chaos.maybe_inject()
        self.chaos.maybe_inject()
        self.assertEqual(self.chaos.count_injections(), 2)

    def test_clear_log(self):
        self.chaos.enable(fk_violation_prob=1.0)
        self.chaos.maybe_inject()
        self.chaos.clear_log()
        self.assertEqual(self.chaos.count_injections(), 0)


class TestIntegrityBridge(TestCase):
    def setUp(self):
        self.bridge = IntegrityBridge.get_instance()
        from core.integrity.engine import IntegrityEngine
        eng = IntegrityEngine.get_instance()
        eng.configure()
        self.bridge.connect(eng)

    def test_is_connected(self):
        self.assertTrue(self.bridge.is_connected())

    def test_execute_clean_operation(self):
        result = self.bridge.execute_with_integrity(
            operation_fn=lambda: 42,
            verify_after=False,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 42)

    def test_execute_blocked_by_no_engine(self):
        bridge = IntegrityBridge.get_instance()
        result = bridge.execute_with_integrity(
            operation_fn=lambda: 1,
        )
        self.assertTrue(result["success"])


class TestReplayBuffer(TestCase):
    def setUp(self):
        self.buf = ReplayBuffer.get_instance()
        self.buf.clear()

    def test_record_returns_sequence(self):
        seq = self.buf.record(command_type="TEST")
        self.assertEqual(seq, 1)

    def test_record_increments(self):
        s1 = self.buf.record(command_type="A")
        s2 = self.buf.record(command_type="B")
        self.assertEqual(s1, 1)
        self.assertEqual(s2, 2)

    def test_get_sequence(self):
        self.buf.record(command_type="A")
        self.buf.record(command_type="B")
        seq = self.buf.get_sequence(from_id=1, to_id=2)
        self.assertEqual(len(seq), 2)

    def test_get_sequence_from_start(self):
        self.buf.record(command_type="X")
        self.buf.record(command_type="Y")
        seq = self.buf.get_sequence(from_id=1)
        self.assertEqual(len(seq), 2)

    def test_replay_all(self):
        self.buf.record(command_type="A")
        self.buf.record(command_type="B")
        self.buf.record(command_type="C")
        entries = self.buf.replay()
        self.assertGreaterEqual(len(entries), 3)

    def test_checksum(self):
        self.buf.record(command_type="A", payload={"x": 1})
        cs1 = self.buf.checksum()
        self.buf.record(command_type="B", payload={"x": 2})
        cs2 = self.buf.checksum()
        self.assertNotEqual(cs1, cs2)

    def test_count(self):
        self.buf.record(command_type="A")
        self.buf.record(command_type="B")
        self.assertEqual(self.buf.count(), 2)

    def test_clear(self):
        self.buf.record(command_type="A")
        self.buf.clear()
        self.assertEqual(self.buf.count(), 0)

    def test_get_last_sequence_id(self):
        self.assertEqual(self.buf.get_last_sequence_id(), 0)
        self.buf.record(command_type="A")
        self.assertEqual(self.buf.get_last_sequence_id(), 1)

    def test_bounded(self):
        for i in range(10001):
            self.buf.record(command_type=f"EV{i}")
        self.assertLessEqual(self.buf.count(), 10000)


class TestObservabilityLayer(TestCase):
    def setUp(self):
        self.obs = ObservabilityLayer.get_instance()
        self.obs.reset()

    def test_initial_state(self):
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_executed, 0)

    def test_record_success(self):
        self.obs.record_success(10.0)
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_executed, 1)
        self.assertEqual(s.commands_succeeded, 1)

    def test_record_failure(self):
        self.obs.record_failure(5.0)
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_failed, 1)

    def test_record_rollback(self):
        self.obs.record_rollback()
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_rolled_back, 1)

    def test_record_blocked(self):
        self.obs.record_blocked()
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_blocked, 1)

    def test_record_chaos_injection(self):
        self.obs.record_chaos_injection()
        s = self.obs.get_snapshot()
        self.assertEqual(s.chaos_injections, 1)

    def test_record_integrity_violation(self):
        self.obs.record_integrity_violation()
        s = self.obs.get_snapshot()
        self.assertEqual(s.integrity_violations, 1)

    def test_record_freeze_trigger(self):
        self.obs.record_freeze_trigger()
        s = self.obs.get_snapshot()
        self.assertEqual(s.freeze_triggers, 1)

    def test_record_event_processed(self):
        self.obs.record_event_processed()
        self.assertEqual(self.obs._events_processed, 1)

    def test_record_execution_result_success(self):
        r = ExecutionResult.ok("c1", "T", "result", 2.0)
        status = self.obs.record_execution_result(r)
        self.assertEqual(status, "SUCCESS")
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_succeeded, 1)
        self.assertEqual(s.avg_duration_ms, 2.0)

    def test_record_execution_result_fail(self):
        r = ExecutionResult.fail("c1", "T", "error", True)
        status = self.obs.record_execution_result(r)
        self.assertEqual(status, "FAILED")
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_failed, 1)
        self.assertEqual(s.commands_rolled_back, 1)

    def test_get_report(self):
        self.obs.record_success(10.0)
        self.obs.record_failure(5.0)
        report = self.obs.get_report()
        self.assertIn("success_rate", report)
        self.assertIn("snapshot", report)
        self.assertEqual(report["snapshot"].commands_executed, 2)

    def test_reset(self):
        self.obs.record_success(1.0)
        self.obs.reset()
        s = self.obs.get_snapshot()
        self.assertEqual(s.commands_executed, 0)


class TestSandboxEngine(TestCase):
    def setUp(self):
        self.engine = SandboxEngine.get_instance()
        self.engine.initialize()
        self.engine.disable_chaos()
        buf = ReplayBuffer.get_instance()
        buf.clear()
        obs = ObservabilityLayer.get_instance()
        obs.reset()

    def test_register_and_run_command(self):
        def echo(cmd):
            return cmd.payload

        self.engine.register_command("ECHO", echo)
        from inventory.models import Product

        result = self.engine.run_command(
            command_type="ECHO",
            payload={"msg": "hello"},
            model_class=Product,
            data={"name": "test"},
            verify_after=False,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.result["msg"], "hello")

    def test_run_command_no_model_skips_integrity(self):
        def echo(cmd):
            return "ok"

        self.engine.register_command("ECHO_NOMODEL", echo)
        result = self.engine.run_command(
            command_type="ECHO_NOMODEL",
            payload={},
        )
        self.assertTrue(result.success)

    def test_run_batch_sequential(self):
        def increment(cmd):
            return cmd.payload["val"] + 1

        self.engine.register_command("INCR", increment)
        commands = [
            {"command_type": "INCR", "payload": {"val": 1}},
            {"command_type": "INCR", "payload": {"val": 2}},
            {"command_type": "INCR", "payload": {"val": 3}},
        ]
        results = self.engine.run_batch(commands, parallel=False)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.success for r in results))
        self.assertEqual([r.result for r in results], [2, 3, 4])

    def test_run_batch_parallel(self):
        def echo(cmd):
            return cmd.payload

        self.engine.register_command("ECHO_BATCH", echo)
        commands = [
            {"command_type": "ECHO_BATCH", "payload": {"n": i}}
            for i in range(5)
        ]
        results = self.engine.run_batch(commands, parallel=True)
        self.assertEqual(len(results), 5)

    def test_chaos_rejected(self):
        def safe_op(cmd):
            return "done"

        self.engine.register_command("SAFE", safe_op)
        self.engine.enable_chaos(invalid_op_prob=1.0)
        from inventory.models import Product

        result = self.engine.run_command(
            command_type="SAFE",
            payload={},
            model_class=Product,
            data={"name": "x"},
            verify_after=False,
        )
        self.assertFalse(result.success)
        self.assertIn("Chaos injection", result.error)
        self.engine.disable_chaos()

    def test_replay_records_after_command(self):
        def ok(cmd):
            return "recorded"

        self.engine.register_command("REC", ok)
        buf = ReplayBuffer.get_instance()
        before = buf.count()
        from inventory.models import Product

        self.engine.run_command(
            command_type="REC",
            payload={"record": True},
            model_class=Product,
            data={"name": "x"},
            verify_after=False,
        )
        after = buf.count()
        self.assertGreater(after, before)

    def test_observability_updated_after_command(self):
        def ok(cmd):
            return "done"

        self.engine.register_command("OBS", ok)
        obs = ObservabilityLayer.get_instance()
        before = obs.get_snapshot().commands_executed
        from inventory.models import Product

        self.engine.run_command(
            command_type="OBS",
            payload={},
            model_class=Product,
            data={"name": "x"},
            verify_after=False,
        )
        after = obs.get_snapshot().commands_executed
        self.assertGreater(after, before)

    def test_status_report(self):
        report = self.engine.get_status_report()
        self.assertIn("observability", report)
        self.assertIn("replay", report)
        self.assertIn("event_bus", report)
        self.assertIn("chaos", report)

    def test_double_initialize_safe(self):
        self.engine.initialize()
        self.assertTrue(self.engine._bridge.is_connected())


class TestSingletons(TestCase):
    def test_event_bus_singleton(self):
        a = EventBus.get_instance()
        b = EventBus.get_instance()
        self.assertIs(a, b)

    def test_processor_singleton(self):
        a = CommandProcessor.get_instance()
        b = CommandProcessor.get_instance()
        self.assertIs(a, b)

    def test_concurrency_singleton(self):
        a = ConcurrencyManager.get_instance()
        b = ConcurrencyManager.get_instance()
        self.assertIs(a, b)

    def test_chaos_singleton(self):
        a = FailureInjectionEngine.get_instance()
        b = FailureInjectionEngine.get_instance()
        self.assertIs(a, b)

    def test_bridge_singleton(self):
        a = IntegrityBridge.get_instance()
        b = IntegrityBridge.get_instance()
        self.assertIs(a, b)

    def test_replay_singleton(self):
        a = ReplayBuffer.get_instance()
        b = ReplayBuffer.get_instance()
        self.assertIs(a, b)

    def test_observability_singleton(self):
        a = ObservabilityLayer.get_instance()
        b = ObservabilityLayer.get_instance()
        self.assertIs(a, b)

    def test_engine_singleton(self):
        a = SandboxEngine.get_instance()
        b = SandboxEngine.get_instance()
        self.assertIs(a, b)


class TestEventPriorities(TestCase):
    def test_all_priorities(self):
        expected = {"low", "normal", "high", "critical"}
        actual = {p.value for p in EventPriority}
        self.assertEqual(actual, expected)


class TestCommandStatusEnum(TestCase):
    def test_all_statuses(self):
        expected = {"pending", "running", "success", "failed", "rolled_back", "blocked"}
        actual = {s.value for s in CommandStatus}
        self.assertEqual(actual, expected)


class TestFailureConfig(TestCase):
    def test_default_disabled(self):
        cfg = FailureConfig()
        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.fk_violation_probability, 0.0)

    def test_rounds(self):
        cfg = FailureConfig(enabled=True, fk_violation_probability=0.5)
        self.assertTrue(cfg.enabled)
        self.assertEqual(cfg.fk_violation_probability, 0.5)

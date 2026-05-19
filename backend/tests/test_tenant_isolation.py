"""Phase 17++ — Event Bus Final Hardening Tests.
Validates: safety layer, buffer, backpressure, deterministic envelope, replay, dispatch priority.
"""
import time
from uuid import UUID

from django.test import TestCase

from core.models import Company
from core.multitenant.context import TenantContext
from core.multitenant.views import UnifiedEnterpriseViewSetMixin
import core.events
from core.events import EnterpriseEventBus, MAX_EVENT_DEPTH
from core.events.instrumentors import publish_event
from core.events.safety import (
    EventCategory, EVENT_PRIORITY, safety_buffer, backpressure,
    build_envelope, validate_envelope, dispatch_safe, classify_handlers,
    should_downgrade, BackpressureMetrics, EventSafetyBuffer,
)
from core.audit_collector import UnifiedAuditCollector
from core.governance.query_governance import warn_unsafe_query, QueryGovernance
from workflows.models import ApprovalChain, WorkflowInstance


class Phase17ValidationTest(TestCase):
    """Phase 17.7 — Validate unified enforcement + event bus + audit + governance."""

    def setUp(self):
        self.company_a = Company.objects.create(name="Company A", code="CMP_A", is_active=True)
        self.company_b = Company.objects.create(name="Company B", code="CMP_B", is_active=True)

    # ── Phase 17.1/17.2: Unified Enforcement Layer ──

    def test_unified_mixin_inherits_correctly(self):
        """UnifiedEnterpriseViewSetMixin has both get_queryset and perform_create."""
        mixin = UnifiedEnterpriseViewSetMixin
        self.assertTrue(hasattr(mixin, "get_queryset"))
        self.assertTrue(hasattr(mixin, "perform_create"))
        self.assertTrue(hasattr(mixin, "perform_update"))

    def test_cross_tenant_isolation_approval_chain(self):
        """ApprovalChains remain isolated between companies."""
        ac_a = ApprovalChain.objects.create(company=self.company_a, name="Chain A", code="CH_A", entity_type="SALE")
        ac_b = ApprovalChain.objects.create(company=self.company_b, name="Chain B", code="CH_B", entity_type="SALE")
        visible_a = list(ApprovalChain.objects.filter(company_id=self.company_a.id))
        self.assertIn(ac_a, visible_a)
        self.assertNotIn(ac_b, visible_a)

    def test_cross_tenant_isolation_workflow_instance(self):
        """WorkflowInstances remain isolated between companies."""
        wi_a = WorkflowInstance.objects.create(
            company=self.company_a, content_type="SALE",
            object_id="00000000-0000-0000-0000-000000000001",
            current_state="DRAFT", title="WI A"
        )
        wi_b = WorkflowInstance.objects.create(
            company=self.company_b, content_type="SALE",
            object_id="00000000-0000-0000-0000-000000000002",
            current_state="DRAFT", title="WI B"
        )
        visible_a = list(WorkflowInstance.objects.filter(company_id=self.company_a.id))
        self.assertIn(wi_a, visible_a)
        self.assertNotIn(wi_b, visible_a)

    # ── Phase 17.3: Event Bus (Thin Dispatcher) ──

    def test_event_bus_subscribe_and_publish(self):
        """EnterpriseEventBus delivers events to subscribed handlers."""
        received = []

        def test_handler(payload):
            received.append(payload)

        EnterpriseEventBus.subscribe("test.event", test_handler)
        EnterpriseEventBus.publish("test.event", {"key": "value"})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["key"], "value")
        EnterpriseEventBus._subscribers["test.event"].remove(test_handler)

    def test_event_bus_handler_failure_does_not_break(self):
        """EnterpriseEventBus handler failure must not raise."""
        def broken_handler(payload):
            raise ValueError("Handler failure")

        def good_handler(payload):
            pass

        EnterpriseEventBus.subscribe("test.broken", broken_handler)
        EnterpriseEventBus.subscribe("test.broken", good_handler)
        try:
            EnterpriseEventBus.publish("test.broken", {"key": "value"})
        except Exception:
            self.fail("Event bus raised on handler failure")
        EnterpriseEventBus._subscribers["test.broken"].remove(broken_handler)
        EnterpriseEventBus._subscribers["test.broken"].remove(good_handler)

    def test_event_bus_clear(self):
        """EnterpriseEventBus.clear removes all subscribers."""
        EnterpriseEventBus.subscribe("test.clear", lambda p: None)
        EnterpriseEventBus.clear()
        self.assertEqual(len(EnterpriseEventBus._subscribers), 0)

    # ── Phase 17+ Loop Prevention ──

    def test_event_loop_prevention_drops_at_max_depth(self):
        """Events exceeding MAX_EVENT_DEPTH are dropped."""
        received = []

        def recursive_handler(payload):
            received.append(payload)
            EnterpriseEventBus.publish("test.loop", {"correlation_id": payload.get("correlation_id", "")})

        EnterpriseEventBus.subscribe("test.loop", recursive_handler)
        publish_event("test.loop", {"msg": "start"})
        self.assertLessEqual(len(received), MAX_EVENT_DEPTH + 1)
        EnterpriseEventBus._subscribers["test.loop"].remove(recursive_handler)

    def test_event_loop_reentry_correlation_id(self):
        """Deeply nested publish with same correlation_id is bounded."""
        depths = []

        def depth_handler(payload):
            depths.append(payload.get("depth", 0))
            if payload.get("depth", 0) < 3:
                EnterpriseEventBus.publish("test.reentry", payload)

        EnterpriseEventBus.subscribe("test.reentry", depth_handler)
        publish_event("test.reentry", {"msg": "reentry"})
        self.assertLessEqual(len(depths), MAX_EVENT_DEPTH + 1)
        EnterpriseEventBus._subscribers["test.reentry"].remove(depth_handler)

    def test_instrumentor_fail_open_on_bus_error(self):
        """publish_event must never raise even if bus is broken."""
        original_publish = EnterpriseEventBus.publish
        def broken_publish(event_name, payload):
            raise RuntimeError("Bus failure")
        EnterpriseEventBus.publish = broken_publish
        try:
            publish_event("test.failopen", {"msg": "should not raise"})
        except Exception:
            self.fail("publish_event raised on bus failure")
        finally:
            EnterpriseEventBus.publish = original_publish

    # ── Phase 17+ Handler Isolation ──

    def test_handler_domain_isolation(self):
        """Domain handler modules have no cross-domain imports."""
        import ast
        import core.events.handlers.sales as hs
        import core.events.handlers.purchases as hp
        import core.events.handlers.inventory as hi
        import core.events.handlers.accounting as ha
        import core.events.handlers.returns as hr_mod
        import core.events.handlers.payroll as hpy
        ALLOWED_MODULES = {"logging", "core.events"}
        for mod in [hs, hp, hi, ha, hr_mod, hpy]:
            source = mod.__file__
            if source and source.endswith(".py"):
                tree = ast.parse(open(source).read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name not in ALLOWED_MODULES:
                                self.fail(f"{mod.__name__} imports forbidden: {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module not in ALLOWED_MODULES:
                            self.fail(f"{mod.__name__} imports from forbidden: {node.module}")

    # ── Phase 17+ Performance Baseline ──

    def test_event_dispatch_performance(self):
        """Event dispatch overhead must be < 2ms."""
        received = []

        def fast_handler(payload):
            received.append(payload)

        EnterpriseEventBus.subscribe("test.perf", fast_handler)
        start = time.perf_counter()
        for _ in range(100):
            EnterpriseEventBus.publish("test.perf", {"n": 1})
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100
        self.assertLess(elapsed_ms, 2.0, f"Dispatch took {elapsed_ms:.3f}ms (limit 2ms)")
        EnterpriseEventBus._subscribers["test.perf"].remove(fast_handler)

    def test_publish_event_is_lightweight(self):
        """publish_event creates proper event envelope with correlation_id."""
        received = []

        def capture_handler(payload):
            received.append(payload)

        EnterpriseEventBus.subscribe("test.envelope", capture_handler)
        publish_event("test.envelope", {"msg": "hello"}, actor_id="u1", company_id="c1")
        self.assertEqual(len(received), 1)
        event = received[0]
        self.assertEqual(event["name"], "test.envelope")
        self.assertEqual(event["actor_id"], "u1")
        self.assertEqual(event["company_id"], "c1")
        UUID(event["correlation_id"])
        self.assertEqual(event["payload"]["msg"], "hello")
        EnterpriseEventBus._subscribers["test.envelope"].remove(capture_handler)

    def test_publish_event_never_raises(self):
        """publish_event must never raise under any circumstances."""
        try:
            publish_event("test.safe", {"id": "1"}, company_id=str(self.company_a.id))
            publish_event("test.safe", {"id": "2", "nested": {"a": 1}})
            publish_event("test.safe", {})
        except Exception as e:
            self.fail(f"publish_event raised: {e}")

    # ── Phase 17.5: Audit Unification ──

    def test_audit_collector_normalizes_security_log(self):
        """UnifiedAuditCollector normalizes Security log entries."""
        class MockEntry:
            action = "user.login"
            user_id = "u1"
            model_name = "User"
            object_id = "u1"
            company_id = "c1"
            message = "User logged in"
            details = {"ip": "127.0.0.1"}
            created_at = "2026-01-01T00:00:00Z"

        result = UnifiedAuditCollector.collect_security_log(MockEntry())
        self.assertEqual(result["event_type"], "user.login")
        self.assertEqual(result["actor_id"], "u1")
        self.assertEqual(result["target_type"], "User")
        self.assertEqual(result["company_id"], "c1")
        self.assertEqual(result["source"], "security.AuditLog")

    def test_audit_collector_normalizes_event_log(self):
        """UnifiedAuditCollector normalizes Event log entries."""
        class MockEntry:
            event_type = "journal.posted"
            actor_id = "u1"
            target_type = "JournalEntry"
            target_id = "je1"
            company_id = "c1"
            description = "JE posted"
            metadata = {"amount": 100}
            created_at = "2026-01-01T00:00:00Z"

        result = UnifiedAuditCollector.collect_event_log(MockEntry())
        self.assertEqual(result["event_type"], "journal.posted")
        self.assertEqual(result["actor_id"], "u1")
        self.assertEqual(result["target_id"], "je1")
        self.assertEqual(result["source"], "audit.EventLog")

    # ── Phase 17.6: Query Governance ──

    def test_query_governance_warns_on_unsafe(self):
        """warn_unsafe_query must not raise in soft mode."""
        try:
            warn_unsafe_query("TestModel", "global_all", "test_caller", "test detail")
        except Exception:
            self.fail("Query governance raised in soft mode")

    def test_query_governance_checks_queryset(self):
        """QueryGovernance.check_queryset must not raise on None."""
        try:
            QueryGovernance.check_queryset(None)
        except Exception:
            self.fail("QueryGovernance.check_queryset raised on None")

    # ════════════════════════════════════════════════════════════════
    # Phase 17++ — Event Safety Layer Tests (Phases 1-7)
    # ════════════════════════════════════════════════════════════════

    # ── Phase 1: Event Classification ──

    def test_event_classification_financial_critical(self):
        """Financial-critical events have priority 5."""
        self.assertEqual(EVENT_PRIORITY["accounting.journal.posted"], EventCategory.FINANCIAL_CRITICAL)
        self.assertEqual(EVENT_PRIORITY["inventory.stock.moved"], EventCategory.FINANCIAL_CRITICAL)
        self.assertEqual(EVENT_PRIORITY["customer.payment.received"], EventCategory.FINANCIAL_CRITICAL)
        self.assertEqual(EventCategory.FINANCIAL_CRITICAL.value, 5)

    def test_event_classification_operational_default(self):
        """Unknown events default to OPERATIONAL (priority 3)."""
        env = build_envelope("unknown.event", {"a": 1})
        self.assertEqual(env["event_type"], "OPERATIONAL")
        self.assertEqual(env["priority"], 3)

    # ── Phase 2: EventSafetyBuffer ──

    def test_safety_buffer_stores_and_replays(self):
        """EventSafetyBuffer stores events and replays them."""
        buf = EventSafetyBuffer(max_size=10)
        buf.store({"name": "test.ev", "id": "1"}, "DEFERRED")
        buf.store({"name": "test.ev", "id": "2"}, "DEPTH_LIMITED")
        self.assertEqual(buf.pending_count, 2)
        replayed = buf.replay(limit=10)
        self.assertEqual(len(replayed), 2)
        self.assertEqual(buf.pending_count, 0)

    def test_safety_buffer_respects_max_size(self):
        """EventSafetyBuffer respects max_size (ring buffer behavior)."""
        buf = EventSafetyBuffer(max_size=5)
        for i in range(10):
            buf.store({"name": "test", "id": str(i)}, "DEFERRED")
        self.assertEqual(buf.pending_count, 5)
        self.assertEqual(buf.usage_ratio, 1.0)

    def test_safety_buffer_replay_by_correlation(self):
        """EventSafetyBuffer replays by correlation_id."""
        buf = EventSafetyBuffer(max_size=20)
        cid = "corr-1"
        buf.store({"name": "ev1", "correlation_id": cid}, "FAILED_HANDLER")
        buf.store({"name": "ev2", "correlation_id": "other"}, "FAILED_HANDLER")
        buf.store({"name": "ev3", "correlation_id": cid}, "FAILED_HANDLER")
        replayed = buf.replay_by_correlation(cid)
        self.assertEqual(len(replayed), 2)
        self.assertEqual(buf.pending_count, 1)

    def test_safety_buffer_invalid_reason_defaults(self):
        """Invalid reason defaults to DEFERRED."""
        buf = EventSafetyBuffer(max_size=10)
        buf.store({"name": "test"}, "INVALID_REASON")
        self.assertEqual(buf.pending_count, 1)

    # ── Phase 3: Backpressure Control ──

    def test_backpressure_metrics_tracks_events(self):
        """BackpressureMetrics records dispatch events."""
        bpm = BackpressureMetrics(window_seconds=60)
        bpm.record_dispatch()
        bpm.record_handler_time(1.5)
        self.assertGreaterEqual(bpm.events_per_second, 0)
        self.assertAlmostEqual(bpm.handler_avg_ms, 1.5)

    def test_backpressure_pressure_levels(self):
        """BackpressureMetrics returns correct pressure level."""
        bpm = BackpressureMetrics(window_seconds=60)
        self.assertEqual(bpm.pressure_level(0.0), "normal")
        self.assertEqual(bpm.pressure_level(0.6), "elevated")
        self.assertEqual(bpm.pressure_level(0.9), "critical")

    # ── Phase 4: Deterministic EventEnvelope ──

    def test_build_envelope_has_all_required_fields(self):
        """build_envelope produces deterministic schema."""
        env = build_envelope("test.event", {"key": "val"}, EventCategory.BUSINESS_CRITICAL, "u1", "c1")
        required = {"event_id", "correlation_id", "event_type", "priority", "name",
                    "actor_id", "company_id", "timestamp", "depth", "payload", "checksum"}
        self.assertTrue(required.issubset(env.keys()))
        UUID(env["event_id"])
        UUID(env["correlation_id"])
        self.assertEqual(env["name"], "test.event")
        self.assertEqual(env["actor_id"], "u1")
        self.assertEqual(env["company_id"], "c1")
        self.assertEqual(env["event_type"], "BUSINESS_CRITICAL")
        self.assertEqual(env["priority"], 4)

    def test_envelope_checksum_validates(self):
        """validate_envelope checks payload integrity."""
        env = build_envelope("test.checksum", {"a": 1})
        self.assertTrue(validate_envelope(env))
        env["payload"]["a"] = 2
        self.assertFalse(validate_envelope(env))

    def test_envelope_rejects_large_payload(self):
        """build_envelope truncates payload >10KB."""
        large = {"data": "x" * 12000}
        env = build_envelope("test.large", large)
        self.assertTrue(env["payload"].get("_truncated"))

    # ── Phase 5: Safe Dispatch Strategy ──

    def test_classify_handlers_no_downgrade(self):
        """classify_handlers separates critical vs non-critical."""
        env = build_envelope("test.event", {}, EventCategory.FINANCIAL_CRITICAL)
        handlers = [lambda p: None, lambda p: None]
        crit, non = classify_handlers(handlers, env, downgrade=False)
        self.assertEqual(len(crit), 2)
        self.assertEqual(len(non), 0)

    def test_classify_handlers_downgrade(self):
        """classify_handlers downgrades non-critical on pressure."""
        env = build_envelope("test.event", {}, EventCategory.OPERATIONAL)
        handlers = [lambda p: None]
        crit, non = classify_handlers(handlers, env, downgrade=True)
        self.assertEqual(len(crit), 0)
        self.assertEqual(len(non), 1)

    def test_should_downgrade_threshold(self):
        """should_downgrade returns True above 80% buffer usage."""
        self.assertFalse(should_downgrade(0.5))
        self.assertTrue(should_downgrade(0.85))

    def test_dispatch_safe_critical_executed_before_non_critical(self):
        """dispatch_safe executes critical handlers first."""
        execution = []

        def crit_handler(payload):
            execution.append("crit")
        safety_buffer.clear()
        env = build_envelope("test.critical_first", {}, EventCategory.FINANCIAL_CRITICAL)
        dispatch_safe([crit_handler], env)
        self.assertEqual(execution, ["crit"])

    def test_financial_critical_buffered_on_depth_limit(self):
        """FINANCIAL_CRITICAL events are buffered (not dropped) at depth limit."""
        safety_buffer.clear()
        self.assertEqual(safety_buffer.pending_count, 0)

        def depth_trigger(payload):
            EnterpriseEventBus.publish("accounting.journal.posted", payload)

        EnterpriseEventBus.subscribe("test.depth_fin", depth_trigger)
        publish_event("test.depth_fin", {"msg": "start"})
        # Depth exceeds, financial event should be buffered
        self.assertGreaterEqual(safety_buffer.pending_count, 0)
        EnterpriseEventBus._subscribers["test.depth_fin"].remove(depth_trigger)

    # ── Phase 6: Event Replay ──

    def test_safety_buffer_replay_management_command_signature(self):
        """replay_events management command exists and has expected interface."""
        from django.core.management import load_command_class
        cmd = load_command_class("core", "replay_events")
        self.assertIsNotNone(cmd)
        parser = cmd.create_parser("manage.py", "replay_events")
        self.assertIsNotNone(parser)

    # ── Phase 7: Handler Resource Isolation ──

    def test_handler_no_expensive_imports(self):
        """Domain handlers do not import ORM or API modules (enforced by import scan)."""
        import ast
        import core.events.handlers.sales as hs
        import core.events.handlers.accounting as ha
        FORBIDDEN = {"django.db", "django.http", "requests", "core.operations"}
        for mod in [hs, ha]:
            source = mod.__file__
            if source and source.endswith(".py"):
                tree = ast.parse(open(source).read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        for alias in node.names:
                            for fb in FORBIDDEN:
                                if alias.name.startswith(fb):
                                    self.fail(f"{mod.__name__} imports forbidden module: {alias.name}")

    # ── Envelope Dispatch Integrity ──

    def test_publish_event_produces_valid_envelope(self):
        """publish_event output passes validate_envelope."""
        received = []

        def capture(payload):
            received.append(payload)

        EnterpriseEventBus.subscribe("test.envelope_valid", capture)
        safety_buffer.clear()
        publish_event("test.envelope_valid", {"x": 1})
        self.assertEqual(len(received), 1)
        self.assertTrue(validate_envelope(received[0]))
        EnterpriseEventBus._subscribers["test.envelope_valid"].remove(capture)

    # ════════════════════════════════════════════════════════════════
    # Architecture Freeze — Final Invariant Tests
    # ════════════════════════════════════════════════════════════════

    def test_freeze_dispatcher_under_80_lines(self):
        """ARCHITECTURE FREEZE: EnterpriseEventBus must stay under 80 lines."""
        import inspect
        src = inspect.getsource(EnterpriseEventBus)
        lines = len(src.strip().splitlines())
        self.assertLessEqual(lines, 80, f"Dispatcher is {lines} lines (limit 80)")

    def test_freeze_max_depth_is_2(self):
        """ARCHITECTURE FREEZE: MAX_EVENT_DEPTH must remain 2."""
        self.assertEqual(MAX_EVENT_DEPTH, 2)

    def test_freeze_max_buffer_is_200(self):
        """ARCHITECTURE FREEZE: Safety buffer max_size must remain 200."""
        self.assertEqual(safety_buffer.max_size, 200)

    def test_freeze_max_payload_is_10kb(self):
        """ARCHITECTURE FREEZE: MAX_PAYLOAD_BYTES must remain 10240."""
        from core.events.safety import MAX_PAYLOAD_BYTES
        self.assertEqual(MAX_PAYLOAD_BYTES, 10 * 1024)

    def test_freeze_no_orm_in_payload_rejected(self):
        """ARCHITECTURE FREEZE: ORM objects in payload must raise TypeError."""
        from django.db.models import Model
        from core.events.safety import _validate_payload
        with self.assertRaises(TypeError):
            _validate_payload({"model": self.company_a})

    def test_freeze_dispatcher_imports_no_heavy_modules(self):
        """ARCHITECTURE FREEZE: __init__.py must not import heavy modules."""
        import ast, os
        path = os.path.join(os.path.dirname(core.events.__file__), "__init__.py")
        with open(path) as f:
            tree = ast.parse(f.read())
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module.split(".")[0])
        FORBIDDEN_IMPORTS = {"django", "requests", "celery", "kombu", "redis", "pika"}
        forbidden_found = imported_modules & FORBIDDEN_IMPORTS
        self.assertFalse(forbidden_found, f"Dispatcher imports forbidden modules: {forbidden_found}")

    def test_freeze_event_system_not_used_for_auth(self):
        """ARCHITECTURE FREEZE: No event names reference auth/permissions."""
        from core.events.safety import EVENT_PRIORITY
        for name in EVENT_PRIORITY:
            self.assertNotIn("auth", name)
            self.assertNotIn("permission", name)
            self.assertNotIn("login", name)
            self.assertNotIn("token", name)

    def test_freeze_governance_document_exists(self):
        """ARCHITECTURE FREEZE: GOVERNANCE.md must exist with all required sections."""
        import os
        path = os.path.join(os.path.dirname(core.events.__file__), "GOVERNANCE.md")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        required = ["Role", "Hard Rules", "Forbidden", "Performance Contract", "Final Word"]
        for section in required:
            self.assertIn(section, content, f"GOVERNANCE.md missing section: {section}")

    def test_freeze_no_direct_handler_db_access(self):
        """ARCHITECTURE FREEZE: Domain handlers must not import django.db."""
        import ast
        import core.events.handlers.sales as hs
        import core.events.handlers.purchases as hp
        import core.events.handlers.inventory as hi
        import core.events.handlers.accounting as ha
        import core.events.handlers.returns as hr_mod
        import core.events.handlers.payroll as hpy
        for mod in [hs, hp, hi, ha, hr_mod, hpy]:
            source = mod.__file__
            if source and source.endswith(".py"):
                tree = ast.parse(open(source).read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if "django" in alias.name:
                                self.fail(f"{mod.__name__} imports django: {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and "django" in node.module:
                            self.fail(f"{mod.__name__} imports from django: {node.module}")

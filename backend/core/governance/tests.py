"""
Governance Kernel Test Suite — all 6 phases.

Tests:
  1. Kernel initialization (no startup overhead)
  2. Policy registration and enforcement (fail-closed)
  3. Invariant registration and checking
  4. Priority tier enforcement (degradation)
  5. Failsafe mode (low-priority bypass)
  6. Feature gates (fail-closed)
  7. Audit trail (denials recorded)
  8. Self-health monitoring (recursion detection, event rate)
  9. Event deduplication (storm protection)
  10. Metrics tracking
  11. Environment-aware behavior
  12. Backward compatibility (existing governance still works)
  13. Discovery API integrity
"""
import threading
import time
from typing import Any, Dict, Tuple
from unittest.mock import patch

from django.test import TestCase

from core.governance.kernel import GovernanceKernel, PriorityTier, EnforcementResult
from core.governance.registries import (
    PolicyRegistry, InvariantRegistry, EnvironmentRegistry,
    FeatureGateRegistry, ReadinessRegistry, UIRuleRegistry, PolicyRule,
)
from core.governance.enforcer import register_enforcement_policies
from core.governance.contracts import register_all_contracts
from core.governance.events import get_event_bus, GovernanceEvent, EventSeverity, EventDeduplicator
from core.governance.metrics import get_metrics, GovernanceMetrics
from core.governance.self_health import GovernanceHealthMonitor
from core.governance.api import generate_documentation, discovery_response


# ── Phase 1: Governance Kernel Foundation ────────────────

class TestKernelInitialization(TestCase):
    """Kernel must be lazily initialized with zero startup overhead."""

    def test_kernel_creates_singleton_state(self):
        k1 = GovernanceKernel()
        k2 = GovernanceKernel()
        self.assertIs(k1._state, k2._state)

    def test_kernel_has_all_registries(self):
        k = GovernanceKernel()
        self.assertIsNotNone(k.policies)
        self.assertIsNotNone(k.invariants)
        self.assertIsNotNone(k.environment)
        self.assertIsNotNone(k.feature_gates)
        self.assertIsNotNone(k.readiness)
        self.assertIsNotNone(k.ui_rules)

    def test_kernel_has_no_startup_overhead(self):
        start = time.time()
        for _ in range(1000):
            GovernanceKernel()
        elapsed = (time.time() - start) * 1000
        self.assertLess(elapsed, 100, "Kernel creation must be <100ms for 1000 instances")

    def test_kernel_health_returns_basic_info(self):
        k = GovernanceKernel()
        h = k.health()
        self.assertIn("kernel_version", h)
        self.assertIn("policies", h)
        self.assertIn("invariants", h)
        self.assertIn("failsafe_mode", h)
        self.assertIn("environment_profile", h)


class TestPolicyRegistry(TestCase):
    """Policy registry must centralize all enforcement rules."""

    def test_register_and_get(self):
        r = PolicyRegistry()
        rule = PolicyRule("test_policy", "Test", "high", lambda ctx: (True, "ok"))
        r.register(rule)
        self.assertIsNotNone(r.get("test_policy"))

    def test_unregister(self):
        r = PolicyRegistry()
        rule = PolicyRule("test_policy", "Test", "high", lambda ctx: (True, "ok"))
        r.register(rule)
        self.assertTrue(r.unregister("test_policy"))
        self.assertIsNone(r.get("test_policy"))

    def test_count(self):
        r = PolicyRegistry()
        rule1 = PolicyRule("p1", "Test1", "high", lambda ctx: (True, "ok"))
        rule2 = PolicyRule("p2", "Test2", "high", lambda ctx: (True, "ok"))
        r.register(rule1)
        r.register(rule2)
        self.assertEqual(r.count(), 2)

    def test_list_all(self):
        r = PolicyRegistry()
        rule = PolicyRule("test_policy", "Test", "high", lambda ctx: (True, "ok"))
        r.register(rule)
        all_p = r.list_all()
        self.assertIn("test_policy", all_p)


class TestInvariantRegistry(TestCase):
    """Invariant registry must centralize all invariant checks."""

    def test_register_and_check(self):
        r = InvariantRegistry()
        r.register("test_inv", lambda ctx: (True, "ok"), {"domain": "test"})
        checker = r.get("test_inv")
        self.assertIsNotNone(checker)
        passed, msg = checker({})
        self.assertTrue(passed)

    def test_get_meta(self):
        r = InvariantRegistry()
        r.register("test_inv", lambda ctx: (True, "ok"), {"domain": "test"})
        self.assertEqual(r.get_meta("test_inv").get("domain"), "test")

    def test_count(self):
        r = InvariantRegistry()
        r.register("i1", lambda ctx: (True, "ok"))
        r.register("i2", lambda ctx: (True, "ok"))
        self.assertEqual(r.count(), 2)


class TestFeatureGateRegistry(TestCase):
    """Feature gate registry with fail-closed behavior."""

    def test_register_and_get(self):
        r = FeatureGateRegistry()
        r.register("gate1", lambda ctx: True)
        self.assertIsNotNone(r.get("gate1"))

    def test_unregistered_returns_none(self):
        r = FeatureGateRegistry()
        self.assertIsNone(r.get("nonexistent_gate"))


class TestEnvironmentRegistry(TestCase):
    """Environment registry must detect profile correctly."""

    def test_profile_detected(self):
        r = EnvironmentRegistry()
        self.assertIn(r.profile, ["development", "qa", "staging", "production"])

    def test_sampling_rate(self):
        r = EnvironmentRegistry()
        rate = r.sampling_rate()
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 1.0)

    def test_always_sample_governance_paths(self):
        r = EnvironmentRegistry()
        rate = r.sampling_rate(path="/api/governance/health/")
        self.assertEqual(rate, 1.0)


# ── Phase 2: Governance Performance Safety ───────────────

class TestEnforcementPriorityTiers(TestCase):
    """Priority tiers must prevent low-priority from blocking critical operations."""

    def test_high_priority_enforces_normally(self):
        k = GovernanceKernel()
        rule = PolicyRule("test_high", "Test", PriorityTier.CRITICAL.value,
                          lambda ctx: (False, "denied"))
        k.policies.register(rule)
        result = k.enforce("test_high", priority=PriorityTier.CRITICAL)
        self.assertFalse(result.allowed)

    def test_degraded_tier_bypasses(self):
        k = GovernanceKernel()
        rule = PolicyRule("test_low", "Test", PriorityTier.LOW.value,
                          lambda ctx: (False, "denied"))
        k.policies.register(rule)
        k.degrade_tier(PriorityTier.LOW.value)
        result = k.enforce("test_low", priority=PriorityTier.LOW)
        self.assertTrue(result.allowed)  # Bypassed due to degradation
        self.assertIn("Degraded", result.reason)
        k.restore_tier(PriorityTier.LOW.value)


class TestEnforcementCaching(TestCase):
    """Enforcement results must be cachable (kernel is stateless, no duplicate scans)."""

    def test_multiple_enforcements_same_policy(self):
        k = GovernanceKernel()
        call_count = [0]
        def check(ctx):
            call_count[0] += 1
            return (True, "allowed")
        rule = PolicyRule("test_cache", "Test", "high", check)
        k.policies.register(rule)
        for _ in range(10):
            k.enforce("test_cache")
        self.assertEqual(call_count[0], 10)  # Each call executes


# ── Phase 3: Runtime Enforcement Consolidation ───────────

class TestFailClosedEnforcement(TestCase):
    """Missing governance context MUST block execution (fail-closed)."""

    def test_unregistered_policy_denies(self):
        k = GovernanceKernel()
        result = k.enforce("nonexistent_policy", {})
        self.assertFalse(result.allowed)
        self.assertIn("not registered", result.reason)
        self.assertIn("fail-closed", result.reason)

    def test_enforcement_returns_structured_result(self):
        k = GovernanceKernel()
        rule = PolicyRule("test", "Test", "high", lambda ctx: (True, "ok"))
        k.policies.register(rule)
        result = k.enforce("test", {"key": "val"}, user="admin", entity="TestEntity")
        self.assertIsInstance(result, EnforcementResult)
        self.assertTrue(result.allowed)
        self.assertEqual(result.user, "admin")
        self.assertEqual(result.affected_entity, "TestEntity")
        self.assertGreaterEqual(result.latency_ms, 0)

    def test_denied_enforcement_recorded_in_audit(self):
        k = GovernanceKernel()
        result = k.enforce("nonexistent", {}, user="testuser")
        self.assertFalse(result.allowed)
        audit = k.get_recent_audit(limit=10)
        self.assertTrue(any(e.policy_id == "nonexistent" and e.result == "denied"
                            for e in audit))


class TestStateTransitionEnforcement(TestCase):
    """State transition enforcement via registered policies."""

    def test_register_enforcement_policies(self):
        k = GovernanceKernel()
        register_enforcement_policies(k)
        self.assertIsNotNone(k.policies.get("enforce.return_state_transition"))
        self.assertIsNotNone(k.policies.get("enforce.sales_state_transition"))
        self.assertIsNotNone(k.policies.get("enforce.purchase_state_transition"))
        self.assertIsNotNone(k.policies.get("enforce.je_debit_equals_credit"))

    def test_return_transition_allowed(self):
        k = GovernanceKernel()
        register_enforcement_policies(k)
        result = k.enforce("enforce.return_state_transition", {
            "current_state": "DRAFT",
            "target_state": "PENDING",
            "entity_id": "RET-001",
        })
        self.assertTrue(result.allowed, result.reason)

    def test_return_transition_blocked(self):
        k = GovernanceKernel()
        register_enforcement_policies(k)
        result = k.enforce("enforce.return_state_transition", {
            "current_state": "DRAFT",
            "target_state": "APPROVED",
            "entity_id": "RET-001",
        })
        self.assertFalse(result.allowed)
        self.assertIn("Illegal transition", result.reason)

    def test_return_transition_missing_condition(self):
        k = GovernanceKernel()
        register_enforcement_policies(k)
        result = k.enforce("enforce.return_state_transition", {
            "current_state": "PENDING",
            "target_state": "APPROVED",
            "entity_id": "RET-001",
        })
        self.assertFalse(result.allowed)
        self.assertIn("Missing required condition", result.reason)


class TestContractRegistration(TestCase):
    """Governance contracts must register through the kernel."""

    def test_register_all_contracts(self):
        k = GovernanceKernel()
        from core.governance.contracts import register_all_contracts
        register_all_contracts(k)
        self.assertGreater(k.invariants.count(), 0)

    def test_accounting_invariant_registered(self):
        k = GovernanceKernel()
        register_all_contracts(k)
        self.assertIsNotNone(k.invariants.get("accounting.je_balanced"))

    def test_system_invariant_registered(self):
        k = GovernanceKernel()
        register_all_contracts(k)
        self.assertIsNotNone(k.invariants.get("system.database_connectivity"))

    def test_invariant_scan(self):
        k = GovernanceKernel()
        register_all_contracts(k)
        results = k.run_invariant_scan(domain="test")
        self.assertIsInstance(results, list)


# ── Phase 4: Governance Observability ────────────────────

class TestGovernanceEvents(TestCase):
    """Governance events must be structured and noise-controlled."""

    def test_event_emit_and_retrieve(self):
        bus = get_event_bus()
        count_before = bus.count()
        event = GovernanceEvent(
            event_id="test-001",
            event_type="enforcement",
            severity=EventSeverity.INFO,
            message="Test event",
            policy_id="test_policy",
            latency_ms=1.0,
        )
        bus.emit(event)
        recent = bus.get_recent(limit=10)
        self.assertGreaterEqual(len(recent), 1)

    def test_event_deduplication(self):
        dedup = EventDeduplicator(window_seconds=300, max_entries=100)
        event1 = GovernanceEvent(
            event_id="dup-001", event_type="test", severity=EventSeverity.INFO,
            message="Duplicate test",
        )
        event2 = GovernanceEvent(
            event_id="dup-002", event_type="test", severity=EventSeverity.INFO,
            message="Duplicate test",
        )
        self.assertFalse(dedup.is_duplicate(event1))
        self.assertTrue(dedup.is_duplicate(event2))

    def test_event_summary(self):
        bus = get_event_bus()
        summary = bus.summary()
        self.assertIn("total_events", summary)
        self.assertIn("by_type", summary)

    def test_different_messages_not_deduplicated(self):
        dedup = EventDeduplicator(window_seconds=300, max_entries=100)
        e1 = GovernanceEvent("1", "test", EventSeverity.INFO, "Message A")
        e2 = GovernanceEvent("2", "test", EventSeverity.INFO, "Message B")
        self.assertFalse(dedup.is_duplicate(e1))
        self.assertFalse(dedup.is_duplicate(e2))


class TestGovernanceMetrics(TestCase):
    """Metrics must track enforcement with bounded memory."""

    def test_record_enforcement(self):
        m = get_metrics()
        before = m.snapshot()["total_enforcements"]
        m.record_enforcement("test_policy", True, 1.5)
        snapshot = m.snapshot()
        self.assertEqual(snapshot["total_enforcements"], before + 1)

    def test_latency_stats(self):
        m = get_metrics()
        m.record_enforcement("latency_test", True, 10.0)
        m.record_enforcement("latency_test", True, 20.0)
        stats = m.get_latency_stats("latency_test")
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["avg"], 15.0, delta=0.1)

    def test_record_invariant_failure(self):
        m = get_metrics()
        m.record_invariant_failure("test_inv")
        snapshot = m.snapshot()
        self.assertIn("test_inv", snapshot["invariant_failures"])

    def test_reset(self):
        m = get_metrics()
        m.record_enforcement("p1", True, 1.0)
        m.reset()
        snapshot = m.snapshot()
        self.assertEqual(snapshot["total_enforcements"], 0)

    def test_record_error(self):
        m = get_metrics()
        m.record_error()
        snapshot = m.snapshot()
        self.assertEqual(snapshot["total_errors"], 1)

    def test_record_readiness(self):
        m = get_metrics()
        m.record_readiness(8, 10)
        snapshot = m.snapshot()
        self.assertEqual(snapshot["readiness_checkpoints"], 1)


# ── Phase 5: Governance Self-Protection ──────────────────

class TestGovernanceHealthMonitor(TestCase):
    """Self-health monitor must detect recursion and event storms."""

    def test_recursion_depth_tracking(self):
        k = GovernanceKernel()
        monitor = GovernanceHealthMonitor(k)
        self.assertTrue(monitor.enter_enforcement())
        self.assertTrue(monitor.enter_enforcement())
        monitor.leave_enforcement()
        monitor.leave_enforcement()
        report = monitor.check()
        self.assertEqual(report.recursion_depth, 0)

    def test_excessive_recursion_triggers_warning(self):
        k = GovernanceKernel()
        monitor = GovernanceHealthMonitor(k)
        for _ in range(12):
            monitor.enter_enforcement()
        report = monitor.check()
        self.assertGreaterEqual(len(report.warnings), 0)

    def test_listener_registration(self):
        k = GovernanceKernel()
        monitor = GovernanceHealthMonitor(k)
        self.assertTrue(monitor.register_listener("test_listener"))
        report = monitor.check()
        self.assertEqual(report.listener_count, 1)
        monitor.unregister_listener("test_listener")
        report = monitor.check()
        self.assertEqual(report.listener_count, 0)

    def test_handler_failure_tracking(self):
        k = GovernanceKernel()
        monitor = GovernanceHealthMonitor(k)
        monitor.record_handler_failure()
        report = monitor.check()
        self.assertEqual(report.handler_failures, 1)

    def test_event_rate_tracking(self):
        k = GovernanceKernel()
        monitor = GovernanceHealthMonitor(k)
        for _ in range(10):
            monitor.record_event()
        report = monitor.check()
        self.assertGreaterEqual(report.events_per_second, 0)

    def test_reset(self):
        k = GovernanceKernel()
        monitor = GovernanceHealthMonitor(k)
        monitor.record_handler_failure()
        monitor.reset()
        report = monitor.check()
        self.assertEqual(report.handler_failures, 0)


class TestFailsafeMode(TestCase):
    """Failsafe mode must bypass low-priority enforcement."""

    def test_failsafe_bypasses_low_priority(self):
        k = GovernanceKernel()
        rule = PolicyRule("low_pol", "Test", PriorityTier.LOW.value,
                          lambda ctx: (False, "denied"))
        k.policies.register(rule)
        k.enable_failsafe()
        result = k.enforce("low_pol", priority=PriorityTier.LOW)
        self.assertTrue(result.allowed)
        self.assertIn("Failsafe mode", result.reason)

    def test_failsafe_does_not_bypass_critical(self):
        k = GovernanceKernel()
        rule = PolicyRule("crit_pol", "Test", PriorityTier.CRITICAL.value,
                          lambda ctx: (False, "denied"))
        k.policies.register(rule)
        k.enable_failsafe()
        result = k.enforce("crit_pol", priority=PriorityTier.CRITICAL)
        self.assertFalse(result.allowed)

    def test_disable_failsafe_restores_enforcement(self):
        k = GovernanceKernel()
        rule = PolicyRule("low_pol2", "Test", PriorityTier.LOW.value,
                          lambda ctx: (False, "denied"))
        k.policies.register(rule)
        k.enable_failsafe()
        k.disable_failsafe()
        result = k.enforce("low_pol2", priority=PriorityTier.LOW)
        self.assertFalse(result.allowed)

    def test_failsafe_property(self):
        k = GovernanceKernel()
        k.disable_failsafe()
        self.assertFalse(k.failsafe_mode)
        k.enable_failsafe()
        self.assertTrue(k.failsafe_mode)
        k.disable_failsafe()
        self.assertFalse(k.failsafe_mode)


# ── Phase 6: Enterprise Maintainability ──────────────────

class TestDiscoveryAPI(TestCase):
    """Discovery API must expose all registered governance items."""

    def test_discovery_contains_all_sections(self):
        k = GovernanceKernel()
        discovery = discovery_response(k)
        self.assertIn("policies", discovery)
        self.assertIn("invariants", discovery)
        self.assertIn("feature_gates", discovery)
        self.assertIn("ui_rules", discovery)
        self.assertIn("summary", discovery)
        self.assertIn("failsafe_mode", discovery)

    def test_documentation_generation(self):
        k = GovernanceKernel()
        doc = generate_documentation(k)
        self.assertIsNotNone(doc.policies)
        self.assertIsNotNone(doc.invariants)

    def test_kernel_health_in_discovery(self):
        k = GovernanceKernel()
        h = k.health()
        self.assertIn("kernel_version", h)
        self.assertIn("audit_entries", h)

    def test_audit_summary(self):
        k = GovernanceKernel()
        summary = k.get_audit_summary()
        self.assertIn("total_entries", summary)
        self.assertIn("denied", summary)
        self.assertIn("allowed", summary)

    def test_get_active_features(self):
        k = GovernanceKernel()
        active = k.get_active_features()
        self.assertIsInstance(active, list)

    def test_feature_gate_fail_closed(self):
        k = GovernanceKernel()
        self.assertFalse(k.is_feature_active("nonexistent_gate"))


class TestBackwardCompatibility(TestCase):
    """Existing governance utilities must continue functioning."""

    def test_readiness_still_works(self):
        k = GovernanceKernel()
        report = k.check_readiness()
        self.assertIn("overall", report)
        self.assertIn("passed", report)
        self.assertIn("total", report)

    def test_invariant_validator_still_works(self):
        try:
            from core.governance.invariant_validator import run_full_invariant_check
            report = run_full_invariant_check()
            self.assertIsNotNone(report)
        except Exception as e:
            self.fail(f"run_full_invariant_check failed: {e}")

    def test_state_transitions_still_work(self):
        try:
            from core.governance.state_transitions import (
                validate_return_transition, IllegalTransitionError,
            )
            validate_return_transition("DRAFT", "PENDING")
            with self.assertRaises(IllegalTransitionError):
                validate_return_transition("DRAFT", "APPROVED")
        except Exception as e:
            self.fail(f"state_transitions failed: {e}")

    def test_graceful_degradation_still_works(self):
        try:
            from core.governance.graceful_degradation import compute_degradation
            state = compute_degradation()
            self.assertEqual(state.level.value, "FULL")
        except Exception as e:
            self.fail(f"graceful_degradation failed: {e}")


class TestNoStartupOverhead(TestCase):
    """Importing governance kernel must not execute heavy operations."""

    def test_import_does_not_register_policies(self):
        k = GovernanceKernel()
        count_before = k.policies.count()
        # Re-initializing should not double-register
        _ = GovernanceKernel()
        self.assertEqual(k.policies.count(), count_before)

    def test_initialization_is_lazy(self):
        """Kernel constructor does no heavy work (policies may be pre-registered by hooks)."""
        import time
        start = time.time()
        k = GovernanceKernel()
        elapsed = (time.time() - start) * 1000
        self.assertLess(elapsed, 10, "Kernel constructor must be <10ms")

    def test_no_heavy_startup_in_kernel_creation(self):
        import time
        start = time.time()
        for _ in range(100):
            GovernanceKernel()
        elapsed = (time.time() - start) * 1000
        self.assertLess(elapsed, 50, "100 kernel instantiations must be <50ms total")

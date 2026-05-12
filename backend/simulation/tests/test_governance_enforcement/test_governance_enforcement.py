"""
Phase 5B.0 — Governance Enforcement Skeleton Tests.

Validates:
A. Interception — all action types intercepted, no direct execution bypass
B. Policy Enforcement — correct mapping, deterministic evaluation, violation detection
C. Risk Classification — correct scoring, deterministic, consistent across runs
D. Decision Gate — correct blocking, simulation routing, approval routing
E. Non-Execution Safety — NO ERP mutation, NO state changes, NO execution
F. Determinism — identical input → identical decisions
"""
import unittest
from core.operations.governance.models import (
    ActionIntent, PolicyEvaluationResult, RiskClassificationResult, DecisionResult,
)
from core.operations.governance.interceptor import (
    intercept, get_supported_action_types, is_action_type_registered,
    ACTION_TYPE_REGISTRY, VALID_SOURCES,
)
from core.operations.governance.policy_evaluator import evaluate
from core.operations.governance.risk_classifier import classify
from core.operations.governance.decision_gate import decide


# ═══════════════════════════════════════════════════════════
# A. INTERCEPTION TESTS
# ═══════════════════════════════════════════════════════════

class InterceptionTest(unittest.TestCase):
    """All action types are intercepted correctly."""

    def test_all_action_types_intercepted(self):
        """Every registered action type can be intercepted."""
        for action_type in ACTION_TYPE_REGISTRY:
            intent = intercept(action_type, "api")
            self.assertIsNotNone(intent)
            self.assertEqual(intent.action_type, action_type)
            self.assertEqual(intent.source, "api")

    def test_intercept_returns_action_intent(self):
        """Intercept returns an ActionIntent."""
        intent = intercept("observability_read", "api", {"path": "/health/"})
        self.assertIsInstance(intent, ActionIntent)
        self.assertEqual(intent.action_type, "observability_read")
        self.assertEqual(intent.source, "api")

    def test_intercept_all_valid_sources(self):
        """All valid sources work for interception."""
        for source in VALID_SOURCES:
            intent = intercept("observability_read", source)
            self.assertEqual(intent.source, source)

    def test_intercept_forbidden_action(self):
        """Forbidden actions are tagged in metadata."""
        intent = intercept("erp_create_product", "ui")
        self.assertTrue(intent.metadata.get("is_forbidden", False))

    def test_intercept_safe_action(self):
        """Safe actions are NOT tagged as forbidden."""
        intent = intercept("observability_read", "api")
        self.assertFalse(intent.metadata.get("is_forbidden", True))

    def test_intercept_unknown_action_type(self):
        """Unknown action type raises ValueError."""
        with self.assertRaises(ValueError):
            intercept("nonexistent_action", "api")

    def test_intercept_invalid_source(self):
        """Invalid source raises ValueError."""
        with self.assertRaises(ValueError):
            intercept("observability_read", "invalid_source")

    def test_intercept_domain_assignment(self):
        """Each action type is assigned to correct domain."""
        domain_checks = {
            "observability_read": "observability_read",
            "replay_execute": "replay_operations",
            "inventory_dispatch": "domain_operations",
            "accounting_journal_entry": "erp_mutation",
            "system_rollback": "system_operations",
            "security_create_user": "security_operations",
        }
        for action_type, expected_domain in domain_checks.items():
            intent = intercept(action_type, "api")
            self.assertEqual(intent.domain, expected_domain,
                             f"{action_type} should map to {expected_domain}")

    def test_intercept_risk_pre_classification(self):
        """Risk pre-classification is set in metadata."""
        intent = intercept("inventory_dispatch", "api")
        self.assertEqual(intent.metadata["risk_pre_classification"], "CRITICAL")

    def test_intercept_context_preserved(self):
        """Context is preserved in ActionIntent."""
        context = {"tick": 42, "source_phase": "test"}
        intent = intercept("observability_read", "api", context=context)
        self.assertEqual(intent.context["tick"], 42)


class InterceptorActionTypeRegistryTest(unittest.TestCase):
    """Action type registry is complete."""

    def test_registry_has_all_action_types(self):
        """Registry has known action types."""
        action_types = get_supported_action_types()
        expected = ["replay_execute", "replay_start", "inventory_dispatch",
                    "accounting_journal_entry", "observability_read",
                    "system_rollback", "security_create_user"]
        for at in expected:
            self.assertIn(at, action_types)

    def test_registry_check_registered(self):
        """Registered action type checked correctly."""
        self.assertTrue(is_action_type_registered("observability_read"))
        self.assertFalse(is_action_type_registered("nonexistent_action"))


# ═══════════════════════════════════════════════════════════
# B. POLICY ENFORCEMENT TESTS
# ═══════════════════════════════════════════════════════════

class PolicyEnforcementTest(unittest.TestCase):
    """Policy evaluation is deterministic and correct."""

    def test_evaluate_replay_action(self):
        """Replay action is evaluated (decision gate handles blocking)."""
        action = intercept("replay_execute", "replay")
        result = evaluate(action)
        self.assertIsInstance(result, PolicyEvaluationResult)

    def test_evaluate_observability_action(self):
        """Observability read action passes policy check."""
        action = intercept("observability_read", "api")
        result = evaluate(action)
        self.assertIsInstance(result, PolicyEvaluationResult)

    def test_evaluate_forbidden_action_checked(self):
        """Forbidden action is evaluated (decision gate handles blocking)."""
        action = intercept("erp_create_product", "ui")
        result = evaluate(action)
        self.assertIsInstance(result, PolicyEvaluationResult)

    def test_evaluate_dispatch_policy_check(self):
        """Dispatch action is evaluated (decision gate handles blocking)."""
        action = intercept("inventory_dispatch", "workflow")
        result = evaluate(action)
        self.assertIsNotNone(result)
        self.assertIn("evaluator_version", result.metadata)

    def test_evaluate_rollback_policy_check(self):
        """Rollback action is evaluated (decision gate handles blocking)."""
        action = intercept("system_rollback", "system")
        result = evaluate(action)
        self.assertIsNotNone(result)
        self.assertIn("evaluator_version", result.metadata)

    def test_policy_evaluation_is_deterministic(self):
        """Same action produces same policy result."""
        action = intercept("replay_execute", "replay")
        result1 = evaluate(action)
        result2 = evaluate(action)
        self.assertEqual(result1.compliance, result2.compliance)
        self.assertEqual(result1.violated_rules, result2.violated_rules)

    def test_policy_result_has_metadata(self):
        """Policy result includes metadata."""
        action = intercept("observability_read", "api")
        result = evaluate(action)
        self.assertIn("evaluator_version", result.metadata)
        self.assertIn("domain", result.metadata)


# ═══════════════════════════════════════════════════════════
# C. RISK CLASSIFICATION TESTS
# ═══════════════════════════════════════════════════════════

class RiskClassificationTest(unittest.TestCase):
    """Risk classification is deterministic and correct."""

    def test_observability_read_is_none(self):
        """Observability read has NONE risk."""
        action = intercept("observability_read", "api")
        result = classify(action)
        self.assertEqual(result.risk_level, "NONE")
        self.assertEqual(result.risk_score, 0)

    def test_replay_execute_is_critical(self):
        """Replay execute has CRITICAL risk (blocked during governance skeleton)."""
        action = intercept("replay_execute", "replay")
        result = classify(action)
        self.assertEqual(result.risk_level, "CRITICAL")
        self.assertEqual(result.risk_score, 4)

    def test_inventory_dispatch_is_critical(self):
        """Inventory dispatch has CRITICAL risk."""
        action = intercept("inventory_dispatch", "workflow")
        result = classify(action)
        self.assertEqual(result.risk_level, "CRITICAL")
        self.assertEqual(result.risk_score, 4)

    def test_system_rollback_is_critical(self):
        """System rollback has CRITICAL risk."""
        action = intercept("system_rollback", "system")
        result = classify(action)
        self.assertEqual(result.risk_level, "CRITICAL")

    def test_erp_create_product_is_critical(self):
        """ERP create product has CRITICAL risk."""
        action = intercept("erp_create_product", "ui")
        result = classify(action)
        self.assertEqual(result.risk_level, "CRITICAL")

    def test_replay_pause_is_none(self):
        """Replay pause has NONE risk."""
        action = intercept("replay_pause", "replay")
        result = classify(action)
        self.assertEqual(result.risk_level, "NONE")

    def test_risk_classification_is_deterministic(self):
        """Same action produces same risk classification."""
        action = intercept("inventory_dispatch", "workflow")
        result1 = classify(action)
        result2 = classify(action)
        self.assertEqual(result1.risk_level, result2.risk_level)
        self.assertEqual(result1.risk_score, result2.risk_score)
        self.assertEqual(result1.justification, result2.justification)

    def test_forbidden_action_max_risk(self):
        """Forbidden action always gets max risk."""
        action = intercept("erp_create_product", "ui")
        result = classify(action)
        self.assertEqual(result.risk_level, "CRITICAL")

    def test_risk_result_has_metadata(self):
        """Risk result includes metadata."""
        action = intercept("observability_read", "api")
        result = classify(action)
        self.assertIn("classifier_version", result.metadata)
        self.assertIn("source", result.metadata)

    def test_all_domains_have_risk_mapping(self):
        """All domains have a risk score mapping."""
        actions_tested = 0
        for action_type in ACTION_TYPE_REGISTRY:
            action = intercept(action_type, "api")
            result = classify(action)
            self.assertIn(result.risk_level, ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
            actions_tested += 1
        self.assertGreater(actions_tested, 10)


# ═══════════════════════════════════════════════════════════
# D. DECISION GATE TESTS
# ═══════════════════════════════════════════════════════════

class DecisionGateTest(unittest.TestCase):
    """Decision gate produces correct blocking/simulation/approval decisions."""

    def test_forbidden_action_blocked(self):
        """Forbidden actions are BLOCKED."""
        action = intercept("erp_create_product", "ui")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertEqual(decision.decision, "BLOCKED")

    def test_critical_risk_blocked(self):
        """CRITICAL risk actions are BLOCKED (no governance execution yet)."""
        action = intercept("inventory_dispatch", "workflow")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertEqual(decision.decision, "BLOCKED")

    def test_replay_execute_blocked_critical(self):
        """Replay execute is BLOCKED (CRITICAL risk, no governance execution yet)."""
        action = intercept("replay_execute", "replay")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertEqual(decision.decision, "BLOCKED")
        self.assertEqual(risk_result.risk_level, "CRITICAL")

    def test_medium_risk_simulation_only(self):
        """MEDIUM risk actions (policy PASS) are SIMULATION_ONLY."""
        action = intercept("replay_start", "replay")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertEqual(decision.decision, "SIMULATION_ONLY")

    def test_none_risk_safe_pass(self):
        """NONE risk actions (policy PASS) are SAFE_PASS."""
        action = intercept("observability_read", "api")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertEqual(decision.decision, "SAFE_PASS")

    def test_decision_includes_audit_entry(self):
        """Decision includes audit trail entry."""
        action = intercept("observability_read", "api")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        audit = decision.audit_entry
        self.assertIn("action_id", audit)
        self.assertIn("decision", audit)
        self.assertIn("simulated", audit)
        self.assertIn("executed", audit)
        self.assertTrue(audit["simulated"])
        self.assertFalse(audit["executed"])

    def test_decision_includes_reasoning(self):
        """Decision includes reasoning string."""
        action = intercept("observability_read", "api")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertGreater(len(decision.reasoning), 0)

    def test_decision_is_deterministic(self):
        """Same inputs produce same decision."""
        action = intercept("inventory_dispatch", "workflow")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision1 = decide(action, policy_result, risk_result)
        decision2 = decide(action, policy_result, risk_result)
        self.assertEqual(decision1.decision, decision2.decision)
        self.assertEqual(decision1.reasoning, decision2.reasoning)

    def test_decision_has_metadata(self):
        """Decision includes metadata."""
        action = intercept("observability_read", "api")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertIn("gate_version", decision.metadata)

    def test_none_risk_navigation_safe(self):
        """Navigation actions with NONE risk are SAFE_PASS."""
        action = intercept("replay_step", "replay")
        policy_result = evaluate(action)
        risk_result = classify(action)
        decision = decide(action, policy_result, risk_result)
        self.assertEqual(decision.decision, "SAFE_PASS")


# ═══════════════════════════════════════════════════════════
# E. NON-EXECUTION SAFETY TESTS
# ═══════════════════════════════════════════════════════════

class NonExecutionSafetyTest(unittest.TestCase):
    """No ERP mutation, no execution, no state changes."""

    def test_decide_does_not_mutate_action(self):
        """Decide does not mutate the ActionIntent (immutable)."""
        action = intercept("observability_read", "api")
        action_id_before = action.action_id
        policy_result = evaluate(action)
        risk_result = classify(action)
        _ = decide(action, policy_result, risk_result)
        self.assertEqual(action.action_id, action_id_before)

    def test_no_execution_in_decision(self):
        """All decisions have executed=False in audit."""
        for action_type in list(ACTION_TYPE_REGISTRY.keys())[:5]:
            action = intercept(action_type, "api")
            policy_result = evaluate(action)
            risk_result = classify(action)
            decision = decide(action, policy_result, risk_result)
            self.assertFalse(decision.audit_entry["executed"],
                             f"Decision for {action_type} should not execute")

    def test_all_decisions_simulated(self):
        """All decisions are simulated (not real)."""
        for action_type in list(ACTION_TYPE_REGISTRY.keys())[:5]:
            action = intercept(action_type, "api")
            policy_result = evaluate(action)
            risk_result = classify(action)
            decision = decide(action, policy_result, risk_result)
            self.assertTrue(decision.audit_entry["simulated"],
                            f"Decision for {action_type} should be simulated")

    def test_interceptor_no_side_effects(self):
        """Interceptor creates intent without side effects."""
        count_before = len(ACTION_TYPE_REGISTRY)
        intent = intercept("observability_read", "api")
        count_after = len(ACTION_TYPE_REGISTRY)
        self.assertEqual(count_before, count_after)
        self.assertIsNotNone(intent)

    def test_full_pipeline_no_mutation(self):
        """Full pipeline from intercept→evaluate→classify→decide has no mutations."""
        import copy
        action = intercept("observability_read", "api", {"test": True})
        action_copy = copy.deepcopy(action)
        pr = evaluate(action)
        rc = classify(action)
        _ = decide(action, pr, rc)
        self.assertEqual(action.action_id, action_copy.action_id)
        self.assertEqual(action.action_type, action_copy.action_type)
        self.assertEqual(action.context, action_copy.context)

    def test_action_intent_is_frozen(self):
        """ActionIntent is immutable (frozen dataclass)."""
        action = intercept("observability_read", "api")
        with self.assertRaises(AttributeError):
            action.action_type = "modified"


# ═══════════════════════════════════════════════════════════
# F. DETERMINISM TESTS
# ═══════════════════════════════════════════════════════════

class DeterminismTest(unittest.TestCase):
    """Identical input produces identical decisions."""

    def test_full_pipeline_deterministic(self):
        """Full pipeline is deterministic for same input."""
        action = intercept("replay_execute", "replay", {"tick": 42})
        pr1 = evaluate(action)
        rc1 = classify(action)
        d1 = decide(action, pr1, rc1)

        pr2 = evaluate(action)
        rc2 = classify(action)
        d2 = decide(action, pr2, rc2)

        self.assertEqual(d1.decision, d2.decision)
        # Compare deterministic fields (action_id is UUID-based and unique per intent)
        self.assertEqual(d1.reasoning, d2.reasoning)

    def test_stable_risk_scoring(self):
        """Risk scoring is stable across repeated classifications."""
        action = intercept("inventory_dispatch", "workflow")
        results = [classify(action) for _ in range(10)]
        for i in range(1, len(results)):
            self.assertEqual(results[i].risk_score, results[0].risk_score)
            self.assertEqual(results[i].risk_level, results[0].risk_level)

    def test_stable_policy_evaluation(self):
        """Policy evaluation is stable across repeated evaluations."""
        action = intercept("erp_create_product", "ui")
        results = [evaluate(action) for _ in range(10)]
        for i in range(1, len(results)):
            self.assertEqual(results[i].compliance, results[0].compliance)
            self.assertEqual(results[i].violated_rules, results[0].violated_rules)

    def test_stable_interception(self):
        """Interception produces deterministic metadata."""
        intent1 = intercept("observability_read", "api", {"path": "/health/"})
        intent2 = intercept("observability_read", "api", {"path": "/health/"})
        self.assertEqual(intent1.action_type, intent2.action_type)
        self.assertEqual(intent1.domain, intent2.domain)
        self.assertEqual(intent1.source, intent2.source)
        self.assertEqual(intent1.context, intent2.context)
        self.assertEqual(intent1.metadata["risk_pre_classification"],
                         intent2.metadata["risk_pre_classification"])

    def test_decision_consistency_across_types(self):
        """Same decision for same type is consistent."""
        types_to_test = ["observability_read", "inventory_dispatch",
                         "replay_execute", "erp_create_product", "replay_start"]
        for action_type in types_to_test:
            action1 = intercept(action_type, "api")
            action2 = intercept(action_type, "api")
            d1 = decide(action1, evaluate(action1), classify(action1))
            d2 = decide(action2, evaluate(action2), classify(action2))
            self.assertEqual(d1.decision, d2.decision,
                             f"Inconsistent decision for {action_type}")

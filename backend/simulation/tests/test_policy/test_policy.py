"""
Phase 5A.5.5 — Policy Foundation Tests.

Validates:
- Deterministic policy evaluation
- Immutable authority mapping
- Forbidden-action enforcement
- Escalation-chain consistency
- Risk classification stability
- Policy registry completeness
"""
import unittest
from core.operations.policy.registry import (
    get_policy, get_all_policies, get_policies_by_risk,
    get_policies_by_enforcement, evaluate_policy, ALL_POLICIES,
)
from core.operations.policy.authority import (
    get_authority, get_authorities_for_domain, get_risk_level,
    check_authority_for_action, AUTHORITY_CLASSIFICATIONS, DOMAIN_AUTHORITY_MAP,
)
from core.operations.policy.forbidden import (
    get_forbidden_action, get_all_forbidden_actions,
    get_forbidden_actions_by_domain, get_forbidden_actions_by_risk,
    is_action_forbidden,
)


class DeterministicPolicyEvaluationTest(unittest.TestCase):
    """Policy evaluation is deterministic."""

    def test_get_all_policies_has_policies(self):
        """Registry has policies."""
        policies = get_all_policies()
        self.assertGreater(len(policies), 0)

    def test_policies_have_ids(self):
        """All policies have policy_id."""
        for policy in ALL_POLICIES:
            self.assertIn("policy_id", policy)

    def test_policies_have_risk_levels(self):
        """All policies have risk levels."""
        for policy in ALL_POLICIES:
            self.assertIn("risk_level", policy)

    def test_get_policy_by_id(self):
        """Can retrieve policy by ID."""
        policy = get_policy("REPLAY-001")
        self.assertIsNotNone(policy)
        self.assertEqual(policy["name"], "replay_write_block")

    def test_get_nonexistent_policy(self):
        """Nonexistent policy returns None."""
        self.assertIsNone(get_policy("NONEXISTENT"))

    def test_policies_by_risk_critical(self):
        """CRITICAL risk policies exist."""
        critical = get_policies_by_risk("CRITICAL")
        self.assertGreater(len(critical), 0)

    def test_policies_by_enforcement_always_blocked(self):
        """ALWAYS_BLOCKED enforcement policies exist."""
        blocked = get_policies_by_enforcement("ALWAYS_BLOCKED")
        self.assertGreater(len(blocked), 0)


class ForbiddenActionTest(unittest.TestCase):
    """Forbidden action registry is complete."""

    def test_forbidden_actions_have_ids(self):
        """All forbidden actions have action_id."""
        actions = get_all_forbidden_actions()
        for action in actions:
            self.assertIn("action_id", action)

    def test_forbidden_actions_have_domains(self):
        """All forbidden actions have domain."""
        actions = get_all_forbidden_actions()
        for action in actions:
            self.assertIn("domain", action)

    def test_get_forbidden_action(self):
        """Can retrieve forbidden action by ID."""
        action = get_forbidden_action("ERP-001")
        self.assertIsNotNone(action)
        self.assertEqual(action["action"], "create_inventory_product")

    def test_get_nonexistent_forbidden_action(self):
        """Nonexistent action returns None."""
        self.assertIsNone(get_forbidden_action("NONEXISTENT"))

    def test_is_action_forbidden(self):
        """Known action is identified as forbidden."""
        self.assertTrue(is_action_forbidden("create_inventory_product"))

    def test_is_action_not_forbidden(self):
        """Unknown action is not identified as forbidden."""
        self.assertFalse(is_action_forbidden("harmless_action"))

    def test_forbidden_actions_by_domain(self):
        """Can filter forbidden actions by domain."""
        erp_actions = get_forbidden_actions_by_domain("erp_mutation")
        self.assertGreater(len(erp_actions), 0)

    def test_forbidden_actions_by_risk(self):
        """Can filter forbidden actions by risk level."""
        critical = get_forbidden_actions_by_risk("CRITICAL")
        self.assertGreater(len(critical), 0)


class EscalationChainTest(unittest.TestCase):
    """Escalation chain is consistent."""

    def test_replay_policies_always_blocked(self):
        """Replay policies are all ALWAYS_BLOCKED."""
        replay = get_policies_by_enforcement("ALWAYS_BLOCKED")
        for policy in replay:
            self.assertIn(policy["policy_id"], ["REPLAY-001", "REPLAY-002"])

    def test_evaluate_always_blocked(self):
        """ALWAYS_BLOCKED policy evaluates to not allowed."""
        policy = get_policy("REPLAY-001")
        result = evaluate_policy(policy, {})
        self.assertFalse(result["allowed"])

    def test_evaluate_method_restriction_get(self):
        """METHOD_RESTRICTION allows GET."""
        policy = get_policy("OBS-001")
        result = evaluate_policy(policy, {"method": "GET"})
        self.assertTrue(result["allowed"])

    def test_evaluate_method_restriction_post(self):
        """METHOD_RESTRICTION blocks POST."""
        policy = get_policy("OBS-001")
        result = evaluate_policy(policy, {"method": "POST"})
        self.assertFalse(result["allowed"])


class AuthorityClassificationTest(unittest.TestCase):
    """Authority classifications are complete and consistent."""

    def test_authorities_have_ids(self):
        """All authorities have authority_id."""
        for auth in AUTHORITY_CLASSIFICATIONS:
            self.assertIn("authority_id", auth)

    def test_observability_admin_highest(self):
        """ObservabilityAdmin has MEDIUM risk (highest current)."""
        admin = get_authority("AUTH-OBSERVABILITY-ADMIN")
        self.assertEqual(admin["risk_level"], "MEDIUM")

    def test_observer_lowest(self):
        """Observer has NONE risk (lowest)."""
        observer = get_authority("AUTH-OBSERVER")
        self.assertEqual(observer["risk_level"], "NONE")

    def test_domain_authority_mapping(self):
        """Domain authority map covers all domains."""
        domains = ["observability_read", "replay_view", "forensic_analysis",
                   "audit_log_view", "observability_config", "replay_config"]
        for domain in domains:
            self.assertIn(domain, DOMAIN_AUTHORITY_MAP)

    def test_get_authorities_for_domain(self):
        """Can retrieve authorities for a domain."""
        for_read = get_authorities_for_domain("observability_read")
        self.assertEqual(len(for_read), 4)

    def test_get_nonexistent_authority(self):
        """Nonexistent authority returns None."""
        self.assertIsNone(get_authority("AUTH-NONEXISTENT"))


class RiskClassificationTest(unittest.TestCase):
    """Risk classification is stable."""

    def test_risk_levels_have_scores(self):
        """All risk levels have scores."""
        for level in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            rl = get_risk_level(level)
            self.assertIn("score", rl)
            self.assertGreaterEqual(rl["score"], 0)

    def test_risk_scores_ordered(self):
        """Risk scores increase with severity."""
        scores = [get_risk_level(l)["score"]
                  for l in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
        for i in range(len(scores) - 1):
            self.assertLess(scores[i], scores[i + 1])

    def test_unknown_risk_level(self):
        """Unknown risk level returns score -1."""
        rl = get_risk_level("UNKNOWN")
        self.assertEqual(rl["score"], -1)


class AuthorityDomainMatrixTest(unittest.TestCase):
    """Authority-domain matrix is consistent."""

    def test_check_authority_for_known_action(self):
        """Known authority-domain pairing succeeds."""
        result = check_authority_for_action("AUTH-OBSERVER", "observability_read")
        self.assertTrue(result["allowed"])

    def test_check_authority_for_unknown_action(self):
        """Known authority for unknown domain fails."""
        result = check_authority_for_action("AUTH-OBSERVER", "governance_execution")
        self.assertFalse(result["allowed"])

    def test_check_unknown_authority(self):
        """Unknown authority fails."""
        result = check_authority_for_action("AUTH-NONEXISTENT", "observability_read")
        self.assertFalse(result["allowed"])

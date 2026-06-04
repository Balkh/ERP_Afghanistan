"""
Phase 5B.1 (v2.0 Hardened) — Simulation Sandbox Tests.

Validates the hardened architecture invariants:
A. Simulation Plan Builder — Governance→Plan, deterministic, no pseudo-execution
B. Simulation Engine — No side effects, no mutation, bounded output
C. Impact Analysis — Descriptive only, no decision coupling, deterministic
D. Simulation Trace — Immutable, bounded, forensic-only
E. Full Pipeline Integration with 5B.0 — All layers separated, no execution
"""
import unittest
from collections import deque
from core.operations.execution.models import (
    SimulationPlan, SimulationStep, SimulationOutcome,
    ImpactAnalysisReport, SimulationTrace,
)
from core.operations.execution.simulation_plan_builder import (
    build_simulation_plan, get_supported_simulation_templates,
)
from core.operations.execution.simulation_engine import model_plan
from core.operations.execution.impact_analysis import estimate_impact
from core.operations.execution.simulation_trace import SimulationTraceLogger
from core.operations.governance.models import DecisionResult


def _make_decision(decision_type: str = "SAFE_PASS",
                   action_type: str = "observability_read",
                   domain: str = "observability_read",
                   risk_level: str = "NONE",
                   risk_score: int = 0) -> DecisionResult:
    return DecisionResult(
        decision=decision_type,
        action_id="test-action-001",
        reasoning="Test decision",
        audit_entry={
            "action_id": "test-action-001",
            "action_type": action_type,
            "domain": domain,
            "source": "api",
            "decision": decision_type,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "policy_compliance": "PASS",
            "policy_violations": [],
            "simulated": True,
            "executed": False,
        },
        metadata={"gate_version": "1.0.0"},
    )


# ═══════════════════════════════════════════════════════════
# INVARIANT: ALL OUTPUTS MUST BE IN SIMULATION CONTEXT
# ═══════════════════════════════════════════════════════════

class SimulationContextMarkerTest(unittest.TestCase):
    """Every output carries the simulation context marker."""

    def test_plan_has_context_marker(self):
        decision = _make_decision("SAFE_PASS")
        plan = build_simulation_plan(decision)
        self.assertIn("simulation_context", plan.metadata)

    def test_outcome_has_context_marker(self):
        decision = _make_decision("SAFE_PASS")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        self.assertIn("simulation_context", outcome.metadata)

    def test_impact_has_context_marker(self):
        decision = _make_decision("SAFE_PASS")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        self.assertIn("simulation_context", impact.metadata)

    def test_trace_has_context_marker(self):
        decision = _make_decision("SAFE_PASS")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        logger = SimulationTraceLogger()
        trace = logger.record(plan, outcome, impact)
        self.assertIn("simulation_context", trace.metadata)


# ═══════════════════════════════════════════════════════════
# A. SIMULATION PLAN BUILDER TESTS
# ═══════════════════════════════════════════════════════════

class SimulationPlanBuilderTest(unittest.TestCase):
    """Governance DecisionResult → SimulationPlan conversion."""

    def test_build_from_safe_pass(self):
        decision = _make_decision("SAFE_PASS")
        plan = build_simulation_plan(decision)
        self.assertIsInstance(plan, SimulationPlan)
        self.assertEqual(plan.decision_id, "test-action-001")
        self.assertEqual(plan.action_type, "observability_read")

    def test_build_from_blocked(self):
        decision = _make_decision("BLOCKED", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="CRITICAL")
        plan = build_simulation_plan(decision)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].modeled_status, "SKIPPED")

    def test_build_deterministic(self):
        d1 = _make_decision("SAFE_PASS")
        d2 = _make_decision("SAFE_PASS")
        p1 = build_simulation_plan(d1)
        p2 = build_simulation_plan(d2)
        self.assertEqual(len(p1.steps), len(p2.steps))
        self.assertEqual(p1.action_type, p2.action_type)

    def test_plan_has_policy_trace(self):
        decision = _make_decision("SAFE_PASS")
        plan = build_simulation_plan(decision)
        self.assertIn("policy_compliance", plan.policy_trace)

    def test_plan_is_immutable(self):
        decision = _make_decision("SAFE_PASS", action_type="replay_start")
        plan = build_simulation_plan(decision)
        with self.assertRaises(AttributeError):
            plan.action_type = "modified"

    def test_blocked_description_subjunctive(self):
        decision = _make_decision("BLOCKED", action_type="system_rollback",
                                  domain="system_operations", risk_level="CRITICAL")
        plan = build_simulation_plan(decision)
        desc = plan.steps[0].description
        self.assertIn("[SIMULATION]", desc)
        self.assertIn("BLOCKED", desc)

    def test_template_registry(self):
        templates = get_supported_simulation_templates()
        self.assertIn("replay_execute", templates)
        self.assertIn("observability_read", templates)
        self.assertIn("inventory_dispatch", templates)


# ═══════════════════════════════════════════════════════════
# B. SIMULATION ENGINE TESTS
# ═══════════════════════════════════════════════════════════

class SimulationEngineTest(unittest.TestCase):
    """No side effects, no mutation, deterministic modeling."""

    def test_all_steps_marked_applied_false(self):
        """Every modeled step has applied=False."""
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        self.assertTrue(outcome.all_modeled_cleanly)
        for step in outcome.step_outcomes:
            output = step.modeled_output
            app = output.get("applied", True)
            self.assertFalse(app, f"Step {step.step_type} should not be applied")

    def test_no_erp_mutation_in_modeling(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        for step in outcome.step_outcomes:
            self.assertEqual(step.modeled_status, "MODELED")

    def test_bounded_output(self):
        decision = _make_decision("SAFE_PASS", action_type="replay_execute",
                                  risk_level="HIGH", risk_score=3)
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        self.assertLessEqual(len(outcome.step_outcomes), 10)

    def test_no_side_effects_on_plan(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_simulation_plan(decision)
        step_count_before = len(plan.steps)
        _ = model_plan(plan)
        self.assertEqual(len(plan.steps), step_count_before)

    def test_blocked_dispatch_is_skipped(self):
        decision = _make_decision("BLOCKED", action_type="system_rollback",
                                  domain="system_operations", risk_level="CRITICAL")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        for step in outcome.step_outcomes:
            self.assertEqual(step.modeled_status, "SKIPPED")


# ═══════════════════════════════════════════════════════════
# C. IMPACT ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════

class ImpactAnalysisTest(unittest.TestCase):
    """Descriptive estimation, no decision coupling, deterministic."""

    def test_observability_read_no_impact(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        self.assertEqual(impact.financial_estimate.get("severity"), "none")
        self.assertEqual(impact.inventory_estimate.get("severity"), "none")
        self.assertEqual(impact.workflow_estimate.get("severity"), "none")

    def test_inventory_dispatch_high_impact(self):
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        self.assertEqual(impact.financial_estimate.get("severity"), "high")
        self.assertEqual(impact.inventory_estimate.get("severity"), "high")

    def test_impact_deterministic(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact1 = estimate_impact(plan, outcome)
        impact2 = estimate_impact(plan, outcome)
        self.assertEqual(impact1.financial_estimate, impact2.financial_estimate)

    def test_impact_lists_domains(self):
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        self.assertGreater(len(impact.domains_affected), 0)

    def test_impact_has_risk_propagation(self):
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        self.assertIsInstance(impact.risk_propagation, list)

    def test_impact_is_immutable(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        with self.assertRaises(AttributeError):
            impact.plan_id = "modified"


# ═══════════════════════════════════════════════════════════
# D. SIMULATION TRACE TESTS
# ═══════════════════════════════════════════════════════════

class SimulationTraceTest(unittest.TestCase):
    """Immutable, bounded, forensic-only records."""

    def setUp(self):
        self.logger = SimulationTraceLogger(max_traces=50)

    def test_trace_recorded(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        trace = self.logger.record(plan, outcome, impact)
        self.assertIsInstance(trace, SimulationTrace)
        self.assertEqual(trace.plan_id, plan.plan_id)

    def test_trace_decision_lineage(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_simulation_plan(decision)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        trace = self.logger.record(plan, outcome, impact)
        self.assertEqual(trace.decision_id, "test-action-001")
        self.assertEqual(trace.action_type, "observability_read")

    def test_trace_bounded_memory(self):
        logger = SimulationTraceLogger(max_traces=10)
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        for _ in range(20):
            plan = build_simulation_plan(decision)
            outcome = model_plan(plan)
            impact = estimate_impact(plan, outcome)
            logger.record(plan, outcome, impact)
        self.assertEqual(logger.get_trace_count(), 10)

    def test_trace_get_limit_capped(self):
        logger = SimulationTraceLogger(max_traces=200)
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        for _ in range(150):
            plan = build_simulation_plan(decision)
            outcome = model_plan(plan)
            impact = estimate_impact(plan, outcome)
            logger.record(plan, outcome, impact)
        traces = logger.get_traces(limit=500)
        self.assertLessEqual(len(traces), 100)

    def test_trace_clear(self):
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        for _ in range(10):
            plan = build_simulation_plan(decision)
            outcome = model_plan(plan)
            impact = estimate_impact(plan, outcome)
            self.logger.record(plan, outcome, impact)
        self.logger.clear()
        self.assertEqual(self.logger.get_trace_count(), 0)

    def test_trace_is_immutable(self):
        trace = SimulationTrace(trace_id="test-trace")
        with self.assertRaises(AttributeError):
            trace.trace_id = "modified"


# ═══════════════════════════════════════════════════════════
# E. FULL PIPELINE INTEGRATION WITH 5B.0
# ═══════════════════════════════════════════════════════════

class GovernanceIntegrationTest(unittest.TestCase):
    """Full pipeline: 5B.0 → Plan Builder → Engine → Impact → Trace."""

    def test_full_pipeline_safe_pass(self):
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        logger = SimulationTraceLogger(max_traces=50)

        action = intercept("observability_read", "api", {"path": "/health/"})
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_simulation_plan(d)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        trace = logger.record(plan, outcome, impact)

        self.assertEqual(d.decision, "SAFE_PASS")
        self.assertTrue(outcome.all_modeled_cleanly)
        self.assertEqual(impact.financial_estimate.get("severity"), "none")
        self.assertEqual(trace.action_type, "observability_read")

    def test_full_pipeline_blocked(self):
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        action = intercept("erp_create_product", "ui")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_simulation_plan(d)
        outcome = model_plan(plan)

        self.assertEqual(d.decision, "BLOCKED")
        self.assertTrue(outcome.all_modeled_cleanly)
        for step in outcome.step_outcomes:
            self.assertEqual(step.modeled_status, "SKIPPED")

    def test_full_pipeline_simulation_only(self):
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        logger = SimulationTraceLogger(max_traces=50)

        action = intercept("replay_start", "replay")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_simulation_plan(d)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        trace = logger.record(plan, outcome, impact)

        self.assertEqual(d.decision, "SIMULATION_ONLY")
        self.assertTrue(outcome.all_modeled_cleanly)
        self.assertIsNotNone(trace)

    def test_full_pipeline_no_step_applied(self):
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        action = intercept("inventory_dispatch", "workflow")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_simulation_plan(d)
        outcome = model_plan(plan)

        for step in outcome.step_outcomes:
            output = step.modeled_output
            app = output.get("applied", True)
            self.assertFalse(app, f"Step {step.step_type} should not be applied")

    def test_full_pipeline_deterministic(self):
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        logger = SimulationTraceLogger(max_traces=50)

        action1 = intercept("observability_read", "api", {"path": "/health/"})
        pr1 = evaluate(action1)
        rc1 = classify(action1)
        d1 = decide(action1, pr1, rc1)
        plan1 = build_simulation_plan(d1)
        outcome1 = model_plan(plan1)
        impact1 = estimate_impact(plan1, outcome1)
        trace1 = logger.record(plan1, outcome1, impact1)

        action2 = intercept("observability_read", "api", {"path": "/health/"})
        pr2 = evaluate(action2)
        rc2 = classify(action2)
        d2 = decide(action2, pr2, rc2)
        plan2 = build_simulation_plan(d2)
        outcome2 = model_plan(plan2)
        impact2 = estimate_impact(plan2, outcome2)
        trace2 = logger.record(plan2, outcome2, impact2)

        self.assertEqual(d1.decision, d2.decision)
        self.assertEqual(outcome1.all_modeled_cleanly, outcome2.all_modeled_cleanly)
        self.assertEqual(impact1.financial_estimate, impact2.financial_estimate)
        self.assertEqual(trace1.action_type, trace2.action_type)

    def test_no_executed_flag_in_any_output(self):
        """No output in the entire pipeline contains executed=True."""
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        action = intercept("inventory_dispatch", "workflow")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)
        plan = build_simulation_plan(d)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)

        self.assertFalse(d.audit_entry.get("executed", True))
        for step in outcome.step_outcomes:
            output = step.modeled_output
            self.assertNotIn("executed", output,
                             f"Step {step.step_type} has forbidden 'executed' key")
            self.assertEqual(output.get("applied"), False,
                             f"Step {step.step_type} should have applied=False")

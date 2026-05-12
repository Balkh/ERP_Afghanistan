"""
Phase 5B.1 — Controlled Execution Sandbox Tests.

Validates:
A. Execution Plan Builder — Decision→Plan conversion, deterministic plan generation
B. Simulation Safety — no database writes, no ERP mutation, sandbox isolation
C. Impact Analysis — deterministic estimation, bounded outputs, repeatable
D. Trace Integrity — immutable logs, bounded memory, decision lineage
E. Integration with 5B.0 — governance pipeline continuity
"""
import unittest
from collections import deque
from core.operations.execution.models import (
    ExecutionPlan, ExecutionStep, SimulationResult, ImpactReport, TraceLog,
)
from core.operations.execution.plan_builder import build_plan, get_supported_action_templates
from core.operations.execution.simulator import simulate
from core.operations.execution.impact_analyzer import analyze
from core.operations.execution.trace_logger import SandboxTraceLogger
from core.operations.governance.models import DecisionResult


def _make_decision(decision_type: str = "SAFE_PASS",
                   action_type: str = "observability_read",
                   domain: str = "observability_read",
                   risk_level: str = "NONE",
                   risk_score: int = 0) -> DecisionResult:
    """Helper to create a DecisionResult for testing."""
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
# A. EXECUTION PLAN TESTS
# ═══════════════════════════════════════════════════════════

class ExecutionPlanTest(unittest.TestCase):
    """Decision → Plan conversion correctness."""

    def test_build_plan_from_safe_pass(self):
        """SAFE_PASS decision produces valid plan."""
        decision = _make_decision("SAFE_PASS")
        plan = build_plan(decision)
        self.assertIsInstance(plan, ExecutionPlan)
        self.assertEqual(plan.decision_id, "test-action-001")
        self.assertEqual(plan.action_type, "observability_read")

    def test_build_plan_from_blocked(self):
        """BLOCKED decision produces plan with single blocked step."""
        decision = _make_decision("BLOCKED", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="CRITICAL")
        plan = build_plan(decision)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].simulated_status, "SKIPPED")

    def test_build_plan_deterministic(self):
        """Same decision produces same plan structure."""
        d1 = _make_decision("SAFE_PASS")
        d2 = _make_decision("SAFE_PASS")
        p1 = build_plan(d1)
        p2 = build_plan(d2)
        self.assertEqual(len(p1.steps), len(p2.steps))
        self.assertEqual(p1.action_type, p2.action_type)
        self.assertEqual(p1.domain, p2.domain)

    def test_plan_has_policy_trace(self):
        """Plan includes policy trace from decision."""
        decision = _make_decision("SAFE_PASS")
        plan = build_plan(decision)
        self.assertIn("policy_compliance", plan.policy_trace)
        self.assertIn("policy_violations", plan.policy_trace)

    def test_plan_immutable(self):
        """ExecutionPlan is immutable (frozen dataclass)."""
        decision = _make_decision("SAFE_PASS", action_type="replay_start")
        plan = build_plan(decision)
        with self.assertRaises(AttributeError):
            plan.action_type = "modified"

    def test_observability_read_has_4_steps(self):
        """observability_read plan has 4 steps."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        self.assertEqual(len(plan.steps), 4)

    def test_replay_execute_has_5_steps(self):
        """replay_execute plan has 5 steps."""
        decision = _make_decision("SIMULATION_ONLY", action_type="replay_execute",
                                  risk_level="HIGH", risk_score=3)
        plan = build_plan(decision)
        self.assertEqual(len(plan.steps), 5)

    def test_template_registry(self):
        """Template registry has action types."""
        templates = get_supported_action_templates()
        self.assertIn("replay_execute", templates)
        self.assertIn("observability_read", templates)
        self.assertIn("inventory_dispatch", templates)


# ═══════════════════════════════════════════════════════════
# B. SIMULATION SAFETY TESTS
# ═══════════════════════════════════════════════════════════

class SimulationSafetyTest(unittest.TestCase):
    """No side effects, no ERP mutation, sandbox isolation."""

    def test_simulation_no_write(self):
        """Simulation marks all mutation steps as simulated (not executed)."""
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_plan(decision)
        result = simulate(plan)
        self.assertTrue(result.success)
        for step in result.step_results:
            output = step.simulated_output
            if output.get("mutation_blocked", False):
                self.assertFalse(output.get("executed", True),
                                 f"Step {step.step_type} should not be executed")

    def test_simulation_no_erp_mutation(self):
        """No ERP mutation during simulation."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        result = simulate(plan)
        for step in result.step_results:
            self.assertEqual(step.simulated_status, "SIMULATED")

    def test_simulation_bounded_output(self):
        """Simulation result has bounded step count."""
        decision = _make_decision("SAFE_PASS", action_type="replay_execute",
                                  risk_level="HIGH", risk_score=3)
        plan = build_plan(decision)
        result = simulate(plan)
        self.assertLessEqual(len(result.step_results), 10)

    def test_simulation_no_side_effects(self):
        """Simulation does not modify the plan."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        step_count_before = len(plan.steps)
        _ = simulate(plan)
        self.assertEqual(len(plan.steps), step_count_before)

    def test_blocked_plan_simulation(self):
        """BLOCKED plan simulation marks steps as skipped."""
        decision = _make_decision("BLOCKED", action_type="system_rollback",
                                  domain="system_operations", risk_level="CRITICAL")
        plan = build_plan(decision)
        result = simulate(plan)
        for step in result.step_results:
            self.assertEqual(step.simulated_status, "SKIPPED")


# ═══════════════════════════════════════════════════════════
# C. IMPACT ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════

class ImpactAnalysisTest(unittest.TestCase):
    """Deterministic impact estimation, bounded outputs."""

    def test_observability_read_no_impact(self):
        """observability_read has no financial/inventory/workflow impact."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        result = simulate(plan)
        impact = analyze(plan, result)
        self.assertEqual(impact.financial_impact.get("severity"), "none")
        self.assertEqual(impact.inventory_impact.get("severity"), "none")
        self.assertEqual(impact.workflow_impact.get("severity"), "none")

    def test_inventory_dispatch_has_impact(self):
        """inventory_dispatch has high financial/inventory impact."""
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_plan(decision)
        result = simulate(plan)
        impact = analyze(plan, result)
        self.assertEqual(impact.financial_impact.get("severity"), "high")
        self.assertEqual(impact.inventory_impact.get("severity"), "high")

    def test_impact_deterministic(self):
        """Same plan + simulation = same impact report."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        result = simulate(plan)
        impact1 = analyze(plan, result)
        impact2 = analyze(plan, result)
        self.assertEqual(impact1.financial_impact, impact2.financial_impact)
        self.assertEqual(impact1.inventory_impact, impact2.inventory_impact)
        self.assertEqual(impact1.domains_affected, impact2.domains_affected)

    def test_impact_has_domains_affected(self):
        """Impact report lists affected domains."""
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_plan(decision)
        result = simulate(plan)
        impact = analyze(plan, result)
        self.assertGreater(len(impact.domains_affected), 0)

    def test_impact_has_risk_propagation(self):
        """Impact report has risk propagation map."""
        decision = _make_decision("SIMULATION_ONLY", action_type="inventory_dispatch",
                                  domain="domain_operations", risk_level="MEDIUM")
        plan = build_plan(decision)
        result = simulate(plan)
        impact = analyze(plan, result)
        self.assertIsInstance(impact.risk_propagation, list)

    def test_impact_immutable(self):
        """ImpactReport is immutable."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        result = simulate(plan)
        impact = analyze(plan, result)
        with self.assertRaises(AttributeError):
            impact.plan_id = "modified"


# ═══════════════════════════════════════════════════════════
# D. TRACE INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════

class TraceIntegrityTest(unittest.TestCase):
    """Immutable logs, bounded memory, correct lineage."""

    def setUp(self):
        self.logger = SandboxTraceLogger(max_traces=50)

    def test_trace_recorded(self):
        """Recorded trace is accessible."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        result = simulate(plan)
        impact = analyze(plan, result)
        trace = self.logger.record(plan, result, impact)
        self.assertIsInstance(trace, TraceLog)
        self.assertEqual(trace.plan_id, plan.plan_id)

    def test_trace_has_decision_lineage(self):
        """Trace maintains decision lineage."""
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        plan = build_plan(decision)
        result = simulate(plan)
        impact = analyze(plan, result)
        trace = self.logger.record(plan, result, impact)
        self.assertEqual(trace.decision_id, "test-action-001")
        self.assertEqual(trace.action_type, "observability_read")

    def test_trace_bounded_memory(self):
        """Trace logger enforces maxlen."""
        logger = SandboxTraceLogger(max_traces=10)
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        for i in range(20):
            plan = build_plan(decision)
            result = simulate(plan)
            impact = analyze(plan, result)
            logger.record(plan, result, impact)
        self.assertEqual(logger.get_trace_count(), 10)

    def test_trace_get_recent(self):
        """get_traces returns most recent traces."""
        logger = SandboxTraceLogger(max_traces=50)
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        for i in range(5):
            plan = build_plan(decision)
            result = simulate(plan)
            impact = analyze(plan, result)
            logger.record(plan, result, impact)
        traces = logger.get_traces(limit=3)
        self.assertLessEqual(len(traces), 3)

    def test_trace_limit_capped(self):
        """Trace limit is capped at 100."""
        logger = SandboxTraceLogger(max_traces=200)
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        for i in range(150):
            plan = build_plan(decision)
            result = simulate(plan)
            impact = analyze(plan, result)
            logger.record(plan, result, impact)
        traces = logger.get_traces(limit=500)
        self.assertLessEqual(len(traces), 100)

    def test_trace_clear(self):
        """Trace logger clear resets all traces."""
        logger = SandboxTraceLogger(max_traces=50)
        decision = _make_decision("SAFE_PASS", action_type="observability_read")
        for i in range(10):
            plan = build_plan(decision)
            result = simulate(plan)
            impact = analyze(plan, result)
            logger.record(plan, result, impact)
        logger.clear()
        self.assertEqual(logger.get_trace_count(), 0)

    def test_trace_immutable(self):
        """TraceLog is immutable."""
        trace = TraceLog(trace_id="test-trace")
        with self.assertRaises(AttributeError):
            trace.trace_id = "modified"


# ═══════════════════════════════════════════════════════════
# E. INTEGRATION WITH 5B.0
# ═══════════════════════════════════════════════════════════

class GovernanceIntegrationTest(unittest.TestCase):
    """Full pipeline integration with Phase 5B.0 governance."""

    def test_full_pipeline_safe_pass(self):
        """Full pipeline: 5B.0 decision → plan → simulate → impact → trace."""
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        logger = SandboxTraceLogger(max_traces=50)

        action = intercept("observability_read", "api", {"path": "/health/"})
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_plan(d)
        sim = simulate(plan)
        impact = analyze(plan, sim)
        trace = logger.record(plan, sim, impact)

        self.assertEqual(d.decision, "SAFE_PASS")
        self.assertTrue(sim.success)
        self.assertEqual(impact.financial_impact.get("severity"), "none")
        self.assertEqual(trace.action_type, "observability_read")

    def test_full_pipeline_blocked(self):
        """Full pipeline: blocked action never reaches simulation."""
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        action = intercept("erp_create_product", "ui")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_plan(d)
        sim = simulate(plan)

        self.assertEqual(d.decision, "BLOCKED")
        self.assertTrue(sim.success)  # simulation still succeeds
        for step in sim.step_results:
            self.assertEqual(step.simulated_status, "SKIPPED")

    def test_full_pipeline_simulation_only(self):
        """Full pipeline: SIMULATION_ONLY action passes through sandbox."""
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        logger = SandboxTraceLogger(max_traces=50)

        action = intercept("replay_start", "replay")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_plan(d)
        sim = simulate(plan)
        impact = analyze(plan, sim)
        trace = logger.record(plan, sim, impact)

        self.assertEqual(d.decision, "SIMULATION_ONLY")
        self.assertTrue(sim.success)
        self.assertIsNotNone(trace)

    def test_full_pipeline_trace_has_risk_context(self):
        """Trace maintains risk context from governance."""
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        logger = SandboxTraceLogger(max_traces=50)

        action = intercept("replay_start", "replay")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_plan(d)
        sim = simulate(plan)
        impact = analyze(plan, sim)
        trace = logger.record(plan, sim, impact)

        self.assertEqual(trace.risk_level, "MEDIUM")
        self.assertIn("replay", trace.domain)

    def test_full_pipeline_no_execution(self):
        """Full pipeline: no step has executed=True."""
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        action = intercept("inventory_dispatch", "workflow")
        pr = evaluate(action)
        rc = classify(action)
        d = decide(action, pr, rc)

        plan = build_plan(d)
        sim = simulate(plan)

        for step in sim.step_results:
            output = step.simulated_output
            self.assertFalse(output.get("executed", False),
                             f"Step {step.step_type} should not be executed")

    def test_integration_determinism(self):
        """Full pipeline is deterministic for same input."""
        from core.operations.governance.interceptor import intercept
        from core.operations.governance.policy_evaluator import evaluate
        from core.operations.governance.risk_classifier import classify
        from core.operations.governance.decision_gate import decide

        logger = SandboxTraceLogger(max_traces=50)

        action1 = intercept("observability_read", "api", {"path": "/health/"})
        pr1 = evaluate(action1)
        rc1 = classify(action1)
        d1 = decide(action1, pr1, rc1)
        plan1 = build_plan(d1)
        sim1 = simulate(plan1)
        impact1 = analyze(plan1, sim1)
        trace1 = logger.record(plan1, sim1, impact1)

        action2 = intercept("observability_read", "api", {"path": "/health/"})
        pr2 = evaluate(action2)
        rc2 = classify(action2)
        d2 = decide(action2, pr2, rc2)
        plan2 = build_plan(d2)
        sim2 = simulate(plan2)
        impact2 = analyze(plan2, sim2)
        trace2 = logger.record(plan2, sim2, impact2)

        self.assertEqual(d1.decision, d2.decision)
        self.assertEqual(sim1.success, sim2.success)
        self.assertEqual(impact1.financial_impact, impact2.financial_impact)
        self.assertEqual(trace1.action_type, trace2.action_type)
        self.assertEqual(trace1.domain, trace2.domain)

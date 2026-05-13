"""
Phase 5B.6 — Governance API (Phase 5B.0/5B.1/5B.2).

Thin REST endpoints for:
- Decision pipeline (intercept, evaluate, decide)
- Simulation sandbox (plan, run, analyze)
- Approval gateway (workflows, signatures, escalation)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from typing import Any, Dict, List, Optional

from core.operations.governance.interceptor import intercept, get_supported_action_types
from core.operations.governance.policy_evaluator import evaluate as evaluate_policy
from core.operations.governance.risk_classifier import classify
from core.operations.governance.decision_gate import decide
from core.operations.approval.gateway import HumanApprovalGateway, get_gateway as get_approval_gateway
from core.operations.approval.models import AuthorityLevel
from core.operations.execution.simulation_plan_builder import build_simulation_plan
from core.operations.execution.simulation_engine import model_plan
from core.operations.execution.impact_analysis import estimate_impact


def _ok(data: Any, status: int = 200) -> Response:
    return Response({"success": True, "data": data}, status=status)


def _err(message: str, code: str = "GOV_001", status: int = 400) -> Response:
    return Response({"success": False, "error": {"code": code, "message": str(message)}}, status=status)


# ─── Decision Pipeline ───

@api_view(['POST'])
@permission_classes([AllowAny])
def governance_intercept(request):
    """Intercept an action through the governance pipeline."""
    action_type = request.data.get('action_type', '')
    source = request.data.get('source', 'api')
    context = request.data.get('context', {})
    metadata = request.data.get('metadata', {})
    try:
        intent = intercept(action_type, source, context, metadata)
        return _ok({
            "action_id": intent.action_id,
            "action_type": intent.action_type,
            "domain": intent.domain,
            "source": intent.source,
            "timestamp": intent.timestamp,
            "metadata": intent.metadata,
        })
    except ValueError as e:
        return _err(str(e), "GOV_INTERCEPT_001")


@api_view(['POST'])
@permission_classes([AllowAny])
def governance_evaluate(request):
    """Run full governance pipeline: intercept → evaluate → classify → decide."""
    action_type = request.data.get('action_type', '')
    source = request.data.get('source', 'api')
    context = request.data.get('context', {})
    metadata = request.data.get('metadata', {})
    try:
        intent = intercept(action_type, source, context, metadata)
        policy_result = evaluate_policy(intent)
        risk_result = classify(intent)
        decision = decide(intent, policy_result, risk_result)
        return _ok({
            "decision": decision.decision,
            "action_id": decision.action_id,
            "reasoning": decision.reasoning,
            "risk_level": risk_result.risk_level,
            "risk_score": risk_result.risk_score,
            "policy_compliance": policy_result.compliance,
            "audit_entry": decision.audit_entry,
        })
    except ValueError as e:
        return _err(str(e), "GOV_EVAL_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def governance_action_types(request):
    """List all supported action types."""
    return _ok(get_supported_action_types())


# ─── Simulation Sandbox ───

@api_view(['POST'])
@permission_classes([AllowAny])
def governance_simulate(request):
    """Run a simulation: plan → model → impact."""
    decision_result = request.data.get('decision_result', {})
    try:
        plan = build_simulation_plan(decision_result)
        outcome = model_plan(plan)
        impact = estimate_impact(plan, outcome)
        return _ok({
            "plan": {
                "plan_id": plan.plan_id,
                "decision_id": plan.decision_id,
                "action_type": plan.action_type,
                "risk_level": plan.risk_level,
                "steps_count": len(plan.steps),
            },
            "outcome": {
                "all_modeled_cleanly": outcome.all_modeled_cleanly,
                "steps_modeled": outcome.steps_modeled,
                "steps_failed": outcome.steps_failed,
            },
            "impact": {
                "report_id": impact.report_id,
                "domains_affected": impact.domains_affected,
                "financial_estimate": impact.financial_estimate,
            },
        })
    except Exception as e:
        return _err(str(e), "GOV_SIM_001")


# ─── Approval Gateway ───

@api_view(['POST'])
@permission_classes([AllowAny])
def governance_workflow_create(request):
    """Route a decision result through the approval gateway."""
    decision_result = request.data.get('decision_result', {})
    simulation_plan = request.data.get('simulation_plan')
    simulation_outcome = request.data.get('simulation_outcome')
    try:
        gateway = get_approval_gateway()
        workflow = gateway.route_decision(
            decision_result, simulation_plan, simulation_outcome,
        )
        return _ok({
            "workflow_id": workflow.workflow_id,
            "state": workflow.state.value,
            "risk_level": workflow.risk_level,
            "required_signatures": workflow.config.required_signatures,
            "action_type": workflow.action_type,
        })
    except Exception as e:
        return _err(str(e), "GOV_WF_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def governance_workflows_list(request):
    """List all active approval workflows."""
    gateway = get_approval_gateway()
    workflows = gateway.list_active_workflows()
    return _ok([{
        "workflow_id": w.workflow_id,
        "state": w.state.value,
        "action_type": w.action_type,
        "risk_level": w.risk_level,
        "signature_count": len(w.signatures),
        "required_signatures": w.config.required_signatures,
        "created_at": w.created_at,
    } for w in workflows])


@api_view(['GET'])
@permission_classes([AllowAny])
def governance_workflow_detail(request, workflow_id: str):
    """Get detailed workflow information."""
    gateway = get_approval_gateway()
    try:
        summary = gateway.get_workflow_summary(workflow_id)
        return _ok(summary)
    except ValueError as e:
        return _err(str(e), "GOV_WF_NOT_FOUND", 404)


@api_view(['POST'])
@permission_classes([AllowAny])
def governance_workflow_sign(request, workflow_id: str):
    """Submit an approval or rejection signature."""
    approver_id = request.data.get('approver_id', '')
    authority = request.data.get('authority_level', 'APPROVER')
    decision = request.data.get('decision', '')
    justification = request.data.get('justification', '')
    try:
        auth_level = AuthorityLevel(authority)
    except (ValueError, KeyError):
        return _err(f"Invalid authority level: {authority}", "GOV_SIG_AUTH")
    if decision not in ('APPROVED', 'REJECTED'):
        return _err("Decision must be APPROVED or REJECTED", "GOV_SIG_DEC")
    gateway = get_approval_gateway()
    try:
        updated = gateway.submit_signature(workflow_id, approver_id, auth_level, decision, justification)
        return _ok({
            "workflow_id": updated.workflow_id,
            "state": updated.state.value,
            "signature_count": len(updated.signatures),
        })
    except (ValueError, Exception) as e:
        return _err(str(e), "GOV_SIG_001")


@api_view(['POST'])
@permission_classes([AllowAny])
def governance_workflow_escalate(request, workflow_id: str):
    """Escalate a workflow to higher authority."""
    escalated_by = request.data.get('escalated_by', '')
    escalated_to = request.data.get('escalated_to', 'SENIOR_APPROVER')
    reason = request.data.get('reason', '')
    try:
        auth_level = AuthorityLevel(escalated_to)
    except (ValueError, KeyError):
        return _err(f"Invalid authority: {escalated_to}", "GOV_ESC_AUTH")
    gateway = get_approval_gateway()
    try:
        updated = gateway.escalate_workflow(workflow_id, escalated_by, auth_level, reason)
        return _ok({"workflow_id": updated.workflow_id, "state": updated.state.value})
    except Exception as e:
        return _err(str(e), "GOV_ESC_001")


@api_view(['POST'])
@permission_classes([AllowAny])
def governance_workflow_cancel(request, workflow_id: str):
    """Cancel a pending workflow."""
    cancelled_by = request.data.get('cancelled_by', '')
    gateway = get_approval_gateway()
    try:
        updated = gateway.cancel_workflow(workflow_id, cancelled_by)
        return _ok({"workflow_id": updated.workflow_id, "state": updated.state.value})
    except (ValueError, Exception) as e:
        return _err(str(e), "GOV_CANCEL_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def governance_gateway_status(request):
    """Get approval gateway status."""
    gateway = get_approval_gateway()
    return _ok(gateway.get_gateway_status())

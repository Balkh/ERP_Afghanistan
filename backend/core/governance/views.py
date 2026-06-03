"""
Governance API endpoints — routed through GovernanceKernel.

Provides read-only governance status, enforcement, invariant checking,
self-health monitoring, and discovery.

All endpoints use DRF ``@api_view`` which provides:
- CSRF protection (no more ``@csrf_exempt``)
- JWT authentication via ``DEFAULT_AUTHENTICATION_CLASSES``
- ``IsAuthenticated`` via ``DEFAULT_PERMISSION_CLASSES``
- Automatic ``StandardizedJSONRenderer`` wrapping
"""
import logging
from datetime import datetime, timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.governance.kernel import GovernanceKernel, PriorityTier
from core.governance.enforcer import register_enforcement_policies
from core.governance.contracts import register_all_contracts
from core.governance.events import get_event_bus, GovernanceEvent, EventSeverity
from core.governance.metrics import get_metrics
from core.governance.api import discovery_response

logger = logging.getLogger("erp.governance.views")


# ── Permission helpers ──────────────────────────────────────

class IsSuperUser(IsAuthenticated):
    """Allow only authenticated superusers."""
    message = 'Admin access required'

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_superuser


KERNEL = GovernanceKernel()

# Ensure built-in policies and contracts are registered once
_initialized = False


def _ensure_initialized() -> None:
    global _initialized
    if not _initialized:
        register_enforcement_policies(KERNEL)
        register_all_contracts(KERNEL)
        _initialized = True
        logger.info(
            "GovernanceKernel initialized: %d policies, %d invariants, %d feature gates",
            KERNEL.policies.count(), KERNEL.invariants.count(),
            KERNEL.feature_gates.count(),
        )


# ── Health ─────────────────────────────────────────────────

@api_view(['GET'])
def kernel_health(request):
    _ensure_initialized()
    return Response(KERNEL.health())


# ── Readiness ──────────────────────────────────────────────

@api_view(['GET'])
def readiness_check(request):
    _ensure_initialized()
    include = request.GET.get("include_integrity", "true").lower() == "true"
    report = KERNEL.check_readiness(include_integrity=include)
    return Response(report)


# ── Enforcement ────────────────────────────────────────────

@api_view(['POST'])
def enforce(request):
    _ensure_initialized()
    policy_id = request.data.get("policy_id", "")
    context = request.data.get("context", {})
    priority = request.data.get("priority", "high")
    user = request.data.get("user", "")
    entity = request.data.get("entity", "")

    result = KERNEL.enforce(
        policy_id=policy_id,
        context=context,
        priority=priority,
        user=user,
        entity=entity,
    )
    return Response({
        "policy_id": result.policy_id,
        "allowed": result.allowed,
        "reason": result.reason,
        "correlation_id": result.correlation_id,
        "latency_ms": round(result.latency_ms, 2),
        "timestamp": result.timestamp,
    })


# ── Invariants ─────────────────────────────────────────────

@api_view(['GET'])
def invariants(request):
    _ensure_initialized()
    domain = request.GET.get("domain", "")
    priority = request.GET.get("priority", "")
    results = KERNEL.run_invariant_scan(domain=domain, priority=priority)
    return Response({
        "results": results,
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
    })


# ── Discovery ──────────────────────────────────────────────

@api_view(['GET'])
def discover(request):
    _ensure_initialized()
    return Response(discovery_response(KERNEL))


# ── Audit ──────────────────────────────────────────────────

@api_view(['GET'])
def audit(request):
    _ensure_initialized()
    limit = int(request.GET.get("limit", 50))
    entries = KERNEL.get_recent_audit(limit=limit)
    summary = KERNEL.get_audit_summary()
    return Response({
        "entries": [
            {
                "correlation_id": e.correlation_id,
                "action": e.action,
                "policy_id": e.policy_id,
                "result": e.result,
                "reason": e.reason,
                "affected_entity": e.affected_entity,
                "user": e.user,
                "latency_ms": round(e.latency_ms, 2),
                "timestamp": e.timestamp,
            }
            for e in entries
        ],
        "summary": summary,
    })


# ── Feature Gates ──────────────────────────────────────────

@api_view(['GET'])
def features(request):
    _ensure_initialized()
    active = KERNEL.get_active_features()
    return Response({
        "active": active,
        "count": len(active),
    })


# ── Failsafe ───────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSuperUser])
def failsafe(request):
    _ensure_initialized()
    action = request.data.get("action", "status")
    if action == "enable":
        KERNEL.enable_failsafe()
    elif action == "disable":
        KERNEL.disable_failsafe()
    elif action == "degrade_tier":
        tier = request.data.get("tier", "")
        if tier:
            KERNEL.degrade_tier(tier)
    elif action == "restore_tier":
        tier = request.data.get("tier", "")
        if tier:
            KERNEL.restore_tier(tier)

    return Response({
        "failsafe_mode": KERNEL.failsafe_mode,
        "degraded_tiers": KERNEL.health().get("degraded_tiers", []),
    })


# ── Bootstrap ──────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSuperUser])
def bootstrap(request):
    _ensure_initialized()
    from core.governance.bootstrap import BootstrapOrchestrator
    orch = BootstrapOrchestrator()
    results = orch.execute()
    return Response({
        "steps": results,
        "overall_success": orch.success,
    })


# ── Metrics ────────────────────────────────────────────────

@api_view(['GET'])
def metrics(request):
    _ensure_initialized()
    m = get_metrics()
    return Response(m.snapshot())


# ── Events ─────────────────────────────────────────────────

@api_view(['GET'])
def events(request):
    _ensure_initialized()
    bus = get_event_bus()
    return Response({
        "recent": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "severity": e.severity,
                "message": e.message,
                "policy_id": e.policy_id,
                "latency_ms": round(e.latency_ms, 2),
                "timestamp": e.timestamp,
            }
            for e in bus.get_recent(limit=50)
        ],
        "summary": bus.summary(),
    })


# ── Chaos / Resilience Certification ─────────────────────

@api_view(['GET'])
def chaos_summary(request):
    """GET /api/governance/chaos/summary/ — Chaos engine results summary."""
    from core.governance.chaos.engine import ChaosEngine
    engine = ChaosEngine()
    return Response(engine.get_summary())


@api_view(['POST'])
def run_chaos_scenario(request):
    """POST /api/governance/chaos/run/ — Execute a single chaos scenario.

    Body: {"scenario_id": "chaos-gov-001", "context": {...}}
    """
    scenario_id = request.data.get("scenario_id", "")
    context = request.data.get("context", {})

    from core.governance.chaos.simulations import get_all_scenarios
    scenario = None
    for s in get_all_scenarios():
        if s.scenario_id == scenario_id:
            scenario = s
            break

    if not scenario:
        from rest_framework.exceptions import NotFound
        raise NotFound(f"Unknown scenario: {scenario_id}")

    from core.governance.chaos.engine import ChaosEngine
    engine = ChaosEngine()
    result = engine.run_scenario(scenario, context)

    return Response({
        "scenario_id": result.scenario_id,
        "name": result.name,
        "passed": result.passed,
        "summary": result.summary,
        "severity": result.severity.value if hasattr(result.severity, 'value') else str(result.severity),
        "failure_mode": result.failure_mode,
        "root_cause": result.root_cause,
        "affected_subsystem": result.affected_subsystem,
        "latency_ms": result.latency_ms,
        "memory_delta": result.memory_delta,
        "governance_response": result.governance_response,
        "invariant_response": result.invariant_response,
        "recovery_behavior": result.recovery_behavior,
        "regression_risk": result.regression_risk,
        "warnings": result.warnings,
        "timestamp": result.timestamp,
    })


@api_view(['GET'])
def chaos_scenarios(request):
    """GET /api/governance/chaos/scenarios/ — List all available chaos scenarios."""
    from core.governance.chaos.simulations import get_all_scenarios
    scenarios = get_all_scenarios()
    return Response([
        {
            "scenario_id": s.scenario_id,
            "name": s.name,
            "description": s.description,
            "severity": s.severity.value if hasattr(s.severity, 'value') else str(s.severity),
            "domain": s.domain,
            "timeout_s": s.timeout_s,
            "requires_write": s.requires_write,
        }
        for s in scenarios
    ])


# ── Enterprise Operational Certification (Phase 1-7) ──────────

@api_view(['GET'])
def certification_summary(request):
    """GET /api/governance/certification/summary/ — Full certification report."""
    _ensure_initialized()
    from core.governance.operational_certification import OperationalCertificationOrchestrator
    orch = OperationalCertificationOrchestrator(KERNEL)
    report = orch.certify_all(soak_iterations=50)
    return Response({
        "certification_version": CERTIFICATION_VERSION if 'CERTIFICATION_VERSION' in dir() else "2.0.0",
        "overall": {
            "passed": report.overall_passed,
            "score": report.overall_score,
            "phases_passed": sum(1 for p in report.phases if p.passed),
            "phases_total": len(report.phases),
        },
        "phases": [
            {
                "phase": p.phase,
                "name": p.name,
                "passed": p.passed,
                "score": p.score,
                "warnings": p.warnings[:5],
                "errors": p.errors[:5],
                "duration_ms": p.duration_ms,
            }
            for p in report.phases
        ],
        "governance": report.governance_status,
        "warnings": report.warnings[:10],
        "errors": report.errors[:10],
        "timestamp": report.timestamp,
    })


@api_view(['GET'])
def certification_phase(request):
    """GET /api/governance/certification/phase/?id=1 — Single phase certification."""
    _ensure_initialized()
    phase_id = request.GET.get("id", "1")
    from core.governance.operational_certification import OperationalCertificationOrchestrator
    orch = OperationalCertificationOrchestrator(KERNEL)
    report = orch.certify_all(soak_iterations=20)

    phase_map = {str(p.phase): p for p in report.phases}
    phase = phase_map.get(phase_id)
    if not phase:
        from rest_framework.exceptions import NotFound
        raise NotFound(f"Phase {phase_id} not found")

    return Response({
        "phase": phase.phase,
        "name": phase.name,
        "passed": phase.passed,
        "score": phase.score,
        "details": phase.details,
        "warnings": phase.warnings,
        "errors": phase.errors,
        "duration_ms": phase.duration_ms,
    })


@api_view(['GET'])
def deployment_fingerprint(request):
    """GET /api/governance/deployment/fingerprint/ — Current deployment fingerprint."""
    _ensure_initialized()
    from core.governance.deployment import DeploymentValidator
    dv = DeploymentValidator(KERNEL)
    fp = dv.get_fingerprint()
    return Response({
        "fingerprint_id": fp.fingerprint_id,
        "python_version": fp.python_version,
        "django_version": fp.django_version,
        "db_engine": fp.db_engine,
        "env_profile": fp.env_profile,
        "policy_count": fp.policy_count,
        "invariant_count": fp.invariant_count,
        "migration_count": fp.migration_count,
        "debug_mode": fp.debug_mode,
        "ssl_enabled": fp.ssl_enabled,
        "jdatetime_installed": fp.jdatetime_installed,
        "checksum": fp.checksum,
        "timestamp": fp.timestamp,
    })


@api_view(['GET'])
def operational_health(request):
    """GET /api/governance/health/operational/ — Full operational health dashboard."""
    _ensure_initialized()
    from core.governance.observability import OperationalHealthDashboard
    ohd = OperationalHealthDashboard(KERNEL)
    health = ohd.get_health()
    return Response({
        "overall": health.overall,
        "score": health.score,
        "governance": health.governance,
        "invariants": health.invariants,
        "deployment": health.deployment,
        "memory": health.memory,
        "latency": health.latency,
        "recovery": health.recovery,
        "warnings": health.warnings,
        "timestamp": health.timestamp,
    })


@api_view(['GET'])
def operational_drift(request):
    """GET /api/governance/drift/ — Operational drift detection."""
    _ensure_initialized()
    from core.governance.maintainability import OperationalDriftDetector
    odd = OperationalDriftDetector()
    odd.take_config_snapshot()
    odd.take_policy_snapshot(KERNEL)
    drift = odd.run(KERNEL)
    return Response({
        "drifting": drift.drifting,
        "config_drift": drift.config_drift,
        "policy_drift": drift.policy_drift,
        "environment_drift": drift.environment_drift,
        "registry_drift": drift.registry_drift,
        "warnings": drift.warnings,
        "timestamp": drift.timestamp,
    })


# ── Control Plane API ────────────────────────────────────────

@api_view(['GET'])
def control_plane_status(request):
    """GET /api/governance/control-plane/status/ — Unified control plane status."""
    _ensure_initialized()
    from core.governance.control_plane.orchestrator import ControlPlaneOrchestrator
    from core.governance.control_plane.schedule_registry import OperationalScheduleRegistry
    from core.governance.control_plane.execution_policy import ExecutionPolicyEngine

    orch = ControlPlaneOrchestrator(KERNEL)
    reg = OperationalScheduleRegistry()
    policy = ExecutionPolicyEngine()

    results = orch.run_all_checks()

    return Response({
        "control_plane_version": "1.0.0",
        "schedules": {
            name: {
                "frequency": entry.frequency.value,
                "interval_hours": entry.interval_hours,
                "cooldown_minutes": entry.cooldown_minutes,
                "allowed_during_degradation": entry.allowed_during_degradation,
                "timeout_seconds": entry.timeout_seconds,
            }
            for name, entry in reg.list_all().items()
        },
        "execution_states": {
            name: state.status.value
            for name, state in policy.list_states().items()
        },
        "checks": {
            name: {
                "success": result.success,
                "summary": result.summary,
                "warnings": result.warnings[:3],
                "errors": result.errors[:3],
                "duration_ms": result.duration_ms,
            }
            for name, result in results.items()
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@api_view(['GET'])
def control_plane_intelligence(request):
    """GET /api/governance/control-plane/intelligence/ — Operational risk score + trends."""
    _ensure_initialized()
    from core.governance.control_plane.intelligence_engine import (
        OperationalIntelligenceEngine,
    )

    engine = OperationalIntelligenceEngine()
    health = KERNEL.health()
    metrics_snapshot = get_metrics().snapshot()

    # Populate from existing metrics
    total_enforcements = metrics_snapshot.get("total_enforcements", 0)
    total_latency = metrics_snapshot.get("total_latency_ms", 0)
    if total_enforcements > 0 and total_latency > 0:
        avg_latency = total_latency / total_enforcements
        for _ in range(min(total_enforcements, 20)):
            engine.record_latency(avg_latency)

    if health.get("failsafe_mode"):
        engine.record_governance_denial()

    risk = engine.compute_risk_score()

    return Response({
        "overall_risk_score": risk.overall_score,
        "factors": {
            "latency_risk": risk.factors.latency_risk,
            "governance_risk": risk.factors.governance_risk,
            "invariant_risk": risk.factors.invariant_risk,
            "deployment_risk": risk.factors.deployment_risk,
            "memory_risk": risk.factors.memory_risk,
            "drift_risk": risk.factors.drift_risk,
        },
        "predictive_flags": {
            "degradation_risk": risk.degradation_risk,
            "memory_growth_risk": risk.memory_growth_risk,
            "latency_drift_risk": risk.latency_drift_risk,
            "event_amplification_risk": risk.event_amplification_risk,
        },
        "warnings": risk.warnings,
        "timestamp": risk.timestamp,
    })


@api_view(['GET'])
def control_plane_gate(request):
    """GET /api/governance/control-plane/gate/ — Pre-deployment gate evaluation."""
    _ensure_initialized()
    from core.governance.control_plane.deployment_gate import DeploymentControlGate

    gate = DeploymentControlGate(KERNEL)
    result = gate.evaluate()

    return Response({
        "verdict": result.verdict.value,
        "governance_ready": result.governance_ready,
        "drift_ok": result.drift_ok,
        "recovery_ready": result.recovery_ready,
        "certification_healthy": result.certification_healthy,
        "blockers": result.blockers,
        "warnings": result.warnings,
        "checks": {
            name: details
            for name, details in result.checks.items()
        },
        "timestamp": result.timestamp,
    })


@api_view(['GET'])
def control_plane_drift_prevention(request):
    """GET /api/governance/control-plane/drift-prevention/ — Drift prevention report."""
    _ensure_initialized()
    from core.governance.control_plane.drift_prevention import DriftPreventionLayer

    layer = DriftPreventionLayer(KERNEL)
    report = layer.check()

    return Response({
        "drift_detected": report.drift_detected,
        "blocked_deployment": report.blocked_deployment,
        "alerts": [
            {
                "drift_type": a.drift_type,
                "level": a.level.value,
                "message": a.message,
            }
            for a in report.alerts
        ],
        "suggestions": report.suggestions,
        "warnings": report.warnings,
        "timestamp": report.timestamp,
    })


@api_view(['GET'])
def control_plane_recovery_plan(request):
    """GET /api/governance/control-plane/recovery-plan/?scenario=full — Generate recovery plan."""
    _ensure_initialized()
    from core.governance.control_plane.recovery_orchestration import (
        RecoveryOrchestrationLayer,
    )

    scenario = request.GET.get("scenario", "full")
    layer = RecoveryOrchestrationLayer(KERNEL)
    plan = layer.generate_recovery_plan(scenario=scenario)
    simulation = layer.simulate_recovery(plan)
    readiness = layer.get_recovery_readiness()

    return Response({
        "plan_id": plan.plan_id,
        "steps": [
            {
                "step_id": s.step_id,
                "action": s.action,
                "description": s.description,
                "risk": s.risk,
                "automated": s.automated,
                "requires_approval": s.requires_approval,
            }
            for s in plan.steps
        ],
        "estimated_duration_minutes": plan.estimated_duration_minutes,
        "rollback_possible": plan.rollback_possible,
        "simulation": {
            "passed": simulation.simulation_passed,
            "invariant_check_ok": simulation.invariant_check_ok,
            "governance_check_ok": simulation.governance_check_ok,
            "warnings": simulation.warnings,
            "errors": simulation.errors,
        },
        "recovery_readiness": readiness,
        "timestamp": plan.timestamp,
    })


@api_view(['GET'])
def control_plane_stability(request):
    """GET /api/governance/control-plane/stability/ — System stability score + health loop."""
    _ensure_initialized()
    from core.governance.control_plane.health_loop import OperationalHealthLoop

    loop = OperationalHealthLoop(KERNEL)
    stability = loop.compute_stability()

    return Response({
        "overall_stability": stability.overall,
        "trend": stability.trend,
        "scores": {
            "governance": stability.governance_score,
            "invariants": stability.invariant_score,
            "deployment": stability.deployment_score,
            "memory": stability.memory_score,
            "latency": stability.latency_score,
            "recovery": stability.recovery_score,
            "drift": stability.drift_score,
        },
        "warnings": stability.warnings,
        "timestamp": stability.timestamp,
    })

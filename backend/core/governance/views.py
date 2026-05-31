"""
Governance API endpoints — routed through GovernanceKernel.

Provides read-only governance status, enforcement, invariant checking,
self-health monitoring, and discovery.
"""
import json
import time
import logging
from typing import Any, Dict

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.governance.kernel import GovernanceKernel, PriorityTier
from core.governance.enforcer import register_enforcement_policies
from core.governance.contracts import register_all_contracts
from core.governance.events import get_event_bus, GovernanceEvent, EventSeverity
from core.governance.metrics import get_metrics
from core.governance.api import discovery_response

logger = logging.getLogger("erp.governance.views")

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

@csrf_exempt
@require_GET
def kernel_health(request) -> JsonResponse:
    _ensure_initialized()
    return JsonResponse({"success": True, "data": KERNEL.health()})


# ── Readiness ──────────────────────────────────────────────

@csrf_exempt
@require_GET
def readiness_check(request) -> JsonResponse:
    _ensure_initialized()
    try:
        include = request.GET.get("include_integrity", "true").lower() == "true"
        report = KERNEL.check_readiness(include_integrity=include)
        return JsonResponse({"success": True, "data": report})
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_001", "message": str(e)},
        }, status=500)


# ── Enforcement ────────────────────────────────────────────

@csrf_exempt
@require_POST
def enforce(request) -> JsonResponse:
    _ensure_initialized()
    try:
        body = json.loads(request.body)
        policy_id = body.get("policy_id", "")
        context = body.get("context", {})
        priority = body.get("priority", "high")
        user = body.get("user", "")
        entity = body.get("entity", "")

        result = KERNEL.enforce(
            policy_id=policy_id,
            context=context,
            priority=priority,
            user=user,
            entity=entity,
        )
        return JsonResponse({
            "success": True,
            "data": {
                "policy_id": result.policy_id,
                "allowed": result.allowed,
                "reason": result.reason,
                "correlation_id": result.correlation_id,
                "latency_ms": round(result.latency_ms, 2),
                "timestamp": result.timestamp,
            },
        })
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_002", "message": "Invalid JSON body"},
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_003", "message": str(e)},
        }, status=500)


# ── Invariants ─────────────────────────────────────────────

@csrf_exempt
@require_GET
def invariants(request) -> JsonResponse:
    _ensure_initialized()
    try:
        domain = request.GET.get("domain", "")
        priority = request.GET.get("priority", "")
        results = KERNEL.run_invariant_scan(domain=domain, priority=priority)
        return JsonResponse({
            "success": True,
            "data": {
                "results": results,
                "total": len(results),
                "passed": sum(1 for r in results if r["passed"]),
                "failed": sum(1 for r in results if not r["passed"]),
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_004", "message": str(e)},
        }, status=500)


# ── Discovery ──────────────────────────────────────────────

@csrf_exempt
@require_GET
def discover(request) -> JsonResponse:
    _ensure_initialized()
    try:
        return JsonResponse({
            "success": True,
            "data": discovery_response(KERNEL),
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_005", "message": str(e)},
        }, status=500)


# ── Audit ──────────────────────────────────────────────────

@csrf_exempt
@require_GET
def audit(request) -> JsonResponse:
    _ensure_initialized()
    try:
        limit = int(request.GET.get("limit", 50))
        entries = KERNEL.get_recent_audit(limit=limit)
        summary = KERNEL.get_audit_summary()
        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_006", "message": str(e)},
        }, status=500)


# ── Feature Gates ──────────────────────────────────────────

@csrf_exempt
@require_GET
def features(request) -> JsonResponse:
    _ensure_initialized()
    try:
        active = KERNEL.get_active_features()
        return JsonResponse({
            "success": True,
            "data": {
                "active": active,
                "count": len(active),
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_007", "message": str(e)},
        }, status=500)


# ── Failsafe ───────────────────────────────────────────────

@csrf_exempt
@require_POST
def failsafe(request) -> JsonResponse:
    _ensure_initialized()
    try:
        body = json.loads(request.body)
        action = body.get("action", "status")
        if action == "enable":
            KERNEL.enable_failsafe()
        elif action == "disable":
            KERNEL.disable_failsafe()
        elif action == "degrade_tier":
            tier = body.get("tier", "")
            if tier:
                KERNEL.degrade_tier(tier)
        elif action == "restore_tier":
            tier = body.get("tier", "")
            if tier:
                KERNEL.restore_tier(tier)

        return JsonResponse({
            "success": True,
            "data": {
                "failsafe_mode": KERNEL.failsafe_mode,
                "degraded_tiers": KERNEL.health().get("degraded_tiers", []),
            },
        })
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_008", "message": "Invalid JSON body"},
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_009", "message": str(e)},
        }, status=500)


# ── Bootstrap ──────────────────────────────────────────────

@csrf_exempt
@require_POST
def bootstrap(request) -> JsonResponse:
    _ensure_initialized()
    try:
        from core.governance.bootstrap import BootstrapOrchestrator
        orch = BootstrapOrchestrator()
        results = orch.execute()
        return JsonResponse({
            "success": True,
            "data": {
                "steps": results,
                "overall_success": orch.success,
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_010", "message": str(e)},
        }, status=500)


# ── Metrics ────────────────────────────────────────────────

@csrf_exempt
@require_GET
def metrics(request) -> JsonResponse:
    _ensure_initialized()
    try:
        m = get_metrics()
        return JsonResponse({
            "success": True,
            "data": m.snapshot(),
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_011", "message": str(e)},
        }, status=500)


# ── Events ─────────────────────────────────────────────────

@csrf_exempt
@require_GET
def events(request) -> JsonResponse:
    _ensure_initialized()
    try:
        bus = get_event_bus()
        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_012", "message": str(e)},
        }, status=500)


# ── Chaos / Resilience Certification ─────────────────────

@csrf_exempt
@require_GET
def chaos_summary(request) -> JsonResponse:
    """GET /api/governance/chaos/summary/ — Chaos engine results summary."""
    try:
        from core.governance.chaos.engine import ChaosEngine
        engine = ChaosEngine()
        return JsonResponse({
            "success": True,
            "data": engine.get_summary(),
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_020", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_POST
def run_chaos_scenario(request) -> JsonResponse:
    """POST /api/governance/chaos/run/ — Execute a single chaos scenario.

    Body: {"scenario_id": "chaos-gov-001", "context": {...}}
    """
    try:
        body = json.loads(request.body)
        scenario_id = body.get("scenario_id", "")
        context = body.get("context", {})

        from core.governance.chaos.simulations import get_all_scenarios
        scenario = None
        for s in get_all_scenarios():
            if s.scenario_id == scenario_id:
                scenario = s
                break

        if not scenario:
            return JsonResponse({
                "success": False,
                "error": {"code": "GOV_021", "message": f"Unknown scenario: {scenario_id}"},
            }, status=404)

        from core.governance.chaos.engine import ChaosEngine
        engine = ChaosEngine()
        result = engine.run_scenario(scenario, context)

        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_022", "message": "Invalid JSON body"},
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_023", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def chaos_scenarios(request) -> JsonResponse:
    """GET /api/governance/chaos/scenarios/ — List all available chaos scenarios."""
    try:
        from core.governance.chaos.simulations import get_all_scenarios
        scenarios = get_all_scenarios()
        return JsonResponse({
            "success": True,
            "data": [
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
            ],
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_024", "message": str(e)},
        }, status=500)


# ── Enterprise Operational Certification (Phase 1-7) ──────────

@csrf_exempt
@require_GET
def certification_summary(request) -> JsonResponse:
    """GET /api/governance/certification/summary/ — Full certification report."""
    try:
        _ensure_initialized()
        from core.governance.operational_certification import OperationalCertificationOrchestrator
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=50)
        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_030", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def certification_phase(request) -> JsonResponse:
    """GET /api/governance/certification/phase/?id=1 — Single phase certification."""
    try:
        _ensure_initialized()
        phase_id = request.GET.get("id", "1")
        from core.governance.operational_certification import OperationalCertificationOrchestrator
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=20)

        phase_map = {str(p.phase): p for p in report.phases}
        phase = phase_map.get(phase_id)
        if not phase:
            return JsonResponse({
                "success": False,
                "error": {"code": "GOV_031", "message": f"Phase {phase_id} not found"},
            }, status=404)

        return JsonResponse({
            "success": True,
            "data": {
                "phase": phase.phase,
                "name": phase.name,
                "passed": phase.passed,
                "score": phase.score,
                "details": phase.details,
                "warnings": phase.warnings,
                "errors": phase.errors,
                "duration_ms": phase.duration_ms,
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_032", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def deployment_fingerprint(request) -> JsonResponse:
    """GET /api/governance/deployment/fingerprint/ — Current deployment fingerprint."""
    try:
        _ensure_initialized()
        from core.governance.deployment import DeploymentValidator
        dv = DeploymentValidator(KERNEL)
        fp = dv.get_fingerprint()
        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_033", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def operational_health(request) -> JsonResponse:
    """GET /api/governance/health/operational/ — Full operational health dashboard."""
    try:
        _ensure_initialized()
        from core.governance.observability import OperationalHealthDashboard
        ohd = OperationalHealthDashboard(KERNEL)
        health = ohd.get_health()
        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_034", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def operational_drift(request) -> JsonResponse:
    """GET /api/governance/drift/ — Operational drift detection."""
    try:
        _ensure_initialized()
        from core.governance.maintainability import OperationalDriftDetector
        odd = OperationalDriftDetector()
        odd.take_config_snapshot()
        odd.take_policy_snapshot(KERNEL)
        drift = odd.run(KERNEL)
        return JsonResponse({
            "success": True,
            "data": {
                "drifting": drift.drifting,
                "config_drift": drift.config_drift,
                "policy_drift": drift.policy_drift,
                "environment_drift": drift.environment_drift,
                "registry_drift": drift.registry_drift,
                "warnings": drift.warnings,
                "timestamp": drift.timestamp,
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_035", "message": str(e)},
        }, status=500)


# ── Control Plane API ────────────────────────────────────────

@csrf_exempt
@require_GET
def control_plane_status(request) -> JsonResponse:
    """GET /api/governance/control-plane/status/ — Unified control plane status."""
    try:
        _ensure_initialized()
        from core.governance.control_plane.orchestrator import ControlPlaneOrchestrator
        from core.governance.control_plane.schedule_registry import OperationalScheduleRegistry
        from core.governance.control_plane.execution_policy import ExecutionPolicyEngine

        orch = ControlPlaneOrchestrator(KERNEL)
        reg = OperationalScheduleRegistry()
        policy = ExecutionPolicyEngine()

        results = orch.run_all_checks()

        return JsonResponse({
            "success": True,
            "data": {
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
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_036", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def control_plane_intelligence(request) -> JsonResponse:
    """GET /api/governance/control-plane/intelligence/ — Operational risk score + trends."""
    try:
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

        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_037", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def control_plane_gate(request) -> JsonResponse:
    """GET /api/governance/control-plane/gate/ — Pre-deployment gate evaluation."""
    try:
        _ensure_initialized()
        from core.governance.control_plane.deployment_gate import DeploymentControlGate

        gate = DeploymentControlGate(KERNEL)
        result = gate.evaluate()

        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_038", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def control_plane_drift_prevention(request) -> JsonResponse:
    """GET /api/governance/control-plane/drift-prevention/ — Drift prevention report."""
    try:
        _ensure_initialized()
        from core.governance.control_plane.drift_prevention import DriftPreventionLayer

        layer = DriftPreventionLayer(KERNEL)
        report = layer.check()

        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_039", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def control_plane_recovery_plan(request) -> JsonResponse:
    """GET /api/governance/control-plane/recovery-plan/?scenario=full — Generate recovery plan."""
    try:
        _ensure_initialized()
        from core.governance.control_plane.recovery_orchestration import (
            RecoveryOrchestrationLayer,
        )

        scenario = request.GET.get("scenario", "full")
        layer = RecoveryOrchestrationLayer(KERNEL)
        plan = layer.generate_recovery_plan(scenario=scenario)
        simulation = layer.simulate_recovery(plan)
        readiness = layer.get_recovery_readiness()

        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_040", "message": str(e)},
        }, status=500)


@csrf_exempt
@require_GET
def control_plane_stability(request) -> JsonResponse:
    """GET /api/governance/control-plane/stability/ — System stability score + health loop."""
    try:
        _ensure_initialized()
        from core.governance.control_plane.health_loop import OperationalHealthLoop

        loop = OperationalHealthLoop(KERNEL)
        stability = loop.compute_stability()

        return JsonResponse({
            "success": True,
            "data": {
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
            },
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": {"code": "GOV_041", "message": str(e)},
        }, status=500)

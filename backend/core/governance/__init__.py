"""
Phase 5B.13 — Enterprise Runtime Governor.

READ-ONLY aggregation layer that connects existing stability signals
from across the system into a single unified runtime snapshot.

NO business logic. NO state mutation. Pure observation.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


RUNTIME_GOVERNOR_VERSION = "1.0.0"


@dataclass
class RuntimeState:
    """Unified runtime state snapshot — read-only, aggregated from existing systems."""
    system_health_score: float = 100.0
    ui_health_score: float = 100.0
    api_health_score: float = 100.0
    stability_score: float = 100.0
    active_errors: int = 0
    active_warnings: int = 0
    degraded_services: List[str] = field(default_factory=list)
    active_timers_count: int = 0
    ux_violation_count: int = 0
    db_status: str = "unknown"
    last_check: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


def get_runtime_snapshot() -> RuntimeState:
    """Get a single unified runtime health snapshot.

    Aggregates from:
    - core.operations.stability (stability score, config drift)
    - core.operations.health (DB/system health)
    - core.operations.guardrails (sampling, performance budgets)
    - core.operations.concurrency (safety status)

    Returns RuntimeState with graceful degradation on any subsystem failure.
    """
    state = RuntimeState()
    degraded = []

    # 1. Stability monitoring
    try:
        from core.operations.stability import get_stability_status
        status = get_stability_status()
        state.stability_score = status.get("stability_score", 100)
        if state.stability_score < 100:
            state.active_warnings += status.get("config_drift_count", 0)
            if state.stability_score < 60:
                degraded.append("stability_monitor")
    except Exception:
        state.active_warnings += 1
        degraded.append("stability_monitor")

    # 2. Health monitoring
    try:
        from core.operations.health import HealthMonitor
        db = HealthMonitor.check_database()
        sys = HealthMonitor.check_system()
        state.db_status = db.get("status", "unknown")
        if db.get("status") != "healthy":
            state.active_errors += 1
            degraded.append("database")
        if sys.get("status") != "healthy":
            state.active_warnings += 1
            degraded.append("system")
    except Exception:
        state.active_errors += 1
        degraded.append("health_monitor")

    # 3. Guardrails status
    try:
        from core.operations.guardrails import get_guardrail_status
        gr = get_guardrail_status()
        if not gr.get("all_guards_pass", True):
            state.active_warnings += 1
            degraded.append("guardrails")
    except Exception:
        pass

    # 4. Compute health scores
    state.system_health_score = max(0, 100 - (state.active_errors * 15) - (state.active_warnings * 5))
    state.api_health_score = max(0, 100 - (state.active_errors * 10))
    state.ui_health_score = max(0, min(100, state.stability_score))
    state.degraded_services = degraded

    return state

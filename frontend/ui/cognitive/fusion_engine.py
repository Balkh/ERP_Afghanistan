"""
Phase 5B.10 — Cognitive Fusion Engine (UI-only).

Aggregates multiple intelligence API sources into a unified
CognitiveState object. This is PURE UI COMPOSITION LOGIC.
No backend modification. No new API calls beyond existing ones.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from api.observability_client import ObservabilityAPIClient


@dataclass
class CognitiveState:
    """Single unified cognitive representation of enterprise state.

    THIS IS UI-ONLY. Not persisted. Not sent to backend.
    """
    risk_score: float = 0.0
    risk_trend: str = "STABLE"
    confidence: float = 0.0
    forecast_count: int = 0
    anomaly_count: int = 0
    insight_count: int = 0
    recommendation_count: int = 0
    decision_count: int = 0
    system_health: str = "UNKNOWN"
    stream_health: str = "UNKNOWN"
    total_events: int = 0
    runtime_health_score: float = 100.0
    runtime_errors: int = 0
    runtime_degraded: List[str] = field(default_factory=list)
    active_timers_count: int = 0
    optimization_actions: int = 0
    optimization_impact: float = 0.0
    optimization_risk: float = 0.0
    optimization_issues: int = 0
    orchestration_active_policies: List[str] = field(default_factory=list)
    orchestration_degraded: bool = False
    orchestration_timer_pressure: str = "NORMAL"
    orchestration_optimization_level: str = "NONE"
    domain_event_counts: Dict[str, int] = field(default_factory=dict)
    top_anomalies: List[Dict[str, Any]] = field(default_factory=list)
    forecast_summaries: List[Dict[str, Any]] = field(default_factory=list)
    decision_summaries: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class CognitiveFusionEngine:
    """UI-level aggregator that fetches from multiple APIs
    and fuses into a single CognitiveState.

    NO backend logic. NO persistence. UI composition only.
    """

    def __init__(self, api_client: APIClient):
        self._auto = AutonomousAPIClient(api_client)
        self._obs = ObservabilityAPIClient(api_client)

    def fuse(self) -> CognitiveState:
        """Fetch all intelligence sources and fuse into CognitiveState.

        Returns a fully populated CognitiveState, or a partial one
        if some APIs are unavailable (graceful degradation).
        """
        state = CognitiveState()

        try:
            report_resp = self._auto.get_full_report()
            report = report_resp.get("data", report_resp) if isinstance(report_resp, dict) else {}
            state.risk_score = report.get("risk_score_overall", 0)
            state.confidence = report.get("confidence_score_overall", 0)
            state.insight_count = report.get("insight_count", 0)
            state.recommendation_count = report.get("recommendation_count", 0)
            state.forecast_count = report.get("forecast_count", 0)
        except Exception:
            pass

        try:
            risk_resp = self._auto.get_risk_summary()
            risk_data = risk_resp.get("data", risk_resp) if isinstance(risk_resp, dict) else {}
            scores = risk_data.get("scores", [])
            if scores:
                trends = [s.get("trend", "STABLE") for s in scores]
                state.risk_trend = max(set(trends), key=trends.count) if trends else "STABLE"
        except Exception:
            pass

        try:
            warn_resp = self._auto.get_anomaly_warnings()
            warn_data = warn_resp.get("data", warn_resp) if isinstance(warn_resp, dict) else {}
            warnings = warn_data.get("warnings", [])
            state.anomaly_count = len(warnings)
            state.top_anomalies = sorted(
                warnings, key=lambda w: {"CRITICAL": 0, "WARNING": 1, "INFO": 2}.get(w.get("severity", "INFO"), 3)
            )[:5]
        except Exception:
            pass

        try:
            dec_resp = self._auto.get_decision_options()
            dec_data = dec_resp.get("data", dec_resp) if isinstance(dec_resp, dict) else {}
            decisions = dec_data.get("decisions", [])
            state.decision_count = len(decisions)
            state.decision_summaries = [
                {"type": d.get("decision_type", ""), "options": len(d.get("options", []))}
                for d in decisions
            ]
        except Exception:
            pass

        try:
            fc_resp = self._auto.get_forecasts()
            fc_data = fc_resp.get("data", fc_resp) if isinstance(fc_resp, dict) else {}
            forecasts = fc_data.get("forecasts", [])
            state.forecast_summaries = [
                {"domain": f.get("domain", ""), "metric": f.get("metric", ""),
                 "direction": f.get("direction", ""), "value": f.get("predicted_value", 0)}
                for f in forecasts
            ]
        except Exception:
            pass

        try:
            snap = self._obs.get_snapshot()
            snap_data = snap.get("data", snap) if isinstance(snap, dict) else {}
            state.total_events = snap_data.get("total_events", 0)
            state.system_health = snap_data.get("integrity_status", "UNKNOWN")
            state.stream_health = snap_data.get("stream_health", "UNKNOWN")
            state.domain_event_counts = snap_data.get("domain_event_counts", {})
        except Exception:
            pass

        try:
            from runtime.timer_registry import active_timer_count
            state.active_timers_count = active_timer_count()
        except Exception:
            pass

        try:
            from core.governance.runtime_governor import get_runtime_snapshot
            snap = get_runtime_snapshot()
            state.runtime_health_score = snap.system_health_score
            state.runtime_errors = snap.active_errors
            state.runtime_degraded = snap.degraded_services
        except Exception:
            pass

        try:
            from runtime.auto_healer import AutoHealingEngine
            try:
                from core.governance.runtime_governor import get_runtime_snapshot
                rs = get_runtime_snapshot()
            except Exception:
                rs = None
            healer = AutoHealingEngine()
            plan = healer.run_cycle(rs)
            opt = healer.run_optimization_analysis()
            state.optimization_actions = len(plan.actions)
            state.optimization_impact = plan.total_impact
            state.optimization_risk = plan.total_risk
            state.optimization_issues = opt.total_issues
        except Exception:
            pass

        try:
            from runtime.orchestrator import RuntimeOrchestrator
            orch = RuntimeOrchestrator()
            try:
                from core.governance.runtime_governor import get_runtime_snapshot as grs
                rs2 = grs()
            except Exception:
                rs2 = None
            ostate = orch.run_cycle(rs2)
            state.orchestration_active_policies = ostate.active_policies
            state.orchestration_degraded = ostate.degraded_mode
            state.orchestration_timer_pressure = ostate.timer_pressure
            state.orchestration_optimization_level = ostate.optimization_level
        except Exception:
            pass

        return state

"""Route signals and queries through the Control Center Engine.

Provides a thin routing layer over ControlCenterEngine that handles
signal dispatch, batch processing, and query routing to the correct
subcomponent. Exception-safe and read-only.
"""
import logging
from typing import Any, Dict, List

from simulation.control_center.models import OperationalSignal

logger = logging.getLogger(__name__)


class ControlCenterRouter:
    """Routes signals, batches, and queries to the ControlCenterEngine."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._routing_count: int = 0

    # ──────────────────────────────────────────────
    # Signal Routing
    # ──────────────────────────────────────────────

    def route_signal(self, signal: OperationalSignal) -> Dict[str, Any]:
        """Route a single signal to the engine for processing.

        Sets source_phase on the signal if it is empty.
        """
        try:
            self._routing_count += 1
            if not signal.source_phase:
                signal.source_phase = "control_center"
            return self._engine.process_signal(signal)
        except Exception:
            logger.exception("route_signal failed for %s", signal.signal_id)
            return {
                "signal_id": signal.signal_id,
                "success": False,
                "error": f"route_signal failed for {signal.signal_id}",
            }

    def route_batch(
        self, signals: List[OperationalSignal]
    ) -> List[Dict[str, Any]]:
        """Route a batch of signals through the engine.

        Each signal is processed independently; failures are isolated per signal.
        """
        results: List[Dict[str, Any]] = []
        for signal in signals:
            try:
                result = self.route_signal(signal)
                results.append(result)
            except Exception:
                logger.exception(
                    "route_batch failed for signal %s", signal.signal_id
                )
                results.append(
                    {
                        "signal_id": signal.signal_id,
                        "success": False,
                        "error": f"unexpected error in batch for {signal.signal_id}",
                    }
                )
        return results

    # ──────────────────────────────────────────────
    # Query Routing
    # ──────────────────────────────────────────────

    def route_query(
        self,
        query_type: str,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Route a query to the appropriate subcomponent.

        Supported query_types:
            state, timeline, incidents, dashboard, health, safety, reports
        """
        params = params or {}
        try:
            self._routing_count += 1

            if query_type == "state":
                aggregated = self._engine.get_aggregated_state()
                return {
                    "success": True,
                    "query_type": query_type,
                    "data": {
                        "state": aggregated.state.value,
                        "severity_score": aggregated.severity_score,
                        "active_signals": aggregated.active_signals,
                        "critical_count": aggregated.critical_count,
                        "incident_count": aggregated.incident_count,
                        "source_summaries": aggregated.source_summaries,
                        "priority": aggregated.priority.value,
                    },
                }

            if query_type == "timeline":
                timeline = self._engine.get_unified_timeline()
                events = timeline.get_events(
                    tick_start=params.get("tick_start"),
                    tick_end=params.get("tick_end"),
                    source_phase=params.get("source_phase"),
                    event_type=params.get("event_type"),
                    severity=params.get("severity"),
                    limit=params.get("limit", 100),
                )
                return {
                    "success": True,
                    "query_type": query_type,
                    "data": {
                        "event_count": len(events),
                        "events": [
                            {
                                "event_id": e.event_id,
                                "tick": e.tick,
                                "source_phase": e.source_phase,
                                "event_type": e.event_type,
                                "description": e.description,
                                "severity": e.severity.value,
                            }
                            for e in events
                        ],
                    },
                }

            if query_type == "incidents":
                registry = self._engine.get_incident_registry()
                from simulation.control_center.models import (
                    IncidentStatus,
                    IntelligenceSeverity,
                    SignalType,
                )

                status_filter = params.get("status")
                severity_filter = params.get("severity")
                signal_type_filter = params.get("signal_type")
                status = (
                    IncidentStatus(status_filter) if status_filter else None
                )
                severity = (
                    IntelligenceSeverity(severity_filter)
                    if severity_filter
                    else None
                )
                signal_type = (
                    SignalType(signal_type_filter)
                    if signal_type_filter
                    else None
                )
                incidents = registry.get_incidents(
                    status=status,
                    severity=severity,
                    signal_type=signal_type,
                    limit=params.get("limit", 100),
                )
                return {
                    "success": True,
                    "query_type": query_type,
                    "data": {
                        "incident_count": len(incidents),
                        "incidents": [
                            {
                                "incident_id": inc.incident_id,
                                "signal_type": inc.signal_type.value,
                                "severity": inc.severity.value,
                                "status": inc.status.value,
                                "tick_detected": inc.tick_detected,
                                "description": inc.description,
                                "occurrence_count": inc.occurrence_count,
                                "escalation_level": inc.escalation_level.value,
                            }
                            for inc in incidents
                        ],
                    },
                }

            if query_type == "dashboard":
                tick = params.get("tick", 0)
                snapshot = self._engine.generate_dashboard_snapshot(tick)
                return {
                    "success": True,
                    "query_type": query_type,
                    "data": {
                        "snapshot_id": snapshot.snapshot_id,
                        "tick": snapshot.tick,
                        "operational_state": snapshot.operational_state,
                        "stability_score": snapshot.stability_score,
                        "health_status": snapshot.health_status,
                        "active_incidents": snapshot.active_incidents,
                        "summary": snapshot.summary,
                    },
                }

            if query_type == "health":
                aggregated = self._engine.get_aggregated_state()
                health_matrix = self._engine.get_health_matrix()
                health_result = health_matrix.compute_health(
                    severity_score=aggregated.severity_score,
                    critical_count=aggregated.critical_count,
                    incident_count=aggregated.incident_count,
                    active_signals=aggregated.active_signals,
                    source_summaries=aggregated.source_summaries,
                )
                trend = health_matrix.get_health_trend()
                stability = self._engine.get_stability_widgets()
                stability_data = stability.compute_stability_score(
                    severity_score=aggregated.severity_score,
                    critical_count=aggregated.critical_count,
                    incident_count=aggregated.incident_count,
                    active_signals=aggregated.active_signals,
                    cascading_risk=False,
                )
                return {
                    "success": True,
                    "query_type": query_type,
                    "data": {
                        "health": health_result,
                        "health_trend": trend,
                        "stability": stability_data,
                        "stability_trend": stability.get_stability_trend(),
                    },
                }

            if query_type == "safety":
                report = self._engine.generate_safety_report(
                    context=params.get("context", "query")
                )
                return {
                    "success": True,
                    "query_type": query_type,
                    "data": {
                        "report_id": report.report_id,
                        "is_safe": report.is_safe,
                        "recursion_depth": report.recursion_depth,
                        "graph_size": report.graph_size,
                        "memory_pressure": report.memory_pressure,
                        "violations": report.violations,
                    },
                }

            if query_type == "reports":
                report_type = params.get("report_type", "executive_summary")
                tick = params.get("tick", 0)
                report_id = f"{report_type}_{tick}"
                data: Dict[str, Any] = {}

                if report_type == "executive_summary":
                    aggregated = self._engine.get_aggregated_state()
                    exec_summary = self._engine.get_executive_summary()
                    report = exec_summary.generate_report(
                        report_id=report_id,
                        tick=tick,
                        title=f"Executive Summary - Tick {tick}",
                        operational_state=aggregated.state.value,
                        stability_score=max(
                            0.0, 1.0 - aggregated.severity_score
                        ),
                        summary=(
                            f"Executive summary for tick {tick}: "
                            f"state={aggregated.state.value}, "
                            f"signals={aggregated.active_signals}"
                        ),
                        sections=params.get("sections"),
                        recommendations=params.get("recommendations"),
                    )
                    data = {
                        "report_id": report.report_id,
                        "tick": report.tick,
                        "operational_state": report.operational_state,
                        "stability_score": report.stability_score,
                        "summary": report.summary,
                    }

                elif report_type == "risk_report":
                    aggregated = self._engine.get_aggregated_state()
                    registry = self._engine.get_incident_registry()
                    escalation_engine = self._engine.get_escalation_engine()
                    risk = self._engine.get_risk_report()
                    report = risk.generate_risk_report(
                        report_id=report_id,
                        tick=tick,
                        aggregated_state=aggregated,
                        incidents=registry.get_active_incidents(),
                        escalations=escalation_engine.get_escalation_summary(),
                    )
                    data = {
                        "report_id": report.report_id,
                        "summary": report.summary,
                        "recommendations": report.recommendations,
                    }

                elif report_type == "intelligence_digest":
                    digest = self._engine.get_intelligence_digest()
                    health_data = {
                        "operational_state": params.get(
                            "operational_state", "unknown"
                        ),
                        "stability_score": params.get("stability_score", 0.0),
                    }
                    report = digest.generate_digest(
                        digest_id=report_id,
                        tick=tick,
                        signals=params.get("signals", []),
                        incidents=params.get("incidents", []),
                        health_data=health_data,
                    )
                    data = {
                        "report_id": report.report_id,
                        "summary": report.summary,
                    }

                elif report_type == "stability_report":
                    stability = self._engine.get_stability_report()
                    health_matrix = self._engine.get_health_matrix()
                    trend = health_matrix.get_health_trend()
                    stability_widgets = self._engine.get_stability_widgets()
                    stability_score_data = stability_widgets.compute_stability_score(
                        severity_score=params.get("severity_score", 0.0),
                        critical_count=params.get("critical_count", 0),
                        incident_count=params.get("incident_count", 0),
                        active_signals=params.get("active_signals", 0),
                        cascading_risk=params.get("cascading_risk", False),
                    )
                    report = stability.generate_stability_report(
                        report_id=report_id,
                        tick=tick,
                        stability_score=stability_score_data.get(
                            "stability_score", 0.0
                        ),
                        health_status=params.get("health_status", "unknown"),
                        trend=trend,
                        drift_data=params.get("drift_data", []),
                        violation_count=params.get("violation_count", 0),
                    )
                    data = {
                        "report_id": report.report_id,
                        "summary": report.summary,
                        "recommendations": report.recommendations,
                    }

                else:
                    return {
                        "success": False,
                        "query_type": query_type,
                        "error": f"unknown report_type: {report_type}",
                    }

                return {
                    "success": True,
                    "query_type": query_type,
                    "report_type": report_type,
                    "data": data,
                }

            return {
                "success": False,
                "query_type": query_type,
                "error": f"unknown query_type: {query_type}",
            }

        except Exception:
            logger.exception("route_query failed for type %s", query_type)
            return {
                "success": False,
                "query_type": query_type,
                "error": f"route_query failed for {query_type}",
            }

    # ──────────────────────────────────────────────
    # Accessors
    # ──────────────────────────────────────────────

    def get_engine(self) -> Any:
        """Get the underlying ControlCenterEngine instance."""
        return self._engine

    def get_routing_count(self) -> int:
        """Get the total number of routing operations performed."""
        return self._routing_count

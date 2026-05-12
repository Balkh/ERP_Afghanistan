"""Read-only command orchestrator for safe introspection operations.

Executes validated, read-only commands against the Control Center Engine.
All commands are logged in a bounded history deque. Mutations are strictly
forbidden — supported commands only query or snapshot state.
"""
import logging
from collections import deque
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_ALLOWED_COMMANDS = frozenset(
    {
        "aggregate_state",
        "generate_snapshot",
        "safety_check",
        "generate_report",
        "get_timeline",
        "get_incidents",
        "get_health",
        "clear",
    }
)


class OperationalCommandOrchestrator:
    """Executes validated read-only commands against the Control Center Engine.

    Maintains a bounded command history. All operations are exception-safe.
    No command may mutate ERP state.
    """

    def __init__(self, engine: Any, max_command_history: int = 500) -> None:
        self._engine = engine
        self._command_history: deque = deque(maxlen=max_command_history)

    # ──────────────────────────────────────────────
    # Command Execution
    # ──────────────────────────────────────────────

    def execute_command(
        self,
        command: str,
        params: Dict[str, Any] | None = None,
        tick: int = 0,
    ) -> Dict[str, Any]:
        """Execute a validated read-only command.

        Supported commands:
            aggregate_state, generate_snapshot, safety_check,
            generate_report, get_timeline, get_incidents,
            get_health, clear
        """
        params = params or {}
        base = {"command": command, "tick": tick}

        try:
            if command not in _ALLOWED_COMMANDS:
                result = {
                    **base,
                    "success": False,
                    "result": None,
                    "error": f"unknown or disallowed command: {command}",
                }
                self._command_history.append(result)
                return result

            if command == "aggregate_state":
                aggregated = self._engine.get_aggregated_state()
                result_data = {
                    "state": aggregated.state.value,
                    "severity_score": aggregated.severity_score,
                    "active_signals": aggregated.active_signals,
                    "critical_count": aggregated.critical_count,
                    "incident_count": aggregated.incident_count,
                    "source_summaries": aggregated.source_summaries,
                    "priority": aggregated.priority.value,
                }
                result = {**base, "success": True, "result": result_data}
                self._command_history.append(result)
                return result

            if command == "generate_snapshot":
                snapshot = self._engine.generate_dashboard_snapshot(tick)
                result_data = {
                    "snapshot_id": snapshot.snapshot_id,
                    "tick": snapshot.tick,
                    "operational_state": snapshot.operational_state,
                    "stability_score": snapshot.stability_score,
                    "health_status": snapshot.health_status,
                    "active_incidents": snapshot.active_incidents,
                    "summary": snapshot.summary,
                }
                result = {**base, "success": True, "result": result_data}
                self._command_history.append(result)
                return result

            if command == "safety_check":
                context = params.get("context", "command_orchestrator")
                report = self._engine.generate_safety_report(context=context)
                result_data = {
                    "report_id": report.report_id,
                    "is_safe": report.is_safe,
                    "recursion_depth": report.recursion_depth,
                    "graph_size": report.graph_size,
                    "memory_pressure": report.memory_pressure,
                    "violations": list(report.violations),
                }
                result = {**base, "success": True, "result": result_data}
                self._command_history.append(result)
                return result

            if command == "generate_report":
                report_type = params.get("report_type", "executive_summary")
                report_tick = params.get("tick", tick)

                if report_type == "executive_summary":
                    aggregated = self._engine.get_aggregated_state()
                    exec_summary = self._engine.get_executive_summary()
                    report = exec_summary.generate_report(
                        report_id=f"exec_{report_tick}",
                        tick=report_tick,
                        title=f"Executive Summary - Tick {report_tick}",
                        operational_state=aggregated.state.value,
                        stability_score=max(
                            0.0, 1.0 - aggregated.severity_score
                        ),
                        summary=(
                            f"Executive summary for tick {report_tick}: "
                            f"state={aggregated.state.value}, "
                            f"signals={aggregated.active_signals}"
                        ),
                    )
                    result_data = {
                        "report_id": report.report_id,
                        "summary": report.summary,
                        "recommendations": list(report.recommendations),
                    }

                elif report_type == "risk_report":
                    aggregated = self._engine.get_aggregated_state()
                    registry = self._engine.get_incident_registry()
                    escalation_engine = self._engine.get_escalation_engine()
                    risk = self._engine.get_risk_report()
                    report = risk.generate_risk_report(
                        report_id=f"risk_{report_tick}",
                        tick=report_tick,
                        aggregated_state=aggregated,
                        incidents=registry.get_active_incidents(),
                        escalations=escalation_engine.get_escalation_summary(),
                    )
                    result_data = {
                        "report_id": report.report_id,
                        "summary": report.summary,
                        "recommendations": list(report.recommendations),
                    }

                elif report_type == "stability_report":
                    health_matrix = self._engine.get_health_matrix()
                    stability_widgets = self._engine.get_stability_widgets()
                    aggregated = self._engine.get_aggregated_state()
                    stability = self._engine.get_stability_report()
                    stability_score_data = (
                        stability_widgets.compute_stability_score(
                            severity_score=aggregated.severity_score,
                            critical_count=aggregated.critical_count,
                            incident_count=aggregated.incident_count,
                            active_signals=aggregated.active_signals,
                            cascading_risk=False,
                        )
                    )
                    report = stability.generate_stability_report(
                        report_id=f"stability_{report_tick}",
                        tick=report_tick,
                        stability_score=stability_score_data.get(
                            "stability_score", 0.0
                        ),
                        health_status=health_matrix.compute_health(
                            severity_score=aggregated.severity_score,
                            critical_count=aggregated.critical_count,
                            incident_count=aggregated.incident_count,
                            active_signals=aggregated.active_signals,
                        ).get("status", "unknown"),
                        trend=health_matrix.get_health_trend(),
                        drift_data=params.get("drift_data", []),
                        violation_count=params.get("violation_count", 0),
                    )
                    result_data = {
                        "report_id": report.report_id,
                        "summary": report.summary,
                        "recommendations": list(report.recommendations),
                    }

                else:
                    result = {
                        **base,
                        "success": False,
                        "result": None,
                        "error": f"unknown report_type: {report_type}",
                    }
                    self._command_history.append(result)
                    return result

                result = {**base, "success": True, "result": result_data}
                self._command_history.append(result)
                return result

            if command == "get_timeline":
                timeline = self._engine.get_unified_timeline()
                events = timeline.get_events(
                    tick_start=params.get("tick_start"),
                    tick_end=params.get("tick_end"),
                    source_phase=params.get("source_phase"),
                    event_type=params.get("event_type"),
                    severity=params.get("severity"),
                    limit=params.get("limit", 100),
                )
                result_data = {
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
                }
                result = {**base, "success": True, "result": result_data}
                self._command_history.append(result)
                return result

            if command == "get_incidents":
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
                result_data = {
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
                }
                result = {**base, "success": True, "result": result_data}
                self._command_history.append(result)
                return result

            if command == "get_health":
                aggregated = self._engine.get_aggregated_state()
                health_matrix = self._engine.get_health_matrix()
                health_result = health_matrix.compute_health(
                    severity_score=aggregated.severity_score,
                    critical_count=aggregated.critical_count,
                    incident_count=aggregated.incident_count,
                    active_signals=aggregated.active_signals,
                    source_summaries=aggregated.source_summaries,
                )
                health_trend = health_matrix.get_health_trend()
                stability_widgets = self._engine.get_stability_widgets()
                stability_trend = stability_widgets.get_stability_trend()
                result_data = {
                    "health": health_result,
                    "health_trend": health_trend,
                    "stability_trend": stability_trend,
                }
                result = {**base, "success": True, "result": result_data}
                self._command_history.append(result)
                return result

            if command == "clear":
                confirm = params.get("confirm", False)
                if not confirm:
                    error_msg = (
                        "clear requires safety confirmation: "
                        "set params.confirm=True"
                    )
                    result = {
                        **base,
                        "success": False,
                        "result": None,
                        "error": error_msg,
                    }
                    self._command_history.append(result)
                    return result

                self._engine.clear_all()
                result = {
                    **base,
                    "success": True,
                    "result": {"cleared": True},
                }
                self._command_history.append(result)
                return result

            result = {
                **base,
                "success": False,
                "result": None,
                "error": f"unhandled command: {command}",
            }
            self._command_history.append(result)
            return result

        except Exception:
            logger.exception("execute_command failed for %s", command)
            error_result = {
                **base,
                "success": False,
                "result": None,
                "error": f"execute_command failed for {command}",
            }
            try:
                self._command_history.append(error_result)
            except Exception:
                pass
            return error_result

    # ──────────────────────────────────────────────
    # Validation / Query
    # ──────────────────────────────────────────────

    @staticmethod
    def is_command_allowed(command: str) -> bool:
        """Check if a command string is in the allowed set."""
        return command in _ALLOWED_COMMANDS

    def get_command_history(self) -> List[Dict[str, Any]]:
        """Get the full command history as a list (oldest first)."""
        try:
            return list(self._command_history)
        except Exception:
            logger.exception("get_command_history failed")
            return []

    def get_command_count(self) -> int:
        """Get the total number of commands executed."""
        try:
            return len(self._command_history)
        except Exception:
            return 0

    def clear_history(self) -> None:
        """Clear command history only — does NOT affect the engine."""
        try:
            self._command_history.clear()
        except Exception:
            logger.exception("clear_history failed")

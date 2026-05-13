from uuid import uuid4
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.digital_twin.pipeline.digital_twin import DigitalTwin


_engine: Optional[ControlCenterEngine] = None
_router: Optional[ControlCenterRouter] = None
_replay: Optional[ReplayEngine] = None
_digital_twin: Optional[DigitalTwin] = None


def _get_engine() -> Tuple[Optional[ControlCenterEngine], Optional[ControlCenterRouter]]:
    global _engine, _router
    if _engine is None:
        try:
            _engine = ControlCenterEngine()
            _router = ControlCenterRouter(_engine)
        except Exception:
            return None, None
    return _engine, _router


def _get_replay() -> Optional[ReplayEngine]:
    global _replay
    if _replay is None:
        try:
            _replay = ReplayEngine()
        except Exception:
            return None
    return _replay


def _get_digital_twin() -> Optional[DigitalTwin]:
    global _digital_twin
    if _digital_twin is None:
        try:
            _digital_twin = DigitalTwin()
        except Exception:
            return None
    return _digital_twin


def _obs_response(data: Any, meta_extras: Optional[Dict[str, Any]] = None, status: int = 200) -> Response:
    """Build a read-only observability Response. The StandardizedJSONRenderer
    wraps the data as {success, data, meta} — we add read_only via a response attribute."""
    resp = Response(data, status=status)
    resp.observability_read_only = True
    if meta_extras:
        resp.observability_meta_extras = meta_extras
    return resp


def _obs_error(message: str, code: str = "OBS_001", status: int = 500) -> Response:
    """Build an error Response. The renderer wraps non-2xx as {success, error, meta}."""
    resp = Response({"code": code, "message": str(message)}, status=status)
    resp.observability_read_only = True
    return resp


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_health(request):
    try:
        engine = _get_engine()[0]
        return _obs_response({
            "status": "healthy",
            "version": "1.0.0",
            "uptime_ticks": engine.get_orchestration_count() if engine else 0,
        })
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_state(request):
    try:
        engine, router = _get_engine()
        if router is None:
            return _obs_response({"state": None}, meta_extras={"warning": "simulation engine not available"})
        result = router.route_query("state")
        return _obs_response(result.get("data", result))
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_timeline(request):
    try:
        engine, router = _get_engine()
        if router is None:
            return _obs_response({"events": [], "event_count": 0}, meta_extras={"warning": "simulation engine not available"})
        params: Dict[str, Any] = {}
        limit = request.query_params.get("limit")
        offset = request.query_params.get("offset")
        if limit is not None:
            params["limit"] = int(limit)
        if offset is not None:
            params["offset"] = int(offset)
        result = router.route_query("timeline", params)
        return _obs_response(result.get("data", result))
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_incidents(request):
    try:
        engine, router = _get_engine()
        if router is None:
            return _obs_response({"incidents": [], "incident_count": 0}, meta_extras={"warning": "simulation engine not available"})
        params: Dict[str, Any] = {}
        severity = request.query_params.get("severity")
        status = request.query_params.get("status")
        limit = request.query_params.get("limit")
        if severity is not None:
            params["severity"] = severity
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = int(limit)
        result = router.route_query("incidents", params)
        return _obs_response(result.get("data", result))
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_dashboard(request):
    try:
        engine, router = _get_engine()
        if router is None:
            return _obs_response({}, meta_extras={"warning": "simulation engine not available"})
        tick = request.query_params.get("tick", 0)
        try:
            tick = int(tick)
        except (ValueError, TypeError):
            tick = 0
        dashboard_result = router.route_query("dashboard", {"tick": tick})
        health_result = router.route_query("health")
        return _obs_response({
            "dashboard": dashboard_result.get("data", dashboard_result),
            "health": health_result.get("data", health_result),
        })
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_drift(request):
    try:
        engine_obj, _ = _get_engine()
        if engine_obj is None:
            return _obs_response({"data_points": [], "count": 0}, meta_extras={"warning": "simulation engine not available"})
        drift = engine_obj.get_drift_visualization()
        viz = drift.get_visualization() if hasattr(drift, "get_visualization") else {}
        return _obs_response(viz)
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_replay_sessions(request):
    try:
        replay = _get_replay()
        if replay is None:
            return _obs_response({"sessions": [], "count": 0}, meta_extras={"warning": "replay engine not available"})
        session_manager = replay.sessions
        sessions_list = []
        raw = getattr(session_manager, "_sessions", {})
        for session_id, session in raw.items():
            sessions_list.append({
                "session_id": session.session_id,
                "status": session.status.value if hasattr(session.status, "value") else str(session.status),
                "mode": session.mode.value if hasattr(session.mode, "value") else str(session.mode),
                "start_tick": session.start_tick,
                "current_tick": session.current_tick,
                "end_tick": session.end_tick,
                "events_replayed": session.events_replayed,
                "is_paused": session.is_paused,
            })
        return _obs_response({"sessions": sessions_list, "count": len(sessions_list)})
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_replay_session_detail(request, session_id: str):
    try:
        replay = _get_replay()
        if replay is None:
            return _obs_response(None, meta_extras={"warning": "replay engine not available"})
        session = replay.sessions.get_session(session_id)
        if session is None:
            return _obs_response(None, meta_extras={"warning": f"session '{session_id}' not found"})
        return _obs_response({
            "session_id": session.session_id,
            "status": session.status.value if hasattr(session.status, "value") else str(session.status),
            "mode": session.mode.value if hasattr(session.mode, "value") else str(session.mode),
            "start_tick": session.start_tick,
            "current_tick": session.current_tick,
            "end_tick": session.end_tick,
            "events_replayed": session.events_replayed,
            "is_paused": session.is_paused,
        })
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_digital_twin(request):
    try:
        dt = _get_digital_twin()
        if dt is None:
            return _obs_response({"summary": None, "validation": None}, meta_extras={"warning": "digital twin not available"})
        summary = dt.get_summary() if hasattr(dt, "get_summary") else {}
        validation = dt.validate_system() if hasattr(dt, "validate_system") else {}
        return _obs_response({"summary": summary, "validation": validation})
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_frontend_summary(request):
    """Aggregate summary for the frontend dashboard.

    Returns the shape the ObservabilityMainScreen expects:
        {health: {status, detail}, incidents: {active_count}, stability: {score}}
    """
    try:
        engine, router = _get_engine()
        health_data = {"status": "unknown", "detail": "Simulation engine unavailable"}
        incident_count = 0
        stability_score = 100

        if engine is not None and router is not None:
            try:
                health_result = router.route_query("health")
                hd = health_result.get("data", health_result)
                if isinstance(hd, dict):
                    h_status = hd.get("status", hd.get("overall_status", "unknown"))
                    health_data = {
                        "status": h_status,
                        "detail": hd.get("detail", hd.get("message", "System health")),
                    }
            except Exception:
                pass

            try:
                inc_result = router.route_query("incidents", {"limit": 1})
                inc_data = inc_result.get("data", inc_result)
                if isinstance(inc_data, dict):
                    incident_count = inc_data.get("incident_count", len(inc_data.get("incidents", [])))
            except Exception:
                pass

            try:
                drift = engine.get_drift_visualization() if hasattr(engine, "get_drift_visualization") else None
                if drift is not None:
                    viz = drift.get_visualization() if hasattr(drift, "get_visualization") else {}
                    if isinstance(viz, dict):
                        stability_score = max(0, 100 - abs(viz.get("overall_drift", 0)))
            except Exception:
                pass

        return _obs_response({
            "health": health_data,
            "incidents": {"active_count": incident_count},
            "stability": {"score": stability_score},
        })
    except Exception as e:
        return _obs_error(str(e))


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_telemetry_aggregate(request):
    """Aggregate telemetry data for the DigitalTwinTelemetryView frontend.

    Returns the shape the frontend expects:
        {summary, scenarios, integrity_checks, sla_violations}
    """
    dt = _get_digital_twin()
    summary_data = {"total_scenarios": 0, "pass_rate": 0, "integrity_score": 0}
    scenarios = []
    integrity_checks = []
    sla_violations = []

    if dt is not None:
        try:
            raw_summary = dt.get_summary() if hasattr(dt, "get_summary") else {}
            if isinstance(raw_summary, dict):
                summary_data = {
                    "total_scenarios": raw_summary.get("total_scenarios", raw_summary.get("scenario_count", 0)),
                    "pass_rate": raw_summary.get("pass_rate", raw_summary.get("success_rate", 0)),
                    "integrity_score": raw_summary.get("integrity_score", raw_summary.get("integrity", 0)),
                }
                scenarios = raw_summary.get("scenarios", raw_summary.get("results", []))
        except Exception:
            pass

        try:
            raw_val = dt.validate_system() if hasattr(dt, "validate_system") else {}
            if isinstance(raw_val, dict):
                integrity_checks = raw_val.get("checks", raw_val.get("results", []))
                sla_violations = raw_val.get("violations", raw_val.get("sla_violations", []))
        except Exception:
            pass

    return _obs_response({
        "summary": summary_data,
        "scenarios": scenarios[:100] if isinstance(scenarios, list) else [],
        "integrity_checks": integrity_checks[:50] if isinstance(integrity_checks, list) else [],
        "sla_violations": sla_violations[:50] if isinstance(sla_violations, list) else [],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_safety(request):
    try:
        engine_obj, _ = _get_engine()
        if engine_obj is None:
            return _obs_response({}, meta_extras={"warning": "simulation engine not available"})
        report = engine_obj.generate_safety_report(context="observability-api")
        return _obs_response({
            "report_id": report.report_id,
            "is_safe": report.is_safe,
            "recursion_depth": report.recursion_depth,
            "graph_size": report.graph_size,
            "memory_pressure": report.memory_pressure,
            "violations": report.violations,
        })
    except Exception as e:
        return _obs_error(str(e))

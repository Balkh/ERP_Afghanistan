"""
Phase 5B.6 — Observability API (Phase 5B.4).

Thin REST endpoints for:
- Trace (aggregate lifecycle, causation graphs)
- Timeline (deterministic event timelines)
- Correlation (cross-domain links)
- Integrity (system health checks)
- Replay (time-travel, replay state)
- Dashboard (read-only views)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from typing import Any, Dict, List, Optional

from core.operations.observability.gateway import ObservabilityGateway, get_gateway as get_obs_gateway


def _ok(data: Any, status: int = 200) -> Response:
    return Response({"success": True, "data": data}, status=status)


def _err(message: str, code: str = "OBS_001", status: int = 400) -> Response:
    return Response({"success": False, "error": {"code": code, "message": str(message)}}, status=status)


# ─── Trace ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_trace_aggregate(request, domain: str, aggregate_id: str):
    """Full event chain reconstruction for an aggregate."""
    gw = get_obs_gateway()
    try:
        trace = gw.trace_aggregate(domain, aggregate_id)
        return _ok({
            "trace_id": trace.trace_id,
            "aggregate_id": trace.aggregate_id,
            "domain": trace.domain,
            "event_count": trace.event_count,
            "root_event_id": trace.root_event_id,
            "timestamp_range_start": trace.timestamp_range_start,
            "timestamp_range_end": trace.timestamp_range_end,
            "integrity_hash": trace.integrity_hash,
            "events": [{
                "event_id": e.event_id,
                "event_type": e.event_type,
                "domain": e.domain,
                "sequence": e.sequence,
                "timestamp": e.timestamp,
                "causation_id": e.causation_id,
            } for e in trace.full_event_chain],
        })
    except Exception as e:
        return _err(str(e), "OBS_TRACE_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_trace_by_event(request, event_id: str):
    """Trace starting from a specific event ID."""
    gw = get_obs_gateway()
    try:
        trace = gw.trace_by_event_id(event_id)
        if trace is None:
            return _err("Event not found", "OBS_TRACE_NF", 404)
        return _ok({
            "trace_id": trace.trace_id,
            "aggregate_id": trace.aggregate_id,
            "event_count": trace.event_count,
            "events": [{
                "event_id": e.event_id, "event_type": e.event_type,
                "domain": e.domain, "timestamp": e.timestamp,
            } for e in trace.full_event_chain],
        })
    except Exception as e:
        return _err(str(e), "OBS_TRACE_002")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_causation_graph(request, event_id: str):
    """Build causation graph for an event."""
    gw = get_obs_gateway()
    try:
        graph = gw.build_causation_graph(event_id)
        return _ok(graph)
    except Exception as e:
        return _err(str(e), "OBS_CAUS_001")


# ─── Timeline ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_timeline(request):
    """Get deterministic event timeline."""
    gw = get_obs_gateway()
    from_timestamp = request.query_params.get('from', '')
    to_timestamp = request.query_params.get('to', '')
    domains = request.query_params.getlist('domains') or None
    max_entries = int(request.query_params.get('max', 500))
    try:
        timeline = gw.get_timeline(from_timestamp, to_timestamp, domains, None, max_entries)
        return _ok({
            "timeline_id": timeline.timeline_id,
            "total_entries": timeline.total_entries,
            "domains_present": timeline.domains_present,
            "entries": [{
                "event_id": e.event_id, "event_type": e.event_type,
                "domain": e.domain, "timestamp": e.timestamp,
                "summary": e.summary,
            } for e in timeline.entries],
        })
    except Exception as e:
        return _err(str(e), "OBS_TL_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_timeline_aggregate(request, domain: str, aggregate_id: str):
    """Get timeline for a single aggregate."""
    gw = get_obs_gateway()
    try:
        timeline = gw.get_aggregate_timeline(domain, aggregate_id)
        return _ok({
            "timeline_id": timeline.timeline_id,
            "total_entries": timeline.total_entries,
            "entries": [{
                "event_id": e.event_id, "event_type": e.event_type,
                "domain": e.domain, "timestamp": e.timestamp,
                "sequence": e.sequence, "summary": e.summary,
            } for e in timeline.entries],
        })
    except Exception as e:
        return _err(str(e), "OBS_TL_AGG_001")


# ─── Correlation ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_correlation_event(request, event_id: str):
    """Cross-domain correlation from event ID."""
    gw = get_obs_gateway()
    try:
        graph = gw.correlate_by_event_id(event_id)
        return _ok({
            "graph_id": graph.graph_id,
            "domains_involved": graph.domains_involved,
            "nodes": [{
                "event_id": n.event_id, "event_type": n.event_type,
                "domain": n.domain, "aggregate_id": n.aggregate_id,
            } for n in graph.nodes],
            "dependency_clusters": graph.dependency_clusters,
        })
    except Exception as e:
        return _err(str(e), "OBS_CORR_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_correlation_domains(request, domain_a: str, domain_b: str):
    """Correlation between two domains."""
    gw = get_obs_gateway()
    try:
        graph = gw.correlate_domain_pair(domain_a, domain_b)
        return _ok({
            "domains_involved": graph.domains_involved,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        })
    except Exception as e:
        return _err(str(e), "OBS_CORR_DOM_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_domain_dependencies(request):
    """Get domain dependency map."""
    gw = get_obs_gateway()
    return _ok(gw.get_domain_dependency_map())


# ─── Integrity ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_integrity_check(request):
    """Run full system integrity check."""
    gw = get_obs_gateway()
    try:
        report = gw.run_integrity_check()
        return _ok({
            "status": report.status.value,
            "total_events_checked": report.total_events_checked,
            "anomaly_count": len(report.detected_anomalies),
            "sequence_gaps": report.sequence_gaps,
            "affected_domains": report.affected_domains,
            "domain_balances": report.domain_balances,
        })
    except Exception as e:
        return _err(str(e), "OBS_INT_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_domain_integrity(request, domain: str):
    """Get integrity status for a domain."""
    gw = get_obs_gateway()
    try:
        result = gw.get_domain_integrity(domain)
        return _ok(result)
    except Exception as e:
        return _err(str(e), "OBS_INT_DOM_001")


# ─── Replay ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_replay_state(request):
    """Get replay state for a sequence range."""
    gw = get_obs_gateway()
    from_seq = int(request.query_params.get('from', 0))
    to_seq = request.query_params.get('to')
    to_seq = int(to_seq) if to_seq else None
    try:
        state = gw.get_replay_state(from_seq, to_seq)
        return _ok({
            "replay_id": state.replay_id,
            "from_sequence": state.from_sequence,
            "to_sequence": state.to_sequence,
            "total_events_in_range": state.total_events_in_range,
            "domains_in_range": state.domains_in_range,
            "is_complete": state.is_complete,
        })
    except Exception as e:
        return _err(str(e), "OBS_RP_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_replay_render(request, sequence: int):
    """Render system state at a specific sequence (time-travel)."""
    gw = get_obs_gateway()
    try:
        entries = gw.render_at_sequence(sequence)
        return _ok({
            "sequence": sequence,
            "event_count": len(entries),
            "events": entries,
        })
    except Exception as e:
        return _err(str(e), "OBS_RP_RENDER_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_replay_hash(request):
    """Compute deterministic replay hash for a range."""
    gw = get_obs_gateway()
    from_seq = int(request.query_params.get('from', 0))
    to_seq = int(request.query_params.get('to', 0))
    try:
        h = gw.compute_replay_hash(from_seq, to_seq)
        return _ok({"hash": h, "from_sequence": from_seq, "to_sequence": to_seq})
    except Exception as e:
        return _err(str(e), "OBS_RP_HASH_001")


# ─── Dashboard ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_dashboard(request, dashboard_type: str = "overview"):
    """Get read-only dashboard view."""
    gw = get_obs_gateway()
    domain = request.query_params.get('domain', 'inventory')
    try:
        dash = gw.get_dashboard(dashboard_type, domain)
        return _ok({
            "dashboard_id": dash.dashboard_id,
            "dashboard_type": dash.dashboard_type,
            "domain": dash.domain,
            "integrity": {
                "status": dash.integrity.status.value if dash.integrity else "UNKNOWN",
                "anomaly_count": len(dash.integrity.detected_anomalies) if dash.integrity else 0,
            } if dash.integrity else None,
        })
    except Exception as e:
        return _err(str(e), "OBS_DASH_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_snapshot(request):
    """Get point-in-time observability snapshot."""
    gw = get_obs_gateway()
    try:
        snap = gw.get_snapshot()
        return _ok({
            "snapshot_id": snap.snapshot_id,
            "total_events": snap.total_events,
            "integrity_status": snap.integrity_status.value,
            "stream_health": snap.stream_health.value,
            "domain_event_counts": snap.domain_event_counts,
        })
    except Exception as e:
        return _err(str(e), "OBS_SNAP_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_status(request):
    """Get comprehensive observability status."""
    gw = get_obs_gateway()
    try:
        return _ok(gw.get_observability_status())
    except Exception as e:
        return _err(str(e), "OBS_STATUS_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obs_stream_metrics(request):
    """Get read-only stream metrics."""
    gw = get_obs_gateway()
    try:
        metrics = gw.get_stream_metrics()
        return _ok({
            "total_events_received": metrics.total_events_received,
            "events_per_second": metrics.events_per_second,
            "health": metrics.health.value,
            "lag_seconds": metrics.lag_seconds,
            "events_by_domain": metrics.events_by_domain,
        })
    except Exception as e:
        return _err(str(e), "OBS_STREAM_001")

"""
Phase 5B.6 — Intelligence API (Phase 5B.5).

Thin REST endpoints for:
- Drift detection (baseline, drift scores, velocity)
- Anomaly detection (patterns, rare events, bursts, cycles)
- Cross-domain anomaly graphs
- Temporal drift analysis
- Consistency deviation analysis
- Full intelligence snapshot
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from typing import Any, Dict

from core.operations.intelligence.gateway import AnomalyIntelligenceGateway, get_gateway as get_intel_gateway


def _ok(data: Any, status: int = 200) -> Response:
    return Response({"success": True, "data": data}, status=status)


def _err(message: str, code: str = "INT_001", status: int = 400) -> Response:
    return Response({"success": False, "error": {"code": code, "message": str(message)}}, status=status)


# ─── Drift ───

@api_view(['GET'])
@permission_classes([AllowAny])
def intel_drift_baseline(request, domain: str):
    """Compute baseline statistics for a domain."""
    gw = get_intel_gateway()
    try:
        baseline = gw.compute_baseline(domain)
        return _ok({
            "domain": domain,
            "total_events_in_window": baseline.total_events_in_window,
            "mean_event_rate": baseline.mean_event_rate,
            "std_event_rate": baseline.std_event_rate,
            "window_start": baseline.window_start,
            "window_end": baseline.window_end,
        })
    except Exception as e:
        return _err(str(e), "INT_BASE_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def intel_drift_aggregate(request, domain: str, aggregate_id: str):
    """Detect drift for a specific aggregate."""
    gw = get_intel_gateway()
    try:
        report = gw.detect_drift(domain, aggregate_id)
        return _ok({
            "domain": report.domain,
            "entity_id": report.entity_id,
            "drift_score": report.drift_score,
            "drift_velocity": report.drift_velocity,
            "deviation": {
                "absolute": report.deviation_vector.absolute_deviation if report.deviation_vector else 0,
                "percentage": report.deviation_vector.percentage_deviation if report.deviation_vector else 0,
                "z_score": report.deviation_vector.z_score if report.deviation_vector else 0,
                "direction": report.deviation_vector.direction.value if report.deviation_vector else "UNKNOWN",
            } if report.deviation_vector else None,
            "confidence_level": report.confidence_level.value,
        })
    except Exception as e:
        return _err(str(e), "INT_DRIFT_AGG_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def intel_drift_all(request, domain: str):
    """Detect drift for all aggregates in a domain."""
    gw = get_intel_gateway()
    try:
        reports = gw.detect_drift_all(domain)
        return _ok({
            "domain": domain,
            "aggregate_count": len(reports),
            "reports": [{
                "entity_id": r.entity_id,
                "drift_score": r.drift_score,
                "confidence_level": r.confidence_level.value,
            } for r in reports],
        })
    except Exception as e:
        return _err(str(e), "INT_DRIFT_ALL_001")


# ─── Patterns ───

@api_view(['GET'])
@permission_classes([AllowAny])
def intel_patterns(request, domain: str):
    """Mine all event patterns for a domain."""
    gw = get_intel_gateway()
    try:
        all_patterns = gw.mine_all_patterns(domain)
        result = {}
        for pattern_type, patterns in all_patterns.items():
            result[pattern_type] = [{
                "pattern_type": p.pattern_type.value,
                "event_types": p.event_types,
                "occurrence_count": p.occurrence_count,
                "frequency": p.frequency,
                "confidence_level": p.confidence_level.value,
            } for p in patterns]
        return _ok({"domain": domain, "patterns": result})
    except Exception as e:
        return _err(str(e), "INT_PAT_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def intel_rare_events(request, domain: str):
    """Detect rare events in a domain."""
    gw = get_intel_gateway()
    try:
        patterns = gw.detect_rare_events(domain)
        return _ok({
            "domain": domain,
            "rare_events": [{
                "event_type": p.event_types[0] if p.event_types else "",
                "occurrence_count": p.occurrence_count,
                "frequency": p.frequency,
            } for p in patterns],
        })
    except Exception as e:
        return _err(str(e), "INT_RARE_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def intel_bursts(request, domain: str):
    """Detect burst patterns in a domain."""
    gw = get_intel_gateway()
    try:
        patterns = gw.detect_bursts(domain)
        return _ok({
            "domain": domain,
            "bursts": [{
                "occurrence_count": p.occurrence_count,
                "window_start": p.window_start,
                "window_end": p.window_end,
            } for p in patterns],
        })
    except Exception as e:
        return _err(str(e), "INT_BURST_001")


# ─── Anomaly Graph ───

@api_view(['GET'])
@permission_classes([AllowAny])
def intel_anomaly_graph(request, domain: str):
    """Build cross-domain anomaly graph for a domain."""
    gw = get_intel_gateway()
    try:
        graph = gw.build_anomaly_graph(domain)
        return _ok({
            "graph_id": graph.graph_id,
            "domains_involved": graph.domains_involved,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "confidence_level": graph.confidence_level.value,
        })
    except Exception as e:
        return _err(str(e), "INT_GRAPH_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def intel_cross_domain_graph(request):
    """Build complete cross-domain anomaly graph."""
    gw = get_intel_gateway()
    try:
        graph = gw.build_cross_domain_graph()
        return _ok({
            "graph_id": graph.graph_id,
            "domains_involved": graph.domains_involved,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        })
    except Exception as e:
        return _err(str(e), "INT_CROSS_001")


# ─── Temporal ───

@api_view(['GET'])
@permission_classes([AllowAny])
def intel_temporal_drift(request, domain: str):
    """Analyze temporal drift for a domain."""
    gw = get_intel_gateway()
    try:
        report = gw.analyze_temporal_drift(domain)
        return _ok({
            "domain": report.domain,
            "overall_trend": report.overall_trend.value,
            "acceleration": report.acceleration,
            "persistence_score": report.persistence_score,
            "segment_count": len(report.segments),
            "confidence_level": report.confidence_level.value,
        })
    except Exception as e:
        return _err(str(e), "INT_TEMP_001")


# ─── Consistency ───

@api_view(['GET'])
@permission_classes([AllowAny])
def intel_consistency(request):
    """Analyze consistency deviations across the system."""
    gw = get_intel_gateway()
    try:
        reports = gw.analyze_consistency_deviations()
        return _ok({
            "total_deviations": len(reports),
            "deviations": [{
                "deviation_type": r.deviation_type.value,
                "affected_entities": r.affected_entities,
                "deviation_score": r.deviation_score,
                "confidence_level": r.confidence_level.value,
            } for r in reports],
        })
    except Exception as e:
        return _err(str(e), "INT_CONS_001")


@api_view(['POST'])
@permission_classes([AllowAny])
def intel_consistency_compare(request):
    """Compare Event Store with Truth Layer reported counts."""
    gw = get_intel_gateway()
    counts = request.data.get('truth_layer_counts', {})
    try:
        report = gw.compare_with_truth_layer(counts)
        return _ok({
            "deviation_type": report.deviation_type.value,
            "deviation_score": report.deviation_score,
            "affected_entities": report.affected_entities,
            "confidence_level": report.confidence_level.value,
        })
    except Exception as e:
        return _err(str(e), "INT_CONS_CMP_001")


# ─── Snapshot ───

@api_view(['GET'])
@permission_classes([AllowAny])
def intel_snapshot(request):
    """Get point-in-time intelligence snapshot."""
    gw = get_intel_gateway()
    try:
        snap = gw.get_snapshot()
        return _ok({
            "total_drift_reports": snap.total_drift_reports,
            "total_patterns_detected": snap.total_patterns_detected,
            "total_anomalies_correlated": snap.total_anomalies_correlated,
            "total_consistency_deviations": snap.total_consistency_deviations,
            "domains_analyzed": snap.domains_analyzed,
        })
    except Exception as e:
        return _err(str(e), "INT_SNAP_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def intel_status(request):
    """Get intelligence engine status."""
    gw = get_intel_gateway()
    return _ok(gw.get_status())

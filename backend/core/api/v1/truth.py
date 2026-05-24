"""
Phase 5B.6 — Truth Layer API (Phase 5B.3).

Thin REST endpoints for:
- Event Store (emit, query, list)
- Truth verification (claim, existence, aggregate)
- Projections (inventory, accounting, HR, SP)
- Reports (stock, ledger, trial balance, etc.)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from typing import Any, Dict, Optional

from core.operations.truth.gateway import TruthGateway, get_gateway as get_truth_gateway
from core.operations.truth.models import (
    Domain, SourceType, VerificationClaim,
)


def _ok(data: Any, status: int = 200) -> Response:
    return Response({"success": True, "data": data}, status=status)


def _err(message: str, code: str = "TRU_001", status: int = 400) -> Response:
    return Response({"success": False, "error": {"code": code, "message": str(message)}}, status=status)


def _parse_source_type(st: str) -> SourceType:
    try:
        return SourceType(st.upper())
    except (ValueError, KeyError):
        return SourceType.REAL


def _parse_domain(d: str) -> Domain:
    try:
        return Domain(d.lower())
    except (ValueError, KeyError):
        return Domain.INVENTORY


# ─── Event Store ───

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def truth_event_emit(request):
    """Emit a single event to the Event Store."""
    gw = get_truth_gateway()
    try:
        domain = _parse_domain(request.data.get('domain', 'inventory'))
        source_type = _parse_source_type(request.data.get('source_type', 'REAL'))
        event_type = request.data.get('event_type', '')
        aggregate_id = request.data.get('aggregate_id', '')
        payload = request.data.get('payload', {})
        metadata = request.data.get('metadata', {})
        if not event_type:
            return _err("event_type is required", "TRU_EMIT_001")
        if not aggregate_id:
            return _err("aggregate_id is required", "TRU_EMIT_002")
        eid = gw.emit_event(source_type, domain, event_type, aggregate_id, payload, metadata)
        return _ok({"event_id": eid}, 201)
    except Exception as e:
        return _err(str(e), "TRU_EMIT_003")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_events_list(request):
    """List events from the Event Store."""
    gw = get_truth_gateway()
    store = gw._store
    domain_str = request.query_params.get('domain')
    source_str = request.query_params.get('source_type')
    aggregate_id = request.query_params.get('aggregate_id')
    limit = int(request.query_params.get('limit', 100))

    events = store.get_all()
    if domain_str:
        events = [e for e in events if e.domain.value == domain_str]
    if source_str:
        events = [e for e in events if e.source_type.value == source_str.upper()]
    if aggregate_id:
        events = [e for e in events if e.aggregate_id == aggregate_id]

    events = events[-limit:]

    return _ok({
        "events": [{
            "event_id": e.event_id,
            "source_type": e.source_type.value,
            "domain": e.domain.value,
            "event_type": e.event_type,
            "aggregate_id": e.aggregate_id,
            "timestamp": e.timestamp,
            "sequence": e.sequence,
            "payload": e.payload,
        } for e in events],
        "total": len(events),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_event_detail(request, event_id: str):
    """Get a single event by ID."""
    gw = get_truth_gateway()
    event = gw.get_event(event_id)
    if event is None:
        return _err("Event not found", "TRU_GET_001", 404)
    return _ok(event)


# ─── Truth Verification ───

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def truth_verify_claim(request):
    """Verify a claim against the Event Store."""
    gw = get_truth_gateway()
    event_type = request.data.get('event_type', '')
    aggregate_id = request.data.get('aggregate_id', '')
    domain = _parse_domain(request.data.get('domain', 'inventory'))
    expected_count = int(request.data.get('expected_count', 1))
    if not event_type or not aggregate_id:
        return _err("event_type and aggregate_id required", "TRU_VER_001")
    claim = VerificationClaim(
        event_type=event_type, aggregate_id=aggregate_id,
        domain=domain, expected_count=expected_count,
    )
    result = gw.verify_claim(claim)
    return _ok({
        "verified": result.verified,
        "evidence_event_ids": result.evidence_event_ids,
        "missing_entities": result.missing_entities,
        "inconsistencies": result.inconsistencies,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_verify_aggregate(request, domain: str, aggregate_id: str):
    """Verify and reconstruct an aggregate's state."""
    gw = get_truth_gateway()
    try:
        state = gw.verify_aggregate(_parse_domain(domain), aggregate_id)
        return _ok(state)
    except Exception as e:
        return _err(str(e), "TRU_AGG_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_event_exists(request, event_id: str):
    """Check if an event exists in the store."""
    gw = get_truth_gateway()
    exists = gw.verify_event_exists(event_id)
    return _ok({"event_id": event_id, "exists": exists})


# ─── Projections ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_projection_rebuild(request, domain: str):
    """Rebuild and return projection state for a domain."""
    gw = get_truth_gateway()
    try:
        d = _parse_domain(domain)
        counts = gw.rebuild_all_projections()
        return _ok({"domain": domain, "rebuild_counts": counts})
    except Exception as e:
        return _err(str(e), "TRU_PROJ_001")


# ─── Reports ───

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_reports_stock_levels(request):
    """Get current stock levels (inventory report)."""
    gw = get_truth_gateway()
    report = gw.get_stock_levels()
    return _ok({
        "report_id": report.report_id,
        "data": report.data,
        "audit": {
            "events_scanned": report.audit.events_scanned if report.audit else 0,
            "projection_hash": report.audit.projection_hash if report.audit else "",
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_reports_ledger(request):
    """Get current ledger balances."""
    gw = get_truth_gateway()
    report = gw.get_ledger_balances()
    return _ok({
        "report_id": report.report_id,
        "data": report.data,
        "audit": {
            "events_scanned": report.audit.events_scanned if report.audit else 0,
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_reports_trial_balance(request):
    """Get trial balance."""
    gw = get_truth_gateway()
    report = gw.get_trial_balance()
    return _ok({
        "report_id": report.report_id,
        "data": report.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_reports_employees(request):
    """Get employee roster."""
    gw = get_truth_gateway()
    report = gw.get_employee_roster()
    return _ok({
        "report_id": report.report_id,
        "data": report.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_reports_orders(request):
    """Get order status report."""
    gw = get_truth_gateway()
    report = gw.get_order_status()
    return _ok({
        "report_id": report.report_id,
        "data": report.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_store_summary(request):
    """Get Event Store summary."""
    gw = get_truth_gateway()
    return _ok(gw.get_store_summary())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def truth_consistency(request):
    """Run consistency check on Event Store."""
    gw = get_truth_gateway()
    result = gw.run_consistency_check()
    return _ok({
        "consistent": result.consistent,
        "total_events": result.total_events,
        "events_by_domain": result.events_by_domain,
        "sequence_gaps": len(result.sequence_gaps),
        "timestamp_anomalies": len(result.timestamp_anomalies),
    })

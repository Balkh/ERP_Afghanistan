"""
Phase 5B.8 — Autonomous Intelligence REST API.

Read-only endpoints:
- /insights — domain/cross-domain intelligence
- /risk-summary — risk scoring
- /decision-options — structured decision alternatives
- /forecast — deterministic predictions
- /anomaly-warning — early warning signals
- /report — full intelligence report
- /recommendations — non-executable recommendations
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from typing import Any

from core.operations.intelligence_autonomous.gateway import AutonomousIntelligenceGateway


_gateway: AutonomousIntelligenceGateway = None


def _get_gw() -> AutonomousIntelligenceGateway:
    global _gateway
    if _gateway is None:
        _gateway = AutonomousIntelligenceGateway()
    return _gateway


def _ok(data: Any, status: int = 200) -> Response:
    return Response({"success": True, "data": data}, status=status)


def _err(msg: str, code: str = "AUTO_001", status: int = 400) -> Response:
    return Response({"success": False, "error": {"code": code, "message": msg}}, status=status)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_insights(request):
    """Get domain-specific or all insights."""
    domain = request.query_params.get('domain', '')
    gw = _get_gw()
    try:
        insights = gw.get_insights(domain)
        return _ok({
            "insight_count": len(insights),
            "insights": [{
                "insight_id": i.insight_id,
                "title": i.title,
                "description": i.description,
                "domain": i.domain,
                "severity": i.severity.value,
                "supporting_events": i.supporting_event_ids,
            } for i in insights],
        })
    except Exception as e:
        return _err(str(e), "AUTO_INSIGHTS_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_risk_summary(request):
    """Get cross-domain risk summary."""
    gw = _get_gw()
    try:
        return _ok(gw.get_risk_summary())
    except Exception as e:
        return _err(str(e), "AUTO_RISK_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_decision_options(request):
    """Get structured decision options (non-executable)."""
    gw = _get_gw()
    try:
        decisions = gw.get_decision_options()
        return _ok({
            "decision_count": len(decisions),
            "decisions": [{
                "decision_id": d.decision_id,
                "decision_type": d.decision_type,
                "domain": d.domain,
                "context_summary": d.context_summary,
                "options": [{
                    "option_id": o.option_id,
                    "action_summary": o.action_summary,
                    "risk_level": o.risk_level,
                    "confidence": o.confidence,
                } for o in d.options],
                "recommended_option_id": d.recommended_option_id,
            } for d in decisions],
        })
    except Exception as e:
        return _err(str(e), "AUTO_DEC_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_forecast(request):
    """Get deterministic forecasts."""
    gw = _get_gw()
    try:
        forecasts = gw.get_forecasts()
        return _ok({
            "forecast_count": len(forecasts),
            "forecasts": [{
                "forecast_id": f.forecast_id,
                "domain": f.domain,
                "metric": f.metric,
                "current_value": f.current_value,
                "predicted_value": f.predicted_value,
                "direction": f.direction.value,
                "confidence_interval": [f.confidence_interval_low, f.confidence_interval_high],
                "supporting_event_count": f.supporting_event_count,
            } for f in forecasts],
        })
    except Exception as e:
        return _err(str(e), "AUTO_FORECAST_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_anomaly_warnings(request):
    """Get predicted anomaly warnings."""
    gw = _get_gw()
    try:
        warnings = gw.get_anomaly_warnings()
        return _ok({
            "warning_count": len(warnings),
            "warnings": [{
                "warning_id": w.warning_id,
                "domain": w.domain,
                "signal_type": w.signal_type,
                "severity": w.severity.value,
                "description": w.description,
                "deviation_pct": w.deviation_pct,
                "confidence_score": w.confidence_score,
                "estimated_occurrence": w.estimated_occurrence,
            } for w in warnings],
        })
    except Exception as e:
        return _err(str(e), "AUTO_WARN_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_full_report(request):
    """Get complete enterprise intelligence report."""
    gw = _get_gw()
    domain = request.query_params.get('domain', 'enterprise')
    try:
        report = gw.get_full_report(domain)
        return _ok({
            "report_id": report.report_id,
            "domain_scope": report.domain_scope,
            "risk_score_overall": report.risk_score_overall,
            "confidence_score_overall": report.confidence_score_overall,
            "insight_count": len(report.insights),
            "recommendation_count": len(report.recommendations),
            "forecast_count": len(report.forecasts),
            "warning_count": len(report.anomaly_warnings),
            "supporting_events": report.supporting_events[:20],
            "projection_hash": report.projection_hash,
        })
    except Exception as e:
        return _err(str(e), "AUTO_REPORT_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_recommendations(request):
    """Get non-executable recommendations."""
    gw = _get_gw()
    try:
        recs = gw.get_recommendations()
        return _ok({
            "recommendation_count": len(recs),
            "recommendations": [{
                "recommendation_id": r.recommendation_id,
                "title": r.title,
                "description": r.description,
                "decision_type": r.decision_type,
                "risk_level": r.risk_level,
                "confidence_score": r.confidence_score,
                "options": r.options,
            } for r in recs],
        })
    except Exception as e:
        return _err(str(e), "AUTO_REC_001")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auto_status(request):
    """Get autonomous intelligence gateway status."""
    gw = _get_gw()
    return _ok(gw.get_status())

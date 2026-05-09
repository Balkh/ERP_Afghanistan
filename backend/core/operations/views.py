"""
Operations API Views.
Exposes operational metrics and health data.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from core.operations.health import HealthMonitor
from core.operations.financial import FinancialIntegrityMonitor
from core.operations.inventory import InventoryIntegrityMonitor
from core.operations.alerts import AlertManager, AlertSeverity, AlertCategory
from core.operations.postgres_audit import PostgresReadinessAudit
from core.operations.api_observability import get_metrics, get_observability_summary
from core.operations.scalability import run_scalability_audit, DatabaseScaler
from core.operations.concurrency import run_concurrency_safety_check
from core.operations.integrity import DataIntegrityRunner
from core.operations.trends import ObservabilityDashboard, TrendAnalyzer, AnomalyClustering
from core.operations.guardrails import get_guardrail_status, AdaptiveSamplingSystem, AlertNoiseReducer, GuardrailConfig
from core.operations.stability import get_stability_status, ConfigurationDriftDetector


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Full health check."""
    return Response(HealthMonitor.get_full_health())


@api_view(['GET'])
@permission_classes([AllowAny])
def health_database(request):
    """Database health check."""
    return Response(HealthMonitor.check_database())


@api_view(['GET'])
@permission_classes([AllowAny])
def health_system(request):
    """System resources health check."""
    return Response(HealthMonitor.check_system())


@api_view(['GET'])
@permission_classes([AllowAny])
def financial_integrity(request):
    """Financial integrity audit."""
    return Response(FinancialIntegrityMonitor.run_full_audit())


@api_view(['GET'])
@permission_classes([AllowAny])
def inventory_integrity(request):
    """Inventory integrity audit."""
    return Response(InventoryIntegrityMonitor.run_full_audit())


@api_view(['GET'])
@permission_classes([AllowAny])
def alerts_list(request):
    """Get recent alerts."""
    hours = int(request.query_params.get('hours', 24))
    limit = int(request.query_params.get('limit', 100))
    severity = request.query_params.get('severity')
    category = request.query_params.get('category')

    alerts = AlertManager.get_recent_alerts(hours, limit)

    if severity:
        try:
            severity_enum = AlertSeverity[severity.upper()]
            alerts = [a for a in alerts if a.severity == severity_enum]
        except KeyError:
            pass

    if category:
        try:
            category_enum = AlertCategory[category.upper()]
            alerts = [a for a in alerts if a.category == category_enum]
        except KeyError:
            pass

    return Response({
        'alerts': [a.to_dict() for a in alerts],
        'count': len(alerts)
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def alerts_clear(request):
    """Clear all alerts."""
    AlertManager.clear_alerts()
    return Response({'status': 'cleared'})


@api_view(['GET'])
@permission_classes([AllowAny])
def postgres_readiness(request):
    """PostgreSQL migration readiness audit."""
    return Response(PostgresReadinessAudit.run_full_audit())


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_summary(request):
    """Complete observability summary."""
    return Response({
        'health': HealthMonitor.get_full_health(),
        'alerts': {
            'recent': [a.to_dict() for a in AlertManager.get_recent_alerts(hours=24, limit=10)]
        },
        'postgres_readiness': PostgresReadinessAudit.run_full_audit()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_bad_requests(request):
    """Get bad request metrics."""
    hours = int(request.query_params.get('hours', 24))
    limit = int(request.query_params.get('limit', 100))
    metrics = get_metrics()
    return Response({
        'bad_requests': metrics.get_bad_requests(hours, limit),
        'top_endpoints': metrics.get_top_bad_endpoints(hours),
        'total_count': len(metrics.get_bad_requests(hours)),
        'error_rates': metrics.get_error_rates()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_slow_requests(request):
    """Get slow request metrics."""
    hours = int(request.query_params.get('hours', 24))
    limit = int(request.query_params.get('limit', 100))
    metrics = get_metrics()
    return Response({
        'slow_requests': metrics.get_slow_requests(hours, limit),
        'top_endpoints': metrics.get_top_slow_endpoints(hours),
        'total_count': len(metrics.get_slow_requests(hours))
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_observability_detail(request):
    """Get detailed API observability summary."""
    hours = int(request.query_params.get('hours', 24))
    return Response(get_observability_summary(hours))


@api_view(['GET'])
@permission_classes([AllowAny])
def scalability_audit(request):
    """Database scalability audit."""
    return Response(run_scalability_audit())


@api_view(['GET'])
@permission_classes([AllowAny])
def database_record_counts(request):
    """Get record counts for major tables."""
    return Response(DatabaseScaler.get_record_counts())


@api_view(['GET'])
@permission_classes([AllowAny])
def concurrency_safety(request):
    """Concurrency safety check."""
    return Response(run_concurrency_safety_check())


@api_view(['GET'])
@permission_classes([AllowAny])
def data_integrity_check(request):
    """Run full data integrity check."""
    return Response(DataIntegrityRunner.run_full_integrity_check())


@api_view(['GET'])
@permission_classes([AllowAny])
def data_integrity_summary(request):
    """Get data integrity summary."""
    return Response(DataIntegrityRunner.get_integrity_summary())


@api_view(['GET'])
@permission_classes([AllowAny])
def observability_dashboard(request):
    """Get complete observability dashboard."""
    hours = int(request.query_params.get('hours', 24))
    return Response(ObservabilityDashboard.get_dashboard_data(hours))


@api_view(['GET'])
@permission_classes([AllowAny])
def performance_trends(request):
    """Get performance trend analysis."""
    hours = int(request.query_params.get('hours', 24))
    return Response({
        'error_trend': TrendAnalyzer.get_error_rate_trend(hours),
        'latency_trend': TrendAnalyzer.get_latency_trend(hours)
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def anomaly_clusters(request):
    """Get anomaly clustering data."""
    hours = int(request.query_params.get('hours', 24))
    return Response({
        'repeated_failures': AnomalyClustering.get_repeated_failure_clusters(hours),
        'repeated_slow': AnomalyClustering.get_repeated_slow_clusters(hours),
        'suspicious_ips': AnomalyClustering.get_suspicious_ips(hours)
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def guardrail_status(request):
    """Get comprehensive guardrail status."""
    return Response(get_guardrail_status())


@api_view(['GET'])
@permission_classes([AllowAny])
def sampling_status(request):
    """Get sampling strategy status."""
    policy = AdaptiveSamplingSystem.get_sampling_policy()
    return Response({
        'version': policy['version'],
        'implementation': policy['implementation'],
        'sampling_policy': policy['sampling_policy']
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def stability_status(request):
    """Get system stability status."""
    ConfigurationDriftDetector.capture_snapshot()
    return Response(get_stability_status())
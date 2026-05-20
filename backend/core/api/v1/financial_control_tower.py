"""Phase 18 — Financial Control Tower API.

Unified endpoints for the Financial Control Tower dashboard.
All endpoints are on-demand (no polling, no background jobs).

GET /api/financial/control-tower/summary/
GET /api/financial/control-tower/alerts/
GET /api/financial/control-tower/decisions/
POST /api/financial/control-tower/re-evaluate/
"""
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from core.services.financial_policy_engine import FinancialPolicyEngine
from core.models.decision_record import DecisionRecord


def _ok(data):
    return Response(data)


def _err(message, code="CT_001", status=400):
    return Response({"error": {"code": code, "message": message}}, status=status)


@api_view(['GET'])
@permission_classes([AllowAny])
def control_tower_summary(request):
    """Unified summary: SSOT + FCUE + FICL + Policy aggregation."""
    try:
        from core.services.financial_diagnostics import FinancialDiagnostics
        from core.services.anomaly_detection import AnomalyDetectionEngine
        from core.services.cashflow_observability import CashflowObservability
        from core.services.financial_truth_engine import FinancialTruthEngine
        from sales.models import Customer
        from purchases.models import Supplier

        # System health
        health = FinancialDiagnostics.run_full_health_check()

        # Anomaly index
        anomaly_report = AnomalyDetectionEngine.detect_all()

        # Cashflow
        cashflow = CashflowObservability.get_cashflow_summary(days=30)

        # Risk distribution
        risk_distribution = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0, 'MINIMAL': 0}
        for customer in Customer.objects.filter(status='ACTIVE')[:100]:
            decision = FinancialPolicyEngine.evaluate_customer(customer)
            if decision.risk_score >= 80:
                risk_distribution['CRITICAL'] += 1
            elif decision.risk_score >= 60:
                risk_distribution['HIGH'] += 1
            elif decision.risk_score >= 40:
                risk_distribution['MEDIUM'] += 1
            elif decision.risk_score >= 20:
                risk_distribution['LOW'] += 1
            else:
                risk_distribution['MINIMAL'] += 1

        # Credit exposure
        total_exposure = Decimal('0.00')
        for customer in Customer.objects.filter(status='ACTIVE')[:200]:
            balance = FinancialTruthEngine.get_customer_balance(customer)
            if balance > 0:
                total_exposure += balance

        return _ok({
            'health_score': health['health_score'],
            'health_status': health['status'],
            'anomaly_index': anomaly_report['total_anomalies'],
            'reconciliation_health': health['components']['reconciliation_lag']['status'],
            'cashflow_status': cashflow.get('net_liquidity', '0.00'),
            'cashflow_trend': cashflow.get('inflow_trend', 'STABLE'),
            'total_credit_exposure': str(total_exposure),
            'risk_distribution': risk_distribution,
            'ssot_consistency_pct': health['components']['ssot_consistency']['consistency_pct'],
            'warnings': health['warnings'],
            'critical': health['critical'],
            'safe_mode': health['components']['ssot_consistency']['mismatch_count'] > 0,
        })
    except Exception as e:
        return _err(str(e), "CT_SUMMARY_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def control_tower_alerts(request):
    """Active WARN / BLOCK / ESCALATE alerts only."""
    try:
        alerts = DecisionRecord.objects.filter(
            lifecycle_state='ACTIVE',
            decision_type__in=['WARN', 'SOFT_BLOCK', 'HARD_BLOCK', 'ESCALATE_MANAGER'],
        ).order_by('-timestamp')[:100]

        return _ok({
            'active_alerts': [
                {
                    'id': str(a.id),
                    'entity_type': a.entity_type,
                    'entity_id': a.entity_id,
                    'decision_type': a.decision_type,
                    'risk_score': a.risk_score,
                    'triggered_rules': a.triggered_rules,
                    'explanation': a.explanation,
                    'timestamp': a.timestamp.isoformat(),
                }
                for a in alerts
            ],
            'total_alerts': alerts.count(),
        })
    except Exception as e:
        return _err(str(e), "CT_ALERTS_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def control_tower_decisions(request):
    """Last 100 DecisionRecords."""
    try:
        limit = int(request.query_params.get('limit', 100))
        decisions = DecisionRecord.objects.order_by('-timestamp')[:limit]

        return _ok({
            'decisions': [
                {
                    'id': str(d.id),
                    'entity_type': d.entity_type,
                    'entity_id': d.entity_id,
                    'decision_type': d.decision_type,
                    'lifecycle_state': d.lifecycle_state,
                    'risk_score': d.risk_score,
                    'triggered_rules': d.triggered_rules,
                    'explanation': d.explanation,
                    'timestamp': d.timestamp.isoformat(),
                    'source_modules': d.source_modules,
                }
                for d in decisions
            ],
            'total': decisions.count(),
        })
    except Exception as e:
        return _err(str(e), "CT_DECISIONS_001")


@api_view(['POST'])
@permission_classes([AllowAny])
def control_tower_reevaluate(request):
    """Synchronous policy recomputation ONLY (no background jobs)."""
    try:
        result = FinancialPolicyEngine.re_evaluate_all()
        return _ok(result)
    except Exception as e:
        return _err(str(e), "CT_REEVAL_001")

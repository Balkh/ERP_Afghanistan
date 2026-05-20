"""Phase 17 — Financial Intelligence API Views.

Thin REST endpoints for all 6 FICL modules:
1. Anomaly Detection
2. Reconciliation Assistance V2
3. Credit Risk Intelligence
4. Cashflow Observability
5. Financial Explainability
6. Financial Diagnostics

All endpoints are GET-only (read-only intelligence).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def _ok(data, message=""):
    return Response(data)


def _err(message, code="FICL_001", status=400):
    return Response({"error": {"code": code, "message": message}}, status=status)


def _get_model(model_name, pk):
    """Resolve a model instance by name and UUID."""
    if model_name == 'customer':
        from sales.models import Customer
        return Customer.objects.filter(pk=pk).first()
    elif model_name == 'supplier':
        from purchases.models import Supplier
        return Supplier.objects.filter(pk=pk).first()
    elif model_name == 'sales_invoice':
        from sales.models import SalesInvoice
        return SalesInvoice.objects.filter(pk=pk).first()
    elif model_name == 'purchase_invoice':
        from purchases.models import PurchaseInvoice
        return PurchaseInvoice.objects.filter(pk=pk).first()
    elif model_name == 'customer_payment':
        from sales.models import CustomerPayment
        return CustomerPayment.objects.filter(pk=pk).first()
    elif model_name == 'supplier_payment':
        from purchases.models import SupplierPayment
        return SupplierPayment.objects.filter(pk=pk).first()
    return None


# ─── 1. Anomaly Detection ───

@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_anomalies(request):
    """Run all anomaly detectors and return structured report."""
    from core.services.anomaly_detection import AnomalyDetectionEngine
    try:
        threshold = int(request.query_params.get('days_past_due', 30))
        report = AnomalyDetectionEngine.detect_all(days_past_due_threshold=threshold)
        return _ok(report, f"Anomaly scan complete: {report['total_anomalies']} anomalies found.")
    except Exception as e:
        return _err(str(e), "FICL_ANOMALY_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_anomalies_payments(request):
    """Detect payment-specific anomalies."""
    from core.services.anomaly_detection import AnomalyDetectionEngine
    try:
        anomalies = AnomalyDetectionEngine.detect_payment_anomalies()
        return _ok({'anomalies': anomalies, 'count': len(anomalies)})
    except Exception as e:
        return _err(str(e), "FICL_ANOMALY_PAY_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_anomalies_invoices(request):
    """Detect invoice-specific anomalies."""
    from core.services.anomaly_detection import AnomalyDetectionEngine
    try:
        threshold = int(request.query_params.get('days_past_due', 30))
        anomalies = AnomalyDetectionEngine.detect_invoice_anomalies(days_past_due_threshold=threshold)
        return _ok({'anomalies': anomalies, 'count': len(anomalies)})
    except Exception as e:
        return _err(str(e), "FICL_ANOMALY_INV_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_anomalies_ledger(request):
    """Detect ledger-specific anomalies."""
    from core.services.anomaly_detection import AnomalyDetectionEngine
    try:
        anomalies = AnomalyDetectionEngine.detect_ledger_anomalies()
        return _ok({'anomalies': anomalies, 'count': len(anomalies)})
    except Exception as e:
        return _err(str(e), "FICL_ANOMALY_LEDGER_001")


# ─── 2. Reconciliation Assistance V2 ───

@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_reconciliation_suggest_customer(request, customer_id):
    """Suggest payment-invoice matches for a customer."""
    from core.services.reconciliation_v2 import ReconciliationAssistanceV2
    customer = _get_model('customer', customer_id)
    if not customer:
        return _err("Customer not found", "FICL_REC_001", 404)
    try:
        suggestions = ReconciliationAssistanceV2.suggest_customer_matches(customer)
        return _ok({
            'customer_id': customer_id,
            'customer_name': customer.name,
            'suggestions': suggestions,
            'count': len(suggestions),
        })
    except Exception as e:
        return _err(str(e), "FICL_REC_002")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_reconciliation_suggest_supplier(request, supplier_id):
    """Suggest supplier payment-invoice matches."""
    from core.services.reconciliation_v2 import ReconciliationAssistanceV2
    supplier = _get_model('supplier', supplier_id)
    if not supplier:
        return _err("Supplier not found", "FICL_REC_003", 404)
    try:
        suggestions = ReconciliationAssistanceV2.suggest_supplier_matches(supplier)
        return _ok({
            'supplier_id': supplier_id,
            'supplier_name': supplier.name,
            'suggestions': suggestions,
            'count': len(suggestions),
        })
    except Exception as e:
        return _err(str(e), "FICL_REC_004")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_reconciliation_unresolved(request):
    """Get all unresolved reconciliation items."""
    from core.services.reconciliation_v2 import ReconciliationAssistanceV2
    try:
        items = ReconciliationAssistanceV2.get_unresolved_items()
        return _ok(items)
    except Exception as e:
        return _err(str(e), "FICL_REC_005")


# ─── 3. Credit Risk Intelligence ───

@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_credit_risk_assess(request, customer_id):
    """Full credit risk assessment for a customer."""
    from core.services.credit_risk_intelligence import CreditRiskIntelligence
    customer = _get_model('customer', customer_id)
    if not customer:
        return _err("Customer not found", "FICL_RISK_001", 404)
    try:
        assessment = CreditRiskIntelligence.assess_customer_risk(customer)
        return _ok(assessment)
    except Exception as e:
        return _err(str(e), "FICL_RISK_002")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_credit_risk_high_risk(request):
    """Get all high-risk customers."""
    from core.services.credit_risk_intelligence import CreditRiskIntelligence
    try:
        threshold = int(request.query_params.get('threshold', 60))
        customers = CreditRiskIntelligence.get_high_risk_customers(threshold=threshold)
        return _ok({
            'high_risk_customers': customers,
            'count': len(customers),
            'threshold': threshold,
        })
    except Exception as e:
        return _err(str(e), "FICL_RISK_003")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_credit_risk_predict(request, customer_id):
    """Predict credit breach for a customer."""
    from core.services.credit_risk_intelligence import CreditRiskIntelligence
    customer = _get_model('customer', customer_id)
    if not customer:
        return _err("Customer not found", "FICL_RISK_004", 404)
    try:
        days = int(request.query_params.get('days', 30))
        prediction = CreditRiskIntelligence.predict_credit_breach(customer, days_ahead=days)
        return _ok(prediction)
    except Exception as e:
        return _err(str(e), "FICL_RISK_005")


# ─── 4. Cashflow Observability ───

@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_cashflow_summary(request):
    """Get cashflow summary for last N days."""
    from core.services.cashflow_observability import CashflowObservability
    try:
        days = int(request.query_params.get('days', 30))
        summary = CashflowObservability.get_cashflow_summary(days=days)
        return _ok(summary)
    except Exception as e:
        return _err(str(e), "FICL_CASH_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_liquidity_snapshot(request):
    """Get point-in-time liquidity snapshot."""
    from core.services.cashflow_observability import CashflowObservability
    try:
        snapshot = CashflowObservability.get_liquidity_snapshot()
        return _ok(snapshot)
    except Exception as e:
        return _err(str(e), "FICL_CASH_002")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_outstanding_exposure(request):
    """Get outstanding exposure with aging buckets."""
    from core.services.cashflow_observability import CashflowObservability
    try:
        exposure = CashflowObservability.get_outstanding_exposure()
        return _ok(exposure)
    except Exception as e:
        return _err(str(e), "FICL_CASH_003")


# ─── 5. Financial Explainability ───

@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_explain_customer(request, customer_id):
    """Explain customer balance with full trace."""
    from core.services.financial_explainability import FinancialExplainability
    customer = _get_model('customer', customer_id)
    if not customer:
        return _err("Customer not found", "FICL_EXP_001", 404)
    try:
        explanation = FinancialExplainability.explain_customer_balance(customer)
        return _ok(explanation)
    except Exception as e:
        return _err(str(e), "FICL_EXP_002")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_explain_supplier(request, supplier_id):
    """Explain supplier balance with full trace."""
    from core.services.financial_explainability import FinancialExplainability
    supplier = _get_model('supplier', supplier_id)
    if not supplier:
        return _err("Supplier not found", "FICL_EXP_003", 404)
    try:
        explanation = FinancialExplainability.explain_supplier_balance(supplier)
        return _ok(explanation)
    except Exception as e:
        return _err(str(e), "FICL_EXP_004")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_trace_invoice(request, model_name, invoice_id):
    """Full trace chain for a specific invoice."""
    from core.services.financial_explainability import FinancialExplainability
    invoice = _get_model(model_name, invoice_id)
    if not invoice:
        return _err(f"Invoice not found ({model_name})", "FICL_EXP_005", 404)
    try:
        trace = FinancialExplainability.trace_invoice(invoice)
        return _ok(trace)
    except Exception as e:
        return _err(str(e), "FICL_EXP_006")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_trace_payment(request, model_name, payment_id):
    """Full trace chain for a specific payment."""
    from core.services.financial_explainability import FinancialExplainability
    payment = _get_model(model_name, payment_id)
    if not payment:
        return _err(f"Payment not found ({model_name})", "FICL_EXP_007", 404)
    try:
        trace = FinancialExplainability.trace_payment(payment)
        return _ok(trace)
    except Exception as e:
        return _err(str(e), "FICL_EXP_008")


# ─── 6. Financial Diagnostics ───

@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_health(request):
    """Run full financial health check."""
    from core.services.financial_diagnostics import FinancialDiagnostics
    try:
        health = FinancialDiagnostics.run_full_health_check()
        return _ok(health, f"Health score: {health['health_score']}/100 ({health['status']})")
    except Exception as e:
        return _err(str(e), "FICL_HEALTH_001")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_health_ssot(request):
    """Check SSOT consistency."""
    from core.services.financial_diagnostics import FinancialDiagnostics
    try:
        result = FinancialDiagnostics.check_ssot_consistency()
        return _ok(result)
    except Exception as e:
        return _err(str(e), "FICL_HEALTH_002")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_health_ledger(request):
    """Check ledger integrity."""
    from core.services.financial_diagnostics import FinancialDiagnostics
    try:
        result = FinancialDiagnostics.check_ledger_integrity()
        return _ok(result)
    except Exception as e:
        return _err(str(e), "FICL_HEALTH_003")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_health_fifo(request):
    """Check FIFO allocation integrity."""
    from core.services.financial_diagnostics import FinancialDiagnostics
    try:
        result = FinancialDiagnostics.check_fifo_allocation_integrity()
        return _ok(result)
    except Exception as e:
        return _err(str(e), "FICL_HEALTH_004")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_health_credit(request):
    """Check credit enforcement coverage."""
    from core.services.financial_diagnostics import FinancialDiagnostics
    try:
        result = FinancialDiagnostics.check_credit_enforcement_coverage()
        return _ok(result)
    except Exception as e:
        return _err(str(e), "FICL_HEALTH_005")


@api_view(['GET'])
@permission_classes([AllowAny])
def ficl_health_reconciliation(request):
    """Check reconciliation lag."""
    from core.services.financial_diagnostics import FinancialDiagnostics
    try:
        result = FinancialDiagnostics.check_reconciliation_lag()
        return _ok(result)
    except Exception as e:
        return _err(str(e), "FICL_HEALTH_006")

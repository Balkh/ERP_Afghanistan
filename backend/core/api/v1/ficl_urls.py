"""Phase 17 — Financial Intelligence API URL routes."""
from django.urls import path
from . import ficl_views

urlpatterns = [
    # 1. Anomaly Detection
    path('anomalies/', ficl_views.ficl_anomalies, name='ficl-anomalies'),
    path('anomalies/payments/', ficl_views.ficl_anomalies_payments, name='ficl-anomalies-payments'),
    path('anomalies/invoices/', ficl_views.ficl_anomalies_invoices, name='ficl-anomalies-invoices'),
    path('anomalies/ledger/', ficl_views.ficl_anomalies_ledger, name='ficl-anomalies-ledger'),

    # 2. Reconciliation Assistance V2
    path('reconciliation/suggest/customer/<uuid:customer_id>/', ficl_views.ficl_reconciliation_suggest_customer, name='ficl-rec-suggest-customer'),
    path('reconciliation/suggest/supplier/<uuid:supplier_id>/', ficl_views.ficl_reconciliation_suggest_supplier, name='ficl-rec-suggest-supplier'),
    path('reconciliation/unresolved/', ficl_views.ficl_reconciliation_unresolved, name='ficl-rec-unresolved'),

    # 3. Credit Risk Intelligence
    path('credit-risk/assess/<uuid:customer_id>/', ficl_views.ficl_credit_risk_assess, name='ficl-risk-assess'),
    path('credit-risk/high-risk/', ficl_views.ficl_credit_risk_high_risk, name='ficl-risk-high'),
    path('credit-risk/predict/<uuid:customer_id>/', ficl_views.ficl_credit_risk_predict, name='ficl-risk-predict'),

    # 4. Cashflow Observability
    path('cashflow/', ficl_views.ficl_cashflow_summary, name='ficl-cashflow'),
    path('cashflow/liquidity/', ficl_views.ficl_liquidity_snapshot, name='ficl-liquidity'),
    path('cashflow/exposure/', ficl_views.ficl_outstanding_exposure, name='ficl-exposure'),

    # 5. Financial Explainability
    path('explain/customer/<uuid:customer_id>/', ficl_views.ficl_explain_customer, name='ficl-explain-customer'),
    path('explain/supplier/<uuid:supplier_id>/', ficl_views.ficl_explain_supplier, name='ficl-explain-supplier'),
    path('trace/invoice/<str:model_name>/<uuid:invoice_id>/', ficl_views.ficl_trace_invoice, name='ficl-trace-invoice'),
    path('trace/payment/<str:model_name>/<uuid:payment_id>/', ficl_views.ficl_trace_payment, name='ficl-trace-payment'),

    # 6. Financial Diagnostics
    path('health/', ficl_views.ficl_health, name='ficl-health'),
    path('health/ssot/', ficl_views.ficl_health_ssot, name='ficl-health-ssot'),
    path('health/ledger/', ficl_views.ficl_health_ledger, name='ficl-health-ledger'),
    path('health/fifo/', ficl_views.ficl_health_fifo, name='ficl-health-fifo'),
    path('health/credit/', ficl_views.ficl_health_credit, name='ficl-health-credit'),
    path('health/reconciliation/', ficl_views.ficl_health_reconciliation, name='ficl-health-reconciliation'),
]

"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls.static import static
from core.operations import views as ops_views
from core.operations.views import decisions_list, decisions_detail, decisions_evaluate_event
from core.operations.control_center import (
    control_center, quick_stats, health_live, financial_summary,
    inventory_summary, operations_summary, hr_summary,
    operational_intelligence, signal_summary, active_signals, register_signal,
    jobs_dashboard
)
from core.operations.decision_engine import get_active_decisions, get_decision_summary, evaluate_event_decisions


@csrf_exempt
def health(request):
    """Health check endpoint."""
    return JsonResponse({
        "status": "healthy",
        "version": "1.0.0"
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/health/db/', ops_views.health_database, name='health-db'),
    path('api/health/system/', ops_views.health_system, name='health-system'),
    path('api/ops/health/', ops_views.health_check, name='ops-health'),
    path('api/ops/financial-integrity/', ops_views.financial_integrity, name='financial-integrity'),
    path('api/ops/inventory-integrity/', ops_views.inventory_integrity, name='inventory-integrity'),
    path('api/ops/alerts/', ops_views.alerts_list, name='alerts-list'),
    path('api/ops/alerts/clear/', ops_views.alerts_clear, name='alerts-clear'),
    path('api/ops/postgres-readiness/', ops_views.postgres_readiness, name='postgres-readiness'),
    path('api/ops/summary/', ops_views.observability_summary, name='ops-summary'),
    path('api/ops/bad-requests/', ops_views.api_bad_requests, name='api-bad-requests'),
    path('api/ops/slow-requests/', ops_views.api_slow_requests, name='api-slow-requests'),
    path('api/ops/api-detail/', ops_views.api_observability_detail, name='api-observability-detail'),
    path('api/ops/scalability/', ops_views.scalability_audit, name='scalability-audit'),
    path('api/ops/db-records/', ops_views.database_record_counts, name='db-records'),
    path('api/ops/concurrency/', ops_views.concurrency_safety, name='concurrency-safety'),
    path('api/ops/integrity/', ops_views.data_integrity_check, name='data-integrity'),
    path('api/ops/integrity-summary/', ops_views.data_integrity_summary, name='integrity-summary'),
    path('api/ops/dashboard/', ops_views.observability_dashboard, name='observability-dashboard'),
    path('api/ops/trends/', ops_views.performance_trends, name='performance-trends'),
    path('api/ops/anomalies/', ops_views.anomaly_clusters, name='anomaly-clusters'),
    path('api/ops/guardrails/', ops_views.guardrail_status, name='guardrail-status'),
    path('api/ops/sampling/', ops_views.sampling_status, name='sampling-status'),
    path('api/ops/stability/', ops_views.stability_status, name='stability-status'),
    path('api/control-center/', control_center, name='control-center'),
    path('api/control-center/stats/', quick_stats, name='control-stats'),
    path('api/control-center/health/', health_live, name='control-health'),
    path('api/control-center/financial/', financial_summary, name='control-financial'),
    path('api/control-center/inventory/', inventory_summary, name='control-inventory'),
    path('api/control-center/operations/', operations_summary, name='control-operations'),
    path('api/control-center/hr/', hr_summary, name='control-hr'),
    path('api/control-center/intelligence/', operational_intelligence, name='operational-intelligence'),
    path('api/control-center/signals/', signal_summary, name='signal-summary'),
    path('api/control-center/signals/active/', active_signals, name='active-signals'),
    path('api/control-center/signals/register/', register_signal, name='register-signal'),
    path('api/control-center/decisions/', decisions_list, name='decisions-list'),
    path('api/control-center/decisions/detail/', decisions_detail, name='decisions-detail'),
    path('api/control-center/decisions/evaluate/', decisions_evaluate_event, name='decisions-evaluate'),
    path('api/control-center/jobs/', jobs_dashboard, name='control-jobs'),
    path('api/auth/', include('security.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/sales/', include('sales.urls')),
    path('api/purchases/', include('purchases.urls')),
    path('api/returns/', include('returns.urls')),
    path('api/accounting/', include('accounting.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/expenses/', include('expenses.urls')),
    path('api/licensing/', include('licensing.urls')),
    # path('api/reports/', include('reports.urls')),  # Removed: empty scaffold

    path('api/backup/', include('backup.urls')),
    path('api/hr/', include('hr.urls')),
    path('api/payroll/', include('payroll.urls')),
    path('api/assets/', include('fixed_assets.urls')),
    path('api/budgets/', include('budgeting.urls')),
    path('api/tax/', include('tax.urls')),
    path('api/cost-centers/', include('cost_centers.urls')),
    path('api/entities/', include('entities.urls')),
    path('api/audit/', include('audit.urls')),
    path('api/cashflow/', include('cashflow.urls')),
    # path('api/dashboard/', include('dashboard.urls')),  # Removed: zero frontend consumers

    # path('api/analytics/', include('analytics.urls')),  # Removed: logic consolidated into control-center + native apps

    path('api/workflows/', include('workflows.urls')),
    path('api/jobs/', include('jobs.urls')),
    path('api/core/', include('core.urls')),
    path('api/observability/v1/', include('core.operations.observability.urls')),
    path('api/insurance/', include('insurance.urls')),

    # ─── Phase 5B.6 — API v1 Integration Layer ───
    path('api/v1/governance/', include('core.api.v1.governance_urls')),
    path('api/v1/truth/', include('core.api.v1.truth_urls')),
    path('api/v1/observability/', include('core.api.v1.observability_urls')),
    path('api/v1/intelligence/', include('core.api.v1.intelligence_urls')),
    path('api/v1/autonomous/', include('core.api.v1.autonomous_urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
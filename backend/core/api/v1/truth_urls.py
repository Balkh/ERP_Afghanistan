from django.urls import path
from . import truth

urlpatterns = [
    # Event Store
    path('events/', truth.truth_events_list, name='v1-truth-events'),
    path('events/emit/', truth.truth_event_emit, name='v1-truth-event-emit'),
    path('events/<str:event_id>/', truth.truth_event_detail, name='v1-truth-event-detail'),
    path('events/<str:event_id>/exists/', truth.truth_event_exists, name='v1-truth-event-exists'),

    # Verification
    path('verify/', truth.truth_verify_claim, name='v1-truth-verify'),
    path('verify/<str:domain>/<str:aggregate_id>/', truth.truth_verify_aggregate, name='v1-truth-verify-aggregate'),

    # Projections
    path('projections/<str:domain>/rebuild/', truth.truth_projection_rebuild, name='v1-truth-projection-rebuild'),

    # Reports
    path('reports/stock-levels/', truth.truth_reports_stock_levels, name='v1-truth-reports-stock'),
    path('reports/ledger/', truth.truth_reports_ledger, name='v1-truth-reports-ledger'),
    path('reports/trial-balance/', truth.truth_reports_trial_balance, name='v1-truth-reports-tb'),
    path('reports/employees/', truth.truth_reports_employees, name='v1-truth-reports-employees'),
    path('reports/orders/', truth.truth_reports_orders, name='v1-truth-reports-orders'),

    # System
    path('summary/', truth.truth_store_summary, name='v1-truth-summary'),
    path('consistency/', truth.truth_consistency, name='v1-truth-consistency'),
]

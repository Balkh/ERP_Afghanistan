from django.urls import path
from . import intelligence

urlpatterns = [
    # Drift
    path('drift/baseline/<str:domain>/', intelligence.intel_drift_baseline, name='v1-intel-drift-baseline'),
    path('drift/<str:domain>/<str:aggregate_id>/', intelligence.intel_drift_aggregate, name='v1-intel-drift-agg'),
    path('drift/<str:domain>/', intelligence.intel_drift_all, name='v1-intel-drift-all'),

    # Patterns
    path('patterns/<str:domain>/', intelligence.intel_patterns, name='v1-intel-patterns'),
    path('patterns/<str:domain>/rare/', intelligence.intel_rare_events, name='v1-intel-rare'),
    path('patterns/<str:domain>/bursts/', intelligence.intel_bursts, name='v1-intel-bursts'),

    # Anomaly Graph
    path('anomalies/<str:domain>/', intelligence.intel_anomaly_graph, name='v1-intel-anomaly'),
    path('anomalies/cross-domain/', intelligence.intel_cross_domain_graph, name='v1-intel-anomaly-cross'),

    # Temporal
    path('temporal/<str:domain>/', intelligence.intel_temporal_drift, name='v1-intel-temporal'),

    # Consistency
    path('consistency/', intelligence.intel_consistency, name='v1-intel-consistency'),
    path('consistency/compare/', intelligence.intel_consistency_compare, name='v1-intel-consistency-compare'),

    # Snapshot
    path('snapshot/', intelligence.intel_snapshot, name='v1-intel-snapshot'),
    path('status/', intelligence.intel_status, name='v1-intel-status'),
]

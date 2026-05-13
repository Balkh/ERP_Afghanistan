from django.urls import path
from . import observability_api

urlpatterns = [
    # Trace
    path('trace/<str:domain>/<str:aggregate_id>/', observability_api.obs_trace_aggregate, name='v1-obs-trace'),
    path('trace/event/<str:event_id>/', observability_api.obs_trace_by_event, name='v1-obs-trace-event'),
    path('trace/<str:event_id>/causation/', observability_api.obs_causation_graph, name='v1-obs-causation'),

    # Timeline
    path('timeline/', observability_api.obs_timeline, name='v1-obs-timeline'),
    path('timeline/<str:domain>/<str:aggregate_id>/', observability_api.obs_timeline_aggregate, name='v1-obs-timeline-agg'),

    # Correlation
    path('correlation/<str:event_id>/', observability_api.obs_correlation_event, name='v1-obs-correlation'),
    path('correlation/<str:domain_a>/<str:domain_b>/', observability_api.obs_correlation_domains, name='v1-obs-correlation-domains'),
    path('correlation/dependencies/', observability_api.obs_domain_dependencies, name='v1-obs-dependencies'),

    # Integrity
    path('integrity/', observability_api.obs_integrity_check, name='v1-obs-integrity'),
    path('integrity/<str:domain>/', observability_api.obs_domain_integrity, name='v1-obs-domain-integrity'),

    # Replay
    path('replay/', observability_api.obs_replay_state, name='v1-obs-replay'),
    path('replay/render/<int:sequence>/', observability_api.obs_replay_render, name='v1-obs-replay-render'),
    path('replay/hash/', observability_api.obs_replay_hash, name='v1-obs-replay-hash'),

    # Dashboard
    path('dashboard/<str:dashboard_type>/', observability_api.obs_dashboard, name='v1-obs-dashboard'),
    path('snapshot/', observability_api.obs_snapshot, name='v1-obs-snapshot'),
    path('status/', observability_api.obs_status, name='v1-obs-status'),
    path('stream/', observability_api.obs_stream_metrics, name='v1-obs-stream'),
]

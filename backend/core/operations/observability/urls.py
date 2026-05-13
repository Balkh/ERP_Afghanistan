from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.observability_health, name='obs-health'),
    path('state/', views.observability_state, name='obs-state'),
    path('summary/', views.observability_frontend_summary, name='obs-summary'),
    path('timeline/', views.observability_timeline, name='obs-timeline'),
    path('incidents/', views.observability_incidents, name='obs-incidents'),
    path('dashboard/', views.observability_dashboard, name='obs-dashboard'),
    path('drift/', views.observability_drift, name='obs-drift'),
    path('telemetry/', views.observability_telemetry_aggregate, name='obs-telemetry'),
    path('replay/sessions/', views.observability_replay_sessions, name='obs-replay-sessions'),
    path('replay/sessions/<str:session_id>/', views.observability_replay_session_detail, name='obs-replay-session-detail'),
    path('digital-twin/', views.observability_digital_twin, name='obs-digital-twin'),
    path('safety/', views.observability_safety, name='obs-safety'),
]

from django.urls import path
from . import autonomous

urlpatterns = [
    path('insights/', autonomous.auto_insights, name='v1-auto-insights'),
    path('risk-summary/', autonomous.auto_risk_summary, name='v1-auto-risk'),
    path('decision-options/', autonomous.auto_decision_options, name='v1-auto-decisions'),
    path('forecast/', autonomous.auto_forecast, name='v1-auto-forecast'),
    path('anomaly-warnings/', autonomous.auto_anomaly_warnings, name='v1-auto-warnings'),
    path('report/', autonomous.auto_full_report, name='v1-auto-report'),
    path('recommendations/', autonomous.auto_recommendations, name='v1-auto-recs'),
    path('status/', autonomous.auto_status, name='v1-auto-status'),
]

"""Phase 18 — Financial Control Tower URL routes."""
from django.urls import path
from . import financial_control_tower

urlpatterns = [
    path('summary/', financial_control_tower.control_tower_summary, name='ct-summary'),
    path('alerts/', financial_control_tower.control_tower_alerts, name='ct-alerts'),
    path('decisions/', financial_control_tower.control_tower_decisions, name='ct-decisions'),
    path('re-evaluate/', financial_control_tower.control_tower_reevaluate, name='ct-reevaluate'),
]

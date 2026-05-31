"""Governance API routes — all routed through GovernanceKernel."""
from django.urls import path
from core.governance import views

urlpatterns = [
    # Kernel
    path('health/', views.kernel_health, name='governance-health'),
    path('readiness/', views.readiness_check, name='governance-readiness'),

    # Enforcement
    path('enforce/', views.enforce, name='governance-enforce'),

    # Invariant Checks
    path('invariants/', views.invariants, name='governance-invariants'),

    # Discovery & Audit
    path('discover/', views.discover, name='governance-discover'),
    path('audit/', views.audit, name='governance-audit'),

    # Feature Gates
    path('features/', views.features, name='governance-features'),

    # Failsafe Control
    path('failsafe/', views.failsafe, name='governance-failsafe'),

    # Bootstrap
    path('bootstrap/', views.bootstrap, name='governance-bootstrap'),

    # Observability
    path('metrics/', views.metrics, name='governance-metrics'),
    path('events/', views.events, name='governance-events'),

    # Chaos / Resilience Certification
    path('chaos/summary/', views.chaos_summary, name='governance-chaos-summary'),
    path('chaos/run/', views.run_chaos_scenario, name='governance-chaos-run'),
    path('chaos/scenarios/', views.chaos_scenarios, name='governance-chaos-scenarios'),

    # Enterprise Operational Certification (Phases 1-7)
    path('certification/summary/', views.certification_summary, name='governance-certification-summary'),
    path('certification/phase/', views.certification_phase, name='governance-certification-phase'),

    # Deployment
    path('deployment/fingerprint/', views.deployment_fingerprint, name='governance-deployment-fingerprint'),

    # Operational Observability
    path('health/operational/', views.operational_health, name='governance-operational-health'),

    # Drift Detection
    path('drift/', views.operational_drift, name='governance-drift'),

    # Control Plane (Enterprise Operations Governance)
    path('control-plane/status/', views.control_plane_status, name='governance-control-plane-status'),
    path('control-plane/intelligence/', views.control_plane_intelligence, name='governance-control-plane-intelligence'),
    path('control-plane/gate/', views.control_plane_gate, name='governance-control-plane-gate'),
    path('control-plane/drift-prevention/', views.control_plane_drift_prevention, name='governance-control-plane-drift-prevention'),
    path('control-plane/recovery-plan/', views.control_plane_recovery_plan, name='governance-control-plane-recovery-plan'),
    path('control-plane/stability/', views.control_plane_stability, name='governance-control-plane-stability'),
]

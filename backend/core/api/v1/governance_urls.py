from django.urls import path
from . import governance

urlpatterns = [
    # Decision Pipeline
    path('intercept/', governance.governance_intercept, name='v1-gov-intercept'),
    path('evaluate/', governance.governance_evaluate, name='v1-gov-evaluate'),
    path('action-types/', governance.governance_action_types, name='v1-gov-action-types'),

    # Simulation
    path('simulate/', governance.governance_simulate, name='v1-gov-simulate'),

    # Approval Gateway
    path('workflows/', governance.governance_workflows_list, name='v1-gov-workflows'),
    path('workflows/create/', governance.governance_workflow_create, name='v1-gov-workflow-create'),
    path('workflows/<str:workflow_id>/', governance.governance_workflow_detail, name='v1-gov-workflow-detail'),
    path('workflows/<str:workflow_id>/sign/', governance.governance_workflow_sign, name='v1-gov-workflow-sign'),
    path('workflows/<str:workflow_id>/escalate/', governance.governance_workflow_escalate, name='v1-gov-workflow-escalate'),
    path('workflows/<str:workflow_id>/cancel/', governance.governance_workflow_cancel, name='v1-gov-workflow-cancel'),

    # Gateway Status
    path('status/', governance.governance_gateway_status, name='v1-gov-status'),
]

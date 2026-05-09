"""Workflows app URLs"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    WorkflowInstanceViewSet,
    ApprovalChainViewSet,
    ApprovalRequestViewSet,
    WorkflowStatusView,
    WorkflowActionView,
    MyPendingApprovalsView,
    ApprovalRequestActionView
)

router = DefaultRouter()
router.register(r'instances', WorkflowInstanceViewSet, basename='workflow-instance')
router.register(r'chains', ApprovalChainViewSet, basename='approval-chain')
router.register(r'requests', ApprovalRequestViewSet, basename='approval-request')

urlpatterns = [
    path('status/<str:entity_type>/<int:entity_id>/', WorkflowStatusView.as_view(), name='workflow-status'),
    path('action/<int:workflow_id>/', WorkflowActionView.as_view(), name='workflow-action'),
    path('my-pending/', MyPendingApprovalsView.as_view(), name='my-pending-approvals'),
    path('request/<int:request_id>/action/', ApprovalRequestActionView.as_view(), name='approval-request-action'),
] + router.urls
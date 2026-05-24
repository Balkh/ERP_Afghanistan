"""Workflows API Views"""
from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from workflows.models import (
    WorkflowInstance, ApprovalChain, ApprovalLevel, ApprovalRequest, WorkflowState
)
from workflows.services import WorkflowService, WorkflowValidator
from core.api.responses import APIResponse
from security.permissions import RoleBasedPermission
from core.multitenant.views import UnifiedEnterpriseViewSetMixin


class WorkflowInstanceViewSet(UnifiedEnterpriseViewSetMixin, viewsets.ModelViewSet):
    """Workflow instances CRUD"""
    queryset = WorkflowInstance.objects.all()
    permission_classes = [RoleBasedPermission]
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs


class ApprovalChainViewSet(UnifiedEnterpriseViewSetMixin, viewsets.ModelViewSet):
    """Approval chains CRUD"""
    queryset = ApprovalChain.objects.all()
    permission_classes = [RoleBasedPermission]


class ApprovalRequestViewSet(UnifiedEnterpriseViewSetMixin, viewsets.ModelViewSet):
    """Approval requests CRUD"""
    queryset = ApprovalRequest.objects.all()
    permission_classes = [RoleBasedPermission]


class WorkflowStatusView(generics.GenericAPIView):
    """Get workflow status for an entity"""
    permission_classes = [RoleBasedPermission]
    
    def get(self, request, entity_type, entity_id):
        result = WorkflowService.get_workflow_status(entity_type, entity_id)
        
        if result is None:
            return Response(APIResponse.success(data={'has_workflow': False}))
        
        return Response(APIResponse.success(data=result))


class WorkflowActionView(generics.GenericAPIView):
    """Perform workflow action (submit, approve, reject, post, cancel)"""
    permission_classes = [RoleBasedPermission]
    
    def post(self, request, workflow_id):
        action = request.data.get('action')
        comment = request.data.get('comment', '')
        
        if not action:
            return Response(APIResponse.error('Action is required'), status=400)
        
        workflow = get_object_or_404(WorkflowInstance, id=workflow_id)
        
        if not WorkflowValidator.validate_company_isolation(workflow, request.user):
            return Response(APIResponse.error('Cross-company access denied'), status=403)
        
        state_map = {
            'submit': 'PENDING_APPROVAL',
            'approve': 'APPROVED',
            'reject': 'REJECTED',
            'post': 'POSTED',
            'cancel': 'CANCELLED',
            'reopen': 'DRAFT',
        }
        
        new_state = state_map.get(action)
        if not new_state:
            return Response(APIResponse.error(f'Invalid action: {action}'), status=400)
        
        validation = WorkflowValidator.validate_state_transition(workflow, new_state)
        if not validation.get('valid'):
            return Response(APIResponse.error(validation['error']), status=400)
        
        try:
            if action == 'submit':
                workflow = WorkflowService.submit_for_approval(workflow_id, request.user, comment)
            elif action == 'approve':
                workflow = WorkflowService.approve(workflow_id, request.user, comment)
            elif action == 'reject':
                workflow = WorkflowService.reject(workflow_id, request.user, comment)
            elif action == 'post':
                workflow = WorkflowService.post(workflow_id, request.user, comment)
            elif action == 'cancel':
                workflow = WorkflowService.cancel(workflow_id, request.user, comment)
            elif action == 'reopen':
                workflow = WorkflowService.reopen(workflow_id, request.user, comment)
            
            return Response(APIResponse.success(
                data={
                    'workflow_id': workflow.id,
                    'state': workflow.current_state,
                    'state_display': workflow.get_current_state_display()
                },
                message=f"Action {action} completed successfully"
            ))
            
        except ValidationError as e:
            return Response(APIResponse.error(str(e)), status=400)
        except Exception as e:
            return Response(APIResponse.error(f"Action failed: {str(e)}"), status=500)


class MyPendingApprovalsView(generics.GenericAPIView):
    """Get pending approval requests for current user"""
    permission_classes = [RoleBasedPermission]
    
    def get(self, request):
        user = request.user
        
        # Get pending approval requests where user is the pending approver
        pending_requests = ApprovalRequest.objects.filter(
            approver=user,
            status='PENDING',
            due_date__gte=timezone.now()
        ).select_related(
            'workflow_instance',
            'chain',
            'level',
            'requested_by'
        ).order_by('due_date')
        
        # Get overdue requests
        overdue_requests = ApprovalRequest.objects.filter(
            approver=user,
            status='PENDING',
            due_date__lt=timezone.now()
        ).select_related(
            'workflow_instance',
            'chain',
            'level',
            'requested_by'
        ).order_by('-due_date')
        
        data = {
            'pending': [
                {
                    'id': r.id,
                    'workflow_id': r.workflow_instance.id,
                    'entity_type': r.workflow_instance.content_type,
                    'entity_ref': r.workflow_instance.object_reference,
                    'title': r.workflow_instance.title,
                    'amount': str(r.amount),
                    'currency': r.currency,
                    'level': r.level.name if r.level else None,
                    'requested_by': r.requested_by.username if r.requested_by else None,
                    'due_date': r.due_date.isoformat() if r.due_date else None,
                    'created_at': r.created_at.isoformat(),
                }
                for r in pending_requests
            ],
            'overdue': [
                {
                    'id': r.id,
                    'workflow_id': r.workflow_instance.id,
                    'entity_type': r.workflow_instance.content_type,
                    'entity_ref': r.workflow_instance.object_reference,
                    'title': r.workflow_instance.title,
                    'amount': str(r.amount),
                    'currency': r.currency,
                    'level': r.level.name if r.level else None,
                    'requested_by': r.requested_by.username if r.requested_by else None,
                    'due_date': r.due_date.isoformat() if r.due_date else None,
                    'overdue_hours': int((timezone.now() - r.due_date).total_seconds() / 3600) if r.due_date else 0,
                }
                for r in overdue_requests
            ]
        }
        
        return Response(APIResponse.success(data=data))


class ApprovalRequestActionView(generics.GenericAPIView):
    """Approve or reject an approval request"""
    permission_classes = [RoleBasedPermission]
    
    def post(self, request, request_id):
        action = request.data.get('action')  # 'approve' or 'reject'
        comment = request.data.get('comment', '')
        
        if action not in ['approve', 'reject']:
            return Response(APIResponse.error('Invalid action'), status=400)
        
        approval_req = get_object_or_404(ApprovalRequest, id=request_id, approver=request.user)
        
        if approval_req.status != 'PENDING':
            return Response(APIResponse.error('Request already processed'), status=400)
        
        # Process the request
        if action == 'approve':
            approval_req.status = 'APPROVED'
            approval_req.approver = request.user
            approval_req.responded_at = timezone.now()
            approval_req.response_comment = comment
            approval_req.save()
            
            # Approve the workflow
            WorkflowService.approve(approval_req.workflow_instance.id, request.user, comment)
            
        else:  # reject
            approval_req.status = 'REJECTED'
            approval_req.approver = request.user
            approval_req.responded_at = timezone.now()
            approval_req.response_comment = comment
            approval_req.save()
            
            # Reject the workflow
            WorkflowService.reject(approval_req.workflow_instance.id, request.user, comment)
        
        return Response(APIResponse.success(
            data={'request_id': approval_req.id, 'status': approval_req.status},
            message=f"Request {action}d successfully"
        ))
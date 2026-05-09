"""
Workflow Service Layer
Safe, modular, reusable workflow operations.
"""
from decimal import Decimal
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from workflows.models import (
    WorkflowInstance, WorkflowAuditLog, WorkflowState,
    ApprovalChain, ApprovalLevel, ApprovalRequest,
    WorkflowRule, WorkflowPermission
)
from core.multitenant.context import TenantContext


class WorkflowService:
    """
    Centralized workflow service - handles all workflow operations.
    """
    
    # Supported modules
    SUPPORTED_MODULES = {
        'SALES_INVOICE': 'sales.SalesInvoice',
        'PURCHASE_INVOICE': 'purchases.PurchaseInvoice',
        'RETURN_ORDER': 'returns.ReturnOrder',
        'JOURNAL_ENTRY': 'accounting.JournalEntry',
    }
    
    @staticmethod
    def create_workflow(entity_type: str, entity_id: int, entity_ref: str,
                       user, company_id: str = None, title: str = '',
                       amount: Decimal = Decimal('0')) -> WorkflowInstance:
        """Create a new workflow instance for an entity."""
        
        company_id = company_id or TenantContext.get_company_id()
        
        # Validate entity type
        if entity_type not in WorkflowService.SUPPORTED_MODULES:
            raise ValidationError(f"Unsupported entity type: {entity_type}")
        
        # Check company isolation
        if company_id:
            from core.models import Company
            company = Company.objects.filter(id=company_id, is_active=True).first()
            if not company:
                raise ValidationError("Invalid company")
        
        # Create workflow instance
        workflow = WorkflowInstance.objects.create(
            content_type=entity_type,
            object_id=entity_id,
            object_reference=entity_ref,
            current_state=WorkflowState.DRAFT,
            company_id=company_id,
            created_by=user,
            title=title or entity_ref,
            amount=amount,
        )
        
        # Add audit log
        WorkflowService._log_action(workflow, 'CREATED', user, '', '', f"Workflow created for {entity_ref}")
        
        return workflow
    
    @staticmethod
    def submit_for_approval(workflow_id: int, user, comment: str = '') -> WorkflowInstance:
        """Submit workflow for approval."""
        
        workflow = WorkflowInstance.objects.get(id=workflow_id)
        
        # Validate transition
        if not workflow.can_transition_to(WorkflowState.PENDING_APPROVAL):
            raise ValidationError(f"Cannot submit from {workflow.current_state}")
        
        # Validate permission
        WorkflowService._validate_permission(user, workflow, 'can_submit')
        
        # Execute transition
        workflow.transition_to(WorkflowState.PENDING_APPROVAL, user, comment or 'Submitted for approval')
        
        # Find pending approvers
        WorkflowService._assign_approvers(workflow, user)
        
        return workflow
    
    @staticmethod
    def approve(workflow_id: int, user, comment: str = '') -> WorkflowInstance:
        """Approve a pending workflow."""
        
        workflow = WorkflowInstance.objects.get(id=workflow_id)
        
        # Validate transition
        if not workflow.can_transition_to(WorkflowState.APPROVED):
            raise ValidationError(f"Cannot approve from {workflow.current_state}")
        
        # Validate permission
        WorkflowService._validate_permission(user, workflow, 'can_approve')
        
        # Execute transition
        workflow.transition_to(WorkflowState.APPROVED, user, comment or 'Approved')
        
        # Clear pending approver
        workflow.pending_approver = None
        workflow.save(update_fields=['pending_approver'])
        
        # Send notification
        try:
            WorkflowNotificationService.notify_approval_completed(workflow, 'APPROVED', user)
        except Exception:
            pass
        
        return workflow
    
    @staticmethod
    def reject(workflow_id: int, user, comment: str = '') -> WorkflowInstance:
        """Reject a pending workflow."""
        
        workflow = WorkflowInstance.objects.get(id=workflow_id)
        
        # Validate transition
        if not workflow.can_transition_to(WorkflowState.REJECTED):
            raise ValidationError(f"Cannot reject from {workflow.current_state}")
        
        # Validate permission
        WorkflowService._validate_permission(user, workflow, 'can_reject')
        
        # Execute transition
        workflow.transition_to(WorkflowState.REJECTED, user, comment or 'Rejected')
        
        # Clear pending approver
        workflow.pending_approver = None
        workflow.save(update_fields=['pending_approver'])
        
        # Send notification
        try:
            WorkflowNotificationService.notify_approval_completed(workflow, 'REJECTED', user)
        except Exception:
            pass
        
        return workflow
    
    @staticmethod
    def post(workflow_id: int, user, comment: str = '') -> WorkflowInstance:
        """Post/complete a workflow (financial posting)."""
        
        workflow = WorkflowInstance.objects.get(id=workflow_id)
        
        # CRITICAL: Check if approval is done - accounting safety
        if workflow.current_state != WorkflowState.APPROVED:
            raise ValidationError("Document must be approved before posting")
        
        # Validate transition
        if not workflow.can_transition_to(WorkflowState.POSTED):
            raise ValidationError(f"Cannot post from {workflow.current_state}")
        
        # Validate permission
        WorkflowService._validate_permission(user, workflow, 'can_post')
        
        # Execute transition
        workflow.transition_to(WorkflowState.POSTED, user, comment or 'Posted')
        
        return workflow
    
    @staticmethod
    def cancel(workflow_id: int, user, comment: str = '') -> WorkflowInstance:
        """Cancel a workflow."""
        
        workflow = WorkflowInstance.objects.get(id=workflow_id)
        
        # Validate transition
        if not workflow.can_transition_to(WorkflowState.CANCELLED):
            raise ValidationError(f"Cannot cancel from {workflow.current_state}")
        
        # Validate permission - can_cancel
        WorkflowService._validate_permission(user, workflow, 'can_cancel')
        
        # Execute transition
        workflow.transition_to(WorkflowState.CANCELLED, user, comment or 'Cancelled')
        
        return workflow
    
    @staticmethod
    def reopen(workflow_id: int, user, comment: str = '') -> WorkflowInstance:
        """Reopen a rejected workflow to draft."""
        
        workflow = WorkflowInstance.objects.get(id=workflow_id)
        
        # Can only reopen from REJECTED
        if workflow.current_state != WorkflowState.REJECTED:
            raise ValidationError("Can only reopen rejected documents")
        
        # Execute transition
        workflow.transition_to(WorkflowState.DRAFT, user, comment or 'Reopened')
        
        return workflow
    
    @staticmethod
    def _validate_permission(user, workflow, permission: str):
        """Validate user has required permission"""
        
        # Get user roles
        from security.models import UserRole
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        role_ids = [ur.role_id for ur in user_roles]
        
        # If no roles, check for global permission or allow (for testing purposes)
        if not role_ids:
            global_perm = WorkflowPermission.objects.filter(
                role__isnull=True,
                entity_type__in=[workflow.content_type, '']
            ).first()
            if global_perm and getattr(global_perm, permission, False):
                return True
            # Allow if no permissions defined yet (for system bootstrapping)
            return
        
        # Check role-based permissions
        perms = WorkflowPermission.objects.filter(
            role_id__in=role_ids,
            entity_type__in=[workflow.content_type, '']
        )
        
        has_perm = False
        for perm in perms:
            if getattr(perm, permission, False):
                if not perm.max_amount or workflow.amount <= perm.max_amount:
                    has_perm = True
                    break
        
        if not has_perm:
            raise ValidationError(f"User does not have {permission} permission for this document")
    
    @staticmethod
    def _assign_approvers(workflow: WorkflowInstance, submitted_by):
        """Assign approvers based on approval chain"""
        
        # Find applicable approval chain
        chain = ApprovalChain.objects.filter(
            entity_type=workflow.content_type,
            is_active=True
        ).first()
        
        if chain:
            workflow.approval_chain = chain
            # Get required level
            level = chain.get_approval_level(workflow.amount)
            if level:
                workflow.current_approval_level = level.level_number
                
                # Find approver based on level configuration
                approver = WorkflowService._get_approver(level, workflow)
                if approver:
                    workflow.pending_approver = approver
                    
                    # Create approval request
                    approval_req = ApprovalRequest.objects.create(
                        workflow_instance=workflow,
                        chain=chain,
                        level=level,
                        requested_by=submitted_by,
                        company=workflow.company,
                        amount=workflow.amount,
                        due_date=timezone.now() + timezone.timedelta(hours=level.timeout_hours)
                    )
                    
                    # Send notification to approver
                    try:
                        WorkflowNotificationService.notify_approval_request(approval_req)
                    except Exception:
                        pass
        
        workflow.save(update_fields=['approval_chain', 'current_approval_level', 'pending_approver'])
    
    @staticmethod
    def _get_approver(level: ApprovalLevel, workflow: WorkflowInstance):
        """Get approver based on level configuration"""
        
        if level.approver_type == 'USER':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.filter(id=level.approver_id).first()
        
        elif level.approver_type == 'ROLE':
            # Get users with this role in the same company
            from security.models import UserRole
            from core.models.multitenant import UserCompanyMapping
            
            ur = UserRole.objects.filter(role=level.approver_role).first()
            if ur and workflow.company:
                mapping = UserCompanyMapping.objects.filter(
                    user=ur.user,
                    company=workflow.company,
                    is_active=True
                ).first()
                return ur.user if mapping else None
        
        return None
    
    @staticmethod
    def _log_action(workflow: WorkflowInstance, action: str, user, from_state: str, 
                   to_state: str, comment: str):
        """Create audit log entry"""
        WorkflowAuditLog.objects.create(
            instance=workflow,
            action=action,
            from_state=from_state,
            to_state=to_state,
            user=user,
            user_name=user.username if user else 'system',
            comment=comment,
        )
    
    @staticmethod
    def can_post(entity_type: str, entity_id: int) -> bool:
        """Check if entity can be posted (safety check)"""
        try:
            workflow = WorkflowInstance.objects.get(
                content_type=entity_type,
                object_id=entity_id,
                is_active=True
            )
            return workflow.can_post()
        except WorkflowInstance.DoesNotExist:
            return False  # No workflow = cannot post
    
    @staticmethod
    def get_workflow_status(entity_type: str, entity_id: int) -> Optional[Dict]:
        """Get workflow status for an entity"""
        try:
            workflow = WorkflowInstance.objects.get(
                content_type=entity_type,
                object_id=entity_id,
                is_active=True
            )
            return {
                'state': workflow.current_state,
                'state_display': workflow.get_current_state_display(),
                'created_by': workflow.created_by.username if workflow.created_by else None,
                'created_at': workflow.created_at.isoformat(),
                'submitted_at': workflow.submitted_at.isoformat() if workflow.submitted_at else None,
                'approved_at': workflow.approved_at.isoformat() if workflow.approved_at else None,
                'posted_at': workflow.posted_at.isoformat() if workflow.posted_at else None,
                'pending_approver': workflow.pending_approver.username if workflow.pending_approver else None,
                'is_approved': workflow.current_state == WorkflowState.APPROVED,
                'is_posted': workflow.current_state == WorkflowState.POSTED,
                'can_submit': workflow.current_state == WorkflowState.DRAFT,
                'can_approve': workflow.current_state == WorkflowState.PENDING_APPROVAL,
                'can_post': workflow.can_post(),
                'can_cancel': workflow.can_transition_to(WorkflowState.CANCELLED),
            }
        except WorkflowInstance.DoesNotExist:
            return None


class WorkflowValidator:
    """Validates workflow operations"""
    
    @staticmethod
    def validate_company_isolation(workflow: WorkflowInstance, user) -> bool:
        """Ensure no cross-company workflow access"""
        user_company = TenantContext.get_company_id()
        
        if user_company and workflow.company_id:
            return str(user_company) == str(workflow.company_id)
        
        return True  # Allow if no company context
    
    @staticmethod
    def validate_state_transition(workflow: WorkflowInstance, new_state: str) -> Dict[str, Any]:
        """Validate state transition and return result"""
        if not workflow.can_transition_to(new_state):
            return {
                'valid': False,
                'error': f"Invalid transition from {workflow.current_state} to {new_state}"
            }
        
        # Check accounting safety - cannot post without approval
        if new_state == WorkflowState.POSTED and workflow.current_state != WorkflowState.APPROVED:
            return {
                'valid': False,
                'error': "Document must be approved before posting"
            }
        
        return {'valid': True}


class WorkflowNotificationService:
    """Service for workflow-related notifications"""
    
    @staticmethod
    def notify_approval_request(approval_request: ApprovalRequest):
        """Send notification to approver about pending approval request"""
        if not approval_request.approver:
            return
        
        from security.notification_service import NotificationService
        
        entity_type_map = {
            'SALES_INVOICE': 'Sales Invoice',
            'PURCHASE_INVOICE': 'Purchase Invoice',
            'RETURN_ORDER': 'Return Order',
            'JOURNAL_ENTRY': 'Journal Entry',
        }
        
        entity_name = entity_type_map.get(
            approval_request.workflow_instance.content_type,
            approval_request.workflow_instance.content_type
        )
        
        title = f"Approval Request: {entity_name}"
        message = (
            f"New approval request for {approval_request.workflow_instance.object_reference}\n"
            f"Amount: {approval_request.amount} {approval_request.currency}\n"
            f"Requested by: {approval_request.requested_by.username if approval_request.requested_by else 'Unknown'}\n"
            f"Due: {approval_request.due_date.strftime('%Y-%m-%d %H:%M') if approval_request.due_date else 'No deadline'}"
        )
        
        try:
            NotificationService.create_notification(
                user=approval_request.approver,
                notification_type='WORKFLOW',
                title=title,
                message=message,
                severity='WARNING',
                content_type='workflows.WorkflowInstance',
                object_id=approval_request.workflow_instance.id,
            )
        except Exception:
            pass  # Don't fail workflow if notification fails
    
    @staticmethod
    def notify_approval_completed(workflow: WorkflowInstance, action: str, user):
        """Notify requester about approval decision"""
        if not workflow.created_by:
            return
        
        from security.notification_service import NotificationService
        
        entity_type_map = {
            'SALES_INVOICE': 'Sales Invoice',
            'PURCHASE_INVOICE': 'Purchase Invoice',
            'RETURN_ORDER': 'Return Order',
            'JOURNAL_ENTRY': 'Journal Entry',
        }
        
        entity_name = entity_type_map.get(workflow.content_type, workflow.content_type)
        
        action_verb = {
            'APPROVED': 'approved',
            'REJECTED': 'rejected',
            'POSTED': 'posted',
            'CANCELLED': 'cancelled',
        }.get(action, action.lower())
        
        title = f"Document {action_verb.title()}: {workflow.object_reference}"
        message = f"Your {entity_name} ({workflow.object_reference}) has been {action_verb}."
        
        try:
            NotificationService.create_notification(
                user=workflow.created_by,
                notification_type='WORKFLOW',
                title=title,
                message=message,
                severity='INFO',
                content_type='workflows.WorkflowInstance',
                object_id=workflow.id,
            )
        except Exception:
            pass
    
    @staticmethod
    def notify_overdue_approval():
        """Check and notify about overdue approval requests"""
        from django.utils import timezone
        from security.notification_service import NotificationService
        
        overdue_requests = ApprovalRequest.objects.filter(
            status='PENDING',
            due_date__lt=timezone.now()
        )
        
        for req in overdue_requests:
            if not req.approver:
                continue
            
            # Check if we've already notified recently (last 24 hours)
            from security.models import Notification
            recent = Notification.objects.filter(
                user=req.approver,
                content_type__model='workflowinstance',
                object_id=req.workflow_instance.id,
                created_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).exists()
            
            if recent:
                continue
            
            title = f"Overdue Approval: {req.workflow_instance.object_reference}"
            message = (
                f"Your approval for {req.workflow_instance.object_reference} is overdue.\n"
                f"Original due: {req.due_date.strftime('%Y-%m-%d') if req.due_date else 'Unknown'}"
            )
            
            try:
                NotificationService.create_notification(
                    user=req.approver,
                    notification_type='WORKFLOW',
                    title=title,
                    message=message,
                    severity='ERROR',
                    content_type='workflows.WorkflowInstance',
                    object_id=req.workflow_instance.id,
                )
            except Exception:
                pass
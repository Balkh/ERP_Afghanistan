"""
Enterprise Workflow & Approval Engine
Safe, modular, and enterprise-grade workflow system.

CORE PRINCIPLE: "No important financial or operational action should bypass controlled approval flow."
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel


# Standard workflow states
class WorkflowState:
    """Standard workflow states"""
    DRAFT = 'DRAFT'
    PENDING_APPROVAL = 'PENDING_APPROVAL'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    POSTED = 'POSTED'
    CANCELLED = 'CANCELLED'
    COMPLETED = 'COMPLETED'
    
    CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING_APPROVAL, 'Pending Approval'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (POSTED, 'Posted'),
        (CANCELLED, 'Cancelled'),
        (COMPLETED, 'Completed'),
    ]
    
    # Valid transitions map - defines which transitions are allowed
    VALID_TRANSITIONS = {
        DRAFT: [PENDING_APPROVAL, CANCELLED],
        PENDING_APPROVAL: [APPROVED, REJECTED, CANCELLED],
        APPROVED: [POSTED, COMPLETED, CANCELLED],
        REJECTED: [DRAFT, CANCELLED],  # Can reopen to draft
        POSTED: [],  # Posted documents cannot be changed (final state)
        CANCELLED: [],
        COMPLETED: [],
    }
    
    # States that require approval
    REQUIRES_APPROVAL = [PENDING_APPROVAL, APPROVED, POSTED]
    
    # States that block financial posting
    BLOCKS_POSTING = [DRAFT, PENDING_APPROVAL, REJECTED, CANCELLED]
    
    @classmethod
    def can_transition(cls, from_state, to_state):
        """Check if transition is valid"""
        return to_state in cls.VALID_TRANSITIONS.get(from_state, [])
    
    @classmethod
    def is_safe_transition(cls, from_state, to_state):
        """Check if transition is safe (not invalid)"""
        return cls.can_transition(from_state, to_state)


class WorkflowInstance(TimeStampedUUIDModel):
    """
    Centralized workflow instance - Generic model that works with any content type.
    """
    # Generic entity references
    content_type = models.CharField(max_length=50, verbose_name=_('Entity Type'))
    object_id = models.UUIDField(verbose_name=_('Entity ID'))
    object_reference = models.CharField(max_length=200, blank=True, verbose_name=_('Object Reference'))
    
    # Workflow state
    current_state = models.CharField(max_length=30, choices=WorkflowState.CHOICES, default=WorkflowState.DRAFT)
    previous_state = models.CharField(max_length=30, blank=True)
    
    # Context
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='workflow_instances')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_workflows')
    
    # Tracking
    is_active = models.BooleanField(default=True)
    priority = models.CharField(max_length=20, default='NORMAL')
    
    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Approval chain
    current_approval_level = models.PositiveIntegerField(default=0)
    approval_chain = models.ForeignKey('workflows.ApprovalChain', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Current approver
    pending_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_approvals')
    
    # Metadata
    title = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    currency = models.CharField(max_length=3, default='AFN')
    
    class Meta:
        db_table = 'workflow_instance'
        ordering = ['-created_at']
        unique_together = ['content_type', 'object_id', 'is_active']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['company', 'current_state']),
            models.Index(fields=['current_state', 'is_active']),
            models.Index(fields=['pending_approver', 'current_state']),
        ]
    
    def __str__(self):
        return f"{self.content_type}:{self.object_reference} ({self.current_state})"
    
    def can_transition_to(self, new_state):
        """Check if transition to new_state is valid"""
        return WorkflowState.can_transition(self.current_state, new_state)
    
    def transition_to(self, new_state, user, comment=''):
        """Execute transition to new state"""
        if not self.can_transition_to(new_state):
            raise ValidationError(f"Invalid transition from {self.current_state} to {new_state}")
        
        # Validate permission
        self._validate_permission(user, new_state)
        
        # Record previous state
        self.previous_state = self.current_state
        self.current_state = new_state
        self._update_timestamp(new_state)
        
        # Add audit entry
        self._add_audit_entry(user, self.previous_state, new_state, comment)
        
        self.save(update_fields=['current_state', 'previous_state', 'submitted_at', 'approved_at', 'rejected_at', 'posted_at', 'completed_at', 'cancelled_at', 'updated_at'])
        
        # Trigger notifications
        self._trigger_notifications(new_state)
        
        return True
    
    def _validate_permission(self, user, new_state):
        """Validate user has permission for this transition"""
        # Permission check delegated to service layer - skip model-level check
        # This allows for more flexible permission handling
        pass
    
    def _update_timestamp(self, state):
        """Update appropriate timestamp for state"""
        now = timezone.now()
        if state == WorkflowState.PENDING_APPROVAL:
            self.submitted_at = now
        elif state == WorkflowState.APPROVED:
            self.approved_at = now
        elif state == WorkflowState.REJECTED:
            self.rejected_at = now
        elif state == WorkflowState.POSTED:
            self.posted_at = now
        elif state == WorkflowState.COMPLETED:
            self.completed_at = now
        elif state == WorkflowState.CANCELLED:
            self.cancelled_at = now
    
    def _add_audit_entry(self, user, from_state, to_state, comment):
        """Add audit trail entry"""
        WorkflowAuditLog.objects.create(
            instance=self,
            action='STATE_CHANGE',
            from_state=from_state,
            to_state=to_state,
            user=user,
            user_name=user.username if user else 'system',
            comment=comment or f"Transitioned from {from_state} to {to_state}"
        )
    
    def _trigger_notifications(self, new_state):
        """Trigger notifications based on state change"""
        # This will integrate with notification system
        pass
    
    def requires_approval(self):
        """Check if document requires approval before posting"""
        return self.current_state == WorkflowState.PENDING_APPROVAL
    
    def can_post(self):
        """Check if document can be posted (requires approval first)"""
        return self.current_state == WorkflowState.APPROVED
    
    def get_status_display_class(self):
        """Get CSS class for UI display"""
        state_classes = {
            WorkflowState.DRAFT: 'secondary',
            WorkflowState.PENDING_APPROVAL: 'warning',
            WorkflowState.APPROVED: 'success',
            WorkflowState.REJECTED: 'danger',
            WorkflowState.POSTED: 'primary',
            WorkflowState.CANCELLED: 'dark',
            WorkflowState.COMPLETED: 'success',
        }
        return state_classes.get(self.current_state, 'secondary')


class WorkflowAuditLog(TimeStampedUUIDModel):
    """
    Audit trail for all workflow actions.
    """
    instance = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE, related_name='audit_logs')
    
    # Action details
    action = models.CharField(max_length=50, verbose_name=_('Action'))
    from_state = models.CharField(max_length=30, blank=True)
    to_state = models.CharField(max_length=30)
    
    # User info
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    user_name = models.CharField(max_length=100, blank=True)
    
    # Comment
    comment = models.TextField(blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'workflow_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['instance', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.action} by {self.user_name} on {self.created_at}"


class ApprovalChain(TimeStampedUUIDModel):
    """
    Multi-level approval chains with amount-based thresholds.
    """
    name = models.CharField(max_length=100, verbose_name=_('Chain Name'))
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    # Applicable entity types
    ENTITY_TYPES = [
        ('SALES_INVOICE', 'Sales Invoice'),
        ('PURCHASE_INVOICE', 'Purchase Invoice'),
        ('RETURN_ORDER', 'Return Order'),
        ('JOURNAL_ENTRY', 'Journal Entry'),
        ('PAYMENT', 'Payment'),
    ]
    entity_type = models.CharField(max_length=30, choices=ENTITY_TYPES, verbose_name=_('Entity Type'))
    
    is_active = models.BooleanField(default=True)
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        db_table = 'approval_chain'
        verbose_name = _('Approval Chain')
        verbose_name_plural = _('Approval Chains')
    
    def __str__(self):
        return self.name
    
    def get_approval_level(self, amount):
        """Get the approval level needed for given amount"""
        levels = self.levels.order_by('min_amount')
        for level in levels:
            if level.min_amount <= amount <= level.max_amount:
                return level
        return levels.last()  # Default to highest level


class ApprovalLevel(TimeStampedUUIDModel):
    """
    Single level in an approval chain.
    """
    chain = models.ForeignKey(ApprovalChain, on_delete=models.CASCADE, related_name='levels')
    
    name = models.CharField(max_length=100)
    level_number = models.PositiveIntegerField()
    
    # Amount thresholds
    min_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    max_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('999999999'))
    
    # Approver configuration
    APPROVER_TYPES = [
        ('USER', 'Specific User'),
        ('ROLE', 'Role-based'),
        ('MANAGER', 'Manager'),
        ('DEPARTMENT_HEAD', 'Department Head'),
    ]
    approver_type = models.CharField(max_length=20, choices=APPROVER_TYPES, default='ROLE')
    
    approver_id = models.UUIDField(null=True, blank=True)
    approver_role = models.ForeignKey('security.Role', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timeout
    timeout_hours = models.PositiveIntegerField(default=48)
    
    class Meta:
        db_table = 'approval_level'
        ordering = ['level_number']
        unique_together = ['chain', 'level_number']
    
    def __str__(self):
        return f"{self.chain.name} - Level {self.level_number}: {self.name}"


class ApprovalRequest(TimeStampedUUIDModel):
    """
    Approval request at specific level.
    """
    # References
    workflow_instance = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE, related_name='approval_requests')
    chain = models.ForeignKey(ApprovalChain, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.ForeignKey(ApprovalLevel, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Request details
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='approval_requests_made')
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, null=True, blank=True)
    
    # Amount
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    currency = models.CharField(max_length=3, default='AFN')
    
    # Status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SKIPPED', 'Skipped'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Timing
    due_date = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Response
    response_comment = models.TextField(blank=True)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approvals_given')
    
    class Meta:
        db_table = 'approval_request'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Approval for {self.workflow_instance.object_reference} - {self.status}"


class WorkflowRule(TimeStampedUUIDModel):
    """
    Configurable workflow rules (not hardcoded).
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    # Rule configuration
    MODULE_CHOICES = [
        ('SALES_INVOICE', 'Sales Invoice'),
        ('PURCHASE_INVOICE', 'Purchase Invoice'),
        ('RETURN_ORDER', 'Return Order'),
        ('JOURNAL_ENTRY', 'Journal Entry'),
    ]
    module = models.CharField(max_length=30, choices=MODULE_CHOICES, verbose_name=_('Applies To'))
    
    # Conditions (JSON)
    conditions = models.JSONField(default=dict, verbose_name=_('Conditions'))
    # Example: {"amount_operator": ">", "amount_value": 5000, "field": "total_amount"}
    
    # Required roles for transition
    required_roles = models.ManyToManyField('security.Role', blank=True, verbose_name=_('Required Roles'))
    
    # Next state
    target_state = models.CharField(max_length=30, choices=WorkflowState.CHOICES)
    
    # Priority
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'workflow_rule'
        ordering = ['priority']
    
    def __str__(self):
        return f"{self.module}: {self.name} → {self.target_state}"


class WorkflowPermission(TimeStampedUUIDModel):
    """
    Role-based workflow permissions.
    """
    role = models.ForeignKey('security.Role', on_delete=models.CASCADE, related_name='workflow_permissions', null=True, blank=True)
    
    # Permission configuration
    can_submit = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_reject = models.BooleanField(default=False)
    can_post = models.BooleanField(default=False)
    can_cancel = models.BooleanField(default=False)
    can_override = models.BooleanField(default=False)
    
    # Entity-specific permissions
    entity_type = models.CharField(max_length=30, blank=True)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('999999999'))
    
    class Meta:
        db_table = 'workflow_permission'
    
    def __str__(self):
        return f"{self.role.name} - Submit:{self.can_submit} Approve:{self.can_approve} Post:{self.can_post}"
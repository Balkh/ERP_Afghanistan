"""Workflow Service Tests"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from workflows.models import (
    WorkflowInstance, WorkflowState, ApprovalChain, ApprovalLevel,
    WorkflowAuditLog
)
from workflows.services import WorkflowService, WorkflowValidator
from core.models import Company

User = get_user_model()


class WorkflowServiceCreateTests(TestCase):
    """Test WorkflowService.create_workflow"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_workflow_success(self):
        workflow = WorkflowService.create_workflow(
            entity_type='SALES_INVOICE',
            entity_id=1,
            entity_ref='INV-001',
            user=self.user,
            company_id=str(self.company.id),
            title='Test Invoice',
            amount=Decimal('5000.00')
        )
        self.assertEqual(workflow.current_state, WorkflowState.DRAFT)
        self.assertEqual(workflow.content_type, 'SALES_INVOICE')
        self.assertEqual(workflow.amount, Decimal('5000.00'))
    
    def test_create_workflow_unsupported_type(self):
        with self.assertRaises(ValidationError) as ctx:
            WorkflowService.create_workflow(
                entity_type='INVALID_TYPE',
                entity_id=1,
                entity_ref='INV-001',
                user=self.user,
                company_id=str(self.company.id)
            )
        self.assertIn('Unsupported entity type', str(ctx.exception))
    
    def test_create_workflow_creates_audit(self):
        workflow = WorkflowService.create_workflow(
            entity_type='SALES_INVOICE',
            entity_id=1,
            entity_ref='INV-001',
            user=self.user,
            company_id=str(self.company.id)
        )
        log = WorkflowAuditLog.objects.filter(instance=workflow, action='CREATED').first()
        self.assertIsNotNone(log)


class WorkflowServiceTransitionTests(TestCase):
    """Test workflow state transitions via service"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_submit_for_approval(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowService.submit_for_approval(workflow.id, self.user, 'Submitting')
        
        self.assertEqual(result.current_state, WorkflowState.PENDING_APPROVAL)
        self.assertIsNotNone(result.submitted_at)
    
    def test_approve_workflow(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.PENDING_APPROVAL,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowService.approve(workflow.id, self.user, 'Approved')
        
        self.assertEqual(result.current_state, WorkflowState.APPROVED)
        self.assertIsNotNone(result.approved_at)
    
    def test_reject_workflow(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.PENDING_APPROVAL,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowService.reject(workflow.id, self.user, 'Rejected')
        
        self.assertEqual(result.current_state, WorkflowState.REJECTED)
    
    def test_post_workflow_requires_approval(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        with self.assertRaises(ValidationError) as ctx:
            WorkflowService.post(workflow.id, self.user)
        
        self.assertIn('must be approved', str(ctx.exception))
    
    def test_post_workflow_success(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.APPROVED,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowService.post(workflow.id, self.user)
        
        self.assertEqual(result.current_state, WorkflowState.POSTED)
        self.assertIsNotNone(result.posted_at)
    
    def test_cancel_workflow(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowService.cancel(workflow.id, self.user, 'Cancelled by user')
        
        self.assertEqual(result.current_state, WorkflowState.CANCELLED)
    
    def test_reopen_rejected_workflow(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.REJECTED,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowService.reopen(workflow.id, self.user, 'Reopened')
        
        self.assertEqual(result.current_state, WorkflowState.DRAFT)
    
    def test_reopen_non_rejected_fails(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        with self.assertRaises(ValidationError) as ctx:
            WorkflowService.reopen(workflow.id, self.user)
        
        self.assertIn('rejected', str(ctx.exception))


class WorkflowServiceHelperTests(TestCase):
    """Test helper methods"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_get_workflow_status_draft(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        status = WorkflowService.get_workflow_status('SALES_INVOICE', 1)
        
        self.assertEqual(status['state'], WorkflowState.DRAFT)
        self.assertTrue(status['can_submit'])
        self.assertFalse(status['can_approve'])
        self.assertFalse(status['can_post'])
    
    def test_get_workflow_status_approved(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.APPROVED,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        status = WorkflowService.get_workflow_status('SALES_INVOICE', 1)
        
        self.assertTrue(status['is_approved'])
        self.assertTrue(status['can_post'])
    
    def test_get_workflow_status_none(self):
        status = WorkflowService.get_workflow_status('SALES_INVOICE', 999)
        self.assertIsNone(status)
    
    def test_can_post_safety_check(self):
        # No workflow = cannot post
        self.assertFalse(WorkflowService.can_post('SALES_INVOICE', 1))
        
        # Draft = cannot post
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        self.assertFalse(WorkflowService.can_post('SALES_INVOICE', 1))
        
        # Approved = can post
        workflow.current_state = WorkflowState.APPROVED
        workflow.save()
        self.assertTrue(WorkflowService.can_post('SALES_INVOICE', 1))


class WorkflowValidatorTests(TestCase):
    """Test WorkflowValidator"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_validate_state_transition_valid(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowValidator.validate_state_transition(workflow, WorkflowState.PENDING_APPROVAL)
        
        self.assertTrue(result['valid'])
    
    def test_validate_state_transition_invalid(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowValidator.validate_state_transition(workflow, WorkflowState.POSTED)
        
        self.assertFalse(result['valid'])
        self.assertIn('Invalid transition', result['error'])
    
    def test_validate_state_transition_post_without_approval(self):
        # APPROVED -> POSTED is valid transition
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.APPROVED,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        
        result = WorkflowValidator.validate_state_transition(workflow, WorkflowState.POSTED)
        
        # Should pass - APPROVED can transition to POSTED
        self.assertTrue(result['valid'])
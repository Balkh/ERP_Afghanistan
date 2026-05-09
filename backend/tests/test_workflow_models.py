"""Workflow Model Tests"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from workflows.models import (
    WorkflowInstance, WorkflowState, WorkflowAuditLog,
    ApprovalChain, ApprovalLevel, ApprovalRequest,
    WorkflowRule, WorkflowPermission
)
from core.models import Company
from unittest.mock import Mock

User = get_user_model()


class WorkflowStateTests(TestCase):
    """Test WorkflowState class"""
    
    def test_valid_states(self):
        self.assertEqual(WorkflowState.DRAFT, 'DRAFT')
        self.assertEqual(WorkflowState.PENDING_APPROVAL, 'PENDING_APPROVAL')
        self.assertEqual(WorkflowState.APPROVED, 'APPROVED')
        self.assertEqual(WorkflowState.REJECTED, 'REJECTED')
        self.assertEqual(WorkflowState.POSTED, 'POSTED')
        self.assertEqual(WorkflowState.CANCELLED, 'CANCELLED')
        self.assertEqual(WorkflowState.COMPLETED, 'COMPLETED')
    
    def test_valid_transitions_from_draft(self):
        valid = WorkflowState.VALID_TRANSITIONS[WorkflowState.DRAFT]
        self.assertIn(WorkflowState.PENDING_APPROVAL, valid)
        self.assertIn(WorkflowState.CANCELLED, valid)
    
    def test_valid_transitions_from_pending_approval(self):
        valid = WorkflowState.VALID_TRANSITIONS[WorkflowState.PENDING_APPROVAL]
        self.assertIn(WorkflowState.APPROVED, valid)
        self.assertIn(WorkflowState.REJECTED, valid)
        self.assertIn(WorkflowState.CANCELLED, valid)
    
    def test_valid_transitions_from_approved(self):
        valid = WorkflowState.VALID_TRANSITIONS[WorkflowState.APPROVED]
        self.assertIn(WorkflowState.POSTED, valid)
        self.assertIn(WorkflowState.CANCELLED, valid)
    
    def test_rejected_can_reopen(self):
        valid = WorkflowState.VALID_TRANSITIONS[WorkflowState.REJECTED]
        self.assertIn(WorkflowState.DRAFT, valid)
    
    def test_posted_cannot_transition(self):
        valid = WorkflowState.VALID_TRANSITIONS[WorkflowState.POSTED]
        self.assertEqual(len(valid), 0)
    
    def test_blocks_posting_requires_approval(self):
        self.assertIn(WorkflowState.DRAFT, WorkflowState.BLOCKS_POSTING)
        self.assertIn(WorkflowState.PENDING_APPROVAL, WorkflowState.BLOCKS_POSTING)
        self.assertIn(WorkflowState.REJECTED, WorkflowState.BLOCKS_POSTING)
        self.assertNotIn(WorkflowState.APPROVED, WorkflowState.BLOCKS_POSTING)
        self.assertNotIn(WorkflowState.POSTED, WorkflowState.BLOCKS_POSTING)


class WorkflowInstanceTests(TestCase):
    """Test WorkflowInstance model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_workflow_instance(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            title='Test Invoice',
            amount=Decimal('1000.00')
        )
        self.assertEqual(workflow.current_state, WorkflowState.DRAFT)
        self.assertEqual(workflow.content_type, 'SALES_INVOICE')
        self.assertEqual(workflow.amount, Decimal('1000.00'))
    
    def test_can_transition_to_valid(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('1000.00')
        )
        self.assertTrue(workflow.can_transition_to(WorkflowState.PENDING_APPROVAL))
    
    def test_can_transition_to_invalid(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('1000.00')
        )
        self.assertFalse(workflow.can_transition_to(WorkflowState.APPROVED))
    
    def test_can_post_requires_approval(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('1000.00')
        )
        self.assertFalse(workflow.can_post())
        
        workflow.current_state = WorkflowState.APPROVED
        workflow.save()
        self.assertTrue(workflow.can_post())
    
    def test_transition_to_creates_audit_log(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('1000.00')
        )
        workflow.transition_to(WorkflowState.PENDING_APPROVAL, self.user, 'Submitted')
        
        self.assertEqual(WorkflowAuditLog.objects.filter(instance=workflow).count(), 1)
        log = WorkflowAuditLog.objects.filter(instance=workflow).first()
        self.assertEqual(log.action, 'STATE_CHANGE')
        self.assertEqual(log.from_state, WorkflowState.DRAFT)
        self.assertEqual(log.to_state, WorkflowState.PENDING_APPROVAL)
    
    def test_unique_content_object_constraint(self):
        WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.DRAFT,
            company=self.company,
            created_by=self.user,
            amount=Decimal('1000.00')
        )
        with self.assertRaises(Exception):
            WorkflowInstance.objects.create(
                content_type='SALES_INVOICE',
                object_id=1,
                object_reference='INV-001',
                current_state=WorkflowState.DRAFT,
                company=self.company,
                created_by=self.user,
                amount=Decimal('1000.00')
            )


class ApprovalChainTests(TestCase):
    """Test ApprovalChain and ApprovalLevel models"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_approval_chain(self):
        chain = ApprovalChain.objects.create(
            name='Standard Approval',
            entity_type='SALES_INVOICE',
            company=self.company,
            is_active=True
        )
        self.assertEqual(chain.name, 'Standard Approval')
        self.assertTrue(chain.is_active)
    
    def test_add_approval_levels(self):
        chain = ApprovalChain.objects.create(
            name='Standard Approval',
            entity_type='SALES_INVOICE',
            company=self.company,
            is_active=True
        )
        ApprovalLevel.objects.create(
            chain=chain,
            level_number=1,
            name='Manager Approval',
            approver_type='ROLE',
            min_amount=Decimal('0'),
            max_amount=Decimal('10000'),
            timeout_hours=24
        )
        ApprovalLevel.objects.create(
            chain=chain,
            level_number=2,
            name='Director Approval',
            approver_type='ROLE',
            min_amount=Decimal('10000.01'),
            max_amount=Decimal('100000'),
            timeout_hours=48
        )
        levels = chain.levels.order_by('level_number')
        self.assertEqual(levels.count(), 2)
        self.assertEqual(levels.first().level_number, 1)
    
    def test_get_approval_level(self):
        chain = ApprovalChain.objects.create(
            name='Standard Approval',
            entity_type='SALES_INVOICE',
            company=self.company,
            is_active=True
        )
        ApprovalLevel.objects.create(
            chain=chain,
            level_number=1,
            name='Manager Approval',
            approver_type='ROLE',
            min_amount=Decimal('0'),
            max_amount=Decimal('10000'),
            timeout_hours=24
        )
        ApprovalLevel.objects.create(
            chain=chain,
            level_number=2,
            name='Director Approval',
            approver_type='ROLE',
            min_amount=Decimal('10000.01'),
            max_amount=Decimal('100000'),
            timeout_hours=48
        )
        
        level = chain.get_approval_level(Decimal('5000'))
        self.assertEqual(level.level_number, 1)
        
        level = chain.get_approval_level(Decimal('15000'))
        self.assertEqual(level.level_number, 2)
    
    def test_chain_unique_per_company_entity(self):
        ApprovalChain.objects.create(
            name='Standard Approval',
            entity_type='SALES_INVOICE',
            company=self.company,
            is_active=True
        )
        with self.assertRaises(Exception):
            ApprovalChain.objects.create(
                name='Another Approval',
                entity_type='SALES_INVOICE',
                company=self.company,
                is_active=True
            )


class WorkflowRuleTests(TestCase):
    """Test WorkflowRule model"""
    
    def test_create_workflow_rule(self):
        rule = WorkflowRule.objects.create(
            name='High Value Approval',
            code='HIGH_VALUE_APPROVAL',
            module='SALES_INVOICE',
            conditions={'amount_operator': '>', 'amount_value': 50000},
            target_state='PENDING_APPROVAL',
            is_active=True,
            priority=1
        )
        self.assertEqual(rule.name, 'High Value Approval')
        self.assertTrue(rule.is_active)
        self.assertEqual(rule.priority, 1)


class WorkflowPermissionTests(TestCase):
    """Test WorkflowPermission model"""
    
    def test_create_workflow_permission(self):
        perm = WorkflowPermission.objects.create(
            entity_type='SALES_INVOICE',
            can_submit=True,
            can_approve=True,
            can_reject=True,
            can_post=False,
            can_cancel=False,
            max_amount=Decimal('50000')
        )
        self.assertTrue(perm.can_submit)
        self.assertTrue(perm.can_approve)
        self.assertFalse(perm.can_post)
        self.assertEqual(perm.max_amount, Decimal('50000'))


class ApprovalRequestTests(TestCase):
    """Test ApprovalRequest model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_approval_request(self):
        workflow = WorkflowInstance.objects.create(
            content_type='SALES_INVOICE',
            object_id=1,
            object_reference='INV-001',
            current_state=WorkflowState.PENDING_APPROVAL,
            company=self.company,
            created_by=self.user,
            amount=Decimal('5000.00')
        )
        chain = ApprovalChain.objects.create(
            name='Standard',
            entity_type='SALES_INVOICE',
            company=self.company,
            is_active=True
        )
        level = ApprovalLevel.objects.create(
            chain=chain,
            level_number=1,
            name='Manager',
            approver_type='USER',
            min_amount=Decimal('0'),
            max_amount=Decimal('50000'),
            timeout_hours=24
        )
        
        request = ApprovalRequest.objects.create(
            workflow_instance=workflow,
            chain=chain,
            level=level,
            requested_by=self.user,
            company=self.company,
            amount=Decimal('5000.00')
        )
        self.assertEqual(request.status, 'PENDING')
        self.assertIsNone(request.approver)
"""
Job-Workflow Integration Service
Connects background jobs with workflow engine.
"""
import logging
from typing import Optional, Dict, Any

from django.utils import timezone
from django.db import transaction

from jobs.models import BackgroundJob, JobType, JobPriority
from jobs.services import JobService
from workflows.models import WorkflowInstance, WorkflowState

logger = logging.getLogger(__name__)


class JobWorkflowIntegration:
    """
    Integration between background jobs and workflow engine.
    Triggers jobs based on workflow state changes.
    """
    
    # Mapping of workflow states to job triggers
    WORKFLOW_JOB_MAP = {
        WorkflowState.APPROVED: [
            {
                'job_type': JobType.REPORT_GENERATION,
                'trigger': 'invoice_approved_report',
                'description': 'Generate report when invoice approved'
            },
        ],
        WorkflowState.POSTED: [
            {
                'job_type': JobType.FINANCIAL_RECONCILIATION,
                'trigger': 'post_reconciliation',
                'description': 'Run reconciliation when document posted'
            },
            {
                'job_type': JobType.NOTIFICATION_DISPATCH,
                'trigger': 'document_posted_notify',
                'description': 'Notify relevant parties of posting'
            },
        ],
    }
    
    @classmethod
    def on_workflow_approved(cls, workflow: WorkflowInstance, user) -> list:
        """Trigger jobs when workflow is approved"""
        triggered_jobs = []
        
        # Map based on entity type
        if workflow.content_type == 'SALES_INVOICE':
            job = JobService.create_job(
                job_type=JobType.REPORT_GENERATION,
                company_id=str(workflow.company_id) if workflow.company_id else None,
                payload={
                    'report_type': 'sales_summary',
                    'invoice_id': workflow.object_id,
                    'params': {
                        'start_date': workflow.created_at.date().isoformat(),
                        'end_date': timezone.now().date().isoformat()
                    }
                },
                triggered_by=user,
                priority=JobPriority.NORMAL,
                idempotency_key=f"invoice_report_{workflow.object_id}"
            )
            triggered_jobs.append(job)
            logger.info(f"Created report job {job.id} for approved invoice {workflow.object_reference}")
        
        elif workflow.content_type == 'PURCHASE_INVOICE':
            job = JobService.create_job(
                job_type=JobType.REPORT_GENERATION,
                company_id=str(workflow.company_id) if workflow.company_id else None,
                payload={
                    'report_type': 'purchase_summary',
                    'invoice_id': workflow.object_id,
                    'params': {}
                },
                triggered_by=user,
                priority=JobPriority.NORMAL,
                idempotency_key=f"purchase_report_{workflow.object_id}"
            )
            triggered_jobs.append(job)
        
        return triggered_jobs
    
    @classmethod
    def on_workflow_posted(cls, workflow: WorkflowInstance, user) -> list:
        """Trigger jobs when workflow is posted"""
        triggered_jobs = []
        
        # Run reconciliation for financial documents
        if workflow.content_type in ['SALES_INVOICE', 'PURCHASE_INVOICE', 'JOURNAL_ENTRY']:
            job = JobService.create_reconciliation_job(
                company_id=str(workflow.company_id) if workflow.company_id else None,
                triggered_by=user
            )
            triggered_jobs.append(job)
            logger.info(f"Created reconciliation job {job.id} after posting {workflow.object_reference}")
        
        return triggered_jobs
    
    @classmethod
    def trigger_workflow_jobs(cls, workflow: WorkflowInstance, new_state: str, user) -> list:
        """Main entry point - trigger appropriate jobs based on state"""
        triggered = []
        
        if new_state == WorkflowState.APPROVED:
            triggered = cls.on_workflow_approved(workflow, user)
        
        elif new_state == WorkflowState.POSTED:
            triggered = cls.on_workflow_posted(workflow, user)
        
        return triggered


class ScheduledTaskDefaults:
    """
    Creates default scheduled tasks for the ERP.
    These run periodically for system maintenance and automation.
    """
    
    DEFAULT_TASKS = [
        # Daily tasks
        {
            'name': 'Daily Overdue Scan',
            'job_type': JobType.OVERDUE_SCAN,
            'schedule_type': 'daily',
            'run_time': '06:00',
            'description': 'Scan for overdue invoices and approvals',
            'default_payload': {},
            'max_retries': 3,
        },
        {
            'name': 'Daily Expiry Scan',
            'job_type': JobType.INVENTORY_EXPIRY_SCAN,
            'schedule_type': 'daily',
            'run_time': '05:30',
            'description': 'Scan for expiring inventory items',
            'default_payload': {'days_warning': 30},
            'max_retries': 3,
        },
        {
            'name': 'Daily Cleanup - Old Sessions',
            'job_type': JobType.CLEANUP_TASK,
            'schedule_type': 'daily',
            'run_time': '02:00',
            'description': 'Clean up old session data',
            'default_payload': {'cleanup_type': 'old_sessions'},
            'max_retries': 2,
        },
        {
            'name': 'Daily Notification Cleanup',
            'job_type': JobType.CLEANUP_TASK,
            'schedule_type': 'daily',
            'run_time': '03:00',
            'description': 'Clean up old read notifications',
            'default_payload': {'cleanup_type': 'old_notifications'},
            'max_retries': 2,
        },
        
        # Weekly tasks
        {
            'name': 'Weekly Financial Reconciliation',
            'job_type': JobType.FINANCIAL_RECONCILIATION,
            'schedule_type': 'weekly',
            'run_time': '01:00',
            'day_of_week': 0,  # Sunday
            'description': 'Weekly financial reconciliation check',
            'default_payload': {},
            'max_retries': 3,
        },
        {
            'name': 'Weekly Anomaly Scan',
            'job_type': JobType.ANOMALY_SCAN,
            'schedule_type': 'weekly',
            'run_time': '02:00',
            'day_of_week': 0,  # Sunday
            'description': 'Weekly anomaly detection scan',
            'default_payload': {},
            'max_retries': 2,
        },
        {
            'name': 'Weekly Export Cleanup',
            'job_type': JobType.CLEANUP_TASK,
            'schedule_type': 'weekly',
            'run_time': '04:00',
            'day_of_week': 0,  # Sunday
            'description': 'Clean up old export files',
            'default_payload': {'cleanup_type': 'old_exports'},
            'max_retries': 2,
        },
        
        # Monthly tasks
        {
            'name': 'Monthly Backup Validation',
            'job_type': JobType.BACKUP_VALIDATION,
            'schedule_type': 'monthly',
            'run_time': '00:00',
            'day_of_month': 1,
            'description': 'Validate system backups',
            'default_payload': {},
            'max_retries': 3,
        },
        {
            'name': 'Monthly Financial Consistency Check',
            'job_type': JobType.FINANCIAL_RECONCILIATION,
            'schedule_type': 'monthly',
            'run_time': '00:30',
            'day_of_month': 1,
            'description': 'Monthly comprehensive financial check',
            'default_payload': {'comprehensive': True},
            'max_retries': 3,
        },
    ]
    
    @classmethod
    def create_default_tasks(cls):
        """Create all default scheduled tasks"""
        from jobs.models import ScheduledTask
        
        created = 0
        for task_config in cls.DEFAULT_TASKS:
            # Check if already exists
            if ScheduledTask.objects.filter(name=task_config['name']).exists():
                continue
            
            task = ScheduledTask.objects.create(
                name=task_config['name'],
                job_type=task_config['job_type'],
                schedule_type=task_config['schedule_type'],
                run_time=task_config['run_time'],
                day_of_week=task_config.get('day_of_week'),
                day_of_month=task_config.get('day_of_month'),
                is_active=True,
                default_payload=task_config.get('default_payload', {}),
                max_retries=task_config.get('max_retries', 3),
            )
            task.calculate_next_run()
            task.save()
            created += 1
            logger.info(f"Created scheduled task: {task.name}")
        
        return created
    
    @classmethod
    def initialize_system_tasks(cls):
        """Initialize system tasks - called from management command"""
        created = cls.create_default_tasks()
        logger.info(f"Initialized {created} default scheduled tasks")
        return created
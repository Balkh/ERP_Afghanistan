"""
Job Runner Service
Executes background jobs with retry logic and error handling.
"""
import logging
import traceback
from datetime import timedelta
from typing import Optional, Dict, Any

from django.utils import timezone
from django.db import transaction

from jobs.models import BackgroundJob, JobState, JobPriority, JobAuditLog
from jobs.job_registry import JobRegistry

logger = logging.getLogger(__name__)


class JobRunner:
    """
    Central job execution service.
    Handles running, retrying, and monitoring background jobs.
    """
    
    # Configuration
    MAX_RUNTIME_SECONDS = 3600  # 1 hour max
    STUCK_THRESHOLD_MINUTES = 30
    BATCH_SIZE = 10
    
    @classmethod
    def run_job(cls, job_id: int) -> bool:
        """Execute a single job"""
        try:
            job = BackgroundJob.objects.get(id=job_id)
            return cls._execute_job(job)
        except BackgroundJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            return False
    
    @classmethod
    def run_pending_jobs(cls, company_id: str = None, limit: int = 10) -> int:
        """Run pending jobs for a company or all companies"""
        qs = BackgroundJob.objects.filter(
            status__in=[JobState.PENDING, JobState.RETRYING]
        ).order_by('priority', 'created_at')
        
        if company_id:
            qs = qs.filter(company_id=company_id)
        
        qs = qs[:limit]
        
        executed = 0
        for job in qs:
            try:
                if cls._execute_job(job):
                    executed += 1
            except Exception:
                logger.exception(f"Error executing job {job.id}")
        
        return executed
    
    @classmethod
    def _execute_job(cls, job: BackgroundJob) -> bool:
        """Internal job execution with full lifecycle"""
        start_time = timezone.now()
        
        # Start job
        try:
            job.start()
        except Exception:
            logger.error(f"Failed to start job {job.id}")
            return False
        
        # Log start
        cls._log_audit(job, 'STARTED', {'payload': job.payload})
        
        # Check idempotency
        idempotency_key = job.get_idempotency_key()
        
        # Execute via registry
        try:
            handler = JobRegistry.get_handler(job.job_type)
            if not handler:
                raise ValueError(f"No handler for job type: {job.job_type}")
            
            result = handler.execute(job, job.payload)
            job.complete(result)
            
            # Log completion
            duration = (timezone.now() - start_time).total_seconds()
            cls._log_audit(job, 'COMPLETED', {'result': result, 'duration': duration})
            
            # Post-execute hook
            try:
                handler.post_execute(job, result)
            except Exception:
                logger.warning(f"Post-execute hook failed for job {job.id}")
            
            logger.info(f"Job {job.id} completed successfully")
            return True
            
        except Exception as e:
            # Handle failure
            error_trace = traceback.format_exc()
            job.fail(str(e), error_trace)
            
            # Log failure
            duration = (timezone.now() - start_time).total_seconds()
            cls._log_audit(job, 'FAILED', {
                'error': str(e),
                'traceback': error_trace,
                'retry_count': job.retry_count,
                'duration': duration
            })
            
            # Handle retry
            if job.can_retry():
                logger.info(f"Job {job.id} will be retried (attempt {job.retry_count})")
                cls._schedule_retry(job)
            else:
                logger.error(f"Job {job.id} failed permanently after {job.retry_count} retries")
            
            return False
    
    @classmethod
    def _log_audit(cls, job: BackgroundJob, action: str, details: dict):
        """Log job audit entry"""
        JobAuditLog.objects.create(
            job=job,
            action=action,
            details=details
        )
    
    @classmethod
    def _schedule_retry(cls, job: BackgroundJob):
        """Schedule job for retry with exponential backoff"""
        # Exponential backoff: 1min, 5min, 15min, 30min
        backoff_minutes = [1, 5, 15, 30]
        retry_index = min(job.retry_count - 1, len(backoff_minutes) - 1)
        
        job.scheduled_for = timezone.now() + timedelta(minutes=backoff_minutes[retry_index])
        job.is_scheduled = True
        job.save(update_fields=['scheduled_for', 'is_scheduled', 'updated_at'])
    
    @classmethod
    def detect_stuck_jobs(cls) -> int:
        """Detect and mark stuck jobs"""
        threshold = timezone.now() - timedelta(minutes=cls.STUCK_THRESHOLD_MINUTES)
        
        stuck_jobs = BackgroundJob.objects.filter(
            status=JobState.RUNNING,
            started_at__lt=threshold
        )
        
        count = 0
        for job in stuck_jobs:
            job.mark_stuck()
            cls._log_audit(job, 'STUCK', {'started_at': job.started_at.isoformat()})
            count += 1
        
        if count:
            logger.warning(f"Marked {count} jobs as stuck")
        
        return count
    
    @classmethod
    def run_scheduled_jobs(cls) -> int:
        """Run jobs that are scheduled for execution"""
        now = timezone.now()
        
        # Find scheduled jobs ready to run
        scheduled = BackgroundJob.objects.filter(
            is_scheduled=True,
            scheduled_for__lte=now,
            status__in=[JobState.PENDING, JobState.RETRYING]
        )
        
        executed = 0
        for job in scheduled:
            job.is_scheduled = False
            job.scheduled_for = None
            job.save(update_fields=['is_scheduled', 'scheduled_for', 'updated_at'])
            
            if cls._execute_job(job):
                executed += 1
        
        return executed
    
    @classmethod
    def get_job_stats(cls, company_id: str = None) -> dict:
        """Get job statistics"""
        qs = BackgroundJob.objects.all()
        if company_id:
            qs = qs.filter(company_id=company_id)
        
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        
        return {
            'total': qs.count(),
            'pending': qs.filter(status=JobState.PENDING).count(),
            'running': qs.filter(status=JobState.RUNNING).count(),
            'completed': qs.filter(status=JobState.COMPLETED).count(),
            'failed': qs.filter(status=JobState.FAILED).count(),
            'stuck': qs.filter(status=JobState.STUCK).count(),
            'last_24h': qs.filter(created_at__gte=last_24h).count(),
            'avg_duration': cls._get_avg_duration(qs.filter(status=JobState.COMPLETED)),
        }
    
    @classmethod
    def _get_avg_duration(cls, qs) -> float:
        """Calculate average job duration"""
        from django.db.models import Avg
        result = qs.annotate(
            duration=models.F('completed_at') - models.F('started_at')
        ).aggregate(avg=Avg('duration'))
        
        if result['avg']:
            return result['avg'].total_seconds()
        return 0


class JobScheduler:
    """
    Scheduler for periodic tasks.
    Runs scheduled tasks based on their configuration.
    """
    
    @classmethod
    def run_due_tasks(cls) -> int:
        """Run all due scheduled tasks"""
        from jobs.models import ScheduledTask
        from jobs.services import JobService
        
        now = timezone.now()
        
        due_tasks = ScheduledTask.objects.filter(
            is_active=True,
            next_run__lte=now
        )
        
        executed = 0
        for task in due_tasks:
            try:
                # Create a job for this task
                job = JobService.create_job(
                    job_type=task.job_type,
                    company_id=None,  # System-wide
                    payload=task.default_payload,
                    triggered_by=None,
                    max_retries=task.max_retries,
                    is_scheduled=True,
                    recurring_id=task.name
                )
                
                task.last_run = now
                task.calculate_next_run()
                task.save(update_fields=['last_run', 'next_run'])
                
                # Run immediately
                JobRunner.run_job(job.id)
                executed += 1
                
            except Exception:
                logger.exception(f"Failed to run scheduled task: {task.name}")
        
        return executed
    
    @classmethod
    def calculate_all_next_runs(cls):
        """Calculate next run times for all active tasks"""
        from jobs.models import ScheduledTask
        
        for task in ScheduledTask.objects.filter(is_active=True):
            task.calculate_next_run()
            task.save(update_fields=['next_run'])


# Import models for avg duration query
from django.db import models


class JobService:
    """
    Centralized job creation and management service.
    Provides safe, idempotent job creation with multi-company safety.
    """
    
    @staticmethod
    @transaction.atomic
    def create_job(
        job_type: str,
        company_id: Optional[str],
        payload: Dict[str, Any],
        triggered_by=None,
        priority: str = JobPriority.NORMAL,
        max_retries: int = 3,
        scheduled_for=None,
        is_scheduled: bool = False,
        recurring_id: str = '',
        idempotency_key: str = ''
    ) -> BackgroundJob:
        """Create a new background job"""
        
        # Validate job type
        if not JobRegistry.get_handler(job_type):
            raise ValueError(f"Unknown job type: {job_type}")
        
        # Check idempotency - skip if same job exists within 24h
        if idempotency_key:
            existing = BackgroundJob.objects.filter(
                idempotency_key=idempotency_key,
                status__in=[JobState.PENDING, JobState.RUNNING, JobState.RETRYING],
                created_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).first()
            
            if existing:
                logger.info(f"Skipping duplicate job with idempotency key: {idempotency_key}")
                return existing
        
        # Validate company
        if company_id:
            from core.models import Company
            if not Company.objects.filter(id=company_id, is_active=True).exists():
                raise ValueError(f"Invalid or inactive company: {company_id}")
        
        # Create job
        job = BackgroundJob.objects.create(
            job_type=job_type,
            company_id=company_id,
            status=JobState.PENDING,
            priority=priority,
            payload=payload,
            triggered_by=triggered_by,
            max_retries=max_retries,
            scheduled_for=scheduled_for,
            is_scheduled=is_scheduled,
            recurring_id=recurring_id,
            idempotency_key=idempotency_key
        )
        
        logger.info(f"Created job {job.id} of type {job_type}")
        return job
    
    @staticmethod
    def create_report_job(
        company_id: str,
        report_type: str,
        params: Dict[str, Any],
        triggered_by=None,
        priority: str = JobPriority.NORMAL
    ) -> BackgroundJob:
        """Create a report generation job"""
        
        handler = JobRegistry.get_handler('report_generation')
        idempotency_key = handler.get_idempotency_key({
            'report_type': report_type,
            'company_id': company_id,
            **params
        }) if handler else ''
        
        return JobService.create_job(
            job_type='report_generation',
            company_id=company_id,
            payload={
                'report_type': report_type,
                'params': params
            },
            triggered_by=triggered_by,
            priority=priority,
            idempotency_key=idempotency_key
        )
    
    @staticmethod
    def create_export_job(
        company_id: str,
        export_type: str,
        filters: Dict[str, Any],
        triggered_by=None
    ) -> BackgroundJob:
        """Create an export generation job"""
        
        return JobService.create_job(
            job_type='export_generation',
            company_id=company_id,
            payload={
                'export_type': export_type,
                'filters': filters,
                'timestamp': timezone.now().isoformat()
            },
            triggered_by=triggered_by,
            priority=JobPriority.NORMAL
        )
    
    @staticmethod
    def create_reconciliation_job(
        company_id: str,
        triggered_by=None
    ) -> BackgroundJob:
        """Create a financial reconciliation job"""
        
        handler = JobRegistry.get_handler('financial_reconciliation')
        from django.utils import timezone as tz
        idempotency_key = f"reconciliation:{company_id}:{tz.now().date()}"
        
        return JobService.create_job(
            job_type='financial_reconciliation',
            company_id=company_id,
            payload={'date': str(tz.now().date())},
            triggered_by=triggered_by,
            priority=JobPriority.CRITICAL,
            idempotency_key=idempotency_key
        )
    
    @staticmethod
    def create_anomaly_scan_job(
        company_id: str,
        triggered_by=None
    ) -> BackgroundJob:
        """Create an anomaly scan job"""
        
        return JobService.create_job(
            job_type='anomaly_scan',
            company_id=company_id,
            payload={},
            triggered_by=triggered_by,
            priority=JobPriority.NORMAL
        )
    
    @staticmethod
    def create_expiry_scan_job(
        company_id: str,
        days_warning: int = 30,
        triggered_by=None
    ) -> BackgroundJob:
        """Create an inventory expiry scan job"""
        
        return JobService.create_job(
            job_type='inventory_expiry_scan',
            company_id=company_id,
            payload={'days_warning': days_warning},
            triggered_by=triggered_by,
            priority=JobPriority.HIGH
        )
    
    @staticmethod
    def create_overdue_scan_job(
        company_id: str,
        triggered_by=None
    ) -> BackgroundJob:
        """Create an overdue scan job"""
        
        return JobService.create_job(
            job_type='overdue_scan',
            company_id=company_id,
            payload={},
            triggered_by=triggered_by,
            priority=JobPriority.HIGH
        )
    
    @staticmethod
    def create_notification_job(
        company_id: str,
        notification_type: str,
        user_ids: list,
        title: str,
        message: str,
        severity: str = 'INFO'
    ) -> BackgroundJob:
        """Create a notification dispatch job"""
        
        return JobService.create_job(
            job_type='notification_dispatch',
            company_id=company_id,
            payload={
                'notification_type': notification_type,
                'user_ids': user_ids,
                'title': title,
                'message': message,
                'severity': severity
            },
            priority=JobPriority.HIGH
        )
    
    @staticmethod
    def create_cleanup_job(
        company_id: str,
        cleanup_type: str,
        triggered_by=None
    ) -> BackgroundJob:
        """Create a cleanup job"""
        
        return JobService.create_job(
            job_type='cleanup_task',
            company_id=company_id,
            payload={'cleanup_type': cleanup_type},
            triggered_by=triggered_by,
            priority=JobPriority.LOW
        )
    
    @staticmethod
    def get_job_status(job_id: int) -> Optional[Dict[str, Any]]:
        """Get job status"""
        try:
            job = BackgroundJob.objects.get(id=job_id)
            return {
                'id': job.id,
                'job_type': job.job_type,
                'status': job.status,
                'status_display': job.get_status_display(),
                'progress_percent': job.progress_percent,
                'progress_message': job.progress_message,
                'result': job.result,
                'error_message': job.error_message,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'duration_seconds': job.get_duration_seconds(),
            }
        except BackgroundJob.DoesNotExist:
            return None
    
    @staticmethod
    def cancel_job(job_id: int) -> bool:
        """Cancel a pending job"""
        try:
            job = BackgroundJob.objects.get(id=job_id)
            if job.status in [JobState.PENDING, JobState.RETRYING]:
                job.cancel()
                return True
            return False
        except BackgroundJob.DoesNotExist:
            return False
    
    @staticmethod
    def retry_job(job_id: int) -> bool:
        """Manually retry a failed job"""
        try:
            job = BackgroundJob.objects.get(id=job_id)
            if job.status in [JobState.FAILED, JobState.STUCK]:
                job.status = JobState.PENDING
                job.error_message = ''
                job.error_traceback = ''
                job.save(update_fields=['status', 'error_message', 'error_traceback', 'updated_at'])
                return True
            return False
        except BackgroundJob.DoesNotExist:
            return False
"""
Background Job Models
Centralized async job processing.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models.base import TimeStampedUUIDModel
from core.models import Company


class JobState:
    """Background job states"""
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    RETRYING = 'RETRYING'
    CANCELLED = 'CANCELLED'
    STUCK = 'STUCK'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (RUNNING, 'Running'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (RETRYING, 'Retrying'),
        (CANCELLED, 'Cancelled'),
        (STUCK, 'Stuck'),
    ]
    
    FINAL_STATES = [COMPLETED, FAILED, CANCELLED, STUCK]


class JobPriority:
    """Job priority levels"""
    LOW = 'LOW'
    NORMAL = 'NORMAL'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'
    
    CHOICES = [
        (LOW, 'Low'),
        (NORMAL, 'Normal'),
        (HIGH, 'High'),
        (CRITICAL, 'Critical'),
    ]
    
    ORDER = {CRITICAL: 0, HIGH: 1, NORMAL: 2, LOW: 3}


class JobType:
    """Supported job types"""
    REPORT_GENERATION = 'report_generation'
    EXPORT_GENERATION = 'export_generation'
    FINANCIAL_RECONCILIATION = 'financial_reconciliation'
    ANOMALY_SCAN = 'anomaly_scan'
    INVENTORY_EXPIRY_SCAN = 'inventory_expiry_scan'
    NOTIFICATION_DISPATCH = 'notification_dispatch'
    BACKUP_VALIDATION = 'backup_validation'
    CLEANUP_TASK = 'cleanup_task'
    WORKFLOW_NOTIFICATION = 'workflow_notification'
    OVERDUE_SCAN = 'overdue_scan'
    
    CHOICES = [
        (REPORT_GENERATION, 'Report Generation'),
        (EXPORT_GENERATION, 'Export Generation'),
        (FINANCIAL_RECONCILIATION, 'Financial Reconciliation'),
        (ANOMALY_SCAN, 'Anomaly Scan'),
        (INVENTORY_EXPIRY_SCAN, 'Inventory Expiry Scan'),
        (NOTIFICATION_DISPATCH, 'Notification Dispatch'),
        (BACKUP_VALIDATION, 'Backup Validation'),
        (CLEANUP_TASK, 'Cleanup Task'),
        (WORKFLOW_NOTIFICATION, 'Workflow Notification'),
        (OVERDUE_SCAN, 'Overdue Scan'),
    ]


class BackgroundJob(TimeStampedUUIDModel):
    """
    Centralized background job model.
    Supports async processing with retry, recovery, and audit.
    """
    job_type = models.CharField(max_length=50, choices=JobType.CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=JobState.CHOICES, default=JobState.PENDING, db_index=True)
    priority = models.CharField(max_length=20, choices=JobPriority.CHOICES, default=JobPriority.NORMAL, db_index=True)
    
    payload = models.JSONField(default=dict, help_text=_('Job input data'))
    result = models.JSONField(default=dict, help_text=_('Job output data'))
    
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    # Execution tracking
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='triggered_jobs'
    )
    
    # Company isolation
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='background_jobs'
    )
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    is_scheduled = models.BooleanField(default=False)
    recurring_id = models.CharField(max_length=50, blank=True, help_text=_('ID for recurring jobs'))
    
    # Idempotency
    idempotency_key = models.CharField(max_length=100, blank=True, db_index=True, help_text=_('Key to prevent duplicate execution'))
    
    # Progress
    progress_percent = models.PositiveIntegerField(default=0)
    progress_message = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'background_job'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['job_type', 'status']),
            models.Index(fields=['scheduled_for', 'is_scheduled']),
            models.Index(fields=['company', 'status']),
        ]
    
    def __str__(self):
        return f"{self.job_type} [{self.status}] - {self.id}"
    
    def clean(self):
        if self.retry_count > self.max_retries:
            raise ValidationError(_('Retry count exceeds max retries'))
    
    def can_retry(self):
        """Check if job can be retried"""
        return (
            self.status in [JobState.FAILED, JobState.STUCK] and 
            self.retry_count < self.max_retries
        )
    
    def start(self, user=None):
        """Start job execution"""
        self.status = JobState.RUNNING
        self.started_at = timezone.now()
        self.progress_percent = 0
        self.save(update_fields=['status', 'started_at', 'progress_percent', 'updated_at'])
    
    def complete(self, result=None):
        """Mark job as completed"""
        self.status = JobState.COMPLETED
        self.completed_at = timezone.now()
        self.progress_percent = 100
        self.result = result or {}
        self.save(update_fields=['status', 'completed_at', 'progress_percent', 'result', 'updated_at'])
    
    def fail(self, error_message, error_traceback=''):
        """Mark job as failed"""
        self.status = JobState.FAILED if self.retry_count >= self.max_retries else JobState.RETRYING
        self.failed_at = timezone.now()
        self.error_message = str(error_message)[:2000]
        self.error_traceback = error_traceback[:5000]
        
        if self.status == JobState.RETRYING:
            self.retry_count += 1
            self.last_retry_at = timezone.now()
        
        self.save(update_fields=[
            'status', 'failed_at', 'error_message', 'error_traceback', 
            'retry_count', 'last_retry_at', 'updated_at'
        ])
    
    def cancel(self):
        """Cancel job"""
        self.status = JobState.CANCELLED
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_stuck(self):
        """Mark job as stuck"""
        self.status = JobState.STUCK
        self.error_message = 'Job exceeded maximum execution time'
        self.save(update_fields=['status', 'error_message', 'updated_at'])
    
    def get_duration_seconds(self):
        """Get job execution duration in seconds"""
        if self.started_at:
            end = self.completed_at or timezone.now()
            return (end - self.started_at).total_seconds()
        return 0
    
    def get_idempotency_key(self):
        """Get the idempotency key for this job"""
        return self.idempotency_key or f"{self.job_type}:{self.id}"


class JobAuditLog(TimeStampedUUIDModel):
    """Audit trail for job execution"""
    job = models.ForeignKey(BackgroundJob, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50)
    details = models.JSONField(default=dict)
    duration_seconds = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'job_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.job_id} - {self.action}"


class ScheduledTask(TimeStampedUUIDModel):
    """Scheduled task configuration"""
    name = models.CharField(max_length=100, unique=True)
    job_type = models.CharField(max_length=50, choices=JobType.CHOICES)
    
    # Schedule configuration
    CRON_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    schedule_type = models.CharField(max_length=20, choices=CRON_CHOICES, default='daily')
    
    # Time configuration (HH:MM format)
    run_time = models.CharField(max_length=5, default='00:00')
    
    # Day of week for weekly (0=Monday, 6=Sunday)
    day_of_week = models.PositiveIntegerField(null=True, blank=True)
    # Day of month for monthly (1-31)
    day_of_month = models.PositiveIntegerField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    # Job configuration
    default_payload = models.JSONField(default=dict)
    max_retries = models.PositiveIntegerField(default=3)
    
    class Meta:
        db_table = 'scheduled_task'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.schedule_type})"
    
    def calculate_next_run(self):
        """Calculate next run time based on schedule"""
        from datetime import datetime, timedelta
        now = timezone.now()
        
        hour, minute = map(int, self.run_time.split(':'))
        
        if self.schedule_type == 'daily':
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif self.schedule_type == 'weekly':
            days_ahead = (self.day_of_week - now.weekday()) % 7
            if days_ahead == 0 and now.hour >= hour:
                days_ahead = 7
            next_run = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        
        elif self.schedule_type == 'monthly':
            target_day = min(self.day_of_month or 1, 28)
            next_run = now.replace(day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                from calendar import monthrange
                days_in_month = monthrange(now.year, now.month)[1]
                next_run = (now + timedelta(days=days_in_month - now.day + target_day)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
        
        self.next_run = next_run
        return next_run
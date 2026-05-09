import uuid
from django.db import models
from django.conf import settings


class BackupRecord(models.Model):
    """Tracks backup operations and metadata"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('verified', 'Verified'),
        ('restored', 'Restored'),
        ('deleted', 'Deleted'),
    ]
    
    TYPE_CHOICES = [
        ('manual', 'Manual'),
        ('scheduled', 'Scheduled'),
        ('pre_update', 'Pre-Update'),
        ('pre_maintenance', 'Pre-Maintenance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Backup details
    backup_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='manual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # File information
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size_bytes = models.BigIntegerField(default=0)
    
    # Metadata
    checksum = models.CharField(max_length=64, blank=True, help_text='SHA-256 checksum')
    description = models.TextField(blank=True)
    encrypted = models.BooleanField(default=False)
    compressed = models.BooleanField(default=False)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Database info
    database_path = models.CharField(max_length=500, blank=True)
    database_size_bytes = models.BigIntegerField(default=0)
    
    # User who initiated the backup
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backups_created'
    )
    
    # Verification
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backups_verified'
    )
    verification_result = models.TextField(blank=True)
    
    # Restore info
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backups_restored'
    )
    restore_target_path = models.CharField(max_length=500, blank=True)
    
    class Meta:
        db_table = 'backup_record'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['backup_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.filename} ({self.status})"
    
    @property
    def file_size_mb(self):
        return round(self.file_size_bytes / (1024 * 1024), 2)
    
    @property
    def database_size_mb(self):
        return round(self.database_size_bytes / (1024 * 1024), 2)


class BackupSchedule(models.Model):
    """Stores backup schedule configurations"""
    
    FREQUENCY_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    time = models.CharField(max_length=5, default='02:00', help_text='HH:MM format')
    day_of_week = models.CharField(max_length=20, blank=True, help_text='For weekly frequency')
    day_of_month = models.IntegerField(default=1, help_text='For monthly frequency')
    
    enabled = models.BooleanField(default=True)
    encrypted = models.BooleanField(default=True)
    compressed = models.BooleanField(default=True)
    include_files = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    
    # Retention
    max_backups = models.IntegerField(default=30)
    max_age_days = models.IntegerField(default=90)
    
    # Last run info
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=20, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'backup_schedule'
        verbose_name_plural = 'Backup schedules'
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"


class BackupLog(models.Model):
    """Logs backup operations for auditing"""
    
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    EVENT_CHOICES = [
        ('backup_started', 'Backup Started'),
        ('backup_completed', 'Backup Completed'),
        ('backup_failed', 'Backup Failed'),
        ('restore_started', 'Restore Started'),
        ('restore_completed', 'Restore Completed'),
        ('restore_failed', 'Restore Failed'),
        ('backup_deleted', 'Backup Deleted'),
        ('backup_verified', 'Backup Verified'),
        ('schedule_created', 'Schedule Created'),
        ('schedule_updated', 'Schedule Updated'),
        ('schedule_deleted', 'Schedule Deleted'),
        ('cleanup_started', 'Cleanup Started'),
        ('cleanup_completed', 'Cleanup Completed'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    event = models.CharField(max_length=30, choices=EVENT_CHOICES)
    message = models.TextField()
    
    # Optional references
    backup_record = models.ForeignKey(
        BackupRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    schedule = models.ForeignKey(
        BackupSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    # Additional data
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'backup_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['level', 'timestamp']),
            models.Index(fields=['event', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.level} - {self.event}"


class RestorePoint(models.Model):
    """Tracks restore operations and validation"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('validating', 'Validating'),
        ('validated', 'Validated'),
        ('failed', 'Failed'),
        ('restored', 'Restored'),
        ('rolled_back', 'Rolled Back'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Reference to backup
    backup_record = models.ForeignKey(
        BackupRecord,
        on_delete=models.CASCADE,
        related_name='restore_points'
    )
    
    # Restore details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Validation results
    is_valid = models.BooleanField(default=False)
    validation_errors = models.JSONField(default=list, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restore_validations'
    )
    
    # Restore info
    restore_started_at = models.DateTimeField(null=True, blank=True)
    restore_completed_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restores_performed'
    )
    
    # Rollback protection
    can_rollback = models.BooleanField(default=True)
    rollback_reason = models.TextField(blank=True)
    
    # Pre-restore snapshot (for rollback)
    snapshot_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'backup_restore_point'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['backup_record', 'status']),
        ]
    
    def __str__(self):
        return f"Restore {self.backup_record.filename} ({self.status})"


class RestoreValidation(models.Model):
    """Stores validation results for restore operations"""
    
    TYPE_CHOICES = [
        ('schema', 'Schema Validation'),
        ('data_integrity', 'Data Integrity'),
        ('foreign_key', 'Foreign Key Check'),
        ('business_rule', 'Business Rule'),
        ('transaction', 'Transaction Check'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restore_point = models.ForeignKey(
        RestorePoint,
        on_delete=models.CASCADE,
        related_name='validations'
    )
    
    validation_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    is_valid = models.BooleanField()
    error_message = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'backup_restore_validation'
    
    def __str__(self):
        return f"{self.validation_type}: {'PASS' if self.is_valid else 'FAIL'}"
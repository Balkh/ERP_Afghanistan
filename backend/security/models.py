from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class Role(models.Model):
    """
    Role model for RBAC (Role-Based Access Control)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'security_role'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


class Permission(models.Model):
    """
    Permission model for fine-grained access control
    """
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(
        max_length=100,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[a-z][a-z0-9_]*$',
            message='Codename must be lowercase letters, numbers, and underscores only, starting with a letter'
        )]
    )
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50, help_text='App/module this permission belongs to')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'security_permission'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        unique_together = ('module', 'codename')

    def __str__(self):
        return f"{self.module}.{self.codename}"


class RolePermission(models.Model):
    """
    Many-to-many relationship between Role and Permission
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='permission_roles')
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'security_role_permission'
        unique_together = ('role', 'permission')
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'

    def __str__(self):
        return f"{self.role.name} -> {self.permission.name}"


class UserRole(models.Model):
    """
    Many-to-many relationship between User and Role
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_roles')
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Role assignment expiration (null = permanent)')

    class Meta:
        db_table = 'security_user_role'
        unique_together = ('user', 'role')
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return f"{self.user.username} -> {self.role.name}"

    @property
    def is_expired(self):
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False


class AuditLog(models.Model):
    """
    Audit trail for tracking user actions and system events
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('PERMISSION_DENIED', 'Permission Denied'),
        ('SYSTEM', 'System Event'),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    username = models.CharField(max_length=150, blank=True, help_text='Username at time of action')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True, help_text='Model affected (if applicable)')
    object_id = models.CharField(max_length=100, blank=True, help_text='Primary key of object (if applicable)')
    object_repr = models.CharField(max_length=200, blank=True, help_text='String representation of object')
    change_message = models.TextField(blank=True, help_text='Description of changes made')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    additional_data = models.JSONField(default=dict, blank=True, help_text='Additional context data')

    class Meta:
        db_table = 'security_audit_log'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.username or 'Anonymous'} - {self.action}"


class SecurityEvent(models.Model):
    """
    Security-specific events for monitoring threats and anomalies
    """
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    EVENT_TYPES = [
        ('BRUTE_FORCE', 'Brute Force Attack'),
        ('SQL_INJECTION', 'SQL Injection Attempt'),
        ('XSS_ATTEMPT', 'XSS Attempt'),
        ('PATH_TRAVERSAL', 'Path Traversal Attempt'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access Attempt'),
        ('PRIVILEGE_ESCALATION', 'Privilege Escalation Attempt'),
        ('TAMPERING_DETECTED', 'Tampering Detected'),
        ('LICENSE_VIOLATION', 'License Violation'),
        ('DATA_EXFILTRATION', 'Data Exfiltration Attempt'),
    ]

    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='security_events')
    username = models.CharField(max_length=150, blank=True, help_text='Username at time of event')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_security_events')
    resolution_notes = models.TextField(blank=True)
    additional_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'security_security_event'
        verbose_name = 'Security Event'
        verbose_name_plural = 'Security Events'
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['severity', 'timestamp']),
            models.Index(fields=['is_resolved']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.get_event_type_display()} - {self.severity}"


class Notification(models.Model):
    """
    User notifications for stock alerts, activity, and system events
    """
    TYPE_CHOICES = [
        ('STOCK_LOW', 'Low Stock Alert'),
        ('STOCK_EXPIRY', 'Expiring Batch Alert'),
        ('STOCK_OUT', 'Out of Stock Alert'),
        ('ACTIVITY_LOGIN', 'User Login'),
        ('ACTIVITY_LOGOUT', 'User Logout'),
        ('ACTIVITY_CREATE', 'Record Created'),
        ('ACTIVITY_UPDATE', 'Record Updated'),
        ('ACTIVITY_DELETE', 'Record Deleted'),
        ('SYSTEM', 'System Alert'),
    ]

    SEVERITY_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='INFO')
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional link to related object
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Optional reference to inventory/item
    product = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    batch = models.ForeignKey('inventory.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'security_notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['user', 'notification_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.title}"

    def mark_as_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
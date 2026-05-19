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
    require_2fa = models.BooleanField(default=False, help_text='Require two-factor authentication for users with this role')
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


class PasswordResetToken(models.Model):
    """
    Secure password reset token with expiration and single-use enforcement.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text='Token expiration time (default: 1 hour)')
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'security_password_reset_token'
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reset token for {self.user.username} (expires: {self.expires_at})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired


class TOTPDevice(models.Model):
    """
    TOTP (Time-based One-Time Password) device for 2FA.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='totp_device')
    secret = models.CharField(max_length=64, help_text='Base32-encoded TOTP secret')
    is_confirmed = models.BooleanField(default=False, help_text='True after user verifies first TOTP code')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True, help_text='Lockout after too many failed attempts')

    class Meta:
        db_table = 'security_totp_device'
        verbose_name = 'TOTP Device'
        verbose_name_plural = 'TOTP Devices'

    def __str__(self):
        return f"TOTP for {self.user.username} (confirmed: {self.is_confirmed})"

    @property
    def is_locked(self):
        from django.utils import timezone
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def record_failure(self, max_attempts=5, lockout_minutes=15):
        """Record a failed TOTP attempt and lock if threshold exceeded."""
        from django.utils import timezone
        import datetime
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.locked_until = timezone.now() + datetime.timedelta(minutes=lockout_minutes)
        self.save(update_fields=['failed_attempts', 'locked_until'])

    def reset_failures(self):
        """Reset failure counter on successful verification."""
        self.failed_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_attempts', 'locked_until'])


class RevokedToken(models.Model):
    """
    Persistent token revocation store.
    Replaces in-memory blacklist so revocations survive server restarts.
    Expired entries are cleaned up by a management command or periodic task.
    """
    id = models.BigAutoField(primary_key=True)
    jti = models.CharField(max_length=255, unique=True, db_index=True, help_text='JWT ID claim')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revoked_tokens', null=True, blank=True)
    token_type = models.CharField(max_length=10, choices=[('access', 'Access'), ('refresh', 'Refresh')], default='access')
    revoked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text='Original token expiry — used for cleanup')
    reason = models.CharField(max_length=50, blank=True, default='', choices=[
        ('logout', 'User logout'),
        ('password_change', 'Password changed'),
        ('admin_revoke', 'Admin revocation'),
        ('security_event', 'Security event'),
    ])

    class Meta:
        db_table = 'security_revoked_token'
        verbose_name = 'Revoked Token'
        verbose_name_plural = 'Revoked Tokens'
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['user', 'revoked_at']),
        ]
        ordering = ['-revoked_at']

    def __str__(self):
        return f"Revoked token {self.jti[:8]}... (user: {self.user_id}, type: {self.token_type})"

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        """Check if a token JTI is in the revocation store."""
        return cls.objects.filter(jti=jti).exists()

    @classmethod
    def revoke(cls, jti: str, user=None, token_type='access', expires_at=None, reason='logout') -> 'RevokedToken':
        """Add a token to the revocation store."""
        from django.utils import timezone
        if expires_at is None:
            expires_at = timezone.now() + timezone.timedelta(hours=24)
        obj, _ = cls.objects.get_or_create(
            jti=jti,
            defaults={
                'user': user,
                'token_type': token_type,
                'expires_at': expires_at,
                'reason': reason,
            }
        )
        return obj

    @classmethod
    def cleanup_expired(cls) -> int:
        """Remove expired revoked tokens. Returns count of deleted rows."""
        from django.utils import timezone
        deleted, _ = cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return deleted
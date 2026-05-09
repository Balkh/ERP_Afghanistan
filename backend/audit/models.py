import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel


class AuditTrail(TimeStampedUUIDModel):
    """Advanced audit trail for all data changes."""

    ACTION_CHOICES = [
        ('CREATE', _('Create')),
        ('UPDATE', _('Update')),
        ('DELETE', _('Delete')),
        ('VIEW', _('View')),
        ('LOGIN', _('Login')),
        ('LOGOUT', _('Logout')),
        ('EXPORT', _('Export')),
        ('IMPORT', _('Import')),
        ('APPROVE', _('Approve')),
        ('REJECT', _('Reject')),
        ('REVERSE', _('Reverse')),
        ('CANCEL', _('Cancel')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_trail_logs',
        verbose_name=_('User')
    )
    username = models.CharField(max_length=150, verbose_name=_('Username'))
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_('Action'))
    app_label = models.CharField(max_length=50, verbose_name=_('App'))
    model_name = models.CharField(max_length=100, verbose_name=_('Model'))
    object_id = models.CharField(max_length=50, blank=True, verbose_name=_('Object ID'))
    object_repr = models.TextField(blank=True, verbose_name=_('Object Representation'))
    changes = models.JSONField(default=dict, verbose_name=_('Field Changes'))
    old_values = models.JSONField(default=dict, verbose_name=_('Old Values'))
    new_values = models.JSONField(default=dict, verbose_name=_('New Values'))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('IP Address'))
    user_agent = models.TextField(blank=True, verbose_name=_('User Agent'))
    session_key = models.CharField(max_length=40, blank=True, verbose_name=_('Session Key'))
    request_method = models.CharField(max_length=10, blank=True, verbose_name=_('Request Method'))
    request_path = models.TextField(blank=True, verbose_name=_('Request Path'))
    is_error = models.BooleanField(default=False, verbose_name=_('Is Error'))
    error_message = models.TextField(blank=True, verbose_name=_('Error Message'))
    execution_time_ms = models.IntegerField(null=True, blank=True, verbose_name=_('Execution Time (ms)'))

    class Meta:
        verbose_name = _('Audit Trail')
        verbose_name_plural = _('Audit Trails')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['app_label', 'model_name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['object_id']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.created_at}"


class AuditRetentionPolicy(TimeStampedUUIDModel):
    """Defines retention periods for audit logs."""

    name = models.CharField(max_length=100, verbose_name=_('Policy Name'))
    app_labels = models.JSONField(default=list, verbose_name=_('App Labels'))
    action_types = models.JSONField(default=list, verbose_name=_('Action Types'))
    retention_days = models.IntegerField(verbose_name=_('Retention Days'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Audit Retention Policy')
        verbose_name_plural = _('Audit Retention Policies')

    def __str__(self):
        return f"{self.name} ({self.retention_days} days)"
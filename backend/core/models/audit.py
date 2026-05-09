import uuid
from django.db import models
from django.contrib.auth import get_user_model
from core.models.base import BaseModel

User = get_user_model()


class AuditLog(BaseModel):
    """Lightweight audit log for core operations."""
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('POST', 'Post'),
        ('REVERSE', 'Reverse'),
    ]
    
    MODULE_CHOICES = [
        ('ACCOUNTING', 'Accounting'),
        ('INVENTORY', 'Inventory'),
        ('SALES', 'Sales'),
        ('PURCHASES', 'Purchases'),
        ('PAYMENTS', 'Payments'),
        ('HR', 'HR'),
        ('SYSTEM', 'System'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='core_audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    before_state = models.JSONField(default=dict, blank=True)
    after_state = models.JSONField(default=dict, blank=True)
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, default='SYSTEM')
    description = models.TextField(blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}:{self.entity_id}"


class SystemConfig(BaseModel):
    """Key-value system configuration storage."""
    
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField()
    description = models.TextField(blank=True, default='')
    is_sensitive = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'

    def __str__(self):
        return self.key
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class TimeStampedUUIDModel(models.Model):
    """
    An abstract base class model that provides UUID as primary key
    and timestamp fields.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.id)


class SoftDeleteModel(models.Model):
    """
    An abstract base class model that provides soft delete functionality.
    """
    is_deleted = models.BooleanField(default=False, verbose_name=_('Is Deleted'))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Deleted At'))

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the object."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self):
        """Permanently delete the object."""
        super().delete()

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])

    class Meta:
        abstract = True


class BaseModel(TimeStampedUUIDModel, SoftDeleteModel):
    """
    Abstract base model that combines UUID primary key, timestamps,
    and soft delete functionality.
    """
    class Meta:
        abstract = True


class AuditLog(BaseModel):
    """
    Model to track changes to important entities in the system.
    """
    ACTION_CHOICES = [
        ('CREATE', _('Create')),
        ('UPDATE', _('Update')),
        ('DELETE', _('Delete')),
        ('RESTORE', _('Restore')),
        ('LOGIN', _('Login')),
        ('LOGOUT', _('Logout')),
        ('ACCESS', _('Access')),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_('User')
    )
    action = models.CharField(
        max_length=20, 
        choices=ACTION_CHOICES, 
        verbose_name=_('Action')
    )
    model_name = models.CharField(max_length=100, verbose_name=_('Model Name'))
    object_id = models.CharField(max_length=100, verbose_name=_('Object ID'))
    object_repr = models.CharField(max_length=200, verbose_name=_('Object Representation'))
    changes = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name=_('Changes'),
        help_text=_('JSON representation of the changes made')
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        verbose_name=_('IP Address')
    )
    user_agent = models.TextField(
        blank=True, 
        verbose_name=_('User Agent')
    )

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.model_name} - {self.object_repr}"
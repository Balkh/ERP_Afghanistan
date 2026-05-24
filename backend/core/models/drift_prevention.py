import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class DriftRecord(models.Model):
    """Records a comparison between JournalEngine (source of truth) and JournalGateway (shadow)."""

    CLASS_CHOICES = [
        ('A', 'A — Match'),
        ('B', 'B — Minor Deviation'),
        ('C', 'C — Financial Drift (CRITICAL)'),
        ('D', 'D — System Failure'),
    ]

    IMPACT_CHOICES = [
        ('NONE', 'No financial impact'),
        ('LOW', 'Low financial impact'),
        ('HIGH', 'High financial impact'),
        ('CRITICAL', 'Critical financial impact'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.CharField(max_length=64, db_index=True, help_text=_('Originating module (expenses, returns, payments, purchases, sales)'))
    operation = models.CharField(max_length=64, help_text=_('Operation type (create_entry, reverse_entry, post_entry)'))
    reference = models.CharField(max_length=255, blank=True, db_index=True, help_text=_('Document reference (invoice number, expense number, etc.)'))
    classification = models.CharField(max_length=2, choices=CLASS_CHOICES, db_index=True)
    financial_impact = models.CharField(max_length=16, choices=IMPACT_CHOICES, default='NONE')
    engine_entry_id = models.CharField(max_length=255, blank=True, help_text=_('JournalEntry ID created by JournalEngine'))
    gateway_entry_id = models.CharField(max_length=255, blank=True, help_text=_('JournalEntry ID created by JournalGateway'))
    mismatch_detail = models.JSONField(default=dict, blank=True, help_text=_('Structured mismatch description'))
    engine_success = models.BooleanField(null=True)
    gateway_success = models.BooleanField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Drift Record')
        verbose_name_plural = _('Drift Records')
        indexes = [
            models.Index(fields=['module', 'classification']),
            models.Index(fields=['module', 'created_at']),
        ]

    def __str__(self):
        return f'{self.module}.{self.operation} [{self.classification}] @ {self.created_at}'


class ModuleDriftState(models.Model):
    """Aggregated drift state per module — determines Phase 3 blocking."""

    module = models.CharField(max_length=64, unique=True, db_index=True)
    latest_classification = models.CharField(max_length=2, choices=DriftRecord.CLASS_CHOICES, default='A')
    total_comparisons = models.PositiveIntegerField(default=0)
    class_c_count = models.PositiveIntegerField(default=0, help_text=_('Number of Class C (Critical) drifts'))
    class_d_count = models.PositiveIntegerField(default=0, help_text=_('Number of Class D (System Failure) drifts'))
    is_blocked = models.BooleanField(default=False, help_text=_('Blocked from Phase 3 migration'))
    block_reason = models.TextField(blank=True, help_text=_('Reason for blocking'))
    last_drift_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Module Drift State')
        verbose_name_plural = _('Module Drift States')

    def __str__(self):
        status = 'BLOCKED' if self.is_blocked else 'ALLOWED'
        return f'{self.module}: {self.latest_classification} ({status})'

    def clean(self):
        if self.class_c_count > 0 and not self.is_blocked:
            raise ValidationError(_('Module with Class C drifts must be blocked.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

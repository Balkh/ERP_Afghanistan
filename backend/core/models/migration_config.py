from django.db import models
from django.utils.translation import gettext_lazy as _


class MigrationConfig(models.Model):
    """Per-function migration state for JournalEngine → JournalGateway switchover."""

    STATE_CHOICES = [
        ('ENGINE', _('Engine — using JournalEngine')),
        ('READY', _('Ready — passes readiness checks, awaiting switch')),
        ('GATEWAY', _('Gateway — using JournalGateway')),
        ('ROLLED_BACK', _('Rolled Back — was Gateway, returned to Engine due to drift')),
    ]

    module = models.CharField(max_length=64, db_index=True)
    function = models.CharField(max_length=64, help_text=_('Operation name (create_entry, reverse_entry, post_entry)'))
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default='ENGINE', db_index=True)
    switched_at = models.DateTimeField(null=True, blank=True, help_text=_('When this function was switched to Gateway'))
    rolled_back_at = models.DateTimeField(null=True, blank=True)
    rollback_reason = models.TextField(blank=True)
    gateway_call_count = models.PositiveIntegerField(default=0, help_text=_('Number of successful Gateway calls'))
    drift_count_since_switch = models.PositiveIntegerField(default=0)
    last_execution_hash = models.CharField(max_length=64, blank=True, help_text=_('SHA-256 of last execution params'))
    last_financial_signature = models.CharField(max_length=64, blank=True, help_text=_('Hash of resulting journal lines'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Migration Config')
        verbose_name_plural = _('Migration Configs')
        unique_together = [('module', 'function')]
        indexes = [
            models.Index(fields=['module', 'state']),
        ]

    def __str__(self):
        return f'{self.module}.{self.function} [{self.state}]'


class MigrationLog(models.Model):
    """Audit log for every switchover event."""

    MODULE_CHOICES = [
        ('expenses', 'Expenses'),
        ('returns', 'Returns'),
        ('payments', 'Payments'),
        ('purchases', 'Purchases'),
        ('sales', 'Sales'),
        ('accounting', 'Accounting'),
    ]

    OPERATION_CHOICES = [
        ('create_entry', 'Create Entry'),
        ('reverse_entry', 'Reverse Entry'),
        ('post_entry', 'Post Entry'),
    ]

    ENGINE_CHOICES = [
        ('ENGINE', 'JournalEngine'),
        ('GATEWAY', 'JournalGateway'),
    ]

    module = models.CharField(max_length=64, db_index=True, choices=MODULE_CHOICES)
    function = models.CharField(max_length=64, choices=OPERATION_CHOICES)
    engine_used = models.CharField(max_length=16, choices=ENGINE_CHOICES)
    execution_hash = models.CharField(max_length=64, blank=True, help_text=_('SHA-256 of normalized execution parameters'))
    financial_signature = models.CharField(max_length=64, blank=True, help_text=_('SHA-256 of resulting debit/credit lines'))
    drift_score = models.IntegerField(default=0, help_text=_('0=clean, 1-100=drift severity at execution time'))
    validation_result = models.CharField(max_length=32, default='PASS', help_text=_('PASS, FAIL, ROLLED_BACK'))
    reference = models.CharField(max_length=255, blank=True, help_text=_('Document reference'))
    duration_ms = models.IntegerField(default=0, help_text=_('Execution duration in milliseconds'))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Migration Log')
        verbose_name_plural = _('Migration Logs')

    def __str__(self):
        return f'{self.engine_used}: {self.module}.{self.function} [{self.validation_result}] @ {self.created_at}'

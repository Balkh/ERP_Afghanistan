"""Decision Record model — bounded governance decision store.

Stores policy engine decisions with lifecycle management.
Bounded to max 200 recent records per entity_type.
"""
import uuid
from django.db import models
from django.utils import timezone


class DecisionRecord(models.Model):
    """Lightweight policy decision record with lifecycle management.
    
    Stores deterministic policy decisions for traceability and governance.
    Bounded storage — old records are pruned automatically.
    """
    DECISION_TYPES = [
        ('ALLOW', 'Allow'),
        ('WARN', 'Warning'),
        ('SOFT_BLOCK', 'Soft Block'),
        ('HARD_BLOCK', 'Hard Block'),
        ('ESCALATE_MANAGER', 'Escalate to Manager'),
    ]

    LIFECYCLE_STATES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('RESOLVED', 'Resolved'),
        ('SUPERSEDED', 'Superseded'),
        ('EXPIRED', 'Expired'),
    ]

    ENTITY_TYPES = [
        ('Customer', 'Customer'),
        ('Supplier', 'Supplier'),
        ('SalesInvoice', 'Sales Invoice'),
        ('PurchaseInvoice', 'Purchase Invoice'),
        ('CustomerPayment', 'Customer Payment'),
        ('SupplierPayment', 'Supplier Payment'),
        ('ReturnOrder', 'Return Order'),
        ('System', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=30, choices=ENTITY_TYPES)
    entity_id = models.CharField(max_length=50)
    risk_score = models.IntegerField(default=0)
    decision_type = models.CharField(max_length=20, choices=DECISION_TYPES)
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LIFECYCLE_STATES,
        default='ACTIVE',
    )
    triggered_rules = models.JSONField(default=list)
    explanation = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    source_modules = models.JSONField(default=list)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id', 'lifecycle_state']),
            models.Index(fields=['decision_type', 'lifecycle_state']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f'{self.decision_type} - {self.entity_type}/{self.entity_id}'

    @staticmethod
    def enforce_bounded_storage(max_records=200):
        """Prune old records to maintain bounded storage.
        
        Keeps only the most recent max_records entries.
        """
        total = DecisionRecord.objects.count()
        if total > max_records:
            to_delete = total - max_records
            oldest_ids = DecisionRecord.objects.order_by('timestamp').values_list(
                'id', flat=True
            )[:to_delete]
            DecisionRecord.objects.filter(id__in=oldest_ids).delete()

    @staticmethod
    def expire_old_decisions(hours=24):
        """Auto-expire decisions older than the context window."""
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        DecisionRecord.objects.filter(
            timestamp__lt=cutoff,
            lifecycle_state='ACTIVE',
        ).update(
            lifecycle_state='EXPIRED',
            resolved_at=timezone.now(),
        )

    @staticmethod
    def supersede_decision(entity_type, entity_id, new_decision_id):
        """Supersede all active decisions for the same entity+rule."""
        DecisionRecord.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id,
            lifecycle_state='ACTIVE',
        ).exclude(
            id=new_decision_id,
        ).update(
            lifecycle_state='SUPERSEDED',
            resolved_at=timezone.now(),
        )

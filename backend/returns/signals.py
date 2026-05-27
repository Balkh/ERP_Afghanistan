"""
Signals for Returns Management Module.
Auto-completes return orders after all approval processing is done.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from returns.models import ReturnOrder
from core.transition_provenance import record_transition

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReturnOrder)
def auto_complete_return_order(sender, instance, created, **kwargs):
    """
    After a ReturnOrder is saved with status=APPROVED, transition it to COMPLETED.

    The approve() method performs all heavy lifting (inventory restore, accounting
    entries, reconciliation creation, refund execution). The APPROVED status is an
    intermediate step — once the save completes, all post-approval processing has
    already succeeded (or logged warnings for non-blocking failures like refund
    errors). This signal completes the lifecycle by advancing to COMPLETED.

    PROVENANCE: This auto-transition is recorded with source='signal' and
    reason='auto_complete' so that all downstream consumers have visibility
    into why the state changed.
    """
    if created:
        return

    if instance.status == 'APPROVED' and instance.approved_by:
        logger.info(
            "Auto-completing return %s after successful approval",
            instance.return_number,
        )
        record_transition(
            model_name='ReturnOrder',
            instance_id=str(instance.pk),
            from_status='APPROVED',
            to_status='COMPLETED',
            source='signal',
            reason=f'auto_complete after approval by {instance.approved_by}',
            condition='status == APPROVED && approved_by is not None',
        )
        ReturnOrder.objects.filter(pk=instance.pk).update(status='COMPLETED')

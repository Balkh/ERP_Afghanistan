"""
Signals for Returns Management Module.
Auto-completes return orders after all approval processing is done.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from returns.models import ReturnOrder

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

    Uses update() to avoid recursive signal firing.
    """
    if created:
        return

    if instance.status == 'APPROVED' and instance.approved_by:
        logger.info(
            "Auto-completing return %s after successful approval",
            instance.return_number,
        )
        ReturnOrder.objects.filter(pk=instance.pk).update(status='COMPLETED')

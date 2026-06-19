"""
Warehouse Transfer models for multi-warehouse inventory transfers.
"""
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from .models import TimeStampedUUIDModel, Warehouse, Product, Batch


class WarehouseTransfer(TimeStampedUUIDModel):
    """
    Model for tracking warehouse-to-warehouse transfers.
    """
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('IN_TRANSIT', _('In Transit')),
        ('COMPLETED', _('Completed')),
        ('CANCELLED', _('Cancelled')),
    ]

    transfer_number = models.CharField(max_length=50, unique=True, verbose_name=_('Transfer Number'))
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
        verbose_name=_('Source Warehouse')
    )
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
        verbose_name=_('Destination Warehouse')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name=_('Status')
    )
    transfer_date = models.DateField(verbose_name=_('Transfer Date'))
    expected_arrival_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Expected Arrival Date')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_transfers',
        verbose_name=_('Created By')
    )

    class Meta:
        verbose_name = _('Warehouse Transfer')
        verbose_name_plural = _('Warehouse Transfers')
        ordering = ['-transfer_date', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['transfer_date']),
            models.Index(fields=['source_warehouse', 'destination_warehouse']),
        ]

    def __str__(self):
        return f"{self.transfer_number} - {self.source_warehouse.name} → {self.destination_warehouse.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.source_warehouse_id and self.destination_warehouse_id:
            if self.source_warehouse_id == self.destination_warehouse_id:
                raise ValidationError(_('Source and destination warehouses must be different.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class WarehouseTransferItem(TimeStampedUUIDModel):
    """
    Individual items in a warehouse transfer.
    """
    transfer = models.ForeignKey(
        WarehouseTransfer,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Transfer')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name=_('Product')
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Batch (Optional)')
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Quantity')
    )
    quantity_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Quantity Received')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Transfer Item')
        verbose_name_plural = _('Transfer Items')
        unique_together = ['transfer', 'product', 'batch']
        ordering = ['transfer', 'product__name']

    def __str__(self):
        batch_info = f" (Batch: {self.batch.batch_number})" if self.batch else ""
        return f"{self.transfer.transfer_number} - {self.product.name}{batch_info}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity <= 0:
            raise ValidationError(_('Quantity must be positive.'))
        if self.quantity_received < 0:
            raise ValidationError(_('Quantity received cannot be negative.'))
        if self.quantity_received > self.quantity:
            raise ValidationError(_('Quantity received cannot exceed quantity transferred.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

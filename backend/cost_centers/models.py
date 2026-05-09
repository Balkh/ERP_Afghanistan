import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from accounting.models import Account


class CostCenter(TimeStampedUUIDModel):
    """
    Cost centers for tracking expenses by department/project/branch.
    Links to existing HR Department or can be standalone.
    """
    TYPE_CHOICES = [
        ('DEPARTMENT', _('Department')),
        ('PROJECT', _('Project')),
        ('BRANCH', _('Branch')),
        ('STORE', _('Store')),
        ('OTHER', _('Other')),
    ]

    name = models.CharField(max_length=255, verbose_name=_('Cost Center Name'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('Code'))
    cost_center_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='DEPARTMENT',
        verbose_name=_('Type')
    )
    department = models.ForeignKey(
        'hr.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cost_centers',
        verbose_name=_('Linked Department')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Cost Center')
    )
    default_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cost_centers',
        verbose_name=_('Default Expense Account')
    )
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Annual Budget')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    manager = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Manager')
    )

    class Meta:
        verbose_name = _('Cost Center')
        verbose_name_plural = _('Cost Centers')
        ordering = ['code']
        indexes = [
            models.Index(fields=['cost_center_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        if self.parent and self.parent.id == self.id:
            raise ValidationError(_('Cost center cannot be its own parent.'))


class CostAllocation(TimeStampedUUIDModel):
    """
    Allocation rules for distributing costs across cost centers.
    """
    ALLOCATION_METHOD_CHOICES = [
        ('PERCENTAGE', _('Percentage')),
        ('EQUAL', _('Equal Split')),
        ('UNITS', _('By Units')),
        ('REVENUE', _('By Revenue')),
    ]

    name = models.CharField(max_length=255, verbose_name=_('Allocation Name'))
    source_cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name='allocations_from',
        verbose_name=_('Source Cost Center')
    )
    allocation_method = models.CharField(
        max_length=20,
        choices=ALLOCATION_METHOD_CHOICES,
        default='PERCENTAGE',
        verbose_name=_('Allocation Method')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Cost Allocation')
        verbose_name_plural = _('Cost Allocations')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.source_cost_center.code}"


class CostAllocationLine(models.Model):
    """
    Lines for cost allocation rules.
    """
    allocation = models.ForeignKey(
        CostAllocation,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Allocation')
    )
    target_cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name='allocations_to',
        verbose_name=_('Target Cost Center')
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Percentage'),
        help_text=_('Percentage of cost to allocate')
    )

    class Meta:
        unique_together = ['allocation', 'target_cost_center']
        verbose_name = _('Allocation Line')
        verbose_name_plural = _('Allocation Lines')

    def __str__(self):
        return f"{self.allocation.name} -> {self.target_cost_center.code} ({self.percentage}%)"


class CostTransaction(TimeStampedUUIDModel):
    """
    Records cost transactions linked to journal entries.
    """
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Cost Center')
    )
    journal_entry_line = models.ForeignKey(
        'accounting.JournalEntryLine',
        on_delete=models.CASCADE,
        related_name='cost_transactions',
        verbose_name=_('Journal Entry Line')
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    transaction_date = models.DateField(verbose_name=_('Transaction Date'))
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Description')
    )

    class Meta:
        verbose_name = _('Cost Transaction')
        verbose_name_plural = _('Cost Transactions')
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['cost_center', 'transaction_date']),
        ]

    def __str__(self):
        return f"{self.cost_center.code} - {self.amount}"
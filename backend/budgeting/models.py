import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from accounting.models import Account


class Budget(TimeStampedUUIDModel):
    """
    Model representing a budget for a period.
    """
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('APPROVED', _('Approved')),
        ('CLOSED', _('Closed')),
    ]

    name = models.CharField(max_length=255, verbose_name=_('Budget Name'))
    fiscal_year = models.PositiveIntegerField(
        verbose_name=_('Fiscal Year'),
        help_text=_('Budget fiscal year (e.g., 2025)')
    )
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('MONTHLY', _('Monthly')),
            ('QUARTERLY', _('Quarterly')),
            ('ANNUAL', _('Annual')),
        ],
        default='ANNUAL',
        verbose_name=_('Period Type')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name=_('Status')
    )
    total_budgeted = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Budgeted')
    )
    total_actual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Actual')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    approved_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Approved By')
    )
    approved_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Approved Date')
    )

    class Meta:
        verbose_name = _('Budget')
        verbose_name_plural = _('Budgets')
        ordering = ['-fiscal_year', '-created_at']
        unique_together = ['name', 'fiscal_year']
        indexes = [
            models.Index(fields=['fiscal_year']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.fiscal_year})"

    def clean(self):
        if self.fiscal_year and self.fiscal_year < 2000:
            raise ValidationError(_('Invalid fiscal year.'))
        if self.total_budgeted < 0:
            raise ValidationError(_('Total budget cannot be negative.'))

    @property
    def variance(self):
        return self.total_budgeted - self.total_actual

    @property
    def variance_percentage(self):
        if self.total_budgeted == 0:
            return Decimal('0.00')
        return (self.variance / self.total_budgeted) * 100


class BudgetLine(TimeStampedUUIDModel):
    """
    Model representing a budget line for a specific account.
    """
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Budget')
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='budget_lines',
        verbose_name=_('Account')
    )
    period = models.CharField(
        max_length=20,
        verbose_name=_('Period'),
        help_text=_('Period code (e.g., 2025-01, 2025-Q1, or ANNUAL)')
    )
    budgeted_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Budgeted Amount')
    )
    actual_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Actual Amount')
    )

    class Meta:
        verbose_name = _('Budget Line')
        verbose_name_plural = _('Budget Lines')
        ordering = ['period', 'account__code']
        unique_together = ['budget', 'account', 'period']
        indexes = [
            models.Index(fields=['budget', 'period']),
            models.Index(fields=['account', 'period']),
        ]

    def __str__(self):
        return f"{self.budget.name} - {self.account.code} - {self.period}"

    @property
    def variance(self):
        return self.budgeted_amount - self.actual_amount

    @property
    def variance_percentage(self):
        if self.budgeted_amount == 0:
            return Decimal('0.00')
        return (self.variance / self.budgeted_amount) * 100
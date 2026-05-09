import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from accounting.models import Account, Currency


class Entity(TimeStampedUUIDModel):
    """
    Represents a business entity (branch, pharmacy, warehouse).
    Can have separate chart of accounts.
    """
    ENTITY_TYPE_CHOICES = [
        ('HEADQUARTER', _('Headquarters')),
        ('PHARMACY', _('Pharmacy')),
        ('WAREHOUSE', _('Warehouse')),
        ('DISTRIBUTION_CENTER', _('Distribution Center')),
        ('OFFICE', _('Office')),
    ]

    name = models.CharField(max_length=255, verbose_name=_('Entity Name'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('Entity Code'))
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        default='PHARMACY',
        verbose_name=_('Entity Type')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_default = models.BooleanField(default=False, verbose_name=_('Is Default Entity'))
    address = models.TextField(blank=True, verbose_name=_('Address'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Phone'))
    email = models.EmailField(blank=True, verbose_name=_('Email'))
    base_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='entities',
        verbose_name=_('Base Currency')
    )
    tax_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tax Number')
    )
    license_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('License Number')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Business Entity')
        verbose_name_plural = _('Business Entities')
        ordering = ['code']
        indexes = [
            models.Index(fields=['entity_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        if self.is_default:
            existing = Entity.objects.filter(is_default=True).exclude(id=self.id)
            if existing.exists():
                raise ValidationError(_('Only one default entity allowed.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class EntityAccount(TimeStampedUUIDModel):
    """
    Maps entity-specific accounts to the main chart of accounts.
    Each entity can have its own cash/bank accounts.
    """
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='accounts',
        verbose_name=_('Entity')
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='entity_mappings',
        verbose_name=_('Account')
    )
    account_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Entity Account Name'),
        help_text=_('Custom name for this entity (e.g., Main Pharmacy Cash)')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Entity Account')
        verbose_name_plural = _('Entity Accounts')
        unique_together = ['entity', 'account']

    def __str__(self):
        return f"{self.entity.code} - {self.account.code}"


class InterCompanyTransaction(TimeStampedUUIDModel):
    """
    Tracks transactions between entities (inter-company).
    """
    TRANSACTION_TYPE_CHOICES = [
        ('TRANSFER', _('Stock Transfer')),
        ('LOAN', _('Loan/Advance')),
        ('EXPENSE', _('Expense Reimbursement')),
        ('SERVICE', _('Service Fee')),
    ]

    from_entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='transactions_sent',
        verbose_name=_('From Entity')
    )
    to_entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='transactions_received',
        verbose_name=_('To Entity')
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name=_('Transaction Type')
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        verbose_name=_('Currency')
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number')
    )
    transaction_date = models.DateField(verbose_name=_('Transaction Date'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_reconciled = models.BooleanField(default=False, verbose_name=_('Is Reconciled'))

    class Meta:
        verbose_name = _('Inter-Company Transaction')
        verbose_name_plural = _('Inter-Company Transactions')
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['from_entity', 'to_entity']),
            models.Index(fields=['transaction_date']),
        ]

    def __str__(self):
        return f"{self.from_entity.code} -> {self.to_entity.code}: {self.amount}"
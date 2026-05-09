import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from accounting.models import Account


class TaxCategory(TimeStampedUUIDModel):
    """
    Categories for tax treatment (e.g., Essential Medicines, Regular Goods).
    """
    name = models.CharField(max_length=100, verbose_name=_('Category Name'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('Category Code'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    default_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Default Tax Rate (%)')
    )
    is_exempt = models.BooleanField(
        default=False,
        verbose_name=_('Is Exempt'),
        help_text=_('Category is exempt from tax')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Tax Category')
        verbose_name_plural = _('Tax Categories')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class TaxRate(TimeStampedUUIDModel):
    """
    Configurable tax rates with effective date ranges.
    """
    TAX_TYPE_CHOICES = [
        ('STANDARD', _('Standard')),
        ('REDUCED', _('Reduced')),
        ('EXEMPT', _('Exempt')),
        ('ZERO', _('Zero Rated')),
    ]

    name = models.CharField(max_length=100, verbose_name=_('Rate Name'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('Rate Code'))
    rate_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_('Rate Percentage')
    )
    tax_type = models.CharField(
        max_length=20,
        choices=TAX_TYPE_CHOICES,
        default='STANDARD',
        verbose_name=_('Tax Type')
    )
    effective_from = models.DateField(verbose_name=_('Effective From'))
    effective_to = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Effective To')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Tax Rate')
        verbose_name_plural = _('Tax Rates')
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.code} - {self.rate_percentage}%"

    def clean(self):
        if self.rate_percentage < 0:
            raise ValidationError(_('Rate percentage cannot be negative.'))
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError(_('Effective to date must be after effective from date.'))


class TaxJurisdiction(TimeStampedUUIDModel):
    """
    Tax jurisdictions (national, provincial for Afghanistan context).
    """
    name = models.CharField(max_length=100, verbose_name=_('Jurisdiction Name'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('Code'))
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.PROTECT,
        related_name='jurisdictions',
        verbose_name=_('Default Tax Rate')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Tax Jurisdiction')
        verbose_name_plural = _('Tax Jurisdictions')
        ordering = ['name']

    def __str__(self):
        return self.name


class TaxReturn(TimeStampedUUIDModel):
    """
    Tax filing periods and tracking.
    """
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('FILED', _('Filed')),
        ('PAID', _('Paid')),
        ('ADJUSTED', _('Adjusted')),
    ]

    period_start = models.DateField(verbose_name=_('Period Start'))
    period_end = models.DateField(verbose_name=_('Period End'))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name=_('Status')
    )
    gross_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Gross Sales')
    )
    exempt_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Exempt Sales')
    )
    taxable_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Taxable Sales')
    )
    output_tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Output Tax')
    )
    input_tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Input Tax')
    )
    net_tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Net Tax Payable')
    )
    filing_date = models.DateField(null=True, blank=True, verbose_name=_('Filing Date'))
    payment_date = models.DateField(null=True, blank=True, verbose_name=_('Payment Date'))
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Tax Return')
        verbose_name_plural = _('Tax Returns')
        ordering = ['-period_end']
        indexes = [
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Tax Return {self.period_start} - {self.period_end}"

    @property
    def period_display(self):
        return f"{self.period_start} to {self.period_end}"

    def calculate_net_tax(self):
        self.net_tax = self.output_tax - self.input_tax
        return self.net_tax


class TaxTransaction(TimeStampedUUIDModel):
    """
    Links tax transactions to journal entries for reporting.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('SALE', _('Sale')),
        ('PURCHASE', _('Purchase')),
        ('ADJUSTMENT', _('Adjustment')),
    ]

    tax_return = models.ForeignKey(
        TaxReturn,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Tax Return'),
        null=True,
        blank=True
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name=_('Transaction Type')
    )
    reference_id = models.UUIDField(verbose_name=_('Reference ID'))
    base_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Base Amount')
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Tax Amount')
    )
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.PROTECT,
        verbose_name=_('Tax Rate')
    )
    transaction_date = models.DateField(verbose_name=_('Transaction Date'))
    is_reversed = models.BooleanField(default=False, verbose_name=_('Is Reversed'))

    class Meta:
        verbose_name = _('Tax Transaction')
        verbose_name_plural = _('Tax Transactions')
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['transaction_type', 'transaction_date']),
            models.Index(fields=['tax_return']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.base_amount} + {self.tax_amount}"
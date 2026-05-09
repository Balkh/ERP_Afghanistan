import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel


DEPRECIATION_METHOD_CHOICES = [
    ('STRAIGHT_LINE', _('Straight Line')),
    ('DECLINING_BALANCE', _('Declining Balance')),
]


class AssetCategory(TimeStampedUUIDModel):
    """
    Model representing categories for fixed assets.
    """
    name = models.CharField(max_length=100, verbose_name=_('Category Name'))
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Category Code'),
        help_text=_('Unique code for the category (e.g., COMP, FURN, VEHI)')
    )
    description = models.TextField(blank=True, verbose_name=_('Description'))
    default_useful_life_months = models.PositiveIntegerField(
        default=60,
        verbose_name=_('Default Useful Life (Months)'),
        help_text=_('Default useful life in months for assets in this category')
    )
    default_depreciation_method = models.CharField(
        max_length=20,
        choices=DEPRECIATION_METHOD_CHOICES,
        default='STRAIGHT_LINE',
        verbose_name=_('Default Depreciation Method')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Asset Category')
        verbose_name_plural = _('Asset Categories')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class FixedAsset(TimeStampedUUIDModel):
    """
    Model representing a fixed asset in the enterprise ERP system.
    """
    DEPRECIATION_METHOD_CHOICES = DEPRECIATION_METHOD_CHOICES

    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('ACTIVE', _('Active')),
        ('FULLY_DEPRECIATED', _('Fully Depreciated')),
        ('DISPOSED', _('Disposed')),
    ]

    asset_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Asset Code'),
        help_text=_('Unique identifier for the asset')
    )
    asset_name = models.CharField(max_length=255, verbose_name=_('Asset Name'))
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name='assets',
        verbose_name=_('Category')
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Serial Number'),
        help_text=_('Manufacturer serial number')
    )
    purchase_date = models.DateField(verbose_name=_('Purchase Date'))
    purchase_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Purchase Cost'),
        help_text=_('Original purchase cost including any additional costs')
    )
    salvage_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Salvage Value'),
        help_text=_('Estimated value at the end of useful life')
    )
    useful_life_months = models.PositiveIntegerField(
        verbose_name=_('Useful Life (Months)'),
        help_text=_('Total useful life in months')
    )
    depreciation_method = models.CharField(
        max_length=20,
        choices=DEPRECIATION_METHOD_CHOICES,
        default='STRAIGHT_LINE',
        verbose_name=_('Depreciation Method')
    )
    current_book_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Current Book Value'),
        help_text=_('Current book value after depreciation')
    )
    accumulated_depreciation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Accumulated Depreciation'),
        help_text=_('Total depreciation taken to date')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name=_('Status')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Location'),
        help_text=_('Physical location of the asset')
    )
    responsible_person = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Responsible Person'),
        help_text=_('Person responsible for the asset')
    )
    depreciation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Depreciation Rate (%)'),
        help_text=_('Custom depreciation rate for declining balance method')
    )

    class Meta:
        verbose_name = _('Fixed Asset')
        verbose_name_plural = _('Fixed Assets')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_code']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['purchase_date']),
        ]

    def __str__(self):
        return f"{self.asset_code} - {self.asset_name}"

    def clean(self):
        """Validate fixed asset data."""
        if self.purchase_cost and self.purchase_cost <= 0:
            raise ValidationError(_('Purchase cost must be positive.'))
        if self.salvage_value and self.salvage_value < 0:
            raise ValidationError(_('Salvage value cannot be negative.'))
        if self.salvage_value and self.purchase_cost and self.salvage_value >= self.purchase_cost:
            raise ValidationError(_('Salvage value must be less than purchase cost.'))
        if self.useful_life_months and self.useful_life_months <= 0:
            raise ValidationError(_('Useful life must be positive.'))

    def save(self, *args, **kwargs):
        """Override save to calculate initial book value."""
        self.full_clean()
        if self.status in ['DRAFT', 'ACTIVE'] and not self.current_book_value:
            self.current_book_value = self.purchase_cost
        super().save(*args, **kwargs)

    @property
    def depreciable_amount(self):
        """Calculate the depreciable amount (purchase cost - salvage value)."""
        return self.purchase_cost - self.salvage_value

    @property
    def monthly_depreciation(self):
        """Calculate monthly depreciation amount."""
        if self.useful_life_months and self.useful_life_months > 0:
            return self.depreciable_amount / self.useful_life_months
        return Decimal('0.00')

    @property
    def is_fully_depreciated(self):
        """Check if asset is fully depreciated."""
        return self.accumulated_depreciation >= self.depreciable_amount


class AssetDepreciation(TimeStampedUUIDModel):
    """
    Model representing depreciation entries for fixed assets.
    """
    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name='depreciations',
        verbose_name=_('Fixed Asset')
    )
    period_start = models.DateField(verbose_name=_('Period Start'))
    period_end = models.DateField(verbose_name=_('Period End'))
    depreciation_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Depreciation Amount')
    )
    book_value_start = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Book Value at Start of Period')
    )
    book_value_end = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Book Value at End of Period')
    )
    is_posted = models.BooleanField(
        default=False,
        verbose_name=_('Is Posted'),
        help_text=_('Posted depreciation is included in financial statements')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Asset Depreciation')
        verbose_name_plural = _('Asset Depreciations')
        ordering = ['-period_end']
        indexes = [
            models.Index(fields=['asset']),
            models.Index(fields=['period_start']),
            models.Index(fields=['period_end']),
            models.Index(fields=['is_posted']),
        ]

    def __str__(self):
        return f"{self.asset.asset_code} - {self.period_end}: {self.depreciation_amount}"

    def clean(self):
        """Validate depreciation data."""
        if self.depreciation_amount and self.depreciation_amount <= 0:
            raise ValidationError(_('Depreciation amount must be positive.'))


class AssetDisposal(TimeStampedUUIDModel):
    """
    Model representing disposal of fixed assets.
    """
    DISPOSAL_METHOD_CHOICES = [
        ('SOLD', _('Sold')),
        ('SCRAPPED', _('Scrapped')),
        ('DONATED', _('Donated')),
        ('EXCHANGED', _('Exchanged')),
        ('LOST', _('Lost/Stolen')),
    ]

    asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        related_name='disposals',
        verbose_name=_('Fixed Asset')
    )
    disposal_date = models.DateField(verbose_name=_('Disposal Date'))
    disposal_method = models.CharField(
        max_length=20,
        choices=DISPOSAL_METHOD_CHOICES,
        verbose_name=_('Disposal Method')
    )
    proceeds = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Proceeds'),
        help_text=_('Amount received from disposal (0 if scrapped/donated)')
    )
    disposal_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Disposal Cost'),
        help_text=_('Cost incurred for disposal')
    )
    gain_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Gain/Loss'),
        help_text=_('Calculated gain or loss on disposal')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    buyer_info = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Buyer Information'),
        help_text=_('Name/contact of buyer if sold')
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number'),
        help_text=_('Disposal reference document number')
    )
    is_posted = models.BooleanField(
        default=False,
        verbose_name=_('Is Posted'),
        help_text=_('Posted disposal is reflected in financial statements')
    )

    class Meta:
        verbose_name = _('Asset Disposal')
        verbose_name_plural = _('Asset Disposals')
        ordering = ['-disposal_date']
        indexes = [
            models.Index(fields=['asset']),
            models.Index(fields=['disposal_date']),
            models.Index(fields=['is_posted']),
        ]

    def __str__(self):
        return f"{self.asset.asset_code} - {self.disposal_date}"

    def save(self, *args, **kwargs):
        """Calculate gain/loss on disposal."""
        self.full_clean()
        if self.asset:
            book_value = self.asset.current_book_value
            self.gain_loss = self.proceeds - book_value - self.disposal_cost
        super().save(*args, **kwargs)
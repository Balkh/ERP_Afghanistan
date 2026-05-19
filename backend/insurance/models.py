"""Insurance Module for Pharmacy ERP — claim tracking, reimbursement, approval lifecycle."""
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel


class InsuranceProvider(TimeStampedUUIDModel):
    """Insurance provider/company (e.g., Afghan Insurance Co, Takaful)."""
    name = models.CharField(max_length=200, verbose_name=_('Provider Name'))
    code = models.CharField(max_length=50, unique=True, verbose_name=_('Provider Code'))
    contact_phone = models.CharField(max_length=50, blank=True, verbose_name=_('Contact Phone'))
    contact_email = models.EmailField(blank=True, verbose_name=_('Contact Email'))
    address = models.TextField(blank=True, verbose_name=_('Address'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Insurance Provider')
        verbose_name_plural = _('Insurance Providers')
        ordering = ['name']

    def __str__(self):
        return self.name


class InsurancePolicy(TimeStampedUUIDModel):
    """Customer/patient insurance policy linked to a provider."""
    POLICY_TYPE_CHOICES = [
        ('HEALTH', _('Health Insurance')),
        ('PHARMACY', _('Pharmacy Insurance')),
        ('MEDICARE', _('Medicare')),
        ('PRIVATE', _('Private Insurance')),
        ('GOVERNMENT', _('Government Scheme')),
        ('OTHER', _('Other')),
    ]
    COVERAGE_CHOICES = [
        ('FULL', _('Full Coverage')),
        ('PARTIAL', _('Partial Coverage')),
        ('LIMITED', _('Limited Coverage')),
    ]

    policy_number = models.CharField(max_length=100, unique=True, verbose_name=_('Policy Number'))
    provider = models.ForeignKey(
        InsuranceProvider, on_delete=models.PROTECT,
        related_name='policies', verbose_name=_('Insurance Provider')
    )
    customer = models.ForeignKey(
        'sales.Customer', on_delete=models.PROTECT,
        related_name='insurance_policies', verbose_name=_('Customer/Patient')
    )
    policy_type = models.CharField(
        max_length=20, choices=POLICY_TYPE_CHOICES,
        default='PHARMACY', verbose_name=_('Policy Type')
    )
    coverage_type = models.CharField(
        max_length=20, choices=COVERAGE_CHOICES,
        default='PARTIAL', verbose_name=_('Coverage Type')
    )
    coverage_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('80.00'),
        verbose_name=_('Coverage Percentage (%)'),
        help_text=_('Percentage of eligible costs covered by insurance')
    )
    annual_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Annual Limit'),
        help_text=_('Maximum annual coverage amount. 0 = unlimited')
    )
    used_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Used Amount'),
        help_text=_('Amount already claimed this period')
    )
    deductible = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Deductible'),
        help_text=_('Amount patient must pay before coverage kicks in')
    )
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Insurance Policy')
        verbose_name_plural = _('Insurance Policies')
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['policy_number']),
            models.Index(fields=['customer', 'is_active']),
        ]

    def __str__(self):
        return f"{self.policy_number} - {self.customer} ({self.provider})"

    @property
    def remaining_limit(self):
        if self.annual_limit == Decimal('0.00'):
            return Decimal('Infinity')
        return max(Decimal('0.00'), self.annual_limit - self.used_amount)

    @property
    def is_expired(self):
        from django.utils.timezone import now
        from datetime import date
        return (self.end_date or date(1900, 1, 1)) < date.today()

    def clean(self):
        if self.coverage_percentage < 0 or self.coverage_percentage > 100:
            raise ValidationError(_('Coverage percentage must be between 0 and 100.'))
        if self.annual_limit < 0:
            raise ValidationError(_('Annual limit cannot be negative.'))
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError(_('Start date must be before end date.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Claim(TimeStampedUUIDModel):
    """Insurance claim linked to a sale invoice and patient policy."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('SUBMITTED', _('Submitted')),
        ('IN_REVIEW', _('In Review')),
        ('PARTIALLY_APPROVED', _('Partially Approved')),
        ('APPROVED', _('Approved')),
        ('REJECTED', _('Rejected')),
        ('PAID', _('Paid')),
        ('VOIDED', _('Voided')),
    ]

    claim_number = models.CharField(
        max_length=50, unique=True, verbose_name=_('Claim Number')
    )
    policy = models.ForeignKey(
        InsurancePolicy, on_delete=models.PROTECT,
        related_name='claims', verbose_name=_('Insurance Policy')
    )
    invoice = models.ForeignKey(
        'sales.SalesInvoice', on_delete=models.PROTECT,
        related_name='insurance_claims', verbose_name=_('Sales Invoice'),
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='DRAFT', verbose_name=_('Status')
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Total Amount'),
        help_text=_('Total invoice amount (before insurance)')
    )
    covered_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Covered Amount'),
        help_text=_('Amount insurance will cover')
    )
    patient_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Patient Amount'),
        help_text=_('Amount patient must pay')
    )
    deductible_applied = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Deductible Applied')
    )
    rejection_reason = models.TextField(blank=True, verbose_name=_('Rejection Reason'))
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Submitted At'))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Approved At'))
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Paid At'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_('Created By')
    )
    # Accounting integration
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='insurance_claims',
        verbose_name=_('Journal Entry')
    )

    class Meta:
        verbose_name = _('Insurance Claim')
        verbose_name_plural = _('Insurance Claims')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['claim_number']),
            models.Index(fields=['policy', 'status']),
            models.Index(fields=['invoice']),
        ]

    def __str__(self):
        return f"Claim {self.claim_number} - {self.policy}"

    def clean(self):
        if self.total_amount < 0 or self.covered_amount < 0:
            raise ValidationError(_('Amounts cannot be negative.'))
        if self.covered_amount > self.total_amount:
            raise ValidationError(_('Covered amount cannot exceed total amount.'))

    def save(self, *args, **kwargs):
        if not self.claim_number:
            self.claim_number = self._generate_claim_number()
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_claim_number():
        import uuid
        return f"CLM-{uuid.uuid4().hex[:8].upper()}"


class ClaimItem(TimeStampedUUIDModel):
    """Individual line item within an insurance claim."""
    claim = models.ForeignKey(
        Claim, on_delete=models.CASCADE,
        related_name='items', verbose_name=_('Claim')
    )
    invoice_item = models.ForeignKey(
        'sales.SalesItem', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='insurance_claim_items',
        verbose_name=_('Invoice Item')
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT,
        verbose_name=_('Product')
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_('Quantity')
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_('Unit Price')
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_('Total Price')
    )
    covered_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Covered Amount')
    )
    patient_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_('Patient Amount')
    )
    is_approved = models.BooleanField(default=True, verbose_name=_('Is Approved'))
    rejection_note = models.TextField(blank=True, verbose_name=_('Rejection Note'))

    class Meta:
        verbose_name = _('Claim Item')
        verbose_name_plural = _('Claim Items')

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class ClaimApproval(TimeStampedUUIDModel):
    """Audit trail for claim approval/rejection actions."""
    claim = models.ForeignKey(
        Claim, on_delete=models.CASCADE,
        related_name='approvals', verbose_name=_('Claim')
    )
    action = models.CharField(
        max_length=20, choices=[
            ('SUBMIT', _('Submitted')),
            ('APPROVE', _('Approved')),
            ('PARTIAL_APPROVE', _('Partially Approved')),
            ('REJECT', _('Rejected')),
            ('PAY', _('Paid')),
            ('VOID', _('Voided')),
        ],
        verbose_name=_('Action')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    performed_by = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_('Performed By')
    )

    class Meta:
        verbose_name = _('Claim Approval')
        verbose_name_plural = _('Claim Approvals')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - {self.claim.claim_number}"

import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from core.multitenant.models import CompanyScopedMixin, CompanyScopedManager


class Supplier(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Model representing a supplier/vendor for pharmaceutical products.
    Enhanced with extended fields for supply chain management.
    """
    objects = CompanyScopedManager()
    SUBTYPE_CHOICES = [
        ('INDIVIDUAL', _('Individual')),
        ('COMPANY', _('Company')),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', _('Active')),
        ('INACTIVE', _('Inactive')),
        ('BLOCKED', _('Blocked')),
    ]

    # Core fields
    name = models.CharField(max_length=255, verbose_name=_('Supplier Name'))
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Supplier Code'),
        help_text=_('Unique identifier for the supplier')
    )
    
    # Subtype
    subtype = models.CharField(
        max_length=20,
        choices=SUBTYPE_CHOICES,
        default='COMPANY',
        verbose_name=_('Party Subtype')
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name=_('Status')
    )
    
    # Contact information
    email = models.EmailField(blank=True, verbose_name=_('Email'))
    phone = models.CharField(max_length=20, verbose_name=_('Phone'))
    address = models.TextField(blank=True, verbose_name=_('Address'))
    city = models.CharField(max_length=100, blank=True, verbose_name=_('City'))
    country = models.CharField(max_length=100, blank=True, verbose_name=_('Country'))
    
    # Individual fields
    first_name = models.CharField(max_length=100, blank=True, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=100, blank=True, verbose_name=_('Last Name'))
    
    # Company fields
    company_name = models.CharField(max_length=255, blank=True, verbose_name=_('Company Name'))
    registration_number = models.CharField(max_length=50, blank=True, verbose_name=_('Registration Number'))
    tax_number = models.CharField(max_length=50, blank=True, verbose_name=_('Tax Number'))
    
    # Contact person (primary)
    contact_person = models.CharField(max_length=255, blank=True, verbose_name=_('Contact Person'))
    contact_role = models.CharField(max_length=100, blank=True, verbose_name=_('Contact Role'))
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name=_('Contact Phone'))
    contact_email = models.EmailField(blank=True, verbose_name=_('Contact Email'))
    
    # Supply category (multi-select stored as comma-separated)
    supply_categories = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Supply Categories'),
        help_text=_('Categories of products supplied (e.g., Medicines, Medical Devices, Cosmetics)')
    )
    
    # Bank and payment information
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_('Bank Name'))
    bank_account = models.CharField(max_length=50, blank=True, verbose_name=_('Bank Account Number'))
    iban = models.CharField(max_length=50, blank=True, verbose_name=_('IBAN'))
    swift_code = models.CharField(max_length=20, blank=True, verbose_name=_('SWIFT Code'))
    
    # Business terms
    delivery_terms = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Delivery Terms'),
        help_text=_('e.g., FOB, CIF, Ex-Works')
    )
    lead_time_days = models.IntegerField(default=0, verbose_name=_('Lead Time (Days)'))
    minimum_order_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Minimum Order Value')
    )
    
    # Quality and rating
    quality_rating = models.IntegerField(
        default=0,
        verbose_name=_('Quality Rating (0-5)'),
        help_text=_('Supplier quality rating from 0 to 5')
    )
    
    # Financial fields
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Credit Limit'),
        help_text=_('Maximum credit allowed for this supplier')
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Current Balance'),
        help_text=_('Current outstanding balance owed to this supplier')
    )
    payment_terms_days = models.IntegerField(default=0, verbose_name=_('Payment Terms (Days)'))
    risk_level = models.CharField(
        max_length=20,
        choices=[('LOW', _('Low')), ('MEDIUM', _('Medium')), ('HIGH', _('High'))],
        default='LOW',
        verbose_name=_('Risk Level')
    )
    
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Supplier')
        verbose_name_plural = _('Suppliers')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['subtype']),
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['quality_rating']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate supplier data."""
        if self.credit_limit < 0:
            raise ValidationError(_('Credit limit cannot be negative.'))
        if self.balance < 0:
            raise ValidationError(_('Balance cannot be negative.'))
        
        # Must have supply categories
        if not self.supply_categories:
            raise ValidationError(_('Supplier must have at least one supply category.'))
        
        # Individual requires first/last name
        if self.subtype == 'INDIVIDUAL':
            if not self.first_name or not self.last_name:
                raise ValidationError(_('Individual suppliers must have first and last name.'))
        
        # Company requires company name
        if self.subtype == 'COMPANY' and not self.company_name:
            raise ValidationError(_('Company suppliers must have a company name.')
)
    
    def save(self, *args, **kwargs):
        # Set name based on subtype
        if self.subtype == 'INDIVIDUAL' and self.first_name and self.last_name:
            self.name = f"{self.first_name} {self.last_name}"
        elif self.subtype == 'COMPANY' and self.company_name:
            self.name = self.company_name
        super().save(*args, **kwargs)

    @property
    def available_credit(self):
        """Calculate available credit for this supplier."""
        return max(Decimal('0.00'), self.credit_limit - self.balance)

    @property
    def is_over_credit_limit(self):
        """Check if supplier has exceeded their credit limit."""
        return self.balance > self.credit_limit
    
    @property
    def categories_list(self):
        """Get supply categories as list."""
        if self.supply_categories:
            return [c.strip() for c in self.supply_categories.split(',')]
        return []
    
    def get_financial_summary(self):
        """Get financial summary from accounting (read-only)."""
        return {
            'total_balance': self.balance,
            'credit_limit': self.credit_limit,
            'payment_terms_days': self.payment_terms_days,
            'risk_level': self.risk_level,
            'available_credit': self.available_credit,
        }


class PurchaseInvoice(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Model representing a purchase invoice from a supplier.
    """
    objects = CompanyScopedManager()
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('CONFIRMED', _('Confirmed')),
        ('RECEIVED', _('Received')),
        ('PARTIAL_PAID', _('Partial Paid')),
        ('PAID', _('Paid')),
        ('CANCELLED', _('Cancelled')),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('UNPAID', _('Unpaid')),
        ('PARTIAL', _('Partial')),
        ('PAID', _('Paid')),
    ]

    invoice_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Invoice Number'),
        help_text=_('Supplier invoice number')
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_invoices',
        verbose_name=_('Supplier')
    )
    order_date = models.DateField(verbose_name=_('Order Date'))
    invoice_date = models.DateField(verbose_name=_('Invoice Date'))
    due_date = models.DateField(verbose_name=_('Due Date'))
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Subtotal')
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount')
    )
    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax')
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Amount')
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Paid Amount')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name=_('Status')
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='UNPAID',
        verbose_name=_('Payment Status')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Created By')
    )

    # Tax configuration
    tax_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Tax Enabled'),
        help_text=_('Enable tax calculation for this invoice')
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax Rate (%)'),
        help_text=_('Tax rate percentage (e.g. 10.00 for 10%%)')
    )

    # Accounting integration
    journal_entry_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('Journal Entry ID'),
        help_text=_('Linked accounting journal entry')
    )

    class Meta:
        verbose_name = _('Purchase Invoice')
        verbose_name_plural = _('Purchase Invoices')
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['supplier', 'order_date']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.supplier.name}"

    def clean(self):
        """Validate invoice data."""
        if self.discount < 0:
            raise ValidationError(_('Discount cannot be negative.'))
        if self.tax < 0:
            raise ValidationError(_('Tax cannot be negative.'))
        if self.total_amount < 0:
            raise ValidationError(_('Total amount cannot be negative.'))
        if self.paid_amount < 0:
            raise ValidationError(_('Paid amount cannot be negative.'))
        if self.paid_amount > self.total_amount:
            raise ValidationError(_('Paid amount cannot exceed total amount.'))

    @property
    def remaining_balance(self):
        """Calculate remaining balance for this invoice."""
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)

    def calculate_totals(self):
        """Calculate subtotal, total from line items."""
        from core.tax.tax_engine import TaxEngine
        self.subtotal = sum(
            item.quantity * item.unit_price for item in self.items.all()
        )
        taxable = self.subtotal - self.discount
        if self.tax_enabled and self.tax_rate > Decimal('0'):
            self.tax = TaxEngine.calculate_tax(taxable, self.tax_rate)
        else:
            self.tax = Decimal('0.00')
        self.total_amount = taxable + self.tax

    def update_payment_status(self):
        """Update payment status based on paid amount."""
        if self.paid_amount <= 0:
            self.payment_status = 'UNPAID'
        elif self.paid_amount >= self.total_amount:
            self.payment_status = 'PAID'
        else:
            self.payment_status = 'PARTIAL'


class PurchaseItem(TimeStampedUUIDModel):
    """
    Model representing a line item in a purchase invoice.
    """
    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Purchase Invoice')
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='purchase_items',
        verbose_name=_('Product')
    )
    batch_number = models.CharField(max_length=100, verbose_name=_('Batch Number'))
    expiry_date = models.DateField(verbose_name=_('Expiry Date'))
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Quantity')
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Unit Price')
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount')
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax')
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Total')
    )
    received_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Received Quantity')
    )

    class Meta:
        verbose_name = _('Purchase Item')
        verbose_name_plural = _('Purchase Items')
        ordering = ['id']
        indexes = [
            models.Index(fields=['invoice']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.quantity} @ {self.unit_price}"

    def clean(self):
        """Validate item data."""
        if self.quantity <= 0:
            raise ValidationError(_('Quantity must be positive.'))
        if self.unit_price < 0:
            raise ValidationError(_('Unit price cannot be negative.'))
        if self.discount < 0:
            raise ValidationError(_('Discount cannot be negative.'))
        if self.tax < 0:
            raise ValidationError(_('Tax cannot be negative.'))
        if self.received_quantity < 0:
            raise ValidationError(_('Received quantity cannot be negative.'))
        if self.received_quantity > self.quantity:
            raise ValidationError(_('Received quantity cannot exceed ordered quantity.'))

    def calculate_total(self):
        """Calculate total for this line item."""
        self.total = (self.quantity * self.unit_price) - self.discount + self.tax


class SupplierPayment(TimeStampedUUIDModel):
    """
    Model representing a payment made to a supplier.
    """
    PAYMENT_METHOD_CHOICES = [
        ('CASH', _('Cash')),
        ('BANK_TRANSFER', _('Bank Transfer')),
        ('CHEQUE', _('Cheque')),
        ('CREDIT_CARD', _('Credit Card')),
        ('OTHER', _('Other')),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('Supplier')
    )
    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name=_('Purchase Invoice')
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    payment_date = models.DateField(verbose_name=_('Payment Date'))
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name=_('Payment Method')
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Supplier Payment')
        verbose_name_plural = _('Supplier Payments')
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['supplier', 'payment_date']),
            models.Index(fields=['invoice']),
        ]

    def __str__(self):
        return f"Payment {self.amount} to {self.supplier.name} on {self.payment_date}"

    def clean(self):
        """Validate payment data."""
        if self.amount <= 0:
            raise ValidationError(_('Payment amount must be positive.'))

    def save(self, *args, **kwargs):
        """Override save to update invoice and supplier balances, and create payment transaction.
        
        Balance is now synced via BalanceSyncService (no direct mutation).
        This eliminates the dual-path balance update issue.

        CRITICAL: If payment transaction creation fails, the ENTIRE transaction rolls back.
        No SupplierPayment record is persisted without a complete accounting trail.
        """
        from core.balance_sync import BalanceSyncService
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.update_invoice_paid_amount()
            BalanceSyncService.sync_supplier(self.supplier, lock=True)
            self._create_payment_transaction()

    def _create_payment_transaction(self):
        """Create a financial transaction record for this payment.

        CRITICAL: If journal entry creation fails, the exception propagates
        and the entire transaction (including the SupplierPayment record) rolls back.
        No ghost payments allowed.
        """
        import logging
        logger = logging.getLogger('erp.purchases.payment')

        from payments.models import PaymentAccount
        from payments.services import PaymentEngine

        method_code_map = {
            'CASH': 'CASH',
            'BANK_TRANSFER': 'BANK',
            'CHEQUE': 'CHEQUE',
            'CREDIT_CARD': 'CC',
            'OTHER': 'OTHER',
        }
        method_code = method_code_map.get(self.payment_method, 'CASH')

        payment_account = PaymentAccount.objects.filter(
            is_active=True
        ).order_by('code').first()

        if not payment_account:
            raise ValidationError(
                f'No active payment account found for supplier payment {self.id}. '
                f'Cannot create financial transaction. '
                f'Invoice: {self.invoice.invoice_number if self.invoice else "N/A"}.'
            )

        result = PaymentEngine.process_payment(
            payment_method_code=method_code,
            source_account_code=payment_account.code,
            amount=self.amount,
            description=f'Payment to {self.supplier.name} for invoice {self.invoice.invoice_number if self.invoice else ""}',
            currency='AFN',
            party_type='SUPPLIER',
            party_id=str(self.supplier.id),
            party_name=self.supplier.name,
            invoice_type='PURCHASE',
            invoice_id=str(self.invoice.id) if self.invoice else None,
            reference_number=self.reference_number,
            performed_by='system',
        )

        if not result.get('success'):
            error_msg = result.get('errors', 'Unknown error')
            logger.error(
                f"[PURCHASES] PaymentEngine.process_payment failed for supplier payment {self.id}: "
                f"{error_msg}. "
                f"Invoice: {self.invoice.invoice_number if self.invoice else 'N/A'}, "
                f"Amount: {self.amount}"
            )
            raise ValidationError(
                f'Payment engine failed for supplier payment {self.id}: {error_msg}. '
                f'Transaction rolled back — no payment record created.'
            )

    def update_invoice_paid_amount(self):
        """Update the paid amount on the related invoice."""
        if self.invoice:
            total_paid = SupplierPayment.objects.filter(
                invoice=self.invoice,
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            self.invoice.paid_amount = total_paid
            self.invoice.update_payment_status()
            self.invoice.save(update_fields=['paid_amount', 'payment_status', 'updated_at'])


class SupplierPaymentAllocation(TimeStampedUUIDModel):
    """Tracks allocation of unallocated supplier payments to outstanding purchase invoices.

    Enables FIFO (First-In-First-Out) payment strategy for suppliers:
    oldest unpaid invoices are paid first.
    Mirrors the sales PaymentAllocation model for supplier parity.
    """
    payment = models.ForeignKey(
        SupplierPayment,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name=_('Supplier Payment'),
    )
    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.PROTECT,
        related_name='payment_allocations',
        verbose_name=_('Purchase Invoice'),
    )
    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Allocated Amount'),
    )
    allocated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Allocated At'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Supplier Payment Allocation')
        verbose_name_plural = _('Supplier Payment Allocations')
        ordering = ['-allocated_at']
        indexes = [
            models.Index(fields=['payment', 'invoice']),
        ]

    def __str__(self):
        return f'Allocation: {self.payment} -> {self.invoice} ({self.allocated_amount})'

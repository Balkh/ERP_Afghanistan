import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from core.multitenant.models import CompanyScopedMixin, CompanyScopedManager


class Customer(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Model representing a customer for pharmaceutical sales.
    Enhanced with Individual/Company subtype support.
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
    
    CUSTOMER_TYPE_CHOICES = [
        ('RETAIL', _('Retail')),
        ('WHOLESALE', _('Wholesale')),
        ('PHARMACY', _('Pharmacy')),
        ('HOSPITAL', _('Hospital')),
        ('CLINIC', _('Clinic')),
        ('DISTRIBUTOR', _('Distributor')),
        ('OTHER', _('Other')),
    ]

    # Core fields
    name = models.CharField(max_length=255, verbose_name=_('Customer Name'))
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Customer Code'),
        help_text=_('Unique identifier for the customer')
    )
    
    # Subtype: Individual or Company
    subtype = models.CharField(
        max_length=20,
        choices=SUBTYPE_CHOICES,
        default='INDIVIDUAL',
        verbose_name=_('Party Subtype')
    )
    
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default='RETAIL',
        verbose_name=_('Customer Category')
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
    
    # Individual-specific fields
    first_name = models.CharField(max_length=100, blank=True, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=100, blank=True, verbose_name=_('Last Name'))
    national_id = models.CharField(max_length=50, blank=True, verbose_name=_('National ID'))
    
    # Company-specific fields
    company_name = models.CharField(max_length=255, blank=True, verbose_name=_('Company Name'))
    registration_number = models.CharField(max_length=50, blank=True, verbose_name=_('Registration Number'))
    business_license = models.CharField(max_length=50, blank=True, verbose_name=_('Business License ( جواز فعالیت )'))
    license_expiry_date = models.DateField(null=True, blank=True, verbose_name=_('License Expiry Date'))
    tax_number = models.CharField(max_length=50, blank=True, verbose_name=_('Tax Number'))
    website = models.URLField(blank=True, verbose_name=_('Website'))
    
    # Contact person (for companies)
    contact_person = models.CharField(max_length=255, blank=True, verbose_name=_('Contact Person'))
    contact_role = models.CharField(max_length=100, blank=True, verbose_name=_('Contact Person Role'))
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name=_('Contact Phone'))
    contact_email = models.EmailField(blank=True, verbose_name=_('Contact Email'))
    
    # Financial fields
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Credit Limit'),
        help_text=_('Maximum credit allowed for this customer')
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Current Balance'),
        help_text=_('Current outstanding balance owed by this customer')
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
        verbose_name = _('Customer')
        verbose_name_plural = _('Customers')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['customer_type']),
            models.Index(fields=['subtype']),
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['risk_level']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate customer data based on subtype."""
        if self.credit_limit < 0:
            raise ValidationError(_('Credit limit cannot be negative.'))
        if self.balance < 0:
            raise ValidationError(_('Balance cannot be negative.'))
        
        # Individual requires first/last name
        if self.subtype == 'INDIVIDUAL':
            if not self.first_name or not self.last_name:
                raise ValidationError(_('Individual customers must have first and last name.'))
        
        # Company requires company name and business license
        if self.subtype == 'COMPANY':
            if not self.company_name:
                raise ValidationError(_('Company customers must have a company name.'))
            if not self.business_license:
                raise ValidationError(_('Company customers must have a business license (جواز فعالیت).'))

    def save(self, *args, **kwargs):
        # Set name based on subtype
        if self.subtype == 'INDIVIDUAL' and self.first_name and self.last_name:
            self.name = f"{self.first_name} {self.last_name}"
        elif self.subtype == 'COMPANY' and self.company_name:
            self.name = self.company_name
        super().save(*args, **kwargs)

    @property
    def available_credit(self):
        """Calculate available credit for this customer."""
        return max(Decimal('0.00'), self.credit_limit - self.balance)

    @property
    def is_over_credit_limit(self):
        """Check if customer has exceeded their credit limit."""
        return self.balance > self.credit_limit

    @property
    def total_debt(self):
        """Get total debt (same as balance for clarity in sales context)."""
        return self.balance
    
    @property
    def full_name(self):
        """Get full name based on subtype."""
        if self.subtype == 'INDIVIDUAL':
            return f"{self.first_name} {self.last_name}".strip()
        return self.company_name or self.name
    
    def get_financial_summary(self):
        """Get financial summary from accounting (read-only)."""
        # This would integrate with accounting module
        # Returns dict with total_balance, credit_limit, payment_terms_days, risk_level
        from accounting.services.financial_reports import FinancialReportsService
        try:
            # Get party-specific AR balance from accounting
            service = FinancialReportsService()
            # Implementation would be in accounting service
            return {
                'total_balance': self.balance,
                'credit_limit': self.credit_limit,
                'payment_terms_days': self.payment_terms_days,
                'risk_level': self.risk_level,
                'available_credit': self.available_credit,
            }
        except Exception as e:
            import logging
            logging.getLogger('sales').warning(f"Financial summary fallback for customer {self.id}: {e}")
            return {
                'total_balance': self.balance,
                'credit_limit': self.credit_limit,
                'payment_terms_days': self.payment_terms_days,
                'risk_level': self.risk_level,
                'available_credit': self.available_credit,
            }


class SalesInvoice(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Model representing a sales invoice to a customer.
    """
    objects = CompanyScopedManager()
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('CONFIRMED', _('Confirmed')),
        ('DISPATCHED', _('Dispatched')),
        ('PARTIAL_PAID', _('Partial Paid')),
        ('PAID', _('Paid')),
        ('CANCELLED', _('Cancelled')),
        ('CREDIT_PENDING', _('Credit Pending Approval')),
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
        help_text=_('Unique sales invoice number')
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='sales_invoices',
        verbose_name=_('Customer')
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

    # Accounting integration
    journal_entry_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('Journal Entry ID'),
        help_text=_('Linked accounting journal entry')
    )

    class Meta:
        verbose_name = _('Sales Invoice')
        verbose_name_plural = _('Sales Invoices')
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['customer', 'order_date']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer.name}"

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
        self.subtotal = sum(
            item.quantity * item.unit_price for item in self.items.all()
        )
        self.total_amount = self.subtotal - self.discount + self.tax

    def update_payment_status(self):
        """Update payment status based on paid amount."""
        if self.paid_amount <= 0:
            self.payment_status = 'UNPAID'
        elif self.paid_amount >= self.total_amount:
            self.payment_status = 'PAID'
        else:
            self.payment_status = 'PARTIAL'


class SalesItem(TimeStampedUUIDModel):
    """
    Model representing a line item in a sales invoice.
    """
    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Sales Invoice')
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='sales_items',
        verbose_name=_('Product')
    )
    batch = models.ForeignKey(
        'inventory.Batch',
        on_delete=models.PROTECT,
        related_name='sales_items',
        null=True,
        blank=True,
        verbose_name=_('Batch')
    )
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
    dispensed_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Dispensed Quantity')
    )

    class Meta:
        verbose_name = _('Sales Item')
        verbose_name_plural = _('Sales Items')
        ordering = ['id']
        indexes = [
            models.Index(fields=['invoice']),
            models.Index(fields=['product']),
            models.Index(fields=['batch']),
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
        if self.dispensed_quantity < 0:
            raise ValidationError(_('Dispensed quantity cannot be negative.'))
        if self.dispensed_quantity > self.quantity:
            raise ValidationError(_('Dispensed quantity cannot exceed ordered quantity.'))

    def calculate_total(self):
        """Calculate total for this line item."""
        self.total = (self.quantity * self.unit_price) - self.discount + self.tax


class CustomerPayment(TimeStampedUUIDModel):
    """
    Model representing a payment received from a customer.
    """
    PAYMENT_METHOD_CHOICES = [
        ('CASH', _('Cash')),
        ('BANK_TRANSFER', _('Bank Transfer')),
        ('CHEQUE', _('Cheque')),
        ('CREDIT_CARD', _('Credit Card')),
        ('INSURANCE', _('Insurance')),
        ('OTHER', _('Other')),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('Customer')
    )
    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name=_('Sales Invoice')
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
        verbose_name = _('Customer Payment')
        verbose_name_plural = _('Customer Payments')
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['customer', 'payment_date']),
            models.Index(fields=['invoice']),
        ]

    def __str__(self):
        return f"Payment {self.amount} from {self.customer.name} on {self.payment_date}"

    def clean(self):
        """Validate payment data."""
        if self.amount <= 0:
            raise ValidationError(_('Payment amount must be positive.'))

    def save(self, *args, **kwargs):
        """Override save to update invoice and customer balances, and create payment transaction.
        
        Balance is now synced via BalanceSyncService (no direct mutation).
        This eliminates the dual-path balance update issue.

        CRITICAL: If payment transaction creation fails, the ENTIRE transaction rolls back.
        No CustomerPayment record is persisted without a complete accounting trail.
        """
        from core.balance_sync import BalanceSyncService
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.update_invoice_paid_amount()
            BalanceSyncService.sync_customer(self.customer, lock=True)
            self._create_payment_transaction()

    def _create_payment_transaction(self):
        """Create a financial transaction record for this payment.

        CRITICAL: If journal entry creation fails, the exception propagates
        and the entire transaction (including the CustomerPayment record) rolls back.
        No ghost payments allowed.
        """
        import logging
        logger = logging.getLogger('erp.sales.payment')

        from payments.models import PaymentAccount
        from payments.services import PaymentEngine

        method_code_map = {
            'CASH': 'CASH',
            'BANK_TRANSFER': 'BANK',
            'CHEQUE': 'CHEQUE',
            'CREDIT_CARD': 'CC',
            'INSURANCE': 'INS',
            'OTHER': 'OTHER',
        }
        method_code = method_code_map.get(self.payment_method, 'CASH')

        payment_account = PaymentAccount.objects.filter(
            is_active=True
        ).order_by('code').first()

        if not payment_account:
            raise ValidationError(
                f'No active payment account found for customer payment {self.id}. '
                f'Cannot create financial transaction. '
                f'Invoice: {self.invoice.invoice_number if self.invoice else "N/A"}.'
            )

        result = PaymentEngine.process_receipt(
            payment_method_code=method_code,
            destination_account_code=payment_account.code,
            amount=self.amount,
            description=f'Payment from {self.customer.name} for invoice {self.invoice.invoice_number if self.invoice else ""}',
            currency='AFN',
            party_type='CUSTOMER',
            party_id=str(self.customer.id),
            party_name=self.customer.name,
            invoice_type='SALES',
            invoice_id=str(self.invoice.id) if self.invoice else None,
            reference_number=self.reference_number,
            performed_by='system',
        )

        if not result.get('success'):
            error_msg = result.get('errors', 'Unknown error')
            logger.error(
                f"[SALES] PaymentEngine.process_receipt failed for customer payment {self.id}: "
                f"{error_msg}. "
                f"Invoice: {self.invoice.invoice_number if self.invoice else 'N/A'}, "
                f"Amount: {self.amount}"
            )
            raise ValidationError(
                f'Payment engine failed for customer payment {self.id}: {error_msg}. '
                f'Transaction rolled back — no payment record created.'
            )

    def update_invoice_paid_amount(self):
        """Update the paid amount on the related invoice."""
        if self.invoice:
            total_paid = CustomerPayment.objects.filter(
                invoice=self.invoice,
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            self.invoice.paid_amount = total_paid
            self.invoice.update_payment_status()
            self.invoice.save(update_fields=['paid_amount', 'payment_status', 'updated_at'])

class PaymentAllocation(TimeStampedUUIDModel):
    """Tracks allocation of unallocated payments to outstanding invoices.

    Enables FIFO (First-In-First-Out) payment strategy:
    oldest unpaid invoices are paid first.
    """
    payment = models.ForeignKey(
        CustomerPayment,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name=_('Customer Payment'),
    )
    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.PROTECT,
        related_name='payment_allocations',
        verbose_name=_('Sales Invoice'),
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
        verbose_name = _('Payment Allocation')
        verbose_name_plural = _('Payment Allocations')
        ordering = ['-allocated_at']
        indexes = [
            models.Index(fields=['payment', 'invoice']),
        ]


class CreditApprovalRequest(TimeStampedUUIDModel):
    """Lightweight credit limit override request for manager approval."""

    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('APPROVED', _('Approved')),
        ('REJECTED', _('Rejected')),
    ]

    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name='credit_requests',
        verbose_name=_('Invoice'),
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='credit_requests',
        verbose_name=_('Customer'),
    )
    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Requested Amount'),
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Current Balance'),
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Credit Limit'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name=_('Status'),
    )
    requested_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_credit_approvals',
        verbose_name=_('Requested By'),
    )
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_credit_requests',
        verbose_name=_('Approved By'),
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Approved At'),
    )
    approval_reason = models.TextField(
        blank=True,
        verbose_name=_('Approval Reason'),
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_('Rejection Reason'),
    )

    class Meta:
        verbose_name = _('Credit Approval Request')
        verbose_name_plural = _('Credit Approval Requests')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f"Credit request for {self.customer.name} - {self.requested_amount} ({self.status})"

    def __str__(self):
        return f"{self.allocated_amount} from {self.payment} to {self.invoice.invoice_number}"

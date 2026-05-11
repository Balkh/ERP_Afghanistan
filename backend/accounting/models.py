import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from core.multitenant.models import CompanyScopedMixin, CompanyScopedManager


class Currency(TimeStampedUUIDModel):
    """
    Model representing a currency supported by the system.
    """
    code = models.CharField(
        max_length=3,
        unique=True,
        verbose_name=_('Currency Code'),
        help_text=_('ISO 4217 currency code (e.g., AFN, USD)')
    )
    name = models.CharField(max_length=50, verbose_name=_('Currency Name'))
    symbol = models.CharField(max_length=10, verbose_name=_('Symbol'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_default = models.BooleanField(default=False, verbose_name=_('Is Default Currency'))

    class Meta:
        verbose_name = _('Currency')
        verbose_name_plural = _('Currencies')
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} ({self.symbol})"

    def clean(self):
        """Ensure only one default currency."""
        if self.is_default:
            existing_default = Currency.objects.filter(is_default=True).exclude(id=self.id if self.id else None)
            if existing_default.exists():
                raise ValidationError(_('Only one currency can be set as default.'))


class ExchangeRate(TimeStampedUUIDModel):
    """
    Model representing exchange rates between currencies.
    Rates are stored as: 1 unit of from_currency = rate units of to_currency
    """
    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='from_exchange_rates',
        verbose_name=_('From Currency')
    )
    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='to_exchange_rates',
        verbose_name=_('To Currency')
    )
    rate = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        verbose_name=_('Exchange Rate'),
        help_text=_('1 unit of from_currency equals this many units of to_currency')
    )
    effective_date = models.DateField(verbose_name=_('Effective Date'))
    source = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Source'),
        help_text=_('Source of the exchange rate (e.g., Central Bank, Manual)')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Exchange Rate')
        verbose_name_plural = _('Exchange Rates')
        ordering = ['-effective_date']
        unique_together = ['from_currency', 'to_currency', 'effective_date']
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', 'effective_date']),
            models.Index(fields=['effective_date']),
        ]

    def __str__(self):
        return f"{self.from_currency.code} → {self.to_currency.code}: {self.rate} ({self.effective_date})"

    def clean(self):
        """Validate exchange rate data."""
        if self.rate <= 0:
            raise ValidationError(_('Exchange rate must be positive.'))
        if self.from_currency == self.to_currency:
            raise ValidationError(_('From and to currencies cannot be the same.'))


class PaymentTransaction(TimeStampedUUIDModel):
    """
    Model representing a payment transaction supporting mixed payments.
    Links to both sales and purchase invoices via generic relations.
    """
    PAYMENT_METHOD_CHOICES = [
        ('CASH', _('Cash')),
        ('BANK_TRANSFER', _('Bank Transfer')),
        ('MOBILE_MONEY', _('Mobile Money')),
        ('HAWALA', _('Hawala')),
        ('CHEQUE', _('Cheque')),
        ('CREDIT_CARD', _('Credit Card')),
        ('INSURANCE', _('Insurance')),
        ('OTHER', _('Other')),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ('SALE', _('Sale Payment')),
        ('PURCHASE', _('Purchase Payment')),
        ('REFUND', _('Refund')),
        ('ADJUSTMENT', _('Adjustment')),
    ]

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='payment_transactions',
        verbose_name=_('Currency')
    )
    exchange_rate = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_('Exchange Rate'),
        help_text=_('Exchange rate applied if currency differs from base currency')
    )
    amount_in_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Amount in Base Currency'),
        help_text=_('Converted amount in the system base currency')
    )
    payment_date = models.DateField(verbose_name=_('Payment Date'))
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name=_('Payment Method')
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name=_('Transaction Type')
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference Number')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    # Generic relation to invoice (can be sales or purchase)
    invoice_model = models.CharField(max_length=100, verbose_name=_('Invoice Model'))
    invoice_id = models.UUIDField(verbose_name=_('Invoice ID'))

    class Meta:
        verbose_name = _('Payment Transaction')
        verbose_name_plural = _('Payment Transactions')
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_date']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['currency']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['invoice_model', 'invoice_id']),
        ]

    def __str__(self):
        return f"{self.payment_method} - {self.amount} {self.currency.code} ({self.payment_date})"

    def clean(self):
        """Validate payment transaction data."""
        if self.amount <= 0:
            raise ValidationError(_('Payment amount must be positive.'))
        if self.exchange_rate and self.exchange_rate <= 0:
            raise ValidationError(_('Exchange rate must be positive.'))

    def save(self, *args, **kwargs):
        """Calculate base currency amount on save."""
        if self.exchange_rate and self.amount:
            base_currency = Currency.objects.filter(is_default=True).first()
            if base_currency and self.currency != base_currency:
                self.amount_in_base = self.amount * self.exchange_rate
            else:
                self.amount_in_base = self.amount
        elif self.amount:
            self.amount_in_base = self.amount
        super().save(*args, **kwargs)


class Account(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Model representing an account in the chart of accounts.
    Supports hierarchical structure with parent-child relationships.
    """
    objects = CompanyScopedManager()
    ACCOUNT_TYPE_CHOICES = [
        ('ASSET', _('Asset')),
        ('LIABILITY', _('Liability')),
        ('EQUITY', _('Equity')),
        ('REVENUE', _('Revenue')),
        ('EXPENSE', _('Expense')),
    ]

    ACCOUNT_CATEGORY_CHOICES = [
        ('CURRENT_ASSET', _('Current Asset')),
        ('FIXED_ASSET', _('Fixed Asset')),
        ('INTANGIBLE_ASSET', _('Intangible Asset')),
        ('CURRENT_LIABILITY', _('Current Liability')),
        ('LONG_TERM_LIABILITY', _('Long Term Liability')),
        ('OWNER_EQUITY', _('Owner Equity')),
        ('OPERATING_REVENUE', _('Operating Revenue')),
        ('NON_OPERATING_REVENUE', _('Non Operating Revenue')),
        ('COST_OF_GOODS_SOLD', _('Cost of Goods Sold')),
        ('OPERATING_EXPENSE', _('Operating Expense')),
        ('NON_OPERATING_EXPENSE', _('Non Operating Expense')),
    ]

    name = models.CharField(max_length=255, verbose_name=_('Account Name'))
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Account Code'),
        help_text=_('Unique account code (e.g., 1000, 1100, 1110)')
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        verbose_name=_('Account Type')
    )
    account_category = models.CharField(
        max_length=30,
        choices=ACCOUNT_CATEGORY_CHOICES,
        blank=True,
        null=True,
        verbose_name=_('Account Category')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Account')
    )
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_system = models.BooleanField(
        default=False,
        verbose_name=_('Is System Account'),
        help_text=_('System accounts cannot be deleted')
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Current Balance'),
        help_text=_('Calculated from journal entries')
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='accounts',
        verbose_name=_('Currency')
    )

    class Meta:
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['account_type']),
            models.Index(fields=['account_category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        """Validate account data."""
        if self.parent and self.parent.id == self.id:
            raise ValidationError(_('An account cannot be its own parent.'))
        
        if self.parent:
            self._check_circular_reference()
        
        if self.code:
            self._validate_code_format()

    def _check_circular_reference(self):
        """Check for circular references in account hierarchy."""
        current = self.parent
        visited = set()
        while current is not None:
            if current.id in visited:
                raise ValidationError(_('Circular reference detected in account hierarchy.'))
            visited.add(current.id)
            if current.id == self.id:
                raise ValidationError(_('Circular reference detected in account hierarchy.'))
            current = current.parent

    def _validate_code_format(self):
        """Validate account code format."""
        if not self.code.isdigit():
            raise ValidationError(_('Account code must contain only digits.'))

    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def level(self):
        """Get the depth level of this account in the hierarchy."""
        if self.parent is None:
            return 0
        return self.parent.level + 1

    @property
    def full_path(self):
        """Get the full hierarchical path of the account."""
        if self.parent is None:
            return self.code
        return f"{self.parent.full_path}.{self.code}"

    @property
    def is_leaf(self):
        """Check if this account is a leaf (has no children)."""
        return not self.children.filter(is_active=True).exists()

    @property
    def has_children(self):
        """Check if this account has children."""
        return self.children.filter(is_active=True).exists()

    @property
    def total_balance(self):
        """Calculate total balance including all child accounts."""
        if self.is_leaf:
            return self.balance
        
        total = self.balance
        for child in self.children.filter(is_active=True):
            total += child.total_balance
        return total


class JournalEntry(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Model representing a journal entry in the accounting system.
    Includes full audit trail for enterprise accountability.
    """
    objects = CompanyScopedManager()
    ENTRY_TYPE_CHOICES = [
        ('SALE', _('Sale')),
        ('PURCHASE', _('Purchase')),
        ('PAYMENT', _('Payment')),
        ('RECEIPT', _('Receipt')),
        ('ADJUSTMENT', _('Adjustment')),
        ('TRANSFER', _('Transfer')),
        ('OPENING', _('Opening Balance')),
        ('CLOSING', _('Closing Balance')),
        ('INVENTORY_IN', _('Inventory Receipt')),
        ('INVENTORY_OUT', _('Inventory Issue')),
        ('INVENTORY_ADJ', _('Inventory Adjustment')),
        ('PAYROLL', _('Payroll')),
        ('REVERSAL', _('Reversal')),
    ]

    entry_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Entry Number')
    )
    entry_date = models.DateField(verbose_name=_('Entry Date'))
    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPE_CHOICES,
        verbose_name=_('Entry Type')
    )
    description = models.TextField(verbose_name=_('Description'))
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference')
    )
    is_posted = models.BooleanField(
        default=False,
        verbose_name=_('Is Posted'),
        help_text=_('Posted entries cannot be modified')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    # Audit trail
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_entries_created',
        verbose_name=_('Created By')
    )
    posted_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_entries_posted',
        verbose_name=_('Posted By')
    )
    reversed_by_entry = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reverses_entry',
        verbose_name=_('Reversed By')
    )
    source_module = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Source Module'),
        help_text=_('Module that created this entry (e.g., sales, purchases, inventory, payroll)')
    )
    source_document = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Source Document'),
        help_text=_('Reference to source document ID (e.g., invoice UUID)')
    )
    change_reason = models.TextField(
        blank=True,
        verbose_name=_('Change Reason'),
        help_text=_('Reason for creation or modification')
    )
    original_entry = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversed_entries',
        verbose_name=_('Original Entry (for reversals)')
    )

    class Meta:
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        ordering = ['-entry_date', '-created_at']
        indexes = [
            models.Index(fields=['entry_number']),
            models.Index(fields=['entry_date']),
            models.Index(fields=['entry_type']),
            models.Index(fields=['is_posted']),
            models.Index(fields=['source_module']),
            models.Index(fields=['source_document']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.entry_number} - {self.entry_date}"

    @property
    def total_debit(self):
        """Calculate total debit amount."""
        return sum(line.debit for line in self.lines.all())

    @property
    def total_credit(self):
        """Calculate total credit amount."""
        return sum(line.credit for line in self.lines.all())

    @property
    def is_balanced(self):
        """Check if entry is balanced (debits = credits)."""
        return self.total_debit == self.total_credit

    @property
    def is_reversed(self):
        """Check if this entry has been reversed."""
        return self.reverses_entry.exists()

    def save(self, *args, **kwargs):
        """Override save with fiscal period locking validation."""
        if self.entry_date and not self._state.adding:
            old_entry = JournalEntry.objects.filter(id=self.id).first()
            if old_entry and old_entry.entry_date != self.entry_date:
                if is_period_locked(self.entry_date):
                    raise ValidationError(
                        _('Cannot modify entry: the fiscal period is locked.')
                    )
        elif self.entry_date and self._state.adding:
            if is_period_locked(self.entry_date):
                raise ValidationError(
                    _('Cannot create entry: the fiscal period is locked.')
                )

        super().save(*args, **kwargs)

    def can_modify(self):
        """Check if entry can be modified based on period locking."""
        if self.is_posted:
            return False
        if is_period_locked(self.entry_date):
            return False
        return True

    def can_reverse(self):
        """Check if this entry can be reversed."""
        if not self.is_posted:
            return False
        if self.entry_type == 'REVERSAL':
            return False
        return not self.is_reversed


class JournalEventLog(TimeStampedUUIDModel):
    """
    Lightweight event log for journal entry lifecycle.
    Provides forensic traceability without performance overhead.
    """
    EVENT_TYPE_CHOICES = [
        ('CREATED', 'Created'),
        ('MODIFIED', 'Modified'),
        ('POSTED', 'Posted'),
        ('UNPOSTED', 'Unposted'),
        ('REVERSED', 'Reversed'),
        ('CANCELLED', 'Cancelled'),
        ('VIEWED', 'Viewed'),
    ]

    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='event_logs',
        verbose_name=_('Journal Entry')
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        verbose_name=_('Event Type')
    )
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_events',
        verbose_name=_('User')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )

    class Meta:
        verbose_name = _('Journal Event Log')
        verbose_name_plural = _('Journal Event Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entry']),
            models.Index(fields=['event_type']),
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        user_str = str(self.user) if self.user else 'System'
        return f"{self.entry.entry_number} - {self.event_type} by {user_str} at {self.timestamp}"


class JournalEntryLine(TimeStampedUUIDModel):
    """
    Model representing a line item in a journal entry.
    Includes audit field for forensic traceability.
    """
    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Journal Entry')
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='journal_lines',
        verbose_name=_('Account')
    )
    debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Debit')
    )
    credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Credit')
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Line Description')
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_lines_created',
        verbose_name=_('Created By')
    )

    class Meta:
        verbose_name = _('Journal Entry Line')
        verbose_name_plural = _('Journal Entry Lines')
        ordering = ['id']
        indexes = [
            models.Index(fields=['account']),
            models.Index(fields=['entry']),
        ]

    def __str__(self):
        return f"{self.account.code} - Debit: {self.debit}, Credit: {self.credit}"

    def clean(self):
        """Validate journal entry line."""
        if self.debit < 0 or self.credit < 0:
            raise ValidationError(_('Debit and credit amounts cannot be negative.'))
        if self.debit == 0 and self.credit == 0:
            raise ValidationError(_('Either debit or credit amount must be positive.'))
        if self.debit > 0 and self.credit > 0:
            raise ValidationError(_('Cannot have both debit and credit on the same line.'))


class FiscalPeriod(TimeStampedUUIDModel):
    """
    Model representing a fiscal accounting period with locking capability.
    Ensures financial compliance by preventing modifications to closed periods.
    """
    STATUS_CHOICES = [
        ('OPEN', _('Open')),
        ('CLOSED', _('Closed')),
        ('LOCKED', _('Locked - No Changes Allowed')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Period Name'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('Period Code'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN',
        verbose_name=_('Status')
    )
    is_locked = models.BooleanField(default=False, verbose_name=_('Is Locked'))
    locked_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Locked At'))
    locked_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_periods',
        verbose_name=_('Locked By')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    
    class Meta:
        verbose_name = _('Fiscal Period')
        verbose_name_plural = _('Fiscal Periods')
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_locked']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date}) - {self.status}"
    
    def clean(self):
        """Validate fiscal period."""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError(_('End date must be after start date.'))
    
    def save(self, *args, **kwargs):
        """Override save to enforce locking rules."""
        self.full_clean()
        
        # Auto-set locked status based on status
        if self.status == 'LOCKED':
            self.is_locked = True
        elif self.status == 'OPEN':
            self.is_locked = False
        
        super().save(*args, **kwargs)
    
    def can_modify(self):
        """Check if period allows modifications."""
        if self.is_locked or self.status == 'LOCKED':
            return False
        if self.status == 'CLOSED':
            return False
        return True
    
    def lock(self, user=None):
        """Lock the period - no changes allowed after this."""
        self.is_locked = True
        self.status = 'LOCKED'
        from django.utils import timezone
        self.locked_at = timezone.now()
        self.locked_by = user
        self.save()
    
    def unlock(self):
        """Unlock the period - requires special permission."""
        self.is_locked = False
        self.status = 'OPEN'
        self.locked_at = None
        self.locked_by = None
        self.save()


def is_period_locked(entry_date):
    """Check if a date falls within a locked period."""
    from django.utils import timezone
    today = timezone.now().date()
    
    # Get any locked period that contains this date
    locked_period = FiscalPeriod.objects.filter(
        is_locked=True,
        start_date__lte=entry_date,
        end_date__gte=entry_date
    ).first()
    
    return locked_period is not None


def get_open_period_for_date(entry_date):
    """Get the open period for a given date."""
    return FiscalPeriod.objects.filter(
        status='OPEN',
        start_date__lte=entry_date,
        end_date__gte=entry_date
    ).first()

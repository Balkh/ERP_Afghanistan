import uuid
import random
import string
from decimal import Decimal
from datetime import date, datetime
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from accounting.models import Account, Currency


class PaymentMethod(TimeStampedUUIDModel):
    """
    Payment method configuration.
    Defines available payment methods and their settings.
    """
    METHOD_TYPE_CHOICES = [
        ('CASH', _('Cash')),
        ('BANK_TRANSFER', _('Bank Transfer')),
        ('MOBILE_MONEY', _('Mobile Money')),
        ('HAWALA', _('Hawala')),
        ('CHEQUE', _('Cheque')),
        ('CREDIT_CARD', _('Credit Card')),
        ('MIXED', _('Mixed Payment')),
    ]

    name = models.CharField(max_length=100, verbose_name=_('Payment Method Name'))
    code = models.CharField(max_length=50, unique=True, verbose_name=_('Method Code'))
    method_type = models.CharField(
        max_length=20,
        choices=METHOD_TYPE_CHOICES,
        verbose_name=_('Method Type')
    )
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_default = models.BooleanField(default=False, verbose_name=_('Is Default'))

    # Provider settings (for mobile money, hawala, banks)
    provider_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Provider Name'),
        help_text=_('e.g., M-Pesa, Etisalat, Al-Farooq Hawala')
    )
    provider_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Provider Code')
    )

    # Fee configuration
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Fee Percentage'),
        help_text=_('Transaction fee as percentage (e.g., 1.5 for 1.5%)')
    )
    fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Fixed Fee')
    )

    # Reference number pattern
    ref_prefix = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Reference Prefix'),
        help_text=_('Prefix for auto-generated transaction numbers')
    )
    ref_format = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Reference Format'),
        help_text=_('Format pattern for transaction references')
    )

    class Meta:
        verbose_name = _('Payment Method')
        verbose_name_plural = _('Payment Methods')
        ordering = ['code']
        indexes = [
            models.Index(fields=['method_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]

    def __str__(self):
        return f"{self.name} ({self.method_type})"

    def clean(self):
        if self.fee_percentage < 0 or self.fee_percentage > 100:
            raise ValidationError(_('Fee percentage must be between 0 and 100.'))
        if self.fee_fixed < 0:
            raise ValidationError(_('Fixed fee cannot be negative.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_default:
            PaymentMethod.objects.filter(
                method_type=self.method_type, is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def calculate_fee(self, amount: Decimal) -> Decimal:
        """Calculate transaction fee for a given amount."""
        percentage_fee = amount * (self.fee_percentage / Decimal('100'))
        return percentage_fee + self.fee_fixed


class PaymentAccount(TimeStampedUUIDModel):
    """
    Payment account (cash drawer, bank account, mobile wallet, hawala account).
    Links to the chart of accounts for double-entry tracking.
    """
    ACCOUNT_TYPE_CHOICES = [
        ('CASH', _('Cash Account')),
        ('BANK', _('Bank Account')),
        ('MOBILE_WALLET', _('Mobile Wallet')),
        ('HAWALA', _('Hawala Account')),
        ('CHEQUE', _('Cheque Account')),
    ]

    CURRENCY_CHOICES = [
        ('AFN', _('Afghan Afghani')),
        ('USD', _('US Dollar')),
        ('PKR', _('Pakistani Rupee')),
        ('IRR', _('Iranian Rial')),
    ]

    name = models.CharField(max_length=100, verbose_name=_('Account Name'))
    code = models.CharField(max_length=50, unique=True, verbose_name=_('Account Code'))
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        verbose_name=_('Account Type')
    )

    # Link to chart of accounts
    accounting_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='payment_accounts',
        verbose_name=_('Linked Accounting Account'),
        help_text=_('Account in the chart of accounts')
    )

    # Provider information
    provider_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Provider Name'),
        help_text=_('Bank name, mobile operator, hawala dealer')
    )
    account_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Account Number')
    )
    iban = models.CharField(
        max_length=34,
        blank=True,
        verbose_name=_('IBAN')
    )
    swift_code = models.CharField(
        max_length=11,
        blank=True,
        verbose_name=_('SWIFT/BIC Code')
    )

    # Currency
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='AFN',
        verbose_name=_('Account Currency')
    )

    # Balance tracking
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Current Balance')
    )
    min_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Minimum Balance Alert')
    )
    max_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Maximum Balance Limit')
    )

    # Status
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_default = models.BooleanField(default=False, verbose_name=_('Is Default'))

    # Location (for cash drawers)
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Location'),
        help_text=_('e.g., Counter 1, Main Office, Branch 2')
    )

    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Payment Account')
        verbose_name_plural = _('Payment Accounts')
        ordering = ['code']
        indexes = [
            models.Index(fields=['account_type']),
            models.Index(fields=['currency']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name} ({self.account_type})"

    def clean(self):
        if self.current_balance < 0:
            raise ValidationError(_('Current balance cannot be negative.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_default:
            PaymentAccount.objects.filter(
                account_type=self.account_type, is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def formatted_balance(self) -> str:
        return f"{self.currency} {self.current_balance:,.2f}"

    def can_withdraw(self, amount: Decimal) -> bool:
        """Check if account has sufficient funds."""
        return self.current_balance >= amount


class FinancialTransaction(TimeStampedUUIDModel):
    """
    Core financial transaction model.
    Handles receipts, payments, transfers between accounts.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('RECEIPT', _('Receipt')),
        ('PAYMENT', _('Payment')),
        ('TRANSFER', _('Transfer')),
        ('ADJUSTMENT', _('Adjustment')),
        ('REFUND', _('Refund')),
    ]

    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('PROCESSING', _('Processing')),
        ('COMPLETED', _('Completed')),
        ('FAILED', _('Failed')),
        ('CANCELLED', _('Cancelled')),
        ('REVERSED', _('Reversed')),
    ]

    # Transaction identification
    transaction_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Transaction Number'),
        help_text=_('Auto-generated unique transaction reference')
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name=_('Transaction Type')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='COMPLETED',
        verbose_name=_('Status')
    )

    # Payment method and accounts
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name=_('Payment Method')
    )

    # Source account (where money comes from)
    source_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.PROTECT,
        related_name='outgoing_transactions',
        null=True,
        blank=True,
        verbose_name=_('Source Account'),
        help_text=_('Account money is coming from (for payments/transfers)')
    )

    # Destination account (where money goes)
    destination_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.PROTECT,
        related_name='incoming_transactions',
        null=True,
        blank=True,
        verbose_name=_('Destination Account'),
        help_text=_('Account money is going to (for receipts/transfers)')
    )

    # Amounts
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    currency = models.CharField(
        max_length=3,
        default='AFN',
        verbose_name=_('Currency')
    )
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Transaction Fee')
    )
    net_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Net Amount'),
        help_text=_('Amount after deducting fees')
    )

    # Exchange rate (for multi-currency)
    exchange_rate = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        default=Decimal('1.000000'),
        verbose_name=_('Exchange Rate')
    )
    amount_in_base = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Amount in Base Currency (AFN)')
    )

    # References
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('External Reference'),
        help_text=_('Mobile payment ref, hawala ref, bank ref')
    )
    internal_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Internal Reference')
    )
    description = models.TextField(verbose_name=_('Description'))

    # Related entities (generic relations)
    party_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('CUSTOMER', _('Customer')),
            ('SUPPLIER', _('Supplier')),
            ('EMPLOYEE', _('Employee')),
            ('OTHER', _('Other')),
        ],
        verbose_name=_('Party Type')
    )
    party_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('Party ID')
    )
    party_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Party Name')
    )

    # Invoice linkage
    invoice_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('SALES', _('Sales Invoice')),
            ('PURCHASE', _('Purchase Invoice')),
        ],
        verbose_name=_('Invoice Type')
    )
    invoice_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('Invoice ID')
    )

    # Dates
    transaction_date = models.DateField(
        default=timezone.now,
        verbose_name=_('Transaction Date')
    )
    value_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Value Date'),
        help_text=_('Date when funds are actually available')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed At')
    )

    # Hawala-specific fields
    hawala_dealer = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Hawala Dealer')
    )
    hawala_token = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Hawala Token/Code'),
        help_text=_('Secret code for hawala collection')
    )
    hawala_origin = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Hawala Origin'),
        help_text=_('City/country of origin')
    )
    hawala_destination = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Hawala Destination'),
        help_text=_('City/country of destination')
    )

    # Mobile money specific
    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Mobile Number')
    )
    mobile_operator = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Mobile Operator')
    )

    # Settlement tracking
    is_settled = models.BooleanField(
        default=False,
        verbose_name=_('Is Settled'),
        help_text=_('Whether the transaction has been reconciled')
    )
    settled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Settled At')
    )
    settlement_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Settlement Reference')
    )

    # Accounting
    journal_entry_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('Journal Entry ID')
    )

    # Audit
    performed_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Performed By')
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

    class Meta:
        verbose_name = _('Financial Transaction')
        verbose_name_plural = _('Financial Transactions')
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_number']),
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['transaction_date']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['source_account']),
            models.Index(fields=['destination_account']),
            models.Index(fields=['invoice_type', 'invoice_id']),
            models.Index(fields=['party_type', 'party_id']),
            models.Index(fields=['is_settled']),
            models.Index(fields=['reference_number']),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.amount} {self.currency} ({self.transaction_type})"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError(_('Transaction amount must be positive.'))
        if self.fee < 0:
            raise ValidationError(_('Transaction fee cannot be negative.'))
        if self.exchange_rate <= 0:
            raise ValidationError(_('Exchange rate must be positive.'))

    def save(self, *args, **kwargs):
        """Calculate derived fields. Retries transaction_number on IntegrityError (PAY-01)."""
        from django.db import IntegrityError, transaction as db_transaction
        if not self.transaction_number:
            # Try up to 5 times to allocate a unique transaction_number under concurrency
            for _attempt in range(5):
                candidate = self.generate_transaction_number()
                self.transaction_number = candidate
                try:
                    with db_transaction.atomic():
                        if self.net_amount is None:
                            self.net_amount = self.amount - self.fee
                        if self.currency == 'AFN':
                            self.amount_in_base = self.amount
                        elif self.exchange_rate:
                            self.amount_in_base = self.amount * self.exchange_rate
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.transaction_number = None
                    continue
            raise IntegrityError(
                _('Could not allocate a unique transaction_number after 5 attempts.')
            )

        if self.net_amount is None:
            self.net_amount = self.amount - self.fee

        if self.currency == 'AFN':
            self.amount_in_base = self.amount
        elif self.exchange_rate:
            self.amount_in_base = self.amount * self.exchange_rate

        super().save(*args, **kwargs)

    def generate_transaction_number(self) -> str:
        """Generate unique transaction number based on method type."""
        prefix_map = {
            'CASH': 'CASH',
            'BANK_TRANSFER': 'BANK',
            'MOBILE_MONEY': 'MOB',
            'HAWALA': 'HAW',
            'CHEQUE': 'CHQ',
            'CREDIT_CARD': 'CC',
            'MIXED': 'MIX',
        }

        type_prefix_map = {
            'RECEIPT': 'R',
            'PAYMENT': 'P',
            'TRANSFER': 'T',
            'ADJUSTMENT': 'A',
            'REFUND': 'RF',
        }

        method_prefix = prefix_map.get(self.payment_method.method_type, 'PAY') if hasattr(self, 'payment_method') else 'PAY'
        type_prefix = type_prefix_map.get(self.transaction_type, 'T')

        now = timezone.now()
        date_str = now.strftime('%Y%m%d')
        seq = FinancialTransaction.objects.filter(
            transaction_date=now.date()
        ).count() + 1

        return f"{type_prefix}-{method_prefix}-{date_str}-{seq:05d}"


class TransactionSettlement(TimeStampedUUIDModel):
    """
    Tracks settlement/reconciliation of transactions.
    Used for batch settlements, bank reconciliations, hawala settlements.
    """
    SETTLEMENT_TYPE_CHOICES = [
        ('BATCH', _('Batch Settlement')),
        ('BANK_RECONCILIATION', _('Bank Reconciliation')),
        ('HAWALA_SETTLEMENT', _('Hawala Settlement')),
        ('MOBILE_SETTLEMENT', _('Mobile Money Settlement')),
        ('MANUAL', _('Manual Settlement')),
    ]

    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('IN_PROGRESS', _('In Progress')),
        ('COMPLETED', _('Completed')),
        ('DISCREPANCY', _('Discrepancy')),
        ('CANCELLED', _('Cancelled')),
    ]

    settlement_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Settlement Number')
    )
    settlement_type = models.CharField(
        max_length=30,
        choices=SETTLEMENT_TYPE_CHOICES,
        verbose_name=_('Settlement Type')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name=_('Status')
    )

    # Accounts involved
    payment_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.PROTECT,
        related_name='settlements',
        verbose_name=_('Payment Account')
    )

    # Date range
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))

    # Amounts
    expected_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Expected Amount')
    )
    actual_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Actual Amount')
    )
    difference = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Difference')
    )

    # External references
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('External Reference'),
        help_text=_('Bank statement ref, hawala settlement ref')
    )

    # Settlement details
    description = models.TextField(verbose_name=_('Description'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    # Tracking
    performed_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Performed By')
    )
    approved_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Approved By')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed At')
    )

    class Meta:
        verbose_name = _('Transaction Settlement')
        verbose_name_plural = _('Transaction Settlements')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.settlement_number} - {self.settlement_type} ({self.status})"

    def save(self, *args, **kwargs):
        from django.db import IntegrityError
        if not self.settlement_number:
            prefix_map = {
                'BATCH': 'SET',
                'BANK_RECONCILIATION': 'BNK',
                'HAWALA_SETTLEMENT': 'HAW',
                'MOBILE_SETTLEMENT': 'MOB',
                'MANUAL': 'MAN',
            }
            prefix = prefix_map.get(self.settlement_type, 'SET')
            now = timezone.now()
            # Retry on IntegrityError to handle concurrent settlement_number generation (PAY-02)
            for _attempt in range(5):
                seq = TransactionSettlement.objects.filter(
                    created_at__month=now.month,
                    created_at__year=now.year
                ).count() + 1
                self.settlement_number = f"{prefix}-{now.strftime('%Y%m')}-{seq:04d}"
                if self.actual_amount is not None:
                    self.difference = self.actual_amount - self.expected_amount
                try:
                    super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.settlement_number = None
                    continue
            raise IntegrityError(
                _('Could not allocate a unique settlement_number after 5 attempts.')
            )

        if self.actual_amount is not None:
            self.difference = self.actual_amount - self.expected_amount

        super().save(*args, **kwargs)


class SettlementTransaction(TimeStampedUUIDModel):
    """
    Links individual transactions to a settlement batch.
    """
    settlement = models.ForeignKey(
        TransactionSettlement,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Settlement')
    )
    transaction = models.ForeignKey(
        FinancialTransaction,
        on_delete=models.PROTECT,
        related_name='settlements',
        verbose_name=_('Transaction')
    )
    included_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Included Amount')
    )

    class Meta:
        verbose_name = _('Settlement Transaction')
        verbose_name_plural = _('Settlement Transactions')
        unique_together = ['settlement', 'transaction']

    def __str__(self):
        return f"{self.settlement.settlement_number} - {self.transaction.transaction_number}"

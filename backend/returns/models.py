"""
Returns Management Module for Pharmacy ERP.
Integrates with Sales, Purchases, Inventory, and Accounting.
"""
import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel


class ReturnOrder(TimeStampedUUIDModel):
    """
    Return order - linked to Invoice, Inventory, and Accounting.
    MUST be transaction-safe: ALL OR NOTHING.
    """
    RETURN_TYPE_CHOICES = [
        ('SALE_RETURN', _('Sale Return')),
        ('PURCHASE_RETURN', _('Purchase Return')),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('APPROVED', _('Approved')),
        ('REJECTED', _('Rejected')),
        ('COMPLETED', _('Completed')),
    ]

    # Core identification
    return_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Return Number'),
        help_text=_('Auto-generated return identifier')
    )
    
    # Type
    return_type = models.CharField(
        max_length=20,
        choices=RETURN_TYPE_CHOICES,
        verbose_name=_('Return Type')
    )
    
    # Link to Invoice
    invoice = models.ForeignKey(
        'sales.SalesInvoice',
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name=_('Sales Invoice'),
        blank=True,
        null=True
    )
    purchase_invoice = models.ForeignKey(
        'purchases.PurchaseInvoice',
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name=_('Purchase Invoice'),
        blank=True,
        null=True
    )
    
    # Party (Customer or Supplier)
    party = models.ForeignKey(
        'sales.Customer',
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name=_('Customer'),
        blank=True,
        null=True
    )
    supplier = models.ForeignKey(
        'purchases.Supplier',
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name=_('Supplier'),
        blank=True,
        null=True
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name=_('Status')
    )
    
    # Financial
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Return Amount')
    )
    
    # Reason
    reason = models.TextField(verbose_name=_('Return Reason'))
    
    # Notes
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    
    # Approval
    approved_by = models.ForeignKey(
        'hr.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_returns',
        verbose_name=_('Approved By')
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Approved At'))
    
    # Accounting reference
    credit_note_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Credit Note Number')
    )
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returns',
        verbose_name=_('Journal Entry')
    )

    class Meta:
        verbose_name = _('Return Order')
        verbose_name_plural = _('Return Orders')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['return_number']),
            models.Index(fields=['return_type']),
            models.Index(fields=['status']),
            models.Index(fields=['invoice']),
            models.Index(fields=['party']),
        ]

    def __str__(self):
        return f"{self.return_number} - {self.get_return_type_display()}"

    def clean(self):
        """Validate return order."""
        if self.return_type == 'SALE_RETURN' and not self.invoice:
            raise ValidationError(_('Sale return must reference a sales invoice.'))
        if self.return_type == 'PURCHASE_RETURN' and not self.purchase_invoice:
            raise ValidationError(_('Purchase return must reference a purchase invoice.'))
        
        # Validate party matches invoice
        if self.invoice and self.party != self.invoice.customer:
            raise ValidationError(_('Return party must match invoice customer.'))
        if self.purchase_invoice and self.supplier != self.purchase_invoice.supplier:
            raise ValidationError(_('Return supplier must match invoice supplier.'))

    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self._generate_return_number()
        super().save(*args, **kwargs)
    
    def _generate_return_number(self):
        """Generate unique return number."""
        prefix = 'SR' if self.return_type == 'SALE_RETURN' else 'PR'
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
    
    @transaction.atomic
    def approve(self, employee):
        """
        Approve return — triggers inventory and accounting updates.
        MUST be atomic: ALL OR NOTHING.
        select_for_update ensures no concurrent approval race.
        """
        # Lock the return order FIRST — prevents race conditions
        locked = ReturnOrder.objects.select_for_update().get(pk=self.pk)
        self.status = locked.status
        self.invoice = locked.invoice
        self.purchase_invoice = locked.purchase_invoice

        if self.status != 'PENDING':
            raise ValidationError(_('Only pending returns can be approved.'))
        
        # 1. Update Inventory - restore stock based on item conditions
        for item in self.items.all():
            if item.return_quantity > item.get_original_quantity():
                raise ValidationError(
                    _(f'Return quantity for {item.product.name} exceeds invoice quantity.')
                )
            item.restore_inventory()
            
        # 2. Create Accounting - credit/debit note using JournalEngine
        self._create_accounting_entries(employee)
        
        # 3. Create Reconciliation record
        from returns.services.reconciliation_service import ReconciliationService
        rec_service = ReconciliationService(company_id=self.invoice.company_id if self.invoice else self.purchase_invoice.company_id)
        rec_service.create_return_reconciliation(self, self.journal_entry)
        
        # 4. Execute refund for sale returns that have payments
        if self.return_type == 'SALE_RETURN':
            try:
                from returns.services.refund_service import RefundExecutionService, RefundRequest
                refund_service = RefundExecutionService()
                refund_request = RefundRequest(
                    return_order=self,
                    refund_amount=self.total_amount,
                    reason_code="CUSTOMER_RETURN",
                    performed_by=str(employee.id) if hasattr(employee, 'id') else 'system',
                    notes=self.reason,
                )
                refund_service.execute_return_refund(refund_request)
            except Exception:
                pass

        # 5. Update status
        self.status = 'APPROVED'
        self.approved_by = employee
        from django.utils import timezone
        self.approved_at = timezone.now()
        self.save()
        
        return True
    
    def _create_accounting_entries(self, employee):
        """Create accounting journal entries for the return with tax and discount reversal."""
        from accounting.services.journal_engine import JournalEngine
        from accounting.models import JournalEntry, Account
        
        # Get accounts based on return type
        if self.return_type == 'SALE_RETURN':
            # Customer returns - reverse Revenue, Tax, and AR
            try:
                ar_account = Account.objects.get(code='1200')  # Accounts Receivable
                sales_return_account = Account.objects.get(code='4200')  # Sales Returns
                tax_account = Account.objects.get(code='2100')  # Sales Tax Payable
                inventory_account = Account.objects.get(code='1300')  # Inventory
                cogs_account = Account.objects.get(code='5100')  # Cost of Goods Sold
            except Account.DoesNotExist:
                raise ValidationError(_('Required accounting accounts not found.'))
            
            # Calculate totals for reversal
            total_tax = sum(item.tax_amount for item in self.items.all())
            total_subtotal_net = sum((item.return_quantity * item.unit_price) - item.discount_amount for item in self.items.all())
            
            description = f"Return {self.return_number} - Credit Note"
            
            # 1. Main Return Entry: 
            # Dr Sales Returns (Net Subtotal)
            # Dr Tax Payable (Total Tax)
            # Cr Accounts Receivable (Grand Total)
            lines = [
                {'account': sales_return_account, 'debit': total_subtotal_net, 'credit': 0},
            ]
            
            if total_tax > 0:
                lines.append({'account': tax_account, 'debit': total_tax, 'credit': 0})
            
            lines.append({'account': ar_account, 'debit': 0, 'credit': self.total_amount})
            
            journal_entry = JournalEngine.create_journal_entry(
                date=self.created_at.date(),
                description=description,
                company_id=self.invoice.company_id if self.invoice else None,
                lines=lines,
                created_by=employee
            )
            
            # Update customer balance
            if self.party:
                self.party.balance -= self.total_amount
                self.party.save()
        
        else:  # PURCHASE_RETURN
            # Supplier returns - reduce AP, reduce Inventory, reverse Tax
            try:
                ap_account = Account.objects.get(code='2100')  # Accounts Payable
                inventory_account = Account.objects.get(code='1300')  # Inventory
                tax_account = Account.objects.get(code='2110')  # Purchase Tax Receivable
            except Account.DoesNotExist:
                raise ValidationError(_('Required accounting accounts not found.'))
            
            total_tax = sum(item.tax_amount for item in self.items.all())
            total_subtotal_net = sum((item.return_quantity * item.unit_price) - item.discount_amount for item in self.items.all())
            
            description = f"Return {self.return_number} - Debit Note"
            
            # Dr Accounts Payable (Grand Total)
            # Cr Inventory (Net Subtotal)
            # Cr Tax Receivable (Total Tax)
            lines = [
                {'account': ap_account, 'debit': self.total_amount, 'credit': 0},
                {'account': inventory_account, 'debit': 0, 'credit': total_subtotal_net},
            ]
            
            if total_tax > 0:
                lines.append({'account': tax_account, 'debit': 0, 'credit': total_tax})
            
            journal_entry = JournalEngine.create_journal_entry(
                date=self.created_at.date(),
                description=description,
                company_id=self.purchase_invoice.company_id if self.purchase_invoice else None,
                lines=lines,
                created_by=employee
            )
            
            # Update supplier balance
            if self.supplier:
                self.supplier.balance -= self.total_amount
                self.supplier.save()
        
        self.journal_entry = journal_entry
        self.credit_note_number = f"CN-{self.return_number}"
        self.save()
    
    def get_total_invoice_amount(self):
        """Get the original invoice total."""
        if self.invoice:
            return self.invoice.total_amount
        if self.purchase_invoice:
            return self.purchase_invoice.total_amount
        return Decimal('0.00')


class ReturnItem(TimeStampedUUIDModel):
    """
    Individual items in a return order.
    """
    return_order = models.ForeignKey(
        ReturnOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Return Order')
    )
    
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='return_items',
        verbose_name=_('Product')
    )
    
    # Quantity
    return_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Return Quantity')
    )
    
    # Price
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Unit Price')
    )
    
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Amount')
    )
    
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax Amount')
    )
    
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Total Price')
    )
    
    # Batch (if applicable)
    batch = models.ForeignKey(
        'inventory.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_items',
        verbose_name=_('Batch')
    )
    
    # Original invoice item reference
    invoice_item = models.ForeignKey(
        'sales.SalesItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_items',
        verbose_name=_('Invoice Item')
    )
    purchase_invoice_item = models.ForeignKey(
        'purchases.PurchaseItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_items',
        verbose_name=_('Purchase Invoice Item')
    )
    
    CONDITION_CHOICES = [
        ('GOOD', _('Good (Back to Stock)')),
        ('DAMAGED', _('Damaged (Quarantine)')),
        ('EXPIRED', _('Expired (Quarantine)')),
    ]
    
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='GOOD',
        verbose_name=_('Item Condition')
    )
    
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Return Item')
        verbose_name_plural = _('Return Items')

    def __str__(self):
        return f"{self.product.name} x {self.return_quantity}"
    
    def save(self, *args, **kwargs):
        # Total Price = (Qty * Unit Price) - Discount + Tax
        self.total_price = (self.return_quantity * self.unit_price) - self.discount_amount + self.tax_amount
        super().save(*args, **kwargs)
    
    def get_original_quantity(self):
        """Get the quantity from the original invoice."""
        if self.invoice_item:
            return self.invoice_item.quantity
        if self.purchase_invoice_item:
            return self.purchase_invoice_item.quantity
        return Decimal('0.00')
    
    def restore_inventory(self):
        """
        Restore inventory for this return item based on condition.
        Used inside the approve() atomic transaction — NOT independently atomic.
        StockMovement.save() handles batch quantity updates automatically via _update_batch_quantity().
        """
        from inventory.models import StockMovement, Batch
        
        # Determine warehouse
        warehouse = None
        if self.return_order.invoice:
            warehouse = self.return_order.invoice.warehouse
        elif self.return_order.purchase_invoice:
            warehouse = self.return_order.purchase_invoice.warehouse
        
        if not warehouse:
            raise ValidationError(_('Cannot determine warehouse for inventory restoration.'))
        
        # Determine movement type based on condition
        if self.condition == 'GOOD':
            movement_type = 'RETURN_IN' if self.return_order.return_type == 'SALE_RETURN' else 'RETURN_PURCHASE'
        elif self.condition == 'DAMAGED':
            movement_type = 'RETURN_DAMAGED'
        else:
            movement_type = 'RETURN_EXPIRED'

        # Create stock movement (StockMovement.save() auto-updates batch via _update_batch_quantity)
        # Do NOT manually update batch here — _update_batch_quantity() sums all movements
        movement = StockMovement.objects.create(
            product=self.product,
            warehouse=warehouse,
            batch=self.batch,
            movement_type=movement_type,
            reference_type='RETURN',
            quantity=self.return_quantity,
            reference=f"Return {self.return_order.return_number}",
            reference_id=self.return_order.return_number,
            company_id=warehouse.company_id,
            notes=f"Condition: {self.get_condition_display()}. {self.notes}"
        )
        
        return movement


class ReconciliationEntry(TimeStampedUUIDModel):
    """
    Tracks reconciliation between Invoice, Return, and Accounting Entries.
    Source of truth for financial consistency.
    """
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('MATCHED', _('Matched')),
        ('MISMATCHED', _('Mismatch')),
        ('FIXED', _('Fixed')),
    ]
    
    TRANSACTION_TYPE_CHOICES = [
        ('INVOICE', _('Invoice')),
        ('RETURN', _('Return')),
        ('PAYMENT', _('Payment')),
        ('ADJUSTMENT', _('Adjustment')),
    ]
    
    # Links
    invoice = models.ForeignKey(
        'sales.SalesInvoice',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reconciliation_entries',
        verbose_name=_('Sales Invoice')
    )
    
    return_order = models.ForeignKey(
        'returns.ReturnOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reconciliation_entries',
        verbose_name=_('Return Order')
    )
    
    accounting_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reconciliation_entries',
        verbose_name=_('Journal Entry')
    )
    
    linked_reconciliation = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_entries',
        verbose_name=_('Linked Reconciliation')
    )
    
    # Party (Customer/Supplier)
    party = models.ForeignKey(
        'sales.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_entries',
        verbose_name=_('Customer')
    )
    supplier = models.ForeignKey(
        'purchases.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliation_entries',
        verbose_name=_('Supplier')
    )
    
    # Company
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='reconciliation_entries',
        verbose_name=_('Company')
    )
    
    # Type and Amount
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name=_('Transaction Type')
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name=_('Status')
    )
    
    # Fix tracking
    fixed_by = models.ForeignKey(
        'hr.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fixed_reconciliations',
        verbose_name=_('Fixed By')
    )
    fixed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Fixed At'))
    fix_notes = models.TextField(blank=True, verbose_name=_('Fix Notes'))
    
    # Notes
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Reconciliation Entry')
        verbose_name_plural = _('Reconciliation Entries')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['invoice']),
            models.Index(fields=['return_order']),
            models.Index(fields=['accounting_entry']),
            models.Index(fields=['company']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status}"
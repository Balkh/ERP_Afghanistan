import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel, Company
from core.multitenant.models import CompanyScopedMixin, CompanyScopedManager


class Category(TimeStampedUUIDModel):
    """
    Model representing a product category
    """
    name = models.CharField(max_length=255, verbose_name=_('Category Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='children',
        verbose_name=_('Parent Category')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']
        unique_together = ['name', 'parent']  # Prevent duplicate names under same parent

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def clean(self):
        """Validate category to prevent circular references"""
        from django.core.exceptions import ValidationError
        
        # Prevent category from being its own parent
        if self.parent and self.parent.id == self.id:
            raise ValidationError(_('A category cannot be its own parent.'))
        
        # Check for circular references
        if self.parent:
            current = self.parent
            level = 0
            while current is not None and level < 100:  # Prevent infinite loops
                if current.id == self.id:
                    raise ValidationError(_('Circular reference detected in category hierarchy.'))
                current = current.parent
                level += 1

    def save(self, *args, **kwargs):
        """
        Override save to ensure validation is called
        """
        self.full_clean()
        super().save(*args, **kwargs)


class Unit(TimeStampedUUIDModel):
    """
    Model representing a unit of measurement
    """
    name = models.CharField(max_length=50, verbose_name=_('Unit Name'))
    symbol = models.CharField(max_length=10, verbose_name=_('Symbol'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Unit')
        verbose_name_plural = _('Units')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class Product(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Product model representing items in the inventory.
    Supports both company-specific and global (non-company) products.
    """
    objects = CompanyScopedManager()
    name = models.CharField(max_length=255, verbose_name=_('Product Name'))
    generic_name = models.CharField(max_length=255, verbose_name=_('Generic Name'))
    brand_name = models.CharField(max_length=255, verbose_name=_('Brand Name'))
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        verbose_name=_('Category')
    )
    unit = models.ForeignKey(
        Unit, 
        on_delete=models.PROTECT, 
        verbose_name=_('Unit')
    )
    strength = models.CharField(max_length=100, verbose_name=_('Strength'))
    form = models.CharField(max_length=100, verbose_name=_('Form'))
    manufacturer = models.CharField(max_length=255, verbose_name=_('Manufacturer'))
    barcode = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name=_('Barcode'),
        help_text=_('Product barcode for scanning')
    )
    sku = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name=_('SKU'),
        help_text=_('Stock Keeping Unit')
    )
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    requires_prescription = models.BooleanField(
        default=False, 
        verbose_name=_('Requires Prescription'),
        help_text=_('Whether this product requires a prescription to sell')
    )
    is_controlled_substance = models.BooleanField(
        default=False, 
        verbose_name=_('Controlled Substance'),
        help_text=_('Whether this product is a controlled substance')
    )

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['generic_name']),
            models.Index(fields=['brand_name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.strength} {self.form})"


class Batch(TimeStampedUUIDModel):
    """
    Model representing a pharmaceutical batch with tracking information
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        verbose_name=_('Product')
    )
    batch_number = models.CharField(max_length=100, unique=True, verbose_name=_('Batch Number'))
    barcode = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        unique=True, 
        verbose_name=_('Batch Barcode'),
        help_text=_('Optional barcode for this specific batch. Falls back to batch_number if empty.')
    )
    manufacturing_date = models.DateField(
        verbose_name=_('Manufacturing Date'),
        help_text=_('Date when the batch was manufactured')
    )
    expiry_date = models.DateField(verbose_name=_('Expiry Date'))
    purchase_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Purchase Price'),
        help_text=_('Purchase price per unit')
    )
    sale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Sale Price'),
        help_text=_('Sale price per unit')
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Quantity'),
        help_text=_('Total quantity in this batch')
    )
    remaining_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Remaining Quantity'),
        help_text=_('Quantity remaining in stock')
    )
    location = models.CharField(max_length=255, verbose_name=_('Location'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Batch')
        verbose_name_plural = _('Batches')
        ordering = ['expiry_date', 'manufacturing_date']
        indexes = [
            models.Index(fields=['expiry_date']),
            models.Index(fields=['product', 'expiry_date']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return f"{self.product.name} - Batch: {self.batch_number} (Exp: {self.expiry_date})"

    def clean(self):
        """Validate batch data"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone

        # Ensure manufacturing date is not in the future
        if self.manufacturing_date and self.manufacturing_date > timezone.now().date():
            raise ValidationError(_('Manufacturing date cannot be in the future.'))

        # Ensure expiry date is after manufacturing date
        if self.manufacturing_date and self.expiry_date and self.expiry_date <= self.manufacturing_date:
            raise ValidationError(_('Expiry date must be after manufacturing date.'))

        # Ensure remaining quantity does not exceed total quantity
        if self.remaining_quantity and self.quantity and self.remaining_quantity > self.quantity:
            raise ValidationError(_('Remaining quantity cannot exceed total quantity.'))

        # Ensure prices are positive
        if self.purchase_price is not None and self.purchase_price < 0:
            raise ValidationError(_('Purchase price cannot be negative.'))
        if self.sale_price is not None and self.sale_price < 0:
            raise ValidationError(_('Sale price cannot be negative.'))
    
    def save(self, *args, **kwargs):
        """
        Override save to ensure validation is called and set remaining quantity if not set
        """
        # Set remaining quantity to quantity only if it's None (not set)
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
        
        # Only run full_clean if all fields are being saved (not using update_fields)
        update_fields = kwargs.get('update_fields')
        if not update_fields:
            self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if the batch has expired"""
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
    
    @property
    def days_until_expiry(self):
        """Get days until expiry (negative if already expired)"""
        from django.utils import timezone
        delta = self.expiry_date - timezone.now().date()
        return delta.days
    
    @property
    def is_expiring_soon(self, threshold_days=30):
        """Check if batch is expiring within threshold days"""
        from django.utils import timezone
        if self.is_expired:
            return False
        return self.days_until_expiry <= threshold_days
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.purchase_price and self.purchase_price > 0:
            return ((self.sale_price - self.purchase_price) / self.purchase_price) * 100
        return 0


class Warehouse(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Model representing a warehouse or storage location
    """
    objects = CompanyScopedManager()
    name = models.CharField(max_length=255, verbose_name=_('Warehouse Name'))
    code = models.CharField(max_length=50, unique=True, verbose_name=_('Warehouse Code'))
    address = models.TextField(blank=True, verbose_name=_('Address'))
    contact_person = models.CharField(max_length=255, blank=True, verbose_name=_('Contact Person'))
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name=_('Contact Phone'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_default = models.BooleanField(default=False, verbose_name=_('Is Default Warehouse'))

    class Meta:
        verbose_name = _('Warehouse')
        verbose_name_plural = _('Warehouses')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Ensure only one default warehouse"""
        from django.core.exceptions import ValidationError
        if self.is_default:
            # Check if another warehouse is already set as default
            existing_default = Warehouse.objects.filter(is_default=True).exclude(id=self.id)
            if existing_default.exists():
                raise ValidationError(_('Only one warehouse can be set as default.'))


class StockMovement(TimeStampedUUIDModel):
    """
    Model representing stock movements (in/out/adjustment)
    """
    MOVEMENT_TYPES = [
        ('IN', _('Stock In')),
        ('OUT', _('Stock Out')),
        ('ADJUSTMENT', _('Adjustment')),
        ('TRANSFER', _('Transfer')),
        ('RETURN_IN', _('Return In (Sale Return)')),
        ('RETURN_PURCHASE', _('Return Purchase')),
        ('RETURN_DAMAGED', _('Return Damaged (Quarantine)')),
        ('RETURN_EXPIRED', _('Return Expired (Quarantine)')),
    ]
    
    REFERENCE_TYPES = [
        ('PURCHASE', _('Purchase')),
        ('SALE', _('Sale')),
        ('RETURN', _('Return')),
        ('PRODUCTION', _('Production')),
        ('WASTE', _('Waste')),
        ('EXPIRY', _('Expiry')),
        ('MANUAL', _('Manual Adjustment')),
    ]
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        verbose_name=_('Product')
    )
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.CASCADE, 
        verbose_name=_('Batch'),
        null=True,
        blank=True
    )
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.CASCADE, 
        verbose_name=_('Warehouse')
    )
    movement_type = models.CharField(
        max_length=20, 
        choices=MOVEMENT_TYPES, 
        verbose_name=_('Movement Type')
    )
    reference_type = models.CharField(
        max_length=20, 
        choices=REFERENCE_TYPES, 
        verbose_name=_('Reference Type')
    )
    reference_id = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name=_('Reference ID'),
        help_text=_('ID from related system (purchase order, sale invoice, etc.)')
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Quantity'),
        help_text=_('Positive for IN, Negative for OUT')
    )
    unit_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Unit Cost'),
        null=True,
        blank=True
    )
    total_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Total Cost'),
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Stock Movement')
        verbose_name_plural = _('Stock Movements')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['warehouse', 'created_at']),
            models.Index(fields=['movement_type', 'created_at']),
            models.Index(fields=['batch', 'created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.movement_type} {self.quantity} {self.product.unit.symbol}"

    def clean(self):
        """Validate stock movement data"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        # Quantity should not be zero
        if self.quantity == 0:
            raise ValidationError(_('Quantity cannot be zero.'))
        
        # For IN movements, quantity should be positive
        if self.movement_type == 'IN' and self.quantity < 0:
            raise ValidationError(_('Stock IN quantity must be positive.'))
        
        # For OUT movements, quantity should be negative
        if self.movement_type == 'OUT' and self.quantity > 0:
            raise ValidationError(_('Stock OUT quantity must be negative.'))
        
        # If batch is provided, verify it belongs to the product
        if self.batch and self.batch.product_id != self.product_id:
            raise ValidationError(_('Batch does not belong to the specified product.'))
        
        # Calculate total cost if unit cost and quantity are provided
        if self.unit_cost is not None and self.quantity is not None:
            self.total_cost = (abs(self.quantity) * self.unit_cost).quantize(Decimal('0.01'))
        
        # For ADJUSTMENT movements, reference type should be MANUAL or similar
        if self.movement_type == 'ADJUSTMENT' and self.reference_type not in ['MANUAL', 'WASTE', 'EXPIRY']:
            # Not raising error, just noting - adjustments can have various reference types
            pass

    def save(self, *args, **kwargs):
        """
        Override save to ensure validation is called
        """
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Update batch remaining quantity after saving the movement
        if self.batch:
            self._update_batch_quantity()

    def _update_batch_quantity(self):
        """Update the batch's remaining quantity based on this movement"""
        from django.db import transaction
        
        # Skip recalculation for TRANSFER movements
        # Transfer movements manually manage the remaining quantity
        # so we don't want the automatic calculation to interfere
        if self.movement_type == 'TRANSFER':
            return
        
        # Calculate the net effect of all movements for this batch
        # Sum all IN, OUT, and TRANSFER quantities (positive adds, negative subtracts)
        total = StockMovement.objects.filter(
            batch=self.batch,
            is_active=True
        ).exclude(movement_type='TRANSFER').aggregate(total=models.Sum('quantity'))['total'] or 0
        
        # Update the batch's remaining quantity
        Batch.objects.filter(id=self.batch.id).update(remaining_quantity=total)


class Stock(TimeStampedUUIDModel):
    """
    Model representing stock levels for products at different locations (legacy)
    Kept for backward compatibility
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        verbose_name=_('Product')
    )
    location = models.CharField(max_length=255, verbose_name=_('Location'))
    batch_number = models.CharField(max_length=100, verbose_name=_('Batch Number'))
    expiry_date = models.DateField(verbose_name=_('Expiry Date'))
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Quantity')
    )
    unit_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_('Unit Cost')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Stock')
        verbose_name_plural = _('Stocks')
        ordering = ['product__name', 'expiry_date']
        unique_together = ['product', 'location', 'batch_number']

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit.symbol} (Batch: {self.batch_number})"


class WarehouseTransfer(TimeStampedUUIDModel):
    """
    Model for tracking warehouse-to-warehouse transfers.
    """
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('IN_TRANSIT', _('In Transit')),
        ('COMPLETED', _('Completed')),
        ('CANCELLED', _('Cancelled')),
    ]

    transfer_number = models.CharField(max_length=50, unique=True, verbose_name=_('Transfer Number'))
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
        verbose_name=_('Source Warehouse')
    )
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
        verbose_name=_('Destination Warehouse')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name=_('Status')
    )
    transfer_date = models.DateField(verbose_name=_('Transfer Date'))
    expected_arrival_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Expected Arrival Date')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='created_transfers',
        verbose_name=_('Created By')
    )

    class Meta:
        verbose_name = _('Warehouse Transfer')
        verbose_name_plural = _('Warehouse Transfers')
        ordering = ['-transfer_date', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['transfer_date']),
            models.Index(fields=['source_warehouse', 'destination_warehouse']),
        ]

    def __str__(self):
        return f"{self.transfer_number} - {self.source_warehouse.name} → {self.destination_warehouse.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.source_warehouse_id and self.destination_warehouse_id:
            if self.source_warehouse_id == self.destination_warehouse_id:
                raise ValidationError(_('Source and destination warehouses must be different.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class WarehouseTransferItem(TimeStampedUUIDModel):
    """
    Individual items in a warehouse transfer.
    """
    transfer = models.ForeignKey(
        WarehouseTransfer,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Transfer')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name=_('Product')
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Batch (Optional)')
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Quantity')
    )
    quantity_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Quantity Received')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Transfer Item')
        verbose_name_plural = _('Transfer Items')
        unique_together = ['transfer', 'product', 'batch']
        ordering = ['transfer', 'product__name']

    def __str__(self):
        batch_info = f" (Batch: {self.batch.batch_number})" if self.batch else ""
        return f"{self.transfer.transfer_number} - {self.product.name}{batch_info}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity <= 0:
            raise ValidationError(_('Quantity must be positive.'))
        if self.quantity_received < 0:
            raise ValidationError(_('Quantity received cannot be negative.'))
        if self.quantity_received > self.quantity:
            raise ValidationError(_('Quantity received cannot exceed quantity transferred.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
import django_filters
from django.db import models
from .models import Product, Batch, Warehouse, StockMovement


class ProductFilter(django_filters.FilterSet):
    """
    Advanced filtering for Product model
    """
    # Barcode search
    barcode = django_filters.CharFilter(lookup_expr='icontains')
    # Generic name search
    generic_name = django_filters.CharFilter(lookup_expr='icontains')
    # Brand name search
    brand_name = django_filters.CharFilter(lookup_expr='icontains')
    # Manufacturer search
    manufacturer = django_filters.CharFilter(lookup_expr='icontains')
    # Category name search
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    # Unit name search
    unit_name = django_filters.CharFilter(field_name='unit__name', lookup_expr='icontains')
    # Is active
    is_active = django_filters.BooleanFilter()
    # Requires prescription
    requires_prescription = django_filters.BooleanFilter()
    # Controlled substance
    is_controlled_substance = django_filters.BooleanFilter()

    class Meta:
        model = Product
        fields = [
            'barcode', 'generic_name', 'brand_name', 'manufacturer',
            'category_name', 'unit_name', 'is_active', 'requires_prescription',
            'is_controlled_substance'
        ]


class BatchFilter(django_filters.FilterSet):
    """
    Advanced filtering for Batch model
    """
    # Batch number search
    batch_number = django_filters.CharFilter(lookup_expr='icontains')
    # Product name search
    product_name = django_filters.CharFilter(field_name='product__name', lookup_expr='icontains')
    # Product generic name search
    product_generic_name = django_filters.CharFilter(field_name='product__generic_name', lookup_expr='icontains')
    # Product brand name search
    product_brand_name = django_filters.CharFilter(field_name='product__brand_name', lookup_expr='icontains')
    # Barcode search (through product)
    barcode = django_filters.CharFilter(field_name='product__barcode', lookup_expr='icontains')
    # SKU search (through product)
    sku = django_filters.CharFilter(field_name='product__sku', lookup_expr='icontains')
    # Manufacturing date range
    manufacturing_date_after = django_filters.DateFilter(field_name='manufacturing_date', lookup_expr='gte')
    manufacturing_date_before = django_filters.DateFilter(field_name='manufacturing_date', lookup_expr='lte')
    # Expiry date range
    expiry_date_after = django_filters.DateFilter(field_name='expiry_date', lookup_expr='gte')
    expiry_date_before = django_filters.DateFilter(field_name='expiry_date', lookup_expr='lte')
    # Quantity range
    minimum_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    maximum_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='lte')
    # Remaining quantity range
    minimum_remaining = django_filters.NumberFilter(field_name='remaining_quantity', lookup_expr='gte')
    maximum_remaining = django_filters.NumberFilter(field_name='remaining_quantity', lookup_expr='lte')
    # Location
    location = django_filters.CharFilter(lookup_expr='icontains')
    # Is active
    is_active = django_filters.BooleanFilter()
    # Is expired
    is_expired = django_filters.BooleanFilter(method='filter_is_expired')
    # Is expiring soon (within 30 days)
    is_expiring_soon = django_filters.BooleanFilter(method='filter_is_expiring_soon')

    class Meta:
        model = Batch
        fields = [
            'batch_number', 'product_name', 'product_generic_name', 'product_brand_name',
            'barcode', 'sku', 'manufacturing_date_after', 'manufacturing_date_before',
            'expiry_date_after', 'expiry_date_before', 'minimum_quantity', 'maximum_quantity',
            'minimum_remaining', 'maximum_remaining', 'location', 'is_active',
            'is_expired', 'is_expiring_soon'
        ]

    def filter_is_expired(self, queryset, name, value):
        from django.utils import timezone
        today = timezone.now().date()
        if value:
            return queryset.filter(expiry_date__lt=today)
        else:
            return queryset.filter(expiry_date__gte=today)

    def filter_is_expiring_soon(self, queryset, name, value):
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now().date()
        threshold_date = today + timedelta(days=30)
        if value:
            return queryset.filter(
                expiry_date__gte=today,
                expiry_date__lte=threshold_date
            )
        else:
            return queryset.filter(
                models.Q(expiry_date__lt=today) | models.Q(expiry_date__gt=threshold_date)
            )


class WarehouseFilter(django_filters.FilterSet):
    """
    Advanced filtering for Warehouse model
    """
    # Name search
    name = django_filters.CharFilter(lookup_expr='icontains')
    # Code search
    code = django_filters.CharFilter(lookup_expr='icontains')
    # Address search
    address = django_filters.CharFilter(lookup_expr='icontains')
    # Contact person search
    contact_person = django_filters.CharFilter(lookup_expr='icontains')
    # Is active
    is_active = django_filters.BooleanFilter()
    # Is default
    is_default = django_filters.BooleanFilter()

    class Meta:
        model = Warehouse
        fields = ['name', 'code', 'address', 'contact_person', 'is_active', 'is_default']


class StockMovementFilter(django_filters.FilterSet):
    """
    Advanced filtering for StockMovement model
    """
    # Product search
    product_name = django_filters.CharFilter(field_name='product__name', lookup_expr='icontains')
    product_generic_name = django_filters.CharFilter(field_name='product__generic_name', lookup_expr='icontains')
    product_brand_name = django_filters.CharFilter(field_name='product__brand_name', lookup_expr='icontains')
    # Batch search
    batch_number = django_filters.CharFilter(field_name='batch__batch_number', lookup_expr='icontains')
    # Warehouse search
    warehouse_name = django_filters.CharFilter(field_name='warehouse__name', lookup_expr='icontains')
    warehouse_code = django_filters.CharFilter(field_name='warehouse__code', lookup_expr='icontains')
    # Movement type
    movement_type = django_filters.MultipleChoiceFilter(choices=StockMovement.MOVEMENT_TYPES)
    # Reference type
    reference_type = django_filters.MultipleChoiceFilter(choices=StockMovement.REFERENCE_TYPES)
    # Reference ID
    reference_id = django_filters.CharFilter(lookup_expr='icontains')
    # Date range
    date_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    # Quantity range
    minimum_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    maximum_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='lte')
    # Notes search
    notes = django_filters.CharFilter(lookup_expr='icontains')
    # Is active
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = StockMovement
        fields = [
            'product_name', 'product_generic_name', 'product_brand_name',
            'batch_number', 'warehouse_name', 'warehouse_code',
            'movement_type', 'reference_type', 'reference_id',
            'date_after', 'date_before', 'minimum_quantity', 'maximum_quantity',
            'notes', 'is_active'
        ]
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from core.multitenant.views import CompanyScopedViewSetMixin
from .models import Category, Unit, Product, Batch, Warehouse, StockMovement
from .serializers.product_serializers import CategorySerializer, UnitSerializer, ProductSerializer
from .serializers.batch_serializers import BatchSerializer
from .serializers.warehouse_serializers import WarehouseSerializer, StockMovementSerializer
from .filters import ProductFilter, BatchFilter, WarehouseFilter, StockMovementFilter
from security.permissions import RoleBasedPermission


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Category CRUD.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # We'll keep the simple filtering for Category for now
    # Could enhance later if needed
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """
        Optionally filter by active status and parent category
        """
        queryset = Category.objects.all()
        is_active = self.request.query_params.get('is_active', None)
        parent = self.request.query_params.get('parent', None)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if parent is not None:
            if parent == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent)
                
        return queryset


class UnitViewSet(viewsets.ModelViewSet):
    """Unit of measure CRUD."""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'symbol', 'description']
    ordering_fields = ['name', 'symbol', 'created_at']
    ordering = ['name']


class ProductViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    Product CRUD with filtering and search.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'generic_name', 'brand_name', 'barcode', 'sku', 'manufacturer']
    ordering_fields = ['name', 'generic_name', 'brand_name', 'created_at']
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        Get products with low stock levels (below threshold)
        """
        threshold = request.query_params.get('threshold', 10)
        try:
            threshold = int(threshold)
        except ValueError:
            threshold = 10
        
        # Get batches with remaining quantity below threshold
        low_stock_batches = Batch.objects.filter(
            remaining_quantity__lt=threshold,
            is_active=True
        ).select_related('product', 'product__category', 'product__unit')
        
        # Group by product to avoid duplicates
        products = {}
        for batch in low_stock_batches:
            product_id = batch.product.id
            if product_id not in products:
                products[product_id] = {
                    'product': batch.product,
                    'batches': [],
                    'total_remaining': 0
                }
            products[product_id]['batches'].append(batch)
            products[product_id]['total_remaining'] += batch.remaining_quantity
        
        # Serialize the data
        result = []
        for product_data in products.values():
            product_serializer = ProductSerializer(product_data['product'])
            batch_serializer = BatchSerializer(product_data['batches'], many=True)
            result.append({
                'product': product_serializer.data,
                'batches': batch_serializer.data,
                'total_remaining_quantity': product_data['total_remaining']
            })
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Get expired products
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        expired_batches = Batch.objects.filter(
            expiry_date__lt=today,
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product', 'product__category', 'product__unit')
        
        # Group by product
        products = {}
        for batch in expired_batches:
            product_id = batch.product.id
            if product_id not in products:
                products[product_id] = {
                    'product': batch.product,
                    'batches': [],
                    'total_expired_quantity': 0
                }
            products[product_id]['batches'].append(batch)
            products[product_id]['total_expired_quantity'] += batch.remaining_quantity
        
        # Serialize the data
        result = []
        for product_data in products.values():
            product_serializer = ProductSerializer(product_data['product'])
            batch_serializer = BatchSerializer(product_data['batches'], many=True)
            result.append({
                'product': product_serializer.data,
                'batches': batch_serializer.data,
                'total_expired_quantity': product_data['total_expired_quantity']
            })
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Get products expiring soon (within threshold days)
        """
        threshold_days = request.query_params.get('days', 30)
        try:
            threshold_days = int(threshold_days)
        except ValueError:
            threshold_days = 30
        
        from django.utils import timezone
        today = timezone.now().date()
        from datetime import timedelta
        threshold_date = today + timedelta(days=threshold_days)
        
        expiring_batches = Batch.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=threshold_date,
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product', 'product__category', 'product__unit')
        
        # Group by product
        products = {}
        for batch in expiring_batches:
            product_id = batch.product.id
            if product_id not in products:
                products[product_id] = {
                    'product': batch.product,
                    'batches': [],
                    'total_expiring_quantity': 0
                }
            products[product_id]['batches'].append(batch)
            products[product_id]['total_expiring_quantity'] += batch.remaining_quantity
        
        # Serialize the data
        result = []
        for product_data in products.values():
            product_serializer = ProductSerializer(product_data['product'])
            batch_serializer = BatchSerializer(product_data['batches'], many=True)
            result.append({
                'product': product_serializer.data,
                'batches': batch_serializer.data,
                'total_expiring_quantity': product_data['total_expiring_quantity']
            })
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        """
        Look up product by barcode
        """
        barcode = request.query_params.get('barcode', '')
        
        if not barcode:
            return Response(
                {'error': 'Barcode parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(barcode=barcode, is_active=True)
            serializer = ProductSerializer(product)
            
            # Also get available batches for this product
            batches = Batch.objects.filter(
                product=product,
                remaining_quantity__gt=0,
                is_active=True
            ).select_related('warehouse')
            
            batch_serializer = BatchSerializer(batches, many=True)
            
            return Response({
                'product': serializer.data,
                'batches': batch_serializer.data,
                'total_stock': sum(b.remaining_quantity for b in batches)
            })
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found', 'barcode': barcode},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def by_sku(self, request):
        """
        Look up product by SKU
        """
        sku = request.query_params.get('sku', '')
        
        if not sku:
            return Response(
                {'error': 'SKU parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(sku=sku, is_active=True)
            serializer = ProductSerializer(product)
            
            batches = Batch.objects.filter(
                product=product,
                remaining_quantity__gt=0,
                is_active=True
            ).select_related('warehouse')
            
            batch_serializer = BatchSerializer(batches, many=True)
            
            return Response({
                'product': serializer.data,
                'batches': batch_serializer.data,
                'total_stock': sum(b.remaining_quantity for b in batches)
            })
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found', 'sku': sku},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def generate_barcode(self, request):
        """
        Generate barcode image for a product.
        Query params: barcode (or sku), format (ean13, code128, code39, qr)
        """
        from inventory.services.barcode_generator import (
            BarcodeGenerator,
            BarcodeFormat,
            BarcodeGenerationError,
        )

        code = request.query_params.get('barcode') or request.query_params.get('sku', '')
        fmt = request.query_params.get('format', BarcodeFormat.CODE128)
        include_text = request.query_params.get('text', 'true').lower() == 'true'

        if not code:
            return Response(
                {'error': 'barcode or sku parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            b64 = BarcodeGenerator.generate(code, fmt=fmt, include_text=include_text)
            return Response({
                'success': True,
                'barcode': code,
                'format': fmt,
                'image_base64': b64,
            })
        except BarcodeGenerationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def validate_barcode(self, request):
        """
        Validate a barcode checksum (EAN-13).
        """
        from inventory.services.barcode_generator import BarcodeGenerator

        code = request.query_params.get('barcode', '')
        fmt = request.query_params.get('format', '')

        if not code:
            return Response(
                {'error': 'barcode parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if fmt.lower() == 'ean13':
            is_valid = BarcodeGenerator.validate_ean13(code)
            return Response({'valid': is_valid, 'format': 'ean13', 'barcode': code})

        return Response({'valid': True, 'format': fmt, 'barcode': code, 'note': 'Validation only for EAN-13'})


class BatchViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    Batch CRUD with filtering.
    """
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BatchFilter
    search_fields = ['batch_number', 'product__name', 'product__generic_name', 'product__brand_name']
    ordering_fields = ['expiry_date', 'manufacturing_date', 'created_at']
    ordering = ['expiry_date']  # Default order by expiry date (FEFO)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Get expired batches
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        expired_batches = self.get_queryset().filter(
            expiry_date__lt=today,
            remaining_quantity__gt=0
        )
        
        page = self.paginate_queryset(expired_batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(expired_batches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Get batches expiring soon (within threshold days)
        """
        threshold_days = request.query_params.get('days', 30)
        try:
            threshold_days = int(threshold_days)
        except ValueError:
            threshold_days = 30
        
        from django.utils import timezone
        today = timezone.now().date()
        from datetime import timedelta
        threshold_date = today + timedelta(days=threshold_days)
        
        expiring_batches = self.get_queryset().filter(
            expiry_date__gte=today,
            expiry_date__lte=threshold_date,
            remaining_quantity__gt=0
        )
        
        page = self.paginate_queryset(expiring_batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(expiring_batches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def fifo_order(self, request):
        """
        Get batches in FIFO order (manufacturing date ascending)
        """
        fifo_batches = self.get_queryset().filter(
            remaining_quantity__gt=0
        ).order_by('manufacturing_date')
        
        page = self.paginate_queryset(fifo_batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(fifo_batches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def fefo_order(self, request):
        """
        Get batches in FEFO order (expiry date ascending)
        """
        fefo_batches = self.get_queryset().filter(
            remaining_quantity__gt=0
        ).order_by('expiry_date')
        
        page = self.paginate_queryset(fefo_batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(fefo_batches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_batch_barcode(self, request):
        """
        Look up batch by its barcode or batch_number.
        Returns batch + product info for POS scanning.
        """
        barcode = request.query_params.get('barcode', '')

        if not barcode:
            return Response(
                {'error': 'barcode parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from django.db.models import Q
            batch = Batch.objects.select_related('product').get(
                Q(barcode=barcode) | Q(batch_number=barcode),
                remaining_quantity__gt=0,
                is_active=True,
            )
            batch_serializer = BatchSerializer(batch)
            product_serializer = ProductSerializer(batch.product)

            return Response({
                'batch': batch_serializer.data,
                'product': product_serializer.data,
                'source': 'batch_barcode',
            })
        except Batch.DoesNotExist:
            return Response(
                {'error': 'Batch not found', 'barcode': barcode},
                status=status.HTTP_404_NOT_FOUND,
            )


class WarehouseViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    Warehouse CRUD.
    """
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = WarehouseFilter
    search_fields = ['name', 'code', 'address', 'contact_person']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """
        Optionally filter by active status and default warehouse
        """
        queryset = Warehouse.objects.all()
        is_active = self.request.query_params.get('is_active', None)
        is_default = self.request.query_params.get('is_default', None)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if is_default is not None:
            queryset = queryset.filter(is_default=is_default.lower() == 'true')
            
        return queryset

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        Get the default warehouse
        """
        default_warehouse = Warehouse.objects.filter(is_default=True, is_active=True).first()
        if default_warehouse:
            serializer = self.get_serializer(default_warehouse)
            return Response(serializer.data)
        return Response({"detail": "No default warehouse found"}, status=404)


class StockMovementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing stock movements
    """
    queryset = StockMovement.objects.select_related(
        'product', 'product__category', 'product__unit',
        'batch',
        'warehouse'
    ).all()
    serializer_class = StockMovementSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StockMovementFilter
    search_fields = ['product__name', 'product__generic_name', 'product__brand_name', 'batch__batch_number', 'warehouse__name', 'reference_id', 'notes']
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']  # Most recent first

    @action(detail=False, methods=['get'])
    def stock_in(self, request):
        """
        Get stock in movements
        """
        movements = self.get_queryset().filter(movement_type='IN')
        
        page = self.paginate_queryset(movements)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stock_out(self, request):
        """
        Get stock out movements
        """
        movements = self.get_queryset().filter(movement_type='OUT')
        
        page = self.paginate_queryset(movements)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def adjustments(self, request):
        """
        Get adjustment movements
        """
        movements = self.get_queryset().filter(movement_type='ADJUSTMENT')
        
        page = self.paginate_queryset(movements)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data)
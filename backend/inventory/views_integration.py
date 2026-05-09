from decimal import Decimal
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from inventory.models import Product, Warehouse, Batch
from inventory.service import StockIntegrationService, StockSelectionMode


class StockAllocationRequestSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)
    selection_mode = serializers.ChoiceField(
        choices=['FEFO', 'FIFO'], default='FEFO'
    )
    batch_id = serializers.UUIDField(required=False, allow_null=True)


class SaleProcessingRequestSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()
    items = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of items with product_id, quantity, and optional batch_id'
    )
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)
    selection_mode = serializers.ChoiceField(
        choices=['FEFO', 'FIFO'], default='FEFO'
    )


class PurchaseProcessingRequestSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()
    items = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of items with product_id, quantity, batch_number, expiry_date, unit_price'
    )
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)


@api_view(['POST'])
def allocate_stock(request):
    """
    Allocate stock for a sale without committing the transaction.
    Useful for checking availability before finalizing a sale.
    
    Request body:
    {
        "product_id": "uuid",
        "quantity": 100,
        "warehouse_id": "uuid",
        "selection_mode": "FEFO"
    }
    """
    serializer = StockAllocationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated = serializer.validated_data
    
    try:
        product = Product.objects.get(id=validated['product_id'])
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    warehouse = None
    if validated.get('warehouse_id'):
        try:
            warehouse = Warehouse.objects.get(id=validated['warehouse_id'])
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
    
    selection_mode = StockSelectionMode(validated['selection_mode'])
    
    result = StockIntegrationService.allocate_stock(
        product=product,
        quantity=validated['quantity'],
        warehouse=warehouse,
        selection_mode=selection_mode,
        batch_id=validated.get('batch_id')
    )
    
    response_data = {
        'success': result.success,
        'message': result.message,
        'allocations': [
            {
                'batch_id': str(a.batch_id),
                'batch_number': a.batch_number,
                'quantity': a.quantity,
                'expiry_date': a.expiry_date.isoformat() if a.expiry_date else None,
                'unit_cost': a.unit_cost,
            }
            for a in result.allocations
        ],
        'shortages': result.stock_shortages,
    }
    
    return Response(response_data)


@api_view(['POST'])
def process_sale_stock(request):
    """
    Process stock deduction for a sales invoice.
    This should be called when a sales invoice is dispatched.
    
    Request body:
    {
        "invoice_id": "uuid",
        "items": [
            {"product_id": "uuid", "quantity": 100, "batch_id": "uuid"},
            {"product_id": "uuid", "quantity": 50}
        ],
        "warehouse_id": "uuid",
        "selection_mode": "FEFO"
    }
    """
    serializer = SaleProcessingRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated = serializer.validated_data
    
    # Parse items
    items = []
    for item_data in validated['items']:
        try:
            product = Product.objects.get(id=item_data['product_id'])
        except Product.DoesNotExist:
            return Response(
                {'error': f"Product {item_data['product_id']} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        items.append({
            'product': product,
            'quantity': Decimal(str(item_data['quantity'])),
            'batch_id': item_data.get('batch_id'),
        })
    
    warehouse = None
    if validated.get('warehouse_id'):
        try:
            warehouse = Warehouse.objects.get(id=validated['warehouse_id'])
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
    
    selection_mode = StockSelectionMode(validated['selection_mode'])
    
    result = StockIntegrationService.process_sale(
        invoice_id=validated['invoice_id'],
        items=items,
        warehouse=warehouse,
        selection_mode=selection_mode
    )
    
    response_data = {
        'success': result.success,
        'message': result.message,
        'movements': result.movements,
        'allocations': [
            {
                'batch_id': str(a.batch_id),
                'batch_number': a.batch_number,
                'quantity': a.quantity,
                'expiry_date': a.expiry_date.isoformat() if a.expiry_date else None,
                'warehouse': a.warehouse_name,
                'unit_cost': a.unit_cost,
            }
            for a in result.allocations
        ],
        'errors': result.errors,
        'warnings': result.warnings,
        'stock_shortages': result.stock_shortages,
    }
    
    status_code = status.HTTP_200_OK if result.success else status.HTTP_400_BAD_REQUEST
    return Response(response_data, status=status_code)


@api_view(['POST'])
def process_purchase_stock(request):
    """
    Process stock addition from a purchase invoice.
    This should be called when a purchase invoice is received.
    
    Request body:
    {
        "invoice_id": "uuid",
        "items": [
            {
                "product_id": "uuid",
                "quantity": 100,
                "batch_number": "BATCH001",
                "expiry_date": "2025-12-31",
                "unit_price": 50.00,
                "manufacturing_date": "2024-01-01"
            }
        ],
        "warehouse_id": "uuid"
    }
    """
    serializer = PurchaseProcessingRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated = serializer.validated_data
    
    # Parse items
    items = []
    for item_data in validated['items']:
        try:
            product = Product.objects.get(id=item_data['product_id'])
        except Product.DoesNotExist:
            return Response(
                {'error': f"Product {item_data['product_id']} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        items.append({
            'product': product,
            'quantity': Decimal(str(item_data['quantity'])),
            'batch_number': item_data['batch_number'],
            'expiry_date': item_data['expiry_date'],
            'unit_price': Decimal(str(item_data['unit_price'])),
            'manufacturing_date': item_data.get('manufacturing_date'),
        })
    
    warehouse = None
    if validated.get('warehouse_id'):
        try:
            warehouse = Warehouse.objects.get(id=validated['warehouse_id'])
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
    
    result = StockIntegrationService.process_purchase(
        invoice_id=validated['invoice_id'],
        items=items,
        warehouse=warehouse
    )
    
    response_data = {
        'success': result.success,
        'message': result.message,
        'movements': result.movements,
        'errors': result.errors,
        'warnings': result.warnings,
    }
    
    status_code = status.HTTP_200_OK if result.success else status.HTTP_400_BAD_REQUEST
    return Response(response_data, status=status_code)


@api_view(['GET'])
def check_stock_availability(request):
    """
    Check stock availability for products.
    
    Query params:
    - product_id: UUID of product (required, or use product_ids)
    - product_ids: Comma-separated UUIDs of products
    - quantity: Required quantity (default: 1)
    - warehouse_id: Optional warehouse filter
    """
    product_id = request.query_params.get('product_id')
    product_ids = request.query_params.get('product_ids')
    quantity = request.query_params.get('quantity', '1')
    warehouse_id = request.query_params.get('warehouse_id')
    
    warehouse = None
    if warehouse_id:
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if product_id:
        products = [Product.objects.get(id=product_id)]
    elif product_ids:
        products = list(Product.objects.filter(id__in=product_ids.split(',')))
    else:
        return Response(
            {'error': 'product_id or product_ids parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    items = [{'product': p, 'quantity': Decimal(quantity)} for p in products]
    results = StockIntegrationService.check_stock_availability(items, warehouse)
    
    return Response(results)


@api_view(['GET'])
def get_stock_levels(request):
    """
    Get current stock levels.
    
    Query params:
    - product_id: Optional product filter
    - warehouse_id: Optional warehouse filter
    - include_expired: Whether to include expired batches (default: false)
    """
    product_id = request.query_params.get('product_id')
    warehouse_id = request.query_params.get('warehouse_id')
    include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'
    
    product = None
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    warehouse = None
    if warehouse_id:
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
    
    levels = StockIntegrationService.get_stock_levels(product, warehouse, include_expired)
    
    return Response(levels)


@api_view(['GET'])
def get_available_batches(request, product_id):
    """
    Get available batches for a product.
    
    Query params:
    - warehouse_id: Optional warehouse filter
    - selection_mode: FEFO or FIFO (default: FEFO)
    - exclude_expired: Whether to exclude expired batches (default: true)
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    warehouse_id = request.query_params.get('warehouse_id')
    selection_mode = request.query_params.get('selection_mode', 'FEFO')
    exclude_expired = request.query_params.get('exclude_expired', 'true').lower() == 'true'
    
    warehouse = None
    if warehouse_id:
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            return Response({'error': 'Warehouse not found'}, status=status.HTTP_404_NOT_FOUND)
    
    batches = StockIntegrationService.get_available_batches(
        product, warehouse, exclude_expired, StockSelectionMode(selection_mode)
    )
    
    batch_data = []
    for batch in batches:
        batch_data.append({
            'id': batch.id,
            'batch_number': batch.batch_number,
            'remaining_quantity': batch.remaining_quantity,
            'expiry_date': batch.expiry_date.isoformat(),
            'manufacturing_date': batch.manufacturing_date.isoformat(),
            'purchase_price': batch.purchase_price,
            'sale_price': batch.sale_price,
            'location': batch.location,
            'is_expired': batch.is_expired,
            'days_until_expiry': batch.days_until_expiry,
        })
    
    return Response(batch_data)

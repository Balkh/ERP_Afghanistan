"""
Warehouse Transfer service methods.
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from inventory.models import WarehouseTransfer, WarehouseTransferItem, Batch, StockMovement, Product
from inventory.service.types import StockOperationResult


def process_transfer(
    transfer_id,
    items,
    warehouse=None,
    reference_type='MANUAL'
) -> StockOperationResult:
    """
    Process a warehouse transfer (move items from one warehouse to another).
    
    Args:
        transfer_id: Transfer ID or WarehouseTransfer instance
        items: List of dicts with keys:
            - product: Product instance or ID
            - quantity: Decimal quantity to transfer
            - batch_id: (Optional) Specific batch ID
        warehouse: Optional warehouse (for backward compatibility)
        reference_type: Type of transfer reference
        
    Returns:
        StockOperationResult with movements or errors
    """
    result = StockOperationResult(success=False, message='')
    all_movements = []
    
    try:
        if hasattr(transfer_id, 'id'):
            transfer = transfer_id
        else:
            transfer = WarehouseTransfer.objects.get(id=transfer_id)
        
        if transfer.status not in ['PENDING', 'IN_TRANSIT']:
            result.errors.append(f'Cannot process transfer with status {transfer.status}')
            return result
        
        with transaction.atomic():
            transfer = WarehouseTransfer.objects.select_for_update().get(id=transfer.id)
            
            for item in items:
                product = item['product']
                quantity = Decimal(str(item['quantity']))
                batch_id = item.get('batch_id')
                
                if quantity <= 0:
                    result.errors.append(f'Invalid quantity for product {product}')
                    result.success = False
                    continue
                
                product_obj = product if hasattr(product, 'id') else Product.objects.get(id=product)
                if batch_id:
                    batch = Batch.objects.select_for_update().get(id=batch_id)
                else:
                    batches = Batch.objects.select_for_update().filter(
                        product=product_obj,
                        remaining_quantity__gt=0,
                        location=str(transfer.source_warehouse.id),
                        is_active=True
                    ).order_by('expiry_date')
                    batch = batches.first()
                
                if not batch:
                    result.errors.append(f'No available batch for product {product_obj.name}')
                    result.success = False
                    continue
                
                if batch.remaining_quantity < quantity:
                    result.errors.append(f'Insufficient stock for {product_obj.name} in source warehouse')
                    result.success = False
                    continue
                
                out_movement = StockMovement.objects.create(
                    product=product_obj,
                    batch=batch,
                    warehouse=transfer.source_warehouse,
                    movement_type='TRANSFER',
                    reference_type=reference_type,
                    reference_id=str(transfer.id),
                    quantity=-quantity,
                    unit_cost=batch.purchase_price,
                    notes=f'Transfer {transfer.transfer_number} - OUT'
                )
                
                batch.remaining_quantity -= quantity
                batch.save(update_fields=['remaining_quantity'])
                
                in_movement = StockMovement.objects.create(
                    product=product_obj,
                    batch=batch,
                    warehouse=transfer.destination_warehouse,
                    movement_type='TRANSFER',
                    reference_type=reference_type,
                    reference_id=str(transfer.id),
                    quantity=quantity,
                    unit_cost=batch.purchase_price,
                    notes=f'Transfer {transfer.transfer_number} - IN'
                )
                
                dest_batch = Batch.objects.select_for_update().filter(
                    product=product_obj,
                    batch_number=batch.batch_number,
                    location=str(transfer.destination_warehouse.id)
                ).first()
                
                if dest_batch:
                    dest_batch.remaining_quantity += quantity
                    dest_batch.save(update_fields=['remaining_quantity'])
                else:
                    Batch.objects.create(
                        product=product_obj,
                        batch_number=f"{batch.batch_number}-{transfer.destination_warehouse.code}",
                        manufacturing_date=batch.manufacturing_date,
                        expiry_date=batch.expiry_date,
                        purchase_price=batch.purchase_price,
                        sale_price=batch.sale_price,
                        quantity=quantity,
                        remaining_quantity=quantity,
                        location=str(transfer.destination_warehouse.id),
                        is_active=True
                    )
                
                all_movements.extend([out_movement.id, in_movement.id])
            
            if not result.errors:
                transfer.status = 'COMPLETED'
                transfer.save(update_fields=['status'])
                result.success = True
                result.message = 'Transfer completed successfully'
        
    except Exception as e:
        result.errors.append(str(e))
        result.success = False
    
    result.movements = all_movements
    return result
from decimal import Decimal
from datetime import date, timezone
from typing import Optional, Union
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

from inventory.models import Batch, StockMovement, Warehouse, Product, WarehouseTransfer, WarehouseTransferItem
from inventory.service import StockSelectionMode, StockAllocation, StockOperationResult


class StockIntegrationService:
    """
    Service for integrating inventory with sales and purchases.
    
    Handles:
    - Automatic stock deduction on sales
    - Purchase stock addition
    - FEFO/FIFO stock selection
    - Transactional inventory operations
    - Stock availability checking
    - Batch allocation
    - Warehouse transfers
    """
    
    # [Previous methods remain unchanged - get_available_batches, allocate_stock, etc.]
    # ... existing code ...
    
    @staticmethod
    def process_transfer(
        transfer_id: any,
        items: list[dict],
        warehouse: Optional[Union[Warehouse, any]] = None,
        reference_type: str = 'MANUAL'
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
            # Get the transfer
            if hasattr(transfer_id, 'id'):
                transfer = transfer_id
            else:
                transfer = WarehouseTransfer.objects.get(id=transfer_id)
            
            # Validate transfer status
            if transfer.status not in ['PENDING', 'IN_TRANSIT']:
                result.errors.append(f'Cannot process transfer with status {transfer.status}')
                return result
            
            with transaction.atomic():
                for item in items:
                    product = item['product']
                    quantity = Decimal(str(item['quantity']))
                    batch_id = item.get('batch_id')
                    
                    if quantity <= 0:
                        result.errors.append(f'Invalid quantity for product {product}')
                        result.success = False
                        continue
                    
                    # Get product and batch
                    product_obj = product if hasattr(product, 'id') else Product.objects.get(id=product)
                    batch = None
                    if batch_id:
                        batch = Batch.objects.select_for_update().get(id=batch_id)
                    else:
                        # Find batch in source warehouse
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
                    
                    # Create OUT movement (from source warehouse)
                    out_movement = StockMovement.objects.create(
                        product=product_obj,
                        batch=batch,
                        warehouse=transfer.source_warehouse,
                        movement_type='TRANSFER',
                        reference_type=reference_type,
                        reference_id=str(transfer.id),
                        quantity=-quantity,  # Negative for OUT
                        unit_cost=batch.purchase_price,
                        notes=f'Transfer {transfer.transfer_number} - OUT'
                    )
                    
                    # Update batch quantity in source warehouse
                    batch.remaining_quantity -= quantity
                    batch.save(update_fields=['remaining_quantity'])
                    
                    # Create IN movement (to destination warehouse)
                    in_movement = StockMovement.objects.create(
                        product=product_obj,
                        batch=batch,
                        warehouse=transfer.destination_warehouse,
                        movement_type='TRANSFER',
                        reference_type=reference_type,
                        reference_id=str(transfer.id),
                        quantity=quantity,  # Positive for IN
                        unit_cost=batch.purchase_price,
                        notes=f'Transfer {transfer.transfer_number} - IN'
                    )
                    
                    # Update or create batch in destination warehouse
                    dest_batch = Batch.objects.filter(
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
                            batch_number=batch.batch_number,
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
                
                # Update transfer status
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

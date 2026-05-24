from decimal import Decimal
from datetime import date, timezone
from typing import Optional, Union
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

from inventory.models import Batch, StockMovement, Warehouse, Product, WarehouseTransfer
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
    """

    @staticmethod
    def get_available_batches(
        product: Union[Product, any],
        warehouse: Optional[Union[Warehouse, any]] = None,
        exclude_expired: bool = True,
        selection_mode: StockSelectionMode = StockSelectionMode.FEFO
    ):
        """
        Get available batches for a product, sorted by selection mode.
        
        Args:
            product: Product instance or ID
            warehouse: Optional warehouse filter
            exclude_expired: Whether to exclude expired batches
            selection_mode: FEFO or FIFO
            
        Returns:
            QuerySet of available batches
        """
        product_id = product.id if hasattr(product, 'id') else product
        
        batches = Batch.objects.filter(
            product_id=product_id,
            remaining_quantity__gt=0,
            is_active=True
        )
        
        if warehouse:
            warehouse_id = warehouse.id if hasattr(warehouse, 'id') else warehouse
            batches = batches.filter(location=str(warehouse_id))
        
        if exclude_expired:
            batches = batches.filter(expiry_date__gte=django_timezone.now().date())
        
        # Sort by selection mode
        if selection_mode == StockSelectionMode.FEFO:
            # First Expiry, First Out - sort by expiry date ascending
            # Tie-breaker: manufacturing_date, then batch_number (alphabetical) for determinism
            batches = batches.order_by('expiry_date', 'manufacturing_date', 'batch_number', 'id')
        else:
            # First In, First Out - sort by manufacturing date ascending
            # Tie-breaker: expiry_date, then batch_number (alphabetical)
            batches = batches.order_by('manufacturing_date', 'expiry_date', 'batch_number', 'id')
        
        return batches

    @staticmethod
    def allocate_stock(
        product: Union[Product, any],
        quantity: Decimal,
        warehouse: Optional[Union[Warehouse, any]] = None,
        selection_mode: StockSelectionMode = StockSelectionMode.FEFO,
        batch_id: Optional[any] = None
    ) -> StockOperationResult:
        """
        Allocate stock for a sale using FEFO/FIFO selection.
        
        Args:
            product: Product instance or ID
            quantity: Quantity to allocate
            warehouse: Optional warehouse to allocate from
            selection_mode: FEFO or FIFO
            batch_id: Optional specific batch to allocate from
            
        Returns:
            StockOperationResult with allocations or errors
        """
        result = StockOperationResult(success=False, message='')
        remaining_to_allocate = quantity
        
        # Get available batches
        if batch_id:
            # Allocate from specific batch
            batches = Batch.objects.select_for_update().filter(
                id=batch_id,
                remaining_quantity__gt=0,
                is_active=True
            )
        else:
            batches = StockIntegrationService.get_available_batches(
                product, warehouse, exclude_expired=True, selection_mode=selection_mode
            ).select_for_update()
        
        if not batches.exists():
            result.errors.append(f'No available stock for product {product}')
            return result
        
        allocations = []
        
        for batch in batches:
            if remaining_to_allocate <= 0:
                break
            
            available = batch.remaining_quantity
            allocate_from_batch = min(available, remaining_to_allocate)
            
            allocations.append(StockAllocation(
                batch_id=batch.id,
                batch_number=batch.batch_number,
                product_id=batch.product_id,
                product_name=str(batch.product),
                quantity=allocate_from_batch,
                expiry_date=batch.expiry_date,
                warehouse_id=warehouse.id if warehouse else None,
                warehouse_name=str(warehouse) if warehouse else 'Default',
                unit_cost=batch.purchase_price
            ))
            
            remaining_to_allocate -= allocate_from_batch
        
        if remaining_to_allocate > 0:
            result.success = False
            result.message = f'Insufficient stock. Shortage: {remaining_to_allocate}'
            result.allocations = allocations
            result.stock_shortages.append({
                'product': str(product),
                'requested': quantity,
                'allocated': quantity - remaining_to_allocate,
                'shortage': remaining_to_allocate,
            })
            return result
        
        result.success = True
        result.message = f'Successfully allocated {quantity} units'
        result.allocations = allocations
        return result

    @staticmethod
    @transaction.atomic
    def process_sale(
        invoice_id: any,
        items: list[dict],
        warehouse: Optional[Union[Warehouse, any]] = None,
        selection_mode: StockSelectionMode = StockSelectionMode.FEFO
    ) -> StockOperationResult:
        """
        Process stock deduction for a sales invoice.
        
        Args:
            invoice_id: Sales invoice ID
            items: List of dicts with keys:
                   - product (Product or ID)
                   - quantity
                   - batch_id (optional, for specific batch allocation)
            warehouse: Warehouse to deduct from
            selection_mode: FEFO or FIFO
            
        Returns:
            StockOperationResult with movements and any issues
        """
        # Idempotency guard: skip if already processed
        existing = StockMovement.objects.filter(
            reference_type='SALE',
            reference_id=str(invoice_id),
            movement_type='OUT'
        )[:1]
        if existing.exists():
            existing_ids = list(StockMovement.objects.filter(
                reference_type='SALE',
                reference_id=str(invoice_id),
                movement_type='OUT'
            ).values_list('id', flat=True))
            return StockOperationResult(
                success=True,
                message='Sale already processed',
                movements=existing_ids
            )

        result = StockOperationResult(success=True, message='Sale processed successfully')
        all_allocations = []
        all_movements = []
        
        for item in items:
            product = item['product']
            quantity = Decimal(str(item['quantity']))
            batch_id = item.get('batch_id')
            
            if quantity <= 0:
                result.errors.append(f'Invalid quantity for product {product}')
                result.success = False
                break
            
            # Check stock availability
            available = StockIntegrationService.get_total_available_stock(product, warehouse)
            if available < quantity and not batch_id:
                result.errors.append(
                    f'Insufficient stock for {product}. Available: {available}, Requested: {quantity}'
                )
                result.success = False
                break
            
            # Allocate stock
            allocation_result = StockIntegrationService.allocate_stock(
                product, quantity, warehouse, selection_mode, batch_id
            )
            
            if not allocation_result.success:
                result.success = False
                result.errors.extend(allocation_result.errors)
                result.stock_shortages.extend(allocation_result.stock_shortages)
                break
            
            all_allocations.extend(allocation_result.allocations)
            
            # Create stock movements for each allocation
            for allocation in allocation_result.allocations:
                movement = StockIntegrationService.create_stock_movement(
                    product=product,
                    batch=allocation.batch_id,
                    warehouse=warehouse,
                    movement_type='OUT',
                    reference_type='SALE',
                    reference_id=str(invoice_id),
                    quantity=-allocation.quantity,  # Negative for OUT
                    unit_cost=allocation.unit_cost,
                    notes=f'Sale invoice #{invoice_id}'
                )
                all_movements.append(movement)
        
        if not result.success:
            result.message = 'Sale processing failed with errors'
        
        result.allocations = all_allocations
        result.movements = [m.id for m in all_movements]
        return result

    @staticmethod
    @transaction.atomic
    def process_purchase(
        invoice_id: any,
        items: list[dict],
        warehouse: Optional[Union[Warehouse, any]] = None
    ) -> StockOperationResult:
        """
        Process stock addition from a purchase invoice.
        Creates new batches if they don't exist, or adds to existing batches.
        
        Args:
            invoice_id: Purchase invoice ID
            items: List of dicts with keys:
                   - product (Product or ID)
                   - quantity
                   - batch_number
                   - expiry_date
                   - unit_price (purchase price)
            warehouse: Warehouse to add stock to
            
        Returns:
            StockOperationResult with movements and batch info
        """
        # Idempotency guard: skip if already processed
        existing = StockMovement.objects.filter(
            reference_type='PURCHASE',
            reference_id=str(invoice_id),
            movement_type='IN'
        )[:1]
        if existing.exists():
            existing_ids = list(StockMovement.objects.filter(
                reference_type='PURCHASE',
                reference_id=str(invoice_id),
                movement_type='IN'
            ).values_list('id', flat=True))
            return StockOperationResult(
                success=True,
                message='Purchase already processed',
                movements=existing_ids
            )

        result = StockOperationResult(success=True, message='Purchase processed successfully')
        all_movements = []
        created_batches = []
        
        if not warehouse:
            warehouse = Warehouse.objects.filter(is_default=True).first()
            if not warehouse:
                warehouse = Warehouse.objects.first()
        
        for item in items:
            product = item['product']
            quantity = Decimal(str(item['quantity']))
            batch_number = item['batch_number']
            expiry_date = item['expiry_date']
            unit_price = Decimal(str(item.get('unit_price', 0)))
            manufacturing_date = item.get('manufacturing_date', django_timezone.now().date())
            
            if quantity <= 0:
                result.errors.append(f'Invalid quantity for product {product}')
                result.success = False
                continue
            
            # Check if batch already exists
            batch, created = Batch.objects.get_or_create(
                batch_number=batch_number,
                defaults={
                    'product': product if hasattr(product, 'id') else Product.objects.get(id=product),
                    'manufacturing_date': manufacturing_date,
                    'expiry_date': expiry_date,
                    'purchase_price': unit_price,
                    'sale_price': (unit_price * Decimal('1.3')).quantize(Decimal('0.01')),  # 30% markup default
                    'quantity': quantity,
                    'remaining_quantity': quantity,
                    'location': str(warehouse.id) if warehouse else 'Default',
                }
            )
            
            if not created:
                # Add to existing batch
                Batch.objects.filter(id=batch.id).update(
                    quantity=models.F('quantity') + quantity,
                    remaining_quantity=models.F('remaining_quantity') + quantity
                )
                batch.refresh_from_db()
            
            created_batches.append({
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'quantity': quantity,
            })
            
            # Create stock movement
            movement = StockIntegrationService.create_stock_movement(
                product=product,
                batch=batch,
                warehouse=warehouse,
                movement_type='IN',
                reference_type='PURCHASE',
                reference_id=str(invoice_id),
                quantity=quantity,  # Positive for IN
                unit_cost=unit_price,
                notes=f'Purchase invoice #{invoice_id}'
            )
            all_movements.append(movement)
        
        if not result.success:
            result.message = 'Purchase processing failed with errors'
        
        result.movements = [m.id for m in all_movements]
        result.warnings.append(f'Created/updated {len(created_batches)} batches')
        return result

    @staticmethod
    @transaction.atomic
    def process_sale_return(
        invoice_id: any,
        items: list[dict],
        warehouse: Optional[Union[Warehouse, any]] = None
    ) -> StockOperationResult:
        """
        Process stock return from a sales return.
        
        Args:
            invoice_id: Original sales invoice ID
            items: List of dicts with keys:
                   - product
                   - quantity
                   - batch_id
            warehouse: Warehouse to return stock to
            
        Returns:
            StockOperationResult
        """
        result = StockOperationResult(success=True, message='Sale return processed successfully')
        all_movements = []
        
        for item in items:
            product = item['product']
            quantity = Decimal(str(item['quantity']))
            batch_id = item.get('batch_id')
            
            if quantity <= 0:
                result.errors.append(f'Invalid quantity for product {product}')
                result.success = False
                continue
            
            # Get batch for the return
            batch = None
            if batch_id:
                batch = Batch.objects.filter(id=batch_id).first()
            
            if not batch:
                # Try to find the original batch from the sale movements
                original_movement = StockMovement.objects.filter(
                    reference_type='SALE',
                    reference_id=str(invoice_id),
                    product=product if hasattr(product, 'id') else Product.objects.get(id=product)
                ).first()
                
                if original_movement:
                    batch = original_movement.batch
            
            if not batch:
                result.errors.append(f'Could not find batch for product {product} return')
                result.success = False
                continue
            
            # Create stock movement for return
            movement = StockIntegrationService.create_stock_movement(
                product=product,
                batch=batch,
                warehouse=warehouse,
                movement_type='IN',
                reference_type='SALE',
                reference_id=f'RETURN-{invoice_id}',
                quantity=quantity,
                unit_cost=batch.purchase_price,
                notes=f'Return for sale invoice #{invoice_id}'
            )
            all_movements.append(movement)
        
        result.movements = [m.id for m in all_movements]
        return result

    @staticmethod
    def get_total_available_stock(
        product: Union[Product, any],
        warehouse: Optional[Union[Warehouse, any]] = None,
        exclude_expired: bool = True
    ) -> Decimal:
        """
        Get total available stock for a product.
        
        Args:
            product: Product instance or ID
            warehouse: Optional warehouse filter
            exclude_expired: Whether to exclude expired batches
            
        Returns:
            Total available quantity
        """
        product_id = product.id if hasattr(product, 'id') else product
        
        batches = Batch.objects.filter(
            product_id=product_id,
            remaining_quantity__gt=0,
            is_active=True
        )
        
        if warehouse:
            warehouse_id = warehouse.id if hasattr(warehouse, 'id') else warehouse
            batches = batches.filter(location=str(warehouse_id))
        
        if exclude_expired:
            batches = batches.filter(expiry_date__gte=django_timezone.now().date())
        
        total = batches.aggregate(total=models.Sum('remaining_quantity'))['total'] or Decimal('0')
        return total

    @staticmethod
    def check_stock_availability(
        items: list[dict],
        warehouse: Optional[Union[Warehouse, any]] = None
    ) -> dict:
        """
        Check stock availability for multiple items.
        
        Args:
            items: List of dicts with 'product' and 'quantity'
            warehouse: Optional warehouse filter
            
        Returns:
            Dict with availability status for each item
        """
        results = {}
        
        for item in items:
            product = item['product']
            quantity = Decimal(str(item['quantity']))
            available = StockIntegrationService.get_total_available_stock(product, warehouse)
            
            product_id = product.id if hasattr(product, 'id') else product
            results[str(product_id)] = {
                'product': str(product),
                'requested': quantity,
                'available': available,
                'is_available': available >= quantity,
                'shortage': max(Decimal('0'), quantity - available),
            }
        
        return results

    @staticmethod
    def create_stock_movement(
        product: Union[Product, any],
        batch: Optional[Union[Batch, any]] = None,
        warehouse: Optional[Union[Warehouse, any]] = None,
        movement_type: str = 'IN',
        reference_type: str = 'MANUAL',
        reference_id: str = '',
        quantity: Decimal = Decimal('0'),
        unit_cost: Optional[Decimal] = None,
        notes: str = ''
    ) -> StockMovement:
        """
        Create a stock movement record.
        
        Args:
            product: Product instance or ID
            batch: Optional Batch instance or ID
            warehouse: Warehouse instance or ID
            movement_type: IN, OUT, ADJUSTMENT, TRANSFER
            reference_type: PURCHASE, SALE, PRODUCTION, WASTE, EXPIRY, MANUAL
            reference_id: Reference ID from related system
            quantity: Quantity (positive for IN, negative for OUT)
            unit_cost: Optional unit cost
            notes: Optional notes
            
        Returns:
            Created StockMovement instance
        """
        if not warehouse:
            warehouse = Warehouse.objects.filter(is_default=True).first()
            if not warehouse:
                warehouse = Warehouse.objects.first()
        
        batch_id = batch.id if hasattr(batch, 'id') else batch if batch else None
        product_obj = product if hasattr(product, 'id') else Product.objects.get(id=product)
        warehouse_obj = warehouse if hasattr(warehouse, 'id') else Warehouse.objects.get(id=warehouse)
        
        total_cost = None
        if unit_cost is not None:
            total_cost = abs(quantity) * unit_cost
            # Round to 2 decimal places to match the model field definition
            total_cost = total_cost.quantize(Decimal('0.01'))
        
        movement = StockMovement.objects.create(
            product=product_obj,
            batch_id=batch_id,
            warehouse=warehouse_obj,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            notes=notes
        )
        
        return movement

    @staticmethod
    def update_batch_quantity(
        batch_id: any,
        quantity_change: Decimal
    ) -> None:
        """
        Update batch remaining quantity.
        
        Args:
            batch_id: Batch ID
            quantity_change: Change in quantity (positive for increase, negative for decrease)
        """
        Batch.objects.filter(id=batch_id).update(
            remaining_quantity=models.F('remaining_quantity') + quantity_change
        )

    @staticmethod
    @transaction.atomic
    def reverse_sale_stock(invoice_id: any) -> StockOperationResult:
        """Reverse stock movements for a cancelled sales invoice.

        Creates IN movements to restore stock that was deducted by the sale.
        """
        result = StockOperationResult(success=True, message='Sale stock reversed')
        movements = StockMovement.objects.filter(
            reference_type='SALE',
            reference_id=str(invoice_id),
            movement_type='OUT',
            is_active=True
        ).select_for_update()

        for movement in movements:
            reversed_qty = abs(movement.quantity)

            StockIntegrationService.update_batch_quantity(
                movement.batch_id, reversed_qty
            )

            new_movement = StockIntegrationService.create_stock_movement(
                product=movement.product,
                batch=movement.batch,
                warehouse=movement.warehouse,
                movement_type='IN',
                reference_type='SALE',
                reference_id=f'CANCEL-{invoice_id}',
                quantity=reversed_qty,
                unit_cost=movement.unit_cost,
                notes=f'Stock restored from cancelled sale #{invoice_id}'
            )
            result.movements.append(new_movement.id)

        return result

    @staticmethod
    @transaction.atomic
    def reverse_purchase_stock(invoice_id: any) -> StockOperationResult:
        """Reverse stock movements for a cancelled purchase invoice.

        Creates OUT movements to remove stock that was added by the purchase.
        """
        result = StockOperationResult(success=True, message='Purchase stock reversed')
        movements = StockMovement.objects.filter(
            reference_type='PURCHASE',
            reference_id=str(invoice_id),
            movement_type='IN',
            is_active=True
        ).select_for_update()

        for movement in movements:
            reversed_qty = -abs(movement.quantity)

            StockIntegrationService.update_batch_quantity(
                movement.batch_id, reversed_qty
            )

            new_movement = StockIntegrationService.create_stock_movement(
                product=movement.product,
                batch=movement.batch,
                warehouse=movement.warehouse,
                movement_type='OUT',
                reference_type='PURCHASE',
                reference_id=f'CANCEL-{invoice_id}',
                quantity=reversed_qty,
                unit_cost=movement.unit_cost,
                notes=f'Stock removed from cancelled purchase #{invoice_id}'
            )
            result.movements.append(new_movement.id)

        return result

    @staticmethod
    @transaction.atomic
    def process_transfer(
        transfer_id: any,
        items: list[dict],
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

            for item in items:
                product = item['product']
                quantity = Decimal(str(item['quantity']))
                batch_id = item.get('batch_id')

                if quantity <= 0:
                    result.errors.append(f'Invalid quantity for product {product}')
                    result.success = False
                    continue

                product_obj = product if hasattr(product, 'id') else Product.objects.get(id=product)
                batch = None
                if batch_id:
                    batch = Batch.objects.select_for_update().get(id=batch_id)
                else:
                    batches = Batch.objects.select_for_update().filter(
                        product=product_obj,
                        remaining_quantity__gt=0,
                        location=str(transfer.source_warehouse.id),
                        is_active=True
                    ).order_by('expiry_date', 'id')
                    batch = batches.first()

                if not batch:
                    result.errors.append(f'No available batch for product {product_obj.name}')
                    result.success = False
                    continue

                if batch.remaining_quantity < quantity:
                    result.errors.append(f'Insufficient stock for {product_obj.name} in source warehouse')
                    result.success = False
                    continue

                out_movement = StockIntegrationService.create_stock_movement(
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

                StockIntegrationService.update_batch_quantity(batch.id, -quantity)

                in_movement = StockIntegrationService.create_stock_movement(
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

                dest_batch = Batch.objects.filter(
                    product=product_obj,
                    batch_number=batch.batch_number,
                    location=str(transfer.destination_warehouse.id)
                ).select_for_update().first()

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

            if not result.errors:
                transfer.status = 'COMPLETED'
                transfer.save(update_fields=['status'])
                result.success = True
                result.message = 'Transfer completed successfully'

        except Exception as e:
            logger.exception("Transfer processing failed — rolling back transaction")
            result.errors.append(str(e))
            result.success = False
            raise

        result.movements = all_movements
        return result

    @staticmethod
    def get_stock_levels(
        product: Optional[Union[Product, any]] = None,
        warehouse: Optional[Union[Warehouse, any]] = None,
        include_expired: bool = False
    ) -> list[dict]:
        """
        Get stock levels for products/batches.
        
        Args:
            product: Optional product filter
            warehouse: Optional warehouse filter
            include_expired: Whether to include expired batches
            
        Returns:
            List of stock level dicts
        """
        batches = Batch.objects.filter(
            remaining_quantity__gt=0,
            is_active=True
        )
        
        if product:
            product_id = product.id if hasattr(product, 'id') else product
            batches = batches.filter(product_id=product_id)
        
        if warehouse:
            warehouse_id = warehouse.id if hasattr(warehouse, 'id') else warehouse
            batches = batches.filter(location=str(warehouse_id))
        
        if not include_expired:
            batches = batches.filter(expiry_date__gte=django_timezone.now().date())
        
        batches = batches.select_related('product').order_by('product__name', 'expiry_date')
        
        results = []
        for batch in batches:
            results.append({
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'product_id': batch.product_id,
                'product_name': str(batch.product),
                'remaining_quantity': batch.remaining_quantity,
                'total_quantity': batch.quantity,
                'expiry_date': batch.expiry_date,
                'location': batch.location,
                'is_expired': batch.is_expired,
                'days_until_expiry': batch.days_until_expiry,
                'is_expiring_soon': batch.is_expiring_soon,
            })
        
        return results

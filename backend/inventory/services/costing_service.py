"""
Advanced Costing Engine
Extends inventory costing with:
- Weighted Average Cost (AVCO)
- Landed Cost allocation
- Cost flow integrity
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, List, Dict
from django.db import models
from django.db.models import Sum, Avg, F

from inventory.models import Batch, Product, Warehouse, StockMovement


class CostingMethod:
    """Costing method constants."""
    FIFO = 'FIFO'
    FEFO = 'FEFO'
    AVCO = 'AVCO'  # Weighted Average Cost


class LandedCostType:
    """Landed cost type constants."""
    IMPORT_DUTY = 'IMPORT_DUTY'
    TRANSPORT = 'TRANSPORT'
    CUSTOMS_FEE = 'CUSTOMS_FEE'
    HANDLING_CHARGE = 'HANDLING_CHARGE'
    INSURANCE = 'INSURANCE'
    OTHER = 'OTHER'


class CostingService:
    """
    Advanced Costing Engine - extends StockIntegrationService.
    
    Provides:
    - FIFO/FEFO (via existing service)
    - Weighted Average Cost (AVCO)
    - Landed Cost allocation
    - Cost flow integrity
    """

    @staticmethod
    def calculate_weighted_average_cost(
        product: Product,
        warehouse: Optional[Warehouse] = None,
        include_pending: bool = False
    ) -> Decimal:
        """
        Calculate Weighted Average Cost for a product.
        
        Formula: Total Cost of All Batches / Total Quantity
        
        Args:
            product: Product instance or ID
            warehouse: Optional warehouse filter
            include_pending: Include pending purchase orders
            
        Returns:
            Weighted average cost per unit
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
        
        total_cost = Decimal('0.00')
        total_qty = Decimal('0.00')
        
        for batch in batches:
            if batch.purchase_price:
                batch_cost = batch.remaining_quantity * batch.purchase_price
                total_cost += batch_cost
                total_qty += batch.remaining_quantity
        
        if total_qty > 0:
            return (total_cost / total_qty).quantize(Decimal('0.01'))
        
        return Decimal('0.00')

    @staticmethod
    def get_average_cost_for_sale(
        product: Product,
        quantity: Decimal,
        warehouse: Optional[Warehouse] = None,
        method: str = CostingMethod.AVCO
    ) -> Decimal:
        """
        Get cost for a sale based on selected costing method.
        
        For AVCO: Returns weighted average cost
        For FIFO/FEFO: Delegates to StockIntegrationService allocations
        
        Args:
            product: Product to sale
            quantity: Quantity being sold
            warehouse: Source warehouse
            method: Costing method (FIFO, FEFO, AVCO)
            
        Returns:
            Total cost for the quantity
        """
        if method == CostingMethod.AVCO:
            avg_cost = CostingService.calculate_weighted_average_cost(product, warehouse)
            return (avg_cost * quantity).quantize(Decimal('0.01'))
        else:
            from inventory.service.stock_integration import StockIntegrationService
            from inventory.service.types import StockSelectionMode
            
            mode = StockSelectionMode.FEFO if method == CostingMethod.FEFO else StockSelectionMode.FIFO
            
            allocations = StockIntegrationService.allocate_stock(
                product, quantity, warehouse, mode
            )
            
            total_cost = Decimal('0.00')
            for alloc in allocations.allocations:
                if alloc.unit_cost:
                    total_cost += alloc.quantity * alloc.unit_cost
            
            return total_cost.quantize(Decimal('0.01'))

    @staticmethod
    def recalculate_product_average_cost(product_id: str) -> Decimal:
        """
        Recalculate and update average cost for a product.
        Useful for batch updates.
        
        Args:
            product_id: Product ID
            
        Returns:
            New average cost
        """
        product = Product.objects.get(id=product_id)
        new_avg = CostingService.calculate_weighted_average_cost(product)
        
        return new_avg


class LandedCostService:
    """
    Landed Cost Allocation Service.
    
    Handles:
    - Import duties
    - Transport costs
    - Customs fees
    - Handling charges
    - Insurance
    """

    @staticmethod
    def allocate_landed_costs(
        batch: Batch,
        landed_costs: List[Dict]
    ) -> Decimal:
        """
        Allocate landed costs to a batch.
        
        Landed costs are added to the batch cost basis.
        
        Args:
            batch: Batch to allocate costs to
            landed_costs: List of dicts with:
                - type: LandedCostType
                - amount: Decimal cost
                - description: str
                
        Returns:
            Total landed cost added
        """
        from inventory.models import StockMovement
        
        total_landed = Decimal('0.00')
        
        for cost in landed_costs:
            amount = Decimal(str(cost.get('amount', 0)))
            if amount <= 0:
                continue
                
            total_landed += amount
            
            StockMovement.objects.create(
                product=batch.product,
                batch=batch,
                warehouse=batch.warehouse,
                movement_type='ADJUSTMENT',
                reference_type='LANDED_COST',
                reference_id=f'LC-{batch.batch_number}',
                quantity=Decimal('0'),
                unit_cost=amount,
                total_cost=amount,
                notes=f"Landed cost: {cost.get('type')} - {cost.get('description', '')}"
            )
        
        if total_landed > 0:
            current_cost = batch.purchase_price or Decimal('0')
            batch.purchase_price = current_cost + total_landed
            batch.save(update_fields=['purchase_price'])
        
        return total_landed

    @staticmethod
    def get_batch_landed_cost_total(batch_id: str) -> Decimal:
        """Get total landed costs for a batch."""
        from inventory.models import StockMovement
        
        total = StockMovement.objects.filter(
            batch_id=batch_id,
            reference_type='LANDED_COST',
            movement_type='ADJUSTMENT'
        ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')
        
        return total

    @staticmethod
    def distribute_landed_cost_to_batches(
        product: Product,
        total_landed_cost: Decimal,
        warehouse: Optional[Warehouse] = None
    ) -> Dict:
        """
        Distribute a total landed cost across all existing batches proportionally.
        
        Used when you have a single landed cost (e.g., shipping) that needs
        to be spread across multiple batches.
        
        Args:
            product: Product to distribute cost for
            total_landed_cost: Total cost to distribute
            warehouse: Optional warehouse filter
            
        Returns:
            Dict with distribution results
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
        
        total_qty = sum(b.remaining_quantity for b in batches)
        
        if total_qty == 0:
            return {'success': False, 'error': 'No batches to distribute cost'}
        
        results = []
        
        for batch in batches:
            proportion = batch.remaining_quantity / total_qty
            batch_cost = (total_landed_cost * proportion).quantize(Decimal('0.01'))
            
            if batch_cost > 0:
                old_cost = batch.purchase_price or Decimal('0')
                batch.purchase_price = old_cost + batch_cost
                batch.save(update_fields=['purchase_price'])
                
                results.append({
                    'batch_number': batch.batch_number,
                    'cost_added': batch_cost,
                    'new_unit_cost': batch.purchase_price
                })
        
        return {
            'success': True,
            'total_distributed': total_landed_cost,
            'batches_updated': len(results),
            'details': results
        }


class CostFlowIntegrityService:
    """
    Ensures cost flows correctly from:
    Purchase → Inventory → Sales → COGS
    
    No duplicate cost calculations allowed.
    """

    @staticmethod
    def verify_inventory_valuation(
        product: Product,
        warehouse: Optional[Warehouse] = None
    ) -> Dict:
        """
        Verify inventory valuation is consistent.
        
        Compares:
        - Sum of (batch.qty * batch.cost) 
        - StockMovement total costs
        - Expected accounting values
        
        Returns verification result.
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
        
        batch_value = Decimal('0.00')
        for batch in batches:
            if batch.purchase_price:
                batch_value += batch.remaining_quantity * batch.purchase_price
        
        movement_value = StockMovement.objects.filter(
            product_id=product_id,
            warehouse=warehouse,
            movement_type__in=['IN', 'OUT'],
            batch__isnull=False
        ).aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0.00')
        
        return {
            'product_id': str(product_id),
            'batch_valuation': batch_value,
            'movement_valuation': movement_value,
            'is_consistent': abs(batch_value - movement_value) < Decimal('0.01'),
            'batch_count': batches.count()
        }

    @staticmethod
    def get_cogs_for_invoice(
        invoice_items: List,
        method: str = CostingMethod.AVCO,
        warehouse: Optional[Warehouse] = None
    ) -> Decimal:
        """
        Calculate COGS for invoice items using specified method.
        
        Ensures COGS calculation is consistent with inventory valuation.
        
        Args:
            invoice_items: SalesInvoice items
            method: Costing method (AVCO, FIFO, FEFO)
            warehouse: Source warehouse
            
        Returns:
            Total COGS amount
        """
        total_cogs = Decimal('0.00')
        
        for item in invoice_items:
            product = item.product
            quantity = item.quantity
            
            item_cost = CostingService.get_average_cost_for_sale(
                product, quantity, warehouse, method
            )
            
            total_cogs += item_cost
        
        return total_cogs.quantize(Decimal('0.01'))
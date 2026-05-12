"""
Inventory Accounting Service
=============================
Perpetual Inventory Accounting Integration with Double-Entry Bookkeeping.

Every inventory movement that affects value MUST generate a journal entry.

IMPORTANT ARCHITECTURE DECISION (to prevent duplicate accounting):
- Sales dispatch accounting (COGS + Inventory) is handled by SalesAccountingService
  in a COMBINED journal entry with Revenue and AR. This is the SINGLE authoritative path.
- Purchase receipt accounting (Inventory + Tax) is handled by PurchaseAccountingService
  in a COMBINED journal entry with AP. This is the SINGLE authoritative path.
- This service handles STANDALONE inventory operations that need their own entries:
  - Inventory adjustments (positive/negative)
  - Inventory write-offs (damage, expiry)
  - COGS calculation helper (used by SalesAccountingService)
"""

import logging
from decimal import Decimal
from datetime import date
from typing import Optional, List, Dict
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from inventory.models import Batch, StockMovement, Warehouse

logger = logging.getLogger('erp.inventory_accounting')


class InventoryAccountingServiceError(Exception):
    """Raised when inventory accounting operation fails."""
    pass


class InventoryAccountingService:
    """
    Centralized service for STANDALONE inventory accounting operations.

    CRITICAL RULES:
    1. Stock movement and accounting must be atomic - both succeed or both rollback
    2. NO duplicate accounting paths - sales/purchase accounting goes through their own services
    3. This service handles: adjustments, write-offs, and COGS calculation
    4. All operations go through JournalEngine exclusively
    """

    # Account codes - matches chart of accounts
    INVENTORY_ACCOUNT_CODE = '1300'
    COGS_ACCOUNT_CODE = '5100'
    INVENTORY_GAIN_ACCOUNT_CODE = '4900'
    INVENTORY_LOSS_ACCOUNT_CODE = '5200'
    INVENTORY_WRITE_OFF_ACCOUNT_CODE = '5210'

    @staticmethod
    def _get_account_by_code(account_code: str) -> Account:
        """Get account by code or raise error."""
        try:
            return Account.objects.get(code=account_code, is_active=True)
        except Account.DoesNotExist:
            raise InventoryAccountingServiceError(
                f"Required account code {account_code} not found or inactive"
            )

    @staticmethod
    def _validate_stock_movement(movement: StockMovement) -> None:
        """Validate that a stock movement is eligible for accounting."""
        if not movement or not movement.pk:
            raise InventoryAccountingServiceError("Stock movement must be saved before accounting")
        if movement.movement_type not in ['IN', 'OUT', 'ADJUSTMENT', 'TRANSFER']:
            raise InventoryAccountingServiceError(
                f"Unsupported movement type: {movement.movement_type}"
            )

    @staticmethod
    def get_batch_cost(batch: Batch) -> Decimal:
        """Get the cost basis for a batch (purchase price)."""
        if batch.purchase_price is None:
            return Decimal('0.00')
        return batch.purchase_price

    @staticmethod
    def calculate_movement_cost(movement: StockMovement) -> Decimal:
        """Calculate the total cost of a stock movement."""
        if movement.unit_cost:
            return (abs(movement.quantity) * movement.unit_cost).quantize(Decimal('0.01'))
        if movement.batch_id is not None:
            try:
                batch = Batch.objects.get(id=movement.batch_id)
                if batch.purchase_price:
                    return (abs(movement.quantity) * batch.purchase_price).quantize(Decimal('0.01'))
            except Batch.DoesNotExist:
                pass
        return Decimal('0.00')

    @staticmethod
    def calculate_cogs_for_items(
        items: List,
        warehouse: Optional[Warehouse] = None,
        method: str = 'FEFO'
    ) -> Decimal:
        """
        Calculate total COGS for a list of invoice items using FIFO/FEFO.
        Used by SalesAccountingService to get accurate COGS.

        Args:
            items: List of SalesItem instances or dicts with product, quantity, batch
            warehouse: Optional warehouse filter
            method: 'FEFO' or 'FIFO'

        Returns:
            Total COGS amount
        """
        from inventory.service import StockIntegrationService, StockSelectionMode

        total_cogs = Decimal('0.00')

        for item in items:
            product = item.product if hasattr(item, 'product') else item.get('product')
            quantity = item.quantity if hasattr(item, 'quantity') else item.get('quantity')
            batch = item.batch if hasattr(item, 'batch') else item.get('batch')

            if batch and batch.purchase_price:
                # Use actual batch cost if item is linked to a batch
                item_cost = quantity * batch.purchase_price
            else:
                # Fall back to allocation-based costing
                from inventory.service.types import StockSelectionMode as SM
                selection_mode = SM.FEFO if method == 'FEFO' else SM.FIFO
                allocations = StockIntegrationService.allocate_stock(
                    product, quantity, warehouse, selection_mode
                )
                if allocations.success:
                    item_cost = Decimal('0.00')
                    for alloc in allocations.allocations:
                        if alloc.unit_cost:
                            item_cost += alloc.quantity * alloc.unit_cost
                else:
                    # Fallback to weighted average
                    from inventory.services.costing_service import CostingService
                    item_cost = CostingService.get_average_cost_for_sale(
                        product, quantity, warehouse
                    )

            total_cogs += item_cost.quantize(Decimal('0.01'))

        return total_cogs.quantize(Decimal('0.01'))

    @classmethod
    @db_transaction.atomic
    def process_sales_dispatch(
        cls,
        movement: StockMovement,
        invoice_reference: str = '',
        cogs_override: Optional[Decimal] = None,
    ) -> Dict:
        """
        Create journal entry for a sales dispatch (stock OUT to customer).
        
        Debit: Cost of Goods Sold (COGS)
        Credit: Inventory Asset (reduces inventory value)
        
        The sales revenue entry is handled separately by SalesAccountingService.
        This method ONLY handles the inventory/COGS side.
        
        Args:
            movement: StockMovement of type 'OUT' with reference_type='SALE'
            invoice_reference: Sales invoice number
            cogs_override: Optional COGS override (uses movement cost if not provided)
            
        Returns:
            Dict with success status and entry details
        """
        cls._validate_stock_movement(movement)

        if movement.movement_type != 'OUT':
            raise InventoryAccountingServiceError(
                f"Expected OUT movement, got {movement.movement_type}"
            )

        if cogs_override is not None:
            cost = cogs_override.quantize(Decimal('0.01'))
        else:
            cost = cls.calculate_movement_cost(movement)

        if cost <= 0:
            # Movements with zero cost still need accounting but with zero value
            cost = Decimal('0.00')

        inventory_account = cls._get_account_by_code(cls.INVENTORY_ACCOUNT_CODE)
        cogs_account = cls._get_account_by_code(cls.COGS_ACCOUNT_CODE)

        lines = [
            {
                'account_code': cls.COGS_ACCOUNT_CODE,
                'debit': cost,
                'credit': Decimal('0.00'),
                'description': f"COGS for sale - {movement.product.name} - Ref: {invoice_reference or movement.reference_id}"
            },
            {
                'account_code': cls.INVENTORY_ACCOUNT_CODE,
                'debit': Decimal('0.00'),
                'credit': cost,
                'description': f"Inventory reduction - {movement.product.name} - Ref: {invoice_reference or movement.reference_id}"
            },
        ]

        entry_date = movement.created_at.date() if movement.created_at else django_timezone.now().date()

        result = JournalEngine.create_entry(
            entry_type='INVENTORY_OUT',
            description=f"Sales dispatch: {movement.product.name} - Qty: {abs(movement.quantity)} - COGS: {cost}",
            lines=lines,
            entry_date=entry_date,
            reference=invoice_reference or movement.reference_id or str(movement.id),
            auto_post=True,
            source_module='inventory',
            source_document=str(movement.id),
            change_reason=f"Inventory dispatch for sale {invoice_reference}"
        )

        if result.get('success'):
            try:
                movement.journal_entry_id = result.get('entry_id')
                movement.save(update_fields=['journal_entry_id', 'updated_at'])
            except (AttributeError, ValueError):
                pass

        return result

    @classmethod
    @db_transaction.atomic
    def process_inventory_adjustment(
        cls,
        movement: StockMovement,
        reason: str = '',
    ) -> Dict:
        """
        Create journal entry for an inventory adjustment.
        
        Positive adjustment:
            Debit: Inventory Asset
            Credit: Inventory Gain/Loss
            
        Negative adjustment:
            Debit: Inventory Gain/Loss (Loss account)
            Credit: Inventory Asset
        
        Args:
            movement: StockMovement of type 'ADJUSTMENT'
            reason: Reason for the adjustment
            
        Returns:
            Dict with success status and entry details
        """
        cls._validate_stock_movement(movement)

        if movement.movement_type != 'ADJUSTMENT':
            raise InventoryAccountingServiceError(
                f"Expected ADJUSTMENT movement, got {movement.movement_type}"
            )

        # For adjustments, we need a cost basis
        cost = cls.calculate_movement_cost(movement)
        
        # If no unit_cost on movement, try to get from batch
        if cost <= 0 and movement.batch_id:
            try:
                batch = Batch.objects.get(id=movement.batch_id)
                if batch.purchase_price:
                    cost = abs(movement.quantity) * batch.purchase_price
            except Batch.DoesNotExist:
                pass

        cost = cost.quantize(Decimal('0.01'))

        if cost <= 0:
            return {
                'success': False,
                'errors': [f'Cannot create adjustment entry with zero cost for movement {movement.id}']
            }

        lines = []

        if movement.quantity > 0:
            # Positive adjustment - increase inventory value
            # Debit: Inventory, Credit: Gain
            lines = [
                {
                    'account_code': cls.INVENTORY_ACCOUNT_CODE,
                    'debit': cost,
                    'credit': Decimal('0.00'),
                    'description': f"Inventory adjustment (+) - {movement.product.name} - Qty: {movement.quantity}"
                },
                {
                    'account_code': cls.INVENTORY_GAIN_ACCOUNT_CODE,
                    'debit': Decimal('0.00'),
                    'credit': cost,
                    'description': f"Inventory gain - {movement.product.name} - {reason}"
                },
            ]
            entry_type = 'INVENTORY_ADJ'
            description = f"Positive inventory adjustment: {movement.product.name} - Qty: {movement.quantity}, Value: {cost}"
        else:
            # Negative adjustment - decrease inventory value
            # Debit: Loss, Credit: Inventory
            loss_cost = abs(cost)
            lines = [
                {
                    'account_code': cls.INVENTORY_LOSS_ACCOUNT_CODE,
                    'debit': loss_cost,
                    'credit': Decimal('0.00'),
                    'description': f"Inventory loss - {movement.product.name} - {reason}"
                },
                {
                    'account_code': cls.INVENTORY_ACCOUNT_CODE,
                    'debit': Decimal('0.00'),
                    'credit': loss_cost,
                    'description': f"Inventory adjustment (-) - {movement.product.name} - Qty: {abs(movement.quantity)}"
                },
            ]
            entry_type = 'INVENTORY_ADJ'
            description = f"Negative inventory adjustment: {movement.product.name} - Qty: {abs(movement.quantity)}, Loss: {loss_cost}"

        entry_date = movement.created_at.date() if movement.created_at else django_timezone.now().date()

        result = JournalEngine.create_entry(
            entry_type=entry_type,
            description=description,
            lines=lines,
            entry_date=entry_date,
            reference=movement.reference_id or str(movement.id),
            auto_post=True,
            source_module='inventory',
            source_document=str(movement.id),
            change_reason=reason or f"Inventory adjustment for {movement.product.name}"
        )

        if result.get('success'):
            try:
                movement.journal_entry_id = result.get('entry_id')
                movement.save(update_fields=['journal_entry_id', 'updated_at'])
            except (AttributeError, ValueError):
                pass

        return result

    @classmethod
    @db_transaction.atomic
    def process_inventory_write_off(
        cls,
        product,
        quantity: Decimal,
        batch: Optional[Batch] = None,
        reason: str = 'Write-off',
        reference_type: str = 'EXPIRY',
    ) -> Dict:
        """
        Create journal entry for inventory write-off (damage, expiry, etc.).
        
        Debit: Inventory Loss Expense
        Credit: Inventory Asset
        
        Args:
            product: Product instance or ID
            quantity: Quantity being written off (positive)
            batch: Optional batch being written off
            reason: Reason for write-off
            reference_type: EXPIRY, WASTE, DAMAGE, etc.
            
        Returns:
            Dict with success status and entry details
        """
        from inventory.models import Product as ProductModel
        
        if isinstance(product, int) or isinstance(product, str):
            product = ProductModel.objects.get(id=product)

        quantity = abs(quantity)
        
        # Get cost from batch if available
        if batch and batch.purchase_price:
            cost = (quantity * batch.purchase_price).quantize(Decimal('0.01'))
        else:
            # Use weighted average cost
            from inventory.services.costing_service import CostingService
            cost = CostingService.get_average_cost_for_sale(product, quantity)

        if cost <= 0:
            return {
                'success': False,
                'errors': [f'Cannot write off with zero cost for {product.name}']
            }

        lines = [
            {
                'account_code': cls.INVENTORY_WRITE_OFF_ACCOUNT_CODE,
                'debit': cost,
                'credit': Decimal('0.00'),
                'description': f"Inventory write-off ({reference_type}) - {product.name} - Qty: {quantity} - Reason: {reason}"
            },
            {
                'account_code': cls.INVENTORY_ACCOUNT_CODE,
                'debit': Decimal('0.00'),
                'credit': cost,
                'description': f"Inventory reduction - write-off ({reference_type}) - {product.name} - Qty: {quantity}"
            },
        ]

        result = JournalEngine.create_entry(
            entry_type='INVENTORY_ADJ',
            description=f"Inventory write-off: {product.name} - Qty: {quantity} - Cost: {cost} - Reason: {reason}",
            lines=lines,
            entry_date=django_timezone.now().date(),
            reference=f"WROFF-{reference_type}-{product.id}"[:50],
            auto_post=True,
            source_module='inventory',
            source_document=str(batch.id) if batch else str(product.id),
            change_reason=reason
        )

        return result

    @classmethod
    @db_transaction.atomic
    def process_warehouse_transfer(cls, transfer_items: List[Dict], transfer) -> Dict:
        """
        Create journal entries for warehouse transfer IF warehouses have separate valuation.
        
        Current implementation: NO accounting entries for warehouse transfers
        (transfers are operational movements only, not value transfers).
        
        This can be extended in the future if warehouses need separate valuation accounts.
        """
        # For now, warehouse transfers are operational only (no accounting)
        # Architecture is in place for future extension
        return {
            'success': True,
            'message': 'Warehouse transfers are operational movements only - no accounting entry required'
        }

    @classmethod
    def record_accounting_for_movement(cls, movement: StockMovement, **kwargs) -> Dict:
        """
        Central dispatcher - records accounting for ANY stock movement type.
        
        This is the SINGLE ENTRY POINT for inventory accounting.
        
        Args:
            movement: StockMovement instance
            **kwargs: Additional context (supplier_id, invoice_reference, reason, etc.)
            
        Returns:
            Dict with success status and entry details
        """
        cls._validate_stock_movement(movement)

        try:
            if movement.movement_type == 'IN' and movement.reference_type in ['PURCHASE', 'RETURN', 'MANUAL']:
                return cls.process_purchase_receipt(
                    movement,
                    supplier_id=kwargs.get('supplier_id'),
                    invoice_reference=kwargs.get('invoice_reference', movement.reference_id),
                )

            elif movement.movement_type == 'OUT' and movement.reference_type == 'SALE':
                cogs_override = kwargs.get('cogs_override')
                return cls.process_sales_dispatch(
                    movement,
                    invoice_reference=kwargs.get('invoice_reference', movement.reference_id),
                    cogs_override=cogs_override,
                )

            elif movement.movement_type == 'ADJUSTMENT':
                return cls.process_inventory_adjustment(
                    movement,
                    reason=kwargs.get('reason', movement.notes or 'Adjustment'),
                )

            elif movement.movement_type == 'TRANSFER':
                return cls.process_warehouse_transfer(
                    transfer_items=kwargs.get('transfer_items', []),
                    transfer=kwargs.get('transfer'),
                )

            else:
                return {
                    'success': True,
                    'message': f'No accounting action required for movement type {movement.movement_type} / reference {movement.reference_type}'
                }

        except InventoryAccountingServiceError as e:
            return {
                'success': False,
                'errors': [str(e)],
                'type': 'INVENTORY_ACCOUNTING_ERROR'
            }
        except Exception as e:
            logger = logging.getLogger('erp.inventory_accounting')
            logger.error(f"Unexpected error in inventory accounting for movement {movement.id}: {e}", exc_info=True)
            return {
                'success': False,
                'errors': [f'Unexpected error: {str(e)}'],
                'type': 'UNEXPECTED_ERROR'
            }
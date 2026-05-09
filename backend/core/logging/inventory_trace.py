"""
Inventory observability for Pharmacy ERP.
Wraps stock operations without modifying StockIntegrationService.
"""
from typing import Optional, Dict
from datetime import datetime
from functools import wraps

from core.logging.audit import EventType, AuditEventLogger


def trace_stock_movement(func):
    """
    Decorator to trace stock movement operations.
    Wraps stock_in, stock_out, and adjustments with structured logging.

    Usage:
        @trace_stock_movement
        def allocate_stock(...):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)

            # Extract stock info from result
            movement_id = getattr(result, 'id', str(result)) if result else 'unknown'
            quantity = getattr(result, 'quantity', kwargs.get('quantity', 0))
            warehouse = getattr(result, 'warehouse_id', kwargs.get('warehouse_id', ''))

            AuditEventLogger.log_inventory(
                event_type=EventType.STOCK_IN if quantity > 0 else EventType.STOCK_OUT,
                quantity=quantity,
                warehouse_id=str(warehouse),
                status='SUCCESS',
                metadata={'movement_id': movement_id}
            )

            return result

        except Exception as e:
            AuditEventLogger.log_inventory(
                event_type=EventType.STOCK_FAILURE,
                status='FAILED',
                metadata={
                    'function': func.__name__,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise

    return wrapper


class InventoryTraceLogger:
    """
    Manual trace logger for inventory operations.
    Use when decorator approach is not suitable.
    """

    @staticmethod
    def log_stock_in(
        product_id: str,
        quantity: float,
        warehouse_id: str,
        batch_id: Optional[str] = None,
        user: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log stock-in event."""
        AuditEventLogger.log_inventory(
            event_type=EventType.STOCK_IN,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            batch_id=batch_id,
            user=user,
            status='SUCCESS',
            metadata=metadata or {}
        )

    @staticmethod
    def log_stock_out(
        product_id: str,
        quantity: float,
        warehouse_id: str,
        batch_id: Optional[str] = None,
        user: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log stock-out event."""
        AuditEventLogger.log_inventory(
            event_type=EventType.STOCK_OUT,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=-quantity,
            batch_id=batch_id,
            user=user,
            status='SUCCESS',
            metadata=metadata or {}
        )

    @staticmethod
    def log_adjustment(
        product_id: str,
        quantity: float,
        warehouse_id: str,
        reason: str,
        user: Optional[str] = None
    ):
        """Log stock adjustment."""
        AuditEventLogger.log_inventory(
            event_type=EventType.STOCK_ADJUSTMENT,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            user=user,
            status='SUCCESS',
            metadata={'reason': reason}
        )

    @staticmethod
    def log_transfer(
        product_id: str,
        quantity: float,
        source_warehouse: str,
        dest_warehouse: str,
        user: Optional[str] = None
    ):
        """Log warehouse transfer."""
        AuditEventLogger.log_inventory(
            event_type=EventType.STOCK_TRANSFER,
            product_id=product_id,
            warehouse_id=source_warehouse,
            quantity=quantity,
            user=user,
            status='SUCCESS',
            metadata={'source': source_warehouse, 'destination': dest_warehouse}
        )

    @staticmethod
    def log_fefo_allocation(product_id: str, quantity: float, batch_id: str, warehouse_id: str, user: Optional[str] = None):
        """Log FEFO allocation."""
        AuditEventLogger.log_inventory(
            event_type=EventType.FEFO_ALLOCATION,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            batch_id=batch_id,
            user=user,
            status='SUCCESS',
            metadata={'strategy': 'FEFO'}
        )

    @staticmethod
    def log_fifo_allocation(product_id: str, quantity: float, batch_id: str, warehouse_id: str, user: Optional[str] = None):
        """Log FIFO allocation."""
        AuditEventLogger.log_inventory(
            event_type=EventType.FIFO_ALLOCATION,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            batch_id=batch_id,
            user=user,
            status='SUCCESS',
            metadata={'strategy': 'FIFO'}
        )

    @staticmethod
    def log_stock_failure(product_id: str, warehouse_id: str, error: str, user: Optional[str] = None):
        """Log stock failure."""
        AuditEventLogger.log_inventory(
            event_type=EventType.STOCK_FAILURE,
            product_id=product_id,
            warehouse_id=warehouse_id,
            status='FAILED',
            user=user,
            metadata={'error': error}
        )


inventory_trace = InventoryTraceLogger()

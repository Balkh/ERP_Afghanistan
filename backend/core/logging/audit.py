"""
Audit event system for Pharmacy ERP.
Centralized event logging for financial, inventory, and security operations.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.logging.logger import Logger


class EventType:
    """Standard event types for the ERP system."""
    AUTH_LOGIN = 'AUTH_LOGIN'
    AUTH_LOGOUT = 'AUTH_LOGOUT'
    AUTH_LOGIN_FAILED = 'AUTH_LOGIN_FAILED'
    AUTH_PASSWORD_CHANGE = 'AUTH_PASSWORD_CHANGE'
    AUTH_PERMISSION_DENIED = 'AUTH_PERMISSION_DENIED'

    JOURNAL_CREATE = 'JOURNAL_CREATE'
    JOURNAL_POST = 'JOURNAL_POST'
    JOURNAL_REVERSE = 'JOURNAL_REVERSE'
    JOURNAL_FAILED = 'JOURNAL_FAILED'

    STOCK_IN = 'STOCK_IN'
    STOCK_OUT = 'STOCK_OUT'
    STOCK_ADJUSTMENT = 'STOCK_ADJUSTMENT'
    STOCK_TRANSFER = 'STOCK_TRANSFER'
    STOCK_FAILURE = 'STOCK_FAILURE'
    FEFO_ALLOCATION = 'FEFO_ALLOCATION'
    FIFO_ALLOCATION = 'FIFO_ALLOCATION'

    PAYMENT_RECEIVED = 'PAYMENT_RECEIVED'
    PAYMENT_SENT = 'PAYMENT_SENT'
    PAYMENT_FAILED = 'PAYMENT_FAILED'
    PAYMENT_REFUND = 'PAYMENT_REFUND'

    SALE_CREATE = 'SALE_CREATE'
    SALE_DISPATCH = 'SALE_DISPATCH'
    SALE_CANCEL = 'SALE_CANCEL'

    PURCHASE_CREATE = 'PURCHASE_CREATE'
    PURCHASE_RECEIVE = 'PURCHASE_RECEIVE'
    PURCHASE_CANCEL = 'PURCHASE_CANCEL'

    DATA_EXPORT = 'DATA_EXPORT'
    DATA_IMPORT = 'DATA_IMPORT'

    SYSTEM_ERROR = 'SYSTEM_ERROR'
    SYSTEM_STARTUP = 'SYSTEM_STARTUP'
    SYSTEM_SHUTDOWN = 'SYSTEM_SHUTDOWN'

    PERFORMANCE_SLOW = 'PERFORMANCE_SLOW'
    PERFORMANCE_THRESHOLD = 'PERFORMANCE_THRESHOLD'


class AuditEventLogger:
    """
    Central audit event logger.
    Provides typed methods for different domains.
    """

    @staticmethod
    def log_event(
        event_type: str,
        user: Optional[str] = None,
        action: str = '',
        metadata: Optional[Dict[str, Any]] = None,
        status: str = 'SUCCESS',
        **kwargs
    ):
        """
        Log a structured audit event.

        Args:
            event_type: Type of event (from EventType constants)
            user: Username or user ID
            action: Action performed
            metadata: Additional context data
            status: SUCCESS, FAILED, WARNING
        """
        logger = Logger.audit()

        log_data = {
            'event_type': event_type,
            'user': user or 'system',
            'action': action,
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {},
        }
        log_data.update(kwargs)

        log_level = logging.ERROR if status == 'FAILED' else logging.INFO
        logger.log(
            log_level,
            f"{event_type}: {action}",
            extra={
                'extra_fields': log_data,
            }
        )

        return log_data

    @staticmethod
    def log_financial(
        event_type: str,
        journal_id: Optional[str] = None,
        debit_total: float = 0,
        credit_total: float = 0,
        user: Optional[str] = None,
        status: str = 'SUCCESS',
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a financial event."""
        logger = Logger.financial()

        log_data = {
            'event': event_type,
            'journal_id': journal_id,
            'user': user or 'system',
            'debit_total': debit_total,
            'credit_total': credit_total,
            'status': status,
            'balanced': abs(debit_total - credit_total) < 0.01,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {},
        }

        log_level = logging.ERROR if status == 'FAILED' else logging.INFO
        logger.log(
            log_level,
            f"FINANCIAL {event_type}: {status}",
            extra={'extra_fields': log_data}
        )

        return log_data

    @staticmethod
    def log_inventory(
        event_type: str,
        product_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        quantity: float = 0,
        batch_id: Optional[str] = None,
        user: Optional[str] = None,
        status: str = 'SUCCESS',
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an inventory event."""
        logger = Logger.inventory()

        log_data = {
            'event': event_type,
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'quantity': quantity,
            'batch_id': batch_id,
            'user': user or 'system',
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {},
        }

        log_level = logging.WARNING if status == 'FAILED' else logging.INFO
        logger.log(
            log_level,
            f"INVENTORY {event_type}: {quantity} units",
            extra={'extra_fields': log_data}
        )

        return log_data

    @staticmethod
    def log_security(
        event_type: str,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a security event."""
        logger = Logger.security()

        log_data = {
            'event': event_type,
            'user': user or 'anonymous',
            'ip_address': ip_address,
            'success': success,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {},
        }

        log_level = logging.WARNING if not success else logging.INFO
        logger.log(
            log_level,
            f"SECURITY {event_type}: {'SUCCESS' if success else 'FAILED'}",
            extra={'extra_fields': log_data}
        )

        return log_data


audit_logger = AuditEventLogger()

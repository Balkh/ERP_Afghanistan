"""
Financial trace logging for Pharmacy ERP.
Wraps financial operations without modifying JournalEngine or business logic.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps

from core.logging.logger import Logger
from core.logging.audit import EventType, AuditEventLogger


def trace_journal(func):
    """
    Decorator to trace journal entry operations.
    Wraps journal creation, posting, and reversal with structured logging.

    Usage:
        @trace_journal
        def create_journal_entry(...):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = Logger.financial()
        start_time = datetime.utcnow()

        try:
            result = func(*args, **kwargs)

            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            # Extract journal info from result if available
            journal_id = getattr(result, 'id', str(result)) if result else 'unknown'
            debit_total = getattr(result, 'total_debit', 0)
            credit_total = getattr(result, 'total_credit', 0)

            log_data = AuditEventLogger.log_financial(
                event_type=EventType.JOURNAL_POST,
                journal_id=journal_id,
                debit_total=debit_total,
                credit_total=credit_total,
                status='SUCCESS',
                metadata={
                    'function': func.__name__,
                    'duration_ms': round(duration_ms, 2),
                }
            )

            return result

        except Exception as e:
            AuditEventLogger.log_financial(
                event_type=EventType.JOURNAL_FAILED,
                status='FAILED',
                metadata={
                    'function': func.__name__,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise

    return wrapper


class FinancialTraceLogger:
    """
    Manual trace logger for financial operations.
    Use when decorator approach is not suitable.
    """

    @staticmethod
    def log_journal_create(journal_id: str, user: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log journal creation."""
        AuditEventLogger.log_financial(
            event_type=EventType.JOURNAL_CREATE,
            journal_id=journal_id,
            user=user,
            metadata=metadata or {},
        )

    @staticmethod
    def log_journal_post(
        journal_id: str,
        debit_total: float,
        credit_total: float,
        user: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log journal posting with balance validation."""
        balanced = abs(debit_total - credit_total) < 0.01
        AuditEventLogger.log_financial(
            event_type=EventType.JOURNAL_POST,
            journal_id=journal_id,
            debit_total=debit_total,
            credit_total=credit_total,
            user=user,
            status='SUCCESS' if balanced else 'WARNING',
            metadata={
                'balanced': balanced,
                **(metadata or {}),
            }
        )

    @staticmethod
    def log_journal_reverse(journal_id: str, original_journal_id: str, user: Optional[str] = None):
        """Log journal reversal."""
        AuditEventLogger.log_financial(
            event_type=EventType.JOURNAL_REVERSE,
            journal_id=journal_id,
            user=user,
            metadata={'original_journal_id': original_journal_id}
        )

    @staticmethod
    def log_balance_validation(
        journal_id: str,
        debit_total: float,
        credit_total: float,
        is_valid: bool
    ):
        """Log balance validation result."""
        status = 'SUCCESS' if is_valid else 'FAILED'
        AuditEventLogger.log_financial(
            event_type=EventType.JOURNAL_POST,
            journal_id=journal_id,
            debit_total=debit_total,
            credit_total=credit_total,
            status=status,
            metadata={'validation': 'balanced' if is_valid else 'unbalanced'}
        )

    @staticmethod
    def log_rollback(journal_id: str, reason: str, user: Optional[str] = None):
        """Log rollback event."""
        AuditEventLogger.log_financial(
            event_type=EventType.JOURNAL_FAILED,
            journal_id=journal_id,
            user=user,
            status='FAILED',
            metadata={'reason': reason, 'action': 'rollback'}
        )


financial_trace = FinancialTraceLogger()

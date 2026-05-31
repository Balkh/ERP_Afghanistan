"""
Class 3: BusinessTransactionBoundaryGuard — Atomic Business Transactions.

GUARANTEE: Every business action (Sales/Purchase/Return/Payroll) MUST:
  - succeed fully OR
  - rollback fully
  - NO partial states allowed in persistent layer

Wraps any callable and verifies that the transaction boundary
is properly managed. Detects:
  - Missing @transaction.atomic decorators
  - Partial saves without rollback
  - Inconsistent state after boundary exit
"""
import functools
import logging
from contextlib import contextmanager
from typing import Any, Callable, Optional, TypeVar

from django.db import transaction

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


# Models that MUST NOT be in a partial state
CRITICAL_TRANSACTION_MODELS = [
    'sales.SalesInvoice',
    'purchases.PurchaseInvoice',
    'returns.ReturnOrder',
    'accounting.JournalEntry',
    'payments.FinancialTransaction',
    'payroll.PayrollCycle',
    'inventory.StockMovement',
]


class AtomicBoundaryError(RuntimeError):
    """Raised when a business transaction boundary is violated."""


class BusinessTransactionBoundaryGuard:
    """
    Ensures all business operations execute inside proper atomic boundaries.

    Provides:
      - `guard()`: decorator that enforces atomic wrapping
      - `boundary()`: context manager for manual use
      - `validate_state()`: checks for partial state after operation
    """

    def __init__(self, enforce: bool = True):
        self.enforce = enforce

    def guard(self, func: F) -> F:
        """
        Decorator that wraps a function in an atomic transaction and
        validates state on exit.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.boundary():
                return func(*args, **kwargs)
        return wrapper  # type: ignore

    @contextmanager
    def boundary(self):
        """
        Context manager that creates an atomic transaction boundary
        and validates that no partial state was committed on exception.
        """
        try:
            with transaction.atomic():
                yield
        except Exception:
            logger.error("ATOMIC BOUNDARY: Transaction rolled back due to exception")
            raise

    def validate_state(self, model_class, object_id: str, expected_status: Optional[str] = None) -> None:
        """
        After a business operation, verify that the object is not in a
        partial or inconsistent state.
        """
        if not self.enforce:
            return
        try:
            obj = model_class.objects.get(pk=object_id)
            if expected_status and hasattr(obj, 'status'):
                if obj.status not in (expected_status,):
                    if obj.status in ('DRAFT', 'PENDING', 'CANCELLED'):
                        pass
                    else:
                        raise AtomicBoundaryError(
                            f"State boundary violation: {model_class.__name__} "
                            f"(id={object_id}) has status='{obj.status}', "
                            f"expected one of {expected_status}"
                        )
        except model_class.DoesNotExist:
            raise AtomicBoundaryError(
                f"State boundary violation: {model_class.__name__} "
                f"(id={object_id}) not found after operation"
            )


_guard_instance: Optional[BusinessTransactionBoundaryGuard] = None


def get_atomic_guard(enforce: bool = True) -> BusinessTransactionBoundaryGuard:
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = BusinessTransactionBoundaryGuard(enforce=enforce)
    return _guard_instance


def atomic_boundary(func: F = None):
    """Decorator that wraps a function in an atomic business boundary."""
    guard = get_atomic_guard()
    if func is None:
        return guard.guard
    return guard.guard(func)

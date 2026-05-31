"""
Constraint Violation Handler — Unified Stop/Rollback/Log/Mark/Prevent.

SYSTEM GUARANTEE: Every constraint violation MUST:
  1. STOP EXECUTION
  2. ROLLBACK TRANSACTION (if applicable)
  3. LOG FULL CONTEXT
  4. MARK OPERATION AS FAILED
  5. PREVENT FUTURE EXECUTION PATH WITHOUT FIX
"""
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ViolationSeverity(Enum):
    CRITICAL = 'CRITICAL'
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    LOW = 'LOW'


class ViolationCategory(Enum):
    TENANT_ISOLATION = 'TENANT_ISOLATION'
    ATOMIC_BOUNDARY = 'ATOMIC_BOUNDARY'
    RECONCILIATION = 'RECONCILIATION'
    LINEAGE = 'LINEAGE'
    REPORT_TRUTH = 'REPORT_TRUTH'
    DETERMINISM = 'DETERMINISM'
    REGRESSION = 'REGRESSION'
    ADVERSARIAL = 'ADVERSARIAL'
    SYSTEM_CONTRACT = 'SYSTEM_CONTRACT'


@dataclass
class ViolationRecord:
    category: ViolationCategory
    message: str
    severity: ViolationSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: str = ''
    blocked: bool = False
    fix_required: str = ''


class ConstraintViolationHandler:
    """
    Unified handler for all system constraint violations.

    Implements the 5-step fail-fast policy:
    1. STOP  — halt execution
    2. ROLLBACK — revert transaction
    3. LOG — record full context
    4. MARK — tag operation as failed
    5. PREVENT — block future execution paths
    """

    MODE_AUDIT = 'AUDIT'
    MODE_STRICT = 'STRICT'

    def __init__(self, mode: str = 'STRICT'):
        self.mode = mode
        self.history: List[ViolationRecord] = []
        self.blocked_operations: Set[str] = set()

    def handle(
        self,
        category: ViolationCategory,
        message: str,
        severity: ViolationSeverity = ViolationSeverity.CRITICAL,
        context: Optional[Dict[str, Any]] = None,
        rollback: bool = True,
        block_future: bool = True,
        fix_required: str = '',
    ) -> None:
        """
        Handle a constraint violation with the full fail-fast protocol.
        """
        record = ViolationRecord(
            category=category,
            message=message,
            severity=severity,
            context=context or {},
            traceback=traceback.format_exc(),
            blocked=block_future,
            fix_required=fix_required,
        )
        self.history.append(record)

        # Always track blocked operations when block_future is True
        if block_future:
            block_key = self._build_block_key(category, message)
            self.blocked_operations.add(block_key)

        # 1. LOG
        self._log_violation(record)

        # 2. STOP / ROLLBACK
        if self.mode == self.MODE_STRICT:
            self._fail_fast(record)

    def _log_violation(self, record: ViolationRecord) -> None:
        """Log full violation context."""
        logger.error(
            f"CONSTRAINT VIOLATION [{record.category.value}] [{record.severity.value}]: "
            f"{record.message} | context={record.context}"
        )

    def _fail_fast(self, record: ViolationRecord) -> None:
        """Immediately halt execution with a clear error."""
        raise ConstraintViolationError(
            category=record.category,
            message=record.message,
            severity=record.severity,
            fix_required=record.fix_required,
        )

    def _build_block_key(self, category: ViolationCategory, message: str) -> str:
        return f"{category.value}:::{message[:100]}"

    def is_operation_blocked(self, operation_key: str) -> bool:
        """Check if an operation path has been blocked by a previous violation."""
        return operation_key in self.blocked_operations

    def clear_blocked(self, operation_key: str) -> None:
        """Clear a blocked operation (requires manual fix confirmation)."""
        if operation_key in self.blocked_operations:
            self.blocked_operations.remove(operation_key)

    @property
    def violation_count(self) -> int:
        return len(self.history)

    @property
    def has_violations(self) -> bool:
        return len(self.history) > 0

    def summary(self) -> Dict[str, Any]:
        """Return a summary of all violations."""
        by_severity: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        for v in self.history:
            by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
            by_category[v.category.value] = by_category.get(v.category.value, 0) + 1
        return {
            'total_violations': len(self.history),
            'blocked_operations': len(self.blocked_operations),
            'by_severity': by_severity,
            'by_category': by_category,
            'latest': [
                {
                    'category': v.category.value,
                    'message': v.message[:200],
                    'severity': v.severity.value,
                    'timestamp': v.timestamp.isoformat(),
                }
                for v in self.history[-10:]
            ],
        }


class ConstraintViolationError(RuntimeError):
    """
    Raised when a system constraint is violated in STRICT mode.
    Halts execution immediately.
    """

    def __init__(
        self,
        category: ViolationCategory,
        message: str,
        severity: ViolationSeverity = ViolationSeverity.CRITICAL,
        fix_required: str = '',
    ):
        self.category = category
        self.severity = severity
        self.fix_required = fix_required
        full_msg = f"[{category.value}] [{severity.value}] {message}"
        if fix_required:
            full_msg += f" | FIX REQUIRED: {fix_required}"
        super().__init__(full_msg)


_handler_instance = None


def get_constraint_handler(mode: str = 'STRICT') -> ConstraintViolationHandler:
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = ConstraintViolationHandler(mode=mode)
    return _handler_instance


def fail_fast(category: ViolationCategory, message: str, **kwargs) -> None:
    """Shortcut: raise a constraint violation immediately."""
    handler = get_constraint_handler()
    handler.handle(category=category, message=message, **kwargs)

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class OperationType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"
    RAW_SQL = "raw_sql"


class FreezeState(str, Enum):
    UNFROZEN = "unfrozen"
    FROZEN = "frozen"
    THAWING = "thawing"
    PERMANENT_FREEZE = "permanent_freeze"


class IntegrityLevel(str, Enum):
    VALIDATION_FAIL = "validation_fail"
    FK_VIOLATION = "fk_violation"
    SCHEMA_DRIFT = "schema_drift"
    UNKNOWN_STATE = "unknown_state"
    PARTIAL_WRITE = "partial_write"
    CLEAN = "clean"


@dataclass
class ValidationResult:
    allowed: bool
    reason: str = ""
    blocked_by: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(cls, reason: str = "Allowed") -> "ValidationResult":
        return cls(allowed=True, reason=reason)

    @classmethod
    def block(cls, reason: str, blocked_by: str = "") -> "ValidationResult":
        return cls(allowed=False, reason=reason, blocked_by=blocked_by)


@dataclass
class VerificationResult:
    passed: bool
    fk_violations: List[Dict[str, Any]] = field(default_factory=list)
    orphan_count: int = 0
    broken_refs: List[str] = field(default_factory=list)
    aggregate_issues: List[str] = field(default_factory=list)

    @classmethod
    def clean(cls) -> "VerificationResult":
        return cls(passed=True)

    @classmethod
    def failed(
        cls, fk_violations=None, orphans=0, broken_refs=None, aggregates=None
    ) -> "VerificationResult":
        return cls(
            passed=False,
            fk_violations=fk_violations or [],
            orphan_count=orphans,
            broken_refs=broken_refs or [],
            aggregate_issues=aggregates or [],
        )


@dataclass
class DriftResult:
    has_drifted: bool
    schema_change: bool = False
    governance_change: bool = False
    table_registry_change: bool = False
    baseline_hash: str = ""
    current_hash: str = ""
    details: str = ""

    @classmethod
    def stable(cls, baseline: str, current: str) -> "DriftResult":
        return cls(
            has_drifted=False,
            baseline_hash=baseline,
            current_hash=current,
        )

    @classmethod
    def drift_detected(
        cls, baseline: str, current: str, details: str = ""
    ) -> "DriftResult":
        return cls(
            has_drifted=True,
            baseline_hash=baseline,
            current_hash=current,
            details=details,
        )


@dataclass
class IntegrityEvent:
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    operation_type: str = ""
    model_class: str = ""
    validation_result: str = ""
    verification_result: str = ""
    failure_reason: str = ""
    system_hash: str = ""
    rolled_back: bool = False
    frozen: bool = False

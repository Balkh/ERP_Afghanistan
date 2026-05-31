import functools
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from django.db import models

from core.integrity.models import (
    IntegrityEvent,
    OperationType,
    VerificationResult,
)

logger = logging.getLogger(__name__)


class IntegrityEngine:
    _instance = None
    _initialized = False

    def __init__(self):
        if not IntegrityEngine._initialized:
            self._gate = None
            self._controller = None
            self._verifier = None
            self._detector = None
            self._rollback = None
            self._freeze = None
            self._ledger = None
            self._enabled = True
            IntegrityEngine._initialized = True

    @classmethod
    def get_instance(cls) -> "IntegrityEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(self):
        from core.integrity.gate import PreWriteValidationGate
        from core.integrity.controller import (
            AutoRollbackEngine,
            PostWriteVerificationLayer,
            TransactionIntegrityController,
        )
        from core.integrity.detector import RealTimeDriftDetector
        from core.integrity.freeze import (
            ImmutableIntegrityLedger,
            SystemFreezeKillSwitch,
        )

        self._gate = PreWriteValidationGate.get_instance()
        self._verifier = PostWriteVerificationLayer.get_instance()
        self._rollback = AutoRollbackEngine.get_instance()
        self._controller = TransactionIntegrityController.get_instance()
        self._controller.configure(self._verifier, self._rollback)
        self._detector = RealTimeDriftDetector.get_instance()
        self._freeze = SystemFreezeKillSwitch.get_instance()
        self._ledger = ImmutableIntegrityLedger.get_instance()

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def enforce_operation(
        self,
        operation_fn: Callable,
        model_class: Optional[Type[models.Model]] = None,
        operation_type: Optional[OperationType] = None,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        verify_after: bool = True,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        ctx = context or {}

        if not self._enabled:
            return {
                "success": True,
                "result": operation_fn(*args, **kwargs),
                "integrity_skipped": True,
            }

        if not self._gate:
            self.configure()

        operation_type_str = operation_type or OperationType.UPDATE
        model_label = (
            model_class._meta.label_lower if model_class else "unknown"
        )

        freeze_check = self._freeze.require_unfrozen()
        if freeze_check:
            self._ledger.log(
                operation_type=operation_type_str,
                model_class=model_label,
                validation_result="BLOCKED",
                failure_reason=freeze_check["error"],
                frozen=True,
            )
            return {
                "success": False,
                "error": freeze_check["error"],
                "freeze_state": freeze_check,
            }

        if model_class:
            validation = self._gate.validate_write(
                model_class=model_class,
                operation_type=operation_type_str,
                data=data,
                context=ctx,
            )
            if not validation.allowed:
                self._ledger.log(
                    operation_type=operation_type_str,
                    model_class=model_label,
                    validation_result="BLOCKED",
                    failure_reason=validation.reason,
                )
                return {
                    "success": False,
                    "error": validation.reason,
                    "blocked_by": validation.blocked_by,
                    "validation": validation,
                }

        drift_before = self._detector.compute_full_hash()

        result = self._controller.execute_atomic(
            operation_fn=operation_fn,
            model_class=model_class,
            verify_after=verify_after,
            *args,
            **kwargs,
        )

        if not result.get("success", False):
            self._ledger.log(
                operation_type=operation_type_str,
                model_class=model_label,
                validation_result="ALLOWED",
                verification_result="FAIL",
                failure_reason=result.get("error", ""),
                rolled_back=True,
            )

            if self._detector.get_baseline() is not None:
                drift = self._detector.detect_drift()
                if drift.has_drifted:
                    self._freeze.freeze(
                        reason=f"Drift detected after failed operation: "
                        f"{drift.details}"
                    )
            return result

        post_hash = self._detector.compute_full_hash()
        schema_changed = (
            drift_before["schema"] != post_hash["schema"]
            or drift_before["table_registry"]
            != post_hash["table_registry"]
        )

        integrity_level = "CLEAN"
        if schema_changed:
            integrity_level = "SCHEMA_CHANGE"
            logger.warning(
                f"[INTEGRITY] Schema change detected: "
                f"op={operation_type_str}, model={model_label}"
            )

        if self._detector.get_baseline() is not None:
            drift = self._detector.detect_drift()
            if drift.has_drifted:
                self._freeze.freeze(
                    reason=f"Post-operation drift: {drift.details}"
                )
                self._ledger.log(
                    operation_type=operation_type_str,
                    model_class=model_label,
                    validation_result="ALLOWED",
                    verification_result="PASS",
                    failure_reason=f"Drift frozen: {drift.details}",
                    frozen=True,
                )
                return {
                    "success": True,
                    "result": result.get("result"),
                    "integrity_level": "DRIFT_FROZEN",
                    "drift": drift,
                }

        self._ledger.log(
            operation_type=operation_type_str,
            model_class=model_label,
            validation_result="ALLOWED",
            verification_result="PASS",
            system_hash=str(post_hash),
        )

        return {
            "success": True,
            "result": result.get("result"),
            "integrity_level": integrity_level,
        }


def integrity_guard(
    model_class: Optional[Type[models.Model]] = None,
    operation_type: Optional[OperationType] = None,
    verify_after: bool = True,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            engine = IntegrityEngine.get_instance()
            if not engine.is_enabled():
                return func(*args, **kwargs)
            data = kwargs.get("data") or (
                args[1] if len(args) > 1 else None
            )
            result = engine.enforce_operation(
                operation_fn=func if not model_class else lambda: func(*args, **kwargs),
                model_class=model_class,
                operation_type=operation_type,
                data=data if isinstance(data, dict) else None,
                verify_after=verify_after,
            )
            if not result.get("success", False):
                raise RuntimeError(result.get("error", "Integrity enforcement failed"))
            return result.get("result")
        return wrapper
    return decorator


def require_integrity(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        engine = IntegrityEngine.get_instance()
        if not engine.is_enabled():
            engine.configure()
            engine.enable()
        return func(*args, **kwargs)
    return wrapper

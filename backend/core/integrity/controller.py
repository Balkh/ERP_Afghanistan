import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from django.db import connection, models, transaction

from core.integrity.models import (
    VerificationResult,
)

logger = logging.getLogger(__name__)


class TransactionIntegrityController:
    _instance = None
    _initialized = False

    def __init__(self):
        if not TransactionIntegrityController._initialized:
            self._post_verifier: Optional["PostWriteVerificationLayer"] = None
            self._rollback_engine: Optional["AutoRollbackEngine"] = None
            TransactionIntegrityController._initialized = True

    @classmethod
    def get_instance(cls) -> "TransactionIntegrityController":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(
        self,
        verifier: "PostWriteVerificationLayer",
        rollback_engine: "AutoRollbackEngine",
    ):
        self._post_verifier = verifier
        self._rollback_engine = rollback_engine

    def execute_atomic(
        self,
        operation_fn: Callable,
        model_class: Optional[Type[models.Model]] = None,
        verify_after: bool = True,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        with transaction.atomic():
            try:
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = ON")

                result = operation_fn(*args, **kwargs)

                if verify_after and self._post_verifier and model_class:
                    ver_result = self._post_verifier.verify_model(model_class)
                    if not ver_result.passed:
                        reason = f"Post-write verification failed: {ver_result.fk_violations}"
                        if self._rollback_engine:
                            self._rollback_engine.trigger_rollback(
                                reason=reason,
                                operation=str(operation_fn.__name__),
                                model=str(model_class._meta.label_lower),
                            )
                        transaction.set_rollback(True)
                        return {
                            "success": False,
                            "error": reason,
                            "verification": ver_result,
                        }

                return {"success": True, "result": result}

            except Exception as e:
                if self._rollback_engine:
                    self._rollback_engine.trigger_rollback(
                        reason=str(e),
                        operation=str(operation_fn.__name__),
                        model=str(
                            model_class._meta.label_lower
                            if model_class
                            else "unknown"
                        ),
                    )
                transaction.set_rollback(True)
                return {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }


class PostWriteVerificationLayer:
    _instance = None
    _initialized = False

    def __init__(self):
        if not PostWriteVerificationLayer._initialized:
            PostWriteVerificationLayer._initialized = True

    @classmethod
    def get_instance(cls) -> "PostWriteVerificationLayer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def verify_fk_integrity(self) -> List[Dict[str, Any]]:
        violations = []
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_key_check")
            rows = cursor.fetchall()
            for row in rows:
                violations.append({
                    "table": row[0],
                    "rowid": row[1],
                    "parent": row[2],
                    "fkid": row[3],
                })
        return violations

    def verify_no_orphans(
        self, model_class: Type[models.Model]
    ) -> int:
        orphans = 0
        for field in model_class._meta.fields:
            if field.is_relation and field.remote_field:
                related_model = field.related_model
                if related_model:
                    fk_name = field.name if hasattr(field, "column") else field.attname
                    fk_column = getattr(field, "column", fk_name)
                    try:
                        orphans += model_class.objects.filter(
                            **{f"{fk_name}__isnull": False}
                        ).exclude(
                            **{f"{fk_name}__in": related_model.objects.values("pk")}
                        ).count()
                    except Exception:
                        pass
        return orphans

    def verify_no_broken_refs(
        self, model_class: Type[models.Model]
    ) -> List[str]:
        broken = []
        for field in model_class._meta.fields:
            if field.is_relation and field.remote_field:
                fk_name = field.name
                try:
                    bad = model_class.objects.filter(
                        **{f"{fk_name}__isnull": False}
                    ).exclude(
                        **{f"{fk_name}__in": field.related_model.objects.values("pk")}
                    )
                    if bad.exists():
                        broken.append(
                            f"{model_class._meta.label_lower}.{fk_name}: "
                            f"{bad.count()} broken refs"
                        )
                except Exception:
                    pass
        return broken

    def verify_no_invalid_aggregates(
        self, model_class: Type[models.Model]
    ) -> List[str]:
        issues = []
        for field in model_class._meta.fields:
            if hasattr(field, "validators"):
                continue
            name = field.name
            null_type = getattr(field, "null", False)
            if not null_type:
                try:
                    null_count = model_class.objects.filter(
                        **{f"{name}__isnull": True}
                    ).count()
                    if null_count > 0:
                        issues.append(
                            f"{model_class._meta.label_lower}.{name}: "
                            f"{null_count} null values in non-nullable field"
                        )
                except Exception:
                    pass
        return issues

    def verify_model(
        self, model_class: Type[models.Model]
    ) -> VerificationResult:
        try:
            fk_issues = self.verify_fk_integrity()
            if fk_issues:
                return VerificationResult.failed(fk_violations=fk_issues)

            orphans = self.verify_no_orphans(model_class)
            if orphans > 0:
                return VerificationResult.failed(
                    orphans=orphans,
                    fk_violations=fk_issues,
                )

            broken = self.verify_no_broken_refs(model_class)
            aggregates = self.verify_no_invalid_aggregates(model_class)

            if broken or aggregates or fk_issues or orphans > 0:
                return VerificationResult.failed(
                    fk_violations=fk_issues,
                    orphans=orphans,
                    broken_refs=broken,
                    aggregates=aggregates,
                )

            return VerificationResult.clean()

        except Exception as e:
            return VerificationResult.failed(
                fk_violations=[{"error": str(e)}]
            )


class AutoRollbackEngine:
    _instance = None
    _initialized = False

    def __init__(self):
        if not AutoRollbackEngine._initialized:
            self._failure_log: List[Dict[str, Any]] = []
            AutoRollbackEngine._initialized = True

    @classmethod
    def get_instance(cls) -> "AutoRollbackEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def trigger_rollback(
        self,
        reason: str,
        operation: str = "",
        model: str = "",
    ) -> Dict[str, Any]:
        entry = {
            "reason": reason,
            "operation": operation,
            "model": model,
            "rolled_back": True,
            "action": "ROLLBACK",
        }
        self._failure_log.append(entry)
        logger.error(
            f"[INTEGRITY] ROLLBACK triggered: {reason} "
            f"(op={operation}, model={model})"
        )
        return entry

    def get_failure_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._failure_log[-limit:]

    def clear_failure_log(self):
        self._failure_log.clear()

    def failure_count(self) -> int:
        return len(self._failure_log)

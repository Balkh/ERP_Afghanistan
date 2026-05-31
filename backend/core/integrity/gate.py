import logging
from typing import Any, Dict, List, Optional, Set, Type

from django.db import models

from core.integrity.models import (
    OperationType,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class PreWriteValidationGate:
    _instance = None
    _initialized = False

    SYSTEM_TABLE_PREFIXES: Set[str] = {
        "django_", "auth_", "sqlite_",
    }

    SYSTEM_MODEL_LABELS: Set[str] = {
        "django.migrations", "django.content_type", "django.session",
        "django.admin_log", "django.site",
        "auth.permission", "auth.group", "auth.user",
        "contenttypes.contenttype",
        "sessions.session",
        "admin.logentry",
    }

    CRITICAL_OPERATIONS_BLOCKED: Set[str] = {
        "delete", "bulk_delete", "raw_sql",
    }

    def __init__(self):
        if not PreWriteValidationGate._initialized:
            self._custom_rules: List[dict] = []
            PreWriteValidationGate._initialized = True

    @classmethod
    def get_instance(cls) -> "PreWriteValidationGate":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_rule(
        self,
        rule_id: str,
        check_fn,
        description: str = "",
        severity: str = "critical",
    ):
        self._custom_rules = [
            r for r in self._custom_rules if r["rule_id"] != rule_id
        ]
        self._custom_rules.append({
            "rule_id": rule_id,
            "check_fn": check_fn,
            "description": description,
            "severity": severity,
        })

    def clear_rules(self):
        self._custom_rules.clear()

    def validate_write(
        self,
        model_class: Type[models.Model],
        operation_type: OperationType,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        ctx = context or {}

        label = model_class._meta.label_lower
        table = model_class._meta.db_table

        # 1. Block system table writes
        if table.startswith(tuple(self.SYSTEM_TABLE_PREFIXES)):
            return ValidationResult.block(
                f"System table writes blocked: {table}",
                blocked_by="table_whitelist",
            )

        if label in self.SYSTEM_MODEL_LABELS:
            return ValidationResult.block(
                f"System model writes blocked: {label}",
                blocked_by="model_whitelist",
            )

        # 2. Block critical DELETE operations
        if operation_type in self.CRITICAL_OPERATIONS_BLOCKED:
            return ValidationResult.block(
                f"Critical operation blocked: {operation_type} on {label}",
                blocked_by="operation_safety",
            )

        # 3. Schema compliance — model must have expected fields
        if data:
            model_fields = {f.name for f in model_class._meta.fields}
            unknown_fields = set(data.keys()) - model_fields
            if unknown_fields:
                return ValidationResult.block(
                    f"Unknown fields in write: {unknown_fields}",
                    blocked_by="schema_compliance",
                )

        # 4. Business constraints — FK refs must exist
        if data:
            for field in model_class._meta.fields:
                if field.is_relation and field.name in data:
                    ref_value = data[field.name]
                    if ref_value is not None:
                        related_model = field.related_model
                        if related_model and not related_model.objects.filter(
                            pk=ref_value
                        ).exists():
                            return ValidationResult.block(
                                f"FK reference not found: {field.name}={ref_value}",
                                blocked_by="business_constraint",
                            )

        # 5. Custom rules
        for rule in self._custom_rules:
            try:
                allowed, reason = rule["check_fn"]({
                    "model_class": model_class,
                    "operation_type": operation_type,
                    "data": data,
                    "context": ctx,
                })
                if not allowed:
                    return ValidationResult.block(
                        reason or f"Custom rule blocked: {rule['rule_id']}",
                        blocked_by=rule["rule_id"],
                    )
            except Exception as e:
                return ValidationResult.block(
                    f"Custom rule error: {e}",
                    blocked_by=rule["rule_id"],
                )

        return ValidationResult.allow()

    def validate_bulk(
        self,
        operations: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        return [
            self.validate_write(
                op["model_class"],
                op["operation_type"],
                op.get("data"),
                op.get("context"),
            )
            for op in operations
        ]

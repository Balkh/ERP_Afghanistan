"""
Section 2 — Safe Migration Governance.
Pre-deployment validation of migration safety.
"""
from typing import Dict, List
from dataclasses import dataclass

DESTRUCTIVE_OPERATIONS = {"DropField", "RemoveField", "DeleteModel", "AlterField"}

FORBIDDEN_MODELS = {
    "accounting.account", "accounting.journalentry", "accounting.journalentryline",
    "inventory.batch", "inventory.product",
    "audit", "governance", "core.integrity",
}

FORBIDDEN_TABLES = {
    "accounting_account", "accounting_journalentry", "accounting_journalentryline",
}


@dataclass
class MigrationCheck:
    name: str
    safe: bool
    detail: str


@dataclass
class MigrationSafety:
    all_safe: bool
    blocked: List[str]
    warnings: List[str]
    safe_count: int


def _get_unapplied_migrations():
    try:
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        executor = MigrationExecutor(connections["default"])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        return [(m[0].app_label, m[0].name, m[0].migration) for m in plan]
    except Exception:
        return []


def _inspect_migration_operations(migration) -> List[Dict]:
    ops = []
    if hasattr(migration, "operations"):
        for op in migration.operations:
            op_info = {"type": type(op).__name__}
            if hasattr(op, "model_name"):
                op_info["model"] = op.model_name
            if hasattr(op, "name"):
                op_info["field"] = op.name
            ops.append(op_info)
    return ops


def check_migration_safety() -> MigrationSafety:
    blocked = []
    warnings = []
    safe_count = 0

    pending = _get_unapplied_migrations()
    if not pending:
        return MigrationSafety(all_safe=True, blocked=[], warnings=[], safe_count=0)

    for app_label, name, migration in pending:
        ops = _inspect_migration_operations(migration)
        for op in ops:
            op_type = op["type"]
            model = op.get("model", "")
            full_model = f"{app_label}.{model}" if model else app_label

            if op_type in DESTRUCTIVE_OPERATIONS:
                desc = (
                    f"Destructive operation {op_type} on {full_model} "
                    f"({'field: ' + op.get('field', '') if op.get('field') else ''})"
                )
                blocked.append(desc)
            elif full_model in FORBIDDEN_MODELS or any(
                f"{app_label}_{model}".startswith(t) for t in FORBIDDEN_TABLES
            ):
                blocked.append(
                    f"Migration touches protected model: {full_model} ({op_type})"
                )
            elif op_type in {"AlterField", "AddField"}:
                desc = (
                    f"Schema change on {full_model}.{op.get('field', '')} ({op_type})"
                )
                warnings.append(desc)
            else:
                safe_count += 1

    all_safe = len(blocked) == 0
    return MigrationSafety(
        all_safe=all_safe,
        blocked=blocked,
        warnings=warnings,
        safe_count=safe_count,
    )


RISK_LEVELS = {
    "core": "critical",
    "accounting": "high",
    "payments": "high",
    "inventory": "high",
    "sales": "medium",
    "purchases": "medium",
    "hr": "low",
    "payroll": "medium",
    "governance": "medium",
    "config": "medium",
    "backup": "low",
}


def assess_migration_risk(app_label: str) -> str:
    """Return risk level for a given app label."""
    return RISK_LEVELS.get(app_label, "low")

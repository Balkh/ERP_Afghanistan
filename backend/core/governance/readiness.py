"""
Enterprise System Readiness Validator.

Validates all runtime prerequisites before allowing production operation.
Read-only — aggregates state from existing subsystems, never mutates.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from django.conf import settings


READINESS_VERSION = "1.0.0"


@dataclass
class ReadinessCheck:
    name: str
    status: str  # pass | warn | fail
    message: str = ""
    detail: str = ""


@dataclass
class ReadinessReport:
    overall: str  # ready | degraded | blocked
    checks: List[ReadinessCheck] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")

    @property
    def total(self) -> int:
        return len(self.checks)


def check_rbac_seeded() -> ReadinessCheck:
    """Verify roles and permissions are seeded."""
    try:
        from security.models import Role, Permission
        role_count = Role.objects.count()
        perm_count = Permission.objects.count()
        if role_count == 0:
            return ReadinessCheck(
                name="rbac_roles_seeded",
                status="fail",
                message="No roles found. System cannot determine UI access.",
                detail="Run: python manage.py seed_roles"
            )
        if perm_count == 0:
            return ReadinessCheck(
                name="rbac_permissions_seeded",
                status="fail",
                message="No permissions found.",
                detail="Run: python manage.py seed_roles"
            )
        return ReadinessCheck(
            name="rbac_roles_seeded",
            status="pass",
            message=f"{role_count} roles, {perm_count} permissions seeded",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="rbac_roles_seeded",
            status="fail",
            message=f"Cannot check RBAC state: {e}",
            detail=""
        )


def check_admin_has_role() -> ReadinessCheck:
    """Verify admin users have at least one role assigned."""
    try:
        from django.contrib.auth.models import User
        from security.models import UserRole
        admins = User.objects.filter(is_superuser=True)
        if not admins.exists():
            return ReadinessCheck(
                name="admin_role_assignment",
                status="warn",
                message="No superuser accounts exist.",
                detail=""
            )
        missing = 0
        for admin in admins:
            if not UserRole.objects.filter(user=admin).exists():
                missing += 1
        if missing > 0:
            return ReadinessCheck(
                name="admin_role_assignment",
                status="fail",
                message=f"{missing} superuser(s) have no roles. UI access will be blocked.",
                detail="Run: python manage.py seed_roles (assigns Admin role to new superusers)"
            )
        return ReadinessCheck(
            name="admin_role_assignment",
            status="pass",
            message="All superusers have roles assigned",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="admin_role_assignment",
            status="fail",
            message=f"Cannot check admin roles: {e}",
            detail=""
        )


def check_license_state() -> ReadinessCheck:
    """Validate license state for production readiness."""
    try:
        from licensing.validator import LicenseValidator
        v = LicenseValidator()
        v.validate()
        info = v.get_info()
        mode = info.get("mode", "unknown")
        is_valid = info.get("is_valid", False)

        if mode == "licensed":
            return ReadinessCheck(
                name="license_state",
                status="pass",
                message="Valid license installed",
                detail=""
            )
        if mode == "trial":
            days = info.get("days_remaining", 0)
            if days <= 3:
                return ReadinessCheck(
                    name="license_state",
                    status="fail",
                    message=f"Trial expires in {days} day(s). Install a license immediately.",
                    detail=""
                )
            return ReadinessCheck(
                name="license_state",
                status="warn",
                message=f"Running in trial mode ({days} days remaining)",
                detail="Install a license for production deployment"
            )
        if mode == "limited":
            return ReadinessCheck(
                name="license_state",
                status="fail",
                message="License expired or invalid. System in limited mode.",
                detail=""
            )
        return ReadinessCheck(
            name="license_state",
            status="warn",
            message=f"Unknown license mode: {mode}",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="license_state",
            status="fail",
            message=f"Cannot validate license: {e}",
            detail=""
        )


def check_secret_key() -> ReadinessCheck:
    """Verify SECRET_KEY is not the insecure default."""
    key = getattr(settings, "SECRET_KEY", "")
    if not key or key == "django-insecure-please-change-in-production":
        return ReadinessCheck(
            name="secret_key_strength",
            status="fail" if not getattr(settings, "DEBUG", True) else "warn",
            message="SECRET_KEY is set to the insecure default.",
            detail="Set a secure SECRET_KEY via .env or environment variable"
        )
    if len(key) < 50:
        return ReadinessCheck(
            name="secret_key_strength",
            status="warn",
            message="SECRET_KEY is shorter than 50 characters.",
            detail=""
        )
    return ReadinessCheck(
        name="secret_key_strength",
        status="pass",
        message="SECRET_KEY is configured",
        detail=""
    )


def check_ssl_config() -> ReadinessCheck:
    """Verify SSL configuration for production."""
    debug = getattr(settings, "DEBUG", True)
    if debug:
        return ReadinessCheck(
            name="ssl_configuration",
            status="warn",
            message="DEBUG=True. SSL checks skipped.",
            detail="Enable DEBUG=False and configure SSL for production"
        )
    ssl_redirect = getattr(settings, "SECURE_SSL_REDIRECT", False)
    if not ssl_redirect:
        return ReadinessCheck(
            name="ssl_configuration",
            status="fail",
            message="SECURE_SSL_REDIRECT is not enabled.",
            detail="Set SECURE_SSL_REDIRECT=True for production"
        )
    return ReadinessCheck(
        name="ssl_configuration",
        status="pass",
        message="SSL is properly configured",
        detail=""
    )


def check_migrations_applied() -> ReadinessCheck:
    """Verify all database migrations have been applied."""
    try:
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        executor = MigrationExecutor(connections["default"])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        pending = len(plan)
        if pending > 0:
            apps_list = sorted(set(
                mig[0].__module__.split(".")[0] if hasattr(mig[0], "__module__") else str(mig[0])
                for mig, _ in plan
            ))
            return ReadinessCheck(
                name="migration_consistency",
                status="fail",
                message=f"{pending} pending migration(s) in: {', '.join(apps_list)}",
                detail="Run: python manage.py migrate"
            )
        return ReadinessCheck(
            name="migration_consistency",
            status="pass",
            message="All migrations applied",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="migration_consistency",
            status="fail",
            message=f"Cannot check migrations: {e}",
            detail=""
        )


def check_database_connectivity() -> ReadinessCheck:
    """Verify database connection is alive."""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        if row and row[0] == 1:
            return ReadinessCheck(
                name="database_connectivity",
                status="pass",
                message="Database connection is alive",
                detail=""
            )
        return ReadinessCheck(
            name="database_connectivity",
            status="fail",
            message="Database returned unexpected response",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="database_connectivity",
            status="fail",
            message=f"Cannot connect to database: {e}",
            detail=""
        )


def check_dependency_jdatetime() -> ReadinessCheck:
    """Verify jdatetime library availability for Jalali calendar."""
    try:
        import jdatetime  # noqa: F401
        return ReadinessCheck(
            name="dependency_jdatetime",
            status="pass",
            message="jdatetime is available for Jalali date conversion",
            detail=""
        )
    except ImportError:
        return ReadinessCheck(
            name="dependency_jdatetime",
            status="fail",
            message="jdatetime is not installed. Jalali calendar functions will fail.",
            detail="Run: pip install jdatetime"
        )


def check_observability_readiness() -> ReadinessCheck:
    """Verify observability infrastructure is functional."""
    try:
        from core.logging.logger import Logger
        logger = Logger.get("readiness")
        logger.info("Readiness: observability logger check")
        return ReadinessCheck(
            name="observability_readiness",
            status="pass",
            message="Observability logging system is operational",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="observability_readiness",
            status="warn",
            message=f"Observability check failed: {e}",
            detail=""
        )


def check_event_bus() -> ReadinessCheck:
    """Verify enterprise event bus is registered."""
    try:
        from core.events import EnterpriseEventBus
        handler_count = sum(len(handlers) for handlers in EnterpriseEventBus._subscribers.values())
        return ReadinessCheck(
            name="event_bus_readiness",
            status="pass",
            message=f"EnterpriseEventBus active ({handler_count} handler(s))",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="event_bus_readiness",
            status="warn",
            message=f"Event bus check failed: {e}",
            detail=""
        )


def check_accounting_integrity() -> ReadinessCheck:
    """Verify no posted journal entries have unbalanced debits/credits."""
    try:
        from accounting.models import JournalEntry
        from django.db.models import Sum
        errors = 0
        posted_count = JournalEntry.objects.filter(is_posted=True).count()
        for je in JournalEntry.objects.filter(is_posted=True):
            totals = je.lines.aggregate(
                debit_total=Sum("debit"),
                credit_total=Sum("credit")
            )
            if (totals["debit_total"] or 0) != (totals["credit_total"] or 0):
                errors += 1
                if errors >= 5:
                    break
        if errors > 0:
            return ReadinessCheck(
                name="accounting_integrity",
                status="fail",
                message=f"{errors} posted journal entr(y/ies) have unbalanced debits/credits",
                detail="Financial data integrity compromised"
            )
        return ReadinessCheck(
            name="accounting_integrity",
            status="pass",
            message=f"All {posted_count} posted journal entries are balanced",
            detail=""
        )
    except Exception as e:
        return ReadinessCheck(
            name="accounting_integrity",
            status="warn",
            message=f"Cannot verify accounting integrity: {e}",
            detail=""
        )


def get_full_readiness(include_integrity: bool = True) -> ReadinessReport:
    """Run all readiness checks and produce a comprehensive report."""
    checks = [
        check_database_connectivity(),
        check_migrations_applied(),
        check_secret_key(),
        check_ssl_config(),
        check_rbac_seeded(),
        check_admin_has_role(),
        check_license_state(),
        check_dependency_jdatetime(),
        check_observability_readiness(),
        check_event_bus(),
    ]
    if include_integrity:
        checks.append(check_accounting_integrity())

    blockers = [c.message for c in checks if c.status == "fail"]
    warnings_list = [c.message for c in checks if c.status == "warn"]

    recommendations = []
    if any(c.name == "rbac_roles_seeded" and c.status == "fail" for c in checks):
        recommendations.append("Run `python manage.py seed_roles` to initialize roles and permissions")
    if any(c.name == "dependency_jdatetime" and c.status == "fail" for c in checks):
        recommendations.append("Run `pip install jdatetime` to enable Jalali calendar support")
    if any(c.name == "license_state" and c.status in ("fail", "warn") for c in checks):
        recommendations.append("Install a valid device license for production deployment")
    if any(c.name == "secret_key_strength" and c.status == "fail" for c in checks):
        recommendations.append("Set a secure SECRET_KEY in .env or environment variables")
    if any(c.name == "ssl_configuration" and c.status == "fail" for c in checks):
        recommendations.append("Enable SECURE_SSL_REDIRECT for production")

    overall = "blocked" if blockers else ("degraded" if warnings_list else "ready")

    return ReadinessReport(
        overall=overall,
        checks=checks,
        blockers=blockers,
        warnings=warnings_list,
        recommendations=recommendations,
    )

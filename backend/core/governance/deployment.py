"""
Phase 1 — Deployment Certification.
Validates deterministic, safe deployments with atomic guardrails.
"""
import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel, PriorityTier

logger = logging.getLogger("erp.governance.deployment")

DEPLOYMENT_VERSION = "1.0.0"

DEPLOYMENT_FINGERPRINT_FIELDS = [
    "python_version", "django_version", "db_engine", "env_profile",
    "policy_count", "invariant_count", "migration_count", "secret_key_hash",
    "debug_mode", "ssl_enabled", "jdatetime_installed",
]


@dataclass
class DeploymentCheck:
    name: str
    status: str  # pass | warn | fail
    message: str = ""
    detail: str = ""


@dataclass
class DeploymentFingerprint:
    fingerprint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    python_version: str = ""
    django_version: str = ""
    db_engine: str = ""
    env_profile: str = ""
    policy_count: int = 0
    invariant_count: int = 0
    migration_count: int = 0
    secret_key_hash: str = ""
    debug_mode: bool = True
    ssl_enabled: bool = False
    jdatetime_installed: bool = False
    checksum: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def compute_checksum(self) -> str:
        raw = "|".join(str(getattr(self, f, "")) for f in DEPLOYMENT_FINGERPRINT_FIELDS)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class DeploymentReport:
    overall: str = "unknown"  # pass | warn | blocked
    fingerprint: DeploymentFingerprint = field(default_factory=DeploymentFingerprint)
    checks: List[DeploymentCheck] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    config_summary: dict = field(default_factory=dict)
    migration_summary: dict = field(default_factory=dict)
    governance_status: dict = field(default_factory=dict)
    operational_risk: str = "unknown"
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class DeploymentValidator:
    """Validates deployment prerequisites. Read-only, no system mutation."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def validate_environment(self) -> DeploymentCheck:
        env = self._kernel.environment.profile
        if env == "production":
            debug = self._get_debug()
            if debug:
                return DeploymentCheck(
                    name="environment",
                    status="fail",
                    message="Production deployment with DEBUG=True is insecure",
                )
            ssl = self._get_ssl()
            if not ssl:
                return DeploymentCheck(
                    name="environment",
                    status="fail",
                    message="Production deployment without SSL is insecure",
                )
        return DeploymentCheck(
            name="environment",
            status="pass",
            message=f"Environment '{env}' is valid",
        )

    def validate_dependencies(self) -> DeploymentCheck:
        missing = []
        try:
            import jdatetime  # noqa: F401
        except ImportError:
            missing.append("jdatetime")
        try:
            from django.conf import settings  # noqa: F401
        except ImportError:
            missing.append("django")
        if missing:
            return DeploymentCheck(
                name="dependencies",
                status="fail",
                message=f"Missing dependencies: {', '.join(missing)}",
            )
        return DeploymentCheck(
            name="dependencies",
            status="pass",
            message="All critical dependencies available",
        )

    def validate_migrations(self) -> DeploymentCheck:
        try:
            from django.db.migrations.executor import MigrationExecutor
            from django.db import connections
            executor = MigrationExecutor(connections["default"])
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            pending = len(plan)
            if pending > 0:
                return DeploymentCheck(
                    name="migrations",
                    status="fail",
                    message=f"{pending} pending migration(s)",
                )
            return DeploymentCheck(
                name="migrations",
                status="pass",
                message="All migrations applied",
            )
        except Exception as e:
            return DeploymentCheck(
                name="migrations",
                status="fail",
                message=f"Cannot verify migrations: {e}",
            )

    def validate_config(self) -> DeploymentCheck:
        try:
            from django.conf import settings
            key = getattr(settings, "SECRET_KEY", "")
            if not key or key == "django-insecure-please-change-in-production":
                return DeploymentCheck(
                    name="config",
                    status="fail",
                    message="SECRET_KEY is insecure default",
                )
            if len(key) < 50:
                return DeploymentCheck(
                    name="config",
                    status="warn",
                    message="SECRET_KEY shorter than 50 characters",
                )
            return DeploymentCheck(
                name="config",
                status="pass",
                message="Configuration is valid",
            )
        except Exception as e:
            return DeploymentCheck(
                name="config",
                status="fail",
                message=f"Config check error: {e}",
            )

    def validate_governance(self) -> DeploymentCheck:
        health = self._kernel.health()
        if health.get("failsafe_mode"):
            return DeploymentCheck(
                name="governance",
                status="warn",
                message="Governance in failsafe mode — degraded enforcement",
            )
        if health.get("policies", 0) == 0:
            return DeploymentCheck(
                name="governance",
                status="fail",
                message="No governance policies registered",
            )
        if health.get("invariants", 0) == 0:
            return DeploymentCheck(
                name="governance",
                status="warn",
                message="No invariants registered",
            )
        return DeploymentCheck(
            name="governance",
            status="pass",
            message=f"{health['policies']} policies, {health['invariants']} invariants",
        )

    def validate_secret(self) -> DeploymentCheck:
        try:
            from django.conf import settings
            key = getattr(settings, "SECRET_KEY", "")
            if not key:
                return DeploymentCheck(
                    name="secret",
                    status="fail",
                    message="SECRET_KEY is empty",
                )
            return DeploymentCheck(
                name="secret",
                status="pass",
                message="SECRET_KEY is configured",
            )
        except Exception as e:
            return DeploymentCheck(
                name="secret",
                status="fail",
                message=f"Secret check error: {e}",
            )

    def validate_event_bus(self) -> DeploymentCheck:
        try:
            from core.governance.events import get_event_bus
            bus = get_event_bus()
            _ = bus.summary()
            return DeploymentCheck(
                name="event_bus",
                status="pass",
                message="Governance event bus is ready",
            )
        except Exception as e:
            return DeploymentCheck(
                name="event_bus",
                status="fail",
                message=f"Event bus not ready: {e}",
            )

    def get_fingerprint(self) -> DeploymentFingerprint:
        fp = DeploymentFingerprint()
        try:
            import sys; fp.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        except Exception: pass
        try:
            import django; fp.django_version = django.get_version()
        except Exception: pass
        try:
            from django.conf import settings
            fp.debug_mode = getattr(settings, "DEBUG", True)
            fp.ssl_enabled = getattr(settings, "SECURE_SSL_REDIRECT", False)
            key = getattr(settings, "SECRET_KEY", "")
            fp.secret_key_hash = hashlib.sha256(key.encode()).hexdigest()[:8] if key else ""
        except Exception: pass
        try:
            from django.db import connection
            fp.db_engine = connection.vendor
        except Exception: pass
        try:
            import jdatetime; fp.jdatetime_installed = True
        except Exception: pass
        fp.env_profile = self._kernel.environment.profile
        fp.policy_count = self._kernel.policies.count()
        fp.invariant_count = self._kernel.invariants.count()
        try:
            from django.db.migrations.executor import MigrationExecutor
            from django.db import connections
            executor = MigrationExecutor(connections["default"])
            fp.migration_count = len(executor.loader.graph.leaf_nodes())
        except Exception: pass
        fp.checksum = fp.compute_checksum()
        return fp

    def run_all(self) -> DeploymentReport:
        checks = [
            self.validate_environment(),
            self.validate_dependencies(),
            self.validate_migrations(),
            self.validate_config(),
            self.validate_governance(),
            self.validate_secret(),
            self.validate_event_bus(),
        ]
        blockers = [c.message for c in checks if c.status == "fail"]
        warnings = [c.message for c in checks if c.status == "warn"]
        overall = "blocked" if blockers else ("warn" if warnings else "pass")
        fp = self.get_fingerprint()

        governance_status = self._kernel.health()
        config_summary = {"secret_configured": bool(fp.secret_key_hash)}
        migration_summary = {"migration_count": fp.migration_count}
        operational_risk = "high" if blockers else ("medium" if warnings else "low")

        return DeploymentReport(
            overall=overall,
            fingerprint=fp,
            checks=checks,
            blockers=blockers,
            warnings=warnings,
            config_summary=config_summary,
            migration_summary=migration_summary,
            governance_status=governance_status,
            operational_risk=operational_risk,
        )

    def _get_debug(self) -> bool:
        try:
            from django.conf import settings
            return getattr(settings, "DEBUG", True)
        except Exception:
            return True

    def _get_ssl(self) -> bool:
        try:
            from django.conf import settings
            return getattr(settings, "SECURE_SSL_REDIRECT", False)
        except Exception:
            return False


class AtomicDeploymentValidator:
    """Prevents partial deployment activation, partial migrations, partial governance."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()
        self._validator = DeploymentValidator(self._kernel)

    def deployment_blocked(self) -> Tuple[bool, List[str]]:
        report = self._validator.run_all()
        if report.overall == "blocked":
            return True, report.blockers
        return False, []

    def validate_atomic(self) -> Tuple[bool, str]:
        try:
            from django.db.migrations.executor import MigrationExecutor
            from django.db import connections
            executor = MigrationExecutor(connections["default"])
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if plan:
                return False, f"Cannot deploy atomically: {len(plan)} pending migrations"
            policies = self._kernel.policies.count()
            invariants = self._kernel.invariants.count()
            if policies == 0 or invariants == 0:
                return False, "Cannot deploy atomically: governance not fully registered"
            return True, "Atomic deployment validated — all systems consistent"
        except Exception as e:
            return False, f"Atomic validation error: {e}"

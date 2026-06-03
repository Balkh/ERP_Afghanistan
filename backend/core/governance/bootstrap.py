"""
Enterprise Bootstrap Orchestrator.

Automates first-run initialization and validates startup dependencies.
Idempotent — safe to run multiple times.
"""
import logging
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db import transaction

logger = logging.getLogger("erp.system.bootstrap")

BOOTSTRAP_VERSION = "1.0.0"


class BootstrapError(Exception):
    """Raised when a bootstrap step fails irrecoverably."""


class BootstrapOrchestrator:
    """
    Coordinates first-run initialization steps.

    Steps are idempotent and safe to re-run:
    1. Seed roles and permissions
    2. Assign Admin role to superusers missing roles
    3. Seed Chart of Accounts (accounting)
    4. Seed payment methods and accounts
    5. Validate seed completion
    """

    def __init__(self):
        self.results: List[dict] = []
        self._has_errors = False

    @property
    def success(self) -> bool:
        return not self._has_errors

    def execute(self) -> List[dict]:
        """Run all bootstrap steps in order."""
        logger.info("=== Enterprise Bootstrap Orchestrator ===")
        self.results = []

        self._step("seed_roles", self._seed_roles)
        self._step("assign_admin_roles", self._assign_admin_roles)
        self._step("seed_accounts", self._seed_accounts)
        self._step("seed_payments", self._seed_payments)
        self._step("validate_seeding", self._validate_seeding)

        logger.info(f"Bootstrap complete: {len(self.results)} step(s), "
                     f"{'SUCCESS' if self.success else 'ERRORS'}")
        return self.results

    def _step(self, name: str, fn) -> None:
        """Execute a single bootstrap step with error handling."""
        try:
            result = fn()
            status = "skipped" if result is None else ("success" if result.get("success") else "failed")
            self.results.append({
                "step": name,
                "status": status,
                "detail": result.get("detail", "") if result else "already initialized",
            })
            if status == "failed":
                self._has_errors = True
                logger.error(f"  Bootstrap step '{name}' FAILED: {result.get('detail', '')}")
            elif status == "skipped":
                logger.info(f"  Bootstrap step '{name}': skipped (already configured)")
            else:
                logger.info(f"  Bootstrap step '{name}': OK")
        except BootstrapError as e:
            self._has_errors = True
            self.results.append({"step": name, "status": "failed", "detail": str(e)})
            logger.error(f"  Bootstrap step '{name}' ERROR: {e}")
        except Exception as e:
            self._has_errors = True
            self.results.append({"step": name, "status": "error", "detail": str(e)})
            logger.error(f"  Bootstrap step '{name}' UNEXPECTED: {e}")

    def _seed_roles(self) -> Optional[dict]:
        """Seed roles and permissions if not already present."""
        from security.models import Role
        if Role.objects.count() > 0:
            return None  # Already seeded

        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("seed_roles", stdout=out)
        output = out.getvalue()
        logger.info(f"Roles seeded: {output[:200]}")
        return {"success": True, "detail": "Roles and permissions created"}

    def _assign_admin_roles(self) -> Optional[dict]:
        """Assign Admin role to superusers who have no roles."""
        from django.contrib.auth.models import User
        from security.models import Role, UserRole

        admin_role = Role.objects.filter(name="Admin").first()
        if not admin_role:
            return {"success": False, "detail": "Admin role not found (run seed_roles first)"}

        admins_without_role = User.objects.filter(
            is_superuser=True
        ).exclude(
            id__in=UserRole.objects.filter(role=admin_role).values("user_id")
        )

        count = 0
        for admin in admins_without_role:
            with transaction.atomic():
                UserRole.objects.create(user=admin, role=admin_role)
            count += 1

        if count > 0:
            logger.info(f"Assigned Admin role to {count} superuser(s)")
            return {"success": True, "detail": f"Admin role assigned to {count} user(s)"}
        return None  # Already assigned

    def _seed_payments(self) -> Optional[dict]:
        """Seed payment methods and accounts if not already present."""
        from payments.models import PaymentMethod
        if PaymentMethod.objects.count() > 0:
            return None  # Already seeded

        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("seed_payments", stdout=out)
        output = out.getvalue()
        logger.info(f"Payments seeded: {output[:200]}")
        return {"success": True, "detail": "Payment methods and accounts created"}

    def _seed_accounts(self) -> Optional[dict]:
        """Seed Chart of Accounts if not already present."""
        from accounting.models import Account
        if Account.objects.count() > 0:
            return None  # Already seeded

        from accounting.management.commands.seed_accounts import (
            seed_canonical_chart_of_accounts,
        )
        created = seed_canonical_chart_of_accounts()
        return {
            "success": True,
            "detail": f"Created {created} Chart of Accounts entries",
        }

    def _validate_seeding(self) -> dict:
        """Validate that all required seed data exists."""
        from django.contrib.auth.models import User
        from security.models import Role, Permission, UserRole
        from payments.models import PaymentMethod, PaymentAccount
        from accounting.models import Account

        issues = []

        role_count = Role.objects.count()
        if role_count == 0:
            issues.append("No roles seeded")

        perm_count = Permission.objects.count()
        if perm_count == 0:
            issues.append("No permissions seeded")

        admin_count = User.objects.filter(is_superuser=True).count()
        if admin_count > 0:
            roleless = User.objects.filter(is_superuser=True).exclude(
                id__in=UserRole.objects.filter(
                    role__name="Admin"
                ).values("user_id")
            ).count()
            if roleless > 0:
                issues.append(f"{roleless} superuser(s) still lack Admin role")

        acct_count = Account.objects.count()
        if acct_count == 0:
            issues.append("No Chart of Accounts seeded")

        pm_count = PaymentMethod.objects.count()
        if pm_count == 0:
            issues.append("No payment methods seeded")

        pa_count = PaymentAccount.objects.count()
        if pa_count == 0:
            issues.append("No payment accounts seeded")

        if issues:
            return {"success": False, "detail": "; ".join(issues)}
        return {
            "success": True,
            "detail": f"{role_count} roles, {perm_count} perms, "
                      f"{acct_count} accounts, {pm_count} payment methods, {pa_count} accounts"
        }


def run_bootstrap() -> List[dict]:
    """Convenience function to run the full bootstrap."""
    orchestrator = BootstrapOrchestrator()
    return orchestrator.execute()

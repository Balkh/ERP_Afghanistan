"""
Django System Checks for Enterprise Governance.

Registers startup validation checks using Django's system check framework.
These run on every `manage.py` command and server start.
"""
from django.core.checks import register, Tags, Warning, Critical, Error


@register(deploy=True)
def check_secret_key_strength(app_configs, **kwargs):
    """W009: Verify SECRET_KEY is not the insecure default."""
    from django.conf import settings
    key = getattr(settings, "SECRET_KEY", "")
    default = "django-insecure-please-change-in-production"
    if not key or key == default:
        return [Critical(
            "SECRET_KEY is set to the insecure default.",
            hint="Generate a secure SECRET_KEY and set it via .env or environment variable.",
            id="erp.W001",
        )]
    if len(key) < 50:
        return [Warning(
            "SECRET_KEY is shorter than 50 characters.",
            hint="Use a longer, random SECRET_KEY for production.",
            id="erp.W002",
        )]
    return []


@register(deploy=True)
def check_ssl_configuration(app_configs, **kwargs):
    """Verify SSL is enabled when not in DEBUG mode."""
    from django.conf import settings
    if getattr(settings, "DEBUG", True):
        return [Warning(
            "DEBUG mode is enabled. SSL checks skipped.",
            hint="Disable DEBUG and configure SSL for production.",
            id="erp.W003",
        )]
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        return [Error(
            "SECURE_SSL_REDIRECT is not enabled.",
            hint="Set SECURE_SSL_REDIRECT=True for production deployment.",
            id="erp.E001",
        )]
    return []


@register(deploy=True)
def check_jdatetime_installed(app_configs, **kwargs):
    """Verify jdatetime library is available for Jalali calendar."""
    try:
        import jdatetime  # noqa: F401
        return []
    except ImportError:
        return [Warning(
            "jdatetime is not installed. Jalali calendar functions will fail at runtime.",
            hint="Run: pip install jdatetime",
            id="erp.W004",
        )]


@register(deploy=True)
def check_rbac_seeded(app_configs, **kwargs):
    """Check roles and permissions are seeded."""
    try:
        from security.models import Role, Permission
        role_count = Role.objects.count()
        perm_count = Permission.objects.count()
        if role_count == 0:
            return [Critical(
                "No roles seeded. System cannot determine UI access permissions.",
                hint="Run: python manage.py seed_roles",
                id="erp.E002",
            )]
        if perm_count == 0:
            return [Critical(
                "No permissions seeded. RBAC system has no rules.",
                hint="Run: python manage.py seed_roles",
                id="erp.E003",
            )]
        return []
    except Exception:
        return [Warning(
            "Cannot check RBAC seeding. DB may not be ready yet.",
            hint="Run migrations first, then seed_roles.",
            id="erp.W005",
        )]


@register(deploy=True)
def check_accounting_integrity(app_configs, **kwargs):
    """Verify no posted journal entries have unbalanced debits/credits."""
    try:
        from accounting.models import JournalEntry
        from django.db.models import Sum
        errors = []
        for je in JournalEntry.objects.filter(is_posted=True):
            totals = je.lines.aggregate(
                debit_total=Sum("debit"),
                credit_total=Sum("credit")
            )
            if (totals["debit_total"] or 0) != (totals["credit_total"] or 0):
                errors.append(je.entry_number)
                if len(errors) >= 5:
                    break
        if errors:
            return [Critical(
                f"{len(errors)} posted journal entr(y/ies) have unbalanced debits/credits.",
                hint=f"Unbalanced entries: {', '.join(str(e) for e in errors)}. "
                     f"Review accounting/services/journal_engine.py for root cause.",
                id="erp.E004",
            )]
        return []
    except Exception:
        return [Warning(
            "Cannot verify accounting integrity. DB may not be ready.",
            hint="",
            id="erp.W006",
        )]

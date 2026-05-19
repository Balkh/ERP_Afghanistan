"""
Phase 17.6 — Query Governance Enforcement (Soft Mode).
Logs warnings for unsafe query patterns without blocking.

Modes:
- soft (default): log warning only
- strict: raise on detection (requires settings.ENFORCEMENT_MODE='strict')
"""
import logging

from django.conf import settings

logger = logging.getLogger("erp.governance.query")

_ENFORCEMENT_MODE = getattr(settings, "ENFORCEMENT_MODE", "soft")
_IS_STRICT = _ENFORCEMENT_MODE == "strict"


def warn_unsafe_query(
    model_name: str,
    query_type: str = "global_all",
    caller: str = "",
    detail: str = "",
) -> None:
    """Log (or raise in strict mode) when an unsafe query pattern is detected."""
    message = (
        f"Unsafe query [{query_type}] on {model_name}"
        f"{' by ' + caller if caller else ''}"
        f"{': ' + detail if detail else ''}"
    )
    if _IS_STRICT:
        logger.error(message)
        raise RuntimeError(message)
    logger.warning(message)


class QueryGovernance:
    """Query governance checks. Use to mark ViewSets/methods for governance scanning."""

    @staticmethod
    def check_queryset(queryset, view_name: str = "") -> None:
        """Inspect a queryset for safety and log issues."""
        if queryset is None:
            return
        model = getattr(queryset, "model", None)
        if model is None:
            return
        model_name = model.__name__ if hasattr(model, "__name__") else str(model)
        qs_str = str(queryset.query) if hasattr(queryset, "query") else ""
        if "company_id" not in qs_str and "company" not in qs_str:
            has_company_field = hasattr(model, "company_id") or hasattr(model, "company")
            if has_company_field:
                warn_unsafe_query(
                    model_name=model_name,
                    query_type="no_tenant_filter",
                    caller=view_name,
                    detail="Queryset missing company_id filter on company-scoped model",
                )

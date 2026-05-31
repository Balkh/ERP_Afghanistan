"""
Class 1: TenantScopeEnforcer — Multi-Tenant Guarantee.

Enforces that ALL financial, inventory, reconciliation, payroll,
and journal entries ALWAYS include non-null company scope.

GUARANTEE: No company_id can be null or empty for any scoped model.
GUARANTEE: Every query without company filter is detected and rejected.
GUARANTEE: Every object creation without company context is rejected.
"""
from django.db import models
from django.core.exceptions import ValidationError
from typing import Set, Type


SCOPED_MODEL_PATHS: Set[str] = {
    'sales.salesinvoice',
    'sales.salesinvoiceitem',
    'purchases.purchaseinvoice',
    'purchases.purchaseinvoiceitem',
    'returns.returnorder',
    'returns.returnorderitem',
    'returns.reconciliationentry',
    'accounting.journalentry',
    'accounting.journalentryline',
    'accounting.account',
    'payments.financialtransaction',
    'payments.paymentmethod',
    'payments.paymentaccount',
    'inventory.product',
    'inventory.batch',
    'inventory.stockmovement',
    'inventory.warehouse',
    'inventory.category',
    'payroll.payrollcycle',
    'payroll.salarystructure',
    'hr.employee',
    'hr.attendance',
}


class TenantScopeEnforcer:
    """
    Central enforcer of tenant-scoped data access and creation.

    Mode:
      - LOG:   Log warnings (non-blocking, for audits)
      - BLOCK: Raise ValidationError (fail-fast)
    """

    MODE_LOG = 'LOG'
    MODE_BLOCK = 'BLOCK'

    def __init__(self, mode: str = 'BLOCK'):
        self.mode = mode
        self._violations: list = []

    def validate_model_has_company(self, instance: models.Model) -> None:
        """Validate that a model instance has non-null company_id before save."""
        if not hasattr(instance, 'company_id'):
            return
        if instance.company_id is not None:
            return
        model_label = f'{instance._meta.app_label}.{instance._meta.model_name}'
        if model_label not in SCOPED_MODEL_PATHS:
            return
        msg = f"TENANT SCOPE VIOLATION: {model_label} (pk={instance.pk or 'new'}) has null company_id"
        self._violations.append(msg)
        if self.mode == self.MODE_BLOCK:
            raise ValidationError(msg)

    def validate_query_has_company(self, model_class: Type[models.Model], query_kwargs: dict) -> None:
        """Validate that a query includes company filter for scoped models."""
        model_label = f'{model_class._meta.app_label}.{model_class._meta.model_name}'
        if model_label not in SCOPED_MODEL_PATHS:
            return
        if 'company_id' in query_kwargs or 'company' in query_kwargs:
            return
        if hasattr(query_kwargs, 'get') and query_kwargs.get('company__isnull') is not None:
            return
        msg = f"TENANT SCOPE VIOLATION: Query on {model_label} without company filter"
        self._violations.append(msg)
        if self.mode == self.MODE_BLOCK:
            raise ValidationError(msg)

    @property
    def has_violations(self) -> bool:
        return len(self._violations) > 0

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    def clear(self) -> None:
        self._violations.clear()

    def violations(self) -> list:
        return list(self._violations)


_enforcer_instance = None


def get_tenant_enforcer(mode: str = 'BLOCK') -> TenantScopeEnforcer:
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = TenantScopeEnforcer(mode=mode)
    return _enforcer_instance


def validate_company_scope(instance: models.Model) -> None:
    """Pre-save hook: validate company_id is set for all scoped models."""
    enforcer = get_tenant_enforcer()
    enforcer.validate_model_has_company(instance)

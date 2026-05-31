"""
Central Policy Enforcer — Phase 3.

All enforcement flows route through GovernanceKernel.enforce().
Provides fail-closed behavior, state transition validation,
and enforcement audit trails.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core.governance.kernel import GovernanceKernel, PriorityTier, EnforcementResult
from core.governance.state_transitions import (
    validate_return_transition,
    validate_sales_transition,
    validate_purchase_transition,
    IllegalTransitionError,
)
from core.governance.registries import PolicyRule

logger = logging.getLogger("erp.governance.enforcer")

ENFORCER_VERSION = "1.0.0"


def register_enforcement_policies(kernel: GovernanceKernel) -> None:
    """Register all built-in enforcement policies with the kernel."""

    # ── Return Order State Transitions ──────────────────────
    def check_return_transition(context: dict) -> Tuple[bool, str]:
        current = context.get("current_state", "")
        target = context.get("target_state", "")
        if not current or not target:
            return False, "Missing current_state or target_state in context"
        conditions = {k: v for k, v in context.items()
                      if k not in ("current_state", "target_state", "entity_id", "user")}
        try:
            validate_return_transition(current, target, **conditions)
            return True, f"Return transition '{current}' -> '{target}' allowed"
        except IllegalTransitionError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    kernel.policies.register(PolicyRule(
        policy_id="enforce.return_state_transition",
        description="Validate ReturnOrder state transitions with required conditions",
        tier="critical",
        check_fn=check_return_transition,
    ), meta={"domain": "returns"})

    # ── Sales Invoice State Transitions ─────────────────────
    def check_sales_transition(context: dict) -> Tuple[bool, str]:
        current = context.get("current_state", "")
        target = context.get("target_state", "")
        if not current or not target:
            return False, "Missing current_state or target_state in context"
        conditions = {k: v for k, v in context.items()
                      if k not in ("current_state", "target_state", "entity_id", "user")}
        try:
            validate_sales_transition(current, target, **conditions)
            return True, f"Sales transition '{current}' -> '{target}' allowed"
        except IllegalTransitionError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    kernel.policies.register(PolicyRule(
        policy_id="enforce.sales_state_transition",
        description="Validate SalesInvoice state transitions with required conditions",
        tier="critical",
        check_fn=check_sales_transition,
    ), meta={"domain": "sales"})

    # ── Purchase Invoice State Transitions ──────────────────
    def check_purchase_transition(context: dict) -> Tuple[bool, str]:
        current = context.get("current_state", "")
        target = context.get("target_state", "")
        if not current or not target:
            return False, "Missing current_state or target_state in context"
        conditions = {k: v for k, v in context.items()
                      if k not in ("current_state", "target_state", "entity_id", "user")}
        try:
            validate_purchase_transition(current, target, **conditions)
            return True, f"Purchase transition '{current}' -> '{target}' allowed"
        except IllegalTransitionError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    kernel.policies.register(PolicyRule(
        policy_id="enforce.purchase_state_transition",
        description="Validate PurchaseInvoice state transitions with required conditions",
        tier="critical",
        check_fn=check_purchase_transition,
    ), meta={"domain": "purchases"})

    # ── Accounting Integrity ──────────────────────────────
    def check_je_integrity(context: dict) -> Tuple[bool, str]:
        from accounting.models import JournalEntry
        from django.db.models import Sum
        entry_id = context.get("journal_entry_id")
        if not entry_id:
            return True, "No journal entry specified"
        try:
            je = JournalEntry.objects.get(id=entry_id)
            totals = je.lines.aggregate(d=Sum("debit"), c=Sum("credit"))
            if (totals["d"] or 0) != (totals["c"] or 0):
                return False, (
                    f"JE #{je.entry_number} unbalanced: "
                    f"D={totals['d']} C={totals['c']}"
                )
            return True, "JE balanced"
        except JournalEntry.DoesNotExist:
            return False, f"JE #{entry_id} not found"
        except Exception as e:
            return False, str(e)

    kernel.policies.register(PolicyRule(
        policy_id="enforce.je_debit_equals_credit",
        description="Posted journal entries must have equal debits and credits",
        tier="critical",
        check_fn=check_je_integrity,
    ), meta={"domain": "accounting"})

    logger.info("Registered %d enforcement policies", kernel.policies.count())

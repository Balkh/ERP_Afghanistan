"""
Domain State Transition Guards.

Prevents illegal business state transitions by validating state changes
against canonical state machines. Read-only validation layer — never
mutates state directly.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


STATE_TRANSITION_VERSION = "1.0.0"


class IllegalTransitionError(ValueError):
    """Raised when an illegal state transition is attempted."""


@dataclass
class TransitionRule:
    from_state: str
    to_state: str
    required_conditions: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class StateMachine:
    name: str
    valid_states: Set[str]
    transitions: List[TransitionRule]
    initial_state: str = ""

    def validate(self, current: str, target: str, context: Optional[dict] = None) -> None:
        """Validate a state transition. Raises IllegalTransitionError if invalid."""
        if current not in self.valid_states:
            raise IllegalTransitionError(
                f"[{self.name}] Invalid current state '{current}'. "
                f"Valid: {sorted(self.valid_states)}"
            )
        if target not in self.valid_states:
            raise IllegalTransitionError(
                f"[{self.name}] Invalid target state '{target}'. "
                f"Valid: {sorted(self.valid_states)}"
            )
        if current == target:
            return
        allowed = [t for t in self.transitions if t.from_state == current and t.to_state == target]
        if not allowed:
            raise IllegalTransitionError(
                f"[{self.name}] Illegal transition: '{current}' -> '{target}'. "
                f"Allowed targets from '{current}': "
                f"{sorted(set(t.to_state for t in self.transitions if t.from_state == current))}"
            )
        rule = allowed[0]
        if rule.required_conditions:
            effective_context = context or {}
            for condition in rule.required_conditions:
                if condition not in effective_context or not effective_context.get(condition):
                    raise IllegalTransitionError(
                        f"[{self.name}] Missing required condition '{condition}' "
                        f"for transition '{current}' -> '{target}'"
                    )


# ── Canonical State Machines ──

RETURN_ORDER_MACHINE = StateMachine(
    name="ReturnOrder",
    valid_states={"DRAFT", "PENDING", "APPROVED", "REJECTED", "COMPLETED", "VOIDED"},
    initial_state="DRAFT",
    transitions=[
        TransitionRule("DRAFT", "PENDING", description="Submit return for approval"),
        TransitionRule("PENDING", "APPROVED", [
            "journal_entries_created",
            "stock_movements_applied",
        ], description="Approve return - creates JE + restores stock"),
        TransitionRule("PENDING", "REJECTED", description="Reject return"),
        TransitionRule("APPROVED", "COMPLETED", [
            "refund_processed",
        ], description="Complete return - process refund"),
        TransitionRule("APPROVED", "VOIDED", [
            "reversal_entries_created",
        ], description="Void approved return"),
        TransitionRule("COMPLETED", "VOIDED", [
            "reversal_entries_created",
            "refund_reversed",
        ], description="Void completed return"),
    ],
)

SALES_INVOICE_MACHINE = StateMachine(
    name="SalesInvoice",
    valid_states={"DRAFT", "CONFIRMED", "DISPATCHED", "PARTIAL_PAID", "PAID", "CANCELLED", "VOIDED"},
    initial_state="DRAFT",
    transitions=[
        TransitionRule("DRAFT", "CONFIRMED", description="Confirm invoice"),
        TransitionRule("CONFIRMED", "DISPATCHED", [
            "journal_entry_created",
            "stock_deducted",
        ], description="Dispatch - creates JE + deducts stock"),
        TransitionRule("DISPATCHED", "PARTIAL_PAID", description="Partial payment received"),
        TransitionRule("PARTIAL_PAID", "PAID", description="Full payment received"),
        TransitionRule("DISPATCHED", "PAID", description="Full payment received"),
        TransitionRule("CONFIRMED", "CANCELLED", description="Cancel before dispatch"),
        TransitionRule("DISPATCHED", "VOIDED", [
            "reversal_entries_created",
            "stock_restored",
        ], description="Void dispatched invoice"),
        TransitionRule("PAID", "VOIDED", [
            "reversal_entries_created",
            "stock_restored",
            "payment_reversed",
        ], description="Void paid invoice"),
    ],
)

PURCHASE_INVOICE_MACHINE = StateMachine(
    name="PurchaseInvoice",
    valid_states={"DRAFT", "RECEIVED", "PARTIAL_PAID", "PAID", "CANCELLED", "VOIDED"},
    initial_state="DRAFT",
    transitions=[
        TransitionRule("DRAFT", "RECEIVED", [
            "journal_entry_created",
            "stock_added",
        ], description="Receive - creates JE + adds stock"),
        TransitionRule("RECEIVED", "PARTIAL_PAID", description="Partial payment"),
        TransitionRule("PARTIAL_PAID", "PAID", description="Full payment"),
        TransitionRule("RECEIVED", "PAID", description="Full payment"),
        TransitionRule("DRAFT", "CANCELLED", description="Cancel before receipt"),
        TransitionRule("RECEIVED", "VOIDED", [
            "reversal_entries_created",
            "stock_restored",
        ], description="Void received invoice"),
        TransitionRule("PAID", "VOIDED", [
            "reversal_entries_created",
            "stock_restored",
            "payment_reversed",
        ], description="Void paid invoice"),
    ],
)


def validate_return_transition(current: str, target: str, **conditions: bool) -> None:
    """Validate ReturnOrder state transition with required conditions."""
    RETURN_ORDER_MACHINE.validate(current, target, conditions)


def validate_sales_transition(current: str, target: str, **conditions: bool) -> None:
    """Validate SalesInvoice state transition with required conditions."""
    SALES_INVOICE_MACHINE.validate(current, target, conditions)


def validate_purchase_transition(current: str, target: str, **conditions: bool) -> None:
    """Validate PurchaseInvoice state transition with required conditions."""
    PURCHASE_INVOICE_MACHINE.validate(current, target, conditions)

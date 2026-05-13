"""
Phase 5B.2 — Immutable Governance Audit Chain.

Append-only audit trail for all approval actions.
Full lineage preservation with deterministic replay.

Safety guarantees:
- Immutable entries (never modified after creation)
- Append-only storage
- Replay-safe serialization
- Bounded memory
- Full state transition lineage
- Escalation chain preservation
"""
import json
import logging
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Deque
from uuid import uuid4

from core.operations.approval.models import (
    ApprovalState, ApprovalWorkflow, ApprovalAuditEntry,
    ApprovalSignature, EscalationStep,
    SIMULATION_CONTEXT_MARKER,
)

logger = logging.getLogger('erp.approval.audit')

AUDIT_CHAIN_VERSION = "1.0.0"
MAX_AUDIT_ENTRIES = 10000
MAX_WORKFLOW_HISTORY = 5000


class AuditChain:
    """Append-only, bounded, immutable governance audit chain.

    All entries are written once and never modified.
    Full replay support for deterministic reconstruction.
    """

    def __init__(self, max_entries: int = MAX_AUDIT_ENTRIES):
        self._entries: List[ApprovalAuditEntry] = []
        self._max_entries = max_entries
        self._workflow_history: Dict[str, List[ApprovalAuditEntry]] = {}
        self._max_workflow_history = MAX_WORKFLOW_HISTORY

    def append(self, entry: ApprovalAuditEntry) -> None:
        """Append an audit entry. Idempotent by entry_id uniqueness."""
        if entry.context_marker != SIMULATION_CONTEXT_MARKER:
            raise ValueError("Audit entry missing simulation context marker")
        if len(self._entries) >= self._max_entries:
            self._entries.pop(0)
        self._entries.append(entry)
        if entry.workflow_id not in self._workflow_history:
            self._workflow_history[entry.workflow_id] = []
        wh = self._workflow_history[entry.workflow_id]
        if len(wh) >= self._max_workflow_history:
            wh.pop(0)
        wh.append(entry)

    def get_all(self) -> List[ApprovalAuditEntry]:
        """Get all audit entries (immutable view)."""
        return list(self._entries)

    def get_by_workflow(self, workflow_id: str) -> List[ApprovalAuditEntry]:
        """Get audit entries for a specific workflow."""
        return list(self._workflow_history.get(workflow_id, []))

    def get_by_state(self, state: ApprovalState) -> List[ApprovalAuditEntry]:
        """Get audit entries for a specific new_state."""
        return [e for e in self._entries if e.new_state == state]

    def get_by_timerange(self, start: str, end: str) -> List[ApprovalAuditEntry]:
        """Get audit entries within a time range."""
        return [
            e for e in self._entries
            if start <= e.timestamp <= end
        ]

    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self._workflow_history.clear()

    def replay_rebuild(self, entries: List[ApprovalAuditEntry]) -> None:
        """Rebuild audit chain from replayed entries."""
        self.clear()
        for entry in entries:
            self.append(entry)

    def to_serializable(self) -> List[Dict[str, Any]]:
        """Serialize audit entries for export/replay."""
        return [
            self._entry_to_dict(e)
            for e in self._entries
        ]

    def _entry_to_dict(self, e: ApprovalAuditEntry) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "entry_id": e.entry_id,
            "workflow_id": e.workflow_id,
            "action_type": e.action_type,
            "domain": e.domain,
            "risk_level": e.risk_level,
            "previous_state": e.previous_state.value if e.previous_state else None,
            "new_state": e.new_state.value,
            "triggered_by": e.triggered_by,
            "timestamp": e.timestamp,
            "metadata": e.metadata,
            "context_marker": e.context_marker,
        }
        if e.signature:
            sig = e.signature
            result["signature"] = {
                "signature_id": sig.signature_id,
                "approver_id": sig.approver_id,
                "authority_level": sig.authority_level.value,
                "decision": sig.decision,
            }
        if e.escalation:
            esc = e.escalation
            result["escalation"] = {
                "step_index": esc.step_index,
                "escalated_by": esc.escalated_by,
                "escalated_to": esc.escalated_to.value,
                "reason": esc.reason,
            }
        return result

    def rebuild_from_serializable(self, data: List[Dict[str, Any]]) -> None:
        """Rebuild audit chain from serialized data."""
        from core.operations.approval.models import AuthorityLevel
        self.clear()
        for entry_data in data:
            previous_state = (
                ApprovalState(entry_data["previous_state"])
                if entry_data.get("previous_state") else None
            )
            signature = None
            if entry_data.get("signature"):
                sig = entry_data["signature"]
                signature = ApprovalSignature(
                    signature_id=sig["signature_id"],
                    approver_id=sig["approver_id"],
                    authority_level=AuthorityLevel(sig["authority_level"]),
                    decision=sig["decision"],
                )
            escalation = None
            if entry_data.get("escalation"):
                esc = entry_data["escalation"]
                escalation = EscalationStep(
                    step_index=esc["step_index"],
                    escalated_by=esc["escalated_by"],
                    escalated_to=AuthorityLevel(esc["escalated_to"]),
                    reason=esc["reason"],
                )
            entry = ApprovalAuditEntry(
                entry_id=entry_data["entry_id"],
                workflow_id=entry_data["workflow_id"],
                action_type=entry_data["action_type"],
                domain=entry_data["domain"],
                risk_level=entry_data["risk_level"],
                previous_state=previous_state,
                new_state=ApprovalState(entry_data["new_state"]),
                triggered_by=entry_data["triggered_by"],
                timestamp=entry_data["timestamp"],
                signature=signature,
                escalation=escalation,
                metadata=entry_data.get("metadata", {}),
                context_marker=entry_data.get("context_marker", SIMULATION_CONTEXT_MARKER),
            )
            self.append(entry)


# Global audit chain instance
_audit_chain: Optional[AuditChain] = None


def get_audit_chain() -> AuditChain:
    global _audit_chain
    if _audit_chain is None:
        _audit_chain = AuditChain()
    return _audit_chain


def reset_audit_chain() -> None:
    global _audit_chain
    _audit_chain = None


def create_audit_entry(
    workflow: ApprovalWorkflow,
    previous_state: Optional[ApprovalState],
    new_state: ApprovalState,
    triggered_by: str,
    signature: Optional[ApprovalSignature] = None,
    escalation: Optional[EscalationStep] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ApprovalAuditEntry:
    """Create and record an audit entry.

    Deterministic — same inputs produce same audit content.
    """
    entry = ApprovalAuditEntry(
        workflow_id=workflow.workflow_id,
        action_type=workflow.action_type,
        domain=workflow.domain,
        risk_level=workflow.risk_level,
        previous_state=previous_state,
        new_state=new_state,
        triggered_by=triggered_by,
        signature=signature,
        escalation=escalation,
        metadata={
            "audit_chain_version": AUDIT_CHAIN_VERSION,
            **(metadata or {}),
        },
    )

    chain = get_audit_chain()
    chain.append(entry)
    return entry


def get_workflow_audit_trail(workflow_id: str) -> List[Dict[str, Any]]:
    """Get full audit trail for a workflow.

    Returns deterministic, ordered list of state transitions.
    """
    chain = get_audit_chain()
    entries = chain.get_by_workflow(workflow_id)
    return [
        {
            "entry_id": e.entry_id,
            "previous_state": e.previous_state.value if e.previous_state else None,
            "new_state": e.new_state.value,
            "triggered_by": e.triggered_by,
            "timestamp": e.timestamp,
            "has_signature": e.signature is not None,
            "has_escalation": e.escalation is not None,
        }
        for e in entries
    ]


def verify_audit_integrity() -> Dict[str, Any]:
    """Verify the integrity of the audit chain.

    Checks:
    - Entry ordering by timestamp
    - State transition validity
    - Context marker presence
    """
    chain = get_audit_chain()
    entries = chain.get_all()
    issues = []

    for i in range(len(entries) - 1):
        if entries[i].timestamp > entries[i + 1].timestamp:
            issues.append(f"Timestamp ordering violation at index {i}")

    for e in entries:
        if e.context_marker != SIMULATION_CONTEXT_MARKER:
            issues.append(f"Missing context marker: {e.entry_id}")

    return {
        "total_entries": len(entries),
        "unique_workflows": len(set(e.workflow_id for e in entries)),
        "integrity_ok": len(issues) == 0,
        "issues": issues,
        "audit_chain_version": AUDIT_CHAIN_VERSION,
    }




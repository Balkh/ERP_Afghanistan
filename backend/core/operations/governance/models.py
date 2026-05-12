"""
Phase 5B.0 — Governance Models.

Shared data structures for the governance enforcement pipeline.
All models are immutable dataclasses.

These define the contract between:
- Governance Interceptor
- Policy Evaluation Engine
- Risk Classification Engine
- Execution Decision Gate

No execution logic. Deterministic data structures only.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime


ACTION_INTENT_VERSION = "1.0.0"


@dataclass(frozen=True)
class ActionIntent:
    """Captures a potential system action before execution.

    Created by the Governance Interceptor for every action attempt.
    Immutable — once created, cannot be modified.
    """
    action_id: str = field(default_factory=lambda: f"act_{uuid4().hex[:8]}")
    action_type: str = "unknown"
    domain: str = "unknown"
    source: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Result of evaluating an action against governance policies.

    Deterministic — same action + same policies = same result.
    """
    policy_id: str = ""
    policy_name: str = ""
    compliance: str = "NOT_EVALUATED"  # PASS, FAIL, CONDITIONAL, NOT_EVALUATED
    violated_rules: List[str] = field(default_factory=list)
    evaluation_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskClassificationResult:
    """Risk level assigned to an action.

    Risk levels (immutable, from Phase 5A.5.5):
        NONE (0), LOW (1), MEDIUM (2), HIGH (3), CRITICAL (4)
    """
    risk_level: str = "NONE"
    risk_score: int = 0
    justification: str = ""
    classification_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionResult:
    """Final decision for an action.

    Decision types:
        BLOCKED — Action is forbidden and will not proceed
        SIMULATION_ONLY — Action may be simulated but not executed
        REQUIRE_APPROVAL — Action requires approval before execution
        SAFE_PASS — Action is safe to pass (no execution in this phase)

    No actual execution occurs in this phase.
    """
    decision: str = "BLOCKED"
    action_id: str = ""
    reasoning: str = ""
    audit_entry: Dict[str, Any] = field(default_factory=dict)
    decision_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

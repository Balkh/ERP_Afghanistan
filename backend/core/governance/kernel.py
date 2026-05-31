"""
Governance Kernel — Central Runtime Governance Layer.

Single authoritative entry point for ALL governance operations.
Lazily initialized. Zero startup overhead. No global monkey patching.
Extensible by design — register policies, invariants, feature gates.
"""
import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from core.governance.registries import (
    PolicyRegistry, InvariantRegistry, EnvironmentRegistry,
    FeatureGateRegistry, ReadinessRegistry, UIRuleRegistry,
)

logger = logging.getLogger("erp.governance.kernel")

KERNEL_VERSION = "1.0.0"


class PriorityTier(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class EnforcementResult:
    policy_id: str
    allowed: bool
    reason: str = ""
    violated_invariant: str = ""
    affected_entity: str = ""
    user: str = ""
    correlation_id: str = ""
    latency_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class AuditEntry:
    correlation_id: str
    action: str
    policy_id: str
    result: str  # allowed | denied | error
    reason: str
    affected_entity: str
    user: str
    latency_ms: float
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class _GovernanceKernelState:
    _instance = None
    _initialized = False

    def __init__(self):
        if _GovernanceKernelState._initialized:
            return
        _GovernanceKernelState._initialized = True
        self.policies = PolicyRegistry()
        self.invariants = InvariantRegistry()
        self.environment = EnvironmentRegistry()
        self.feature_gates = FeatureGateRegistry()
        self.readiness = ReadinessRegistry()
        self.ui_rules = UIRuleRegistry()
        self._audit_log: List[AuditEntry] = []
        self._audit_maxlen = 1000
        self._failsafe_mode = False
        self._degraded_tiers: Set[str] = set()


def get_kernel():
    if _GovernanceKernelState._instance is None:
        _GovernanceKernelState._instance = _GovernanceKernelState()
    return _GovernanceKernelState._instance


class GovernanceKernel:
    def __init__(self):
        self._state = get_kernel()

    @property
    def policies(self) -> PolicyRegistry:
        return self._state.policies

    @property
    def invariants(self) -> InvariantRegistry:
        return self._state.invariants

    @property
    def environment(self) -> EnvironmentRegistry:
        return self._state.environment

    @property
    def feature_gates(self) -> FeatureGateRegistry:
        return self._state.feature_gates

    @property
    def readiness(self) -> ReadinessRegistry:
        return self._state.readiness

    @property
    def ui_rules(self) -> UIRuleRegistry:
        return self._state.ui_rules

    # ── Core Enforcement ──────────────────────────────────────

    def enforce(
        self,
        policy_id: str,
        context: Optional[dict] = None,
        priority: Union[PriorityTier, str] = PriorityTier.HIGH,
        user: str = "",
        entity: str = "",
    ) -> EnforcementResult:
        """Central enforcement entry point. All enforcement MUST route through here.

        Returns EnforcementResult with allow/deny decision.
        Fail-closed: if policy not found, returns denied.
        """
        cid = _correlation_id()
        start = time.time()

        priority = PriorityTier(priority) if isinstance(priority, str) else priority

        if self._state._failsafe_mode and priority == PriorityTier.LOW:
            return EnforcementResult(
                policy_id=policy_id,
                allowed=True,
                reason="Failsafe mode: low-priority enforcement bypassed",
                correlation_id=cid,
                user=user,
                affected_entity=entity,
            )

        if priority.value in self._state._degraded_tiers:
            return EnforcementResult(
                policy_id=policy_id,
                allowed=True,
                reason=f"Degraded: tier '{priority.value}' disabled",
                correlation_id=cid,
                user=user,
                affected_entity=entity,
            )

        rule = self._state.policies.get(policy_id)
        if rule is None:
            latency = (time.time() - start) * 1000
            entry = AuditEntry(
                correlation_id=cid,
                action="enforce",
                policy_id=policy_id,
                result="denied",
                reason=f"Policy '{policy_id}' not registered",
                affected_entity=entity,
                user=user,
                latency_ms=latency,
            )
            self._audit_append(entry)
            return EnforcementResult(
                policy_id=policy_id,
                allowed=False,
                reason=f"Policy '{policy_id}' not registered (fail-closed)",
                correlation_id=cid,
                user=user,
                affected_entity=entity,
                latency_ms=latency,
            )

        try:
            effective_context = context or {}
            allowed, reason = rule.check(effective_context)
            latency = (time.time() - start) * 1000
            entry = AuditEntry(
                correlation_id=cid,
                action="enforce",
                policy_id=policy_id,
                result="allowed" if allowed else "denied",
                reason=reason,
                affected_entity=entity,
                user=user,
                latency_ms=latency,
            )
            self._audit_append(entry)
            return EnforcementResult(
                policy_id=policy_id,
                allowed=allowed,
                reason=reason,
                correlation_id=cid,
                user=user,
                affected_entity=entity,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.error("Kernel enforcement error: %s", e)
            entry = AuditEntry(
                correlation_id=cid,
                action="enforce",
                policy_id=policy_id,
                result="error",
                reason=str(e),
                affected_entity=entity,
                user=user,
                latency_ms=latency,
            )
            self._audit_append(entry)
            return EnforcementResult(
                policy_id=policy_id,
                allowed=False,
                reason=f"Enforcement error: {e}",
                correlation_id=cid,
                user=user,
                affected_entity=entity,
                latency_ms=latency,
            )

    # ── Invariant Checking ────────────────────────────────────

    def check_invariant(
        self, invariant_id: str, context: Optional[dict] = None
    ) -> Tuple[bool, str]:
        """Check a single registered invariant. Returns (passed, message)."""
        checker = self._state.invariants.get(invariant_id)
        if checker is None:
            return False, f"Invariant '{invariant_id}' not registered"
        try:
            return checker(context or {})
        except Exception as e:
            logger.error("Invariant check error [%s]: %s", invariant_id, e)
            return False, str(e)

    def run_invariant_scan(
        self, domain: str = "", priority: str = ""
    ) -> List[Dict[str, Any]]:
        """Run all invariants matching filters. Returns structured results."""
        results = []
        for inv_id, (checker, meta) in self._state.invariants.list_all().items():
            if domain and meta.get("domain") != domain:
                continue
            if priority and meta.get("priority") != priority:
                continue
            passed, message = self.check_invariant(inv_id)
            results.append({
                "invariant_id": inv_id,
                "domain": meta.get("domain", ""),
                "priority": meta.get("priority", "medium"),
                "passed": passed,
                "message": message,
            })
        return results

    # ── Readiness ─────────────────────────────────────────────

    def check_readiness(self, include_integrity: bool = True) -> dict:
        """Aggregate all registered readiness checks into a report."""
        from core.governance.readiness import get_full_readiness
        report = get_full_readiness(include_integrity=include_integrity)
        return {
            "overall": report.overall,
            "timestamp": report.timestamp,
            "passed": report.passed,
            "total": report.total,
            "blockers": report.blockers,
            "warnings": report.warnings,
            "recommendations": report.recommendations,
        }

    # ── Feature Gates ─────────────────────────────────────────

    def is_feature_active(self, feature_id: str, context: Optional[dict] = None) -> bool:
        """Check if a feature gate is active. Fail-closed: returns False if unknown."""
        gate = self._state.feature_gates.get(feature_id)
        if gate is None:
            return False
        try:
            return gate(context or {})
        except Exception as e:
            logger.error("Feature gate error [%s]: %s", feature_id, e)
            return False

    def get_active_features(self, context: Optional[dict] = None) -> List[str]:
        """Return all active feature IDs for the given context."""
        active = []
        ctx = context or {}
        for fid, gate in self._state.feature_gates.list_all().items():
            try:
                if gate(ctx):
                    active.append(fid)
            except Exception:
                pass
        return active

    # ── Audit ─────────────────────────────────────────────────

    def get_recent_audit(self, limit: int = 50) -> List[AuditEntry]:
        """Return most recent audit entries."""
        return list(self._state._audit_log)[-limit:]

    def get_audit_summary(self) -> dict:
        """Return summary of recent audit entries."""
        log = self._state._audit_log
        total = len(log)
        denied = sum(1 for e in log if e.result == "denied")
        errors = sum(1 for e in log if e.result == "error")
        return {
            "total_entries": total,
            "denied": denied,
            "errors": errors,
            "allowed": total - denied - errors,
            "audit_maxlen": self._state._audit_maxlen,
        }

    # ── Failsafe ──────────────────────────────────────────────

    @property
    def failsafe_mode(self) -> bool:
        return self._state._failsafe_mode

    def enable_failsafe(self) -> None:
        self._state._failsafe_mode = True
        logger.warning("GovernanceKernel FAILSAFE mode enabled — low-priority enforcement bypassed")

    def disable_failsafe(self) -> None:
        self._state._failsafe_mode = False
        logger.info("GovernanceKernel failsafe mode disabled")

    def degrade_tier(self, tier: str) -> None:
        self._state._degraded_tiers.add(tier)
        logger.warning("GovernanceKernel degraded tier '%s'", tier)

    def restore_tier(self, tier: str) -> None:
        self._state._degraded_tiers.discard(tier)
        logger.info("GovernanceKernel restored tier '%s'", tier)

    # ── Self-Health ───────────────────────────────────────────

    def health(self) -> dict:
        """Self-health check for the governance kernel itself."""
        return {
            "kernel_version": KERNEL_VERSION,
            "initialized": self._state._initialized,
            "policies": self._state.policies.count(),
            "invariants": self._state.invariants.count(),
            "feature_gates": self._state.feature_gates.count(),
            "readiness_checks": self._state.readiness.count(),
            "ui_rules": self._state.ui_rules.count(),
            "audit_entries": len(self._state._audit_log),
            "audit_capacity": self._state._audit_maxlen,
            "failsafe_mode": self._state._failsafe_mode,
            "degraded_tiers": sorted(self._state._degraded_tiers),
            "environment_profile": self._state.environment.profile,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    # ── Discovery ─────────────────────────────────────────────

    def discover(self) -> dict:
        """Full governance discovery — all registered policies, invariants, gates, checks."""
        return {
            "kernel_version": KERNEL_VERSION,
            "environment": self._state.environment.profile,
            "policies": [
                {"id": pid, "tier": m.get("tier", "high"), "description": m.get("description", "")}
                for pid, (_, m) in self._state.policies.list_all().items()
            ],
            "invariants": [
                {
                    "id": iid,
                    "domain": m.get("domain", ""),
                    "priority": m.get("priority", "medium"),
                    "description": m.get("description", ""),
                }
                for iid, (_, m) in self._state.invariants.list_all().items()
            ],
            "feature_gates": list(self._state.feature_gates.list_all().keys()),
            "readiness_checks": [
                {"name": r["name"], "status": r["status"]}
                for r in self.check_readiness().get("checks", [])
            ],
            "ui_rules": self._state.ui_rules.list_all(),
            "failsafe_mode": self._state._failsafe_mode,
            "degraded_tiers": sorted(self._state._degraded_tiers),
        }

    # ── Internal ──────────────────────────────────────────────

    def _audit_append(self, entry: AuditEntry) -> None:
        log = self._state._audit_log
        log.append(entry)
        if len(log) > self._state._audit_maxlen:
            log.pop(0)


def _correlation_id() -> str:
    return uuid.uuid4().hex[:12]

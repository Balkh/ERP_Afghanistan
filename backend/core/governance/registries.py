"""
Centralized Governance Registries.

Single authoritative registries for all governance rules, policies, invariants,
feature gates, readiness checks, and UI rules. No scattered hardcoded rules.
"""
import os
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("erp.governance.registries")

REGISTRY_VERSION = "1.0.0"


# ── Policy Registry ──────────────────────────────────────────

@dataclass
class PolicyRule:
    """A governance policy with a check function."""
    policy_id: str
    description: str
    tier: str  # critical | high | medium | low
    check_fn: Callable[[dict], Tuple[bool, str]]

    def check(self, context: dict) -> Tuple[bool, str]:
        return self.check_fn(context)


class PolicyRegistry:
    """Central registry for all governance policies.

    All enforcement rules MUST register here.
    No scattered hardcoded rules allowed.
    """

    def __init__(self):
        self._policies: Dict[str, Tuple[PolicyRule, dict]] = {}

    def register(self, rule: PolicyRule, meta: Optional[dict] = None) -> None:
        if rule.policy_id in self._policies:
            logger.warning("Policy '%s' already registered — overwriting", rule.policy_id)
        self._policies[rule.policy_id] = (rule, meta or {})
        logger.debug("Registered policy: %s (tier=%s)", rule.policy_id, rule.tier)

    def get(self, policy_id: str) -> Optional[PolicyRule]:
        result = self._policies.get(policy_id)
        return result[0] if result else None

    def list_all(self) -> Dict[str, Tuple[PolicyRule, dict]]:
        return dict(self._policies)

    def count(self) -> int:
        return len(self._policies)

    def unregister(self, policy_id: str) -> bool:
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False


# ── Invariant Registry ───────────────────────────────────────

class InvariantRegistry:
    """Central registry for all domain invariant checks."""

    def __init__(self):
        self._invariants: Dict[str, Tuple[Callable, dict]] = {}

    def register(
        self,
        invariant_id: str,
        check_fn: Callable[[dict], Tuple[bool, str]],
        meta: Optional[dict] = None,
    ) -> None:
        if invariant_id in self._invariants:
            logger.warning("Invariant '%s' already registered — overwriting", invariant_id)
        self._invariants[invariant_id] = (check_fn, meta or {})
        logger.debug("Registered invariant: %s", invariant_id)

    def get(self, invariant_id: str) -> Optional[Callable]:
        result = self._invariants.get(invariant_id)
        return result[0] if result else None

    def get_meta(self, invariant_id: str) -> dict:
        result = self._invariants.get(invariant_id)
        return result[1] if result else {}

    def list_all(self) -> Dict[str, Tuple[Callable, dict]]:
        return dict(self._invariants)

    def count(self) -> int:
        return len(self._invariants)


# ── Environment Registry ─────────────────────────────────────

_ENV_PROFILES = {
    "development": {"sampling": 1.0, "verbose": True, "blocking": True},
    "qa": {"sampling": 0.5, "verbose": True, "blocking": False},
    "staging": {"sampling": 0.25, "verbose": False, "blocking": False},
    "production": {"sampling": 0.1, "verbose": False, "blocking": False},
}


class EnvironmentRegistry:
    """Central registry for environment profiles and capabilities."""

    def __init__(self):
        self._profile = self._detect()
        self._overrides: Dict[str, Any] = {}

    @staticmethod
    def _detect() -> str:
        env = os.environ.get("ENV", "").lower()
        from django.conf import settings
        debug = getattr(settings, "DEBUG", True)
        if env == "production":
            return "production"
        if env == "staging":
            return "staging"
        if env in ("qa", "testing"):
            return "qa"
        if debug or env in ("development", ""):
            return "development"
        return "production"

    @property
    def profile(self) -> str:
        return self._profile

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        return _ENV_PROFILES.get(self._profile, {}).get(key, default)

    def set_override(self, key: str, value: Any) -> None:
        self._overrides[key] = value

    def clear_overrides(self) -> None:
        self._overrides.clear()

    def sampling_rate(self, path: str = "") -> float:
        rate = self.get("sampling", 1.0)
        always = ["/api/health", "/api/licensing", "/api/ops", "/api/governance"]
        for prefix in always:
            if path.startswith(prefix):
                return 1.0
        return rate

    def is_verbose(self) -> bool:
        return self.get("verbose", False)

    def is_blocking(self) -> bool:
        return self.get("blocking", False)

    def is_production(self) -> bool:
        return self._profile == "production"


# ── Feature Gate Registry ────────────────────────────────────

class FeatureGateRegistry:
    """Central registry for feature gates.

    Each gate is a callable(context) -> bool.
    Fail-closed: unregistered gates return False.
    """

    def __init__(self):
        self._gates: Dict[str, Callable[[dict], bool]] = {}

    def register(self, gate_id: str, gate_fn: Callable[[dict], bool]) -> None:
        if gate_id in self._gates:
            logger.warning("Feature gate '%s' already registered — overwriting", gate_id)
        self._gates[gate_id] = gate_fn
        logger.debug("Registered feature gate: %s", gate_id)

    def get(self, gate_id: str) -> Optional[Callable[[dict], bool]]:
        return self._gates.get(gate_id)

    def list_all(self) -> Dict[str, Callable[[dict], bool]]:
        return dict(self._gates)

    def count(self) -> int:
        return len(self._gates)

    def unregister(self, gate_id: str) -> bool:
        if gate_id in self._gates:
            del self._gates[gate_id]
            return True
        return False


# ── Readiness Registry ───────────────────────────────────────

@dataclass
class ReadinessCheckDef:
    name: str
    check_fn: Callable[[], dict]
    tier: str = "critical"
    description: str = ""


class ReadinessRegistry:
    """Central registry for readiness checks."""

    def __init__(self):
        self._checks: Dict[str, ReadinessCheckDef] = {}

    def register(self, check_def: ReadinessCheckDef) -> None:
        if check_def.name in self._checks:
            logger.warning("Readiness check '%s' already registered", check_def.name)
        self._checks[check_def.name] = check_def
        logger.debug("Registered readiness check: %s", check_def.name)

    def get(self, name: str) -> Optional[ReadinessCheckDef]:
        return self._checks.get(name)

    def list_all(self) -> Dict[str, ReadinessCheckDef]:
        return dict(self._checks)

    def count(self) -> int:
        return len(self._checks)


# ── UI Rule Registry ─────────────────────────────────────────

@dataclass
class UIRule:
    rule_id: str
    description: str
    severity: str  # error | warning | info
    check_fn: Callable[[], List[dict]]


class UIRuleRegistry:
    """Central registry for UI governance rules."""

    def __init__(self):
        self._rules: Dict[str, UIRule] = {}

    def register(self, rule: UIRule) -> None:
        if rule.rule_id in self._rules:
            logger.warning("UIRule '%s' already registered", rule.rule_id)
        self._rules[rule.rule_id] = rule
        logger.debug("Registered UI rule: %s", rule.rule_id)

    def get(self, rule_id: str) -> Optional[UIRule]:
        return self._rules.get(rule_id)

    def list_all(self) -> Dict[str, UIRule]:
        return dict(self._rules)

    def count(self) -> int:
        return len(self._rules)

    def run_all(self) -> Dict[str, List[dict]]:
        return {
            rid: rule.check_fn()
            for rid, rule in self._rules.items()
        }

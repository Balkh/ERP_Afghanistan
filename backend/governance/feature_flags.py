"""
Section 6 — Feature Flags & Dark Launch.
Lightweight feature flag system for safe rollouts.
"""
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class FeatureFlag:
    name: str
    enabled: bool = False
    description: str = ""
    owner: str = "governance"
    expires: Optional[datetime] = None
    rollout_percentage: int = 0


class FeatureFlagRegistry:

    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}

    def register(self, flag: FeatureFlag) -> None:
        self._flags[flag.name] = flag

    def is_enabled(self, name: str, user_id: Optional[str] = None) -> bool:
        flag = self._flags.get(name)
        if not flag:
            return False
        if not flag.enabled:
            return False
        if flag.expires and datetime.utcnow() > flag.expires:
            return False
        if flag.rollout_percentage < 100 and user_id:
            h = hash(f"{name}:{user_id}") % 100
            if h >= flag.rollout_percentage:
                return False
        return True

    def enable(self, name: str) -> None:
        if name in self._flags:
            self._flags[name].enabled = True
            self._flags[name].rollout_percentage = 100

    def disable(self, name: str) -> None:
        if name in self._flags:
            self._flags[name].enabled = False
            self._flags[name].rollout_percentage = 0

    def list_flags(self) -> Dict[str, FeatureFlag]:
        return dict(self._flags)


FLAG_REGISTRY = FeatureFlagRegistry()

# Built-in feature flags
FLAG_REGISTRY.register(FeatureFlag(
    name="governance.enforce_migration_gates",
    enabled=True,
    description="Enable migration safety gates",
    rollout_percentage=100,
))
FLAG_REGISTRY.register(FeatureFlag(
    name="governance.nightly_audit",
    enabled=True,
    description="Enable nightly audit certification",
    rollout_percentage=100,
))
FLAG_REGISTRY.register(FeatureFlag(
    name="governance.contract_check",
    enabled=True,
    description="Enable API contract checks",
    rollout_percentage=100,
))
FLAG_REGISTRY.register(FeatureFlag(
    name="reports.pdf_export_v2",
    enabled=False,
    description="New PDF export engine (dark launch)",
    rollout_percentage=0,
))
FLAG_REGISTRY.register(FeatureFlag(
    name="ui.dashboard_v3",
    enabled=False,
    description="Dashboard version 3 (dark launch)",
    rollout_percentage=0,
))

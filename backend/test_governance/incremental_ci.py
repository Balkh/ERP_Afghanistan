"""
Section 6 — Incremental CI Validation.
Optimizes CI execution based on changed modules.
"""
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass

from test_governance.critical_registry import REGISTRY, PathTier


@dataclass
class CIBuildPlan:
    full_suite: bool
    critical_suite: bool
    changed_modules: Set[str]
    highest_tier: str
    validation_suites: List[str]
    estimated_savings_pct: float


CRITICAL_SUITE = [
    "tests/test_integrity.py",
    "tests/test_sandbox.py",
    "tests/test_runner.py",
    "tests/test_runner_hardened.py",
    "tests/test_audit_engine.py",
    "tests/test_governance.py",
    "tests/test_test_governance.py",
]

HIGH_SUITE = [
    "tests/test_accounting.py",
    "tests/test_inventory.py",
    "tests/test_sales.py",
    "tests/test_purchases.py",
    "tests/test_api.py",
]

NORMAL_SUITE = [
    "tests/test_auth.py",
    "tests/test_services.py",
    "tests/test_notifications.py",
    "tests/test_financial_reports.py",
]

LOW_SUITE = [
    "tests/test_edge_cases.py",
]


class IncrementalCIEngine:

    def classify_changes(self, changed_files: List[str]) -> CIBuildPlan:
        modules: Set[str] = set()
        has_critical = False
        has_high = False
        has_normal = False

        for f in changed_files:
            mod = self._extract_module(f)
            if mod:
                modules.add(mod)
                tier = REGISTRY.get_tier(mod)
                if tier == PathTier.CRITICAL:
                    has_critical = True
                elif tier == PathTier.HIGH:
                    has_high = True
                elif tier == PathTier.NORMAL:
                    has_normal = True

        if has_critical:
            suites = list(CRITICAL_SUITE)
            highest = PathTier.CRITICAL
            savings = 0.0
        elif has_high:
            suites = list(HIGH_SUITE)
            highest = PathTier.HIGH
            savings = 40.0
        elif has_normal:
            suites = list(NORMAL_SUITE)
            highest = PathTier.NORMAL
            savings = 65.0
        else:
            suites = list(LOW_SUITE)
            highest = PathTier.LOW
            savings = 85.0

        return CIBuildPlan(
            full_suite=has_critical,
            critical_suite=has_critical or has_high,
            changed_modules=modules,
            highest_tier=highest,
            validation_suites=suites,
            estimated_savings_pct=savings,
        )

    def build_validation_plan(self, changed_files: List[str]) -> CIBuildPlan:
        return self.classify_changes(changed_files)

    def _extract_module(self, filepath: str) -> Optional[str]:
        parts = filepath.replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[0] == "core" and len(parts) >= 3:
            return f"core.{parts[1]}"
        if len(parts) >= 1:
            return parts[0]
        return None

"""
Section 1 — Critical Path Classification.
Maps modules/apps into CRITICAL/HIGH/NORMAL/LOW tiers.
"""
import os
import json
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


class PathTier:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


TIER_ORDER = {PathTier.CRITICAL: 4, PathTier.HIGH: 3, PathTier.NORMAL: 2, PathTier.LOW: 1}


@dataclass
class ModuleClassification:
    name: str
    tier: str
    description: str
    critical_subpaths: List[str] = None

    def __post_init__(self):
        if self.critical_subpaths is None:
            self.critical_subpaths = []


CRITICAL_MODULES: List[ModuleClassification] = [
    ModuleClassification("accounting", PathTier.CRITICAL,
                        "Chart of accounts, journal entries, financial reports",
                        ["models", "services/journal_engine", "services/financial_reports",
                         "services/account_hierarchy"]),
    ModuleClassification("core.integrity", PathTier.CRITICAL,
                        "Integrity enforcement layer",
                        ["engine", "gate", "controller", "detector", "freeze"]),
    ModuleClassification("core.audit", PathTier.CRITICAL,
                        "Audit engine — ledger, inventory, event, drift",
                        ["engine", "models", "ledger_audit", "drift_detector"]),
    ModuleClassification("core.runner", PathTier.CRITICAL,
                        "C-RUNNER orchestration engine",
                        ["engine", "snapshot_manager", "validator", "daily_cycle"]),
    ModuleClassification("core.sandbox", PathTier.CRITICAL,
                        "Controlled execution sandbox",
                        ["engine", "bridge", "event_bus"]),
    ModuleClassification("core.governance", PathTier.CRITICAL,
                        "Enterprise governance kernel, guarantees, deployment",
                        ["kernel", "ecek", "orchestrator"]),
    ModuleClassification("inventory", PathTier.CRITICAL,
                        "Products, batches, warehouses, stock movements",
                        ["models", "service/stock_integration"]),
    ModuleClassification("governance", PathTier.CRITICAL,
                        "Evolution governance — change, migration, release gates",
                        ["change_analyzer", "migration_guard", "release_gates",
                         "invariant_registry", "governance_engine"]),
    ModuleClassification("test_governance", PathTier.CRITICAL,
                        "Test governance — coverage, quality, confidence",
                        ["critical_registry", "weighted_coverage", "coverage_policy",
                         "confidence_engine"]),
    ModuleClassification("security", PathTier.CRITICAL,
                        "Auth, RBAC, permissions, rate limiting",
                        ["models", "permissions", "rate_limiter"]),
]

HIGH_MODULES: List[ModuleClassification] = [
    ModuleClassification("payments", PathTier.HIGH,
                        "Payment engine, financial transactions",
                        ["models", "services", "views"]),
    ModuleClassification("sales", PathTier.HIGH,
                        "Sales invoices, customers, credit",
                        ["models", "services/fifo_allocation", "views"]),
    ModuleClassification("purchases", PathTier.HIGH,
                        "Purchase invoices, suppliers",
                        ["models", "services/fifo_allocation", "views"]),
    ModuleClassification("core.operations", PathTier.HIGH,
                        "Operational intelligence, alerts, trends",
                        ["operational_intelligence", "control_center",
                         "signal_coordinator"]),
    ModuleClassification("payroll", PathTier.HIGH,
                        "Payroll processing, cycles",
                        ["models", "services"]),
    ModuleClassification("hr", PathTier.HIGH,
                        "HR — employees, attendance, leave",
                        ["models", "services"]),
]

NORMAL_MODULES: List[ModuleClassification] = [
    ModuleClassification("core.api", PathTier.NORMAL,
                        "API renderers, responses, pagination"),
    ModuleClassification("config", PathTier.NORMAL,
                        "Django settings, celery config"),
    ModuleClassification("pre_production_hardening", PathTier.NORMAL,
                        "Pre-production validation scripts"),
    ModuleClassification("production_gate", PathTier.NORMAL,
                        "Production gate certification"),
    ModuleClassification("production_infrastructure", PathTier.NORMAL,
                        "Infrastructure migration validation"),
    ModuleClassification("core.events", PathTier.NORMAL,
                        "Event handlers"),
    ModuleClassification("core.seeders", PathTier.NORMAL,
                        "Data seeders for testing"),
    ModuleClassification("core.logging", PathTier.NORMAL,
                        "Logging infrastructure"),
]

LOW_MODULES: List[ModuleClassification] = [
    ModuleClassification("core.management.commands", PathTier.LOW,
                        "Management commands"),
    ModuleClassification("core.performance", PathTier.LOW,
                        "Performance utilities"),
    ModuleClassification("core.uuid_safety", PathTier.LOW,
                        "UUID safety checks"),
]


class CriticalPathRegistry:

    def __init__(self):
        self._all = CRITICAL_MODULES + HIGH_MODULES + NORMAL_MODULES + LOW_MODULES
        self._tier_map: Dict[str, str] = {}
        self._module_map: Dict[str, ModuleClassification] = {}
        for m in self._all:
            self._tier_map[m.name] = m.tier
            self._module_map[m.name] = m

    def get_tier(self, module_name: str) -> str:
        matched = [k for k in self._tier_map if module_name.startswith(k)]
        if matched:
            return self._tier_map[max(matched, key=len)]
        return PathTier.NORMAL

    def is_critical(self, module_name: str) -> bool:
        return self.get_tier(module_name) == PathTier.CRITICAL

    def is_high(self, module_name: str) -> bool:
        return self.get_tier(module_name) == PathTier.HIGH

    def list_by_tier(self, tier: str) -> List[ModuleClassification]:
        return [m for m in self._all if m.tier == tier]

    def list_critical(self) -> List[ModuleClassification]:
        return self.list_by_tier(PathTier.CRITICAL)

    def list_high(self) -> List[ModuleClassification]:
        return self.list_by_tier(PathTier.HIGH)

    def get_all(self) -> List[ModuleClassification]:
        return list(self._all)

    def export_map(self) -> Dict:
        return {
            "version": "1.0.0",
            "total_modules": len(self._all),
            "tiers": {
                tier: {
                    "count": len(self.list_by_tier(tier)),
                    "modules": [
                        {"name": m.name, "description": m.description,
                         "critical_subpaths": m.critical_subpaths}
                        for m in self.list_by_tier(tier)
                    ],
                }
                for tier in [PathTier.CRITICAL, PathTier.HIGH, PathTier.NORMAL, PathTier.LOW]
            },
        }


REGISTRY = CriticalPathRegistry()

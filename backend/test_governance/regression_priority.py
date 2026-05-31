"""
Section 5 — Regression Protection Priority.
Defines regression-sensitive domains and ensures they are always protected.
"""
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class RegressionDomain:
    name: str
    description: str
    critical: bool
    required_tests: List[str]


REGRESSION_DOMAINS: List[RegressionDomain] = [
    RegressionDomain("accounting_equations", "Assets = Liabilities + Equity, double-entry balance",
                     True, ["test_double_entry_balance", "test_accounting_equation",
                            "test_journal_balance"]),
    RegressionDomain("inventory_reconciliation", "Stock movement lineage, batch quantity tracking",
                     True, ["test_batch_quantity", "test_stock_movement_lineage",
                            "test_fifo_allocation"]),
    RegressionDomain("replay_determinism", "Replay must produce identical state",
                     True, ["test_replay_checksum", "test_replay_determinism"]),
    RegressionDomain("rollback_correctness", "Transaction rollback must restore state",
                     True, ["test_rollback", "test_integrity_rollback"]),
    RegressionDomain("audit_consistency", "Audit trail must not have gaps",
                     True, ["test_audit_trail", "test_audit_consistency",
                            "test_audit_drift"]),
    RegressionDomain("migration_safety", "No destructive ops on protected models",
                     True, ["test_migration_safety", "test_migration_guard"]),
    RegressionDomain("permission_boundaries", "RBAC and auth enforcement",
                     True, ["test_permissions", "test_auth_enforcement"]),
    RegressionDomain("payment_accuracy", "Payment engine double-spend prevention",
                     False, ["test_double_spend", "test_payment_reconciliation"]),
    RegressionDomain("sales_fulfillment", "Sales invoice dispatch and stock deduction",
                     False, ["test_sales_dispatch", "test_sales_stock_integration"]),
    RegressionDomain("purchases_receiving", "Purchase receive and stock addition",
                     False, ["test_purchase_receive", "test_purchase_stock_integration"]),
]


class RegressionPriorityEngine:

    def get_domains(self) -> List[RegressionDomain]:
        return REGRESSION_DOMAINS

    def get_critical_domains(self) -> List[RegressionDomain]:
        return [d for d in REGRESSION_DOMAINS if d.critical]

    def get_domain_names(self) -> List[str]:
        return [d.name for d in REGRESSION_DOMAINS]

    def get_required_test_patterns(self) -> List[str]:
        patterns = []
        for d in REGRESSION_DOMAINS:
            patterns.extend(d.required_tests)
        return patterns

    def find_untested_domains(self, executed_tests: Set[str]) -> List[RegressionDomain]:
        untested = []
        for domain in REGRESSION_DOMAINS:
            if not any(test in executed_tests for test in domain.required_tests):
                untested.append(domain)
        return untested

    def is_regression_blocked(self, executed_tests: Set[str]) -> Tuple[bool, List[RegressionDomain]]:
        critical = self.get_critical_domains()
        missing = []
        for domain in critical:
            if not any(test in executed_tests for test in domain.required_tests):
                missing.append(domain)
        return (len(missing) == 0, missing)


REGRESSION_ENGINE = RegressionPriorityEngine()

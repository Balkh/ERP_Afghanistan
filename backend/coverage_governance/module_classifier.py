"""
Phase 1 — Critical Path Discovery with extended classification.
Extends test_governance/critical_registry.py with workflow-aware classification.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from test_governance.critical_registry import REGISTRY, PathTier, ModuleClassification


TIER_ORDER = {PathTier.CRITICAL: 4, PathTier.HIGH: 3, PathTier.NORMAL: 2, PathTier.LOW: 1}

TIER_WEIGHTS = {
    PathTier.CRITICAL: 10.0,
    PathTier.HIGH: 5.0,
    PathTier.NORMAL: 2.0,
    PathTier.LOW: 0.5,
}

TIER_MINIMUMS = {
    PathTier.CRITICAL: 85.0,
    PathTier.HIGH: 70.0,
    PathTier.NORMAL: 40.0,
    PathTier.LOW: 0.0,
}


# Extended critical modules with workflow paths
WORKFLOW_CRITICAL_PATHS: Dict[str, List[str]] = {
    "accounting": [
        "journal_entry.create.journal_entry.post.journal_entry.reverse.ledger.report",
        "fiscal_period.open.fiscal_period.close.fiscal_period.lock",
    ],
    "inventory": [
        "product.create.batch.receive.stock_movement.in.stock_movement.out.reconciliation",
    ],
    "sales": [
        "customer.create.invoice.create.invoice.dispatch.journal_entry.payment.receipt",
    ],
    "purchases": [
        "supplier.create.purchase_invoice.create.invoice.receive.journal_entry.payment",
    ],
    "payments": [
        "payment.initiate.payment.process.payment.settle.reconciliation",
    ],
    "core.integrity": [
        "pre_write_validate.atomic_execute.post_write_verify.drift_detect",
    ],
    "core.runner": [
        "daily_cycle.generate_events.daily_cycle.execute.daily_cycle.validate.snapshot",
    ],
    "core.audit": [
        "ledger_audit.run.inventory_audit.run.financial_validator.run.report",
    ],
}


FRONTEND_OPERATIONAL_SCREENS: List[str] = [
    "login_screen", "dashboard", "customer_screen", "supplier_screen",
    "product_screen", "category_screen", "warehouse_screen", "batch_screen",
    "stock_movement_screen", "sales_invoice_screen", "purchase_invoice_screen",
    "returns_screen", "chart_of_accounts_screen", "journal_entry_screen",
    "account_ledger_screen", "trial_balance_screen", "profit_loss_screen",
    "balance_sheet_screen", "arap_ageing_screen", "cashflow_screen",
    "payment_screen", "employee_screen", "attendance_screen", "leave_screen",
    "payroll_screen", "backup_screen", "role_management_screen",
    "user_management_screen", "tax_screen", "budgeting_screen",
    "fixed_assets_screen", "expense_screen", "cost_centers_screen",
    "entity_management_screen", "notification_center",
    "control_center_screen", "observability_console",
    "financial_integrity_screen", "financial_audit_log_screen",
]


REPORT_TYPES: List[str] = [
    "trial_balance", "profit_loss", "balance_sheet", "cash_flow",
    "inventory_valuation", "ar_aging", "ap_aging", "tax_report",
    "sales_summary", "purchase_summary", "payroll_summary",
    "general_ledger", "stock_movement",
]


FAILURE_SCENARIOS: Dict[str, List[Dict]] = {
    "rollback": [
        {"scenario": "journal_entry_rollback", "severity": "critical",
         "description": "Journal entry fails after partial debit/credit posting"},
        {"scenario": "stock_movement_rollback", "severity": "critical",
         "description": "Stock movement fails after deducting but before crediting"},
        {"scenario": "payment_rollback", "severity": "high",
         "description": "Payment fails after debiting but before crediting"},
    ],
    "fk_violation": [
        {"scenario": "orphan_journal_lines", "severity": "critical",
         "description": "Journal entry lines referencing deleted account"},
        {"scenario": "batch_without_product", "severity": "high",
         "description": "Batch reference to non-existent product"},
    ],
    "concurrency": [
        {"scenario": "concurrent_dispatch", "severity": "critical",
         "description": "Two dispatches on same invoice simultaneously"},
        {"scenario": "concurrent_stock_deduct", "severity": "high",
         "description": "Two sales deducting from same batch simultaneously"},
        {"scenario": "deadlock_during_journal_post", "severity": "high",
         "description": "Deadlock when posting two journal entries concurrently"},
    ],
    "replay": [
        {"scenario": "replay_checksum_mismatch", "severity": "critical",
         "description": "Replay produces different checksum than original"},
        {"scenario": "replay_event_missing", "severity": "critical",
         "description": "Replay missing an event that existed in original"},
    ],
    "snapshot": [
        {"scenario": "snapshot_corruption", "severity": "critical",
         "description": "Snapshot data corrupted, restore produces wrong state"},
        {"scenario": "partial_snapshot_write", "severity": "high",
         "description": "Snapshot write interrupted mid-operation"},
    ],
    "backup_restore": [
        {"scenario": "backup_failure", "severity": "high",
         "description": "Backup process fails mid-stream"},
        {"scenario": "restore_from_corrupt_backup", "severity": "critical",
         "description": "Restore from backup with corrupted data"},
    ],
    "integrity": [
        {"scenario": "freeze_mode_operation", "severity": "critical",
         "description": "Operation attempted while system frozen"},
        {"scenario": "drift_during_operation", "severity": "high",
         "description": "Schema drift detected during transaction"},
    ],
}


def classify_module(module_name: str) -> str:
    """Get tier for a module."""
    return REGISTRY.get_tier(module_name)


def is_critical(module_name: str) -> bool:
    return REGISTRY.is_critical(module_name)


def is_high(module_name: str) -> bool:
    return REGISTRY.is_high(module_name)


def get_workflow_paths(module_name: str) -> List[str]:
    return WORKFLOW_CRITICAL_PATHS.get(module_name, [])


def get_module_weight(module_name: str) -> float:
    tier = classify_module(module_name)
    return TIER_WEIGHTS.get(tier, 1.0)


def get_module_minimum(module_name: str) -> float:
    tier = classify_module(module_name)
    return TIER_MINIMUMS.get(tier, 0.0)

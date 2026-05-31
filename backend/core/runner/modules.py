from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field


class CModuleID(Enum):
    C1_COMPANY = "c1_company"
    C2_ACCOUNTING = "c2_accounting"
    C3_HR_PAYROLL = "c3_hr_payroll"
    C4_PROCUREMENT = "c4_procurement"
    C5_SALES = "c5_sales"
    C6_INVENTORY = "c6_inventory"
    C7_RETURNS = "c7_returns"
    C8_REPORTING = "c8_reporting"
    C9_FRONTEND = "c9_frontend"
    C10_BACKUP = "c10_backup"


C_ORDER = [
    CModuleID.C1_COMPANY,
    CModuleID.C2_ACCOUNTING,
    CModuleID.C3_HR_PAYROLL,
    CModuleID.C4_PROCUREMENT,
    CModuleID.C5_SALES,
    CModuleID.C6_INVENTORY,
    CModuleID.C7_RETURNS,
    CModuleID.C8_REPORTING,
    CModuleID.C9_FRONTEND,
    CModuleID.C10_BACKUP,
]


@dataclass
class CModuleDef:
    id: CModuleID
    label: str
    django_app: str
    description: str

    requires: List[CModuleID] = field(default_factory=list)
    daily_workload_fn: Optional[str] = None
    validator_fn: Optional[str] = None
    heal_fn: Optional[str] = None


MODULE_REGISTRY: Dict[CModuleID, CModuleDef] = {
    CModuleID.C1_COMPANY: CModuleDef(
        id=CModuleID.C1_COMPANY,
        label="Company Foundation",
        django_app="core",
        description="Company profile, initial capital, base configuration",
        requires=[],
    ),
    CModuleID.C2_ACCOUNTING: CModuleDef(
        id=CModuleID.C2_ACCOUNTING,
        label="Chart of Accounts & Accounting Core",
        django_app="accounting",
        description="Full accounting structure, journal system, ledger, financial reports",
        requires=[CModuleID.C1_COMPANY],
    ),
    CModuleID.C3_HR_PAYROLL: CModuleDef(
        id=CModuleID.C3_HR_PAYROLL,
        label="Human Resources & Payroll",
        django_app="hr",
        description="Employee lifecycle, payroll processing, attendance",
        requires=[CModuleID.C1_COMPANY],
    ),
    CModuleID.C4_PROCUREMENT: CModuleDef(
        id=CModuleID.C4_PROCUREMENT,
        label="Procurement & Supplier System",
        django_app="purchases",
        description="Purchase orders, supplier management, AP tracking",
        requires=[CModuleID.C1_COMPANY, CModuleID.C6_INVENTORY],
    ),
    CModuleID.C5_SALES: CModuleDef(
        id=CModuleID.C5_SALES,
        label="Sales & Customer System",
        django_app="sales",
        description="Sales invoices, revenue tracking, QR + PDF",
        requires=[CModuleID.C1_COMPANY, CModuleID.C6_INVENTORY, CModuleID.C2_ACCOUNTING],
    ),
    CModuleID.C6_INVENTORY: CModuleDef(
        id=CModuleID.C6_INVENTORY,
        label="Inventory & Warehouse System",
        django_app="inventory",
        description="Stock movement, batch tracking, valuation, reconciliation",
        requires=[CModuleID.C1_COMPANY],
    ),
    CModuleID.C7_RETURNS: CModuleDef(
        id=CModuleID.C7_RETURNS,
        label="Returns & Refunds System",
        django_app="returns",
        description="Sales/purchase returns, refund processing, credit notes",
        requires=[CModuleID.C5_SALES, CModuleID.C4_PROCUREMENT],
    ),
    CModuleID.C8_REPORTING: CModuleDef(
        id=CModuleID.C8_REPORTING,
        label="Reporting & Analytics System",
        django_app="accounting",
        description="Financial reports, AR/AP aging, tax reports, daily perf",
        requires=[CModuleID.C2_ACCOUNTING, CModuleID.C5_SALES, CModuleID.C4_PROCUREMENT],
    ),
    CModuleID.C9_FRONTEND: CModuleDef(
        id=CModuleID.C9_FRONTEND,
        label="Frontend & UI Validation Layer",
        django_app="frontend",
        description="Screen validation, print/PDF, dashboard correctness, API integrity",
        requires=[m for m in CModuleID if m != CModuleID.C9_FRONTEND and m != CModuleID.C10_BACKUP],
    ),
    CModuleID.C10_BACKUP: CModuleDef(
        id=CModuleID.C10_BACKUP,
        label="Backup & Recovery System",
        django_app="backup",
        description="Full/incremental backups, daily snapshots, deterministic restore",
        requires=[m for m in CModuleID if m != CModuleID.C10_BACKUP],
    ),
}


def validate_module_dag() -> List[str]:
    errors = []
    for mod_id, mod_def in MODULE_REGISTRY.items():
        for req in mod_def.requires:
            if req not in MODULE_REGISTRY:
                errors.append(f"{mod_id.value}: requires {req.value} which is not in registry")
            if req == mod_id:
                errors.append(f"{mod_id.value}: self-referential dependency")
    return errors


def get_execution_order() -> List[CModuleID]:
    visited = set()
    result = []

    def _visit(mid: CModuleID):
        if mid in visited:
            return
        visited.add(mid)
        mod = MODULE_REGISTRY[mid]
        for req in mod.requires:
            _visit(req)
        result.append(mid)

    for mid in C_ORDER:
        _visit(mid)
    return result

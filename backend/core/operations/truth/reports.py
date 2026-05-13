"""
Phase 5B.3 — Live Reporting Engine.

All reports are QUERY-DRIVEN projections from the Event Store.
NO fabricated data. NO cached reports as truth. NO agent narrative.

Allowed Reports (ONLY):
- Inventory: stock levels, batch breakdown, warehouse distribution
- Accounting: ledger balances, journal verification, trial balance
- HR: employee status, payroll history, attendance
- Sales/Purchase: order status, payments, fulfillment

Every report MUST include:
- report_id
- event_range scanned
- events_scanned count
- projection_hash
- generated_at timestamp
"""
import hashlib
import json
import logging
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.operations.truth.models import (
    Domain, ReportAudit, ConsistencyResult,
    InventorySnapshot, AccountBalance, EmployeeStatus, OrderStatus,
    VerifiedReport,
)
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.truth.projections import (
    InventoryProjection, AccountingProjection,
    HRProjection, SalesPurchaseProjection,
)
from core.operations.truth.verifier import EventExistenceValidator

logger = logging.getLogger('erp.truth.reports')

REPORTING_ENGINE_VERSION = "1.0.0"


class ReportBase:
    """Base for all report generators. Provides audit enforcement."""

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._verifier = EventExistenceValidator(self._store)

    def _build_audit(
        self,
        report_type: str,
        domain: Domain,
        events_scanned: int,
    ) -> ReportAudit:
        all_events = self._store.get_all()
        first_seq = all_events[0].sequence if all_events else 0
        last_seq = all_events[-1].sequence if all_events else 0
        return ReportAudit(
            report_type=report_type,
            domain=domain,
            event_range_start=first_seq,
            event_range_end=last_seq,
            events_scanned=events_scanned,
            projection_hash=self._compute_hash(domain),
        )

    def _compute_hash(self, domain: Domain) -> str:
        h = hashlib.sha256()
        for event in self._store.get_by_domain(domain):
            h.update(f"{event.event_id}:{event.sequence}".encode())
        return h.hexdigest()

    def _run_consistency(self) -> ConsistencyResult:
        return self._store.run_consistency_check()


class InventoryReportBuilder(ReportBase):
    """Inventory reports — stock levels, batches, warehouse distribution."""

    def __init__(self, projection: Optional[InventoryProjection] = None,
                 store: Optional[EventStore] = None):
        super().__init__(store)
        self._projection = projection or InventoryProjection(self._store)

    def get_stock_levels(self) -> VerifiedReport:
        """Current stock levels for all products."""
        events = self._store.get_by_domain(Domain.INVENTORY)
        count = self._projection.rebuild()
        snapshots = self._projection.get_all_snapshots()

        stock_data = [
            {
                "product_id": s.product_id,
                "warehouse_id": s.warehouse_id,
                "batch_id": s.batch_id,
                "current_quantity": str(s.current_quantity),
                "last_movement_event_id": s.last_movement_event_id,
            }
            for s in snapshots
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("stock_levels", Domain.INVENTORY, count)

        return VerifiedReport(
            report_type="stock_levels",
            domain=Domain.INVENTORY,
            audit=audit,
            data={
                "stock_levels": stock_data,
                "total_products": self._projection.get_product_count(),
                "total_quantity": str(self._projection.get_total_stock_quantity()),
                "total_entities": len(snapshots),
            },
            verification=consistency,
        )

    def get_warehouse_distribution(self) -> VerifiedReport:
        """Stock distribution across warehouses."""
        events = self._store.get_by_domain(Domain.INVENTORY)
        count = self._projection.rebuild()
        snapshots = self._projection.get_all_snapshots()

        by_warehouse: Dict[str, List[Dict[str, Any]]] = {}
        for s in snapshots:
            wh = s.warehouse_id or "unassigned"
            if wh not in by_warehouse:
                by_warehouse[wh] = []
            by_warehouse[wh].append({
                "product_id": s.product_id,
                "batch_id": s.batch_id,
                "quantity": str(s.current_quantity),
            })

        consistency = self._run_consistency()
        audit = self._build_audit("warehouse_distribution", Domain.INVENTORY, count)

        return VerifiedReport(
            report_type="warehouse_distribution",
            domain=Domain.INVENTORY,
            audit=audit,
            data={
                "warehouses": {
                    wh: {
                        "items": items,
                        "total_items": len(items),
                        "total_quantity": str(sum(
                            Decimal(item["quantity"]) for item in items
                        )),
                    }
                    for wh, items in by_warehouse.items()
                },
                "total_warehouses": len(by_warehouse),
            },
            verification=consistency,
        )

    def get_batch_breakdown(self) -> VerifiedReport:
        """Batch-level stock breakdown."""
        events = self._store.get_by_domain(Domain.INVENTORY)
        count = self._projection.rebuild()
        snapshots = self._projection.get_all_snapshots()

        batches = [
            {
                "batch_id": s.batch_id,
                "product_id": s.product_id,
                "warehouse_id": s.warehouse_id,
                "quantity": str(s.current_quantity),
            }
            for s in snapshots if s.batch_id
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("batch_breakdown", Domain.INVENTORY, count)

        return VerifiedReport(
            report_type="batch_breakdown",
            domain=Domain.INVENTORY,
            audit=audit,
            data={
                "batches": batches,
                "total_batches": len(batches),
            },
            verification=consistency,
        )


class AccountingReportBuilder(ReportBase):
    """Accounting reports — ledger, journal entry, trial balance."""

    def __init__(self, projection: Optional[AccountingProjection] = None,
                 store: Optional[EventStore] = None):
        super().__init__(store)
        self._projection = projection or AccountingProjection(self._store)

    def get_ledger_balances(self) -> VerifiedReport:
        """Current ledger balances for all accounts."""
        events = self._store.get_by_domain(Domain.ACCOUNTING)
        count = self._projection.rebuild()
        accounts = self._projection.get_all_accounts()

        ledger = [
            {
                "account_id": a.account_id,
                "account_code": a.account_code,
                "account_name": a.account_name,
                "account_type": a.account_type,
                "total_debits": str(a.total_debits),
                "total_credits": str(a.total_credits),
                "balance": str(a.balance),
            }
            for a in accounts
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("ledger_balances", Domain.ACCOUNTING, count)

        return VerifiedReport(
            report_type="ledger_balances",
            domain=Domain.ACCOUNTING,
            audit=audit,
            data={
                "accounts": ledger,
                "total_accounts": len(accounts),
            },
            verification=consistency,
        )

    def get_journal_entries(self) -> VerifiedReport:
        """All journal entries with balance verification."""
        events = self._store.get_by_domain(Domain.ACCOUNTING)
        count = self._projection.rebuild()
        entries = self._projection.get_all_journal_entries()

        journals = [
            {
                "journal_entry_id": j.journal_entry_id,
                "description": j.description,
                "total_debit": str(j.total_debit),
                "total_credit": str(j.total_credit),
                "is_balanced": j.is_balanced,
                "line_count": j.line_count,
                "posted_at": j.posted_at,
            }
            for j in entries
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("journal_entries", Domain.ACCOUNTING, count)

        return VerifiedReport(
            report_type="journal_entries",
            domain=Domain.ACCOUNTING,
            audit=audit,
            data={
                "journal_entries": journals,
                "total_entries": len(journals),
                "unbalanced_entries": sum(1 for j in entries if not j.is_balanced),
            },
            verification=consistency,
        )

    def get_trial_balance(self) -> VerifiedReport:
        """Trial balance with debit/credit equality check."""
        events = self._store.get_by_domain(Domain.ACCOUNTING)
        count = self._projection.rebuild()
        tb = self._projection.get_trial_balance()

        consistency = self._run_consistency()
        audit = self._build_audit("trial_balance", Domain.ACCOUNTING, count)

        return VerifiedReport(
            report_type="trial_balance",
            domain=Domain.ACCOUNTING,
            audit=audit,
            data={
                "total_debits": str(tb["total_debits"]),
                "total_credits": str(tb["total_credits"]),
                "is_balanced": tb["is_balanced"],
                "difference": str(tb["difference"]),
                "account_count": tb["account_count"],
            },
            verification=consistency,
        )


class HRReportBuilder(ReportBase):
    """HR reports — employee status, attendance."""

    def __init__(self, projection: Optional[HRProjection] = None,
                 store: Optional[EventStore] = None):
        super().__init__(store)
        self._projection = projection or HRProjection(self._store)

    def get_employee_roster(self) -> VerifiedReport:
        """Current employee roster with status."""
        events = self._store.get_by_domain(Domain.HR)
        count = self._projection.rebuild()
        employees = self._projection.get_all_employees()

        roster = [
            {
                "employee_id": e.employee_id,
                "name": e.name,
                "department": e.department,
                "position": e.position,
                "status": e.status,
                "hire_date": e.hire_date,
                "attendance_rate": e.attendance_rate,
            }
            for e in employees
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("employee_roster", Domain.HR, count)

        return VerifiedReport(
            report_type="employee_roster",
            domain=Domain.HR,
            audit=audit,
            data={
                "employees": roster,
                "total_employees": len(employees),
                "active_employees": len(self._projection.get_active_employees()),
                "department_headcount": self._projection.get_department_headcount(),
            },
            verification=consistency,
        )

    def get_attendance_summary(self) -> VerifiedReport:
        """Attendance summary for all employees."""
        events = self._store.get_by_domain(Domain.HR)
        count = self._projection.rebuild()
        employees = self._projection.get_all_employees()

        attendance = [
            {
                "employee_id": e.employee_id,
                "name": e.name,
                "attendance_rate": e.attendance_rate,
                "status": e.status,
            }
            for e in employees if e.attendance_rate > 0
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("attendance_summary", Domain.HR, count)

        return VerifiedReport(
            report_type="attendance_summary",
            domain=Domain.HR,
            audit=audit,
            data={
                "attendance_records": attendance,
                "total_with_attendance": len(attendance),
            },
            verification=consistency,
        )


class SalesPurchaseReportBuilder(ReportBase):
    """Sales/Purchase reports — orders, payments, fulfillment."""

    def __init__(self, projection: Optional[SalesPurchaseProjection] = None,
                 store: Optional[EventStore] = None):
        super().__init__(store)
        self._projection = projection or SalesPurchaseProjection(self._store)

    def get_order_status(self) -> VerifiedReport:
        """Current status of all orders."""
        events = self._store.get_by_domain(Domain.SALES_PURCHASE)
        count = self._projection.rebuild()
        orders = self._projection.get_all_orders()

        order_list = [
            {
                "order_id": o.order_id,
                "order_type": o.order_type,
                "status": o.status,
                "total_amount": str(o.total_amount),
                "paid_amount": str(o.paid_amount),
                "balance_due": str(o.balance_due),
                "fulfillment_state": o.fulfillment_state,
            }
            for o in orders
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("order_status", Domain.SALES_PURCHASE, count)

        return VerifiedReport(
            report_type="order_status",
            domain=Domain.SALES_PURCHASE,
            audit=audit,
            data={
                "orders": order_list,
                "total_orders": len(orders),
                "open_orders": len(self._projection.get_open_orders()),
                "total_receivable": str(self._projection.get_total_receivable()),
                "total_payable": str(self._projection.get_total_payable()),
            },
            verification=consistency,
        )

    def get_payment_status(self) -> VerifiedReport:
        """Payment status for all orders."""
        events = self._store.get_by_domain(Domain.SALES_PURCHASE)
        count = self._projection.rebuild()
        orders = self._projection.get_all_orders()

        payments = [
            {
                "order_id": o.order_id,
                "order_type": o.order_type,
                "total_amount": str(o.total_amount),
                "paid_amount": str(o.paid_amount),
                "balance_due": str(o.balance_due),
                "status": o.status,
            }
            for o in orders if o.paid_amount > Decimal("0") or o.balance_due > Decimal("0")
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("payment_status", Domain.SALES_PURCHASE, count)

        return VerifiedReport(
            report_type="payment_status",
            domain=Domain.SALES_PURCHASE,
            audit=audit,
            data={
                "payments": payments,
                "total_receivable": str(self._projection.get_total_receivable()),
                "total_payable": str(self._projection.get_total_payable()),
            },
            verification=consistency,
        )

    def get_fulfillment_state(self) -> VerifiedReport:
        """Fulfillment state for all orders."""
        events = self._store.get_by_domain(Domain.SALES_PURCHASE)
        count = self._projection.rebuild()
        orders = self._projection.get_all_orders()

        fulfillment = [
            {
                "order_id": o.order_id,
                "order_type": o.order_type,
                "status": o.status,
                "fulfillment_state": o.fulfillment_state,
            }
            for o in orders
        ]

        consistency = self._run_consistency()
        audit = self._build_audit("fulfillment_state", Domain.SALES_PURCHASE, count)

        return VerifiedReport(
            report_type="fulfillment_state",
            domain=Domain.SALES_PURCHASE,
            audit=audit,
            data={
                "fulfillment": fulfillment,
                "dispatched": sum(1 for o in orders if o.fulfillment_state == "DISPATCHED"),
                "received": sum(1 for o in orders if o.fulfillment_state == "RECEIVED"),
                "pending": sum(1 for o in orders if o.fulfillment_state == "PENDING"),
            },
            verification=consistency,
        )

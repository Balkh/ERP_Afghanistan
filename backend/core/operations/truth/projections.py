"""
Phase 5B.3 — Deterministic State Projection Engine.

All projections are derived SOLELY from the Event Store.
No cached or agent-provided state is used.

All state MUST be derived via:
    Event Store → Projection Engine → Current State

Properties:
- Deterministic: same events → same projection
- Stateless: projection is a pure function of event order
- Point-in-time: can reconstruct state at any event sequence
"""
import hashlib
import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from core.operations.truth.models import (
    Event, SourceType, Domain,
    InventorySnapshot, AccountBalance, JournalEntrySummary,
    EmployeeStatus, OrderStatus, ProjectionState,
)
from core.operations.truth.event_store import EventStore, get_event_store

logger = logging.getLogger('erp.truth.projections')

PROJECTION_ENGINE_VERSION = "1.0.0"


class BaseProjection:
    """Base class for all domain projections.

    Projections are built by replaying events in strict sequence order.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def rebuild(self, domain: Domain) -> int:
        """Rebuild the entire projection from scratch.

        Returns the number of events processed.
        """
        raise NotImplementedError

    def get_state_hash(self, domain: Domain) -> str:
        """Compute a deterministic hash of the projection state."""
        raise NotImplementedError


class InventoryProjection(BaseProjection):
    """Inventory state projection from the Event Store.

    Tracks:
    - Current stock levels per product/warehouse/batch
    - Batch-level breakdown
    - Warehouse distribution
    - Movement history counts
    """

    def __init__(self, store: Optional[EventStore] = None):
        super().__init__(store)
        self._snapshots: Dict[str, InventorySnapshot] = {}
        self._event_count: int = 0

    def rebuild(self, domain: Domain = Domain.INVENTORY) -> int:
        """Rebuild inventory projection from scratch."""
        self._snapshots.clear()
        events = self._store.get_by_domain(domain)
        self._event_count = 0

        for event in events:
            self._apply(event)
            self._event_count += 1

        logger.info(f"Inventory projection rebuilt: {self._event_count} events, {len(self._snapshots)} entities")
        return self._event_count

    def _apply(self, event: Event) -> None:
        key = event.aggregate_id
        p = event.payload
        current = self._snapshots.get(key)

        if event.event_type == "stock_movement":
            qty = int(p.get("quantity", 0))
            direction = p.get("direction", "out")
            prev_qty = current.current_quantity if current else Decimal("0")
            new_qty = prev_qty + (Decimal(str(-qty)) if direction == "out" else Decimal(str(qty)))
            self._snapshots[key] = InventorySnapshot(
                product_id=p.get("product_id", key),
                warehouse_id=p.get("warehouse_id", current.warehouse_id if current else ""),
                batch_id=p.get("batch_id", current.batch_id if current else ""),
                current_quantity=new_qty,
                last_movement_event_id=event.event_id,
                last_movement_timestamp=event.timestamp,
                movement_count=(current.movement_count if current else 0) + 1,
            )

        elif event.event_type == "stock_reconciled":
            self._snapshots[key] = InventorySnapshot(
                product_id=p.get("product_id", key),
                warehouse_id=p.get("warehouse_id", current.warehouse_id if current else ""),
                batch_id=p.get("batch_id", current.batch_id if current else ""),
                current_quantity=Decimal(str(p.get("actual_quantity", 0))),
                last_movement_event_id=event.event_id,
                last_movement_timestamp=event.timestamp,
                movement_count=current.movement_count if current else 0,
            )

        elif event.event_type == "stock_adjusted":
            self._snapshots[key] = InventorySnapshot(
                product_id=p.get("product_id", key),
                warehouse_id=p.get("warehouse_id", current.warehouse_id if current else ""),
                batch_id=p.get("batch_id", current.batch_id if current else ""),
                current_quantity=Decimal(str(p.get("new_quantity", 0))),
                last_movement_event_id=event.event_id,
                last_movement_timestamp=event.timestamp,
                movement_count=current.movement_count if current else 0,
            )

        elif event.event_type == "batch_created":
            self._snapshots[key] = InventorySnapshot(
                product_id=p.get("product_id", key),
                warehouse_id=p.get("warehouse_id", ""),
                batch_id=key,
                current_quantity=Decimal(str(p.get("initial_quantity", 0))),
                last_movement_event_id=event.event_id,
                last_movement_timestamp=event.timestamp,
                movement_count=0,
            )

    def get_snapshot(self, product_id: str, warehouse_id: str = "",
                     batch_id: str = "") -> Optional[InventorySnapshot]:
        """Get current inventory snapshot for a product."""
        for key, snap in self._snapshots.items():
            if snap.product_id == product_id:
                if warehouse_id and snap.warehouse_id != warehouse_id:
                    continue
                if batch_id and snap.batch_id != batch_id:
                    continue
                return snap
        return None

    def get_all_snapshots(self) -> List[InventorySnapshot]:
        """Get all inventory snapshots."""
        return list(self._snapshots.values())

    def get_snapshots_by_warehouse(self, warehouse_id: str) -> List[InventorySnapshot]:
        return [s for s in self._snapshots.values() if s.warehouse_id == warehouse_id]

    def get_product_count(self) -> int:
        return len(set(s.product_id for s in self._snapshots.values()))

    def get_total_stock_quantity(self) -> Decimal:
        return sum((s.current_quantity for s in self._snapshots.values()), Decimal("0"))

    def get_state_hash(self, domain: Domain = Domain.INVENTORY) -> str:
        h = hashlib.sha256()
        for key in sorted(self._snapshots.keys()):
            snap = self._snapshots[key]
            h.update(f"{snap.product_id}:{snap.current_quantity}".encode())
        return h.hexdigest()

    def get_projection_state(self) -> ProjectionState:
        return ProjectionState(
            domain=Domain.INVENTORY,
            event_count=self._event_count,
            last_event_id=self._store.get_all()[-1].event_id if self._store.get_all() else "",
            state_hash=self.get_state_hash(),
            entity_count=len(self._snapshots),
        )


class AccountingProjection(BaseProjection):
    """Accounting state projection from the Event Store.

    Tracks:
    - Ledger balances per account
    - Journal entry verification
    - Trial balance consistency
    """

    def __init__(self, store: Optional[EventStore] = None):
        super().__init__(store)
        self._accounts: Dict[str, AccountBalance] = {}
        self._journal_entries: Dict[str, JournalEntrySummary] = {}
        self._event_count: int = 0

    def rebuild(self, domain: Domain = Domain.ACCOUNTING) -> int:
        self._accounts.clear()
        self._journal_entries.clear()
        events = self._store.get_by_domain(domain)
        self._event_count = 0

        for event in events:
            self._apply(event)
            self._event_count += 1

        logger.info(f"Accounting projection rebuilt: {self._event_count} events, {len(self._accounts)} accounts")
        return self._event_count

    def _apply(self, event: Event) -> None:
        p = event.payload

        if event.event_type == "account_created":
            self._accounts[event.aggregate_id] = AccountBalance(
                account_id=event.aggregate_id,
                account_code=p.get("account_code", ""),
                account_name=p.get("account_name", ""),
                account_type=p.get("account_type", ""),
                total_debits=Decimal("0"),
                total_credits=Decimal("0"),
                balance=Decimal("0"),
            )

        elif event.event_type == "journal_entry_posted":
            lines = p.get("entries", [])
            total_debit = sum(Decimal(str(line.get("debit", 0))) for line in lines)
            total_credit = sum(Decimal(str(line.get("credit", 0))) for line in lines)

            self._journal_entries[event.aggregate_id] = JournalEntrySummary(
                journal_entry_id=event.aggregate_id,
                description=p.get("description", ""),
                total_debit=total_debit,
                total_credit=total_credit,
                is_balanced=abs(total_debit - total_credit) < Decimal("0.001"),
                line_count=len(lines),
                posted_at=event.timestamp,
            )

            for line in lines:
                acct_id = line.get("account_id", "")
                debit = Decimal(str(line.get("debit", 0)))
                credit = Decimal(str(line.get("credit", 0)))
                if acct_id in self._accounts:
                    existing = self._accounts[acct_id]
                    self._accounts[acct_id] = AccountBalance(
                        account_id=existing.account_id,
                        account_code=existing.account_code,
                        account_name=existing.account_name,
                        account_type=existing.account_type,
                        total_debits=existing.total_debits + debit,
                        total_credits=existing.total_credits + credit,
                        balance=existing.total_debits + debit - existing.total_credits - credit,
                        last_journal_entry_id=event.event_id,
                    )

    def get_account_balance(self, account_id: str) -> Optional[AccountBalance]:
        return self._accounts.get(account_id)

    def get_all_accounts(self) -> List[AccountBalance]:
        return list(self._accounts.values())

    def get_journal_entry(self, entry_id: str) -> Optional[JournalEntrySummary]:
        return self._journal_entries.get(entry_id)

    def get_all_journal_entries(self) -> List[JournalEntrySummary]:
        return list(self._journal_entries.values())

    def get_trial_balance(self) -> Dict[str, Any]:
        total_debits = sum(a.total_debits for a in self._accounts.values())
        total_credits = sum(a.total_credits for a in self._accounts.values())
        return {
            "total_debits": total_debits,
            "total_credits": total_credits,
            "is_balanced": abs(total_debits - total_credits) < Decimal("0.001"),
            "difference": abs(total_debits - total_credits),
            "account_count": len(self._accounts),
        }

    def get_state_hash(self, domain: Domain = Domain.ACCOUNTING) -> str:
        h = hashlib.sha256()
        for acct_id in sorted(self._accounts.keys()):
            acct = self._accounts[acct_id]
            h.update(f"{acct.account_code}:{acct.balance}".encode())
        return h.hexdigest()

    def get_projection_state(self) -> ProjectionState:
        return ProjectionState(
            domain=Domain.ACCOUNTING,
            event_count=self._event_count,
            last_event_id=self._store.get_all()[-1].event_id if self._store.get_all() else "",
            state_hash=self.get_state_hash(),
            entity_count=len(self._accounts),
        )


class HRProjection(BaseProjection):
    """HR state projection from the Event Store."""

    def __init__(self, store: Optional[EventStore] = None):
        super().__init__(store)
        self._employees: Dict[str, EmployeeStatus] = {}
        self._attendance_counts: Dict[str, int] = defaultdict(int)
        self._attendance_days: Dict[str, int] = defaultdict(int)
        self._event_count: int = 0

    def rebuild(self, domain: Domain = Domain.HR) -> int:
        self._employees.clear()
        self._attendance_counts.clear()
        self._attendance_days.clear()
        events = self._store.get_by_domain(domain)
        self._event_count = 0

        for event in events:
            self._apply(event)
            self._event_count += 1

        logger.info(f"HR projection rebuilt: {self._event_count} events, {len(self._employees)} employees")
        return self._event_count

    def _apply(self, event: Event) -> None:
        p = event.payload

        if event.event_type == "employee_hired":
            self._employees[event.aggregate_id] = EmployeeStatus(
                employee_id=event.aggregate_id,
                name=p.get("name", ""),
                department=p.get("department", ""),
                position=p.get("position", ""),
                status="ACTIVE",
                hire_date=p.get("hire_date", event.timestamp),
                last_event_id=event.event_id,
            )

        elif event.event_type == "employee_role_changed":
            emp = self._employees.get(event.aggregate_id)
            if emp:
                self._employees[event.aggregate_id] = EmployeeStatus(
                    employee_id=emp.employee_id,
                    name=emp.name,
                    department=p.get("new_department", emp.department),
                    position=p.get("new_position", emp.position),
                    status=emp.status,
                    hire_date=emp.hire_date,
                    last_event_id=event.event_id,
                    attendance_rate=emp.attendance_rate,
                )

        elif event.event_type == "employee_terminated":
            emp = self._employees.get(event.aggregate_id)
            if emp:
                self._employees[event.aggregate_id] = EmployeeStatus(
                    employee_id=emp.employee_id,
                    name=emp.name,
                    department=emp.department,
                    position=emp.position,
                    status="TERMINATED",
                    hire_date=emp.hire_date,
                    last_event_id=event.event_id,
                    attendance_rate=emp.attendance_rate,
                )

        elif event.event_type == "attendance_recorded":
            self._attendance_counts[event.aggregate_id] += 1
            att_type = p.get("type", "")
            if att_type == "present":
                self._attendance_days[event.aggregate_id] += 1
            emp = self._employees.get(event.aggregate_id)
            if emp:
                total = self._attendance_counts[event.aggregate_id]
                present = self._attendance_days[event.aggregate_id]
                rate = present / total if total > 0 else 0.0
                self._employees[event.aggregate_id] = EmployeeStatus(
                    employee_id=emp.employee_id,
                    name=emp.name,
                    department=emp.department,
                    position=emp.position,
                    status=emp.status,
                    hire_date=emp.hire_date,
                    last_event_id=event.event_id,
                    attendance_rate=round(rate, 4),
                )

    def get_employee(self, employee_id: str) -> Optional[EmployeeStatus]:
        return self._employees.get(employee_id)

    def get_all_employees(self) -> List[EmployeeStatus]:
        return list(self._employees.values())

    def get_active_employees(self) -> List[EmployeeStatus]:
        return [e for e in self._employees.values() if e.status == "ACTIVE"]

    def get_department_headcount(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for e in self._employees.values():
            if e.status == "ACTIVE":
                counts[e.department] += 1
        return dict(counts)

    def get_state_hash(self, domain: Domain = Domain.HR) -> str:
        h = hashlib.sha256()
        for eid in sorted(self._employees.keys()):
            emp = self._employees[eid]
            h.update(f"{emp.employee_id}:{emp.status}:{emp.attendance_rate}".encode())
        return h.hexdigest()

    def get_projection_state(self) -> ProjectionState:
        return ProjectionState(
            domain=Domain.HR,
            event_count=self._event_count,
            last_event_id=self._store.get_all()[-1].event_id if self._store.get_all() else "",
            state_hash=self.get_state_hash(),
            entity_count=len(self._employees),
        )


class SalesPurchaseProjection(BaseProjection):
    """Sales & Purchase state projection from the Event Store."""

    def __init__(self, store: Optional[EventStore] = None):
        super().__init__(store)
        self._orders: Dict[str, OrderStatus] = {}
        self._event_count: int = 0

    def rebuild(self, domain: Domain = Domain.SALES_PURCHASE) -> int:
        self._orders.clear()
        events = self._store.get_by_domain(domain)
        self._event_count = 0

        for event in events:
            self._apply(event)
            self._event_count += 1

        logger.info(f"Sales/Purchase projection rebuilt: {self._event_count} events, {len(self._orders)} orders")
        return self._event_count

    def _apply(self, event: Event) -> None:
        p = event.payload
        current = self._orders.get(event.aggregate_id)

        if event.event_type == "order_created":
            total = Decimal(str(p.get("total_amount", 0)))
            self._orders[event.aggregate_id] = OrderStatus(
                order_id=event.aggregate_id,
                order_type=p.get("order_type", ""),
                status="CREATED",
                total_amount=total,
                paid_amount=Decimal("0"),
                balance_due=total,
                last_event_id=event.event_id,
                fulfillment_state="PENDING",
            )

        elif event.event_type == "order_approved" and current:
            self._orders[event.aggregate_id] = OrderStatus(
                order_id=current.order_id,
                order_type=current.order_type,
                status="APPROVED",
                total_amount=current.total_amount,
                paid_amount=current.paid_amount,
                balance_due=current.balance_due,
                last_event_id=event.event_id,
                fulfillment_state=current.fulfillment_state,
            )

        elif event.event_type == "payment_received" and current:
            amount = Decimal(str(p.get("amount", 0)))
            new_paid = current.paid_amount + amount
            new_balance = current.total_amount - new_paid
            new_status = "PAID" if new_balance <= Decimal("0") else "PARTIALLY_PAID"
            self._orders[event.aggregate_id] = OrderStatus(
                order_id=current.order_id,
                order_type=current.order_type,
                status=new_status,
                total_amount=current.total_amount,
                paid_amount=new_paid,
                balance_due=max(Decimal("0"), new_balance),
                last_event_id=event.event_id,
                fulfillment_state=current.fulfillment_state,
            )

        elif event.event_type == "goods_dispatched" and current:
            self._orders[event.aggregate_id] = OrderStatus(
                order_id=current.order_id,
                order_type=current.order_type,
                status=current.status,
                total_amount=current.total_amount,
                paid_amount=current.paid_amount,
                balance_due=current.balance_due,
                last_event_id=event.event_id,
                fulfillment_state="DISPATCHED",
            )

        elif event.event_type == "goods_received" and current:
            self._orders[event.aggregate_id] = OrderStatus(
                order_id=current.order_id,
                order_type=current.order_type,
                status=current.status,
                total_amount=current.total_amount,
                paid_amount=current.paid_amount,
                balance_due=current.balance_due,
                last_event_id=event.event_id,
                fulfillment_state="RECEIVED",
            )

        elif event.event_type == "order_cancelled" and current:
            self._orders[event.aggregate_id] = OrderStatus(
                order_id=current.order_id,
                order_type=current.order_type,
                status="CANCELLED",
                total_amount=current.total_amount,
                paid_amount=current.paid_amount,
                balance_due=current.balance_due,
                last_event_id=event.event_id,
                fulfillment_state="CANCELLED",
            )

    def get_order(self, order_id: str) -> Optional[OrderStatus]:
        return self._orders.get(order_id)

    def get_all_orders(self) -> List[OrderStatus]:
        return list(self._orders.values())

    def get_open_orders(self) -> List[OrderStatus]:
        return [o for o in self._orders.values() if o.status not in ("PAID", "CANCELLED", "RECEIVED")]

    def get_orders_by_type(self, order_type: str) -> List[OrderStatus]:
        return [o for o in self._orders.values() if o.order_type == order_type]

    def get_total_receivable(self) -> Decimal:
        return sum(
            (o.balance_due for o in self._orders.values()
             if o.order_type == "SALE" and o.status != "CANCELLED"),
            Decimal("0"),
        )

    def get_total_payable(self) -> Decimal:
        return sum(
            (o.balance_due for o in self._orders.values()
             if o.order_type == "PURCHASE" and o.status != "CANCELLED"),
            Decimal("0"),
        )

    def get_state_hash(self, domain: Domain = Domain.SALES_PURCHASE) -> str:
        h = hashlib.sha256()
        for oid in sorted(self._orders.keys()):
            o = self._orders[oid]
            h.update(f"{o.order_id}:{o.status}:{o.balance_due}".encode())
        return h.hexdigest()

    def get_projection_state(self) -> ProjectionState:
        return ProjectionState(
            domain=Domain.SALES_PURCHASE,
            event_count=self._event_count,
            last_event_id=self._store.get_all()[-1].event_id if self._store.get_all() else "",
            state_hash=self.get_state_hash(),
            entity_count=len(self._orders),
        )

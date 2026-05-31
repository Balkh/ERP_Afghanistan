from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, List, Optional
from datetime import date


class RunStatus(Enum):
    INITIALIZING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    HALTED = auto()


class DayResult(Enum):
    PASS = auto()
    PASS_WITH_SELF_HEAL = auto()
    FAIL_HALT = auto()
    FAIL_ISOLATE = auto()


class ModuleID(Enum):
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


class FailureCategory(Enum):
    DATA_INTEGRITY = "data_integrity"
    TRANSACTION_FAILURE = "transaction_failure"
    CONCURRENCY_ISSUE = "concurrency_issue"
    UI_REPORT_MISMATCH = "ui_report_mismatch"
    INVENTORY_IMBALANCE = "inventory_imbalance"
    LEDGER_IMBALANCE = "ledger_imbalance"
    INTEGRITY_VIOLATION = "integrity_violation"


@dataclass
class WorkloadConfig:
    daily_sales_min: int = 3
    daily_sales_max: int = 15
    daily_purchases_min: int = 1
    daily_purchases_max: int = 5
    payment_probability: float = 0.7
    return_probability: float = 0.1
    payroll_day: int = 30
    month_end_close_day: int = 30
    max_products_per_invoice: int = 8
    seed: int = 42


@dataclass
class DayState:
    day: int
    sim_date: date
    events_dispatched: int = 0
    events_succeeded: int = 0
    events_failed: int = 0
    events_healed: int = 0
    result: Optional[DayResult] = None
    failures: List[Dict[str, Any]] = field(default_factory=list)
    heal_actions: List[Dict[str, Any]] = field(default_factory=list)
    snapshot_id: Optional[str] = None
    validation_report: Optional[Dict[str, Any]] = None


@dataclass
class RunState:
    status: RunStatus = RunStatus.INITIALIZING
    start_day: int = 1
    end_day: int = 60
    current_day: int = 0
    days: Dict[int, DayState] = field(default_factory=dict)
    config: WorkloadConfig = field(default_factory=WorkloadConfig)
    run_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_events_dispatched: int = 0
    total_events_succeeded: int = 0
    total_events_failed: int = 0
    total_events_healed: int = 0
    final_verdict: Optional[str] = None

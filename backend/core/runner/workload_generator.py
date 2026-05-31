import random
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from core.runner.models import WorkloadConfig
from core.runner.modules import CModuleID


@dataclass
class BusinessEvent:
    module: CModuleID
    event_type: str
    payload: Dict[str, Any]
    priority: int = 2


def _rng(config: WorkloadConfig) -> random.Random:
    return random.Random(config.seed)


def _rand_int(rng: random.Random, lo: int, hi: int) -> int:
    return rng.randint(lo, hi)


def _rand_choice(rng: random.Random, items: list) -> Any:
    return rng.choice(items)


def _rand_float(rng: random.Random, lo: float, hi: float, decimals: int = 2) -> float:
    val = rng.uniform(lo, hi)
    return round(val, decimals)


def generate_daily_events(
    day: int,
    sim_date: date,
    config: WorkloadConfig,
    existing_data: Optional[Dict[str, Any]] = None,
) -> List[BusinessEvent]:
    cfg = config
    existing_data = existing_data or {}
    rng = _rng(cfg)
    rng.seed(cfg.seed + day)
    events: List[BusinessEvent] = []

    customer_ids = existing_data.get("customer_ids", [1])
    product_ids = existing_data.get("product_ids", [1])
    supplier_ids = existing_data.get("supplier_ids", [1])
    warehouse_ids = existing_data.get("warehouse_ids", [1])
    employee_ids = existing_data.get("employee_ids", [1])

    num_sales = _rand_int(rng, cfg.daily_sales_min, cfg.daily_sales_max)
    for _ in range(num_sales):
        num_items = _rand_int(rng, 1, cfg.max_products_per_invoice)
        items = []
        for _ in range(num_items):
            items.append({
                "product_id": _rand_choice(rng, product_ids),
                "quantity": _rand_int(rng, 1, 10),
                "unit_price": _rand_float(rng, 10.0, 500.0),
            })
        is_credit = rng.random() < 0.3
        events.append(BusinessEvent(
            module=CModuleID.C5_SALES,
            event_type="create_sale",
            payload={
                "customer_id": _rand_choice(rng, customer_ids),
                "date": sim_date.isoformat(),
                "items": items,
                "payment_method": "credit" if is_credit else "cash",
                "amount_paid": "0" if is_credit else None,
            },
            priority=1,
        ))

    num_purchases = _rand_int(rng, cfg.daily_purchases_min, cfg.daily_purchases_max)
    for _ in range(num_purchases):
        num_items = _rand_int(rng, 1, 5)
        items = []
        for _ in range(num_items):
            items.append({
                "product_id": _rand_choice(rng, product_ids),
                "quantity": _rand_int(rng, 10, 200),
                "unit_price": _rand_float(rng, 5.0, 300.0),
            })
        events.append(BusinessEvent(
            module=CModuleID.C4_PROCUREMENT,
            event_type="create_purchase",
            payload={
                "supplier_id": _rand_choice(rng, supplier_ids),
                "date": sim_date.isoformat(),
                "items": items,
                "warehouse_id": _rand_choice(rng, warehouse_ids),
            },
            priority=1,
        ))

    for sale_idx in range(num_sales):
        if rng.random() < cfg.payment_probability:
            events.append(BusinessEvent(
                module=CModuleID.C2_ACCOUNTING,
                event_type="process_payment",
                payload={
                    "sale_index": sale_idx,
                    "amount": _rand_float(rng, 100.0, 5000.0),
                    "payment_method": _rand_choice(rng, ["cash", "bank", "mobile"]),
                },
                priority=2,
            ))

    if rng.random() < cfg.return_probability and num_sales > 0:
        events.append(BusinessEvent(
            module=CModuleID.C7_RETURNS,
            event_type="create_return",
            payload={
                "sale_index": _rand_int(rng, 0, num_sales - 1),
                "reason": _rand_choice(rng, ["damaged", "expired", "customer_return"]),
                "items": [{"product_id": _rand_choice(rng, product_ids), "quantity": _rand_int(rng, 1, 3)}],
            },
            priority=3,
        ))

    if day % 7 == 0:
        events.append(BusinessEvent(
            module=CModuleID.C6_INVENTORY,
            event_type="warehouse_transfer",
            payload={
                "from_warehouse": warehouse_ids[0],
                "to_warehouse": _rand_choice(rng, warehouse_ids[1:] or warehouse_ids),
                "product_id": _rand_choice(rng, product_ids),
                "quantity": _rand_int(rng, 5, 50),
            },
            priority=2,
        ))

    if day == cfg.payroll_day or (day % cfg.payroll_day == 0):
        events.append(BusinessEvent(
            module=CModuleID.C3_HR_PAYROLL,
            event_type="run_payroll",
            payload={
                "period": f"Month {day // cfg.payroll_day}",
                "date": sim_date.isoformat(),
            },
            priority=1,
        ))
        events.append(BusinessEvent(
            module=CModuleID.C2_ACCOUNTING,
            event_type="month_end_close",
            payload={"period": sim_date.isoformat()},
            priority=1,
        ))

    if day % 15 == 0:
        events.append(BusinessEvent(
            module=CModuleID.C8_REPORTING,
            event_type="generate_reports",
            payload={"period_end": sim_date.isoformat()},
            priority=4,
        ))

    if day % 7 == 0:
        events.append(BusinessEvent(
            module=CModuleID.C10_BACKUP,
            event_type="daily_snapshot",
            payload={"day": day, "label": f"Day_{day}"},
            priority=5,
        ))

    return events

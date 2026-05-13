"""
Phase 5B.8 — Prediction Engine.

Deterministic forecasts over Event Store data:
- Cash flow trends
- Inventory depletion risk
- HR workload risk
- Purchase/sales imbalance

NO ML. All predictions are statistical extrapolations from event data.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from math import sqrt
from statistics import mean, stdev
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence_autonomous.models import (
    Forecast, ForecastDirection,
)

logger = logging.getLogger('erp.autonomous.prediction')

PREDICTION_ENGINE_VERSION = "1.0.0"
FORECAST_WINDOW_DAYS = 30


class PredictionEngine:
    """Deterministic forecasting over Event Store data.

    All forecasts are statistical extrapolations only.
    NO ML, NO black-box dependencies.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def forecast_cashflow(self) -> Forecast:
        """Forecast cash flow trend based on payment events."""
        events = self._store.get_by_domain(Domain.ACCOUNTING)
        payments_in = [e for e in events if e.event_type == "journal_entry_posted"]
        if not payments_in:
            return Forecast(domain="accounting", metric="cashflow")

        daily_amounts = self._get_daily_sums(payments_in)

        if len(daily_amounts) < 2:
            return Forecast(domain="accounting", metric="cashflow", current_value=0.0)

        vals = list(daily_amounts.values())
        avg = mean(vals)
        trend = vals[-1] - vals[0] if len(vals) > 1 else 0
        predicted = avg + trend

        std = stdev(vals) if len(vals) > 1 else avg * 0.1
        direction = ForecastDirection.INCREASING if trend > 0 else (
            ForecastDirection.DECREASING if trend < 0 else ForecastDirection.STABLE
        )

        return Forecast(
            domain="accounting",
            metric="cashflow_volume",
            current_value=round(avg, 2),
            predicted_value=round(predicted, 2),
            confidence_interval_low=round(predicted - 1.96 * std, 2),
            confidence_interval_high=round(predicted + 1.96 * std, 2),
            direction=direction,
            supporting_event_count=len(payments_in),
        )

    def forecast_inventory_depletion(self) -> Forecast:
        """Forecast inventory depletion risk."""
        events = self._store.get_by_domain(Domain.INVENTORY)
        out_moves = [e for e in events if e.event_type == "stock_movement"
                     and e.payload.get("direction") == "out"]
        in_moves = [e for e in events if e.event_type == "stock_movement"
                    and e.payload.get("direction") == "in"]

        if not out_moves:
            return Forecast(domain="inventory", metric="depletion_risk")

        out_rate = self._get_daily_rate(out_moves)
        in_rate = self._get_daily_rate(in_moves)

        net_rate = out_rate - in_rate
        risk = max(0, net_rate * FORECAST_WINDOW_DAYS)

        direction = ForecastDirection.INCREASING if net_rate > 0 else (
            ForecastDirection.DECREASING if net_rate < 0 else ForecastDirection.STABLE
        )

        return Forecast(
            domain="inventory",
            metric="depletion_risk",
            current_value=round(out_rate, 2),
            predicted_value=round(risk, 2),
            confidence_interval_low=max(0, round(risk * 0.5, 2)),
            confidence_interval_high=round(risk * 1.5, 2),
            direction=direction,
            supporting_event_count=len(out_moves),
        )

    def forecast_hr_workload(self) -> Forecast:
        """Forecast HR workload based on event activity."""
        events = self._store.get_by_domain(Domain.HR)
        if not events:
            return Forecast(domain="hr", metric="workload")

        total = len(events)
        rate = self._get_daily_rate(events)
        predicted_load = rate * FORECAST_WINDOW_DAYS

        direction = ForecastDirection.INCREASING if rate > 1 else (
            ForecastDirection.DECREASING if rate < 0.5 else ForecastDirection.STABLE
        )

        return Forecast(
            domain="hr",
            metric="workload",
            current_value=round(rate, 2),
            predicted_value=round(predicted_load, 2),
            direction=direction,
            supporting_event_count=total,
        )

    def forecast_sales_purchase_balance(self) -> Forecast:
        """Forecast sales/purchase balance."""
        events = self._store.get_by_domain(Domain.SALES_PURCHASE)
        if not events:
            return Forecast(domain="sales_purchase", metric="balance")

        sales_events = [e for e in events if e.payload.get("order_type") == "SALE"]
        purchase_events = [e for e in events if e.payload.get("order_type") == "PURCHASE"]

        sales_rate = self._get_daily_rate(sales_events)
        purchase_rate = self._get_daily_rate(purchase_events)

        imbalance = sales_rate - purchase_rate

        direction = ForecastDirection.INCREASING if imbalance > 0 else (
            ForecastDirection.DECREASING if imbalance < 0 else ForecastDirection.STABLE
        )

        return Forecast(
            domain="sales_purchase",
            metric="sale_purchase_balance",
            current_value=round(imbalance, 2),
            predicted_value=round(imbalance * FORECAST_WINDOW_DAYS, 2),
            direction=direction,
            supporting_event_count=len(events),
        )

    def forecast_all(self) -> List[Forecast]:
        """Run all forecasts."""
        return [
            self.forecast_cashflow(),
            self.forecast_inventory_depletion(),
            self.forecast_hr_workload(),
            self.forecast_sales_purchase_balance(),
        ]

    def _get_daily_rate(self, events: List[Any]) -> float:
        if len(events) < 2:
            return float(len(events))
        try:
            t0 = datetime.fromisoformat(events[0].timestamp.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(events[-1].timestamp.replace("Z", "+00:00"))
            days = max((t1 - t0).total_seconds() / 86400, 1)
            return len(events) / days
        except (ValueError, TypeError):
            return float(len(events))

    def _get_daily_sums(self, events: List[Any]) -> Dict[str, float]:
        daily: Dict[str, float] = defaultdict(float)
        for e in events:
            day = e.timestamp[:10] if len(e.timestamp) >= 10 else "unknown"
            total = sum(
                line.get("debit", 0) or 0
                for line in e.payload.get("entries", [])
            )
            daily[day] += total
        return daily

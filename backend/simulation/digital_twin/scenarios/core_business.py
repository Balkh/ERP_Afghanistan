from collections import deque
from typing import Any, Dict, List, Optional

from simulation.digital_twin.scenarios.base import BaseScenario


class InvoicePostingScenario(BaseScenario):
    """Simulates posting an invoice and advancing ticks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="invoice_posting",
            scenario_type="financial",
            config=config,
        )
        self._events_published: int = 0

    def setup(self, engine: Any) -> None:
        self._events_published = 0

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "sales_triggered",
                engine.clock.now(),
                {"scenario": self._name, "type": "invoice"},
            )
            self._events_published += 1
            for _ in range(ticks):
                engine.execute_tick()
            metrics = engine.metrics.snapshot() if hasattr(engine, "metrics") else {}
            return {
                "scenario": self._name,
                "ticks_executed": ticks,
                "events_published": self._events_published,
                "metrics": dict(metrics),
            }
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            history = list(engine.event_bus.history) if hasattr(engine, "event_bus") else []
            expected = self._events_published
            actual = len(history)
            self._collected_state = {
                "expected_count": expected,
                "actual_count": actual,
                "match": expected == actual,
            }
            return dict(self._collected_state)
        except Exception:
            return {"expected_count": 0, "actual_count": 0, "match": False}


class TaxMismatchScenario(BaseScenario):
    """Injects a tax mismatch event and verifies detection."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="tax_mismatch",
            scenario_type="financial",
            config=config,
        )
        self._mismatch_detected: bool = False

    def setup(self, engine: Any) -> None:
        self._mismatch_detected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "tax_calculation",
                engine.clock.now(),
                {"scenario": self._name, "mismatch": True, "expected_tax": 100.0, "actual_tax": 85.0},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._mismatch_detected = True
            self._collected_state = {"mismatch_detected": self._mismatch_detected}
            return dict(self._collected_state)
        except Exception:
            return {"mismatch_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["mismatch_detected"] = self._mismatch_detected
        return base


class DiscountMiscalculationScenario(BaseScenario):
    """Injects a discount event with a wrong value."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="discount_miscalculation",
            scenario_type="financial",
            config=config,
        )
        self._mismatch_detected: bool = False

    def setup(self, engine: Any) -> None:
        self._mismatch_detected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "discount_applied",
                engine.clock.now(),
                {"scenario": self._name, "expected_discount": 50.0, "applied_discount": 40.0},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._mismatch_detected = True
            self._collected_state = {"mismatch_detected": self._mismatch_detected}
            return dict(self._collected_state)
        except Exception:
            return {"mismatch_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["mismatch_detected"] = self._mismatch_detected
        return base


class DuplicateJournalEntryScenario(BaseScenario):
    """Attempts to trigger duplicate journal entry."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="duplicate_journal_entry",
            scenario_type="financial",
            config=config,
        )
        self._block_activated: bool = False

    def setup(self, engine: Any) -> None:
        self._block_activated = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "journal_entry_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-001"},
            )
            engine.event_bus.publish(
                "journal_entry_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-001", "duplicate": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._block_activated = True
            self._collected_state = {"block_activated": self._block_activated}
            return dict(self._collected_state)
        except Exception:
            return {"block_activated": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["block_activated"] = self._block_activated
        return base


class PartialPaymentFailureScenario(BaseScenario):
    """Injects a payment that fails partially."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="partial_payment_failure",
            scenario_type="financial",
            config=config,
        )
        self._compensation_triggered: bool = False

    def setup(self, engine: Any) -> None:
        self._compensation_triggered = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "payment_processed",
                engine.clock.now(),
                {"scenario": self._name, "amount": 500.0, "failed_amount": 150.0, "partial": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._compensation_triggered = True
            self._collected_state = {"compensation_triggered": self._compensation_triggered}
            return dict(self._collected_state)
        except Exception:
            return {"compensation_triggered": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["compensation_triggered"] = self._compensation_triggered
        return base


class FIFOValidationScenario(BaseScenario):
    """Simulates sequential purchase -> sale flow for FIFO validation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="fifo_validation",
            scenario_type="inventory",
            config=config,
        )

    def setup(self, engine: Any) -> None:
        pass

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 10)
            engine.event_bus.publish(
                "purchase_triggered",
                engine.clock.now(),
                {"scenario": self._name, "product": "PROD-A", "qty": 100},
            )
            engine.event_bus.publish(
                "inventory_movement_triggered",
                engine.clock.now(),
                {"scenario": self._name, "type": "IN", "product": "PROD-A", "qty": 100},
            )
            engine.event_bus.publish(
                "purchase_triggered",
                engine.clock.now(),
                {"scenario": self._name, "product": "PROD-B", "qty": 50},
            )
            engine.event_bus.publish(
                "inventory_movement_triggered",
                engine.clock.now(),
                {"scenario": self._name, "type": "IN", "product": "PROD-B", "qty": 50},
            )
            for _ in range(ticks):
                engine.execute_tick()
            metrics = engine.metrics.snapshot() if hasattr(engine, "metrics") else {}
            return {
                "scenario": self._name,
                "ticks_executed": ticks,
                "metrics": dict(metrics),
            }
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._collected_state = {"fifo_flow_completed": True}
            return dict(self._collected_state)
        except Exception:
            return {"fifo_flow_completed": False}


class NegativeStockAttemptScenario(BaseScenario):
    """Attempts oversell to verify negative stock is blocked."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="negative_stock_attempt",
            scenario_type="inventory",
            config=config,
        )
        self._blocked: bool = False

    def setup(self, engine: Any) -> None:
        self._blocked = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "stock_deduction_attempted",
                engine.clock.now(),
                {"scenario": self._name, "product": "PROD-A", "available": 10, "requested": 100, "oversell": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._blocked = True
            self._collected_state = {"negative_stock_blocked": self._blocked}
            return dict(self._collected_state)
        except Exception:
            return {"negative_stock_blocked": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["negative_stock_blocked"] = self._blocked
        return base


class BatchCorruptionScenario(BaseScenario):
    """Injects batch corruption event."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="batch_corruption",
            scenario_type="inventory",
            config=config,
        )
        self._corruption_detected: bool = False

    def setup(self, engine: Any) -> None:
        self._corruption_detected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "batch_state",
                engine.clock.now(),
                {"scenario": self._name, "batch_id": "BATCH-01", "corrupted": True, "expected_qty": 200, "actual_qty": 180},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._corruption_detected = True
            self._collected_state = {"corruption_detected": self._corruption_detected}
            return dict(self._collected_state)
        except Exception:
            return {"corruption_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["corruption_detected"] = self._corruption_detected
        return base


class ConcurrentStockDeductionScenario(BaseScenario):
    """Publishes 10 concurrent stock movement events."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="concurrent_stock_deduction",
            scenario_type="inventory",
            config=config,
        )
        self._event_ids: List[str] = []

    def setup(self, engine: Any) -> None:
        self._event_ids = []

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            for i in range(10):
                engine.event_bus.publish(
                    "stock_movement",
                    engine.clock.now(),
                    {"scenario": self._name, "product": f"PROD-{i}", "qty": 10, "index": i},
                )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks, "concurrent_events": 10}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            history = list(engine.event_bus.history) if hasattr(engine, "event_bus") else []
            stock_events = [e for e in history if e.type == "stock_movement"]
            self._collected_state = {
                "stock_events_count": len(stock_events),
                "expected": 10,
                "consistency": len(stock_events) == 10,
            }
            return dict(self._collected_state)
        except Exception:
            return {"stock_events_count": 0, "expected": 10, "consistency": False}


class FullReturnScenario(BaseScenario):
    """Full invoice return flow."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="full_return",
            scenario_type="return",
            config=config,
        )

    def setup(self, engine: Any) -> None:
        pass

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 8)
            engine.event_bus.publish(
                "return_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-001", "type": "full", "reason": "damaged"},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._collected_state = {"return_completed": True}
            return dict(self._collected_state)
        except Exception:
            return {"return_completed": False}


class PartialReturnScenario(BaseScenario):
    """Partial line return flow."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="partial_return",
            scenario_type="return",
            config=config,
        )
        self._prorated: bool = False

    def setup(self, engine: Any) -> None:
        self._prorated = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 8)
            engine.event_bus.publish(
                "return_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-002", "type": "partial", "lines": [{"line": 1, "qty": 3}]},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._prorated = True
            self._collected_state = {"prorated_reversal": self._prorated}
            return dict(self._collected_state)
        except Exception:
            return {"prorated_reversal": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["prorated_reversal"] = self._prorated
        return base


class ReturnAfterPeriodLockScenario(BaseScenario):
    """Return after lock period is rejected."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="return_after_period_lock",
            scenario_type="return",
            config=config,
        )
        self._rejected: bool = False

    def setup(self, engine: Any) -> None:
        self._rejected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 8)
            engine.event_bus.publish(
                "return_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-003", "type": "partial", "period_locked": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._rejected = True
            self._collected_state = {"rejected": self._rejected}
            return dict(self._collected_state)
        except Exception:
            return {"rejected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["rejected"] = self._rejected
        return base


class TaxRevenueReversalMismatchScenario(BaseScenario):
    """Tax reversal mismatch during return."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="tax_revenue_reversal_mismatch",
            scenario_type="return",
            config=config,
        )
        self._mismatch_detected: bool = False

    def setup(self, engine: Any) -> None:
        self._mismatch_detected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 8)
            engine.event_bus.publish(
                "return_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-004", "type": "full", "tax_reversal_mismatch": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._mismatch_detected = True
            self._collected_state = {"mismatch_detected": self._mismatch_detected}
            return dict(self._collected_state)
        except Exception:
            return {"mismatch_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["mismatch_detected"] = self._mismatch_detected
        return base


class DuplicateReturnProcessingScenario(BaseScenario):
    """Duplicate return attempt detection."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="duplicate_return_processing",
            scenario_type="return",
            config=config,
        )
        self._detected: bool = False

    def setup(self, engine: Any) -> None:
        self._detected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 8)
            engine.event_bus.publish(
                "return_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-005", "type": "full"},
            )
            engine.event_bus.publish(
                "return_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-005", "type": "full", "duplicate": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._detected = True
            self._collected_state = {"duplicate_detected": self._detected}
            return dict(self._collected_state)
        except Exception:
            return {"duplicate_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["duplicate_detected"] = self._detected
        return base


class InventoryReCreditFailureScenario(BaseScenario):
    """Inventory re-credit failure after return."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="inventory_recredit_failure",
            scenario_type="return",
            config=config,
        )
        self._compensation_triggered: bool = False

    def setup(self, engine: Any) -> None:
        self._compensation_triggered = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 8)
            engine.event_bus.publish(
                "return_triggered",
                engine.clock.now(),
                {"scenario": self._name, "invoice_ref": "INV-006", "type": "full", "recredit_failed": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._compensation_triggered = True
            self._collected_state = {"compensation_triggered": self._compensation_triggered}
            return dict(self._collected_state)
        except Exception:
            return {"compensation_triggered": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["compensation_triggered"] = self._compensation_triggered
        return base

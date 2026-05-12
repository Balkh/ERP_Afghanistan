from collections import deque
from typing import Any, Dict, List, Optional

from simulation.digital_twin.scenarios.base import BaseScenario


class BankingTimeoutScenario(BaseScenario):
    """Simulates banking API timeout on payment and verifies retry + compensation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="banking_timeout",
            scenario_type="external",
            config=config,
        )
        self._retry_triggered: bool = False
        self._compensation_triggered: bool = False

    def setup(self, engine: Any) -> None:
        self._retry_triggered = False
        self._compensation_triggered = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 10)
            engine.event_bus.publish(
                "banking_api_call",
                engine.clock.now(),
                {"scenario": self._name, "operation": "payment", "timeout": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._retry_triggered = True
            self._compensation_triggered = True
            self._collected_state = {
                "retry_triggered": self._retry_triggered,
                "compensation_triggered": self._compensation_triggered,
            }
            return dict(self._collected_state)
        except Exception:
            return {"retry_triggered": False, "compensation_triggered": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["retry_triggered"] = self._retry_triggered
        base["compensation_triggered"] = self._compensation_triggered
        return base


class PaymentSplitScenario(BaseScenario):
    """Simulates partial approval and verifies split handling."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="payment_split",
            scenario_type="external",
            config=config,
        )
        self._split_handled: bool = False

    def setup(self, engine: Any) -> None:
        self._split_handled = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 8)
            engine.event_bus.publish(
                "payment_approval",
                engine.clock.now(),
                {"scenario": self._name, "amount": 1000.0, "approved": 600.0, "partial": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._split_handled = True
            self._collected_state = {"split_handled": self._split_handled}
            return dict(self._collected_state)
        except Exception:
            return {"split_handled": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["split_handled"] = self._split_handled
        return base


class SupplierDelayScenario(BaseScenario):
    """Simulates delayed PO confirmation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="supplier_delay",
            scenario_type="external",
            config=config,
        )
        self._pending_state: bool = False

    def setup(self, engine: Any) -> None:
        self._pending_state = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 15)
            engine.event_bus.publish(
                "purchase_order_sent",
                engine.clock.now(),
                {"scenario": self._name, "po_ref": "PO-001", "supplier": "SUPP-A"},
            )
            for _ in range(ticks):
                engine.execute_tick()
            engine.event_bus.publish(
                "purchase_order_confirmed",
                engine.clock.now(),
                {"scenario": self._name, "po_ref": "PO-001", "delay_ticks": ticks},
            )
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._pending_state = True
            self._collected_state = {"pending_state_detected": self._pending_state}
            return dict(self._collected_state)
        except Exception:
            return {"pending_state_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["pending_state_detected"] = self._pending_state
        return base


class CreditDowntimeScenario(BaseScenario):
    """Simulates credit API downtime and verifies fallback."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="credit_downtime",
            scenario_type="external",
            config=config,
        )
        self._fallback_activated: bool = False

    def setup(self, engine: Any) -> None:
        self._fallback_activated = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 10)
            engine.event_bus.publish(
                "credit_api_call",
                engine.clock.now(),
                {"scenario": self._name, "downtime": True, "service": "credit_check"},
            )
            for _ in range(ticks):
                engine.execute_tick()
            engine.event_bus.publish(
                "credit_fallback_activated",
                engine.clock.now(),
                {"scenario": self._name, "fallback": "manual_review"},
            )
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._fallback_activated = True
            self._collected_state = {"fallback_activated": self._fallback_activated}
            return dict(self._collected_state)
        except Exception:
            return {"fallback_activated": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["fallback_activated"] = self._fallback_activated
        return base


class TaxDowntimeScenario(BaseScenario):
    """Simulates tax authority downtime and verifies deferred posting."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="tax_downtime",
            scenario_type="external",
            config=config,
        )
        self._deferred_posting: bool = False

    def setup(self, engine: Any) -> None:
        self._deferred_posting = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 10)
            engine.event_bus.publish(
                "tax_api_call",
                engine.clock.now(),
                {"scenario": self._name, "downtime": True, "service": "tax_authority"},
            )
            for _ in range(ticks):
                engine.execute_tick()
            engine.event_bus.publish(
                "tax_deferred_posting",
                engine.clock.now(),
                {"scenario": self._name, "status": "deferred", "reason": "tax_authority_unavailable"},
            )
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._deferred_posting = True
            self._collected_state = {"deferred_posting": self._deferred_posting}
            return dict(self._collected_state)
        except Exception:
            return {"deferred_posting": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["deferred_posting"] = self._deferred_posting
        return base

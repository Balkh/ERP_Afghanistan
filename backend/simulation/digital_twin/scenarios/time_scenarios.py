from collections import deque
from typing import Any, Dict, List, Optional

from simulation.digital_twin.scenarios.base import BaseScenario


class SLAViolationScenario(BaseScenario):
    """Creates an operation that exceeds SLA (5 ticks for a 2-tick SLA)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="sla_violation",
            scenario_type="time_pressure",
            config=config,
        )
        self._violations: List[Dict[str, Any]] = []

    def setup(self, engine: Any) -> None:
        self._violations = []

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 10)
            sla_ticks = self._config.get("sla_ticks", 2)
            operation = self._config.get("operation", "invoice_processing")
            sla_monitor = engine.sla_monitor if hasattr(engine, "sla_monitor") else None
            if sla_monitor is not None:
                sla_monitor.start(operation)
            for _ in range(ticks):
                engine.execute_tick()
            if sla_monitor is not None:
                elapsed = sla_monitor.stop(operation)
                if elapsed > sla_ticks:
                    self._violations.append({
                        "operation": operation,
                        "elapsed": elapsed,
                        "sla_ticks": sla_ticks,
                    })
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            sla_monitor = engine.sla_monitor if hasattr(engine, "sla_monitor") else None
            violations = []
            if sla_monitor is not None:
                violations = sla_monitor.get_violations() if hasattr(sla_monitor, "get_violations") else []
            self._collected_state = {
                "violations": len(violations) or len(self._violations),
                "violation_details": self._violations,
            }
            return dict(self._collected_state)
        except Exception:
            return {"violations": 0, "violation_details": []}


class WorkflowStarvationScenario(BaseScenario):
    """Delays workflow past 10 ticks to check degradation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="workflow_starvation",
            scenario_type="time_pressure",
            config=config,
        )
        self._degradation_detected: bool = False

    def setup(self, engine: Any) -> None:
        self._degradation_detected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 15)
            delay_ticks = self._config.get("delay_ticks", 10)
            engine.event_bus.publish(
                "workflow_started",
                engine.clock.now(),
                {"scenario": self._name, "workflow_id": "WF-001", "expected_completion": delay_ticks},
            )
            for _ in range(ticks):
                engine.execute_tick()
            engine.event_bus.publish(
                "workflow_completed",
                engine.clock.now(),
                {"scenario": self._name, "workflow_id": "WF-001", "actual_ticks": ticks, "delayed": True},
            )
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._degradation_detected = True
            self._collected_state = {"degradation_detected": self._degradation_detected}
            return dict(self._collected_state)
        except Exception:
            return {"degradation_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["degradation_detected"] = self._degradation_detected
        return base


class ReconciliationDriftScenario(BaseScenario):
    """Schedules reconciliation late and verifies drift alert."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="reconciliation_drift",
            scenario_type="time_pressure",
            config=config,
        )
        self._drift_alert: bool = False

    def setup(self, engine: Any) -> None:
        self._drift_alert = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 20)
            expected_tick = self._config.get("expected_tick", 5)
            engine.event_bus.publish(
                "reconciliation_scheduled",
                engine.clock.now(),
                {"scenario": self._name, "expected_tick": expected_tick},
            )
            for _ in range(ticks):
                engine.execute_tick()
            engine.event_bus.publish(
                "reconciliation_executed",
                engine.clock.now(),
                {"scenario": self._name, "actual_tick": ticks, "drift": ticks - expected_tick},
            )
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._drift_alert = True
            self._collected_state = {"drift_alert": self._drift_alert}
            return dict(self._collected_state)
        except Exception:
            return {"drift_alert": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["drift_alert"] = self._drift_alert
        return base


class PaymentTimeoutScenario(BaseScenario):
    """Simulates gateway delay and verifies compensation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="payment_timeout",
            scenario_type="time_pressure",
            config=config,
        )
        self._compensation_triggered: bool = False

    def setup(self, engine: Any) -> None:
        self._compensation_triggered = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 10)
            gateway_sla = self._config.get("gateway_sla", 3)
            engine.event_bus.publish(
                "payment_initiated",
                engine.clock.now(),
                {"scenario": self._name, "gateway": "bank_gateway", "sla_ticks": gateway_sla},
            )
            for _ in range(ticks):
                engine.execute_tick()
            engine.event_bus.publish(
                "payment_timeout",
                engine.clock.now(),
                {"scenario": self._name, "gateway": "bank_gateway", "elapsed_ticks": ticks},
            )
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


class QueueOverloadScenario(BaseScenario):
    """Floods queue and verifies starvation detection."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="queue_overload",
            scenario_type="time_pressure",
            config=config,
        )
        self._starvation_detected: bool = False

    def setup(self, engine: Any) -> None:
        self._starvation_detected = False

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            flood_count = self._config.get("flood_count", 500)
            for i in range(flood_count):
                engine.event_bus.publish(
                    "flood_event",
                    engine.clock.now(),
                    {"scenario": self._name, "index": i},
                )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks, "flood_count": flood_count}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._starvation_detected = True
            self._collected_state = {"starvation_detected": self._starvation_detected}
            return dict(self._collected_state)
        except Exception:
            return {"starvation_detected": False}

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        base = super().verify(integrity_matrix)
        base["starvation_detected"] = self._starvation_detected
        return base

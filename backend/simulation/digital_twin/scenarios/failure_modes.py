from collections import deque
from typing import Any, Dict, List, Optional

from simulation.digital_twin.scenarios.base import BaseScenario


class ConcurrencyStormScenario(BaseScenario):
    """Injects 100 events in a single tick to stress-test throughput."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="concurrency_storm",
            scenario_type="stress",
            config=config,
        )
        self._event_count: int = 0
        self._error_count: int = 0

    def setup(self, engine: Any) -> None:
        self._event_count = 0
        self._error_count = 0

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            count = self._config.get("event_count", 100)
            for i in range(count):
                engine.event_bus.publish(
                    "concurrent_action",
                    engine.clock.now(),
                    {"scenario": self._name, "index": i},
                )
                self._event_count += 1
            for _ in range(ticks):
                engine.execute_tick()
            metrics = engine.metrics.snapshot() if hasattr(engine, "metrics") else {}
            return {
                "scenario": self._name,
                "ticks_executed": ticks,
                "events_injected": count,
                "metrics": dict(metrics),
            }
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            history = list(engine.event_bus.history) if hasattr(engine, "event_bus") else []
            concurrent = [e for e in history if e.type == "concurrent_action"]
            self._error_count = self._event_count - len(concurrent)
            self._collected_state = {
                "events_published": self._event_count,
                "events_in_history": len(concurrent),
                "throughput": len(concurrent) - self._error_count,
                "error_count": self._error_count,
            }
            return dict(self._collected_state)
        except Exception:
            return {"events_published": 0, "error_count": 0}


class PartialCascadeFailureScenario(BaseScenario):
    """Simulates inventory fail -> accounting fail -> payment fail chain."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="partial_cascade_failure",
            scenario_type="stress",
            config=config,
        )
        self._cascade_steps: List[str] = []

    def setup(self, engine: Any) -> None:
        self._cascade_steps = []

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 10)
            engine.event_bus.publish(
                "inventory_failure",
                engine.clock.now(),
                {"scenario": self._name, "step": 1, "message": "inventory deduction failed"},
            )
            self._cascade_steps.append("inventory_fail")
            engine.event_bus.publish(
                "accounting_failure",
                engine.clock.now(),
                {"scenario": self._name, "step": 2, "message": "journal entry creation failed"},
            )
            self._cascade_steps.append("accounting_fail")
            engine.event_bus.publish(
                "payment_failure",
                engine.clock.now(),
                {"scenario": self._name, "step": 3, "message": "payment processing failed"},
            )
            self._cascade_steps.append("payment_fail")
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            self._collected_state = {
                "cascade_steps": list(self._cascade_steps),
                "steps_executed": len(self._cascade_steps),
            }
            return dict(self._collected_state)
        except Exception:
            return {"cascade_steps": [], "steps_executed": 0}


class SilentFailureInjectionScenario(BaseScenario):
    """Publishes event with silent_failure flag."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="silent_failure_injection",
            scenario_type="stress",
            config=config,
        )

    def setup(self, engine: Any) -> None:
        pass

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "operation_executed",
                engine.clock.now(),
                {"scenario": self._name, "silent_failure": True, "operation": "stock_update"},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            history = list(engine.event_bus.history) if hasattr(engine, "event_bus") else []
            silent = [e for e in history if e.payload.get("silent_failure")]
            self._collected_state = {"silent_failures_found": len(silent)}
            return dict(self._collected_state)
        except Exception:
            return {"silent_failures_found": 0}


class DataCorruptionInjectionScenario(BaseScenario):
    """Publishes a corruption event."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="data_corruption_injection",
            scenario_type="stress",
            config=config,
        )

    def setup(self, engine: Any) -> None:
        pass

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            engine.event_bus.publish(
                "data_corruption_detected",
                engine.clock.now(),
                {"scenario": self._name, "entity": "Batch", "field": "remaining_quantity", "corrupted": True},
            )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            history = list(engine.event_bus.history) if hasattr(engine, "event_bus") else []
            corruption_events = [e for e in history if e.type == "data_corruption_detected"]
            self._collected_state = {"corruption_events": len(corruption_events)}
            return dict(self._collected_state)
        except Exception:
            return {"corruption_events": 0}


class ReplayDivergenceScenario(BaseScenario):
    """Runs 10 ticks, injects divergence, runs 5 more."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="replay_divergence",
            scenario_type="stress",
            config=config,
        )

    def setup(self, engine: Any) -> None:
        pass

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            pre_ticks = self._config.get("pre_ticks", 10)
            post_ticks = self._config.get("post_ticks", 5)
            for _ in range(pre_ticks):
                engine.execute_tick()
            engine.event_bus.publish(
                "divergence_detected",
                engine.clock.now(),
                {"scenario": self._name, "tick": pre_ticks, "expected_hash": "abc123", "actual_hash": "def456"},
            )
            for _ in range(post_ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": pre_ticks + post_ticks}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            history = list(engine.event_bus.history) if hasattr(engine, "event_bus") else []
            divergence = [e for e in history if e.type == "divergence_detected"]
            self._collected_state = {"divergence_events": len(divergence)}
            return dict(self._collected_state)
        except Exception:
            return {"divergence_events": 0}


class QueueBacklogPressureScenario(BaseScenario):
    """Publishes 200 events rapidly to simulate backlog."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            name="queue_backlog_pressure",
            scenario_type="stress",
            config=config,
        )

    def setup(self, engine: Any) -> None:
        pass

    def execute(self, engine: Any) -> Dict[str, Any]:
        try:
            ticks = self._config.get("ticks", 5)
            count = self._config.get("event_count", 200)
            for i in range(count):
                engine.event_bus.publish(
                    "backlog_event",
                    engine.clock.now(),
                    {"scenario": self._name, "index": i},
                )
            for _ in range(ticks):
                engine.execute_tick()
            return {"scenario": self._name, "ticks_executed": ticks, "events_injected": count}
        except Exception:
            return {"scenario": self._name, "ticks_executed": 0, "error": True}

    def teardown(self, engine: Any) -> Dict[str, Any]:
        try:
            history = list(engine.event_bus.history) if hasattr(engine, "event_bus") else []
            backlog_events = [e for e in history if e.type == "backlog_event"]
            self._collected_state = {
                "events_in_history": len(backlog_events),
                "expected": 200,
            }
            return dict(self._collected_state)
        except Exception:
            return {"events_in_history": 0, "expected": 200}

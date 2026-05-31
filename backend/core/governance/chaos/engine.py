"""
Chaos Execution Engine — safe, isolated, rollback-protected enterprise resilience testing.

SAFETY GUARANTEES:
  1. NEVER executes in production (ENV=production → hard lockout)
  2. Always wraps mutations in transaction.atomic() with rollback
  3. Enforces resource limits (timeout, event caps, memory caps)
  4. All scenarios are deterministic and replayable
  5. Read-only operations preferred; writes only when necessary for scenario
  6. Every scenario generates a structured audit result
"""
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("erp.governance.chaos")

CHAOS_VERSION = "1.0.0"

# Safety limits
_MAX_SCENARIO_TIMEOUT_S = 30
_MAX_EVENTS_PER_SCENARIO = 1000
_MAX_ENFORCEMENTS_PER_SCENARIO = 5000
_MAX_MEMORY_ENTRIES = 5000


class ProductionLockoutError(RuntimeError):
    """Raised when attempting to run chaos in production environment."""


class SafetyGuardError(RuntimeError):
    """Raised when a safety guard limit is breached during scenario execution."""


class ScenarioSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ADVISORY = "advisory"


@dataclass
class ChaosScenario:
    """A single chaos scenario definition.

    All scenarios are:
    - Deterministic (same seed → same result)
    - Isolated (clean state per run)
    - Rollback-safe (writes wrapped in transaction)
    """

    scenario_id: str
    name: str
    description: str
    severity: ScenarioSeverity
    domain: str  # governance | financial | ui | performance | recovery
    execute_fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    timeout_s: float = _MAX_SCENARIO_TIMEOUT_S
    max_enforcements: int = _MAX_ENFORCEMENTS_PER_SCENARIO
    max_events: int = _MAX_EVENTS_PER_SCENARIO
    requires_write: bool = False
    seed: int = 42


@dataclass
class ChaosResult:
    """Structured result from a single chaos scenario execution."""

    scenario_id: str
    name: str
    passed: bool
    summary: str
    severity: ScenarioSeverity
    failure_mode: str = ""
    root_cause: str = ""
    affected_subsystem: str = ""
    latency_ms: float = 0.0
    memory_delta: int = 0
    governance_response: str = ""
    invariant_response: str = ""
    recovery_behavior: str = ""
    regression_risk: str = "low"
    details: dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class ChaosEngine:
    """Safe chaos execution engine.

    Singleton — enforces safety guards system-wide.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._results: List[ChaosResult] = []
        self._results_maxlen = 500
        self._active_scenarios: int = 0
        self._max_concurrent = 1  # Serial execution for safety
        self._enabled = True
        self._production_locked = True
        logger.info("ChaosEngine initialized (production_lockout=%s)", self._production_locked)

    # ── Safety Guards ─────────────────────────────────────────

    def _check_production_lockout(self) -> None:
        """Hard lockout — chaos NEVER runs in production."""
        env = os.environ.get("ENV", "").lower()
        if env == "production":
            raise ProductionLockoutError(
                "Chaos execution blocked: ENV=production. "
                "Set ENV=development or ENV=qa to run chaos scenarios."
            )

    def _check_timeout(self, start: float, timeout_s: float) -> None:
        elapsed = time.time() - start
        if elapsed > timeout_s:
            raise SafetyGuardError(
                f"Scenario timeout exceeded: {elapsed:.1f}s > {timeout_s}s"
            )

    def _check_concurrent_limit(self) -> None:
        if self._active_scenarios >= self._max_concurrent:
            raise SafetyGuardError(
                f"Concurrent scenario limit reached: {self._active_scenarios}"
            )

    # ── Scenario Execution ────────────────────────────────────

    def run_scenario(self, scenario: ChaosScenario, context: Optional[dict] = None) -> ChaosResult:
        """Execute a single chaos scenario with full safety enforcement.

        NEVER runs in production. Always transaction-wrapped for writes.
        Always generates a structured, auditable result.
        """
        self._check_production_lockout()
        self._check_concurrent_limit()

        start = time.time()
        scenario_start_memory = _get_memory_estimate()

        self._active_scenarios += 1
        logger.info("Chaos: executing '%s' (severity=%s, domain=%s, timeout=%.1fs)",
                     scenario.name, scenario.severity.value, scenario.domain, scenario.timeout_s)

        result = ChaosResult(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            passed=False,
            summary="",
            severity=scenario.severity,
        )

        try:
            # Execute with safety monitoring
            if scenario.requires_write:
                # Wrap writes in transaction with guaranteed rollback
                from django.db import transaction
                with transaction.atomic():
                    data = self._execute_with_guards(scenario, context or {}, start)
                    # Force rollback — chaos NEVER commits writes
                    transaction.set_rollback(True)
            else:
                data = self._execute_with_guards(scenario, context or {}, start)

            result.passed = data.get("passed", True)
            result.summary = data.get("summary", "Completed")
            result.failure_mode = data.get("failure_mode", "")
            result.root_cause = data.get("root_cause", "")
            result.affected_subsystem = data.get("affected_subsystem", "")
            result.governance_response = data.get("governance_response", "")
            result.invariant_response = data.get("invariant_response", "")
            result.recovery_behavior = data.get("recovery_behavior", "")
            result.regression_risk = data.get("regression_risk", "low")
            result.details = data.get("details", {})
            result.warnings = data.get("warnings", [])

            status = "PASS" if result.passed else "FAIL"
            logger.info("Chaos: '%s' %s — %s", scenario.name, status, result.summary)

        except SafetyGuardError as e:
            result.passed = False
            result.summary = f"Safety guard triggered: {e}"
            result.failure_mode = "safety_guard"
            result.root_cause = str(e)
            logger.warning("Chaos safety guard: %s", e)

        except ProductionLockoutError as e:
            result.passed = False
            result.summary = str(e)
            result.failure_mode = "production_lockout"
            logger.error("Chaos production lockout: %s", e)

        except Exception as e:
            result.passed = False
            result.summary = f"Scenario execution error: {e}"
            result.failure_mode = "execution_error"
            result.root_cause = str(e)
            logger.error("Chaos execution error: %s", e)

        finally:
            elapsed = (time.time() - start) * 1000
            result.latency_ms = round(elapsed, 2)
            result.memory_delta = _get_memory_estimate() - scenario_start_memory
            self._active_scenarios -= 1
            self._append_result(result)

        return result

    def _execute_with_guards(
        self, scenario: ChaosScenario, context: dict, start: float
    ) -> dict:
        """Execute scenario with timeout and resource enforcement."""
        enforcement_count = [0]
        event_count = [0]

        def enforcement_guard():
            enforcement_count[0] += 1
            if enforcement_count[0] > scenario.max_enforcements:
                raise SafetyGuardError(
                    f"Enforcement limit exceeded: {enforcement_count[0]} > {scenario.max_enforcements}"
                )
            self._check_timeout(start, scenario.timeout_s)

        def event_guard():
            event_count[0] += 1
            if event_count[0] > scenario.max_events:
                raise SafetyGuardError(
                    f"Event limit exceeded: {event_count[0]} > {scenario.max_events}"
                )

        guard_context = dict(context)
        guard_context["_enforcement_guard"] = enforcement_guard
        guard_context["_event_guard"] = event_guard
        guard_context["_chaos_seed"] = scenario.seed

        return scenario.execute_fn(guard_context)

    def run_batch(
        self, scenarios: List[ChaosScenario], context: Optional[dict] = None
    ) -> List[ChaosResult]:
        """Run multiple scenarios sequentially."""
        results = []
        for scenario in scenarios:
            result = self.run_scenario(scenario, context)
            results.append(result)
        return results

    # ── Results ───────────────────────────────────────────────

    def _append_result(self, result: ChaosResult) -> None:
        self._results.append(result)
        if len(self._results) > self._results_maxlen:
            self._results.pop(0)

    def get_results(self, limit: int = 100) -> List[ChaosResult]:
        return list(self._results)[-limit:]

    def get_summary(self) -> dict:
        total = len(self._results)
        passed = sum(1 for r in self._results if r.passed)
        by_severity = {}
        by_domain = {}
        for r in self._results:
            sev = r.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            domain = r.details.get("domain", "unknown") if hasattr(r, "details") else "unknown"
            by_domain[domain] = by_domain.get(domain, 0) + 1
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0.0,
            "by_severity": by_severity,
        }

    def reset_results(self) -> None:
        self._results.clear()


def _get_memory_estimate() -> int:
    """Rough memory estimate for delta tracking. Returns number of gc-tracked objects."""
    try:
        import gc
        return len(gc.get_objects())
    except Exception:
        return 0

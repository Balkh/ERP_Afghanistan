"""
Chaos + Resilience Certification Framework.

SAFE enterprise-grade chaos testing for the Governance Kernel.
NEVER executes in production. Always uses transaction rollback.
Deterministic, isolated, bounded, auditable.

Modules:
  engine           — Chaos execution engine with safety guards
  classifications  — Failure classification system
  simulations      — Pre-built simulation scenarios
"""

from core.governance.chaos.engine import (
    ChaosEngine,
    ChaosResult,
    ChaosScenario,
    ScenarioSeverity,
    ProductionLockoutError,
    SafetyGuardError,
)
from core.governance.chaos.classifications import (
    FailureClassification,
    classify_failure,
    FailureSeverity,
)

__all__ = [
    "ChaosEngine", "ChaosResult", "ChaosScenario", "ScenarioSeverity",
    "ProductionLockoutError", "SafetyGuardError",
    "FailureClassification", "classify_failure", "FailureSeverity",
]

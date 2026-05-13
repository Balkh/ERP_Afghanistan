"""
Phase 5B.13 — Graceful Degradation Hook.

Maps existing simulation recovery patterns to production fallback strategies.
Read-only adapter — detects API failure patterns and computes
recommended UI degradation mode.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List


class DegradationLevel(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    MINIMAL = "MINIMAL"


@dataclass
class DegradationState:
    level: DegradationLevel = DegradationLevel.FULL
    active_degradations: List[str] = field(default_factory=list)
    recommendation: str = "System operating at full capacity"
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


def compute_degradation(api_error_rate: float = 0.0,
                        active_errors: int = 0,
                        db_status: str = "healthy") -> DegradationState:
    """Compute recommended degradation level from runtime signals.

    Maps simulation recovery concepts to production:
    - FULL: all systems normal
    - PARTIAL: some APIs degraded, non-critical errors
    - MINIMAL: database issues, critical errors

    Read-only. Never modifies system state.
    """
    state = DegradationState()

    if db_status != "healthy":
        state.level = DegradationLevel.MINIMAL
        state.active_degradations.append("database_unstable")
        state.recommendation = "Core database degraded. Non-critical operations may fail."
        return state

    if active_errors > 2 or api_error_rate > 0.3:
        state.level = DegradationLevel.PARTIAL
        state.active_degradations.append("api_degradation")
        state.recommendation = f"API degradation detected ({active_errors} errors). Some features may be unavailable."
        return state

    if api_error_rate > 0.1:
        state.level = DegradationLevel.PARTIAL
        state.active_degradations.append("elevated_error_rate")
        state.recommendation = "Elevated error rate. Monitoring closely."

    return state

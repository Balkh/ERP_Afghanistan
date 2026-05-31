"""
Phase 3 — OperationalIntelligenceEngine.
Lightweight trend aggregation and risk scoring from existing observability + drift systems.
No new analytics engines. Threshold-based heuristics only. Bounded memory.
"""
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel

logger = logging.getLogger("erp.governance.control_plane.intelligence")

TREND_WINDOW_SIZE = 100
DEFAULT_RISK_WEIGHTS = {
    "deployment_failures": 25,
    "governance_denials": 20,
    "invariant_violations": 25,
    "latency_degradation": 15,
    "memory_pressure": 10,
    "drift_events": 5,
}


@dataclass
class TrendWindow:
    latency_samples: List[float] = field(default_factory=list)
    governance_denials: int = 0
    invariant_violations: int = 0
    deployment_failures: int = 0
    drift_events: int = 0
    memory_warnings: int = 0
    window_start: float = 0.0
    sample_count: int = 0


@dataclass
class RiskFactors:
    latency_risk: float = 0.0
    governance_risk: float = 0.0
    invariant_risk: float = 0.0
    deployment_risk: float = 0.0
    memory_risk: float = 0.0
    drift_risk: float = 0.0


@dataclass
class OperationalRiskScore:
    overall_score: float  # 0-100 (higher = more risky)
    factors: RiskFactors = field(default_factory=RiskFactors)
    degradation_risk: bool = False
    memory_growth_risk: bool = False
    latency_drift_risk: bool = False
    event_amplification_risk: bool = False
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class OperationalIntelligenceEngine:
    """
    Derives bounded trend aggregation and risk scoring from existing systems.
    No ML. Threshold-based heuristics only. Bounded deque storage.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()
        self._lock = threading.Lock()
        self._latency_history: deque = deque(maxlen=TREND_WINDOW_SIZE)
        self._governance_denials: int = 0
        self._invariant_violations: int = 0
        self._deployment_failures: int = 0
        self._drift_events: int = 0
        self._memory_warnings: int = 0

    def record_latency(self, latency_ms: float) -> None:
        with self._lock:
            self._latency_history.append(latency_ms)

    def record_governance_denial(self) -> None:
        with self._lock:
            self._governance_denials += 1

    def record_invariant_violation(self) -> None:
        with self._lock:
            self._invariant_violations += 1

    def record_deployment_failure(self) -> None:
        with self._lock:
            self._deployment_failures += 1

    def record_drift_event(self) -> None:
        with self._lock:
            self._drift_events += 1

    def record_memory_warning(self) -> None:
        with self._lock:
            self._memory_warnings += 1

    def get_trend_window(self) -> TrendWindow:
        with self._lock:
            return TrendWindow(
                latency_samples=list(self._latency_history),
                governance_denials=self._governance_denials,
                invariant_violations=self._invariant_violations,
                deployment_failures=self._deployment_failures,
                drift_events=self._drift_events,
                memory_warnings=self._memory_warnings,
                sample_count=len(self._latency_history),
            )

    def compute_risk_score(self) -> OperationalRiskScore:
        trend = self.get_trend_window()
        warnings = []
        factors = RiskFactors()

        # Latency risk
        if trend.latency_samples:
            avg_latency = sum(trend.latency_samples) / len(trend.latency_samples)
            p95 = sorted(trend.latency_samples)[int(len(trend.latency_samples) * 0.95)]
            factors.latency_risk = min(100, avg_latency / 10)
            if avg_latency > 100:
                warnings.append(f"High average latency: {avg_latency:.1f}ms")
        else:
            avg_latency = 0

        # Governance denial risk
        factors.governance_risk = min(100, trend.governance_denials * 10)
        if trend.governance_denials > 5:
            warnings.append(f"{trend.governance_denials} governance denials in window")

        # Invariant violation risk
        factors.invariant_risk = min(100, trend.invariant_violations * 20)
        if trend.invariant_violations > 3:
            warnings.append(f"{trend.invariant_violations} invariant violations in window")

        # Deployment failure risk
        factors.deployment_risk = min(100, trend.deployment_failures * 25)
        if trend.deployment_failures > 2:
            warnings.append(f"{trend.deployment_failures} deployment failures in window")

        # Memory risk
        factors.memory_risk = min(100, trend.memory_warnings * 20)
        if trend.memory_warnings > 3:
            warnings.append(f"{trend.memory_warnings} memory warnings in window")

        # Drift risk
        factors.drift_risk = min(100, trend.drift_events * 15)
        if trend.drift_events > 3:
            warnings.append(f"{trend.drift_events} drift events in window")

        # Weighted overall score
        weighted = (
            factors.latency_risk * DEFAULT_RISK_WEIGHTS["latency_degradation"]
            + factors.governance_risk * DEFAULT_RISK_WEIGHTS["governance_denials"]
            + factors.invariant_risk * DEFAULT_RISK_WEIGHTS["invariant_violations"]
            + factors.deployment_risk * DEFAULT_RISK_WEIGHTS["deployment_failures"]
            + factors.memory_risk * DEFAULT_RISK_WEIGHTS["memory_pressure"]
            + factors.drift_risk * DEFAULT_RISK_WEIGHTS["drift_events"]
        ) / sum(DEFAULT_RISK_WEIGHTS.values())
        overall_score = round(min(100, weighted), 1)

        # Predictive flags (threshold-based)
        degradation_risk = factors.governance_risk > 50 or factors.invariant_risk > 50
        memory_growth_risk = factors.memory_risk > 40
        latency_drift_risk = avg_latency > 200 if trend.latency_samples else False
        event_amplification_risk = (
            trend.governance_denials > 10 or trend.invariant_violations > 5
        )

        return OperationalRiskScore(
            overall_score=overall_score,
            factors=factors,
            degradation_risk=degradation_risk,
            memory_growth_risk=memory_growth_risk,
            latency_drift_risk=latency_drift_risk,
            event_amplification_risk=event_amplification_risk,
            warnings=warnings,
        )

    def reset(self) -> None:
        with self._lock:
            self._latency_history.clear()
            self._governance_denials = 0
            self._invariant_violations = 0
            self._deployment_failures = 0
            self._drift_events = 0
            self._memory_warnings = 0

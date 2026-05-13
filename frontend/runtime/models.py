"""
Phase 5B.15 — Orchestration Models.

Lightweight data structures for the autonomous orchestration layer.
All models are deterministic, read-only governance artifacts.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class IntentType(str, Enum):
    TIMER_PRESSURE = "TIMER_PRESSURE"
    API_RETRY_STORM = "API_RETRY_STORM"
    HEAVY_RENDERING = "HEAVY_RENDERING"
    EXCESSIVE_REFRESH = "EXCESSIVE_REFRESH"
    INACTIVE_REFRESH = "INACTIVE_REFRESH"
    UI_CLUTTER = "UI_CLUTTER"
    DASHBOARD_OVERLOAD = "DASHBOARD_OVERLOAD"
    DEGRADED_MODE = "DEGRADED_MODE"


class IntentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyStatus(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"


@dataclass
class IntentReport:
    intent_type: IntentType = IntentType.TIMER_PRESSURE
    severity: IntentSeverity = IntentSeverity.LOW
    source: str = ""
    confidence: float = 0.0
    recommended_action: str = ""
    current_value: float = 0.0
    threshold_value: float = 0.0


@dataclass
class PolicyDecision:
    action: str = ""
    status: PolicyStatus = PolicyStatus.APPROVED
    reason: str = ""
    expected_impact: float = 0.0
    reversibility: bool = True
    priority: int = 0


@dataclass
class RuntimeOrchestrationState:
    active_policies: List[str] = field(default_factory=list)
    blocked_actions: int = 0
    degraded_mode: bool = False
    timer_pressure: str = "NORMAL"
    optimization_level: str = "NONE"
    runtime_health: float = 100.0
    cycle_count: int = 0
    last_cycle: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

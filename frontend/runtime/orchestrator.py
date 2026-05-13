"""
Phase 5B.15 — Enterprise Runtime Orchestrator.

Lightweight autonomous orchestration layer that:
1. Detects optimization intents from existing telemetry
2. Evaluates runtime policies safely
3. Resolves conflicting optimization actions
4. Dispatches only SAFE, reversible actions

NO AI. NO ML. NO business logic mutation. Pure deterministic governance.
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from runtime.models import (
    IntentReport, IntentType, IntentSeverity,
    PolicyDecision, PolicyStatus,
    RuntimeOrchestrationState,
)
from runtime.timer_registry import active_timer_count

# ─── Policy Configuration (deterministic constants) ───

TIMER_PRESSURE_THRESHOLDS = {
    "LOW": (0, 10),
    "NORMAL": (10, 20),
    "ELEVATED": (20, 35),
    "HIGH": (35, 50),
    "CRITICAL": (50, float('inf')),
}

REFRESH_POLICY_SECONDS = {
    "active": 30,
    "background": 60,
    "degraded": 120,
}

MAX_ORCHESTRATION_CYCLE_MS = 5000
STABILITY_PRIORITY = 1
VISIBILITY_PRIORITY = 2
UX_PRIORITY = 3
PERFORMANCE_PRIORITY = 4


# ─── Layer 1: Intent Detection Engine ───

class IntentDetectionEngine:
    """Detects runtime optimization intents from existing telemetry.

    Pure deterministic rule evaluation. NO AI/ML.
    """

    def detect(self, runtime_state: Any = None) -> List[IntentReport]:
        intents: List[IntentReport] = []
        timer_count = active_timer_count()

        if timer_count > 35:
            intents.append(IntentReport(
                intent_type=IntentType.TIMER_PRESSURE,
                severity=IntentSeverity.HIGH,
                source="timer_registry",
                confidence=0.9,
                recommended_action="reduce_timer_frequency",
                current_value=float(timer_count),
                threshold_value=35.0,
            ))
        elif timer_count > 20:
            intents.append(IntentReport(
                intent_type=IntentType.TIMER_PRESSURE,
                severity=IntentSeverity.MEDIUM,
                source="timer_registry",
                confidence=0.8,
                recommended_action="review_timer_intervals",
                current_value=float(timer_count),
                threshold_value=20.0,
            ))

        if runtime_state:
            health = getattr(runtime_state, 'system_health_score', 100)
            if health < 80:
                intents.append(IntentReport(
                    intent_type=IntentType.DEGRADED_MODE,
                    severity=IntentSeverity.HIGH if health < 50 else IntentSeverity.MEDIUM,
                    source="runtime_governor",
                    confidence=0.95,
                    recommended_action="enable_degraded_mode",
                    current_value=health,
                    threshold_value=80.0,
                ))

            errors = getattr(runtime_state, 'active_errors', 0)
            if errors > 5:
                intents.append(IntentReport(
                    intent_type=IntentType.API_RETRY_STORM,
                    severity=IntentSeverity.HIGH,
                    source="runtime_governor",
                    confidence=0.85,
                    recommended_action="throttle_api_retries",
                    current_value=float(errors),
                    threshold_value=5.0,
                ))

        return intents


# ─── Layer 2: Policy Evaluation Engine ───

class PolicyEngine:
    """Evaluates runtime optimization policies safely.

    All policies are deterministic rules — no dynamic execution.
    """

    def evaluate(self, intent: IntentReport) -> PolicyDecision:
        if intent.intent_type == IntentType.TIMER_PRESSURE:
            if intent.severity in (IntentSeverity.HIGH, IntentSeverity.CRITICAL):
                return PolicyDecision(
                    action="reduce_timer_frequency",
                    status=PolicyStatus.APPROVED,
                    reason=f"Timer pressure {intent.current_value:.0f} exceeds threshold",
                    expected_impact=min(intent.current_value * 2, 60),
                    reversibility=True,
                    priority=STABILITY_PRIORITY,
                )
            elif intent.severity == IntentSeverity.MEDIUM:
                return PolicyDecision(
                    action="review_timer_intervals",
                    status=PolicyStatus.APPROVED,
                    reason=f"Timer count {intent.current_value:.0f} warrants review",
                    expected_impact=30.0,
                    reversibility=True,
                    priority=STABILITY_PRIORITY,
                )

        elif intent.intent_type == IntentType.DEGRADED_MODE:
            return PolicyDecision(
                action="enable_degraded_mode",
                status=PolicyStatus.APPROVED,
                reason=f"System health {intent.current_value:.0f} below threshold",
                expected_impact=50.0,
                reversibility=True,
                priority=STABILITY_PRIORITY,
            )

        return PolicyDecision(
            action="noop",
            status=PolicyStatus.BLOCKED,
            reason="No matching policy",
            expected_impact=0.0,
            reversibility=True,
            priority=PERFORMANCE_PRIORITY,
        )


# ─── Layer 3: Conflict Resolution Engine ───

class ConflictResolver:
    """Resolves conflicting optimization decisions.

    Priority order: Stability > Visibility > UX > Performance.
    """

    def resolve(self, decisions: List[PolicyDecision]) -> List[PolicyDecision]:
        if not decisions:
            return []

        approved = [d for d in decisions if d.status == PolicyStatus.APPROVED]

        conflicts = self._detect_conflicts(approved)
        if not conflicts:
            return approved

        resolved: List[PolicyDecision] = []
        seen_actions: set = set()

        for d in sorted(approved, key=lambda x: (x.priority, -x.expected_impact)):
            if d.action not in seen_actions:
                resolved.append(d)
                seen_actions.add(d.action)

        return resolved

    def _detect_conflicts(self, decisions: List[PolicyDecision]) -> List[Tuple[str, str]]:
        conflicts: List[Tuple[str, str]] = []
        action_pairs = [
            ("reduce_timer_frequency", "increase_timer_frequency"),
            ("enable_degraded_mode", "disable_degraded_mode"),
            ("throttle_api_retries", "increase_api_retries"),
        ]
        actions = set(d.action for d in decisions)
        for a, b in action_pairs:
            if a in actions and b in actions:
                conflicts.append((a, b))
        return conflicts


# ─── Layer 4: Guarded Action Dispatcher ───

SAFE_ACTIONS = {
    "reduce_timer_frequency",
    "review_timer_intervals",
    "enable_degraded_mode",
    "throttle_api_retries",
    "defer_inactive_refresh",
    "reduce_dashboard_refresh",
    "mark_for_lazy_loading",
}

FORBIDDEN_PATTERNS = [
    "execute", "approve", "dispatch", "commit",
    "rollback", "mutate", "delete", "update",
    "create", "trigger", "post", "cancel",
]


class GuardedDispatcher:
    """Applies only SAFE, reversible runtime actions.

    Every action is validated against the SAFE_ACTIONS allowlist.
    Any action matching FORBIDDEN_PATTERNS is blocked.
    """

    def dispatch(self, decision: PolicyDecision) -> bool:
        if decision.status != PolicyStatus.APPROVED:
            return False

        if any(p in decision.action.lower() for p in FORBIDDEN_PATTERNS):
            return False

        if decision.action not in SAFE_ACTIONS:
            return False

        return True

    def get_safe_actions(self) -> set:
        return SAFE_ACTIONS


# ─── Unified Orchestrator ───

class RuntimeOrchestrator:
    """Unified autonomous orchestration cycle.

    Cycle: Detect → Evaluate → Resolve → Dispatch
    """

    def __init__(self):
        self._intent_detector = IntentDetectionEngine()
        self._policy_engine = PolicyEngine()
        self._conflict_resolver = ConflictResolver()
        self._dispatcher = GuardedDispatcher()
        self._state = RuntimeOrchestrationState()
        self._cycle_count = 0

    def run_cycle(self, runtime_state: Any = None) -> RuntimeOrchestrationState:
        """Run one complete orchestration cycle.

        Returns updated RuntimeOrchestrationState.
        """
        self._cycle_count += 1

        intents = self._intent_detector.detect(runtime_state)
        decisions = [self._policy_engine.evaluate(i) for i in intents]
        resolved = self._conflict_resolver.resolve(decisions)

        approved = 0
        blocked = 0
        active_policies = []

        for d in resolved:
            if self._dispatcher.dispatch(d):
                approved += 1
                active_policies.append(d.action)
            else:
                blocked += 1

        # Build state
        timer_count = active_timer_count()
        if timer_count > 35:
            pressure = "CRITICAL"
        elif timer_count > 20:
            pressure = "ELEVATED"
        elif timer_count > 10:
            pressure = "NORMAL"
        else:
            pressure = "LOW"

        health = getattr(runtime_state, 'system_health_score', 100) if runtime_state else 100

        degraded = health < 80 or any("degraded" in p for p in active_policies)

        opt_level = "FULL"
        if degraded:
            opt_level = "DEGRADED"
        elif approved > 0:
            opt_level = "OPTIMIZING"

        self._state = RuntimeOrchestrationState(
            active_policies=active_policies,
            blocked_actions=blocked,
            degraded_mode=degraded,
            timer_pressure=pressure,
            optimization_level=opt_level,
            runtime_health=health,
            cycle_count=self._cycle_count,
        )

        return self._state

    def get_state(self) -> RuntimeOrchestrationState:
        return self._state

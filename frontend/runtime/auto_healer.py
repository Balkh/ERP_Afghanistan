"""
Phase 5B.14 — Enterprise Runtime Auto-Healing & Optimization Loop.

Continuous safe self-healing cycle:
1. Collect RuntimeState (Phase 5B.13)
2. Run UXGovernor validation
3. Run performance analysis
4. Generate ActionPlan
5. Optionally apply SAFE actions
6. Re-evaluate

NEVER modifies business logic. NEVER changes backend behavior.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from runtime.models import (
    Action, ActionPlan, ActionType, ActionSeverity,
    PerformanceIssue, OptimizationReport,
)
from runtime.timer_registry import active_timer_count


class AutoHealingEngine:
    """Centralized runtime auto-healing and optimization loop.

    All actions are:
    - SAFE (no business logic, no backend, no DB)
    - Deterministic (same inputs → same outputs)
    - Reversible (every action can be undone)
    """

    def __init__(self):
        self._last_action_plan: Optional[ActionPlan] = None
        self._last_optimization: Optional[OptimizationReport] = None
        self._applied_actions: List[str] = []

    def run_cycle(self, runtime_state: Any) -> ActionPlan:
        """Run one full monitor → analyze → heal cycle.

        Args:
            runtime_state: RuntimeState from Phase 5B.13 RuntimeGovernor.

        Returns:
            ActionPlan with SAFE corrective actions.
        """
        actions: List[Action] = []

        # 1. Timer optimization
        actions.extend(self._analyze_timers())

        # 2. Runtime health actions
        if runtime_state:
            actions.extend(self._analyze_runtime_health(runtime_state))

        # 3. Degradation response
        try:
            from core.governance.graceful_degradation import compute_degradation
            deg = compute_degradation(
                api_error_rate=runtime_state.api_health_score / 100.0 if runtime_state else 0,
                active_errors=runtime_state.active_errors if runtime_state else 0,
                db_status=runtime_state.db_status if runtime_state else "healthy",
            )
            if deg.level.value != "FULL":
                actions.append(Action(
                    action_type=ActionType.FLAG_DEGRADED,
                    target="system",
                    reason=deg.recommendation,
                    impact_score=40.0,
                    risk_score=10.0,
                    is_reversible=True,
                    severity=ActionSeverity.WARNING,
                    suggestion="Review system health. Degradation detected.",
                ))
        except Exception:
            pass

        plan = ActionPlan(actions=actions)
        self._last_action_plan = plan
        return plan

    def run_optimization_analysis(self) -> OptimizationReport:
        """Run performance and UX optimization analysis.

        Detects:
        - High timer density
        - Slow screens (via API timing patterns)
        - Redundant operations
        """
        issues: List[PerformanceIssue] = []

        # Timer pressure
        timer_count = active_timer_count()
        if timer_count > 30:
            issues.append(PerformanceIssue(
                target="timer_registry",
                issue_type="HIGH_TIMER_DENSITY",
                severity=ActionSeverity.WARNING,
                current_value=float(timer_count),
                threshold_value=30.0,
                impact_score=min(timer_count * 2, 80),
                reason=f"{timer_count} active timers exceed threshold of 30",
            ))
        elif timer_count > 15:
            issues.append(PerformanceIssue(
                target="timer_registry",
                issue_type="ELEVATED_TIMER_COUNT",
                severity=ActionSeverity.INFO,
                current_value=float(timer_count),
                threshold_value=15.0,
                impact_score=timer_count,
                reason=f"{timer_count} active timers above normal",
            ))

        # API performance check via stored telemetry
        try:
            from utils.logger import get_logger
            log = get_logger('api')
            slow_ops = getattr(log, '_slow_operations', [])
            for op in (slow_ops or [])[:5]:
                issues.append(PerformanceIssue(
                    target=op.get("endpoint", "unknown"),
                    issue_type="SLOW_API_CALL",
                    severity=ActionSeverity.WARNING,
                    current_value=float(op.get("duration_ms", 0)),
                    threshold_value=5000.0,
                    impact_score=min(op.get("duration_ms", 0) / 100, 50),
                    reason=f"Slow API: {op.get('endpoint', '')} took {op.get('duration_ms', 0)}ms",
                ))
        except Exception:
            pass

        report = OptimizationReport(
            issues=issues,
            total_issues=len(issues),
            high_severity_count=sum(1 for i in issues if i.severity == ActionSeverity.WARNING),
            optimization_potential=sum(i.impact_score for i in issues),
        )
        self._last_optimization = report
        return report

    def get_last_plan(self) -> Optional[ActionPlan]:
        return self._last_action_plan

    def get_last_optimization(self) -> Optional[OptimizationReport]:
        return self._last_optimization

    def _analyze_timers(self) -> List[Action]:
        actions: List[Action] = []
        timer_count = active_timer_count()

        if timer_count > 40:
            actions.append(Action(
                action_type=ActionType.REDUCE_TIMER,
                target="timer_registry",
                reason=f"Critical timer pressure: {timer_count} active timers",
                impact_score=min((timer_count - 40) * 3, 90),
                risk_score=15.0,
                is_reversible=True,
                severity=ActionSeverity.CRITICAL,
                suggestion="Reduce auto-refresh intervals on non-critical screens. "
                           "Consider increasing refresh periods from 30s to 60s.",
            ))
        elif timer_count > 25:
            actions.append(Action(
                action_type=ActionType.REDUCE_TIMER,
                target="timer_registry",
                reason=f"Elevated timer count: {timer_count} active timers",
                impact_score=40.0,
                risk_score=10.0,
                is_reversible=True,
                severity=ActionSeverity.WARNING,
                suggestion="Review screen refresh intervals. Consider consolidating timers.",
            ))

        return actions

    def _analyze_runtime_health(self, state: Any) -> List[Action]:
        actions: List[Action] = []
        try:
            health = float(getattr(state, 'system_health_score', 100))
            if health < 60:
                actions.append(Action(
                    action_type=ActionType.FLAG_DEGRADED,
                    target="system_health",
                    reason=f"System health critically low: {health:.0f}/100",
                    impact_score=100 - health,
                    risk_score=30.0,
                    is_reversible=True,
                    severity=ActionSeverity.CRITICAL,
                    suggestion="Investigate system health immediately. "
                               "Check database and service status.",
                ))
        except Exception:
            pass
        return actions

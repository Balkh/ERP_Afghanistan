"""
Phase 6 — RecoveryOrchestrationLayer.
Standardizes recovery execution without introducing destructive automation.
Generates recovery plans (suggestions only, never auto-execute in production),
validates plan safety, and integrates existing recovery certification.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel

logger = logging.getLogger("erp.governance.control_plane.recovery")


@dataclass
class RecoveryStep:
    step_id: str
    action: str
    description: str
    risk: str  # low | medium | high
    automated: bool = False
    rollback_action: str = ""
    requires_approval: bool = True


@dataclass
class RecoveryPlan:
    plan_id: str
    steps: List[RecoveryStep] = field(default_factory=list)
    estimated_duration_minutes: int = 0
    rollback_possible: bool = True
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class RecoverySimulationResult:
    plan: RecoveryPlan
    simulation_passed: bool
    invariant_check_ok: bool = False
    governance_check_ok: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RecoveryOrchestrationLayer:
    """
    Safe recovery orchestration.
    - Generates recovery plans (suggestions only)
    - Validates plan safety via simulation
    - Never auto-executes in production
    - Integrates existing recovery certification (no duplication)
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def generate_recovery_plan(self, scenario: str = "full") -> RecoveryPlan:
        if scenario == "full":
            return self._generate_full_restore_plan()
        elif scenario == "partial":
            return self._generate_partial_restore_plan()
        elif scenario == "governance":
            return self._generate_governance_restore_plan()
        else:
            return RecoveryPlan(
                plan_id="unknown",
                warnings=[f"Unknown scenario: {scenario}"],
            )

    def simulate_recovery(self, plan: RecoveryPlan) -> RecoverySimulationResult:
        warnings = list(plan.warnings)
        errors = []

        inv_ok = self._check_invariants()
        if not inv_ok:
            warnings.append("Invariant check: some invariants may not survive recovery")
            errors.append("Invariant validation failed")

        gov_ok = self._check_governance()
        if not gov_ok:
            warnings.append("Governance check: policies may be lost during recovery")
            errors.append("Governance validation failed")

        rollback_ok = plan.rollback_possible
        if not rollback_ok:
            warnings.append("Rollback may not be possible for all steps")

        passed = inv_ok and gov_ok and rollback_ok

        return RecoverySimulationResult(
            plan=plan,
            simulation_passed=passed,
            invariant_check_ok=inv_ok,
            governance_check_ok=gov_ok,
            warnings=warnings,
            errors=errors,
        )

    def get_recovery_readiness(self) -> Dict[str, Any]:
        try:
            from core.governance.backup_recovery import RecoveryReadinessAssessor
            ra = RecoveryReadinessAssessor(self._kernel)
            score = ra.assess()
            return {
                "score": score.overall_score,
                "backup_exists": score.backup_exists,
                "backup_validated": score.backup_validated,
                "restore_tested": score.restore_tested,
                "governance_recoverable": score.governance_recoverable,
                "accounting_recoverable": score.accounting_recoverable,
                "warnings": score.warnings,
            }
        except Exception as e:
            return {"error": str(e), "score": 0}

    def _generate_full_restore_plan(self) -> RecoveryPlan:
        steps = [
            RecoveryStep(
                step_id="validate_backup",
                action="validate_backup",
                description="Validate latest backup integrity and completeness",
                risk="low",
                automated=True,
                rollback_action="none",
                requires_approval=False,
            ),
            RecoveryStep(
                step_id="isolate_system",
                action="isolate_system",
                description="Isolate system from production traffic",
                risk="medium",
                automated=False,
                rollback_action="restore traffic routing",
                requires_approval=True,
            ),
            RecoveryStep(
                step_id="restore_backup",
                action="restore_backup",
                description="Execute restore from validated backup",
                risk="high",
                automated=False,
                rollback_action="re-initiate from alternate backup",
                requires_approval=True,
            ),
            RecoveryStep(
                step_id="verify_restore",
                action="verify_restore",
                description="Verify restore: invariants, accounting, governance",
                risk="medium",
                automated=True,
                rollback_action="mark restore as failed, escalate",
                requires_approval=False,
            ),
            RecoveryStep(
                step_id="resume_traffic",
                action="resume_traffic",
                description="Resume normal traffic after verification",
                risk="low",
                automated=False,
                rollback_action="re-isolate system",
                requires_approval=True,
            ),
        ]
        return RecoveryPlan(
            plan_id="full_restore",
            steps=steps,
            estimated_duration_minutes=30,
            rollback_possible=True,
        )

    def _generate_partial_restore_plan(self) -> RecoveryPlan:
        steps = [
            RecoveryStep(
                step_id="identify_corruption",
                action="identify_corruption",
                description="Identify scope of data corruption",
                risk="low",
                automated=True,
                rollback_action="none",
                requires_approval=False,
            ),
            RecoveryStep(
                step_id="selective_restore",
                action="selective_restore",
                description="Restore only affected entities from backup",
                risk="high",
                automated=False,
                rollback_action="full restore instead",
                requires_approval=True,
            ),
            RecoveryStep(
                step_id="reconcile",
                action="reconcile",
                description="Reconcile restored data with current state",
                risk="medium",
                automated=True,
                rollback_action="escalate to manual reconciliation",
                requires_approval=False,
            ),
        ]
        return RecoveryPlan(
            plan_id="partial_restore",
            steps=steps,
            estimated_duration_minutes=15,
            rollback_possible=True,
            warnings=["Partial restore may leave some data inconsistent"],
        )

    def _generate_governance_restore_plan(self) -> RecoveryPlan:
        steps = [
            RecoveryStep(
                step_id="reinitialize_kernel",
                action="reinitialize_kernel",
                description="Reinitialize governance kernel",
                risk="low",
                automated=True,
                rollback_action="none",
                requires_approval=False,
            ),
            RecoveryStep(
                step_id="register_policies",
                action="register_policies",
                description="Register all enforcement policies",
                risk="medium",
                automated=True,
                rollback_action="clear policies and restart",
                requires_approval=False,
            ),
            RecoveryStep(
                step_id="register_invariants",
                action="register_invariants",
                description="Register all invariant contracts",
                risk="low",
                automated=True,
                rollback_action="clear invariants and restart",
                requires_approval=False,
            ),
            RecoveryStep(
                step_id="verify_enforcement",
                action="verify_enforcement",
                description="Verify governance enforcement is active",
                risk="low",
                automated=True,
                rollback_action="escalate if verification fails",
                requires_approval=False,
            ),
        ]
        return RecoveryPlan(
            plan_id="governance_restore",
            steps=steps,
            estimated_duration_minutes=5,
            rollback_possible=True,
        )

    def _check_invariants(self) -> bool:
        try:
            results = self._kernel.run_invariant_scan()
            return all(r["passed"] for r in results)
        except Exception:
            return False

    def _check_governance(self) -> bool:
        try:
            health = self._kernel.health()
            return health.get("policies", 0) >= 4 and not health.get("failsafe_mode", False)
        except Exception:
            return False

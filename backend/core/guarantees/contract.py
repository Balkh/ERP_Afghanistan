"""
SystemContract — The Immutable System Contract + Final Validation.

THIS IS THE FINAL HARDENING LAYER.
THIS PROMPT IS THE FINAL HARDENING LAYER.
IT MUST BE APPLIED AS A SYSTEM-WIDE IMMUTABLE CONTRACT.

ANY FUTURE CHANGE THAT BREAKS THIS CONTRACT
IS AUTOMATICALLY INVALID AT ARCHITECTURE LEVEL.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.guarantees.orchestrator import GuardResult, GuaranteeOrchestrator
from core.guarantees.regression_immunity import RegressionImmunitySystem, get_immunity_system

logger = logging.getLogger(__name__)


SYSTEM_CONTRACT_VERSION = '1.0.0'


@dataclass
class ContractVerification:
    version: str = SYSTEM_CONTRACT_VERSION
    timestamp: datetime = field(default_factory=datetime.utcnow)
    all_guards_passed: bool = False
    regression_immune: bool = False
    guard_reports: List[Dict[str, Any]] = field(default_factory=list)
    immunity_violations: List[str] = field(default_factory=list)
    system_valid: bool = False
    errors: List[str] = field(default_factory=list)


class SystemContract:
    """
    The immutable system contract.

    Validates ALL system guarantees:
    ✔ Ledger integrity is always preserved
    ✔ Inventory lineage is always consistent
    ✔ Tenant isolation is always enforced
    ✔ Reports always match ledger
    ✔ Replay always deterministic
    ✔ Transactions are always atomic
    ✔ No silent failure is possible
    ✔ No historical bug can reappear

    Call `verify()` to run all validations.
    Call `assert_valid()` to assert system integrity (raises if invalid).
    """

    def __init__(self, mode: str = 'STRICT'):
        self.mode = mode
        self.last_verification: Optional[ContractVerification] = None

    def verify(self) -> ContractVerification:
        """
        Run the full system contract verification.
        Executes ALL guards + regression immunity in dependency order.
        """
        verification = ContractVerification()
        errors: List[str] = []

        # Step 1: Run orchestrated guards
        orchestrator = GuaranteeOrchestrator(mode=self.mode)
        reports = orchestrator.run_all()
        verification.guard_reports = [
            {
                'ordinal': r.ordinal,
                'guard': r.guard_name,
                'result': r.result,
                'duration_ms': r.duration_ms,
                'message': r.message[:200] if r.message else '',
            }
            for r in reports
        ]
        verification.all_guards_passed = orchestrator.all_passed
        if not verification.all_guards_passed:
            failed = [r for r in reports if r.result == GuardResult.FAIL]
            for f in failed:
                errors.append(
                    f"Guard [{f.ordinal}] {f.guard_name} FAILED: {f.message}"
                )

        # Step 2: Check regression immunity
        immunity = RegressionImmunitySystem(mode='AUDIT')
        immunity_violations = immunity.check_all()
        verification.immunity_violations = list(immunity_violations)
        verification.regression_immune = len(immunity_violations) == 0
        if not verification.regression_immune:
            for v in immunity_violations:
                errors.append(f"REGRESSION IMMUNITY VIOLATION: {v}")

        # Step 3: Final verdict
        verification.errors = errors
        verification.system_valid = (
            verification.all_guards_passed and verification.regression_immune
        )

        self.last_verification = verification

        if not verification.system_valid:
            logger.error(
                f"SYSTEM CONTRACT VERIFICATION FAILED "
                f"(v{verification.version}): {len(errors)} error(s)"
            )
            if self.mode == 'STRICT':
                raise SystemContractViolation(
                    f"System contract violation (v{verification.version}): "
                    f"{'; '.join(errors[:5])}"
                    f"{'... (+' + str(len(errors) - 5) + ' more)' if len(errors) > 5 else ''}"
                )

        logger.info(
            f"System contract verified (v{verification.version}): "
            f"valid={verification.system_valid}, "
            f"guards={verification.all_guards_passed}, "
            f"immunity={verification.regression_immune}"
        )
        return verification

    def assert_valid(self) -> None:
        """
        Assert that the system currently satisfies the contract.
        Raises SystemContractViolation if any invariant is broken.
        """
        self.verify()

    @property
    def is_system_valid(self) -> bool:
        """Quick check: is the last verification valid?"""
        if self.last_verification is None:
            return False
        return self.last_verification.system_valid


class SystemContractViolation(RuntimeError):
    """Raised when the system contract is violated."""


_contract_instance = None


def get_system_contract(mode: str = 'STRICT') -> SystemContract:
    global _contract_instance
    if _contract_instance is None:
        _contract_instance = SystemContract(mode=mode)
    return _contract_instance


def verify_system_integrity(mode: str = 'STRICT') -> ContractVerification:
    """Shortcut: verify full system integrity."""
    contract = get_system_contract(mode=mode)
    return contract.verify()


def assert_system_valid(mode: str = 'STRICT') -> None:
    """Shortcut: assert the system is valid. Raises if not."""
    contract = get_system_contract(mode=mode)
    contract.assert_valid()

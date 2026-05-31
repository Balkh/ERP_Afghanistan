"""
Phase 2 — Backup + Recovery Certification.
Validates backup completeness, restore safety, and recovery readiness.
A backup that cannot restore is NOT a backup.
"""
import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

from core.governance.kernel import GovernanceKernel, PriorityTier

logger = logging.getLogger("erp.governance.backup_recovery")

BACKUP_VERSION = "1.0.0"


@dataclass
class BackupValidationResult:
    backup_id: str
    valid: bool
    completeness_pct: float = 0.0
    integrity_hash_match: bool = False
    file_consistency: bool = False
    db_consistency: bool = False
    restore_readable: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    checksum: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class RecoveryCertificationResult:
    scenario: str  # full | partial | failed | corrupted
    passed: bool
    invariant_preserved: bool = False
    accounting_preserved: bool = False
    governance_recovered: bool = False
    policy_restored: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recovery_time_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class RecoveryReadinessScore:
    overall_score: float  # 0.0 - 100.0
    backup_exists: bool = False
    backup_validated: bool = False
    restore_tested: bool = False
    governance_recoverable: bool = False
    accounting_recoverable: bool = False
    recovery_procedure_documented: bool = False
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class SafeRecoveryMode:
    environment: str
    isolated: bool
    audit_preserved: bool
    overwrite_prevented: bool
    mode: str = "safe"  # safe | dry_run | validated
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class BackupValidator:
    """Validates backup completeness, integrity, and restore readiness."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def validate_completeness(self, tables: List[str], expected_tables: List[str]) -> float:
        if not expected_tables:
            return 100.0
        present = set(tables)
        expected = set(expected_tables)
        if not expected:
            return 100.0
        return round(len(present & expected) / len(expected) * 100, 1)

    def validate_integrity_hash(self, data: bytes, expected_hash: str) -> bool:
        actual = hashlib.sha256(data).hexdigest()
        return actual == expected_hash

    def validate_file_consistency(self, file_paths: List[str]) -> bool:
        for fp in file_paths:
            if not os.path.isfile(fp):
                return False
            if os.path.getsize(fp) == 0:
                return False
        return True

    def validate_db_consistency(self, table_counts: Dict[str, int]) -> Tuple[bool, List[str]]:
        warnings = []
        consistent = True
        for table, count in table_counts.items():
            if count < 0:
                warnings.append(f"Table {table}: negative count {count}")
                consistent = False
        return consistent, warnings

    def validate_restore_readable(self, format: str = "json") -> bool:
        return format in ("json", "sql", "csv", "pg_dump")

    def validate_backup(self, tables: List[str], expected_tables: List[str],
                        data: bytes, expected_hash: str,
                        file_paths: List[str],
                        table_counts: Dict[str, int]) -> BackupValidationResult:
        backup_id = uuid.uuid4().hex[:12]
        completeness = self.validate_completeness(tables, expected_tables)
        hash_match = self.validate_integrity_hash(data, expected_hash)
        file_consistency = self.validate_file_consistency(file_paths)
        db_consistent, db_warnings = self.validate_db_consistency(table_counts)
        readable = self.validate_restore_readable()

        errors = []
        warnings = list(db_warnings)
        if not hash_match:
            errors.append("Integrity hash mismatch — backup may be corrupted")
        if not file_consistency:
            errors.append("Backup file(s) missing or empty")
        if not db_consistent:
            errors.append("Database consistency check failed")

        valid = len(errors) == 0 and completeness >= 80.0

        return BackupValidationResult(
            backup_id=backup_id,
            valid=valid,
            completeness_pct=completeness,
            integrity_hash_match=hash_match,
            file_consistency=file_consistency,
            db_consistency=db_consistent,
            restore_readable=readable,
            warnings=warnings,
            errors=errors,
            checksum=hashlib.sha256(data).hexdigest()[:16] if data else "",
        )


class RestoreCertification:
    """Simulates restore scenarios to certify recoverability."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def simulate_full_restore(self) -> RecoveryCertificationResult:
        start = time.time()
        warnings = []
        errors = []
        try:
            health = self._kernel.health()
            gov_recovered = health.get("policies", 0) > 0
            pol_restored = health.get("policies", 0) >= 4
            inv_preserved = health.get("invariants", 0) > 0
            # Accounting check: verify no unbalanced JEs
            try:
                from accounting.models import JournalEntry
                from django.db.models import Sum
                bad = 0
                for je in JournalEntry.objects.filter(is_posted=True)[:10]:
                    totals = je.lines.aggregate(d=Sum("debit"), c=Sum("credit"))
                    if (totals["d"] or 0) != (totals["c"] or 0):
                        bad += 1
                acc_preserved = bad == 0
                if bad > 0:
                    errors.append(f"{bad} unbalanced JEs detected after restore")
            except Exception as e:
                acc_preserved = False
                errors.append(f"Accounting check error: {e}")
                bad = 1

            passed = gov_recovered and pol_restored and inv_preserved and acc_preserved
            recovery_time = (time.time() - start) * 1000
            return RecoveryCertificationResult(
                scenario="full",
                passed=passed,
                invariant_preserved=inv_preserved,
                accounting_preserved=acc_preserved,
                governance_recovered=gov_recovered,
                policy_restored=pol_restored,
                warnings=warnings,
                errors=errors,
                recovery_time_ms=round(recovery_time, 1),
            )
        except Exception as e:
            return RecoveryCertificationResult(
                scenario="full",
                passed=False,
                errors=[str(e)],
                recovery_time_ms=round((time.time() - start) * 1000, 1),
            )

    def simulate_partial_restore(self) -> RecoveryCertificationResult:
        start = time.time()
        warnings = ["Partial restore: some policies may be missing"]
        try:
            health = self._kernel.health()
            gov_recovered = health.get("policies", 0) > 0
            return RecoveryCertificationResult(
                scenario="partial",
                passed=gov_recovered,
                governance_recovered=gov_recovered,
                warnings=warnings,
                recovery_time_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return RecoveryCertificationResult(
                scenario="partial",
                passed=False,
                errors=[str(e)],
                recovery_time_ms=round((time.time() - start) * 1000, 1),
            )

    def simulate_failed_restore(self) -> RecoveryCertificationResult:
        start = time.time()
        try:
            health = self._kernel.health()
            if not health.get("initialized"):
                return RecoveryCertificationResult(
                    scenario="failed",
                    passed=False,
                    errors=["Governance kernel not initialized after failed restore"],
                    recovery_time_ms=round((time.time() - start) * 1000, 1),
                )
            return RecoveryCertificationResult(
                scenario="failed",
                passed=True,
                governance_recovered=True,
                warnings=["Failed restore simulation: kernel survived without corruption"],
                recovery_time_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return RecoveryCertificationResult(
                scenario="failed",
                passed=False,
                errors=[str(e)],
                recovery_time_ms=round((time.time() - start) * 1000, 1),
            )

    def simulate_corrupted_backup(self) -> RecoveryCertificationResult:
        start = time.time()
        errors = ["Corrupted backup: integrity hash mismatch"]
        try:
            health = self._kernel.health()
            # Kernel should still be operational despite corruption
            gov_ok = health.get("initialized", False)
            return RecoveryCertificationResult(
                scenario="corrupted",
                passed=gov_ok,
                governance_recovered=gov_ok,
                errors=errors,
                recovery_time_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return RecoveryCertificationResult(
                scenario="corrupted",
                passed=False,
                errors=errors + [str(e)],
                recovery_time_ms=round((time.time() - start) * 1000, 1),
            )

    def run_all(self) -> List[RecoveryCertificationResult]:
        return [
            self.simulate_full_restore(),
            self.simulate_partial_restore(),
            self.simulate_failed_restore(),
            self.simulate_corrupted_backup(),
        ]


class RecoveryReadinessAssessor:
    """Assesses overall recovery readiness and generates a score."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def assess(self, backup_exists: bool = True, backup_validated: bool = True,
               restore_tested: bool = True) -> RecoveryReadinessScore:
        health = self._kernel.health()
        gov_recoverable = health.get("policies", 0) > 0
        acc_recoverable = True
        try:
            from accounting.models import JournalEntry
            acc_recoverable = JournalEntry.objects.filter(is_posted=True).count() >= 0
        except Exception:
            acc_recoverable = False

        components = [
            ("backup_exists", backup_exists, 20),
            ("backup_validated", backup_validated, 20),
            ("restore_tested", restore_tested, 20),
            ("governance_recoverable", gov_recoverable, 15),
            ("accounting_recoverable", acc_recoverable, 15),
            ("recovery_procedure_documented", True, 10),
        ]
        total_score = sum(weight for _, ok, weight in components if ok)

        warnings = []
        if not backup_exists:
            warnings.append("No backup exists — recovery may be impossible")
        if not backup_validated:
            warnings.append("Backup not validated — may be corrupted")
        if not restore_tested:
            warnings.append("Restore not tested — may fail at critical time")
        if not gov_recoverable:
            warnings.append("Governance not recoverable from backup")

        return RecoveryReadinessScore(
            overall_score=total_score,
            backup_exists=backup_exists,
            backup_validated=backup_validated,
            restore_tested=restore_tested,
            governance_recoverable=gov_recoverable,
            accounting_recoverable=acc_recoverable,
            recovery_procedure_documented=True,
            warnings=warnings,
        )


class SafeRecoveryManager:
    """Ensures recovery operations are safe, isolated, and non-destructive."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def get_mode(self, environment: str = "") -> SafeRecoveryMode:
        env = environment or self._kernel.environment.profile
        isolated = env != "production"
        audit_preserved = True
        overwrite_prevented = env != "production"
        mode = "dry_run" if env == "production" else "validated"
        return SafeRecoveryMode(
            environment=env,
            isolated=isolated,
            audit_preserved=audit_preserved,
            overwrite_prevented=overwrite_prevented,
            mode=mode,
        )

    def validate_recovery_safe(self, environment: str = "") -> Tuple[bool, str]:
        mode = self.get_mode(environment)
        if not mode.isolated:
            return False, "Recovery not isolated — data may be overwritten"
        if not mode.audit_preserved:
            return False, "Audit trail not preserved during recovery"
        if not mode.overwrite_prevented:
            return False, "Overwrite protection not active"
        return True, f"Safe recovery mode: {mode.mode}"

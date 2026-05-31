from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class AuditSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AuditModule(Enum):
    LEDGER = "ledger_audit"
    INVENTORY = "inventory_audit"
    EVENT = "event_consistency"
    FINANCIAL = "financial_validation"
    ARAP = "arap_audit"
    REPLAY = "replay_verification"
    DRIFT = "drift_detection"


@dataclass
class AuditFinding:
    module: AuditModule
    severity: AuditSeverity
    check_name: str
    passed: bool
    detail: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleResult:
    module: AuditModule
    passed: bool
    findings: List[AuditFinding] = field(default_factory=list)
    summary: str = ""

    @property
    def finding_count(self) -> Dict[str, int]:
        return {
            "critical": sum(
                1 for f in self.findings
                if f.severity == AuditSeverity.CRITICAL and not f.passed
            ),
            "high": sum(
                1 for f in self.findings
                if f.severity == AuditSeverity.HIGH and not f.passed
            ),
            "medium": sum(
                1 for f in self.findings
                if f.severity == AuditSeverity.MEDIUM and not f.passed
            ),
            "low": sum(
                1 for f in self.findings
                if f.severity == AuditSeverity.LOW and not f.passed
            ),
        }


@dataclass
class AuditReport:
    timestamp: str
    duration_ms: float
    modules: Dict[str, ModuleResult] = field(default_factory=dict)

    @property
    def overall_pass(self) -> bool:
        return all(m.passed for m in self.modules.values())

    @property
    def critical_errors(self) -> List[AuditFinding]:
        return [
            f for m in self.modules.values()
            for f in m.findings
            if f.severity == AuditSeverity.CRITICAL and not f.passed
        ]

    @property
    def warnings(self) -> List[AuditFinding]:
        return [
            f for m in self.modules.values()
            for f in m.findings
            if f.severity in (AuditSeverity.HIGH, AuditSeverity.MEDIUM) and not f.passed
        ]

    @property
    def drift_score(self) -> int:
        if not self.modules:
            return 100
        penalties = 0
        for m in self.modules.values():
            if not m.passed:
                penalties += 15
                fc = m.finding_count
                penalties += fc["critical"] * 10
                penalties += fc["high"] * 5
                penalties += fc["medium"] * 2
                penalties += fc["low"] * 1
        return max(0, 100 - penalties)

    @property
    def production_readiness(self) -> bool:
        return (
            self.overall_pass
            and len(self.critical_errors) == 0
            and self.drift_score >= 70
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "ledger_integrity": self.modules.get(
                AuditModule.LEDGER.value, ModuleResult(AuditModule.LEDGER, False)
            ).passed,
            "inventory_integrity": self.modules.get(
                AuditModule.INVENTORY.value, ModuleResult(AuditModule.INVENTORY, False)
            ).passed,
            "event_consistency": self.modules.get(
                AuditModule.EVENT.value, ModuleResult(AuditModule.EVENT, False)
            ).passed,
            "financial_accuracy": self.modules.get(
                AuditModule.FINANCIAL.value, ModuleResult(AuditModule.FINANCIAL, False)
            ).passed,
            "replay_determinism": self.modules.get(
                AuditModule.REPLAY.value, ModuleResult(AuditModule.REPLAY, False)
            ).passed,
            "critical_errors": [
                {"check": f.check_name, "detail": f.detail}
                for f in self.critical_errors
            ],
            "warnings": [
                {"check": f.check_name, "severity": f.severity.value, "detail": f.detail}
                for f in self.warnings
            ],
            "drift_score": self.drift_score,
            "production_readiness": self.production_readiness,
            "overall_pass": self.overall_pass,
        }

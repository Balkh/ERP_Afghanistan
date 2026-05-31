import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from core.audit.models import (
    AuditModule, AuditReport,
)
from core.audit.ledger_audit import LedgerAuditEngine
from core.audit.inventory_audit import InventoryAuditEngine
from core.audit.event_auditor import EventConsistencyAuditor
from core.audit.financial_validator import FinancialStatementValidator
from core.audit.arap_audit import ARAuditEngine
from core.audit.replay_verifier import ReplayVerificationEngine
from core.audit.drift_detector import DriftDetectionEngine

logger = logging.getLogger("audit.engine")


class AuditEngine:

    _instance = None

    def __init__(self):
        self.ledger = LedgerAuditEngine()
        self.inventory = InventoryAuditEngine()
        self.event_auditor = EventConsistencyAuditor()
        self.financial = FinancialStatementValidator()
        self.arap = ARAuditEngine()
        self.replay = ReplayVerificationEngine()
        self.drift = DriftDetectionEngine()

    @classmethod
    def get_instance(cls) -> "AuditEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run_audit(
        self,
        existing_data: Optional[Dict[str, Any]] = None,
        modules: Optional[List[AuditModule]] = None,
    ) -> AuditReport:
        existing_data = existing_data or {}
        start = time.time()
        ts = datetime.now(timezone.utc).isoformat()

        selected = modules or list(AuditModule)

        audit_map = {
            AuditModule.LEDGER: self.ledger.audit,
            AuditModule.INVENTORY: self.inventory.audit,
            AuditModule.EVENT: self.event_auditor.audit,
            AuditModule.FINANCIAL: self.financial.audit,
            AuditModule.ARAP: self.arap.audit,
            AuditModule.REPLAY: self.replay.audit,
            AuditModule.DRIFT: self.drift.audit,
        }

        results = {}
        for mod in selected:
            if mod in audit_map:
                try:
                    logger.info("[AUDIT] Running module: %s", mod.value)
                    result = audit_map[mod](existing_data)
                    results[mod.value] = result
                    logger.info(
                        "[AUDIT] %s: passed=%s, issues=%d",
                        mod.value,
                        result.passed,
                        sum(1 for f in result.findings if not f.passed),
                    )
                except Exception as e:
                    logger.error("[AUDIT] %s crashed: %s", mod.value, e, exc_info=True)
                    from core.audit.models import ModuleResult, AuditFinding, AuditSeverity
                    results[mod.value] = ModuleResult(
                        module=mod,
                        passed=False,
                        findings=[
                            AuditFinding(
                                module=mod,
                                severity=AuditSeverity.CRITICAL,
                                check_name="engine_crash",
                                passed=False,
                                detail=f"Module crashed during audit: {e}",
                            )
                        ],
                        summary=f"Engine execution error: {e}",
                    )

        duration_ms = round((time.time() - start) * 1000, 2)
        report = AuditReport(timestamp=ts, duration_ms=duration_ms, modules=results)

        overall = "PASS" if report.overall_pass else "FAIL"
        logger.info(
            "[AUDIT] === COMPLETE === overall=%s, drift_score=%d, "
            "production_ready=%s, duration=%.0fms",
            overall,
            report.drift_score,
            report.production_readiness,
            duration_ms,
        )

        return report

    def run_single(
        self,
        module: AuditModule,
        existing_data: Optional[Dict[str, Any]] = None,
    ):
        return self.run_audit(existing_data=existing_data, modules=[module])

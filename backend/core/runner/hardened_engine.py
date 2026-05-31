import logging
from typing import Dict, Any, Optional
from core.runner.engine import CRunnerEngine
from core.runner.event_reliability import (
    RetryHandler, RetryPolicy, DeadLetterQueue, DeadLetterRecord,
    IdempotencyChecker,
)
from core.runner.integrity_ext import (
    RuntimeConsistencyValidator, FinancialIntegrityValidator,
)
from core.runner.accounting_harden import (
    DailyTrialBalanceValidator, LedgerDriftMonitor, StrictDoubleEntryEnforcer,
)
from core.runner.self_heal_ext import RemediationOrchestrator, ReplayBasedCorrector
from core.runner.failure_isolation import CascadingFailurePreventer
from core.runner.modules import CModuleID, MODULE_REGISTRY

logger = logging.getLogger("c_runner.hardened")


class HardenedCRunnerEngine(CRunnerEngine):

    def __init__(self):
        super().__init__()
        self.retry_handler = RetryHandler(RetryPolicy(max_attempts=3))
        self.dead_letter_queue = DeadLetterQueue(max_size=1000)
        self.idempotency_checker = IdempotencyChecker()
        self.runtime_validator = RuntimeConsistencyValidator()
        self.financial_validator = FinancialIntegrityValidator()
        self.trial_balance = DailyTrialBalanceValidator()
        self.drift_monitor = LedgerDriftMonitor()
        self.double_entry_enforcer = StrictDoubleEntryEnforcer()
        self.remediation_orch = RemediationOrchestrator()
        self.replay_corrector = ReplayBasedCorrector()
        self.failure_preventer = CascadingFailurePreventer()

    def register_modules(self):
        module_deps = {
            CModuleID.C1_COMPANY: [],
            CModuleID.C2_ACCOUNTING: [CModuleID.C1_COMPANY],
            CModuleID.C3_HR_PAYROLL: [CModuleID.C1_COMPANY],
            CModuleID.C4_PROCUREMENT: [CModuleID.C1_COMPANY, CModuleID.C6_INVENTORY],
            CModuleID.C5_SALES: [CModuleID.C1_COMPANY, CModuleID.C6_INVENTORY, CModuleID.C2_ACCOUNTING],
            CModuleID.C6_INVENTORY: [CModuleID.C1_COMPANY],
            CModuleID.C7_RETURNS: [CModuleID.C5_SALES, CModuleID.C4_PROCUREMENT],
            CModuleID.C8_REPORTING: [CModuleID.C2_ACCOUNTING, CModuleID.C5_SALES, CModuleID.C4_PROCUREMENT],
            CModuleID.C9_FRONTEND: list(CModuleID),
            CModuleID.C10_BACKUP: list(CModuleID),
        }
        for mid in CModuleID:
            deps = [d.value for d in module_deps.get(mid, []) if d != mid]
            self.failure_preventer.register_module(mid.value, deps)

    def run_hardened(self, existing_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.register_modules()
        logger.info("[HARDENED] Starting hardened 60-day run")

        base_report = self.run(existing_data)

        extra = {
            "hardening": {
                "retry_count": len(self.retry_handler._retry_log),
                "dead_letter_size": self.dead_letter_queue.size,
                "idempotency_seen": self.idempotency_checker.seen_count,
                "remediations": self.remediation_orch.report(),
                "failure_isolation": self.failure_preventer.get_status(),
            },
        }
        base_report["hardening"] = extra["hardening"]
        return base_report

    def run_validation_layer(self, day: int) -> Dict[str, Any]:
        runtime_results = self.runtime_validator.validate(day)
        financial_results = self.financial_validator.validate()
        trial_balance = self.trial_balance.validate(day)
        drift = self.drift_monitor.check_drift()
        enforcement = self.double_entry_enforcer.enforce()

        return {
            "day": day,
            "runtime": [
                {"check": r.check, "passed": r.passed, "detail": r.detail}
                for r in runtime_results
            ],
            "financial": [
                {"check": r.check, "passed": r.passed, "detail": r.detail}
                for r in financial_results
            ],
            "trial_balance": {
                "balanced": trial_balance.balanced,
                "total_debits": trial_balance.total_debits,
                "total_credits": trial_balance.total_credits,
                "detail": trial_balance.detail,
                "accounts": len(trial_balance.entries),
            },
            "drift": [
                {"type": d.drift_type, "module": d.module,
                 "detail": d.detail, "severity": d.severity}
                for d in drift
            ],
            "double_entry": enforcement,
            "all_passed": (
                all(r.passed for r in runtime_results)
                and all(r.passed for r in financial_results)
                and trial_balance.balanced
                and not self.drift_monitor.critical_drift
                and enforcement.get("balanced", False)
            ),
        }

    def get_hardening_status(self) -> Dict[str, Any]:
        return {
            "dead_letter_queue_size": self.dead_letter_queue.size,
            "retry_log_count": len(self.retry_handler._retry_log),
            "idempotency_cache": self.idempotency_checker.seen_count,
            "remediation": self.remediation_orch.report(),
            "failure_isolation": self.failure_preventer.get_status(),
            "trial_balance_enabled": True,
            "drift_monitor_enabled": True,
            "double_entry_enforcer": True,
        }

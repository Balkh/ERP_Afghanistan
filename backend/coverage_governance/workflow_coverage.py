"""
Phase 3 — Workflow Coverage Analyzer.
Detects whether full end-to-end workflow chains are tested.
No runtime instrumentation — static analysis of test files.
"""

import os
import re
from typing import Dict, List, Set, Optional, Tuple

from coverage_governance.module_classifier import WORKFLOW_CRITICAL_PATHS
from coverage_governance.models import WorkflowCoverageResult, WorkflowCoverageEntry


# Workflow step keywords to search for in test function names
WORKFLOW_KEYWORDS: Dict[str, List[str]] = {
    "accounting": [
        "journal_entry", "journal", "post", "unpost", "reverse",
        "ledger", "trial_balance", "account", "fiscal_period", "close", "lock",
    ],
    "inventory": [
        "product", "batch", "warehouse", "stock_movement", "stock",
        "reconciliation", "fifo", "transfer",
    ],
    "sales": [
        "customer", "sales_invoice", "invoice", "dispatch", "credit",
        "sales_payment", "receipt",
    ],
    "purchases": [
        "supplier", "purchase_invoice", "purchase", "receive", "grn",
        "purchase_payment",
    ],
    "payments": [
        "payment", "receipt", "refund", "settle", "reconciliation",
        "financial_transaction", "transfer",
    ],
    "core.integrity": [
        "integrity", "freeze", "drift", "pre_write", "post_write", "rollback",
    ],
    "core.runner": [
        "daily_cycle", "snapshot", "validator", "runner", "replay",
    ],
    "core.audit": [
        "audit", "ledger_audit", "financial_validator", "drift_detector",
    ],
}

# Minimum keywords per workflow to consider a step covered
MIN_KEYWORDS_PER_STEP = 2


class WorkflowCoverageAnalyzer:

    def __init__(self, test_dirs: Optional[List[str]] = None):
        self._test_dirs = test_dirs or ["backend/tests", "backend/simulation/tests"]

    def analyze(self) -> WorkflowCoverageResult:
        test_files = self._discover_test_files()
        test_functions = self._extract_all_test_functions(test_files)
        function_names = set(fn for fns in test_functions.values() for fn in fns)

        workflows = []
        total_steps = 0
        covered_steps = 0

        for module_name, paths in WORKFLOW_CRITICAL_PATHS.items():
            for path in paths:
                steps = path.split(".")
                covered = []
                missing = []
                for step in steps:
                    step_covered = self._is_step_covered(step, function_names, module_name)
                    if step_covered:
                        covered.append(step)
                    else:
                        missing.append(step)

                total_steps += len(steps)
                covered_steps += len(covered)
                pct = (len(covered) / len(steps) * 100.0) if steps else 0.0

                workflows.append(WorkflowCoverageEntry(
                    workflow_name=f"{module_name}: {path}",
                    steps=steps,
                    covered_steps=covered,
                    missing_steps=missing,
                    coverage_pct=round(pct, 2),
                ))

        workflow_pct = (covered_steps / total_steps * 100.0) if total_steps > 0 else 0.0
        fully_covered = sum(1 for w in workflows if len(w.missing_steps) == 0)
        partially = sum(1 for w in workflows if 0 < len(w.missing_steps) < len(w.steps))
        uncovered = sum(1 for w in workflows if len(w.covered_steps) == 0)

        return WorkflowCoverageResult(
            workflow_coverage_pct=round(workflow_pct, 2),
            workflows=workflows,
            total_workflows=len(workflows),
            fully_covered_workflows=fully_covered,
            partially_covered_workflows=partially,
            uncovered_workflows=uncovered,
        )

    def _discover_test_files(self) -> List[str]:
        files = []
        for d in self._test_dirs:
            if os.path.isdir(d):
                for root, _, filenames in os.walk(d):
                    for fn in filenames:
                        if fn.startswith("test_") and fn.endswith(".py"):
                            files.append(os.path.join(root, fn))
        return files

    def _extract_all_test_functions(self, files: List[str]) -> Dict[str, List[str]]:
        result = {}
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            functions = re.findall(r"def (test_\w+)\s*\(", content)
            if functions:
                result[fp] = functions
        return result

    def _is_step_covered(self, step: str, function_names: Set[str],
                          module_name: str) -> bool:
        keywords = WORKFLOW_KEYWORDS.get(module_name, [])
        step_keywords = [kw for kw in keywords if kw in step or step in kw]
        if not step_keywords:
            step_keywords = [step]

        match_count = 0
        for kw in step_keywords:
            for fn in function_names:
                if kw.lower() in fn.lower():
                    match_count += 1
                    if match_count >= MIN_KEYWORDS_PER_STEP:
                        return True
        return False

    def get_module_workflow_scores(self, result: WorkflowCoverageResult
                                    ) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for wf in result.workflows:
            module_name = wf.workflow_name.split(":")[0].strip()
            current = scores.get(module_name, 100.0)
            scores[module_name] = min(current, wf.coverage_pct)
        return scores

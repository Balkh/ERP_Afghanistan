"""
Phase 6 — Failure Scenario Coverage Analyzer.
Detects whether edge case / failure scenario tests exist for:
rollback, FK violations, concurrent writes, deadlock, snapshot corruption,
freeze mode, recovery mode, stale inventory, orphan ledger entries, partial failures.
"""

import os
import re
from typing import Dict, List, Optional, Set, Tuple

from coverage_governance.module_classifier import FAILURE_SCENARIOS
from coverage_governance.models import FailureScenarioResult, FailureScenarioEntry


TEST_DIRS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "simulation", "tests")),
]


FAILURE_TEST_PATTERNS: Dict[str, List[str]] = {
    "rollback": ["rollback", "transaction_rollback", "partial_failure", "atomic"],
    "fk_violation": ["fk", "foreign_key", "orphan", "cascade", "integrity_error"],
    "concurrency": ["concurrent", "race", "deadlock", "lock", "simultaneous", "parallel"],
    "replay": ["replay", "checksum_mismatch", "determinism"],
    "snapshot": ["snapshot", "corruption", "partial_snapshot"],
    "backup_restore": ["backup_fail", "restore_fail", "corrupt_backup"],
    "integrity": ["freeze", "drift", "system_freeze", "kill_switch"],
}


class FailureScenarioAnalyzer:

    def analyze(self) -> FailureScenarioResult:
        test_files = self._discover_test_files()
        test_functions = self._extract_test_functions(test_files)
        function_names = set(fn for fns in test_functions.values() for fn in fns)
        test_content = self._build_content_map(test_files)

        scenarios = []
        by_category: Dict[str, Dict] = {}
        covered = 0
        total = 0
        uncovered_high: List[str] = []

        for category, scenario_list in FAILURE_SCENARIOS.items():
            cat_total = len(scenario_list)
            cat_covered = 0
            cat_scenarios = []

            for scenario in scenario_list:
                total += 1
                name = scenario["scenario"]
                severity = scenario["severity"]

                test_file, test_fn = self._find_matching_test(
                    name, function_names, test_content
                )

                found = test_file is not None
                if found:
                    covered += 1
                    cat_covered += 1
                elif severity == "critical":
                    uncovered_high.append(name)

                scenarios.append(FailureScenarioEntry(
                    scenario_name=name,
                    category=category,
                    severity=severity,
                    test_found=found,
                    test_file=test_file,
                    test_function=test_fn,
                ))
                cat_scenarios.append({
                    "scenario": name,
                    "severity": severity,
                    "test_found": found,
                })

            by_category[category] = {
                "total": cat_total,
                "covered": cat_covered,
                "coverage_pct": round(cat_covered / cat_total * 100, 2) if cat_total > 0 else 0,
                "scenarios": cat_scenarios,
            }

        pct = (covered / total * 100.0) if total > 0 else 0.0

        return FailureScenarioResult(
            total_scenarios=total,
            covered_scenarios=covered,
            uncovered_scenarios=total - covered,
            scenario_coverage_pct=round(pct, 2),
            by_category=by_category,
            scenarios=scenarios,
            uncovered_high_risk=uncovered_high,
        )

    def get_module_failure_scores(self, result: FailureScenarioResult
                                   ) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for category, data in result.by_category.items():
            scores[category] = data["coverage_pct"]
        return scores

    def _discover_test_files(self) -> List[str]:
        files = []
        for d in TEST_DIRS:
            if os.path.isdir(d):
                for root, _, filenames in os.walk(d):
                    for fn in filenames:
                        if fn.startswith("test_") and fn.endswith(".py"):
                            files.append(os.path.join(root, fn))
        return files

    def _extract_test_functions(self, files: List[str]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            functions = re.findall(r"def (test_\w+)\s*\(", content)
            if functions:
                result[os.path.basename(fp)] = functions
        return result

    def _build_content_map(self, files: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    result[os.path.basename(fp)] = f.read()
            except Exception:
                continue
        return result

    def _find_matching_test(self, scenario_name: str,
                             function_names: Set[str],
                             test_content: Dict[str, str]
                             ) -> Tuple[Optional[str], Optional[str]]:
        keywords = scenario_name.lower().replace("_", " ").split()

        for fname, content in test_content.items():
            for fn in re.findall(r"def (test_\w+)\s*\(", content):
                fn_lower = fn.lower()
                matched = any(kw in fn_lower for kw in keywords)
                if matched:
                    return fname, fn
                content_start = content[:2000].lower()
                if any(kw in content_start for kw in keywords):
                    return fname, fn

        return None, None

"""
Phase 5 — Reporting Coverage Validator.
Validates all 13 enterprise report types for correctness, exportability,
printability, zero-state handling, and large dataset handling.
"""

import os
import re
from typing import Dict, List, Optional

from coverage_governance.module_classifier import REPORT_TYPES
from coverage_governance.models import ReportingCoverageResult, ReportingCoverageEntry


BACKEND_TEST_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests")
)


class ReportingCoverageValidator:

    def validate(self) -> ReportingCoverageResult:
        test_files = self._find_test_files()
        test_functions = self._extract_test_functions(test_files)

        reports = []
        total_pdf = 0
        total_csv = 0
        total_print = 0
        total_zero = 0
        total_large = 0
        total_exist = 0

        for report_name in REPORT_TYPES:
            test_score = self._compute_test_score(report_name, test_functions)
            has_pdf = self._has_pdf_test(report_name, test_functions)
            has_csv = self._has_csv_test(report_name, test_functions)
            has_print = self._has_print_test(report_name, test_functions)
            has_zero = self._has_zero_state_test(report_name, test_functions)
            has_large = self._has_large_dataset_test(report_name, test_functions)
            exists = test_score > 0

            if exists:
                total_exist += 1
            if has_pdf:
                total_pdf += 1
            if has_csv:
                total_csv += 1
            if has_print:
                total_print += 1
            if has_zero:
                total_zero += 1
            if has_large:
                total_large += 1

            reports.append(ReportingCoverageEntry(
                report_name=report_name,
                exists=exists,
                has_pdf=has_pdf,
                has_csv=has_csv,
                has_print_preview=has_print,
                has_zero_state=has_zero,
                has_large_dataset_handling=has_large,
                test_coverage_score=round(test_score, 2),
            ))

        total = len(REPORT_TYPES)
        return ReportingCoverageResult(
            report_coverage_pct=round(total_exist / total * 100, 2),
            pdf_coverage_pct=round(total_pdf / total * 100, 2),
            csv_coverage_pct=round(total_csv / total * 100, 2),
            print_coverage_pct=round(total_print / total * 100, 2),
            zero_state_coverage_pct=round(total_zero / total * 100, 2),
            overall_reporting_score=round(
                (
                    (total_exist / total) * 30
                    + (total_pdf / total) * 20
                    + (total_csv / total) * 15
                    + (total_print / total) * 15
                    + (total_zero / total) * 10
                    + (total_large / total) * 10
                ),
                2,
            ),
            reports=reports,
        )

    def _find_test_files(self) -> List[str]:
        files = []
        if os.path.isdir(BACKEND_TEST_DIR):
            for fn in os.listdir(BACKEND_TEST_DIR):
                if fn.startswith("test_") and fn.endswith(".py"):
                    files.append(os.path.join(BACKEND_TEST_DIR, fn))
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

    def _compute_test_score(self, report_name: str,
                             test_functions: Dict[str, List[str]]) -> float:
        keywords = report_name.replace("_", " ").split()
        match_count = 0
        for fn_list in test_functions.values():
            for fn in fn_list:
                if any(kw.lower() in fn.lower() for kw in keywords):
                    match_count += 1
        if match_count >= 3:
            return 100.0
        elif match_count >= 1:
            return 60.0
        return 0.0

    def _has_pdf_test(self, report_name: str,
                       test_functions: Dict[str, List[str]]) -> bool:
        pdf_keywords = ["pdf", "render", "generate_pdf"]
        keywords = report_name.replace("_", " ").split() + pdf_keywords
        for fn_list in test_functions.values():
            for fn in fn_list:
                if all(any(k in fn.lower() for k in kw_group)
                       for kw_group in [keywords, pdf_keywords]):
                    if any(k in fn.lower() for k in pdf_keywords):
                        return True
        return bool(self._generic_pattern_match(report_name, test_functions,
                                                 ["pdf", "generate", "render"]))

    def _has_csv_test(self, report_name: str,
                       test_functions: Dict[str, List[str]]) -> bool:
        return bool(self._generic_pattern_match(report_name, test_functions,
                                                 ["csv", "export", "download"]))

    def _has_print_test(self, report_name: str,
                         test_functions: Dict[str, List[str]]) -> bool:
        return bool(self._generic_pattern_match(report_name, test_functions,
                                                 ["print", "preview"]))

    def _has_zero_state_test(self, report_name: str,
                              test_functions: Dict[str, List[str]]) -> bool:
        return bool(self._generic_pattern_match(report_name, test_functions,
                                                 ["empty", "zero", "no_data", "no_records"]))

    def _has_large_dataset_test(self, report_name: str,
                                 test_functions: Dict[str, List[str]]) -> bool:
        return bool(self._generic_pattern_match(report_name, test_functions,
                                                 ["large", "bulk", "many", "thousands", "stress"]))

    def _generic_pattern_match(self, report_name: str,
                                test_functions: Dict[str, List[str]],
                                patterns: List[str]) -> bool:
        keywords = report_name.replace("_", " ").split()
        for fn_list in test_functions.values():
            for fn in fn_list:
                fn_lower = fn.lower()
                if any(k in fn_lower for k in keywords):
                    if any(p in fn_lower for p in patterns):
                        return True
        return False

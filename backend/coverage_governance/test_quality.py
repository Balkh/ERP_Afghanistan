"""
Phase 8 — Test Quality Analyzer.
Detects and penalizes assertionless tests, duplicate tests,
trivial constructor tests, dead tests, meaningless mocks, fake coverage inflation.
Extends test_governance/quality_analyzer.py with deeper analysis.
"""

import os
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from coverage_governance.models import TestQualityResult, TestQualityIssue


TEST_DIRS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "simulation", "tests")),
]


DEAD_TEST_PATTERNS = [
    r"def test_\w+_placeholder\b",
    r"def test_\w+_todo\b",
    r"def test_\w+_skip\b",
    r"pytest\.skip\(\)",
    r"def test_\w+_not_implemented\b",
    r"raise\s+NotImplementedError",
    r"def test_\w+_example\b",
]

TRIVIAL_PATTERNS = [
    r"def test_\w+_init\b",
    r"def test_\w+_creation\b",
    r"def test_\w+_construct\b",
    r"def test_\w+_setup\b",
    r"def test_\w+_smoke\b",
    r"def test_\w+_exists\b",
    r"def test_\w+_load\b",
]

MOCK_PATTERNS = [
    r"from\s+unittest\.mock",
    r"import\s+mock",
    r"@mock\.patch",
    r"MagicMock",
    r"patch\(",
]


class TestQualityAnalyzer:

    def analyze(self, test_dirs: Optional[List[str]] = None) -> TestQualityResult:
        dirs = test_dirs if test_dirs is not None else TEST_DIRS
        test_files = self._discover_test_files(dirs)
        all_issues: List[TestQualityIssue] = []
        files_with_issues: Set[str] = set()
        total_assertionless = 0
        total_trivial = 0
        total_duplicate = 0
        total_dead = 0
        total_bad_mocks = 0

        for fp in test_files:
            issues = self._analyze_file(fp)
            if issues:
                files_with_issues.add(fp)
                all_issues.extend(issues)

        total_assertionless = sum(1 for i in all_issues if i.issue_type == "assertionless")
        total_trivial = sum(1 for i in all_issues if i.issue_type == "trivial")
        total_dead = sum(1 for i in all_issues if i.issue_type == "dead_test")
        total_bad_mocks = sum(1 for i in all_issues if i.issue_type == "meaningless_mock")

        for i in all_issues:
            if i.issue_type == "duplicate":
                total_duplicate += 1

        total_issues = len(all_issues)
        pct_clean = (
            (len(test_files) - len(files_with_issues)) / len(test_files) * 100
            if test_files else 100.0
        )

        test_quality_score = max(0, 100.0 - (
            total_assertionless * 5.0
            + total_trivial * 3.0
            + total_dead * 8.0
            + total_duplicate * 2.0
            + total_bad_mocks * 4.0
        ))

        details: Dict[str, List[Dict]] = {}
        for issue in all_issues:
            fname = os.path.basename(issue.file)
            if fname not in details:
                details[fname] = []
            details[fname].append({
                "line": issue.line,
                "type": issue.issue_type,
                "severity": issue.severity,
            })

        return TestQualityResult(
            total_test_files=len(test_files),
            files_with_issues=len(files_with_issues),
            total_issues=total_issues,
            assertionless_tests=total_assertionless,
            trivial_tests=total_trivial,
            duplicate_tests=total_duplicate,
            dead_tests=total_dead,
            meaningless_mocks=total_bad_mocks,
            test_quality_score=round(min(test_quality_score, 100), 2),
            details=details,
        )

    def get_module_test_quality_scores(self, result: TestQualityResult
                                        ) -> Dict[str, float]:
        return {"test_quality": result.test_quality_score}

    def _discover_test_files(self, dirs: List[str]) -> List[str]:
        files = []
        for d in dirs:
            if os.path.isdir(d):
                for root, _, filenames in os.walk(d):
                    for fn in filenames:
                        if fn.startswith("test_") and fn.endswith(".py"):
                            files.append(os.path.join(root, fn))
        return files

    def _analyze_file(self, filepath: str) -> List[TestQualityIssue]:
        issues: List[TestQualityIssue] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            content = "".join(lines)
        except Exception:
            return issues

        test_functions = self._extract_test_functions(lines)

        seen_bodies: Dict[str, int] = {}

        for func_name, start_line, end_line in test_functions:
            func_lines = lines[start_line - 1:end_line]
            func_body = "".join(func_lines)

            # 1. Assertionless tests
            has_assert = bool(re.search(r"^\s+assert\b", func_body, re.MULTILINE))
            has_pytest_assert = "assert " in func_body
            has_pytest_raises = "pytest.raises" in func_body
            has_pytest_check = "self.assertTrue" in func_body or "self.assertEqual" in func_body

            if not (has_pytest_assert or has_pytest_raises or has_pytest_check):
                if not any(kw in func_body for kw in [
                    "pytest.skip", "pytest.fail", "raise ", "Exception",
                ]):
                    issues.append(TestQualityIssue(
                        file=filepath,
                        line=start_line,
                        issue_type="assertionless",
                        severity="medium",
                    ))

            # 2. Trivial tests (constructor only, < 5 lines)
            if any(re.match(p, func_body.strip()) for p in TRIVIAL_PATTERNS) or \
               func_name.endswith(("_init", "_creation", "_construct", "_setup")):
                if len(func_lines) <= 5:
                    issues.append(TestQualityIssue(
                        file=filepath,
                        line=start_line,
                        issue_type="trivial",
                        severity="low",
                    ))

            # 3. Dead tests
            for pattern in DEAD_TEST_PATTERNS:
                if re.search(pattern, func_body):
                    issues.append(TestQualityIssue(
                        file=filepath,
                        line=start_line,
                        issue_type="dead_test",
                        severity="high",
                    ))
                    break

            # 4. Duplicate tests (identical function bodies)
            normalized = re.sub(r"\s+", " ", func_body.strip())
            if normalized in seen_bodies:
                issues.append(TestQualityIssue(
                    file=filepath,
                    line=start_line,
                    issue_type="duplicate",
                    severity="low",
                ))
            seen_bodies[normalized] = start_line

            # 5. Meaningless mocks (mocked but no assertion)
            has_mock = any(re.search(p, content) for p in MOCK_PATTERNS)
            if has_mock and not has_pytest_assert and not has_pytest_check:
                issues.append(TestQualityIssue(
                    file=filepath,
                    line=start_line,
                    issue_type="meaningless_mock",
                    severity="medium",
                ))

        return issues

    def _extract_test_functions(self, lines: List[str]) -> List[Tuple[str, int, int]]:
        functions = []
        i = 0
        while i < len(lines):
            m = re.match(r"^\s*def (test_\w+)\s*\(", lines[i])
            if m:
                func_name = m.group(1)
                start = i + 1
                depth = 0
                j = i + 1
                indent = len(lines[i]) - len(lines[i].lstrip())
                while j < len(lines):
                    stripped = lines[j].strip()
                    if stripped == "":
                        j += 1
                        continue
                    current_indent = len(lines[j]) - len(lines[j].lstrip())
                    if current_indent <= indent and stripped.startswith(("def ", "class ")):
                        break
                    if current_indent <= indent and stripped and not stripped.startswith(("#", "@")):
                        if j > start and current_indent <= indent:
                            break
                    j += 1
                functions.append((func_name, start, j))
                i = j
            else:
                i += 1
        return functions

"""
Section 4 — Test Quality Analyzer.
Static analysis of test files to detect low-quality tests.
No heavy AST — uses lightweight pattern matching.
"""
import os
import re
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class TestIssue:
    file: str
    line: int
    issue_type: str
    detail: str
    severity: str = "low"


PATTERN_DUPLICATE_ASSERT = re.compile(r"assert\s+\w+\s*==\s*\w+")
PATTERN_TRIVIAL_CONSTRUCTOR = re.compile(r"def test_\w+_init\b")
PATTERN_SIMPLE_SMOKE = re.compile(r"def test_\w+_smoke\b")
PATTERN_NO_ASSERT = re.compile(r"^\s*def test_")
PATTERN_ASSERT = re.compile(r"^\s+assert")


class TestQualityAnalyzer:

    def __init__(self, test_dir: str = "tests"):
        self._test_dir = test_dir

    def scan_file(self, filepath: str) -> List[TestIssue]:
        issues = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return issues

        content = "".join(lines)
        test_functions = self._extract_test_functions(lines)

        for func_name, start_line, end_line in test_functions:
            func_lines = lines[start_line - 1:end_line]
            func_body = "".join(func_lines)

            # Check for no assertions
            has_assert = bool(PATTERN_ASSERT.search(func_body))
            if not has_assert:
                if not any(kw in func_body for kw in ["pytest.skip", "pytest.fail", "raise"]):
                    issues.append(TestIssue(
                        filepath, start_line, "no_assert",
                        f"Test '{func_name}' has no assert statement", "medium",
                    ))

            # Check trivial constructor tests
            if func_name.endswith("_init") or func_name.endswith("_creation"):
                if len(func_lines) <= 5:
                    issues.append(TestIssue(
                        filepath, start_line, "trivial_constructor",
                        f"Trivial constructor test '{func_name}'", "low",
                    ))

            # Check duplicate assertions
            assert_lines = []
            for i, line in enumerate(func_lines):
                m = PATTERN_DUPLICATE_ASSERT.search(line)
                if m:
                    assert_lines.append((start_line + i, line.strip()))
            for i in range(1, len(assert_lines)):
                if assert_lines[i][1] == assert_lines[i - 1][1]:
                    issues.append(TestIssue(
                        filepath, assert_lines[i][0], "duplicate_assert",
                        "Duplicate assertion pattern", "low",
                    ))

        return issues

    def _extract_test_functions(self, lines: List[str]) -> List[Tuple[str, int, int]]:
        functions = []
        i = 0
        while i < len(lines):
            m = re.match(r"^\s*def (test_\w+)", lines[i])
            if m:
                func_name = m.group(1)
                start = i + 1
                depth = 0
                j = i + 1
                while j < len(lines):
                    stripped = lines[j].rstrip()
                    if stripped == "" or stripped.startswith(("#", "    ", "\t")):
                        j += 1
                        continue
                    leading = len(lines[j]) - len(lines[j].lstrip())
                    if leading <= 4 and depth == 0 and re.match(r"^\s*def |^\s*class ", lines[j]):
                        break
                    if lines[j].strip().startswith(("def ", "class ")):
                        break
                    j += 1
                functions.append((func_name, start, j))
                i = j
            else:
                i += 1
        return functions

    def scan_all(self) -> Dict[str, List[TestIssue]]:
        results: Dict[str, List[TestIssue]] = {}
        if not os.path.isdir(self._test_dir):
            return results
        for fname in sorted(os.listdir(self._test_dir)):
            if fname.startswith("test_") and fname.endswith(".py"):
                fpath = os.path.join(self._test_dir, fname)
                issues = self.scan_file(fpath)
                if issues:
                    results[fname] = issues
        return results

    def generate_report(self) -> Dict:
        results = self.scan_all()
        total_issues = sum(len(v) for v in results.values())
        by_type: Dict[str, int] = {}
        for issues in results.values():
            for iss in issues:
                by_type[iss.issue_type] = by_type.get(iss.issue_type, 0) + 1
        return {
            "total_test_files_scanned": sum(
                1 for f in os.listdir(self._test_dir)
                if f.startswith("test_") and f.endswith(".py")
            ) if os.path.isdir(self._test_dir) else 0,
            "files_with_issues": len(results),
            "total_issues": total_issues,
            "issues_by_type": by_type,
            "details": {
                fname: [{"line": i.line, "type": i.issue_type, "detail": i.detail}
                        for i in issues]
                for fname, issues in results.items()
            },
        }

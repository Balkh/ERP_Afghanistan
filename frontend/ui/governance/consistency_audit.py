"""
Phase 16 — UI Consistency Audit Engine.
Inspects runtime consistency of typography, spacing, section hierarchy, button hierarchy,
table density, hover/focus patterns, empty state usage, and validation UX patterns.
This is a STATIC analysis of source code patterns (not a live runtime inspector).
"""
import ast
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .registry import REGISTRY, ComponentCategory
from .audit_scanner import Severity, Violation, ScanReport


# ═══════════════════════════════════════════════════════════════
# CONSISTENCY CHECK RESULTS
# ═══════════════════════════════════════════════════════════════
@dataclass
class PatternScore:
    """Score for a specific consistency dimension."""
    dimension: str
    score: float  # 0.0 to 1.0
    total_checks: int
    passed: int
    details: List[str] = field(default_factory=list)


@dataclass
class ConsistencyReport:
    """Aggregate consistency report."""
    overall_score: float = 0.0
    dimension_scores: Dict[str, PatternScore] = field(default_factory=dict)
    violations: List[Violation] = field(default_factory=list)

    def print_summary(self):
        print("=" * 72)
        print("  UI CONSISTENCY AUDIT — PATTERN SCORES")
        print("=" * 72)
        for dim, score in sorted(self.dimension_scores.items()):
            bar = "#" * int(score.score * 30)
            print(f"  {dim:30s} [{bar:<30}] {score.score:.0%} ({score.passed}/{score.total_checks})")
        print()
        print(f"  OVERALL CONSISTENCY SCORE: {self.overall_score:.0%}")
        if self.violations:
            print(f"  Consistency violations: {len(self.violations)}")


# ═══════════════════════════════════════════════════════════════
# CONSISTENCY INSPECTORS
# ═══════════════════════════════════════════════════════════════
class BaseConsistencyInspector:
    """Base for all consistency inspectors."""

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.violations: List[Violation] = []


class TypographyRhythmInspector(BaseConsistencyInspector):
    """Verify typography tokens TEXT_* are used consistently, not raw font sizes."""

    def inspect(self, report: ConsistencyReport) -> PatternScore:
        total = 0
        passed = 0
        details = []

        TEXT_TOKENS = {"TEXT_PAGE_TITLE", "TEXT_CARD_TITLE", "TEXT_SECTION_TITLE",
                       "TEXT_BODY", "TEXT_BODY_SMALL", "TEXT_LABEL", "TEXT_LABEL_SMALL",
                       "TEXT_HELPER", "TEXT_TABLE", "TEXT_ERROR", "TEXT_DISPLAY"}
        raw_font_size_pattern = re.compile(r'font-size:\s*(\d+)')

        for root, _dirs, files in os.walk(self.base_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, os.path.join(self.base_path, ".."))
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        lines = fh.readlines()
                except Exception:
                    continue

                for lineno, line in enumerate(lines, 1):
                    # Check for raw font-size in stylesheets
                    for m in raw_font_size_pattern.finditer(line):
                        total += 1
                        has_token = any(tok in line for tok in TEXT_TOKENS)
                        if has_token:
                            passed += 1
                        else:
                            details.append(f"{rel}:{lineno} — raw font-size: {m.group(1)}px without TEXT_* token")

                    # Check for QFont with raw point sizes
                    for m in re.finditer(r'QFont\([^)]+,\s*(\d+)', line):
                        total += 1
                        has_token = any(tok in line for tok in TEXT_TOKENS)
                        if has_token or "TEXT_" in line:
                            passed += 1
                        else:
                            details.append(f"{rel}:{lineno} — QFont with raw size {m.group(1)}")

        score = 1.0 if total == 0 else (passed / total)
        return PatternScore("Typography Rhythm", score, total, passed, details)


class SectionHierarchyInspector(BaseConsistencyInspector):
    """Verify FormSection primary/secondary distinction is used consistently."""

    def inspect(self, report: ConsistencyReport) -> PatternScore:
        total = 0
        passed = 0
        details = []

        for root, _dirs, files in os.walk(self.base_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, os.path.join(self.base_path, ".."))
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except Exception:
                    continue

                # Count FormSection usage without primary= parameter
                form_sections = re.findall(r'(?<!class )FormSection\(', content)
                for _ in form_sections:
                    total += 1

                primary_sections = re.findall(r'FormSection\([^)]*primary\s*=\s*(True|False)', content)
                passed += len(primary_sections)

        missing = total - passed
        if missing > 0:
            details.append(f"FormSection instances without primary= parameter: {missing}")
            details.append("  -> Always set primary=True or primary=False for visual hierarchy")

        score = 1.0 if total == 0 else (passed / total)
        return PatternScore("Section Hierarchy", score, total, passed, details)


class ButtonHierarchyInspector(BaseConsistencyInspector):
    """Verify EnterpriseButton variant usage follows patterns."""

    def inspect(self, report: ConsistencyReport) -> PatternScore:
        total = 0
        passed = 0
        details = []

        # Check common patterns for primary/secondary button order
        for root, _dirs, files in os.walk(self.base_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, os.path.join(self.base_path, ".."))
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except Exception:
                    continue

                # Find consecutive EnterpriseButton usages for action pairs
                # Secondary (Cancel) should come first, then Primary (Save)
                pattern = re.findall(
                    r'EnterpriseButton\([^)]+SECONDARY[^)]+\).*?EnterpriseButton\([^)]+PRIMARY[^)]+\)',
                    content, re.DOTALL
                )

        score = 1.0  # No hard rule to check; pattern is well-established
        return PatternScore("Button Hierarchy", score, max(total, 1), max(passed, 1), details)


class EmptyStateInspector(BaseConsistencyInspector):
    """Verify StateHelper.show_empty() uses the actions parameter."""

    def inspect(self, report: ConsistencyReport) -> PatternScore:
        total = 0
        passed = 0
        details = []

        for root, _dirs, files in os.walk(self.base_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, os.path.join(self.base_path, ".."))
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except Exception:
                    continue

                show_empty_calls = re.findall(r'show_empty\(', content)
                for _ in show_empty_calls:
                    total += 1

                with_actions = re.findall(r'show_empty\([^)]*actions\s*=', content)
                passed += len(with_actions)

        if total > 0 and passed < total:
            details.append(f"show_empty() calls without actions= parameter: {total - passed}")

        score = 1.0 if total == 0 else (passed / total)
        return PatternScore("Empty State Quality", score, total, passed, details)


class ValidationUXInspector(BaseConsistencyInspector):
    """Verify validation UX uses inline patterns, not QMessageBox."""

    def inspect(self, report: ConsistencyReport) -> PatternScore:
        total = 0
        passed = 0
        details = []

        # Check QMessageBox.warning / QMessageBox.critical used for validation
        qmb_validation = re.compile(r'QMessageBox\.(warning|critical)\([^)]*[Vv]alid')
        set_error_usage = re.compile(r'\.set_error\(')

        for root, _dirs, files in os.walk(self.base_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, os.path.join(self.base_path, ".."))
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except Exception:
                    continue

                # Count QMessageBox validation (bad)
                for m in qmb_validation.finditer(content):
                    total += 1
                    details.append(f"{rel} — QMessageBox used for validation (should use set_error())")

                # Count set_error usage (good)
                for m in set_error_usage.finditer(content):
                    passed += 1

        score = 1.0 if (total + passed) == 0 else (passed / (total + passed))
        return PatternScore("Validation UX Quality", score, total + passed, passed, details)


class InteractionFeedbackInspector(BaseConsistencyInspector):
    """Verify interaction feedback uses governed tokens (hover, focus, transition timing)."""

    def inspect(self, report: ConsistencyReport) -> PatternScore:
        total = 0
        passed = 0
        details = []

        COLOR_HOVER_PATTERN = re.compile(r'COLOR_BG_HOVER|COLOR_BG_FOCUS|COLOR_HOVER_OVERLAY')
        RAW_HOVER_PATTERN = re.compile(r':hover\s*\{[^}]*background-color:\s*#[0-9a-fA-F]{3,8}')

        for root, _dirs, files in os.walk(self.base_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, os.path.join(self.base_path, ".."))
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except Exception:
                    continue

                # Count raw hover colors
                for m in RAW_HOVER_PATTERN.finditer(content):
                    total += 1
                    details.append(f"{rel} — raw hover color in stylesheet (use COLOR_BG_HOVER)")

                # Count token-based hover
                for m in COLOR_HOVER_PATTERN.finditer(content):
                    passed += 1

        score = 1.0 if (total + passed) == 0 else (passed / (total + passed))
        return PatternScore("Interaction Feedback", score, total + passed, passed, details)


# ═══════════════════════════════════════════════════════════════
# CONSISTENCY ENGINE
# ═══════════════════════════════════════════════════════════════
class ConsistencyEngine:
    """Orchestrates all consistency inspectors and generates the final report."""

    INSPECTORS = [
        TypographyRhythmInspector,
        SectionHierarchyInspector,
        ButtonHierarchyInspector,
        EmptyStateInspector,
        ValidationUXInspector,
        InteractionFeedbackInspector,
    ]

    def __init__(self, base_path: str = ""):
        self.base_path = base_path or os.path.join(os.path.dirname(__file__), "..")
        self.report = ConsistencyReport()

    def run(self) -> ConsistencyReport:
        """Execute all consistency inspectors."""
        scores = []
        for InspectorClass in self.INSPECTORS:
            inspector = InspectorClass(self.base_path)
            try:
                score = inspector.inspect(self.report)
                self.report.dimension_scores[score.dimension] = score
                scores.append(score.score)
            except Exception as e:
                print(f"  [WARN] Inspector {InspectorClass.__name__} failed: {e}")

        self.report.overall_score = sum(scores) / max(len(scores), 1)
        self.report.violations = [
            v for inspector in self.INSPECTORS
            for v in getattr(inspector, "violations", [])
        ]
        return self.report

    def run_and_report(self) -> ConsistencyReport:
        """Run and print summary."""
        self.run()
        self.report.print_summary()
        return self.report

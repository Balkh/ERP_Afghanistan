"""
UI Governance Scanner.

Detects UI governance violations from the backend perspective.
Read-only — scans codebase for forbidden patterns and reports violations.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional


UI_GOVERNANCE_VERSION = "1.0.0"


@dataclass
class UIViolation:
    file_path: str
    line_number: int
    rule: str
    severity: str  # error | warning | info
    message: str
    snippet: str = ""


@dataclass
class UIGovernanceReport:
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.utcnow().isoformat() + "Z")
    violations: List[UIViolation] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def total_violations(self) -> int:
        return len(self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")


def _get_frontend_ui_dir() -> Optional[str]:
    """Get frontend UI directory path."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate = os.path.join(base, "frontend", "ui")
    if os.path.isdir(candidate):
        return candidate
    # Try alternative location
    alt = os.path.join(os.path.dirname(base), "frontend", "ui")
    if os.path.isdir(alt):
        return alt
    return None


def scan_raw_qpushbutton() -> List[UIViolation]:
    """
    Rule: No raw QPushButton usage.
    All buttons must use EnterpriseButton from ui/components/buttons.py.
    """
    violations = []
    ui_dir = _get_frontend_ui_dir()
    if not ui_dir:
        return violations

    pattern = re.compile(r'^\s*(?:self\.)?\w*\s*=\s*QPushButton\s*\(')

    for root, _dirs, files in os.walk(ui_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        if pattern.search(line) and "EnterpriseButton" not in line:
                            violations.append(UIViolation(
                                file_path=os.path.relpath(fpath, ui_dir),
                                line_number=lineno,
                                rule="no_raw_qpushbutton",
                                severity="error",
                                message="Raw QPushButton used instead of EnterpriseButton",
                                snippet=line.strip()[:80],
                            ))
            except (OSError, UnicodeDecodeError):
                continue

    return violations


def scan_inline_stylesheet() -> List[UIViolation]:
    """
    Rule: No setStyleSheet with hardcoded values.
    Must use COLOR_* / SPACING_* tokens from ui/constants.py.
    """
    violations = []
    ui_dir = _get_frontend_ui_dir()
    if not ui_dir:
        return violations

    pattern = re.compile(r'\.setStyleSheet\s*\(')

    for root, _dirs, files in os.walk(ui_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        if pattern.search(line):
                            violations.append(UIViolation(
                                file_path=os.path.relpath(fpath, ui_dir),
                                line_number=lineno,
                                rule="no_inline_stylesheet",
                                severity="warning",
                                message="Inline setStyleSheet() used instead of theme tokens",
                                snippet=line.strip()[:80],
                            ))
            except (OSError, UnicodeDecodeError):
                continue

    return violations


def scan_hardcoded_hex_colors() -> List[UIViolation]:
    """
    Rule: No hardcoded hex color values in UI files.
    Must use COLOR_* constants from ui/constants.py.
    """
    violations = []
    ui_dir = _get_frontend_ui_dir()
    if not ui_dir:
        return violations

    hex_pattern = re.compile(r'#[0-9a-fA-F]{6}\b')

    for root, _dirs, files in os.walk(ui_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        matches = hex_pattern.findall(line)
                        for m in matches:
                            violations.append(UIViolation(
                                file_path=os.path.relpath(fpath, ui_dir),
                                line_number=lineno,
                                rule="no_hardcoded_hex_color",
                                severity="warning",
                                message=f"Hardcoded hex color {m}",
                                snippet=line.strip()[:80],
                            ))
            except (OSError, UnicodeDecodeError):
                continue

    return violations


def run_ui_governance_scan() -> UIGovernanceReport:
    """Run all UI governance scans."""
    report = UIGovernanceReport()
    ui_dir = _get_frontend_ui_dir()
    if not ui_dir:
        return report

    # Count files
    for root, _dirs, files in os.walk(ui_dir):
        report.files_scanned += sum(1 for f in files if f.endswith(".py"))

    report.violations.extend(scan_raw_qpushbutton())
    report.violations.extend(scan_inline_stylesheet())
    report.violations.extend(scan_hardcoded_hex_colors())

    return report

"""
Phase 16 — UI Governance Audit Scanner.
Automated violation detection for design system enforcement.

Usage:
    python -m ui.governance.audit_scanner scan [--path frontend/ui] [--severity CRITICAL]
    python -m ui.governance.audit_scanner report
"""
import ast
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════
# SEVERITY MODEL
# ═══════════════════════════════════════════════════════════════
class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# ═══════════════════════════════════════════════════════════════
# VIOLATION MODEL
# ═══════════════════════════════════════════════════════════════
@dataclass
class Violation:
    file_path: str
    line: int
    severity: Severity
    rule_id: str
    message: str
    suggested_fix: str = ""
    snippet: str = ""


@dataclass
class ScanReport:
    total_violations: int = 0
    by_severity: Dict[str, int] = field(default_factory=lambda: {s.value: 0 for s in Severity})
    violations: List[Violation] = field(default_factory=list)
    files_scanned: int = 0
    errors: List[str] = field(default_factory=list)

    def add(self, v: Violation):
        self.violations.append(v)
        self.total_violations += 1
        self.by_severity[v.severity.value] = self.by_severity.get(v.severity.value, 0) + 1

    def print_summary(self):
        print("=" * 72)
        print("  UI GOVERNANCE AUDIT — VIOLATION REPORT")
        print("=" * 72)
        print(f"  Files scanned: {self.files_scanned}")
        print(f"  Total violations: {self.total_violations}")
        print()
        for sev in Severity:
            count = self.by_severity.get(sev.value, 0)
            print(f"  {sev.value:10s}: {count}")
        print()
        if self.violations:
            print("  --- DETAILS ---")
            for v in sorted(self.violations, key=lambda x: (list(Severity).index(x.severity), x.file_path, x.line)):
                print(f"  [{v.severity.value}] {v.file_path}:{v.line}")
                print(f"    {v.rule_id}: {v.message}")
                if v.suggested_fix:
                    print(f"    -> {v.suggested_fix}")
                print()

    def generate_markdown(self) -> str:
        lines = ["# UI Governance Audit Report\n", f"**Files Scanned:** {self.files_scanned}  ",
                 f"**Total Violations:** {self.total_violations}  \n"]
        for sev in Severity:
            count = self.by_severity.get(sev.value, 0)
            if count:
                lines.append(f"- **{sev.value}**: {count}")
        lines.append("\n## Violations\n")
        for v in sorted(self.violations, key=lambda x: (list(Severity).index(x.severity), x.file_path, x.line)):
            lines.append(f"### [{v.severity.value}] `{v.file_path}` line {v.line}")
            lines.append(f"- **Rule**: `{v.rule_id}`")
            lines.append(f"- **Message**: {v.message}")
            if v.suggested_fix:
                lines.append(f"- **Fix**: {v.suggested_fix}")
            lines.append("")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# GOVERNANCE RULES
# ═══════════════════════════════════════════════════════════════
FORBIDDEN_WIDGETS = {
    "QPushButton": "Use EnterpriseButton from ui.components.buttons",
    "QDialogButtonBox": "Use EnterpriseButton components directly",
    "QToolButton": "Use EnterpriseButton or IconButton",
    "QCommandLinkButton": "Use EnterpriseButton",
    "QInputDialog": "Use InputDialog from ui.components.dialogs",
    "QMessageBox": "Use NotificationManager for notifications, StateHelper for states",
}

FORBIDDEN_RAW_PATTERNS = {
    "hex_color": {
        "pattern": re.compile(r'"[#][0-9a-fA-F]{3,8}"'),
        "message": "Raw hex color detected. Use COLOR_* tokens from ui.constants.",
    },
}

APPROVED_FONT_NAMES = {"Segoe UI"}
CONSTANTS_FILE = "constants.py"
GOVERNANCE_DIR_NAME = "governance"
RENDERING_DIR_NAME = "rendering"


# ═══════════════════════════════════════════════════════════════
# RULE-SPECIFIC CHECKERS
# ═══════════════════════════════════════════════════════════════
class RuleChecker:
    """Base class for rule checkers."""

    def __init__(self, file_path: str, relative_path: str):
        self.file_path = file_path
        self.relative_path = relative_path
        self.is_constants = relative_path.endswith(CONSTANTS_FILE)
        self.is_governance = GOVERNANCE_DIR_NAME in relative_path
        self.is_rendering = RENDERING_DIR_NAME in relative_path

    def check_raw_hex_colors(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_constants or self.is_governance:
            return None
        for match in FORBIDDEN_RAW_PATTERNS["hex_color"]["pattern"].finditer(line):
            hex_val = match.group().strip('"')
            # Skip white/black or standard CSS named colors used in constants
            if hex_val.lower() in ("#ffffff", "#000000", "#fff", "#000"):
                continue
            # Skip if used within a COLOR_* token definition
            if "COLOR_" in line and "=" in line:
                continue
            return Violation(
                file_path=self.relative_path,
                line=lineno,
                severity=Severity.CRITICAL,
                rule_id="GOV-001",
                message=f"Raw hex color {match.group()} detected",
                suggested_fix="Replace with corresponding COLOR_* token from ui.constants",
                snippet=line.strip(),
            )
        return None

    def check_forbidden_widgets(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_governance:
            return None
        line_stripped = line.strip()
        # Skip import lines and type hints
        if line_stripped.startswith("from ") or line_stripped.startswith("import "):
            return None
        # Skip class definitions that inherit from QPushButton
        if "class " in line_stripped and "QPushButton" in line_stripped:
            return None
        for widget, fix in FORBIDDEN_WIDGETS.items():
            if widget in line_stripped:
                if widget == "QPushButton" and "EnterpriseButton" in line_stripped:
                    continue
                sev = Severity.CRITICAL if widget in ("QPushButton", "QDialogButtonBox") else Severity.HIGH
                return Violation(
                    file_path=self.relative_path,
                    line=lineno,
                    severity=sev,
                    rule_id="GOV-002",
                    message=f"Forbidden widget '{widget}' detected",
                    suggested_fix=fix,
                    snippet=line_stripped,
                )
        return None

    def check_raw_spacing(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_constants or self.is_governance:
            return None
        # setSpacing(n) where n is a number
        m = re.search(r'setSpacing\s*\(\s*(\d+)', line)
        if m:
            val = int(m.group(1))
            if val > 0:
                return Violation(
                    file_path=self.relative_path,
                    line=lineno,
                    severity=Severity.HIGH,
                    rule_id="GOV-003",
                    message=f"Raw spacing value detected: setSpacing({val})",
                    suggested_fix=f"Replace with SPACING_* token (e.g., SPACING_SM={4}, SPACING_MD={8})",
                    snippet=line.strip(),
                )
        return None

    def check_qfont_usage(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_constants or self.is_governance:
            return None
        # Match QFont("FontName", ...) — only flag if font name is hardcoded
        m = re.search(r'QFont\s*\(\s*"([^"]+)"', line)
        if m:
            font_name = m.group(1)
            if font_name not in APPROVED_FONT_NAMES:
                return Violation(
                    file_path=self.relative_path,
                    line=lineno,
                    severity=Severity.MEDIUM,
                    rule_id="GOV-004",
                    message=f"Non-standard font name '{font_name}' in QFont()",
                    suggested_fix="Use 'Segoe UI' or centralized font tokens",
                    snippet=line.strip(),
                )
        return None

    def check_inline_stylesheet(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_constants or self.is_governance:
            return None
        # setStyleSheet with inline content longer than 80 chars (abuse detection)
        if 'setStyleSheet(' in line and len(line.strip()) > 120:
            return Violation(
                file_path=self.relative_path,
                line=lineno,
                severity=Severity.MEDIUM,
                rule_id="GOV-005",
                message="Long inline stylesheet detected (>120 chars)",
                suggested_fix="Use centralized build_*_stylesheet() functions or _apply_variant_style()",
                snippet=line.strip()[:80] + "...",
            )
        return None

    def check_raw_border_radius(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_constants or self.is_governance:
            return None
        m = re.search(r'border-radius:\s*(\d+)', line, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            return Violation(
                file_path=self.relative_path,
                line=lineno,
                severity=Severity.MEDIUM,
                rule_id="GOV-006",
                message=f"Raw border-radius value {val}px detected in stylesheet",
                suggested_fix="Use BORDER_RADIUS_SM/MD/LG tokens",
                snippet=line.strip(),
            )
        return None

    def check_renderer_layer_usage(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_governance:
            return None
        # Detect any import or usage of the forbidden renderer classes
        forbidden_renderers = ["ButtonRenderer", "TableRenderer", "DialogRenderer", "CardRenderer"]
        for renderer in forbidden_renderers:
            if renderer in line and "class " not in line:
                return Violation(
                    file_path=self.relative_path,
                    line=lineno,
                    severity=Severity.CRITICAL,
                    rule_id="GOV-007",
                    message=f"Forbidden renderer layer usage: '{renderer}'",
                    suggested_fix=f"Replace with approved primitive from ui.components",
                    snippet=line.strip(),
                )
        return None

    def check_unapproved_dialog(self, line: str, lineno: int) -> Optional[Violation]:
        if self.is_governance or self.is_constants:
            return None
        if re.match(r'^class\s+\w+\(QDialog\)', line.strip()):
            return Violation(
                file_path=self.relative_path,
                line=lineno,
                severity=Severity.HIGH,
                rule_id="GOV-008",
                message="Direct QDialog subclass — must inherit from EnterpriseDialog",
                suggested_fix="Inherit from EnterpriseDialog (ui.components.dialogs) instead of QDialog",
                snippet=line.strip(),
            )
        return None


# ═══════════════════════════════════════════════════════════════
# SCANNER ENGINE
# ═══════════════════════════════════════════════════════════════
class GovernanceScanner:
    """Scans frontend UI code for governance violations."""

    BASE_PATH: str = ""

    def __init__(self, base_path: str = ""):
        self.BASE_PATH = base_path or os.path.join(os.path.dirname(__file__), "..")
        self.report = ScanReport()
        self._checkers: List[RuleChecker] = []
        self._all_py_files: List[str] = []

    def _discover_files(self) -> List[str]:
        """Recursively discover all .py files under the UI tree."""
        py_files = []
        for root, _dirs, files in os.walk(self.BASE_PATH):
            for f in files:
                if f.endswith(".py"):
                    full = os.path.join(root, f)
                    py_files.append(full)
        return sorted(py_files)

    def scan_file(self, file_path: str):
        """Run all rule checkers against a single file."""
        rel_path = os.path.relpath(file_path, os.path.dirname(self.BASE_PATH))
        checker = RuleChecker(file_path, rel_path)

        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except Exception as e:
            self.report.errors.append(f"Cannot read {file_path}: {e}")
            return

        for lineno, line in enumerate(lines, 1):
            for check_method in [
                checker.check_raw_hex_colors,
                checker.check_forbidden_widgets,
                checker.check_raw_spacing,
                checker.check_qfont_usage,
                checker.check_inline_stylesheet,
                checker.check_raw_border_radius,
                checker.check_renderer_layer_usage,
                checker.check_unapproved_dialog,
            ]:
                violation = check_method(line, lineno)
                if violation:
                    self.report.add(violation)

    def run(self) -> ScanReport:
        """Execute full scan across the entire UI tree."""
        self._all_py_files = self._discover_files()
        self.report.files_scanned = len(self._all_py_files)
        for file_path in self._all_py_files:
            self.scan_file(file_path)
        return self.report

    def save_report(self, output_path: str = "governance_audit_report.md"):
        """Write markdown report to disk."""
        md = self.report.generate_markdown()
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"Report saved: {output_path}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════
def main():
    """Run the governance scanner from CLI."""
    args = sys.argv[1:] if len(sys.argv) > 1 else ["scan"]

    base_path = os.path.join(os.path.dirname(__file__), "..")
    scanner = GovernanceScanner(base_path)

    if "scan" in args:
        report = scanner.run()
        report.print_summary()
        if "--save" in args:
            scanner.save_report()

    elif "report" in args:
        report = scanner.run()
        report.print_summary()
        scanner.save_report()


if __name__ == "__main__":
    main()

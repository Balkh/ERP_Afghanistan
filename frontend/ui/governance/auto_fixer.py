"""
Phase 16.1 — Safe Auto-Fixer System.
Automated migration helpers for low-risk governance violations ONLY.

Usage:
    python -m ui.governance.auto_fixer run --dry-run
    python -m ui.governance.auto_fixer run --apply
    python -m ui.governance.auto_fixer run --file path/to/file.py --apply
"""
import os
import re
import sys
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# SAFE MIGRATION RULES
# ═══════════════════════════════════════════════════════════════
@dataclass
class MigrationRule:
    """A single auto-fix rule. Only applied if ALL safety checks pass."""
    name: str
    pattern: "re.Pattern"
    replacement: "Optional[str]"
    description: str
    risk_level: str  # "low" or "medium"
    skip_patterns: List[str] = field(default_factory=list)  # Lines containing these are skipped
    requires_import: Optional[str] = None  # Import to add if not present


# ── LOW-RISK RULES (safe to auto-apply) ──
LOW_RISK_RULES = [
    MigrationRule(
        name="raw_spacing_to_token",
        pattern=re.compile(r'\.setSpacing\((\d+)\)'),
        replacement=None,  # Computed dynamically
        description="Replace setSpacing(N) with SPACING_* token",
        risk_level="low",
        skip_patterns=["# GOVERNANCE-EXEMPT", "# NO-FIX"],
    ),
    MigrationRule(
        name="raw_border_radius_to_token",
        pattern=re.compile(r'border-radius:\s*(\d+)px'),
        replacement=None,
        description="Replace border-radius: Npx with BORDER_RADIUS_* token",
        risk_level="low",
        skip_patterns=["# GOVERNANCE-EXEMPT", "# NO-FIX"],
    ),
    MigrationRule(
        name="raw_margin_to_token",
        pattern=re.compile(r'margin:\s*(\d+)px'),
        replacement=None,
        description="Replace margin: Npx with SPACING_* token",
        risk_level="low",
        skip_patterns=["# GOVERNANCE-EXEMPT", "# NO-FIX"],
    ),
    MigrationRule(
        name="raw_padding_to_token",
        pattern=re.compile(r'padding:\s*(\d+)px'),
        replacement=None,
        description="Replace padding: Npx with SPACING_* token",
        risk_level="low",
        skip_patterns=["# GOVERNANCE-EXEMPT", "# NO-FIX"],
    ),
]

# ── MEDIUM-RISK RULES (review before applying) ──
MEDIUM_RISK_RULES = [
    MigrationRule(
        name="qfont_to_text_token",
        pattern=re.compile(r'QFont\("([^"]+)",\s*(\d+)'),
        replacement=None,
        description="Replace QFont('FontName', N) with governed font pattern",
        risk_level="medium",
        skip_patterns=["# GOVERNANCE-EXEMPT", "# NO-FIX"],
    ),
]


# ═══════════════════════════════════════════════════════════════
# TOKEN MAPPING TABLES
# ═══════════════════════════════════════════════════════════════
SPACING_MAP = {
    0: "SPACING_NONE",
    2: "SPACING_XS",
    3: "SPACING_XS",
    4: "SPACING_XS",
    6: "SPACING_SM",
    8: "SPACING_SM",
    10: "SPACING_MD",
    12: "SPACING_MD",
    15: "SPACING_LG",
    16: "SPACING_LG",
    20: "SPACING_XL",
    24: "SPACING_XXL",
    32: "SPACING_6",
}

BORDER_RADIUS_MAP = {
    1: "BORDER_RADIUS_SM",
    3: "BORDER_RADIUS_SM",
    4: "BORDER_RADIUS_SM",
    6: "BORDER_RADIUS_MD",
    8: "BORDER_RADIUS_MD",
    10: "BORDER_RADIUS_LG",
    12: "BORDER_RADIUS_LG",
    15: "BORDER_RADIUS_LG",
    20: "BORDER_RADIUS_LG",
}


def spacing_token(value: int) -> str:
    """Map a raw spacing value to the closest SPACING_* token."""
    if value in SPACING_MAP:
        return SPACING_MAP[value]
    # Find closest
    closest = min(SPACING_MAP.keys(), key=lambda k: abs(k - value))
    return SPACING_MAP[closest]


def border_radius_token(value: int) -> str:
    """Map a raw border-radius value to the closest BORDER_RADIUS_* token."""
    if value in BORDER_RADIUS_MAP:
        return BORDER_RADIUS_MAP[value]
    closest = min(BORDER_RADIUS_MAP.keys(), key=lambda k: abs(k - value))
    return BORDER_RADIUS_MAP[closest]


# ═══════════════════════════════════════════════════════════════
# AUTO-FIXER ENGINE
# ═══════════════════════════════════════════════════════════════
@dataclass
class FixResult:
    file_path: str
    original_lines: int = 0
    changes_made: int = 0
    changes: List[Tuple[int, str, str]] = field(default_factory=list)  # (line, old, new)
    skipped: List[Tuple[int, str, str]] = field(default_factory=list)  # (line, old, reason)
    errors: List[str] = field(default_factory=list)


class SafeAutoFixer:
    """Applies safe, low-risk governance fixes to Python files."""

    def __init__(self, base_path: str = ""):
        self.base_path = base_path or os.path.join(os.path.dirname(__file__), "..")
        self.dry_run = True
        self.rules = LOW_RISK_RULES  # Default to low-risk only

    def _should_skip(self, line: str, rule: MigrationRule) -> Optional[str]:
        """Check if this line should be skipped. Returns reason or None."""
        for skip in rule.skip_patterns:
            if skip in line:
                return f"Skip pattern: {skip}"
        return None

    def _add_import_if_needed(self, lines: List[str], import_name: str) -> Tuple[List[str], bool]:
        """Add an import if it doesn't exist. Returns (lines, was_added)."""
        for line in lines:
            if import_name in line and "from ui.constants import" in line:
                return lines, False
            if import_name in line and "import" in line:
                return lines, False

        # Find the first 'from ui.constants import' line and add to it
        for i, line in enumerate(lines):
            if "from ui.constants import" in line:
                # Check if the import spans multiple lines (parentheses)
                if "(" in line and ")" not in line:
                    # Multi-line import, find the closing paren
                    j = i
                    while j < len(lines) and ")" not in lines[j]:
                        j += 1
                    if j < len(lines):
                        # Insert before the closing paren line
                        indent = "    "
                        lines.insert(j, f"{indent}{import_name},\n")
                        return lines, True
                else:
                    # Single-line import, append to it
                    stripped = line.rstrip()
                    if stripped.endswith(","):
                        lines[i] = stripped + f" {import_name}\n"
                    else:
                        lines[i] = stripped.replace(")", f", {import_name})\n")
                    return lines, True

        # No constants import found, add one at the top
        for i, line in enumerate(lines):
            if line.startswith("from PySide6") or line.startswith("import "):
                lines.insert(i + 1, f"from ui.constants import {import_name}\n")
                return lines, True

        lines.insert(0, f"from ui.constants import {import_name}\n")
        return lines, True

    def _fix_spacing(self, line: str) -> Optional[Tuple[str, str]]:
        """Fix setSpacing(N) -> setSpacing(SPACING_*). Returns (old, new) or None."""
        m = re.search(r'\.setSpacing\((\d+)\)', line)
        if not m:
            return None
        value = int(m.group(1))
        token = spacing_token(value)
        old = m.group(0)
        new = f".setSpacing({token})"
        return (old, new)

    def _fix_border_radius(self, line: str) -> Optional[Tuple[str, str]]:
        """Fix border-radius: Npx -> border-radius: {BORDER_RADIUS_*}px."""
        m = re.search(r'border-radius:\s*(\d+)px', line)
        if not m:
            return None
        value = int(m.group(1))
        token = border_radius_token(value)
        old = m.group(0)
        new = f"border-radius: {{{token}}}px"
        return (old, new)

    def _fix_margin(self, line: str) -> Optional[Tuple[str, str]]:
        """Fix margin: Npx -> margin: {SPACING_*}px."""
        m = re.search(r'margin:\s*(\d+)px', line)
        if not m:
            return None
        value = int(m.group(1))
        token = spacing_token(value)
        old = m.group(0)
        new = f"margin: {{{token}}}px"
        return (old, new)

    def _fix_padding(self, line: str) -> Optional[Tuple[str, str]]:
        """Fix padding: Npx -> padding: {SPACING_*}px."""
        m = re.search(r'padding:\s*(\d+)px', line)
        if not m:
            return None
        value = int(m.group(1))
        token = spacing_token(value)
        old = m.group(0)
        new = f"padding: {{{token}}}px"
        return (old, new)

    def fix_file(self, file_path: str) -> FixResult:
        """Apply all safe fixes to a single file."""
        result = FixResult(file_path=file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except Exception as e:
            result.errors.append(f"Cannot read: {e}")
            return result

        result.original_lines = len(lines)
        needs_spacing_import = False
        needs_radius_import = False

        for i, line in enumerate(lines):
            # Skip comments and blank lines
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Try each fixer
            fixers = [
                (self._fix_spacing, "setSpacing", "SPACING_SM"),
                (self._fix_border_radius, "border-radius", "BORDER_RADIUS_SM"),
                (self._fix_margin, "margin", "SPACING_SM"),
                (self._fix_padding, "padding", "SPACING_SM"),
            ]

            for fixer, keyword, import_name in fixers:
                fix = fixer(line)
                if fix:
                    old, new = fix
                    skip_reason = None
                    for rule in self.rules:
                        sr = self._should_skip(line, rule)
                        if sr:
                            skip_reason = sr
                            break

                    if skip_reason:
                        result.skipped.append((i + 1, old, skip_reason))
                    else:
                        lines[i] = line.replace(old, new)
                        result.changes.append((i + 1, old, new))
                        result.changes_made += 1
                        if "SPACING" in new:
                            needs_spacing_import = True
                        if "BORDER_RADIUS" in new:
                            needs_radius_import = True

        # Add imports if needed
        if needs_spacing_import:
            lines, added = self._add_import_if_needed(lines, "SPACING_SM")
        if needs_radius_import:
            lines, added = self._add_import_if_needed(lines, "BORDER_RADIUS_SM")

        # Write back if not dry run
        if not self.dry_run and result.changes_made > 0:
            # Backup original
            backup_path = file_path + ".governance_backup"
            shutil.copy2(file_path, backup_path)
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.writelines(lines)

        return result

    def run(self, file_path: Optional[str] = None) -> List[FixResult]:
        """Run auto-fixer on a single file or entire UI tree."""
        if file_path:
            return [self.fix_file(file_path)]

        results = []
        for root, _dirs, files in os.walk(self.base_path):
            # Skip governance module itself
            if "governance" in root:
                continue
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                results.append(self.fix_file(fp))

        return results

    def print_report(self, results: List[FixResult]):
        """Print summary of auto-fix results."""
        total_changes = sum(r.changes_made for r in results)
        total_skipped = sum(len(r.skipped) for r in results)
        files_with_changes = sum(1 for r in results if r.changes_made > 0)

        print("=" * 72)
        print("  GOVERNANCE AUTO-FIX REPORT")
        print("=" * 72)
        mode = "DRY RUN (no files modified)" if self.dry_run else "APPLIED (files modified)"
        print(f"  Mode: {mode}")
        print(f"  Files scanned: {len(results)}")
        print(f"  Files changed: {files_with_changes}")
        print(f"  Total fixes: {total_changes}")
        print(f"  Total skipped: {total_skipped}")
        print()

        for r in results:
            if r.changes_made > 0:
                print(f"  {r.file_path}: {r.changes_made} fixes")
                for lineno, old, new in r.changes:
                    print(f"    L{lineno}: {old} -> {new}")
            if r.skipped:
                for lineno, old, reason in r.skipped:
                    print(f"    L{lineno}: SKIPPED ({reason})")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════
def main():
    """Run the auto-fixer from CLI."""
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    base_path = os.path.join(os.path.dirname(__file__), "..")
    fixer = SafeAutoFixer(base_path)

    if "--apply" in args:
        fixer.dry_run = False
        print("  [!] APPLYING FIXES — files will be modified")
    else:
        print("  [i] DRY RUN — no files will be modified")

    file_path = None
    if "--file" in args:
        idx = args.index("--file")
        if idx + 1 < len(args):
            file_path = args[idx + 1]

    results = fixer.run(file_path)
    fixer.print_report(results)


if __name__ == "__main__":
    main()

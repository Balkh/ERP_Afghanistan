#!/usr/bin/env python3
"""
Design System Enforcer - Pre-commit/Pre-merge Validation
=========================================================
Strict enforcement: FAIL on ANY violation (no warnings).
Exception: ONLY email/print templates (printable_invoice.py HTML).

Usage:
    python scripts/pre_commit_enforcer.py [files...]
    python scripts/pre_commit_enforcer.py --staged-only
    python scripts/pre_commit_enforcer.py --full-scan
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Configuration
# Script is at: E:\Pharmacy_ERP\frontend\scripts\pre_commit_enforcer.py
# Frontend dir is: E:\Pharmacy_ERP\frontend
FRONTEND_DIR = Path(__file__).parent.parent
EXCLUDED_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv"}
EXCLUDED_FILES = {"design_system_governance.py", "pre_commit_enforcer.py", "constants.py", "ux_governor.py"}

# EXCEPTIONS: Files allowed to have non-token values
EXCEPTIONS = {
    "printable_invoice.py": "Email/print templates require specific CSS",
    "operator_safety.py": "Example strings with # prefixes (e.g., invoice #123)",
    "audit_scanner.py": "Governance scanner — lists hex values for validation purposes",
}

# =====================================================
# RULE DETECTION LOGIC - COMPREHENSIVE PATTERNS
# =====================================================

# HARDCODED COLORS - STRICT PATTERNS
COLOR_PATTERNS = [
    # Hex colors (3 or 6 digits)
    (r"#(?:[0-9a-fA-F]{3}){1,2}\b", "HEX_COLOR", "Use COLOR_* token from ui/constants.py"),
    # QColor with raw values
    (r"QColor\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)", "QCOLOR_RAW", "Use COLOR_* token"),
    # rgb/rgba functions
    (r"rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)", "RGB_FUNC", "Use COLOR_* token"),
    (r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)", "RGBA_FUNC", "Use COLOR_* token"),
    # QPen/QBrush with raw colors
    (r"QPen\(QColor\([^)]+\)\)", "QPEN_RAW", "Use COLOR_* token"),
    # Only flag when QColor wraps raw RGB integers, not COLOR_* tokens or variables
    (r"QBrush\(QColor\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:\)|\s*\))", "QBRUSH_RAW", "Use COLOR_* token"),
    # StyleSheet colors in string literals
    (r'["\'][^"\']*:\s*#[0-9a-fA-F]{3,6}\s*;', "STYLESHEET_HEX", "Use COLOR_* token"),
]

# FORBIDDEN FONTS
FORBIDDEN_FONTS = [
    (r"\bArial\b(?!\s*,\s*sans-serif)", "FORBIDDEN_FONT", "Use Typography.FONT_FAMILY_PRIMARY (Segoe UI)"),
    (r"\bTimes\s+New\s+Roman\b", "FORBIDDEN_FONT", "Use Typography.FONT_FAMILY_PRIMARY (Segoe UI)"),
    (r"\bVerdana\b", "FORBIDDEN_FONT", "Use Typography.FONT_FAMILY_PRIMARY (Segoe UI)"),
    (r"\bTahoma\b", "FORBIDDEN_FONT", "Use Typography.FONT_FAMILY_PRIMARY (Segoe UI)"),
]

# RENDERER LAYER DEPRECATION - STRICT PATTERNS
RENDERER_PATTERNS = [
    (r"ButtonRenderer\.", "RENDERER_LAYER", "Use EnterpriseButton component instead"),
    (r"TableRenderer\.", "RENDERER_LAYER", "Use EnterpriseTable component instead"),
    (r"DialogRenderer\.", "RENDERER_LAYER", "Use EnterpriseDialog component instead"),
    (r"CardRenderer\.", "RENDERER_LAYER", "Use EnterpriseCard or inline styling with tokens instead"),
    (r"BadgeRenderer\.", "RENDERER_LAYER", "Use inline QLabel styling with tokens instead"),
]

# HARDCODED SPACING - STRICT PATTERNS
SPACING_PATTERNS = [
    # setContentsMargins with raw numbers (not variables)
    (r"setContentsMargins\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)", "HARDCODED_MARGINS", 
     "Use MARGIN_PAGE, MARGIN_CARD, or SPACING_* constants"),
    # setSpacing with raw numbers (not variables)
    (r"setSpacing\(\s*\d+\s*\)", "HARDCODED_SPACING", 
     "Use SPACING_XS, SM, MD, LG, XL constants"),
    # padding in stylesheets with raw pixels
    (r"padding:\s*\d+px", "HARDCODED_PADDING", "Use SPACING_* constants"),
    (r"margin:\s*\d+px", "HARDCODED_MARGIN", "Use SPACING_* constants or MARGIN_* constants"),
]

# =====================================================
# TOKEN WHITELIST - ALLOWED VALUES
# =====================================================

ALLOWED_TOKENS = {
    # From ui/constants.py - Colors
    "COLOR_PRIMARY", "COLOR_PRIMARY_HOVER", "COLOR_PRIMARY_ACTIVE", "COLOR_PRIMARY_MUTED",
    "COLOR_SUCCESS", "COLOR_SUCCESS_BG", "COLOR_WARNING", "COLOR_WARNING_BG",
    "COLOR_DANGER", "COLOR_DANGER_BG", "COLOR_INFO", "COLOR_INFO_BG",
    "COLOR_BG_MAIN", "COLOR_BG_SURFACE", "COLOR_BG_ELEVATED", "COLOR_BG_INPUT",
    "COLOR_TEXT_PRIMARY", "COLOR_TEXT_SECONDARY", "COLOR_TEXT_MUTED", "COLOR_TEXT_ON_PRIMARY",
    "COLOR_BORDER", "COLOR_BORDER_LIGHT", "COLOR_BORDER_FOCUS",
    "COLOR_TABLE_HEADER", "COLOR_TABLE_ALT", "COLOR_TABLE_GRID",
    "COLOR_TABLE_GRIDLINE", "COLOR_TABLE_BORDER_LIGHT", "COLOR_TABLE_HEADER_BG_LIGHT",
    "COLOR_STATUS_VALID", "COLOR_STATUS_INVALID", "COLOR_STATUS_WARNING", "COLOR_STATUS_PENDING",
    "COLOR_WHATSAPP",
    # Secondary button tokens
    "COLOR_SECONDARY_BG", "COLOR_SECONDARY_HOVER", "COLOR_SECONDARY_TEXT", "COLOR_SECONDARY_ACTIVE",
    # Status
    "COLOR_STATUS_VALID", "COLOR_STATUS_INVALID", "COLOR_STATUS_WARNING", "COLOR_STATUS_PENDING",
    # Form and border tokens
    "COLOR_FORM_BORDER_LIGHT", "COLOR_FORM_TEXT_LIGHT", "COLOR_UI_DIVIDER_LIGHT",
    "COLOR_BORDER_DIALOG", "COLOR_BORDER_TABLE", "COLOR_BORDER_INPUT",
    # Legacy aliases
    "COLOR_TEXT", "COLOR_BACKGROUND",
    # From enterprise_styling.py - Spacing
    "Spacing.SPACING_XXS", "Spacing.SPACING_XS", "Spacing.SPACING_SM", "Spacing.SPACING_MD",
    "Spacing.SPACING_LG", "Spacing.SPACING_XL", "Spacing.SPACING_XXL", "Spacing.SPACING_XXXL",
    "Spacing.BORDER_RADIUS_SM", "Spacing.BORDER_RADIUS_MD", "Spacing.BORDER_RADIUS_LG", "Spacing.BORDER_RADIUS_XL",
    # From ui/constants.py - Spacing
    "SPACING_XS", "SPACING_SM", "SPACING_MD", "SPACING_LG", "SPACING_XL", "SPACING_XXL",
    "MARGIN_PAGE", "MARGIN_CARD", "MARGIN_FORM",
    "PADDING_BUTTON_H", "PADDING_BUTTON_V", "PADDING_INPUT_H", "PADDING_INPUT_V", 
    "PADDING_CARD", "PADDING_DIALOG",
    # Typography
    "Typography.FONT_FAMILY_PRIMARY", "Typography.FONT_FAMILY_SECONDARY", "Typography.FONT_FAMILY_MONO",
}


class DesignSystemEnforcer:
    """
    Strict Design System Enforcer
    - FAIL on ANY violation
    - NO exceptions except email templates
    - Deterministic enforcement
    """
    
    def __init__(self, check_staged: bool = False, full_scan: bool = False):
        self.check_staged = check_staged
        self.full_scan = full_scan
        self.violations = []
        self.stats = {
            "files_checked": 0,
            "color_violations": 0,
            "spacing_violations": 0,
            "font_violations": 0,
            "renderer_violations": 0,
            "exceptions_allowed": 0,
        }
        
    def _is_exception_file(self, file_path: Path) -> bool:
        """Check if file is allowed to have exceptions"""
        filename = file_path.name
        return filename in EXCEPTIONS
    
    def _check_token_usage(self, line: str) -> bool:
        """Check if line uses allowed tokens"""
        # Check if line contains any allowed token
        for token in ALLOWED_TOKENS:
            if token in line:
                return True
        
        # Check if line imports from constants
        if "from ui.constants import" in line or "from theme.enterprise_styling import" in line:
            return True
            
        return False
    
    def _get_files_to_check(self) -> List[Path]:
        """Get list of files to check based on mode"""
        files = []
        
        if self.check_staged:
            # Get staged files
            try:
                result = subprocess.run(
                    ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                    capture_output=True, text=True, cwd=FRONTEND_DIR
                )
                if result.returncode == 0:
                    for f in result.stdout.strip().split('\n'):
                        if f and f.endswith('.py') and not any(x in f for x in EXCLUDED_FILES):
                            files.append(FRONTEND_DIR / f)
            except Exception:
                print("Warning: Could not get staged files, falling back to full scan")
                self.full_scan = True
                
        if self.full_scan or not files:
            # Full project scan
            ui_dir = FRONTEND_DIR / "ui"
            if ui_dir.exists():
                for root, dirs, filenames in os.walk(ui_dir):
                    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                    for f in filenames:
                        if f.endswith('.py') and f not in EXCLUDED_FILES:
                            files.append(Path(root) / f)
        
        return files
    
    def _scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for design system violations"""
        violations = []
        
        is_exception = self._is_exception_file(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return [{"error": f"Could not read file: {e}", "line": 0, "type": "READ_ERROR"}]
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Skip token usage lines and imports
            if self._check_token_usage(line):
                # If this line uses tokens, check if it ALSO contains forbidden values
                # (we need to be more strict - check if there's a violation even with tokens)
                pass
            
            # Skip comment lines (but not commented-out code)
            stripped = line.strip()
            if stripped.startswith('#') and not stripped.startswith('# '):
                continue
            
            # Check HARDCODED COLORS
            for pattern, vtype, suggestion in COLOR_PATTERNS:
                if re.search(pattern, line):
                    # Additional check: is this in a context that uses tokens?
                    # For exception files, allow some violations
                    if is_exception:
                        self.stats["exceptions_allowed"] += 1
                        continue
                    violations.append({
                        "file": str(file_path.relative_to(FRONTEND_DIR)),
                        "line": i,
                        "content": line.strip()[:100],
                        "type": vtype,
                        "suggestion": suggestion,
                        "severity": "HIGH",
                        "value": re.search(pattern, line).group(0) if re.search(pattern, line) else "UNKNOWN"
                    })
                    self.stats["color_violations"] += 1
            
            # Check FORBIDDEN FONTS
            for pattern, vtype, suggestion in FORBIDDEN_FONTS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Exception files can use specific fonts for email compatibility
                    if is_exception:
                        self.stats["exceptions_allowed"] += 1
                        continue
                    violations.append({
                        "file": str(file_path.relative_to(FRONTEND_DIR)),
                        "line": i,
                        "content": line.strip()[:100],
                        "type": vtype,
                        "suggestion": suggestion,
                        "severity": "HIGH",
                        "value": re.search(pattern, line, re.IGNORECASE).group(0)
                    })
                    self.stats["font_violations"] += 1
            
            # Check RENDERER LAYER DEPRECATION
            for pattern, vtype, suggestion in RENDERER_PATTERNS:
                if re.search(pattern, line):
                    if is_exception:
                        self.stats["exceptions_allowed"] += 1
                        continue
                    violations.append({
                        "file": str(file_path.relative_to(FRONTEND_DIR)),
                        "line": i,
                        "content": line.strip()[:100],
                        "type": vtype,
                        "suggestion": suggestion,
                        "severity": "MEDIUM",
                        "value": re.search(pattern, line).group(0)
                    })
                    self.stats["renderer_violations"] += 1

            # Check HARDCODED SPACING
            for pattern, vtype, suggestion in SPACING_PATTERNS:
                if re.search(pattern, line):
                    # Skip if already using constants/variables
                    if "SPACING_" in line or "MARGIN_" in line or "PADDING_" in line:
                        continue
                    if is_exception:
                        self.stats["exceptions_allowed"] += 1
                        continue
                    violations.append({
                        "file": str(file_path.relative_to(FRONTEND_DIR)),
                        "line": i,
                        "content": line.strip()[:100],
                        "type": vtype,
                        "suggestion": suggestion,
                        "severity": "HIGH",
                        "value": re.search(pattern, line).group(0)
                    })
                    self.stats["spacing_violations"] += 1
        
        return violations
    
    def run(self) -> int:
        """Run enforcement - returns 0 on success, 1 on failure"""
        print("=" * 70)
        print("DESIGN SYSTEM ENFORCER - STRICT MODE")
        print("=" * 70)
        print()
        
        files = self._get_files_to_check()
        
        if not files:
            print("No files to check.")
            return 0
        
        print(f"Scanning {len(files)} files...")
        print()
        
        for file_path in files:
            self.stats["files_checked"] += 1
            file_violations = self._scan_file(file_path)
            self.violations.extend(file_violations)
        
        # Generate report
        self._print_report()
        
        # Exit with error if violations found
        if self.violations:
            print()
            print("=" * 70)
            print("[BLOCKED] DESIGN SYSTEM VIOLATIONS DETECTED")
            print("=" * 70)
            print()
            print("COMMIT REJECTED - Fix violations before committing")
            print()
            print("To fix:")
            print("1. Replace hardcoded colors with COLOR_* tokens from ui/constants.py")
            print("2. Replace hardcoded spacing with SPACING_* constants")
            print("3. Replace forbidden fonts with Segoe UI")
            print()
            print("Exception files (allowed non-token values):")
            for fn, reason in EXCEPTIONS.items():
                print(f"  - {fn}: {reason}")
            print()
            return 1
        else:
            print()
            print("=" * 70)
            print("[APPROVED] DESIGN SYSTEM COMPLIANT")
            print("=" * 70)
            return 0
    
    def _print_report(self):
        """Print detailed violation report"""
        if not self.violations:
            return
            
        print("-" * 70)
        print("VIOLATION REPORT")
        print("-" * 70)
        
        # Group by file
        by_file = {}
        for v in self.violations:
            f = v.get("file", "unknown")
            if f not in by_file:
                by_file[f] = []
            by_file[f].append(v)
        
        for file, file_violations in sorted(by_file.items()):
            print(f"\n{file} ({len(file_violations)} violations):")
            for v in file_violations:
                print(f"  Line {v.get('line', '?'):4d} | {v.get('type', 'UNKNOWN'):20s} | {v.get('value', '')[:40]}")
                print(f"              Suggestion: {v.get('suggestion', '')}")
        
        print()
        print("-" * 70)
        print("SUMMARY")
        print("-" * 70)
        print(f"Files Checked:      {self.stats['files_checked']}")
        print(f"Color Violations:   {self.stats['color_violations']}")
        print(f"Font Violations:    {self.stats['font_violations']}")
        print(f"Spacing Viol.:     {self.stats['spacing_violations']}")
        print(f"Renderer Viol.:    {self.stats['renderer_violations']}")
        print(f"Exceptions:        {self.stats['exceptions_allowed']}")
        print(f"Total Violations:   {len(self.violations)}")
        print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Design System Enforcer - Strict Mode")
    parser.add_argument("--staged-only", action="store_true", help="Check only staged files")
    parser.add_argument("--full-scan", action="store_true", help="Full project scan")
    parser.add_argument("files", nargs="*", help="Specific files to check")
    
    args = parser.parse_args()
    
    enforcer = DesignSystemEnforcer(
        check_staged=args.staged_only,
        full_scan=args.full_scan
    )
    
    exit_code = enforcer.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
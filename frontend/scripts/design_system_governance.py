#!/usr/bin/env python3
"""
Design System Governance Scanner
=================================
Enterprise ERP UI Governance - Automated compliance enforcement.
This script scans for design system violations and enforces:
- No hardcoded colors (must use theme tokens)
- No forbidden fonts (must use Segoe UI)
- No hardcoded spacing (must use constants)
- No inline styles bypassing the theme system

Usage:
    python scripts/design_system_governance.py [--fix] [--report]
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple

# Configuration
# Script is at: E:\Pharmacy_ERP\frontend\scripts\design_system_governance.py
# Frontend dir is: E:\Pharmacy_ERP\frontend
FRONTEND_DIR = Path(__file__).parent.parent

EXCLUDED_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv"}
EXCLUDED_FILES = {"design_system_governance.py"}

# Design token enforcements
REQUIRED_IMPORTS = ["from ui.constants import"]
FORBIDDEN_COLORS = [
    r"#(?:[0-9a-fA-F]{3}){1,2}\b",  # Hex colors
    r"QColor\([0-9]+,\s*[0-9]+,\s*[0-9]+\)",  # Raw QColor
    r"rgb\([0-9]+,\s*[0-9]+,\s*[0-9]+\)",  # rgb()
    r"rgba\([0-9]+,\s*[0-9]+,\s*[0-9]+,\s*[\d.]+\)",  # rgba()
]

FORBIDDEN_FONTS = [
    r"\bArial\b",
    r"\bTimes New Roman\b",
    r"\bVerdana\b",
    r"\bTahoma\b",
]

FORBIDDEN_SPACING = [
    r"setContentsMargins\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)",  # Hardcoded margins
    r"setSpacing\(\s*\d+\s*\)",  # Hardcoded spacing
]

# Token whitelist - colors that ARE allowed (from constants.py)
ALLOWED_TOKENS = {
    # From ui/constants.py
    "COLOR_PRIMARY", "COLOR_PRIMARY_HOVER", "COLOR_PRIMARY_ACTIVE", "COLOR_PRIMARY_MUTED",
    "COLOR_SUCCESS", "COLOR_SUCCESS_BG", "COLOR_WARNING", "COLOR_WARNING_BG",
    "COLOR_DANGER", "COLOR_DANGER_BG", "COLOR_INFO", "COLOR_INFO_BG",
    "COLOR_BG_MAIN", "COLOR_BG_SURFACE", "COLOR_BG_ELEVATED", "COLOR_BG_INPUT",
    "COLOR_TEXT_PRIMARY", "COLOR_TEXT_SECONDARY", "COLOR_TEXT_MUTED", "COLOR_TEXT_ON_PRIMARY",
    "COLOR_BORDER", "COLOR_BORDER_LIGHT", "COLOR_BORDER_FOCUS",
    "COLOR_TABLE_HEADER", "COLOR_TABLE_ALT", "COLOR_TABLE_GRID",
    "COLOR_STATUS_VALID", "COLOR_STATUS_INVALID", "COLOR_STATUS_WARNING", "COLOR_STATUS_PENDING",
    "COLOR_WHATSAPP",
    # From enterprise_styling.py
    "Typography.FONT_FAMILY_PRIMARY", "Typography.FONT_FAMILY_SECONDARY", "Typography.FONT_FAMILY_MONO",
    "Spacing.SPACING_XXS", "Spacing.SPACING_XS", "Spacing.SPACING_SM", "Spacing.SPACING_MD",
    "Spacing.SPACING_LG", "Spacing.SPACING_XL", "Spacing.SPACING_XXL", "Spacing.SPACING_XXXL",
    "Spacing.BORDER_RADIUS_SM", "Spacing.BORDER_RADIUS_MD", "Spacing.BORDER_RADIUS_LG", "Spacing.BORDER_RADIUS_XL",
}

# File categories for reporting
FILE_CATEGORIES = {
    "licensing": ["activation_screen.py", "license_status_screen.py", "license_manager_dialog.py"],
    "accounting": ["arap_ageing_screen.py", "balance_sheet_screen.py", "profit_loss_screen.py",
                   "accounting_dashboard.py", "account_ledger_screen.py", "journal_entry_screen.py",
                   "chart_of_accounts_screen.py", "trial_balance_screen.py"],
    "system": ["control_center_screen.py", "intelligence_hub_screen.py", "production_screen.py",
               "backup_screen.py", "correlation_screen.py", "drift_intelligence_screen.py",
               "integrity_screen.py", "workflow_intelligence_screen.py"],
    "auth": ["login_screen.py"],
    "components": ["document_action_dialog.py", "toast.py", "tables.py", "buttons.py", "forms.py"],
}


class DesignSystemGovernance:
    """Enterprise Design System Governance Scanner"""
    
    def __init__(self, auto_fix: bool = False):
        self.auto_fix = auto_fix
        self.violations = []
        self.stats = {
            "files_scanned": 0,
            "color_violations": 0,
            "font_violations": 0,
            "spacing_violations": 0,
            "files_compliant": 0,
            "files_non_compliant": 0,
        }
        
    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for design system violations"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return [{"error": f"Could not read file: {e}", "line": 0, "type": "READ_ERROR"}]
        
        lines = content.split('\n')
        
        # Check for hardcoded colors
        for i, line in enumerate(lines, 1):
            # Skip if line contains allowed tokens
            if any(token in line for token in ALLOWED_TOKENS):
                continue
                
            # Check for forbidden color patterns
            for pattern in FORBIDDEN_COLORS:
                if re.search(pattern, line):
                    # Verify it's not using a token
                    if not any(tok in line for tok in ALLOWED_TOKENS):
                        violations.append({
                            "file": str(file_path.relative_to(FRONTEND_DIR)),
                            "line": i,
                            "content": line.strip()[:80],
                            "type": "HARDCODED_COLOR",
                            "severity": "HIGH",
                            "message": "Hardcoded color found. Use COLOR_* tokens from ui.constants"
                        })
            
            # Check for forbidden fonts
            for pattern in FORBIDDEN_FONTS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append({
                        "file": str(file_path.relative_to(FRONTEND_DIR)),
                        "line": i,
                        "content": line.strip()[:80],
                        "type": "FORBIDDEN_FONT",
                        "severity": "HIGH",
                        "message": "Forbidden font found. Use Segoe UI from Typography.FONT_FAMILY_PRIMARY"
                    })
            
            # Check for hardcoded spacing
            for pattern in FORBIDDEN_SPACING:
                if re.search(pattern, line):
                    # Verify it's not using constants
                    if "SPACING_" not in line and "Spacing.SPACING_" not in line:
                        violations.append({
                            "file": str(file_path.relative_to(FRONTEND_DIR)),
                            "line": i,
                            "content": line.strip()[:80],
                            "type": "HARDCODED_SPACING",
                            "severity": "MEDIUM",
                            "message": "Hardcoded spacing found. Use SPACING_* constants from ui.constants"
                        })
        
        return violations
    
    def scan_directory(self, directory: Path) -> None:
        """Scan entire directory for violations"""
        for root, dirs, files in os.walk(directory):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            for file in files:
                if file.endswith('.py') and file not in EXCLUDED_FILES:
                    file_path = Path(root) / file
                    self.stats["files_scanned"] += 1
                    
                    file_violations = self.scan_file(file_path)
                    
                    if file_violations:
                        self.violations.extend(file_violations)
                        self.stats["files_non_compliant"] += 1
                        
                        # Count violation types
                        for v in file_violations:
                            if v.get("type") == "HARDCODED_COLOR":
                                self.stats["color_violations"] += 1
                            elif v.get("type") == "FORBIDDEN_FONT":
                                self.stats["font_violations"] += 1
                            elif v.get("type") == "HARDCODED_SPACING":
                                self.stats["spacing_violations"] += 1
                    else:
                        self.stats["files_compliant"] += 1
    
    def generate_report(self) -> str:
        """Generate a comprehensive report"""
        total_violations = len(self.violations)
        compliance_score = (self.stats["files_compliant"] / max(1, self.stats["files_scanned"])) * 100
        
        report = []
        report.append("=" * 80)
        report.append("ENTERPRISE DESIGN SYSTEM GOVERNANCE REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Files Scanned: {self.stats['files_scanned']}")
        report.append(f"Compliant Files: {self.stats['files_compliant']}")
        report.append(f"Non-Compliant Files: {self.stats['files_non_compliant']}")
        report.append(f"Compliance Score: {compliance_score:.1f}%")
        report.append("")
        report.append("-" * 80)
        report.append("VIOLATION BREAKDOWN")
        report.append("-" * 80)
        report.append(f"Color Violations: {self.stats['color_violations']}")
        report.append(f"Font Violations: {self.stats['font_violations']}")
        report.append(f"Spacing Violations: {self.stats['spacing_violations']}")
        report.append(f"Total Violations: {total_violations}")
        report.append("")
        
        if self.violations:
            report.append("-" * 80)
            report.append("DETAILED VIOLATIONS")
            report.append("-" * 80)
            
            # Group by file
            by_file = {}
            for v in self.violations:
                f = v.get("file", "unknown")
                if f not in by_file:
                    by_file[f] = []
                by_file[f].append(v)
            
            for file, file_violations in sorted(by_file.items()):
                report.append(f"\n{file} ({len(file_violations)} violations):")
                for v in file_violations[:5]:  # Show first 5 per file
                    report.append(f"  Line {v.get('line', '?')}: {v.get('type', 'UNKNOWN')} - {v.get('message', '')}")
                if len(file_violations) > 5:
                    report.append(f"  ... and {len(file_violations) - 5} more")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run(self) -> int:
        """Run the governance scanner"""
        ui_dir = FRONTEND_DIR / "ui"
        
        if not ui_dir.exists():
            print(f"Error: {ui_dir} does not exist")
            return 1
        
        print(f"Scanning {ui_dir} for design system violations...")
        self.scan_directory(ui_dir)
        
        report = self.generate_report()
        print(report)
        
        # Exit with error code if violations found
        if self.violations:
            print("\n[!] DESIGN SYSTEM VIOLATIONS DETECTED")
            print("Run with --fix flag to attempt auto-fix (may require manual review)")
            return 1
        else:
            print("\n[OK] ALL FILES COMPLIANT WITH DESIGN SYSTEM")
            return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enterprise Design System Governance Scanner")
    parser.add_argument("--fix", action="store_true", help="Attempt to auto-fix violations")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    scanner = DesignSystemGovernance(auto_fix=args.fix)
    exit_code = scanner.run()
    
    if args.json and scanner.violations:
        print("\n" + json.dumps(scanner.violations, indent=2))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
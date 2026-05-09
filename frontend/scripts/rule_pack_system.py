#!/usr/bin/env python3
"""
RULE PACK SYSTEM - Modular Design System Enforcement
=====================================================
Implements 4 rule packs for comprehensive UI governance:
1. COLOR SYSTEM ENFORCEMENT
2. SPACING SYSTEM ENFORCEMENT
3. TYPOGRAPHY ENFORCEMENT  
4. COMPONENT CONSISTENCY ENFORCEMENT

Each rule pack is independently executable and CI-compatible.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# Configuration
FRONTEND_DIR = Path(__file__).parent.parent
UI_DIR = FRONTEND_DIR / "ui"

# =====================================================
# RULE PACK BASE CLASS
# =====================================================

@dataclass
class Violation:
    """Represents a design system violation."""
    rule_pack: str
    file_path: str
    line_number: int
    violation_type: str
    severity: str  # HIGH, MEDIUM, LOW
    message: str
    suggested_fix: str
    line_content: str = ""

@dataclass
class RulePackResult:
    """Result of a rule pack execution."""
    rule_pack_name: str
    violations: List[Violation]
    files_scanned: int
    execution_time_ms: float
    passed: bool
    
    @property
    def violation_count(self) -> int:
        return len(self.violations)
    
    @property
    def severity_counts(self) -> Dict[str, int]:
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for v in self.violations:
            counts[v.severity] = counts.get(v.severity, 0) + 1
        return counts


class RulePack(ABC):
    """Abstract base class for rule packs."""
    
    def __init__(self):
        self.name = "RulePack"
        self.description = ""
        self.severity_threshold = "MEDIUM"
        
    @abstractmethod
    def scan_file(self, file_path: Path) -> List[Violation]:
        """Scan a single file for violations."""
        pass
    
    def scan_directory(self, ui_dir: Path) -> RulePackResult:
        """Scan entire UI directory."""
        import time
        start = time.time()
        
        violations = []
        files_scanned = 0
        
        exclude_files = {"printable_invoice.py", "theme_manager.py"}
        
        for py_file in ui_dir.rglob("*.py"):
            if py_file.name in exclude_files:
                continue
            files_scanned += 1
            violations.extend(self.scan_file(py_file))
        
        elapsed = (time.time() - start) * 1000
        
        return RulePackResult(
            rule_pack_name=self.name,
            violations=violations,
            files_scanned=files_scanned,
            execution_time_ms=elapsed,
            passed=len([v for v in violations if v.severity == "HIGH"]) == 0
        )


# =====================================================
# RULE PACK 1 — COLOR SYSTEM ENFORCEMENT
# =====================================================

class ColorSystemEnforcement(RulePack):
    """
    RULE PACK 1: COLOR SYSTEM ENFORCEMENT
    
    Enforces:
    - No hardcoded hex colors (#XXXXXX)
    - All colors must use COLOR_* tokens
    - Semantic color usage (primary, success, danger, etc.)
    - Dark theme consistency
    
    Exclusions:
    - RGBA with transparency (hover effects)
    - Print/email templates
    """
    
    # Valid color tokens
    VALID_TOKENS = {
        # Primary colors
        "COLOR_PRIMARY", "COLOR_PRIMARY_HOVER", "COLOR_PRIMARY_ACTIVE",
        # Semantic colors
        "COLOR_SUCCESS", "COLOR_WARNING", "COLOR_DANGER", "COLOR_INFO",
        "COLOR_STATUS_VALID", "COLOR_STATUS_WARNING",
        # Background colors
        "COLOR_BG_MAIN", "COLOR_BG_SURFACE", "COLOR_BG_ELEVATED", "COLOR_BG_INPUT",
        # Text colors
        "COLOR_TEXT_PRIMARY", "COLOR_TEXT_SECONDARY", "COLOR_TEXT_MUTED",
        # Border colors
        "COLOR_BORDER", "COLOR_BORDER_LIGHT",
    }
    
    # Common patterns that should use tokens
    COLOR_PATTERNS = {
        # Primary brand
        "#FF6B35": ("COLOR_PRIMARY", "Brand orange"),
        "#3b82f6": ("COLOR_PRIMARY", "Material blue"),
        "#2196F3": ("COLOR_PRIMARY", "Material blue"),
        # Success
        "#10b981": ("COLOR_SUCCESS", "Success green"),
        "#4CAF50": ("COLOR_SUCCESS", "Material green"),
        "#28a745": ("COLOR_SUCCESS", "Bootstrap green"),
        "#2ecc71": ("COLOR_SUCCESS", "Flat green"),
        "#008000": ("COLOR_SUCCESS", "Standard green"),
        # Danger
        "#ef4444": ("COLOR_DANGER", "Tailwind red"),
        "#F44336": ("COLOR_DANGER", "Material red"),
        "#dc3545": ("COLOR_DANGER", "Bootstrap red"),
        "#c0392b": ("COLOR_DANGER", "Flat red"),
        "#FF0000": ("COLOR_DANGER", "Standard red"),
        # Warning
        "#f59e0b": ("COLOR_WARNING", "Tailwind amber"),
        "#FF9800": ("COLOR_WARNING", "Material orange"),
        "#ffc107": ("COLOR_WARNING", "Bootstrap warning"),
        # Backgrounds (dark theme)
        "#1f2937": ("COLOR_BG_MAIN", "Dark surface"),
        "#374151": ("COLOR_BG_ELEVATED", "Dark elevated"),
        "#111827": ("COLOR_BG_INPUT", "Dark input"),
        "#11111b": ("COLOR_BG_INPUT", "Catppuccin base"),
        "#181825": ("COLOR_BG_SURFACE", "Catppuccin mantle"),
        "#313244": ("COLOR_BG_ELEVATED", "Catppuccin surface"),
        # Borders
        "#4b5563": ("COLOR_BORDER", "Gray border"),
        "#dee2e6": ("COLOR_BORDER_LIGHT", "Light border"),
        # Text
        "#e5e7eb": ("COLOR_TEXT_PRIMARY", "Light text"),
        "#6b7280": ("COLOR_TEXT_MUTED", "Muted text"),
        "#495057": ("COLOR_TEXT_SECONDARY", "Secondary text"),
        "#6c757d": ("COLOR_TEXT_MUTED", "Bootstrap muted"),
        "#9ca3af": ("COLOR_TEXT_MUTED", "Gray muted"),
    }
    
    def __init__(self):
        super().__init__()
        self.name = "COLOR_SYSTEM_ENFORCEMENT"
        self.description = "Enforces token-based color usage"
        
    def scan_file(self, file_path: Path) -> List[Violation]:
        """Scan file for color violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return violations
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments and already-tokenized lines
            if self._is_excluded_line(line):
                continue
                
            # Find hex colors
            hex_colors = re.findall(r'#[0-9a-fA-F]{6}', line)
            for hex_color in hex_colors:
                if hex_color.upper() in [c.upper() for c in self.COLOR_PATTERNS.keys()]:
                    # Check if already using token
                    if not self._uses_token(line):
                        token, desc = self.COLOR_PATTERNS.get(hex_color.upper(), 
                                            ("COLOR_*", "Unknown"))
                        violations.append(Violation(
                            rule_pack="COLOR_SYSTEM",
                            file_path=str(file_path.relative_to(FRONTEND_DIR)),
                            line_number=line_num,
                            violation_type="HARDCODED_COLOR",
                            severity=self._assess_severity(hex_color),
                            message=f"Hardcoded color {hex_color}. Use {token} ({desc})",
                            suggested_fix=f"Replace {hex_color} with {token}",
                            line_content=line.strip()
                        ))
        
        return violations
    
    def _is_excluded_line(self, line: str) -> bool:
        """Check if line should be excluded from scanning."""
        stripped = line.strip()
        # Skip comments
        if stripped.startswith('#') or stripped.startswith('//'):
            return True
        # Skip docstrings
        if '"""' in line or "'''" in line:
            return True
        return False
    
    def _uses_token(self, line: str) -> bool:
        """Check if line uses a valid color token."""
        for token in self.VALID_TOKENS:
            if token in line:
                return True
        return False
    
    def _assess_severity(self, hex_color: str) -> str:
        """Assess violation severity based on color."""
        high_priority = {"#FF6B35", "#3b82f6", "#ef4444", "#F44336", "#10b981", "#f59e0b"}
        if hex_color.upper() in high_priority:
            return "HIGH"
        return "MEDIUM"


# =====================================================
# RULE PACK 2 — SPACING SYSTEM ENFORCEMENT
# =====================================================

class SpacingSystemEnforcement(RulePack):
    """
    RULE PACK 2: SPACING SYSTEM ENFORCEMENT
    
    Enforces:
    - No hardcoded spacing integers in setSpacing()
    - No hardcoded setContentsMargins() values
    - Use SPACING_* constants only
    
    Valid tokens:
    - SPACING_XS (4px)
    - SPACING_SM (8px) 
    - SPACING_MD (12px)
    - SPACING_LG (16px)
    - SPACING_XL (20px)
    - SPACING_XXL (30px)
    - MARGIN_PAGE (20px)
    """
    
    # Spacing value to token mapping
    SPACING_MAPPINGS = {
        0: ("0", "Zero spacing"),
        2: ("SPACING_XS", "Micro spacing"),
        4: ("SPACING_XS", "Extra small"),
        5: ("SPACING_XS + 1", "Small plus"),
        6: ("SPACING_SM", "Small"),
        8: ("SPACING_SM", "Small standard"),
        10: ("SPACING_SM + SPACING_XS", "Small medium"),
        12: ("SPACING_MD", "Medium"),
        15: ("SPACING_MD + SPACING_XS", "Medium large"),
        16: ("SPACING_LG", "Large"),
        20: ("SPACING_LG + SPACING_XS", "Large plus"),
        24: ("SPACING_XL", "Extra large"),
        25: ("SPACING_XL + SPACING_XS", "XL small"),
        30: ("SPACING_XL + SPACING_MD", "XL medium"),
        40: ("SPACING_XXL", "XXL"),
    }
    
    def __init__(self):
        super().__init__()
        self.name = "SPACING_SYSTEM_ENFORCEMENT"
        self.description = "Enforces token-based spacing usage"
        
    def scan_file(self, file_path: Path) -> List[Violation]:
        """Scan file for spacing violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return violations
        
        for line_num, line in enumerate(lines, 1):
            if self._is_excluded_line(line):
                continue
            
            # Check setSpacing
            match = re.search(r'setSpacing\(\s*(\d+)\s*\)', line)
            if match:
                spacing = int(match.group(1))
                if not self._uses_token(line):
                    token, desc = self._map_spacing(spacing)
                    violations.append(Violation(
                        rule_pack="SPACING_SYSTEM",
                        file_path=str(file_path.relative_to(FRONTEND_DIR)),
                        line_number=line_num,
                        violation_type="HARDCODED_SPACING",
                        severity="MEDIUM",
                        message=f"Hardcoded spacing {spacing}. Use {token}",
                        suggested_fix=f"setSpacing({token})",
                        line_content=line.strip()
                    ))
            
            # Check setContentsMargins with numeric values
            match = re.search(r'setContentsMargins\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', line)
            if match:
                vals = [int(match.group(i)) for i in range(1, 5)]
                if not self._uses_token(line):
                    violations.append(Violation(
                        rule_pack="SPACING_SYSTEM",
                        file_path=str(file_path.relative_to(FRONTEND_DIR)),
                        line_number=line_num,
                        violation_type="HARDCODED_SPACING",
                        severity="MEDIUM",
                        message=f"Hardcoded margins {vals}. Use SPACING_* constants",
                        suggested_fix=f"setContentsMargins(SPACING_*, SPACING_*, SPACING_*, SPACING_*)",
                        line_content=line.strip()
                    ))
        
        return violations
    
    def _is_excluded_line(self, line: str) -> bool:
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            return True
        return False
    
    def _uses_token(self, line: str) -> bool:
        return "SPACING_" in line or "MARGIN_" in line
    
    def _map_spacing(self, value: int) -> Tuple[str, str]:
        """Map numeric spacing to token."""
        # Find closest match
        closest = min(self.SPACING_MAPPINGS.keys(), key=lambda x: abs(x - value))
        return self.SPACING_MAPPINGS[closest]


# =====================================================
# RULE PACK 3 — TYPOGRAPHY ENFORCEMENT
# =====================================================

class TypographyEnforcement(RulePack):
    """
    RULE PACK 3: TYPOGRAPHY ENFORCEMENT
    
    Enforces:
    - Use Segoe UI for all UI text
    - No other font families
    - Standard font sizes from design system
    """
    
    FORBIDDEN_FONTS = {
        "Arial", "Times New Roman", "Verdana", "Tahoma", "Helvetica",
        "Courier New", "Georgia", "Comic Sans MS"
    }
    
    def __init__(self):
        super().__init__()
        self.name = "TYPOGRAPHY_ENFORCEMENT"
        self.description = "Enforces Segoe UI and standard typography"
        
    def scan_file(self, file_path: Path) -> List[Violation]:
        """Scan file for typography violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return violations
        
        for line_num, line in enumerate(lines, 1):
            for font in self.FORBIDDEN_FONTS:
                if re.search(rf'\b{font}\b', line, re.IGNORECASE):
                    if "Segoe UI" not in line:
                        violations.append(Violation(
                            rule_pack="TYPOGRAPHY",
                            file_path=str(file_path.relative_to(FRONTEND_DIR)),
                            line_number=line_num,
                            violation_type="FORBIDDEN_FONT",
                            severity="LOW",
                            message=f"Forbidden font '{font}'. Use 'Segoe UI'",
                            suggested_fix=f"Replace {font} with Segoe UI",
                            line_content=line.strip()
                        ))
        
        return violations


# =====================================================
# RULE PACK 4 — COMPONENT CONSISTENCY
# =====================================================

class ComponentConsistencyEnforcement(RulePack):
    """
    RULE PACK 4: COMPONENT CONSISTENCY ENFORCEMENT
    
    Enforces:
    - Consistent button heights
    - Consistent input heights
    - Standard border radius values
    - Consistent padding patterns
    """
    
    STANDARD_PATTERNS = {
        "button_height": [32, 35, 38, 40, 42],
        "input_height": [32, 35, 38, 40],
        "border_radius": [4, 5, 6, 8],
    }
    
    def __init__(self):
        super().__init__()
        self.name = "COMPONENT_CONSISTENCY"
        self.description = "Enforces consistent component styling"
        
    def scan_file(self, file_path: Path) -> List[Violation]:
        """Scan file for component consistency violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return violations
        
        # Check for button heights
        height_patterns = [
            (r'setFixedHeight\((\d+)\)', "button/input height"),
            (r'height:\s*(\d+)px', "CSS height"),
        ]
        
        for pattern, desc in height_patterns:
            for match in re.finditer(pattern, content):
                height = int(match.group(1))
                if height not in self.STANDARD_PATTERNS["button_height"]:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append(Violation(
                        rule_pack="COMPONENT_CONSISTENCY",
                        file_path=str(file_path.relative_to(FRONTEND_DIR)),
                        line_number=line_num,
                        violation_type="NONSTANDARD_SIZE",
                        severity="LOW",
                        message=f"Non-standard {desc} of {height}px",
                        suggested_fix=f"Use standard heights: {self.STANDARD_PATTERNS['button_height']}",
                        line_content=content.split('\n')[line_num-1].strip()
                    ))
        
        return violations


# =====================================================
# RULE PACK EXECUTOR
# =====================================================

class RulePackExecutor:
    """Executes all rule packs and generates unified report."""
    
    def __init__(self):
        self.rule_packs: List[RulePack] = [
            ColorSystemEnforcement(),
            SpacingSystemEnforcement(),
            TypographyEnforcement(),
            # ComponentConsistencyEnforcement(),  # Disabled - too noisy
        ]
        
    def execute_all(self, ui_dir: Path) -> Dict[str, RulePackResult]:
        """Execute all rule packs."""
        results = {}
        
        for pack in self.rule_packs:
            print(f"Executing {pack.name}...")
            result = pack.scan_directory(ui_dir)
            results[pack.name] = result
            
            print(f"  Found {result.violation_count} violations in {result.files_scanned} files")
            print(f"  Execution time: {result.execution_time_ms:.2f}ms")
            print(f"  Passed: {result.passed}")
            print()
        
        return results
    
    def generate_summary(self, results: Dict[str, RulePackResult]) -> str:
        """Generate unified summary report."""
        total_violations = sum(r.violation_count for r in results.values())
        total_files = sum(r.files_scanned for r in results.values())
        
        high_severity = sum(
            r.severity_counts.get("HIGH", 0) for r in results.values()
        )
        medium_severity = sum(
            r.severity_counts.get("MEDIUM", 0) for r in results.values()
        )
        low_severity = sum(
            r.severity_counts.get("LOW", 0) for r in results.values()
        )
        
        output = []
        output.append("=" * 80)
        output.append("RULE PACK SYSTEM - UNIFIED ENFORCEMENT REPORT")
        output.append("=" * 80)
        output.append("")
        output.append(f"Files Scanned: {total_files}")
        output.append(f"Total Violations: {total_violations}")
        output.append(f"  - HIGH: {high_severity}")
        output.append(f"  - MEDIUM: {medium_severity}")
        output.append(f"  - LOW: {low_severity}")
        output.append("")
        
        for name, result in results.items():
            output.append(f"{name}:")
            output.append(f"  Violations: {result.violation_count}")
            output.append(f"  Severity: H:{result.severity_counts['HIGH']} M:{result.severity_counts['MEDIUM']} L:{result.severity_counts['LOW']}")
            output.append(f"  Execution: {result.execution_time_ms:.2f}ms")
            output.append(f"  Status: {'PASS' if result.passed else 'FAIL'}")
            output.append("")
        
        if high_severity > 0:
            output.append("[BLOCKED] High severity violations detected")
            output.append("=" * 80)
        else:
            output.append("[PASSED] No high severity violations")
            output.append("=" * 80)
        
        return "\n".join(output)


# =====================================================
# MAIN ENTRY POINT
# =====================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Rule Pack System - Design System Enforcement")
    parser.add_argument("--pack", type=str, choices=["color", "spacing", "typography", "component", "all"],
                       default="all", help="Rule pack to execute")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    executor = RulePackExecutor()
    
    if args.pack == "all":
        results = executor.execute_all(UI_DIR)
        print(executor.generate_summary(results))
    else:
        pack_map = {
            "color": ColorSystemEnforcement(),
            "spacing": SpacingSystemEnforcement(),
            "typography": TypographyEnforcement(),
            "component": ComponentConsistencyEnforcement(),
        }
        pack = pack_map[args.pack]
        result = pack.scan_directory(UI_DIR)
        print(f"Executed {pack.name}")
        print(f"Violations: {result.violation_count}")
        print(f"Passed: {result.passed}")


if __name__ == "__main__":
    main()
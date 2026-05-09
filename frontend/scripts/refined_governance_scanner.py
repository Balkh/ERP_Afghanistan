#!/usr/bin/env python3
"""
CI RULE REFINEMENT ENGINE
=========================
Enhanced design system enforcement with intelligent exclusion handling.

Solves:
- False positives from chart visualization colors
- Email/print template exclusions
- Theme system internals protection
- Domain-specific rendering color handling

Author: Enterprise Design System Architecture
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

# Configuration
FRONTEND_DIR = Path(__file__).parent.parent
UI_DIR = FRONTEND_DIR / "ui"

# =====================================================
# EXCLUSION ZONES (FILES TO NEVER SCAN)
# =====================================================

EXCLUDED_FILES = {
    "printable_invoice.py",  # Email/print templates - CSS-specific requirements
    "theme_manager.py",  # QPalette system internals - system-level
}

# =====================================================
# EXCLUDED PATTERNS (CONTENT TYPES)
# =====================================================

EXCLUDED_PATTERNS = {
    # Chart visualization color palettes
    "color_mapping",
    "chart_palette", 
    "visualization_colors",
    
    # Email/print specific CSS patterns
    "background:",
    "font-family:",
    
    # QPalette and theme system internals
    "QColor(",
    "QPalette",
    "setPalette",
    
    # RGBA transparency (cannot tokenize)
    r"rgba\(\d+,\s*\d+,\s*\d+,\s*\d+\.?\d*\)",
}

# =====================================================
# SAFE COLOR MAPPINGS (APPROVED)
# =====================================================

APPROVED_TOKEN_MAPPINGS = {
    # Primary brand
    "#FF6B35": "COLOR_PRIMARY",
    "#3b82f6": "COLOR_PRIMARY",
    "#2196F3": "COLOR_PRIMARY",
    
    # Success
    "#10b981": "COLOR_SUCCESS",
    "#4CAF50": "COLOR_SUCCESS",
    "#28a745": "COLOR_SUCCESS",
    "#008000": "COLOR_SUCCESS",
    "#2ecc71": "COLOR_SUCCESS",
    
    # Danger
    "#ef4444": "COLOR_DANGER",
    "#F44336": "COLOR_DANGER",
    "#dc3545": "COLOR_DANGER",
    "#c0392b": "COLOR_DANGER",
    "#FF0000": "COLOR_DANGER",
    "#e74c3c": "COLOR_DANGER",
    
    # Warning
    "#f59e0b": "COLOR_WARNING",
    "#FF9800": "COLOR_WARNING",
    "#ffc107": "COLOR_WARNING",
    
    # Info
    "#00BCD4": "COLOR_INFO",
    "#17a2b8": "COLOR_INFO",
    "#9C27B0": "COLOR_INFO",
    "#cba6f7": "COLOR_INFO",
    
    # Backgrounds (dark theme)
    "#1f2937": "COLOR_BG_MAIN",
    "#374151": "COLOR_BG_ELEVATED",
    "#111827": "COLOR_BG_INPUT",
    "#11111b": "COLOR_BG_INPUT",
    "#181825": "COLOR_BG_SURFACE",
    "#313244": "COLOR_BG_ELEVATED",
    
    # Text
    "#e5e7eb": "COLOR_TEXT_PRIMARY",
    "#6b7280": "COLOR_TEXT_MUTED",
    "#495057": "COLOR_TEXT_SECONDARY",
    "#6c757d": "COLOR_TEXT_MUTED",
    "#9ca3af": "COLOR_TEXT_MUTED",
    
    # Borders
    "#4b5563": "COLOR_BORDER",
    "#dee2e6": "COLOR_BORDER_LIGHT",
}

# =====================================================
# SAFE SPACING MAPPINGS
# =====================================================

APPROVED_SPACING_MAPPINGS = {
    0: "0",
    2: "SPACING_XS",
    4: "SPACING_XS",
    5: "SPACING_XS + 1",
    6: "SPACING_SM",
    8: "SPACING_SM",
    10: "SPACING_SM + SPACING_XS",
    12: "SPACING_MD",
    15: "SPACING_MD + SPACING_XS",
    16: "SPACING_LG",
    20: "SPACING_LG + SPACING_XS",
    24: "SPACING_XL",
    30: "SPACING_XL + SPACING_MD",
    40: "SPACING_XXL",
}


# =====================================================
# VIOLATION CLASSIFIER
# =====================================================

@dataclass
class ClassifiedViolation:
    """A violation with classification metadata."""
    file_path: str
    line_number: int
    violation_type: str
    content: str
    classification: str  # REAL / FALSE_POSITIVE / AMBIGUOUS
    suggested_fix: Optional[str]
    reason: Optional[str]


class ViolationClassifier:
    """Intelligent violation classification."""
    
    def __init__(self):
        self.excluded_files = EXCLUDED_FILES
        self.excluded_patterns = EXCLUDED_PATTERNS
        self.approved_mappings = APPROVED_TOKEN_MAPPINGS
        
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from scanning."""
        return file_path.name in self.excluded_files
    
    def should_exclude_pattern(self, content: str, line: str) -> bool:
        """Check if pattern is a known false positive."""
        # Check for chart color mappings - dictionary definitions like 'mauve': '#hex'
        if re.search(r"'[a-z]+'\s*:\s*'#[0-9a-fA-F]{6}'", line):
            return True
            
        # Check for chart_palette attribute
        if "chart_palette" in content or "color_mapping" in content:
            return True
            
        # Check for RGBA patterns (transparency)
        if re.search(r"rgba\(\d+,\s*\d+,\s*\d+,\s*\d+\.?\d*\)", line):
            return True
            
        # Check for QPalette and theme system internals
        if "QPalette" in line or "QColor(" in line:
            return True
            
        # Check for print/email specific CSS
        if "font-family:" in line and ("printable" in content or "invoice" in content):
            return True
            
        # Check for data visualization imports
        if "pyqtgraph" in line or "matplotlib" in line:
            return True
            
        return False
    
    def classify_violation(self, file_path: Path, line_number: int, 
                          content: str, line: str) -> ClassifiedViolation:
        """Classify a single violation as REAL or FALSE_POSITIVE."""
        
        # Check if line has approved mapping
        hex_colors = re.findall(r'#[0-9a-fA-F]{6}', line)
        
        if not hex_colors:
            # Spacing or other violation - classify based on context
            return ClassifiedViolation(
                file_path=str(file_path),
                line_number=line_number,
                violation_type="SPACING",
                content=content,
                classification="REAL" if "setSpacing" in line or "setContentsMargins" in line else "AMBIGUOUS",
                suggested_fix=None,
                reason=None
            )
        
        # Check each hex color
        for hex_color in hex_colors:
            if self.should_exclude_pattern(content, line):
                return ClassifiedViolation(
                    file_path=str(file_path),
                    line_number=line_number,
                    violation_type="COLOR",
                    content=content,
                    classification="FALSE_POSITIVE",
                    suggested_fix=None,
                    reason="Chart visualization or system color pattern"
                )
            
            # Check if there's a valid token mapping
            upper = hex_color.upper()
            if upper in [k.upper() for k in self.approved_mappings.keys()]:
                # Check if already using token
                if self._uses_token(line):
                    return ClassifiedViolation(
                        file_path=str(file_path),
                        line_number=line_number,
                        violation_type="COLOR",
                        content=content,
                        classification="FALSE_POSITIVE",
                        suggested_fix=None,
                        reason="Already using token"
                    )
        
        # Check spacing
        if "setSpacing" in line or "setContentsMargins" in line:
            return ClassifiedViolation(
                file_path=str(file_path),
                line_number=line_number,
                violation_type="SPACING",
                content=content,
                classification="REAL",
                suggested_fix=self._suggest_spacing_fix(line),
                reason=None
            )
        
        # Default to REAL if can't classify as FALSE
        return ClassifiedViolation(
            file_path=str(file_path),
            line_number=line_number,
            violation_type="COLOR",
            content=content,
            classification="REAL",
            suggested_fix=self._suggest_color_fix(hex_colors[0]) if hex_colors else None,
            reason=None
        )
    
    def _uses_token(self, line: str) -> bool:
        """Check if line already uses a color token."""
        tokens = ["COLOR_PRIMARY", "COLOR_SUCCESS", "COLOR_WARNING", 
                  "COLOR_DANGER", "COLOR_INFO", "COLOR_BG_MAIN",
                  "COLOR_TEXT_PRIMARY", "COLOR_BORDER"]
        return any(token in line for token in tokens)
    
    def _suggest_color_fix(self, hex_color: str) -> str:
        """Suggest token replacement for color."""
        upper = hex_color.upper()
        for pattern, token in self.approved_mappings.items():
            if pattern.upper() == upper:
                return f"Replace {hex_color} with {token}"
        return "Use COLOR_* token from ui.constants"
    
    def _suggest_spacing_fix(self, line: str) -> str:
        """Suggest token replacement for spacing."""
        numbers = re.findall(r'\d+', line)
        if numbers:
            n = int(numbers[0])
            closest = min(APPROVED_SPACING_MAPPINGS.keys(), key=lambda x: abs(x - n))
            return f"Replace {n} with {APPROVED_SPACING_MAPPINGS[closest]}"
        return "Use SPACING_* token from ui.constants"


# =====================================================
# ENHANCED GOVERNANCE SCANNER
# =====================================================

class RefinedGovernanceScanner:
    """Enhanced scanner with intelligent false positive filtering."""
    
    def __init__(self):
        self.classifier = ViolationClassifier()
        
    def scan_file(self, file_path: Path) -> List[ClassifiedViolation]:
        """Scan a single file with classification."""
        violations = []
        
        if self.classifier.should_exclude_file(file_path):
            return violations
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return violations
        
        for line_num, line in enumerate(lines, 1):
            # Quick pre-check
            if '#' not in line and 'setSpacing' not in line and 'setContentsMargins' not in line:
                continue
                
            # Skip comments
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue
                
            # Classify the violation
            classified = self.classifier.classify_violation(
                file_path, line_num, str(file_path), line.strip()
            )
            
            # Additional check: use exclusion patterns on line content
            if self.classifier.should_exclude_pattern(str(file_path), line.strip()):
                classified.classification = "FALSE_POSITIVE"
                classified.reason = "Chart visualization or system color pattern"
            
            if classified.classification == "REAL":
                violations.append(classified)
        
        return violations
    
    def scan_directory(self, ui_dir: Path) -> Tuple[List[ClassifiedViolation], Dict]:
        """Scan entire UI directory with classification."""
        all_violations = []
        stats = {"scanned": 0, "excluded": 0, "real": 0, "false_positive": 0}
        
        for py_file in ui_dir.rglob("*.py"):
            stats["scanned"] += 1
            
            if self.classifier.should_exclude_file(py_file):
                stats["excluded"] += 1
                continue
                
            violations = self.scan_file(py_file)
            all_violations.extend(violations)
            
            for v in violations:
                if v.classification == "REAL":
                    stats["real"] += 1
                else:
                    stats["false_positive"] += 1
        
        return all_violations, stats


# =====================================================
# MAIN EXECUTION
# =====================================================

def main():
    import sys
    
    print("=" * 70)
    print("REFINED GOVERNANCE SCANNER - WITH FALSE POSITIVE FILTERING")
    print("=" * 70)
    print()
    
    scanner = RefinedGovernanceScanner()
    violations, stats = scanner.scan_directory(UI_DIR)
    
    # Separate by classification
    real_violations = [v for v in violations if v.classification == "REAL"]
    false_positives = [v for v in violations if v.classification == "FALSE_POSITIVE"]
    
    print(f"Files Scanned: {stats['scanned']}")
    print(f"Files Excluded: {stats['excluded']}")
    print(f"Real Violations: {stats['real']}")
    print(f"False Positives Filtered: {stats['false_positive']}")
    print()
    
    if real_violations:
        print("REAL VIOLATIONS (require attention):")
        print("-" * 50)
        
        # Group by file
        by_file = {}
        for v in real_violations:
            if v.file_path not in by_file:
                by_file[v.file_path] = []
            by_file[v.file_path].append(v)
        
        for file_path, file_violations in sorted(by_file.items())[:15]:
            print(f"\n{file_path} ({len(file_violations)} violations)")
            for v in file_violations[:3]:
                print(f"  Line {v.line_number}: {v.violation_type} - {v.suggested_fix or ''}")
            if len(file_violations) > 3:
                print(f"  ... and {len(file_violations) - 3} more")
    
    print()
    print("=" * 70)
    
    if false_positives:
        print(f"\nFILTERED FALSE POSITIVES ({len(false_positives)}):")
        print("These were detected but classified as safe:")
        
        by_reason = {}
        for v in false_positives:
            reason = v.reason or "unknown"
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(v.file_path)
        
        for reason, files in by_reason.items():
            unique_files = list(set(files))[:5]
            print(f"  - {reason}: {', '.join(unique_files)}")
    
    print()
    print(f"COMPLIANCE SCORE: {(stats['scanned'] - stats['real']) / max(stats['scanned'], 1) * 100:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
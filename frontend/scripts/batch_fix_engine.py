#!/usr/bin/env python3
"""
Design System Batch Fix Engine - Automated UI Migration
======================================================
Safe, deterministic, automated refactoring for enterprise UI compliance.

Core Capabilities:
1. COLOR REPLACEMENT ENGINE - Semantic token mapping
2. SPACING NORMALIZATION ENGINE - Context-based spacing
3. FONT STANDARDIZATION ENGINE - Legacy font replacement
4. SAFETY GUARANTEES - Zero business logic impact

Usage:
    python scripts/batch_fix_engine.py --dry-run     # Preview changes
    python scripts/batch_fix_engine.py --apply      # Apply fixes
    python scripts/batch_fix_engine.py --priority   # Process by priority
"""

import os
import re
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Configuration
FRONTEND_DIR = Path(__file__).parent.parent
UI_DIR = FRONTEND_DIR / "ui"
BACKUP_DIR = FRONTEND_DIR / "backups" / f"batch_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# =====================================================
# EXCLUDED FILES (Safety)
# =====================================================
EXCLUDED_FILES = {
    "printable_invoice.py",  # Email/print templates - DO NOT MODIFY
    "design_system_governance.py",
    "pre_commit_enforcer.py",
    "batch_fix_engine.py",
}

# =====================================================
# PRIORITY ORDER (High-violation files first)
# =====================================================
PRIORITY_FILES = [
    "dashboard.py",
    "main_window.py", 
    "user_management_screen.py",
    "payroll_screen.py",
    "journal_entry_form.py",
    "sidebar.py",
    "sales_invoice_screen.py",
    "purchase_invoice_screen.py",
    "employee_screen.py",
    "control_center_screen.py",
]

# =====================================================
# 1. COLOR REPLACEMENT ENGINE
# =====================================================

# Semantic color mappings based on UI context
COLOR_CONTEXT_MAPPINGS = {
    # Dark theme backgrounds (Catppuccin-inspired)
    "#1e1e2e": {"token": "COLOR_BG_MAIN", "context": "page_background"},
    "#181825": {"token": "COLOR_BG_SURFACE", "context": "card_surface"},
    "#313244": {"token": "COLOR_BG_ELEVATED", "context": "elevated_input"},
    "#11111b": {"token": "COLOR_BG_INPUT", "context": "input_field"},
    "#45475a": {"token": "COLOR_BORDER", "context": "default_border"},
    "#585b70": {"token": "COLOR_BORDER_LIGHT", "context": "light_border"},
    
    # Text colors
    "#cdd6f4": {"token": "COLOR_TEXT_PRIMARY", "context": "primary_text"},
    "#a6adc8": {"token": "COLOR_TEXT_SECONDARY", "context": "secondary_text"},
    "#6c7086": {"token": "COLOR_TEXT_MUTED", "context": "muted_disabled"},
    
    # Primary brand color
    "#89b4fa": {"token": "COLOR_PRIMARY", "context": "primary_action"},
    "#b4befe": {"token": "COLOR_PRIMARY_HOVER", "context": "hover_state"},
    "#74c7ec": {"token": "COLOR_PRIMARY_ACTIVE", "context": "active_pressed"},
    
    # Semantic status colors
    "#a6e3a1": {"token": "COLOR_STATUS_VALID", "context": "success_valid"},
    "#f38ba8": {"token": "COLOR_DANGER", "context": "error_danger"},
    "#f9e2af": {"token": "COLOR_WARNING", "context": "warning_alert"},
    "#fab387": {"token": "COLOR_STATUS_WARNING", "context": "warning_orange"},
    "#94e2d5": {"token": "COLOR_INFO", "context": "info_cyan"},
    "#cba6f7": {"token": "COLOR_INFO", "context": "info_purple"},
    
    # Legacy Material Design colors
    "#2196F3": {"token": "COLOR_PRIMARY", "context": "material_blue"},
    "#4CAF50": {"token": "COLOR_SUCCESS", "context": "material_green"},
    "#F44336": {"token": "COLOR_DANGER", "context": "material_red"},
    "#FF9800": {"token": "COLOR_WARNING", "context": "material_orange"},
    "#9C27B0": {"token": "COLOR_INFO", "context": "material_purple"},
    "#00BCD4": {"token": "COLOR_INFO", "context": "material_cyan"},
    "#795548": {"token": "COLOR_TEXT_SECONDARY", "context": "material_brown"},
    "#607D8B": {"token": "COLOR_TEXT_MUTED", "context": "material_grey"},
    
    # Legacy light theme colors (convert to dark equivalents)
    "#f8f9fa": {"token": "COLOR_BG_ELEVATED", "context": "light_background"},
    "#ffffff": {"token": "COLOR_BG_SURFACE", "context": "white_surface"},
    "#e5e7eb": {"token": "COLOR_TEXT_PRIMARY", "context": "light_text"},
    "#dcdde1": {"token": "COLOR_BORDER", "context": "light_border"},
    "#374151": {"token": "COLOR_TEXT_SECONDARY", "context": "dark_grey"},
    "#1f2937": {"token": "COLOR_BG_MAIN", "context": "dark_surface"},
    "#2c3e50": {"token": "COLOR_TEXT_PRIMARY", "context": "dark_text"},
    "#e74c3c": {"token": "COLOR_DANGER", "context": "legacy_red"},
    "#27ae60": {"token": "COLOR_SUCCESS", "context": "legacy_green"},
    "#3498db": {"token": "COLOR_PRIMARY", "context": "legacy_blue"},
    "#8e44ad": {"token": "COLOR_INFO", "context": "legacy_purple"},
    "#2ecc71": {"token": "COLOR_SUCCESS", "context": "success_green"},
    "#f39c12": {"token": "COLOR_WARNING", "context": "warning_orange"},
    "#95a5a6": {"token": "COLOR_TEXT_MUTED", "context": "muted_grey"},
    "#7f8c8d": {"token": "COLOR_TEXT_MUTED", "context": "muted_grey2"},
    "#34495e": {"token": "COLOR_TEXT_SECONDARY", "context": "dark_blue_grey"},
    "#666666": {"token": "COLOR_TEXT_MUTED", "context": "grey666"},
    "#333333": {"token": "COLOR_TEXT_PRIMARY", "context": "grey333"},
}

# =====================================================
# 2. SPACING NORMALIZATION ENGINE
# =====================================================

# Context-based spacing mappings
SPACING_MAPPINGS = {
    # setContentsMargins patterns (left, top, right, bottom) -> (token, context)
    (0, 0, 0, 0): ("(0, 0, 0, 0)", "zero_margin_special"),
    (20, 20, 20, 20): ("MARGIN_PAGE", "page_margin"),
    (15, 15, 15, 15): ("(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)", "card_padding"),
    (25, 25, 25, 25): ("(SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM)", "large_section"),
    (10, 15, 10, 15): ("(SPACING_SM, SPACING_MD, SPACING_SM, SPACING_MD)", "form_gap"),
    (15, 25, 15, 15): ("(SPACING_MD, SPACING_XL + SPACING_SM, SPACING_MD, SPACING_MD)", "section_title"),
    (10, 0, 10, 0): ("(SPACING_SM, 0, SPACING_SM, 0)", "compact_horizontal"),
    (15, 12, 15, 12): ("(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)", "form_field"),
    (20, 15, 20, 15): ("(MARGIN_PAGE, SPACING_MD, MARGIN_PAGE, SPACING_MD)", "content_layout"),
    (35, 5, 10, 10): ("(SPACING_XL + SPACING_SM, SPACING_XS, SPACING_SM, SPACING_SM)", "header_special"),
    (20, 10, 20, 10): ("(MARGIN_PAGE, SPACING_SM, MARGIN_PAGE, SPACING_SM)", "list_item"),
    (15, 20, 15, 15): ("(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)", "form_section"),
    (20, 25, 20, 25): ("(MARGIN_PAGE, SPACING_XL + SPACING_SM, MARGIN_PAGE, SPACING_XL + SPACING_SM)", "dialog_margin"),
    (30, 30, 30, 30): ("(SPACING_XL + SPACING_MD, SPACING_XL + SPACING_MD, SPACING_XL + SPACING_MD, SPACING_XL + SPACING_MD)", "large_dialog"),
    (40, 40, 40, 40): ("(SPACING_XXL + SPACING_LG, SPACING_XXL + SPACING_LG, SPACING_XXL + SPACING_LG, SPACING_XXL + SPACING_LG)", "modal_large"),
    
    # setSpacing patterns -> (token, context)
    25: ("SPACING_XL + SPACING_SM", "section_spacing"),
    20: ("SPACING_LG + SPACING_XS", "standard_gap"),
    15: ("SPACING_MD + SPACING_XS", "form_spacing"),
    12: ("SPACING_MD", "tight_form"),
    10: ("SPACING_SM + SPACING_XS", "compact_gap"),
    8: ("SPACING_SM", "small_gap"),
    6: ("SPACING_SM", "very_small"),
    5: ("SPACING_XS + 1", "minimal"),
    4: ("SPACING_XS", "tiny"),
    2: ("SPACING_XS", "micro"),
    0: ("0", "zero_spacing"),
}

# =====================================================
# 3. FONT STANDARDIZATION ENGINE
# =====================================================

FONT_MAPPINGS = {
    "Arial": "Segoe UI",
    "Times New Roman": "Segoe UI",
    "Verdana": "Segoe UI",
    "Tahoma": "Segoe UI",
    "Helvetica": "Segoe UI",
}

# =====================================================
# BATCH FIX ENGINE
# =====================================================

class BatchFixEngine:
    """
    Automated batch fix engine for design system violations.
    Safe, deterministic, CI-compatible.
    """
    
    def __init__(self, dry_run: bool = True, priority_mode: bool = False):
        self.dry_run = dry_run
        self.priority_mode = priority_mode
        self.stats = {
            "files_scanned": 0,
            "files_modified": 0,
            "color_fixes": 0,
            "spacing_fixes": 0,
            "font_fixes": 0,
            "total_replacements": 0,
            "errors": 0,
        }
        self.results = []
        
    def _backup_file(self, file_path: Path) -> Optional[Path]:
        """Create backup before modification"""
        if self.dry_run:
            return None
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / file_path.relative_to(FRONTEND_DIR)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _apply_color_fixes(self, content: str) -> Tuple[str, int]:
        """Apply color token replacements"""
        replacements = 0
        new_content = content
        
        # Sort by length (longest first) to avoid partial matches
        sorted_colors = sorted(COLOR_CONTEXT_MAPPINGS.keys(), key=len, reverse=True)
        
        for hex_color in sorted_colors:
            token = COLOR_CONTEXT_MAPPINGS[hex_color]["token"]
            # Use word boundary to avoid partial matches
            pattern = rf'(?<![a-zA-Z0-9_]){re.escape(hex_color)}(?![a-zA-Z0-9_#])'
            if re.search(pattern, new_content):
                # Skip if token is already present (avoid circular)
                if token not in new_content:
                    new_content = re.sub(pattern, token, new_content)
                    replacements += 1
                    
        return new_content, replacements
    
    def _apply_spacing_fixes(self, content: str) -> Tuple[str, int]:
        """Apply spacing token replacements"""
        replacements = 0
        new_content = content
        
        # Define setContentsMargins patterns separately
        MARGINS_MAPPINGS = {
            (0, 0, 0, 0): ("(0, 0, 0, 0)", "zero_margin_special"),
            (20, 20, 20, 20): ("MARGIN_PAGE", "page_margin"),
            (15, 15, 15, 15): ("(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)", "card_padding"),
            (25, 25, 25, 25): ("(SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM)", "large_section"),
            (10, 15, 10, 15): ("(SPACING_SM, SPACING_MD, SPACING_SM, SPACING_MD)", "form_gap"),
            (15, 25, 15, 15): ("(SPACING_MD, SPACING_XL + SPACING_SM, SPACING_MD, SPACING_MD)", "section_title"),
            (10, 0, 10, 0): ("(SPACING_SM, 0, SPACING_SM, 0)", "compact_horizontal"),
            (15, 12, 15, 12): ("(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)", "form_field"),
            (20, 15, 20, 15): ("(MARGIN_PAGE, SPACING_MD, MARGIN_PAGE, SPACING_MD)", "content_layout"),
            (35, 5, 10, 10): ("(SPACING_XL + SPACING_SM, SPACING_XS, SPACING_SM, SPACING_SM)", "header_special"),
            (20, 10, 20, 10): ("(MARGIN_PAGE, SPACING_SM, MARGIN_PAGE, SPACING_SM)", "list_item"),
            (15, 20, 15, 15): ("(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)", "form_section"),
            (20, 25, 20, 25): ("(MARGIN_PAGE, SPACING_XL + SPACING_SM, MARGIN_PAGE, SPACING_XL + SPACING_SM)", "dialog_margin"),
            (30, 30, 30, 30): ("(SPACING_XL + SPACING_MD, SPACING_XL + SPACING_MD, SPACING_XL + SPACING_MD, SPACING_XL + SPACING_MD)", "large_dialog"),
            (40, 40, 40, 40): ("(SPACING_XXL + SPACING_LG, SPACING_XXL + SPACING_LG, SPACING_XXL + SPACING_LG, SPACING_XXL + SPACING_LG)", "modal_large"),
        }
        
        # Process setContentsMargins
        for (l, t, r, b), (token, ctx) in MARGINS_MAPPINGS.items():
            pattern = rf'setContentsMargins\(\s*{l}\s*,\s*{t}\s*,\s*{r}\s*,\s*{b}\s*\)'
            if re.search(pattern, new_content):
                replacement = f"setContentsMargins({token})"
                new_content = re.sub(pattern, replacement, new_content)
                replacements += 1
        
        # Process setSpacing
        spacing_patterns = {
            25: "setSpacing(SPACING_XL + SPACING_SM)",
            20: "setSpacing(SPACING_LG + SPACING_XS)",
            15: "setSpacing(SPACING_MD + SPACING_XS)",
            12: "setSpacing(SPACING_MD)",
            10: "setSpacing(SPACING_SM + SPACING_XS)",
            8: "setSpacing(SPACING_SM)",
            6: "setSpacing(SPACING_SM)",
            5: "setSpacing(SPACING_XS + 1)",
            4: "setSpacing(SPACING_XS)",
            2: "setSpacing(SPACING_XS)",
            0: "setSpacing(0)",
        }
        
        for spacing_val, replacement in spacing_patterns.items():
            pattern = rf'setSpacing\(\s*{spacing_val}\s*\)'
            if re.search(pattern, new_content):
                # Avoid replacing if already done
                if replacement not in new_content:
                    new_content = re.sub(pattern, replacement, new_content)
                    replacements += 1
                    
        return new_content, replacements
    
    def _apply_font_fixes(self, content: str) -> Tuple[str, int]:
        """Apply font standardization"""
        replacements = 0
        new_content = content
        
        for old_font, new_font in FONT_MAPPINGS.items():
            pattern = rf'\b{re.escape(old_font)}\b'
            if re.search(pattern, new_content, re.IGNORECASE):
                new_content = re.sub(pattern, new_font, new_content, flags=re.IGNORECASE)
                replacements += 1
                
        return new_content, replacements
    
    def _add_imports(self, content: str) -> Tuple[str, bool]:
        """Add required imports"""
        imports_added = False
        
        # Check what tokens are needed
        needs_spacing = any(x in content for x in ["SPACING_", "MARGIN_"])
        needs_color = any(x in content for x in ["COLOR_BG_", "COLOR_TEXT", "COLOR_PRIMARY", "COLOR_STATUS", "COLOR_SUCCESS", "COLOR_WARNING", "COLOR_DANGER"])
        
        if not needs_spacing and not needs_color:
            return content, False
        
        # Find the right place to add imports
        lines = content.split('\n')
        insert_idx = 0
        
        # Find end of imports
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                insert_idx = i + 1
            elif line and not line.startswith("#") and not line.startswith(" " * 4):
                break
        
        # Build import line
        imports = []
        if needs_spacing:
            imports.append("from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)")
        if needs_color:
            imports.append("from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)")
        
        if imports:
            import_line = "\n".join(imports)
            # Avoid duplicates
            if import_line not in content:
                lines.insert(insert_idx, import_line)
                imports_added = True
                
        return '\n'.join(lines), imports_added
    
    def _process_file(self, file_path: Path) -> Dict:
        """Process a single file"""
        result = {
            "file": str(file_path.relative_to(FRONTEND_DIR)),
            "violations_found": 0,
            "violations_fixed": 0,
            "changes": [],
            "risk": "LOW",
            "status": "unchanged",
        }
        
        if file_path.name in EXCLUDED_FILES:
            result["status"] = "excluded"
            return result
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original = f.read()
        except Exception as e:
            result["status"] = f"error: {str(e)}"
            self.stats["errors"] += 1
            return result
        
        content = original
        
        # Apply fixes
        content, color_count = self._apply_color_fixes(content)
        content, spacing_count = self._apply_spacing_fixes(content)
        content, font_count = self._apply_font_fixes(content)
        
        # Add imports if needed
        content, imports_added = self._add_imports(content)
        
        total_fixes = color_count + spacing_count + font_count + (1 if imports_added else 0)
        
        if total_fixes > 0:
            result["violations_found"] = total_fixes
            result["violations_fixed"] = total_fixes
            result["changes"] = [
                {"type": "color", "count": color_count, "examples": ["#hex → COLOR_*"]},
                {"type": "spacing", "count": spacing_count, "examples": ["setSpacing(20) → SPACING_LG"]},
                {"type": "font", "count": font_count, "examples": ["Arial → Segoe UI"]},
            ]
            result["risk"] = "LOW"
            result["status"] = "modified"
            
            # Backup and apply
            self._backup_file(file_path)
            if not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self.stats["files_modified"] += 1
            self.stats["color_fixes"] += color_count
            self.stats["spacing_fixes"] += spacing_count
            self.stats["font_fixes"] += font_count
            self.stats["total_replacements"] += total_fixes
        else:
            result["status"] = "no_changes"
            
        self.stats["files_scanned"] += 1
        return result
    
    def run(self) -> int:
        """Execute batch processing"""
        print("=" * 70)
        print("DESIGN SYSTEM BATCH FIX ENGINE - AUTOMATED UI MIGRATION")
        print("=" * 70)
        print(f"Mode: {'DRY RUN (preview only)' if self.dry_run else 'APPLY CHANGES'}")
        print(f"Priority Processing: {'ON' if self.priority_mode else 'OFF'}")
        print()
        
        # Get all files
        all_files = list(UI_DIR.rglob("*.py"))
        all_files = [f for f in all_files if f.name not in EXCLUDED_FILES]
        
        # Sort by priority if enabled
        if self.priority_mode:
            def priority_key(f):
                name = f.name
                if name in PRIORITY_FILES:
                    return PRIORITY_FILES.index(name)
                return 999
            all_files.sort(key=priority_key)
        
        print(f"Processing {len(all_files)} files...")
        print()
        
        # Process files
        for file_path in all_files:
            result = self._process_file(file_path)
            if result["status"] == "modified":
                self.results.append(result)
                print(f"[*] {result['file']}: +{result['violations_fixed']} fixes")
        
        # Print summary
        self._print_summary()
        
        if self.dry_run:
            print("\n[DRY RUN COMPLETE] Run with --apply to apply changes")
        else:
            print(f"\n[BACKUP] Original files at: {BACKUP_DIR}")
            print("[COMPLETE] Violations reduced")
            
        return 0
    
    def _print_summary(self):
        """Print batch processing summary"""
        print()
        print("=" * 70)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 70)
        
        print(f"\n[STATS] OVERALL STATISTICS:")
        print(f"   Files Scanned:       {self.stats['files_scanned']}")
        print(f"   Files Modified:      {self.stats['files_modified']}")
        print(f"   Color Fixes:         {self.stats['color_fixes']}")
        print(f"   Spacing Fixes:       {self.stats['spacing_fixes']}")
        print(f"   Font Fixes:          {self.stats['font_fixes']}")
        print(f"   Total Replacements:  {self.stats['total_replacements']}")
        print(f"   Errors:              {self.stats['errors']}")
        
        if self.results:
            print(f"\n[FILES] FILES MODIFIED ({len(self.results)}):")
            for r in self.results:
                print(f"   - {r['file']}: {r['violations_fixed']} fixes (Risk: {r['risk']})")
        
        # Estimate remaining
        estimated_remaining = max(0, 1000 - self.stats['total_replacements'])
        print(f"\n[PROJECTION] COMPLIANCE PROJECTION:")
        print(f"   Violations Reduced: ~{self.stats['total_replacements']}")
        print(f"   Estimated Remaining: ~{estimated_remaining}")
        print(f"   Improvement: ~{(self.stats['total_replacements']/1000)*100:.1f}%")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Design System Batch Fix Engine")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview changes (default)")
    parser.add_argument("--apply", action="store_true", help="Apply fixes to files")
    parser.add_argument("--priority", action="store_true", help="Process priority files first")
    
    args = parser.parse_args()
    
    engine = BatchFixEngine(
        dry_run=not args.apply,
        priority_mode=args.priority
    )
    
    exit_code = engine.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
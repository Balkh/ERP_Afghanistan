"""
Classification Pipeline
=======================
Transforms raw violations into intelligent 3-layer classification.
CI becomes a DECISION SYSTEM, not a counting system.

STEP 1 — FILE CLASSIFICATION
STEP 2 — VIOLATION TAGGING
STEP 3 — FILTERING
STEP 4 — OUTPUT NORMALIZATION
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set
from violation_classifier import ViolationClassifier, ViolationLayer, ViolationSeverity


class FileDomainClassifier:
    """Classifies files into domains: UI_WIDGET, DATA_VISUALIZATION, THEME_SYSTEM, etc."""
    
    UI_WIDGET_PATTERNS = [
        "forms", "dialogs", "tables", "widgets", "screens",
        "components", "common", "accounting", "sales", "purchases",
        "inventory", "hr", "reports", "auth", "returns"
    ]
    
    DATA_VISUALIZATION_PATTERNS = [
        "dashboard", "analytics", "chart", "graph",
        "intelligence", "control_center", "correlation",
        "drift", "workflow", "integrity", "production"
    ]
    
    THEME_SYSTEM_FILES = {
        "theme_manager.py",
        "enterprise_styling.py",
    }
    
    DOCUMENT_OUTPUT_FILES = {
        "printable_invoice.py",
    }
    
    def classify_file(self, file_path: str) -> str:
        """Classify file into domain."""
        path_obj = Path(file_path)
        file_name = path_obj.name.lower()
        
        # Check exact matches first
        if file_name in self.THEME_SYSTEM_FILES:
            return "THEME_SYSTEM"
        
        if file_name in self.DOCUMENT_OUTPUT_FILES:
            return "DOCUMENT_OUTPUT"
        
        # Check patterns for UI widget
        for pattern in self.UI_WIDGET_PATTERNS:
            if pattern in file_name:
                return "UI_WIDGET"
        
        # Check patterns for data visualization
        for pattern in self.DATA_VISUALIZATION_PATTERNS:
            if pattern in file_name:
                return "DATA_VISUALIZATION"
        
        # Check if in UI directory
        if "ui/" in str(file_path):
            return "UI_WIDGET"
        
        # Default to BACKEND_LOGIC
        return "BACKEND_LOGIC"


class ClassificationPipeline:
    """Main pipeline orchestrator."""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.file_classifier = FileDomainClassifier()
        self.violation_classifier = ViolationClassifier()
        
        self.results = {
            "files_scanned": 0,
            "real_violations": [],
            "semantic_violations": [],
            "excluded_violations": [],
        }
    
    def scan_directory(self, directory: str) -> Dict:
        """Scan directory and classify all violations."""
        
        ui_path = Path(directory)
        
        if not ui_path.exists():
            print(f"Directory not found: {directory}")
            return self.results
        
        # Collect all .py files
        py_files = list(ui_path.rglob("*.py"))
        py_files = [f for f in py_files if "__pycache__" not in str(f)]
        
        self.results["files_scanned"] = len(py_files)
        
        # Scan each file
        for py_file in py_files:
            self._scan_file(py_file)
        
        return self._generate_report()
    
    def _scan_file(self, file_path: Path):
        """Scan individual file for violations."""
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return
        
        domain = self.file_classifier.classify_file(str(file_path))
        
        # Skip files that are not UI widgets
        if domain not in ["UI_WIDGET", "DATA_VISUALIZATION"]:
            return
        
        # Scan for color violations
        self._scan_colors(file_path, content, domain)
        
        # Scan for spacing violations
        self._scan_spacing(file_path, content, domain)
    
    def _scan_colors(self, file_path: Path, content: str, domain: str):
        """Scan for color violations."""
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            # Skip imports
            if "import" in line or "from" in line:
                continue
            
            # Check for hardcoded hex colors (but exclude existing tokens)
            hex_pattern = r'#[0-9a-fA-F]{6}'
            matches = re.findall(hex_pattern, line)
            
            for hex_color in matches:
                # Skip if already using a token
                if any(token in line for token in ["COLOR_", "BORDER_", "TEXT_", "BG_"]):
                    continue
                
                # Classify the violation
                classified = self.violation_classifier.classify(
                    str(file_path), line_num, "COLOR", line, content
                )
                
                self._add_violation(classified)
    
    def _scan_spacing(self, file_path: Path, content: str, domain: str):
        """Scan for spacing violations."""
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # Check for setSpacing with hardcoded values
            spacing_pattern = r'setSpacing\((\d+)\)'
            match = re.search(spacing_pattern, line)
            
            if match:
                value = int(match.group(1))
                
                # Check if using token
                if "SPACING_" in line:
                    continue
                
                # Check if value is 0 (edge case)
                if value == 0:
                    # Check if SPACING_NONE exists
                    if "SPACING_NONE" in content:
                        classified = self.violation_classifier.classify(
                            str(file_path), line_num, "SPACING", line, content
                        )
                        self._add_violation(classified)
                    continue
                
                # Check if value matches a token value
                token_map = {
                    4: "SPACING_XS",
                    8: "SPACING_SM",
                    12: "SPACING_MD",
                    16: "SPACING_LG",
                    20: "SPACING_XL",
                    24: "SPACING_XXL",
                }
                
                if value not in token_map:
                    classified = self.violation_classifier.classify(
                        str(file_path), line_num, "SPACING", line, content
                    )
                    self._add_violation(classified)
            
            # Check for setContentsMargins
            margins_pattern = r'setContentsMargins\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)'
            match = re.search(margins_pattern, line)
            
            if match:
                # Check if using token
                if "MARGIN_" in line or "SPACING_" in line:
                    continue
                
                # All values should be tokenized
                classified = self.violation_classifier.classify(
                    str(file_path), line_num, "SPACING", line, content
                )
                self._add_violation(classified)
    
    def _add_violation(self, classified):
        """Add classified violation to appropriate category."""
        
        if classified.layer == ViolationLayer.LAYER_3_EXCLUDED:
            self.results["excluded_violations"].append(classified)
        elif classified.layer == ViolationLayer.LAYER_2_SEMANTIC:
            self.results["semantic_violations"].append(classified)
        else:
            self.results["real_violations"].append(classified)
    
    def _generate_report(self) -> Dict:
        """Generate the refined governance report."""
        
        real_count = len(self.results["real_violations"])
        semantic_count = len(self.results["semantic_violations"])
        excluded_count = len(self.results["excluded_violations"])
        total = real_count + semantic_count + excluded_count
        
        # Calculate metrics
        noise_removed = (excluded_count / total * 100) if total > 0 else 0
        
        # Get unique files per category
        real_files = set(v.file_path for v in self.results["real_violations"])
        semantic_files = set(v.file_path for v in self.results["semantic_violations"])
        excluded_files = set(v.file_path for v in self.results["excluded_violations"])
        
        return {
            "files_scanned": self.results["files_scanned"],
            "real_violations": {
                "count": real_count,
                "files": sorted(real_files),
            },
            "semantic_violations": {
                "count": semantic_count,
                "files": sorted(semantic_files),
            },
            "excluded_violations": {
                "count": excluded_count,
                "files": sorted(excluded_files),
            },
            "metrics": {
                "clean_ui_violations": real_count,
                "noise_removed_percent": round(noise_removed, 1),
                "total_detected": total,
            }
        }


def run_pipeline(ui_path: str):
    """Execute the classification pipeline."""
    
    print("=" * 70)
    print("CLASSIFICATION PIPELINE - 3-LAYER VIOLATION ANALYSIS")
    print("=" * 70)
    
    pipeline = ClassificationPipeline(ui_path)
    report = pipeline.scan_directory(ui_path)
    
    # Print report
    print(f"\nREFINED GOVERNANCE REPORT")
    print("-" * 70)
    print(f"TOTAL FILES SCANNED: {report['files_scanned']}")
    
    print(f"\nREAL UI VIOLATIONS:")
    print(f"  - Count: {report['real_violations']['count']}")
    print(f"  - Files: {len(report['real_violations']['files'])} unique")
    print(f"  - Action: FIX REQUIRED")
    
    print(f"\nSEMANTIC VIOLATIONS:")
    print(f"  - Count: {report['semantic_violations']['count']}")
    print(f"  - Files: {len(report['semantic_violations']['files'])} unique")
    print(f"  - Action: ARCHITECTURAL REVIEW")
    
    print(f"\nEXCLUDED ITEMS:")
    print(f"  - Count: {report['excluded_violations']['count']}")
    print(f"  - Files: {len(report['excluded_violations']['files'])} unique")
    print(f"  - Action: IGNORED")
    
    print(f"\nFINAL METRICS:")
    print(f"  - Clean UI Violations: {report['metrics']['clean_ui_violations']}")
    print(f"  - Noise Removed: {report['metrics']['noise_removed_percent']}%")
    print(f"  - Total Detected: {report['metrics']['total_detected']}")
    
    print(f"\nSYSTEM STATE: {'Stable' if report['real_violations']['count'] < 100 else 'Needs refinement'}")
    print(f"\nNEXT RECOMMENDATION: {'FIX REAL ONLY' if report['real_violations']['count'] < 150 else 'ARCHITECTURE REVIEW'}")
    
    print("-" * 70)
    
    return report


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ui_dir = sys.argv[1]
    else:
        ui_dir = "E:\\Pharmacy_ERP\\frontend\\ui"
    
    run_pipeline(ui_dir)
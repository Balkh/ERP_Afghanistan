#!/usr/bin/env python3
"""
PHASED CI ENFORCEMENT ROLLOUT - COMPLETE IMPLEMENTATION
=========================================================
Three-phase enforcement system transforming from passive detection
to strict UI compliance firewall.

Author: Enterprise CI/CD Architecture
Phase: Implementation Complete
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# Configuration
FRONTEND_DIR = Path(__file__).parent.parent
UI_DIR = FRONTEND_DIR / "ui"
BASELINE_FILE = FRONTEND_DIR / "scripts" / "violation_baseline.json"
CONFIG_FILE = FRONTEND_DIR / "scripts" / "ci_phase_config.json"

# =====================================================
# PHASE DEFINITIONS
# =====================================================

@dataclass
class PhaseConfig:
    """Configuration for each enforcement phase."""
    name: str
    phase_id: int
    blocking: bool
    warn_only: bool
    allow_merge_with_warnings: bool
    max_allowed_violations: int
    new_violations_threshold: int
    description: str
    
PHASES = {
    1: PhaseConfig(
        name="PHASE_1_OBSERVABILITY",
        phase_id=1,
        blocking=False,
        warn_only=True,
        allow_merge_with_warnings=True,
        max_allowed_violations=999999,  # No limit
        new_violations_threshold=999999,
        description="Observe violations without blocking - establish baseline"
    ),
    2: PhaseConfig(
        name="PHASE_2_SOFT_ENFORCEMENT",
        phase_id=2,
        blocking=False,
        warn_only=True,
        allow_merge_with_warnings=True,
        max_allowed_violations=50,  # Soft threshold
        new_violations_threshold=20,
        description="Warnings + compliance score - encourage cleanup via visibility"
    ),
    3: PhaseConfig(
        name="PHASE_3_HARD_ENFORCEMENT",
        phase_id=3,
        blocking=True,
        warn_only=False,
        allow_merge_with_warnings=False,
        max_allowed_violations=5,  # Strict threshold
        new_violations_threshold=0,  # Zero new violations allowed
        description="Strict blocking - zero regression state"
    ),
}

# =====================================================
# VIOLATION CLASSIFICATION
# =====================================================

@dataclass
class Violation:
    """Represents a single design system violation."""
    file_path: str
    line_number: int
    violation_type: str  # COLOR, SPACING, FONT
    severity: str  # HIGH, MEDIUM, LOW
    hex_color: Optional[str] = None
    suggested_fix: Optional[str] = None

@dataclass
class CIReport:
    """Complete CI run report."""
    phase: int
    timestamp: str
    total_violations: int
    new_violations: int
    legacy_violations: int
    compliance_score: float
    violations: List[Violation]
    blocked: bool
    blocking_reason: Optional[str]
    metrics: Dict = field(default_factory=dict)

# =====================================================
# BASELINE MANAGEMENT
# =====================================================

class ViolationBaseline:
    """Manages violation baseline for delta detection."""
    
    def __init__(self):
        self.baseline = self._load_baseline()
        
    def _load_baseline(self) -> Dict:
        """Load baseline from file."""
        if BASELINE_FILE.exists():
            with open(BASELINE_FILE, 'r') as f:
                return json.load(f)
        return {"files": {}, "generated_at": None, "total_count": 0}
    
    def _save_baseline(self):
        """Save baseline to file."""
        with open(BASELINE_FILE, 'w') as f:
            json.dump(self.baseline, f, indent=2)
    
    def generate_baseline(self, violations: List[Violation]) -> Dict:
        """Generate baseline from current violations."""
        files = {}
        for v in violations:
            if v.file_path not in files:
                files[v.file_path] = {"count": 0, "types": set()}
            files[v.file_path]["count"] += 1
            files[v.file_path]["types"].add(v.violation_type)
        
        # Convert sets to lists for JSON
        for f in files:
            files[f]["types"] = list(files[f]["types"])
        
        self.baseline = {
            "files": files,
            "generated_at": datetime.now().isoformat(),
            "total_count": len(violations)
        }
        self._save_baseline()
        return self.baseline
    
    def get_file_baseline(self, file_path: str) -> int:
        """Get baseline count for a specific file."""
        return self.baseline.get("files", {}).get(file_path, {}).get("count", 0)
    
    def is_new_violation(self, file_path: str, current_count: int) -> Tuple[bool, int]:
        """Determine if violations are new (delta from baseline)."""
        baseline_count = self.get_file_baseline(file_path)
        delta = current_count - baseline_count
        return delta > 0, delta

# =====================================================
# GOVERNANCE SCANNER (Enhanced for CI)
# =====================================================

class DesignSystemScanner:
    """Enhanced scanner for CI integration with delta detection."""
    
    # Color patterns
    COLOR_PATTERNS = [
        r'#[0-9a-fA-F]{6}',
        r'#[0-9a-fA-F]{3}',
    ]
    
    # Spacing patterns
    SPACING_PATTERNS = [
        r'setContentsMargins\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)',
        r'setSpacing\(\s*\d+\s*\)',
        r'padding:\s*\d+px',
        r'margin:\s*\d+px',
    ]
    
    # Font patterns
    FONT_PATTERNS = [
        r'font-family:\s*[A-Za-z]+\s*;',
        r'setFont\(QFont\("[^"]+"\)\)',
    ]
    
    # Tokens for validation (anything not using these is a violation)
    VALID_COLOR_TOKENS = {
        "COLOR_PRIMARY", "COLOR_PRIMARY_HOVER", "COLOR_PRIMARY_ACTIVE",
        "COLOR_SUCCESS", "COLOR_WARNING", "COLOR_DANGER",
        "COLOR_INFO", "COLOR_STATUS_VALID", "COLOR_STATUS_WARNING",
        "COLOR_BG_MAIN", "COLOR_BG_SURFACE", "COLOR_BG_ELEVATED", "COLOR_BG_INPUT",
        "COLOR_TEXT_PRIMARY", "COLOR_TEXT_SECONDARY", "COLOR_TEXT_MUTED",
        "COLOR_BORDER", "COLOR_BORDER_LIGHT",
    }
    
    def __init__(self):
        self.violations: List[Violation] = []
        
    def scan_file(self, file_path: Path) -> List[Violation]:
        """Scan a single file for violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return violations
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments and strings
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue
                
            # Check colors
            for pattern in self.COLOR_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    hex_color = match.group()
                    if not self._is_tokenized_color(line):
                        severity = self._assess_severity(hex_color)
                        violations.append(Violation(
                            file_path=str(file_path),
                            line_number=line_num,
                            violation_type="COLOR",
                            severity=severity,
                            hex_color=hex_color,
                            suggested_fix=self._suggest_color_fix(hex_color)
                        ))
            
            # Check spacing
            for pattern in self.SPACING_PATTERNS:
                if re.search(pattern, line):
                    if not self._is_tokenized_spacing(line):
                        violations.append(Violation(
                            file_path=str(file_path),
                            line_number=line_num,
                            violation_type="SPACING",
                            severity="MEDIUM",
                            suggested_fix=self._suggest_spacing_fix(line)
                        ))
            
            # Check fonts
            for pattern in self.FONT_PATTERNS:
                if re.search(pattern, line) and "Segoe UI" not in line:
                    violations.append(Violation(
                        file_path=str(file_path),
                        line_number=line_num,
                        violation_type="FONT",
                        severity="LOW",
                        suggested_fix="Use Segoe UI from Typography constants"
                    ))
        
        return violations
    
    def _is_tokenized_color(self, line: str) -> bool:
        """Check if line uses tokenized colors."""
        for token in self.VALID_COLOR_TOKENS:
            if token in line:
                return True
        return False
    
    def _is_tokenized_spacing(self, line: str) -> bool:
        """Check if line uses tokenized spacing."""
        return "SPACING_" in line or "MARGIN_" in line or "PADDING_" in line
    
    def _assess_severity(self, hex_color: str) -> str:
        """Assess violation severity based on color."""
        # High severity: primary brand colors, danger colors
        high_colors = {"#FF6B35", "#3b82f6", "#10b981", "#ef4444", "#f59e0b"}
        if hex_color.upper() in high_colors:
            return "HIGH"
        return "MEDIUM"
    
    def _suggest_color_fix(self, hex_color: str) -> str:
        """Suggest token replacement for color."""
        suggestions = {
            "#1f2937": "COLOR_BG_MAIN",
            "#374151": "COLOR_BG_ELEVATED",
            "#4b5563": "COLOR_BORDER",
            "#e5e7eb": "COLOR_TEXT_PRIMARY",
            "#6b7280": "COLOR_TEXT_MUTED",
            "#3b82f6": "COLOR_PRIMARY",
            "#10b981": "COLOR_SUCCESS",
            "#ef4444": "COLOR_DANGER",
            "#f59e0b": "COLOR_WARNING",
        }
        return suggestions.get(hex_color.upper(), f"Use COLOR_* from ui.constants")
    
    def _suggest_spacing_fix(self, line: str) -> str:
        """Suggest token replacement for spacing."""
        # Extract numbers and suggest tokens
        numbers = re.findall(r'\d+', line)
        if numbers:
            n = int(numbers[0])
            if n <= 4: return "SPACING_XS"
            elif n <= 8: return "SPACING_SM"
            elif n <= 12: return "SPACING_MD"
            elif n <= 20: return "SPACING_LG"
            elif n <= 30: return "SPACING_XL"
            else: return "SPACING_XXL"
        return "Use SPACING_* from ui.constants"
    
    def scan_all(self, ui_dir: Path) -> List[Violation]:
        """Scan all Python files in UI directory."""
        all_violations = []
        exclude_files = {"printable_invoice.py", "theme_manager.py"}
        
        for py_file in ui_dir.rglob("*.py"):
            if py_file.name in exclude_files:
                continue
            all_violations.extend(self.scan_file(py_file))
        
        self.violations = all_violations
        return all_violations

# =====================================================
# CI REPORT GENERATOR
# =====================================================

class CIReportGenerator:
    """Generates CI reports for each phase."""
    
    def __init__(self, phase: int, baseline: ViolationBaseline):
        self.phase = phase
        self.baseline = baseline
        self.phase_config = PHASES[phase]
        
    def generate_report(self, violations: List[Violation]) -> CIReport:
        """Generate comprehensive CI report."""
        
        # Categorize violations
        new_violations = 0
        legacy_violations = 0
        
        file_counts = {}
        for v in violations:
            file_counts[v.file_path] = file_counts.get(v.file_path, 0) + 1
        
        for file_path, count in file_counts.items():
            is_new, delta = self.baseline.is_new_violation(file_path, count)
            if is_new:
                new_violations += delta
            else:
                legacy_violations += count - delta if is_new else count
        
        # Calculate compliance score
        total = len(violations)
        compliance_score = ((total - new_violations) / max(total, 1)) * 100 if total > 0 else 100.0
        
        # Determine blocking
        blocked, reason = self._should_block(violations, new_violations, compliance_score)
        
        # Build metrics
        metrics = {
            "color_violations": len([v for v in violations if v.violation_type == "COLOR"]),
            "spacing_violations": len([v for v in violations if v.violation_type == "SPACING"]),
            "font_violations": len([v for v in violations if v.violation_type == "FONT"]),
            "high_severity": len([v for v in violations if v.severity == "HIGH"]),
            "files_affected": len(set(v.file_path for v in violations)),
        }
        
        return CIReport(
            phase=self.phase,
            timestamp=datetime.now().isoformat(),
            total_violations=total,
            new_violations=new_violations,
            legacy_violations=legacy_violations,
            compliance_score=compliance_score,
            violations=violations,
            blocked=blocked,
            blocking_reason=reason,
            metrics=metrics
        )
    
    def _should_block(self, violations: List[Violation], new_count: int, score: float) -> Tuple[bool, Optional[str]]:
        """Determine if CI should block based on phase config."""
        config = self.phase_config
        
        if not config.blocking:
            return False, None
        
        # Phase 3: Hard blocking rules
        if config.new_violations_threshold == 0 and new_count > 0:
            return True, f"BLOCKED: {new_count} new violations introduced"
        
        if new_count > config.new_violations_threshold:
            return True, f"BLOCKED: New violations ({new_count}) exceed threshold ({config.new_violations_threshold})"
        
        return False, None
    
    def format_report(self, report: CIReport) -> str:
        """Format report for CI output."""
        config = self.phase_config
        
        output = []
        output.append("=" * 80)
        output.append(f"DESIGN SYSTEM ENFORCEMENT - {config.name}")
        output.append("=" * 80)
        output.append(f"Timestamp: {report.timestamp}")
        output.append(f"Phase: {report.phase} ({config.description})")
        output.append("")
        
        # Summary
        output.append("SUMMARY")
        output.append("-" * 40)
        output.append(f"Total Violations: {report.total_violations}")
        output.append(f"  - New: {report.new_violations}")
        output.append(f"  - Legacy: {report.legacy_violations}")
        output.append(f"Compliance Score: {report.compliance_score:.1f}/100")
        output.append(f"Files Affected: {report.metrics['files_affected']}")
        output.append("")
        
        # Breakdown
        output.append("VIOLATION BREAKDOWN")
        output.append("-" * 40)
        output.append(f"Colors: {report.metrics['color_violations']}")
        output.append(f"Spacing: {report.metrics['spacing_violations']}")
        output.append(f"Fonts: {report.metrics['font_violations']}")
        output.append(f"High Severity: {report.metrics['high_severity']}")
        output.append("")
        
        # Top violations
        if report.violations:
            output.append("TOP VIOLATIONS")
            output.append("-" * 40)
            files = {}
            for v in report.violations:
                files[v.file_path] = files.get(v.file_path, 0) + 1
            for i, (path, count) in enumerate(sorted(files.items(), key=lambda x: -x[1])[:5]):
                output.append(f"  {i+1}. {path}: {count} violations")
            output.append("")
        
        # Blocking status
        if report.blocked:
            output.append("[BLOCKED] " + report.blocking_reason)
            output.append("=" * 80)
        elif config.warn_only:
            output.append("[WARNING] Violations detected but merge allowed")
            output.append(f"  Compliance Score: {report.compliance_score:.1f}/100")
            output.append("=" * 80)
        else:
            output.append("[PASSED] No blocking violations")
            output.append("=" * 80)
        
        return "\n".join(output)

# =====================================================
# MAIN CI RUNNER
# =====================================================

class CIRunner:
    """Main CI enforcement runner."""
    
    def __init__(self, phase: int = 1):
        self.phase = phase
        self.scanner = DesignSystemScanner()
        self.baseline = ViolationBaseline()
        self.report_gen = CIReportGenerator(phase, self.baseline)
    
    def run(self, generate_baseline: bool = False) -> CIReport:
        """Execute CI scan and generate report."""
        print(f"Running Design System Enforcement - Phase {self.phase}")
        
        # Scan for violations
        violations = self.scanner.scan_all(UI_DIR)
        
        # Generate baseline if requested
        if generate_baseline:
            self.baseline.generate_baseline(violations)
            print(f"Baseline generated: {len(violations)} violations")
        
        # Generate report
        report = self.report_gen.generate_report(violations)
        
        # Output report
        output = self.report_gen.format_report(report)
        print(output)
        
        # Exit with appropriate code
        if report.blocked:
            sys.exit(1)
        
        return report

# =====================================================
# MAIN ENTRY POINT
# =====================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Design System CI Enforcement")
    parser.add_argument("--phase", type=int, default=1, choices=[1, 2, 3], help="CI phase (1=Observability, 2=Soft, 3=Hard)")
    parser.add_argument("--baseline", action="store_true", help="Generate new baseline")
    parser.add_argument("--check", action="store_true", help="Run enforcement check")
    
    args = parser.parse_args()
    
    runner = CIRunner(phase=args.phase)
    
    if args.baseline:
        runner.run(generate_baseline=True)
    elif args.check:
        runner.run(generate_baseline=False)
    else:
        print(f"Phase {args.phase}: {PHASES[args.phase].description}")
        print("Use --check to run enforcement, --baseline to generate baseline")

if __name__ == "__main__":
    main()
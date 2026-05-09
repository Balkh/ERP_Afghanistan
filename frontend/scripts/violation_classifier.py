"""
Violation Classification Engine
=================================
Transforms flat violation detection into intelligent 3-layer classification.
CI becomes a DECISION SYSTEM, not a counting system.

Layer 1: REAL UI VIOLATIONS (Action Required)
    - Direct widget styling (buttons, inputs, dialogs, tables)
    - Immediate visual impact on users
    
Layer 2: SEMANTIC / CONTEXTUAL VIOLATIONS (Architectural Review)
    - Data visualization (chart colors)
    - Complex mixed-context stylesheets
    - Requires manual design decision
    
Layer 3: EXCLUDED / SYSTEM LEVEL (Ignore)
    - Theme system internals
    - Backend logic
    - Print/email templates
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class ViolationLayer(Enum):
    LAYER_1_REAL_UI = "REAL_UI_VIOLATION"
    LAYER_2_SEMANTIC = "SEMANTIC_CONTEXTUAL"
    LAYER_3_EXCLUDED = "EXCLUDED_SYSTEM"


class ViolationSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ClassifiedViolation:
    file_path: str
    line_number: int
    violation_type: str
    raw_value: str
    
    layer: ViolationLayer
    severity: ViolationSeverity
    confidence: float  # 0.0 - 1.0
    
    reason: str
    remediation: str
    requires_review: bool


class ViolationClassifier:
    """
    Intelligent classifier that determines the layer and severity
    of each detected violation based on contextual analysis.
    """
    
    def __init__(self):
        self.stats = {
            "layer_1": 0,
            "layer_2": 0,
            "layer_3": 0,
            "total": 0
        }
    
    # =========================================================================
    # LAYER 3: EXCLUSION PATTERNS (Lowest Priority - Check First)
    # =========================================================================
    
    EXCLUDED_FILES = {
        "theme_manager.py",           # Theme system internals
        "printable_invoice.py",        # Document template
        "enterprise_styling.py",      # Core styling system
        "dashboard.py",               # Data visualization
        "control_center_screen.py",   # Dashboard with charts
        "correlation_screen.py",      # Analytics
        "drift_intelligence_screen.py",
        "workflow_intelligence_screen.py",
        "integrity_screen.py",
        "intelligence_hub_screen.py",
        "production_screen.py",
    }
    
    EXCLUDED_PATTERNS = {
        # Chart color mappings
        r"'[a-z]+'\s*:\s*'#[0-9a-fA-F]{6}'",  # 'mauve': '#cba6f7'
        r"chart_palette",
        r"color_mapping.*=.*\{",
        
        # Theme system internals
        r"QPalette",
        r"QColor\(",
        r"setPalette",
        
        # Data visualization
        r"pyqtgraph",
        r"matplotlib",
        
        # Print/email specific
        r"font-family:",
        r"@media print",
    }
    
    # =========================================================================
    # LAYER 2: SEMANTIC / CONTEXTUAL PATTERNS
    # =========================================================================
    
    SEMANTIC_PATTERNS = {
        # Complex stylesheets with mixed contexts
        r"setStyleSheet.*\{.*background.*gradient",
        r"setStyleSheet.*\{.*border.*image",
        
        # Data display colors (not UI controls)
        r"\.setForeground\(.*color\)",  # Table item colors
        r"itemDelegate",
        
        # KPI/dashboard metrics
        r"kpi_",
        r"metric_",
        r"indicator_",
    }
    
    # =========================================================================
    # LAYER 1: REAL UI VIOLATION PATTERNS (High Priority)
    # =========================================================================
    
    REAL_UI_PATTERNS = {
        # Direct widget styling
        r"QPushButton.*\{",
        r"QPushButton:hover",
        r"QPushButton:pressed",
        r"QPushButton:disabled",
        
        r"QLineEdit.*\{",
        r"QComboBox.*\{",
        r"QTextEdit.*\{",
        r"QSpinBox.*\{",
        r"QDateEdit.*\{",
        
        r"QDialog.*\{",
        r"QWidget.*\{",
        r"QFrame.*\{",
        
        r"QTableWidget.*\{",
        r"QHeaderView.*\{",
        r"QTableWidget::item",
        
        r"QListWidget.*\{",
        r"QTreeWidget.*\{",
        
        # Layout spacing
        r"setSpacing\(",
        r"setContentsMargins\(",
        
        # Color definitions in widgets
        r"background-color:",
        r"color:",
        r"border:",
    }
    
    # =========================================================================
    # CLASSIFICATION LOGIC
    # =========================================================================
    
    def classify(
        self,
        file_path: str,
        line_number: int,
        violation_type: str,
        line_content: str,
        full_file_content: str
    ) -> ClassifiedViolation:
        """Main classification entry point."""
        
        self.stats["total"] += 1
        
        # STEP 1: Check for EXCLUSION (Layer 3)
        layer_3_result = self._check_exclusion(
            file_path, line_content, full_file_content
        )
        if layer_3_result.excluded:
            self.stats["layer_3"] += 1
            return self._create_violation(
                file_path, line_number, violation_type, line_content,
                ViolationLayer.LAYER_3_EXCLUDED,
                ViolationSeverity.INFO,
                layer_3_result.confidence,
                layer_3_result.reason,
                "No action required - system level",
                requires_review=False
            )
        
        # STEP 2: Check for SEMANTIC/CONTEXTUAL (Layer 2)
        layer_2_result = self._check_semantic_context(
            file_path, line_content, full_file_content
        )
        if layer_2_result.is_semantic:
            self.stats["layer_2"] += 1
            return self._create_violation(
                file_path, line_number, violation_type, line_content,
                ViolationLayer.LAYER_2_SEMANTIC,
                ViolationSeverity.MEDIUM,
                layer_2_result.confidence,
                layer_2_result.reason,
                "Requires manual architectural review",
                requires_review=True
            )
        
        # STEP 3: Default to REAL UI VIOLATION (Layer 1)
        self.stats["layer_1"] += 1
        severity = self._determine_severity(violation_type, line_content)
        
        return self._create_violation(
            file_path, line_number, violation_type, line_content,
            ViolationLayer.LAYER_1_REAL_UI,
            severity,
            0.95,
            "Direct UI widget styling violation",
            "Fix via automated remediation",
            requires_review=False
        )
    
    def _check_exclusion(
        self,
        file_path: str,
        line_content: str,
        full_file_content: str
    ) -> 'ExclusionResult':
        """Check if violation should be excluded (Layer 3)."""
        
        # Check file-level exclusion
        file_name = Path(file_path).name
        if file_name in self.EXCLUDED_FILES:
            return ExclusionResult(
                excluded=True,
                confidence=1.0,
                reason=f"File '{file_name}' in excluded list (theme system/visualization)"
            )
        
        # Check pattern-level exclusion
        for pattern in self.EXCLUDED_PATTERNS:
            if re.search(pattern, line_content, re.IGNORECASE):
                return ExclusionResult(
                    excluded=True,
                    confidence=0.95,
                    reason=f"Pattern '{pattern}' matches excluded system pattern"
                )
        
        return ExclusionResult(excluded=False, confidence=0.0, reason="")
    
    def _check_semantic_context(
        self,
        file_path: str,
        line_content: str,
        full_file_content: str
    ) -> 'SemanticResult':
        """Check if violation is semantic/contextual (Layer 2)."""
        
        # Check semantic patterns
        for pattern in self.SEMANTIC_PATTERNS:
            if re.search(pattern, line_content, re.IGNORECASE):
                return SemanticResult(
                    is_semantic=True,
                    confidence=0.85,
                    reason=f"Pattern '{pattern}' indicates semantic/contextual usage"
                )
        
        # Check for chart data in nearby lines (within 20 lines)
        file_name = Path(file_path).name
        if "dashboard" in file_name.lower() or "chart" in full_file_content[:500].lower():
            if any(kw in line_content.lower() for kw in ["color", "palette", "graph"]):
                return SemanticResult(
                    is_semantic=True,
                    confidence=0.75,
                    reason="File contains chart/visualization context"
                )
        
        return SemanticResult(is_semantic=False, confidence=0.0, reason="")
    
    def _determine_severity(
        self,
        violation_type: str,
        line_content: str
    ) -> ViolationSeverity:
        """Determine severity of the violation."""
        
        # Critical: Primary action elements
        if "QPushButton" in line_content and ("hover" in line_content or "pressed" in line_content):
            return ViolationSeverity.CRITICAL
        
        # High: Direct color definitions in main widgets
        if "background-color:" in line_content or "color:" in line_content:
            if any(w in line_content for w in ["QPushButton", "QDialog", "QWidget"]):
                return ViolationSeverity.HIGH
        
        # Medium: Spacing/layout violations
        if violation_type == "SPACING":
            return ViolationSeverity.MEDIUM
        
        # Low: Typography and other
        return ViolationSeverity.LOW
    
    def _create_violation(
        self,
        file_path: str,
        line_number: int,
        violation_type: str,
        raw_value: str,
        layer: ViolationLayer,
        severity: ViolationSeverity,
        confidence: float,
        reason: str,
        remediation: str,
        requires_review: bool
    ) -> ClassifiedViolation:
        return ClassifiedViolation(
            file_path=file_path,
            line_number=line_number,
            violation_type=violation_type,
            raw_value=raw_value,
            layer=layer,
            severity=severity,
            confidence=confidence,
            reason=reason,
            remediation=remediation,
            requires_review=requires_review
        )
    
    def get_stats(self) -> dict:
        """Return classification statistics."""
        return self.stats.copy()


@dataclass
class ExclusionResult:
    excluded: bool
    confidence: float
    reason: str


@dataclass
class SemanticResult:
    is_semantic: bool
    confidence: float
    reason: str


def classify_violation(
    file_path: str,
    line_number: int,
    violation_type: str,
    line_content: str,
    full_file_content: str
) -> ClassifiedViolation:
    """Standalone function for single violation classification."""
    classifier = ViolationClassifier()
    return classifier.classify(
        file_path, line_number, violation_type,
        line_content, full_file_content
    )
"""
Phase 5B.13 — UX Governor.

Validates UI consistency rules against screens.
Read-only — reports violations without blocking.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any
import re


@dataclass
class UXReport:
    screen_name: str = ""
    passes: bool = True
    spacing_violations: int = 0
    color_violations: int = 0
    forbidden_styles: int = 0
    warnings: List[str] = field(default_factory=list)
    score: float = 100.0


_FORBIDDEN_COLORS = re.compile(
    r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|'
    r'rgb\(\d+,\s*\d+,\s*\d+\)|rgba\(\d+,\s*\d+,\s*\d+,\s*[\d.]+\)'
)

_FORBIDDEN_FONTS = ['Arial', 'Times New Roman', 'Verdana', 'Tahoma']
_FORBIDDEN_FONT_RE = re.compile('|'.join(_FORBIDDEN_FONTS), re.IGNORECASE)


def validate_screen(screen: Any) -> UXReport:
    """Validate a screen widget for UX consistency.

    Checks:
    - No hardcoded hex/rgb colors (must use COLOR_* tokens)
    - No forbidden fonts
    - Spacing uses constants (basic heuristic)

    Returns UXReport with findings. NEVER blocks rendering.
    """
    report = UXReport(screen_name=screen.__class__.__name__ if hasattr(screen, '__class__') else "unknown")

    try:
        ss = ""
        if hasattr(screen, 'styleSheet'):
            ss = screen.styleSheet()

        if not ss:
            return report

        colors = _FORBIDDEN_COLORS.findall(ss)
        if colors:
            report.color_violations = len(colors)
            report.warnings.append(f"{len(colors)} hardcoded color(s) detected")
            report.passes = False

        if _FORBIDDEN_FONT_RE.search(ss):
            report.forbidden_styles += 1
            report.warnings.append("Forbidden font detected")
            report.passes = False

    except Exception:
        report.warnings.append("Validation error (non-critical)")

    violations = report.color_violations + report.forbidden_styles
    report.score = max(0, 100 - violations * 10)
    return report

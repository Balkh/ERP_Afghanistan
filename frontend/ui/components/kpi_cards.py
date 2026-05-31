"""
Standardized KPI Card Components.

Three-tier hierarchy for operational metrics:
- KPICard: Primary metrics (dashboard overview, financial summaries)
- MiniMetricCard: Secondary/diagnostic metrics (role-specific sections)
- StatusBadge: Compact status indicators (alert rows, inline status)

All cards use semantic COLOR_* tokens for automatic dark/light parity.
"""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.constants import (
    SPACING_XS, SPACING_SM, SPACING_MD,
    COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    COLOR_PRIMARY, COLOR_DANGER, COLOR_INFO, COLOR_STATUS_VALID, COLOR_STATUS_WARNING,
    BORDER_RADIUS_MD, BORDER_RADIUS_LG,
    TEXT_TABLE, TEXT_CARD_TITLE,
    TEXT_SECTION_TITLE, TEXT_LABEL,
)


# ── Severity color mapping (theme-aware) ──────────────────────────

SEVERITY_COLORS = {
    "success": COLOR_STATUS_VALID,
    "valid": COLOR_STATUS_VALID,
    "ok": COLOR_STATUS_VALID,
    "healthy": COLOR_STATUS_VALID,
    "warning": COLOR_STATUS_WARNING,
    "degraded": COLOR_STATUS_WARNING,
    "danger": COLOR_DANGER,
    "critical": COLOR_DANGER,
    "error": COLOR_DANGER,
    "info": COLOR_INFO,
    "primary": COLOR_PRIMARY,
}


def _severity_color(severity: str) -> str:
    """Map severity string to current theme color."""
    return SEVERITY_COLORS.get(severity.lower(), COLOR_TEXT_MUTED)


# ── Tier 1: Primary KPI Card ──────────────────────────────────────

class KPICard(QFrame):
    """Primary metric card for dashboard overview.

    Hierarchy:
    - Accent left border (severity color)
    - Title (muted, small)
    - Value (large, bold, accent color)
    - Optional subtitle (muted, compact)

    Usage:
        card = KPICard("Revenue", "AFN 1,234,567", "Today", severity="success")
    """

    def __init__(
        self,
        title: str,
        value: str = "\u2014",
        subtitle: str = "",
        severity: str = "primary",
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setMinimumSize(160, 82)
        self._severity = severity
        self._color = _severity_color(severity)

        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG}px;
                border-left: 4px solid {self._color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_XS)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", TEXT_TABLE))
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(str(value))
        self.value_label.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {self._color}; border: none;")
        self.value_label.setWordWrap(True)
        layout.addWidget(self.value_label)

        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setFont(QFont("Segoe UI", TEXT_LABEL))
            self.subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
            layout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None

    def update_value(self, value: str, subtitle: str = None, severity: str = None):
        """Update card value with optional subtitle and severity change."""
        self.value_label.setText(str(value))

        if subtitle is not None and self.subtitle_label:
            self.subtitle_label.setText(subtitle)

        if severity and severity != self._severity:
            self._severity = severity
            self._color = _severity_color(severity)
            self.value_label.setStyleSheet(f"color: {self._color}; border: none;")
            self.setStyleSheet(f"""
                QFrame#kpiCard {{
                    background-color: {COLOR_BG_ELEVATED};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: {BORDER_RADIUS_LG}px;
                    border-left: 4px solid {self._color};
                }}
            """)


# ── Tier 2: Mini Metric Card ──────────────────────────────────────

class MiniMetricCard(QFrame):
    """Compact metric card for role-specific sections.

    Hierarchy:
    - Label (helper text, muted)
    - Value (medium, bold, accent color)

    Usage:
        card = MiniMetricCard("Products", 142, severity="primary")
    """

    def __init__(
        self,
        label: str,
        value: str = "\u2014",
        severity: str = "primary",
        is_currency: bool = False,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setObjectName("miniMetricCard")
        self._severity = severity
        self._color = _severity_color(severity)
        self._is_currency = is_currency

        self.setStyleSheet(f"""
            QFrame#miniMetricCard {{
                background-color: {COLOR_BG_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_XS)

        self.label = QLabel(label)
        self.label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none;")
        layout.addWidget(self.label)

        display = f"AFN {value:,.2f}" if is_currency else str(value)
        self.value_label = QLabel(display)
        self.value_label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {self._color}; border: none;")
        self.value_label.setWordWrap(True)
        layout.addWidget(self.value_label)

    def update_value(self, value, severity: str = None):
        """Update value with optional severity change."""
        display = f"AFN {float(value):,.2f}" if self._is_currency else str(value)
        self.value_label.setText(display)

        if severity and severity != self._severity:
            self._severity = severity
            self._color = _severity_color(severity)
            self.value_label.setStyleSheet(f"color: {self._color}; border: none;")


# ── Tier 3: Status Badge ──────────────────────────────────────────

class StatusBadge(QLabel):
    """Compact status indicator for alert rows and inline status.

    Usage:
        badge = StatusBadge("Operational", severity="success")
    """

    def __init__(self, text: str = "", severity: str = "info", parent: QWidget = None):
        super().__init__(text, parent)
        self._severity = severity
        self._apply_style()

    def set_severity(self, severity: str):
        self._severity = severity
        self._apply_style()

    def _apply_style(self):
        __color = _severity_color(self._severity)
        __clr = _severity_color(self._severity)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {COLOR_BG_ELEVATED};
                color: {__clr};
                padding: {SPACING_XS}px {SPACING_SM}px;
                border-radius: {BORDER_RADIUS_MD}px;
                font-size: {TEXT_TABLE}px;
                font-weight: bold;
                border: 1px solid {__clr};
            }}
        """)
        self.setFont(QFont("Segoe UI", TEXT_TABLE, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignCenter)


# ── Section Header ────────────────────────────────────────────────

class SectionHeader(QLabel):
    """Standardized section header with optional action link."""

    def __init__(self, title: str, parent: QWidget = None):
        super().__init__(title, parent)
        self.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        self.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")

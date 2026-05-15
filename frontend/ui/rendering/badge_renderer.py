from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFont
from ui.constants import (
    COLOR_DANGER, COLOR_WARNING, COLOR_INFO, COLOR_SUCCESS,
    COLOR_BG_SURFACE, COLOR_TEXT_MUTED,
    TEXT_BADGE, TEXT_TABLE, SPACING_XS, SPACING_SM, BORDER_RADIUS_LG)


class BadgeSeverity:
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"


_FG_MAP = {
    BadgeSeverity.CRITICAL: COLOR_DANGER,
    BadgeSeverity.HIGH: COLOR_DANGER,
    BadgeSeverity.MEDIUM: COLOR_WARNING,
    BadgeSeverity.LOW: COLOR_INFO,
    BadgeSeverity.INFO: COLOR_INFO,
    BadgeSeverity.SUCCESS: COLOR_SUCCESS,
    BadgeSeverity.WARNING: COLOR_WARNING,
}

_BG_MAP = {
    BadgeSeverity.CRITICAL: COLOR_BG_SURFACE,
    BadgeSeverity.HIGH: COLOR_BG_SURFACE,
    BadgeSeverity.MEDIUM: COLOR_BG_SURFACE,
    BadgeSeverity.LOW: COLOR_BG_SURFACE,
    BadgeSeverity.INFO: COLOR_BG_SURFACE,
    BadgeSeverity.SUCCESS: COLOR_BG_SURFACE,
    BadgeSeverity.WARNING: COLOR_BG_SURFACE,
}


class BadgeRenderer:
    @staticmethod
    def style(badge: QLabel, severity: str = BadgeSeverity.INFO) -> None:
        fg = _FG_MAP.get(severity, COLOR_TEXT_MUTED)
        bg = _BG_MAP.get(severity, COLOR_BG_SURFACE)
        badge.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            font-weight: bold;
            font-size: {TEXT_TABLE}px;
            padding: {SPACING_XS}px {SPACING_SM}px;
            border-radius: {BORDER_RADIUS_LG}px;
            border: 1px solid {fg};
        """)
        badge.setFont(QFont("Segoe UI", TEXT_BADGE, QFont.Weight.Bold))

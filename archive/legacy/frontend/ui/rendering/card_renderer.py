from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtGui import QFont
from enum import Enum
from ui.constants import (
    COLOR_BG_ELEVATED, COLOR_BG_SURFACE, COLOR_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    BORDER_RADIUS_MD, BORDER_RADIUS_LG,
    TEXT_TABLE_HEADER, TEXT_BODY, TEXT_PAGE_TITLE,
    SPACING_MD, SPACING_SM)


class CardElevation:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_BG_MAP = {
    CardElevation.LOW: COLOR_BG_SURFACE,
    CardElevation.MEDIUM: COLOR_BG_ELEVATED,
    CardElevation.HIGH: COLOR_BORDER,
}

_RADIUS_MAP = {
    CardElevation.LOW: BORDER_RADIUS_MD,
    CardElevation.MEDIUM: BORDER_RADIUS_MD,
    CardElevation.HIGH: BORDER_RADIUS_LG,
}


class CardRenderer:
    @staticmethod
    def style(card: QFrame, elevation: str = CardElevation.MEDIUM, accent_color: str = None) -> None:
        bg = _BG_MAP.get(elevation, COLOR_BG_ELEVATED)
        radius = _RADIUS_MAP.get(elevation, BORDER_RADIUS_MD)
        border = f"border-left: 4px solid {accent_color};" if accent_color else ""
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: {radius}px;
                {border}
            }}
        """)

    @staticmethod
    def create_kpi(title: str, value: str = "\u2014", accent: str = None,
                   elevation: str = CardElevation.MEDIUM) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        CardRenderer.style(card, elevation, accent)
        card.setMinimumHeight(82)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", TEXT_TABLE_HEADER))
        t.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        layout.addWidget(t)
        v = QLabel(value)
        v.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        v.setStyleSheet(f"color: {accent or COLOR_TEXT_PRIMARY};")
        v.setWordWrap(True)
        layout.addWidget(v)
        return card, t, v

    @staticmethod
    def create_mini_card(title: str, value: str, accent: str = None) -> QFrame:
        card = QFrame()
        CardRenderer.style(card, CardElevation.MEDIUM, accent)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", TEXT_TABLE_HEADER))
        t.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        layout.addWidget(t)
        v = QLabel(value)
        v.setFont(QFont("Segoe UI", TEXT_BODY, QFont.Weight.Bold))
        v.setStyleSheet(f"color: {accent or COLOR_TEXT_PRIMARY};")
        layout.addWidget(v)
        return card

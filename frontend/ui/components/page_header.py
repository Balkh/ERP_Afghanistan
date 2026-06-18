"""Reusable enterprise page header component."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.constants import (
    BORDER_RADIUS_LG,
    COLOR_BG_ELEVATED,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    SPACING_MD,
    SPACING_SM,
    SPACING_XL,
    TEXT_BODY_SMALL,
    TEXT_HELPER,
    TEXT_PAGE_TITLE,
)


class PageHeader(QFrame):
    """Lightweight title/subtitle/action shell for enterprise screens."""

    def __init__(self, title: str, subtitle: str = "", eyebrow: str = "ERP WORKSPACE", parent=None):
        super().__init__(parent)
        self.setObjectName("pageHeader")
        self.setMinimumHeight(86)
        self.setStyleSheet(f"""
            QFrame#pageHeader {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-left: 4px solid {COLOR_PRIMARY};
                border-radius: {BORDER_RADIUS_LG}px;
            }}
        """)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(SPACING_XL, SPACING_MD, SPACING_XL, SPACING_MD)
        self._layout.setSpacing(SPACING_MD)

        text_col = QVBoxLayout()
        text_col.setSpacing(SPACING_SM)
        self.eyebrow_label = QLabel(eyebrow.upper())
        self.eyebrow_label.setFont(QFont("Segoe UI", TEXT_HELPER, QFont.Weight.Bold))
        self.eyebrow_label.setStyleSheet(f"color: {COLOR_PRIMARY}; letter-spacing: 1px;")
        text_col.addWidget(self.eyebrow_label)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        text_col.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setFont(QFont("Segoe UI", TEXT_BODY_SMALL))
        self.subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        text_col.addWidget(self.subtitle_label)

        self._layout.addLayout(text_col, 1)
        self._layout.setAlignment(Qt.AlignVCenter)

    def add_action(self, widget):
        self._layout.addWidget(widget)
        return widget

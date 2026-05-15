from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from enum import Enum
from ui.constants import (
    COLOR_HEADER_DARK, COLOR_BG_MAIN, COLOR_BORDER,
    COLOR_PRIMARY, COLOR_TEXT_ON_PRIMARY,
    SPACING_NONE, MARGIN_CARD, MARGIN_COMPACT_H, MARGIN_COMPACT_V,
    TEXT_CARD_TITLE, SPACING_SM, BORDER_RADIUS_SM)


class DialogSection:
    HEADER = "header"
    CONTENT = "content"
    FOOTER = "footer"


_DIALOG_MIN_WIDTH = 400
_DIALOG_MIN_HEIGHT = 200


class DialogRenderer:
    @staticmethod
    def configure(dialog: QDialog) -> None:
        dialog.setMinimumWidth(_DIALOG_MIN_WIDTH)
        dialog.setMinimumHeight(_DIALOG_MIN_HEIGHT)

    @staticmethod
    def create_header(dialog: QDialog, title: str) -> QFrame:
        header = QFrame(dialog)
        header.setFixedHeight(50)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(MARGIN_COMPACT_H, MARGIN_COMPACT_V, MARGIN_COMPACT_H, MARGIN_COMPACT_V)
        label = QLabel(title)
        label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        label.setStyleSheet("color: white;")
        layout.addWidget(label)
        layout.addStretch()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_HEADER_DARK};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
        """)
        return header

    @staticmethod
    def create_footer(dialog: QDialog) -> QFrame:
        footer = QFrame(dialog)
        footer.setFixedHeight(60)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(MARGIN_COMPACT_H, MARGIN_COMPACT_V, MARGIN_COMPACT_H, MARGIN_COMPACT_V)
        layout.addStretch()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_MAIN};
                border-top: 1px solid {COLOR_BORDER};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
        """)
        return footer

    @staticmethod
    def add_save_cancel(footer: QFrame, dialog: QDialog) -> tuple[QPushButton, QPushButton]:
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY};
                padding: {SPACING_SM}px 20px; border-radius: {BORDER_RADIUS_SM}; font-weight: 600;
            }}
        """)
        save_btn.clicked.connect(dialog.accept)
        layout = footer.layout()
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)
        return save_btn, cancel_btn

    @staticmethod
    def build_layout(dialog: QDialog, title: str) -> tuple[QVBoxLayout, QFrame]:
        layout = QVBoxLayout(dialog)
        layout.setSpacing(SPACING_NONE)
        layout.setContentsMargins(SPACING_NONE, SPACING_NONE, SPACING_NONE, SPACING_NONE)
        header = DialogRenderer.create_header(dialog, title)
        layout.addWidget(header)
        content = QFrame(dialog)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(MARGIN_CARD, MARGIN_CARD, MARGIN_CARD, MARGIN_CARD)
        layout.addWidget(content, 1)
        footer = DialogRenderer.create_footer(dialog)
        layout.addWidget(footer)
        return content.layout(), footer

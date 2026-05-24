from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QFont
from enum import Enum
from ui.constants import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
    COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_SUCCESS_ACTIVE, COLOR_SUCCESS_MUTED,
    COLOR_DANGER, COLOR_DANGER_HOVER, COLOR_DANGER_ACTIVE, COLOR_DANGER_MUTED,
    COLOR_WARNING, COLOR_WARNING_HOVER, COLOR_WARNING_ACTIVE, COLOR_WARNING_MUTED,
    COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_BG_ELEVATED,
    BORDER_RADIUS_MD,
    TEXT_TABLE)


class ButtonStyle:
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"
    GHOST = "ghost"


_BUTTON_SIZE = {
    "sm": 32,
    "md": 36,
    "lg": 44,
}


class ButtonRenderer:
    @staticmethod
    def style(btn: QPushButton, variant: str = ButtonStyle.PRIMARY, size: str = "md") -> None:
        h = _BUTTON_SIZE.get(size, 36)
        btn.setFixedHeight(h)
        btn.setMinimumWidth(80)
        font = QFont("Segoe UI", TEXT_TABLE)
        font.setWeight(600)
        btn.setFont(font)
        btn.setStyleSheet(ButtonRenderer._variant_css(variant))

    @staticmethod
    def _variant_css(variant: str) -> str:
        styles = {
            ButtonStyle.PRIMARY: f"""
                QPushButton {{ background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY}; border: none; border-radius: {BORDER_RADIUS_MD}px; }}
                QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
                QPushButton:pressed {{ background-color: {COLOR_PRIMARY_ACTIVE}; }}
                QPushButton:disabled {{ background-color: {COLOR_BORDER}; color: {COLOR_TEXT_MUTED}; }}
            """,
            ButtonStyle.SECONDARY: f"""
                QPushButton {{ background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_ON_PRIMARY}; border: none; border-radius: {BORDER_RADIUS_MD}px; }}
                QPushButton:hover {{ background-color: {COLOR_BORDER}; }}
                QPushButton:pressed {{ background-color: {COLOR_BORDER_LIGHT}; }}
                QPushButton:disabled {{ background-color: {COLOR_BORDER}; color: {COLOR_TEXT_MUTED}; }}
            """,
            ButtonStyle.SUCCESS: f"""
                QPushButton {{ background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_PRIMARY}; border: none; border-radius: {BORDER_RADIUS_MD}px; }}
                QPushButton:hover {{ background-color: {COLOR_SUCCESS_HOVER}; }}
                QPushButton:pressed {{ background-color: {COLOR_SUCCESS_ACTIVE}; }}
                QPushButton:disabled {{ background-color: {COLOR_SUCCESS_MUTED}; color: {COLOR_TEXT_MUTED}; }}
            """,
            ButtonStyle.DANGER: f"""
                QPushButton {{ background-color: {COLOR_DANGER}; color: {COLOR_TEXT_ON_PRIMARY}; border: none; border-radius: {BORDER_RADIUS_MD}px; }}
                QPushButton:hover {{ background-color: {COLOR_DANGER_HOVER}; }}
                QPushButton:pressed {{ background-color: {COLOR_DANGER_ACTIVE}; }}
                QPushButton:disabled {{ background-color: {COLOR_DANGER_MUTED}; color: {COLOR_TEXT_MUTED}; }}
            """,
            ButtonStyle.WARNING: f"""
                QPushButton {{ background-color: {COLOR_WARNING}; color: {COLOR_TEXT_ON_PRIMARY}; border: none; border-radius: {BORDER_RADIUS_MD}px; }}
                QPushButton:hover {{ background-color: {COLOR_WARNING_HOVER}; }}
                QPushButton:pressed {{ background-color: {COLOR_WARNING_ACTIVE}; }}
                QPushButton:disabled {{ background-color: {COLOR_WARNING_MUTED}; color: {COLOR_TEXT_MUTED}; }}
            """,
            ButtonStyle.GHOST: f"""
                QPushButton {{ background-color: transparent; color: {COLOR_PRIMARY}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; }}
                QPushButton:hover {{ background-color: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_PRIMARY}; }}
                QPushButton:pressed {{ background-color: {COLOR_BORDER_LIGHT}; border: 1px solid {COLOR_PRIMARY_ACTIVE}; }}
                QPushButton:disabled {{ color: {COLOR_TEXT_MUTED}; border: 1px solid {COLOR_BORDER_LIGHT}; }}
            """,
        }
        return styles.get(variant, styles[ButtonStyle.PRIMARY])

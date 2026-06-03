"""Canonical stylesheet helpers for the Pharmacy ERP frontend.

Centralizes the 4 _combo_style definitions that previously lived in
finance screens. Provides a single ``combo_stylesheet()`` helper that
returns the canonical QComboBox stylesheet with optional customisation.
"""

from ui.constants import (
    COLOR_BG_ELEVATED,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_TEXT_PRIMARY,
    BORDER_RADIUS_SM,
    SPACING_XS,
    SPACING_SM,
)


def combo_stylesheet(min_height=30, custom_arrow=True, with_selection=True):
    """Return the canonical QComboBox stylesheet.

    Parameters
    ----------
    min_height : int
        ComboBox minimum height in pixels (default 30).
    custom_arrow : bool
        If True, draw a CSS-only triangle for the dropdown indicator
        (default True — matches the two workspace variants).
    with_selection : bool
        If True, include ``selection-background-color`` for the dropdown
        popup (default True — matches the two workspace variants).
    """
    arrow_block = ""
    if custom_arrow:
        arrow_block = (
            f"            QComboBox::down-arrow {{\n"
            f"                image: none;\n"
            f"                border-left: 5px solid transparent;\n"
            f"                border-right: 5px solid transparent;\n"
            f"                border-top: 5px solid {COLOR_TEXT_PRIMARY};\n"
            f"            }}\n"
        )
    selection_block = ""
    if with_selection:
        selection_block = f"                selection-background-color: {COLOR_PRIMARY};\n"

    return (
        f"            QComboBox {{\n"
        f"                background-color: {COLOR_BG_ELEVATED};\n"
        f"                border: 1px solid {COLOR_BORDER};\n"
        f"                border-radius: {BORDER_RADIUS_SM};\n"
        f"                padding: {SPACING_XS}px {SPACING_SM}px;\n"
        f"                color: {COLOR_TEXT_PRIMARY};\n"
        f"                min-height: {min_height}px;\n"
        f"            }}\n"
        f"            QComboBox::drop-down {{ border: none; }}\n"
        f"{arrow_block}"
        f"            QComboBox QAbstractItemView {{\n"
        f"                background-color: {COLOR_BG_ELEVATED};\n"
        f"                color: {COLOR_TEXT_PRIMARY};\n"
        f"{selection_block}"
        f"            }}\n"
    )

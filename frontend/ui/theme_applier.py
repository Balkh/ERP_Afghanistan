"""Theme stylesheet application for MainWindow.

Extracted from ui/main_window.py to reduce God Object responsibilities.
Contains pure functions that apply theme-aware stylesheets to MainWindow
widgets.  No new abstractions -- just stylesheet data moved out of the
controller class.
"""

from PySide6.QtWidgets import QFrame

import ui.constants as _constants
from ui.constants import (
    SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_6,
    BORDER_RADIUS_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG,
    TEXT_BODY, TEXT_LABEL,
    COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
    COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_BORDER_FOCUS,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY,
)


def refresh_content_frame(main_window):
    """Re-apply the content-frame stylesheet after a theme switch.

    Finds the content frame (child of central widget) and applies the
    canonical stylesheet using current theme constants.
    """
    if not hasattr(main_window, 'pages'):
        return

    C = _constants
    content_frame = None
    if hasattr(main_window, 'sidebar'):
        content_frame = main_window.sidebar.parent()

    for child in main_window.findChildren(QFrame):
        if child.parent() is main_window.centralWidget():
            content_frame = child
            break

    if content_frame:
        content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.COLOR_BG_MAIN};
            }}
            QLabel {{
                color: {C.COLOR_TEXT_PRIMARY};
            }}
            QGroupBox {{
                color: {C.COLOR_TEXT_PRIMARY};
                font-weight: bold;
                border: 1px solid {C.COLOR_BORDER};
                border-radius: {C.BORDER_RADIUS_LG}px;
                margin-top: {SPACING_SM}px;
                padding-top: {SPACING_SM}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {SPACING_XS}px;
            }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {C.COLOR_BG_SURFACE};
                color: {C.COLOR_TEXT_PRIMARY};
                border: 1px solid {C.COLOR_BORDER};
                border-radius: {C.BORDER_RADIUS_MD}px;
                padding: {C.SPACING_SM}px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {C.COLOR_BORDER_FOCUS};
            }}
            QScrollArea {{
                background-color: transparent;
            }}
        """)


def refresh_status_bar_labels(main_window):
    """Re-apply status bar label colors, header, and nav_header styles."""
    C = _constants
    for attr, ss in [
        ('user_label', f"color: {C.COLOR_TEXT_SECONDARY}; margin-right: {C.SPACING_LG}px;"),
        ('conn_label', f"color: {C.COLOR_STATUS_VALID}; margin-right: {C.SPACING_LG}px; font-weight: bold;"),
        ('time_label', f"color: {C.COLOR_TEXT_SECONDARY}; margin-right: {C.SPACING_LG}px;"),
        ('device_id_label', f"font-size: {C.TEXT_LABEL}pt; color: {C.COLOR_TEXT_MUTED};"),
        ('license_status_label', f"font-size: {C.TEXT_LABEL}pt; color: {C.COLOR_TEXT_MUTED}; margin-left: {C.SPACING_MD}px;"),
        ('connection_status_label', f"font-size: {C.TEXT_LABEL}pt; color: {C.COLOR_TEXT_MUTED}; margin-left: {C.SPACING_MD}px;"),
    ]:
        widget = getattr(main_window, attr, None)
        if widget is not None:
            try:
                widget.setStyleSheet(ss)
            except RuntimeError:
                pass

    main_window.header.setStyleSheet(f"""
        QLabel {{
            color: {COLOR_TEXT_PRIMARY};
            padding-left: {SPACING_SM}px;
        }}
    """)

    main_window.nav_header.setStyleSheet(f"""
        QWidget {{ background-color: transparent; }}
        EnterpriseButton {{
            background-color: transparent;
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_SM}px;
            padding: {SPACING_6}px {SPACING_SM}px;
            font-size: {TEXT_BODY}pt;
        }}
        EnterpriseButton:hover {{
            background-color: {COLOR_BG_ELEVATED};
            border: 1px solid {COLOR_PRIMARY};
        }}
        EnterpriseButton:pressed {{
            background-color: {COLOR_BORDER};
        }}
        EnterpriseButton:disabled {{
            color: {COLOR_BORDER_LIGHT};
            border: 1px solid {COLOR_BG_ELEVATED};
        }}
        QLabel {{
            background-color: transparent;
            color: {COLOR_TEXT_PRIMARY};
        }}
    """)
    main_window.nav_header.title_label.setStyleSheet(
        f"color: {COLOR_TEXT_PRIMARY};"
    )
    main_window.nav_header.breadcrumb_label.setStyleSheet(
        f"color: {COLOR_TEXT_SECONDARY};"
    )


def apply_theme(main_window):
    """Full theme refresh: content frame + status bar + nav header."""
    refresh_content_frame(main_window)
    refresh_status_bar_labels(main_window)

"""
Sidebar style constants and generators.

All stylesheet generation for sidebar buttons, headers, scroll area, and
brand area. Uses design tokens from ui.constants — no hardcoded values.
"""

from ui.constants import (
    SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    BORDER_RADIUS_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG,
    TEXT_CARD_TITLE, TEXT_LABEL, TEXT_BODY,
    COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
    COLOR_BG_HOVER, COLOR_BG_FOCUS, COLOR_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_DANGER, COLOR_DANGER_HOVER, COLOR_DANGER_ACTIVE,
    COLOR_SIDEBAR_ACTIVE_BG, COLOR_SIDEBAR_ACTIVE_BORDER,
)


# ── Scroll area ──────────────────────────────────────────────────────

SCROLL_AREA_STYLE = f"""
    QScrollArea {{
        border: none;
        background-color: {COLOR_BG_MAIN};
    }}
    QScrollArea>QWidget>QScrollBar:vertical {{
        background: {COLOR_BG_MAIN};
        width: 8px;
    }}
    QScrollArea>QWidget>QScrollBar::handle:vertical {{
        background: {COLOR_BORDER};
        border-radius: {BORDER_RADIUS_SM};
    }}
    QScrollArea>QWidget>QScrollBar::add-line:vertical,
    QScrollArea>QWidget>QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""


# ── Navigation button styles ─────────────────────────────────────────

def nav_button_style() -> str:
    """Default (inactive) nav button style."""
    return f"""
        EnterpriseButton {{
            background-color: transparent;
            color: {COLOR_TEXT_SECONDARY};
            border: none;
            border-radius: {BORDER_RADIUS_MD};
            text-align: left;
            padding-left: {SPACING_LG}px;
            padding-top: {SPACING_XS}px;
            padding-bottom: {SPACING_XS}px;
            font-weight: 400;
            min-height: 20px;
        }}
        EnterpriseButton:hover {{
            background-color: {COLOR_BG_HOVER};
            color: {COLOR_TEXT_PRIMARY};
        }}
        EnterpriseButton:pressed {{
            background-color: {COLOR_BG_FOCUS};
            color: {COLOR_TEXT_PRIMARY};
        }}
    """


def nav_button_active_style() -> str:
    """Active (selected) nav button style."""
    return f"""
        EnterpriseButton {{
            background-color: {COLOR_SIDEBAR_ACTIVE_BG};
            color: {COLOR_TEXT_PRIMARY};
            border: none;
            border-left: 3px solid {COLOR_SIDEBAR_ACTIVE_BORDER};
            border-radius: {BORDER_RADIUS_MD};
            text-align: left;
            padding-left: {SPACING_LG - 3}px;
            font-weight: 600;
        }}
        EnterpriseButton:hover {{
            background-color: {COLOR_SIDEBAR_ACTIVE_BG};
            color: {COLOR_TEXT_PRIMARY};
        }}
    """


# ── Group header style ───────────────────────────────────────────────

def group_header_style() -> str:
    """Collapsible group header button style."""
    return f"""
        EnterpriseButton {{
            background-color: transparent;
            border: none;
            text-align: left;
            padding-left: {SPACING_SM}px;
            padding-top: {SPACING_XS}px;
            padding-bottom: {SPACING_XS}px;
            color: {COLOR_PRIMARY};
            font-weight: bold;
            font-size: {TEXT_CARD_TITLE}px;
            min-height: 24px;
        }}
        EnterpriseButton:hover {{
            background-color: {COLOR_BG_HOVER};
            color: {COLOR_PRIMARY_HOVER};
        }}
    """


# ── Theme refresh styles (used by _refresh_all_styles) ──────────────

def sidebar_container_style() -> str:
    return f"""
        Sidebar {{
            background-color: {COLOR_BG_ELEVATED};
            border-right: 1px solid {COLOR_BORDER};
        }}
        QLabel#sidebar_header {{
            color: {COLOR_TEXT_PRIMARY};
            font-weight: bold;
            padding: {SPACING_SM}px;
        }}
    """


def group_header_theme_style() -> str:
    """Theme-refreshed group header style (uses TEXT_PRIMARY instead of COLOR_PRIMARY)."""
    return f"""
        EnterpriseButton {{
            background-color: transparent;
            border: none;
            text-align: left;
            padding-left: {SPACING_SM}px;
            color: {COLOR_TEXT_PRIMARY};
            font-weight: bold;
            font-size: {TEXT_CARD_TITLE}px;
        }}
        EnterpriseButton:hover {{
            background-color: {COLOR_BG_HOVER};
        }}
    """


def logout_button_style() -> str:
    return f"""
        EnterpriseButton {{
            background-color: {COLOR_DANGER};
            color: {COLOR_TEXT_ON_PRIMARY};
            border: none;
            border-radius: {BORDER_RADIUS_LG};
            padding: {SPACING_MD}px;
        }}
        EnterpriseButton:hover {{
            background-color: {COLOR_DANGER_HOVER};
        }}
        EnterpriseButton:pressed {{
            background-color: {COLOR_DANGER_ACTIVE};
        }}
    """

"""UI constants for consistent styling across the ERP application."""

# ═══════════════════════════════════════════════════════════════
# LIVE THEME SYSTEM — colors switch at runtime
# ═══════════════════════════════════════════════════════════════
# The module-level COLOR_* variables default to DARK theme.
# Call ``set_active_theme("light")`` or ``set_active_theme("dark")``
# to update all COLOR_* globals instantly.
#
# ThemeEngine (theme/theme_engine.py) calls this automatically;
# individual screens import COLOR_* as usual.
# ═══════════════════════════════════════════════════════════════

_active_theme_name: str = "dark"

_THEME_DARK = {
    # Primary colors
    "COLOR_PRIMARY": "#89b4fa",
    "COLOR_PRIMARY_HOVER": "#74c7ec",
    "COLOR_PRIMARY_ACTIVE": "#89dceb",
    "COLOR_PRIMARY_MUTED": "#45475a",
    # Semantic colors
    "COLOR_SUCCESS": "#a6e3a1",
    "COLOR_SUCCESS_HOVER": "#94e2d5",
    "COLOR_SUCCESS_ACTIVE": "#74c7a0",
    "COLOR_SUCCESS_MUTED": "#45475a",
    "COLOR_SUCCESS_BG": "#1e3a2f",
    "COLOR_WARNING": "#f9e2af",
    "COLOR_WARNING_HOVER": "#fab387",
    "COLOR_WARNING_ACTIVE": "#f38ba8",
    "COLOR_WARNING_MUTED": "#45475a",
    "COLOR_WARNING_BG": "#3a3520",
    "COLOR_DANGER": "#f38ba8",
    "COLOR_DANGER_HOVER": "#eba0ac",
    "COLOR_DANGER_ACTIVE": "#dc2626",
    "COLOR_DANGER_MUTED": "#45475a",
    "COLOR_DANGER_BG": "#3a1f2a",
    "COLOR_INFO": "#89b4fa",
    "COLOR_INFO_HOVER": "#74c7ec",
    "COLOR_INFO_ACTIVE": "#89dceb",
    "COLOR_INFO_MUTED": "#45475a",
    "COLOR_INFO_BG": "#1e2a3a",
    # Backgrounds
    "COLOR_BG_MAIN": "#1e1e2e",
    "COLOR_BG_SURFACE": "#282838",
    "COLOR_BG_ELEVATED": "#313244",
    "COLOR_BG_INPUT": "#1e1e2e",
    # Text
    "COLOR_TEXT_PRIMARY": "#cdd6f4",
    "COLOR_TEXT_SECONDARY": "#a6adc8",
    "COLOR_TEXT_MUTED": "#6c7086",
    "COLOR_TEXT_ON_PRIMARY": "#11111b",
    # Light-theme-named tokens (dark values — used as-is in dark mode)
    "COLOR_BG_LIGHT": "#313244",
    "COLOR_BG_LIGHT_SURFACE": "#313244",
    "COLOR_TEXT_LIGHT": "#cdd6f4",
    "COLOR_TEXT_SECONDARY_LIGHT": "#a6adc8",
    "COLOR_TEXT_DIALOG": "#cdd6f4",
    "COLOR_BORDER_LIGHT_THEME": "#45475a",
    "COLOR_MUTED_LIGHT": "#6c7086",
    "COLOR_BG_BUTTON_LIGHT": "#585b70",
    "COLOR_BG_BUTTON_SECONDARY": "#45475a",
    # Secondary button
    "COLOR_SECONDARY_BG": "#45475a",
    "COLOR_SECONDARY_HOVER": "#585b70",
    "COLOR_SECONDARY_TEXT": "#cdd6f4",
    "COLOR_SECONDARY_ACTIVE": "#6c7086",
    # Borders
    "COLOR_BORDER": "#45475a",
    "COLOR_BORDER_LIGHT": "#38384a",
    "COLOR_BORDER_FOCUS": "#89b4fa",
    "COLOR_BORDER_DIALOG": "#45475a",
    "COLOR_BORDER_TABLE": "#45475a",
    "COLOR_BORDER_INPUT": "#45475a",
    "COLOR_TABLE_GRIDLINE": "#45475a",
    "COLOR_TEXT_TITLE": "#cdd6f4",
    "COLOR_HEADER_DARK": "#11111b",
    # Tables
    "COLOR_TABLE_HEADER": "#313244",
    "COLOR_TABLE_ALT": "#282838",
    "COLOR_TABLE_GRID": "#45475a",
    "COLOR_TABLE_BORDER_LIGHT": "#585b70",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#45475a",
    "COLOR_FORM_BORDER_LIGHT": "#585b70",
    "COLOR_FORM_TEXT_LIGHT": "#cdd6f4",
    "COLOR_UI_DIVIDER_LIGHT": "#45475a",
    # Status indicators
    "COLOR_STATUS_VALID": "#a6e3a1",
    "COLOR_STATUS_INVALID": "#f38ba8",
    "COLOR_STATUS_WARNING": "#fab387",
    "COLOR_STATUS_PENDING": "#f9e2af",
    # Brand
    "COLOR_WHATSAPP": "#25D366",
}

_THEME_LIGHT = {
    "COLOR_PRIMARY": "#4a8ae8",
    "COLOR_PRIMARY_HOVER": "#3a7ad8",
    "COLOR_PRIMARY_ACTIVE": "#2a6ac8",
    "COLOR_PRIMARY_MUTED": "#b0b8c8",
    "COLOR_SUCCESS": "#2ecc71",
    "COLOR_SUCCESS_HOVER": "#27ae60",
    "COLOR_SUCCESS_ACTIVE": "#1e9b54",
    "COLOR_SUCCESS_MUTED": "#b0b8c8",
    "COLOR_SUCCESS_BG": "#e8f8f0",
    "COLOR_WARNING": "#f39c12",
    "COLOR_WARNING_HOVER": "#e67e22",
    "COLOR_WARNING_ACTIVE": "#d35400",
    "COLOR_WARNING_MUTED": "#b0b8c8",
    "COLOR_WARNING_BG": "#fef5e7",
    "COLOR_DANGER": "#e74c3c",
    "COLOR_DANGER_HOVER": "#c0392b",
    "COLOR_DANGER_ACTIVE": "#a93226",
    "COLOR_DANGER_MUTED": "#b0b8c8",
    "COLOR_DANGER_BG": "#fdedec",
    "COLOR_INFO": "#3498db",
    "COLOR_INFO_HOVER": "#2980b9",
    "COLOR_INFO_ACTIVE": "#1f6da0",
    "COLOR_INFO_MUTED": "#b0b8c8",
    "COLOR_INFO_BG": "#eaf2f8",
    "COLOR_BG_MAIN": "#f4f5f8",
    "COLOR_BG_SURFACE": "#ffffff",
    "COLOR_BG_ELEVATED": "#e8eaf0",
    "COLOR_BG_INPUT": "#ffffff",
    "COLOR_TEXT_PRIMARY": "#1a1b2e",
    "COLOR_TEXT_SECONDARY": "#5a5b7a",
    "COLOR_TEXT_MUTED": "#9a9bb0",
    "COLOR_TEXT_ON_PRIMARY": "#ffffff",
    "COLOR_BG_LIGHT": "#f4f5f8",
    "COLOR_BG_LIGHT_SURFACE": "#ffffff",
    "COLOR_TEXT_LIGHT": "#1a1b2e",
    "COLOR_TEXT_SECONDARY_LIGHT": "#5a5b7a",
    "COLOR_TEXT_DIALOG": "#1a1b2e",
    "COLOR_BORDER_LIGHT_THEME": "#d1d3dc",
    "COLOR_MUTED_LIGHT": "#9a9bb0",
    "COLOR_BG_BUTTON_LIGHT": "#e8eaf0",
    "COLOR_BG_BUTTON_SECONDARY": "#dcdee5",
    "COLOR_SECONDARY_BG": "#dcdee5",
    "COLOR_SECONDARY_HOVER": "#c5c7d0",
    "COLOR_SECONDARY_TEXT": "#1a1b2e",
    "COLOR_SECONDARY_ACTIVE": "#b0b8c8",
    "COLOR_BORDER": "#d1d3dc",
    "COLOR_BORDER_LIGHT": "#e5e6ed",
    "COLOR_BORDER_FOCUS": "#4a8ae8",
    "COLOR_BORDER_DIALOG": "#d1d3dc",
    "COLOR_BORDER_TABLE": "#d1d3dc",
    "COLOR_BORDER_INPUT": "#c5c7d0",
    "COLOR_TABLE_GRIDLINE": "#d1d3dc",
    "COLOR_TEXT_TITLE": "#1a1b2e",
    "COLOR_HEADER_DARK": "#2c3e70",
    "COLOR_TABLE_HEADER": "#dcdee5",
    "COLOR_TABLE_ALT": "#f4f5f8",
    "COLOR_TABLE_GRID": "#d1d3dc",
    "COLOR_TABLE_BORDER_LIGHT": "#c5c7d0",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#dcdee5",
    "COLOR_FORM_BORDER_LIGHT": "#c5c7d0",
    "COLOR_FORM_TEXT_LIGHT": "#1a1b2e",
    "COLOR_UI_DIVIDER_LIGHT": "#d1d3dc",
    "COLOR_STATUS_VALID": "#27ae60",
    "COLOR_STATUS_INVALID": "#e74c3c",
    "COLOR_STATUS_WARNING": "#e67e22",
    "COLOR_STATUS_PENDING": "#f39c12",
    "COLOR_WHATSAPP": "#25D366",
}


def set_active_theme(theme_name: str) -> None:
    """Update all COLOR_* globals to the named theme's palette."""
    global _active_theme_name
    pool = _THEME_LIGHT if theme_name == "light" else _THEME_DARK
    _active_theme_name = theme_name
    g = globals()
    for name, value in pool.items():
        g[name] = value
    g["COLOR_TEXT"] = g["COLOR_TEXT_PRIMARY"]
    g["COLOR_BACKGROUND"] = g["COLOR_BG_MAIN"]


def get_active_theme() -> str:
    """Return ``"dark"`` or ``"light"`` depending on active palette."""
    return _active_theme_name


def get_active_colors() -> dict:
    """Return the full color dict for the active theme."""
    return _THEME_LIGHT if _active_theme_name == "light" else _THEME_DARK


# ═══════════════════════════════════════════════════════════════
# Apply DARK defaults so existing imports work unchanged.
# ═══════════════════════════════════════════════════════════════
set_active_theme("dark")

# Spacing constants (in pixels)
SPACING_NONE = 0
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 20
SPACING_XXL = 24

# Font sizes (in points)
FONT_SIZE_XS = 9
FONT_SIZE_SM = 10
FONT_SIZE_MD = 11
FONT_SIZE_LG = 12
FONT_SIZE_XL = 13
FONT_SIZE_XXL = 14
FONT_SIZE_TITLE = 18
FONT_SIZE_HEADER = 20
FONT_SIZE_SECTION = 22

# Button heights
BUTTON_HEIGHT_SM = 32
BUTTON_HEIGHT_MD = 36
BUTTON_HEIGHT_LG = 40
BUTTON_HEIGHT_XL = 44

# Input field heights
INPUT_HEIGHT_SM = 32
INPUT_HEIGHT_MD = 38
INPUT_HEIGHT_LG = 44
INPUT_HEIGHT_XL = 50

# Table row heights
TABLE_ROW_HEIGHT_SM = 28
TABLE_ROW_HEIGHT_MD = 32
TABLE_ROW_HEIGHT_LG = 36

# Multiline text area heights
TEXT_AREA_MIN_HEIGHT = 80
TEXT_AREA_MAX_HEIGHT = 120
TEXT_AREA_DESCRIPTION_HEIGHT = 100

# Border radius
BORDER_RADIUS_SM = 4
BORDER_RADIUS_MD = 6
BORDER_RADIUS_LG = 8
BORDER_RADIUS_PILL = 20

# Opacity values
OPACITY_DISABLED = 0.5
OPACITY_HOVER = 0.8
OPACITY_PRESSED = 0.6

# Duration for animations (in milliseconds)
ANIMATION_FAST = 150
ANIMATION_NORMAL = 250
ANIMATION_SLOW = 350

# Z-index values for layering
Z_INDEX_BACKGROUND = 0
Z_INDEX_CONTENT = 1
Z_INDEX_OVERLAY = 2
Z_INDEX_TOOLTIP = 3
Z_INDEX_MODAL = 4
Z_INDEX_TOAST = 5

# ═══════════════════════════════════════════════════════════════
# COLOR TOKENS — sourced from the active theme dict above.
# Values change at runtime when ``set_active_theme()`` is called.
# ═══════════════════════════════════════════════════════════════
# All COLOR_* variables are set by ``set_active_theme("dark")``
# at module init.  See the _THEME_DARK / _THEME_LIGHT dicts above.

# =====================================================
# PHASE 2: LAYOUT TOKENIZATION
# =====================================================

# Spacing is already defined at the top of this file
# Added additional layout constants

# Standardized margins
MARGIN_PAGE = 25
MARGIN_CARD = 16
MARGIN_FORM = 12
MARGIN_VERTICAL_SM = 5
MARGIN_COMPACT_H = 8
MARGIN_COMPACT_V = 5
MARGIN_TOOLBAR = 5
MARGIN_DIALOG_HEADER = 8

# Standardized paddings
PADDING_BUTTON_H = 16
PADDING_BUTTON_V = 8
PADDING_INPUT_H = 10
PADDING_INPUT_V = 6
PADDING_CARD = 16
PADDING_DIALOG = 24

# Legacy color aliases (for backward compatibility)
COLOR_TEXT = COLOR_TEXT_PRIMARY
COLOR_BACKGROUND = COLOR_BG_MAIN
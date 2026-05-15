"""UI constants for consistent styling across the ERP application."""

# ── Forward declarations for LSP (set dynamically by set_active_theme below) ──
COLOR_BG_MAIN: str = ""
COLOR_BG_SURFACE: str = ""
COLOR_BG_ELEVATED: str = ""
COLOR_BG_INPUT: str = ""
COLOR_BG_CARD: str = ""
COLOR_TEXT_PRIMARY: str = ""
COLOR_TEXT_SECONDARY: str = ""
COLOR_TEXT_MUTED: str = ""
COLOR_TEXT_ON_PRIMARY: str = ""
COLOR_TEXT_ON_SUCCESS: str = ""
COLOR_TEXT_ON_WARNING: str = ""
COLOR_TEXT_ON_DANGER: str = ""
COLOR_PRIMARY: str = ""
COLOR_PRIMARY_HOVER: str = ""
COLOR_PRIMARY_ACTIVE: str = ""
COLOR_PRIMARY_MUTED: str = ""
COLOR_SUCCESS: str = ""
COLOR_SUCCESS_HOVER: str = ""
COLOR_SUCCESS_ACTIVE: str = ""
COLOR_SUCCESS_MUTED: str = ""
COLOR_SUCCESS_BG: str = ""
COLOR_WARNING: str = ""
COLOR_WARNING_HOVER: str = ""
COLOR_WARNING_ACTIVE: str = ""
COLOR_WARNING_MUTED: str = ""
COLOR_WARNING_BG: str = ""
COLOR_DANGER: str = ""
COLOR_DANGER_HOVER: str = ""
COLOR_DANGER_ACTIVE: str = ""
COLOR_DANGER_MUTED: str = ""
COLOR_DANGER_BG: str = ""
COLOR_INFO: str = ""
COLOR_INFO_HOVER: str = ""
COLOR_INFO_ACTIVE: str = ""
COLOR_INFO_MUTED: str = ""
COLOR_INFO_BG: str = ""
COLOR_SECONDARY_BG: str = ""
COLOR_SECONDARY_HOVER: str = ""
COLOR_SECONDARY_TEXT: str = ""
COLOR_SECONDARY_ACTIVE: str = ""
COLOR_BORDER: str = ""
COLOR_BORDER_LIGHT: str = ""
COLOR_BORDER_FOCUS: str = ""
COLOR_BORDER_DIALOG: str = ""
COLOR_BORDER_TABLE: str = ""
COLOR_BORDER_INPUT: str = ""
COLOR_TABLE_GRIDLINE: str = ""
COLOR_TABLE_HEADER: str = ""
COLOR_TABLE_ALT: str = ""
COLOR_TABLE_GRID: str = ""
COLOR_TABLE_BORDER_LIGHT: str = ""
COLOR_TABLE_HEADER_BG_LIGHT: str = ""
COLOR_FORM_BORDER_LIGHT: str = ""
COLOR_FORM_TEXT_LIGHT: str = ""
COLOR_BG_LIGHT: str = ""
COLOR_BG_LIGHT_SURFACE: str = ""
COLOR_TEXT_LIGHT: str = ""
COLOR_TEXT_SECONDARY_LIGHT: str = ""
COLOR_TEXT_DIALOG: str = ""
COLOR_BORDER_LIGHT_THEME: str = ""
COLOR_MUTED_LIGHT: str = ""
COLOR_BG_BUTTON_LIGHT: str = ""
COLOR_BG_BUTTON_SECONDARY: str = ""
COLOR_UI_DIVIDER_LIGHT: str = ""
COLOR_STATUS_VALID: str = ""
COLOR_STATUS_INVALID: str = ""
COLOR_STATUS_WARNING: str = ""
COLOR_STATUS_PENDING: str = ""
COLOR_TEXT_TITLE: str = ""
COLOR_HEADER_DARK: str = ""
COLOR_WHATSAPP: str = ""
COLOR_TEXT: str = ""
COLOR_BACKGROUND: str = ""

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

# ═══════════════════════════════════════════════════════════════
# PHASE 15A: CONTRAST REBALANCING + COLOR ROLE SEPARATION
# ═══════════════════════════════════════════════════════════════
# Color roles:
#   SURFACE  — backgrounds (main, card, elevated, input)
#   CONTENT  — text (primary, secondary, muted, on-primary)
#   STATE    — semantic (success, warning, danger, info)
#
# Contrast rules enforced:
#   - TEXT_* never within ±10% luminance of background
#   - COLOR_MUTED never used on PRIMARY backgrounds
#   - Disabled states remain readable (≥3:1 ratio)
#   - KPI values pass AA-level contrast (≥4.5:1)
# ═══════════════════════════════════════════════════════════════

_active_theme_name: str = "dark"

_THEME_DARK = {
    # ── SURFACE COLORS ──
    "COLOR_BG_MAIN": "#1e1e2e",
    "COLOR_BG_SURFACE": "#282838",
    "COLOR_BG_ELEVATED": "#313244",
    "COLOR_BG_INPUT": "#1e1e2e",
    "COLOR_BG_CARD": "#282838",

    # ── CONTENT COLORS (high contrast against surfaces) ──
    "COLOR_TEXT_PRIMARY": "#e5e8f0",       # was #cdd6f4 — brighter for better contrast
    "COLOR_TEXT_SECONDARY": "#b8bdd0",     # was #a6adc8 — slightly brighter
    "COLOR_TEXT_MUTED": "#7a7f96",         # was #6c7086 — readable on dark surfaces
    "COLOR_TEXT_ON_PRIMARY": "#0f1118",    # dark text on primary buttons
    "COLOR_TEXT_ON_SUCCESS": "#0f1a14",    # dark text on success badges
    "COLOR_TEXT_ON_WARNING": "#1a1508",    # dark text on warning badges
    "COLOR_TEXT_ON_DANGER": "#1a0f12",     # dark text on danger badges

    # ── PRIMARY BRAND ──
    "COLOR_PRIMARY": "#89b4fa",
    "COLOR_PRIMARY_HOVER": "#74c7ec",
    "COLOR_PRIMARY_ACTIVE": "#89dceb",
    "COLOR_PRIMARY_MUTED": "#5a6a8a",      # was #45475a — more visible when disabled

    # ── STATE: SUCCESS ──
    "COLOR_SUCCESS": "#a6e3a1",
    "COLOR_SUCCESS_HOVER": "#94e2d5",
    "COLOR_SUCCESS_ACTIVE": "#74c7a0",
    "COLOR_SUCCESS_MUTED": "#5a7a6a",
    "COLOR_SUCCESS_BG": "#1e3a2f",

    # ── STATE: WARNING ──
    "COLOR_WARNING": "#f9e2af",
    "COLOR_WARNING_HOVER": "#fab387",
    "COLOR_WARNING_ACTIVE": "#f38ba8",
    "COLOR_WARNING_MUTED": "#8a7a5a",
    "COLOR_WARNING_BG": "#3a3520",

    # ── STATE: DANGER ──
    "COLOR_DANGER": "#f38ba8",
    "COLOR_DANGER_HOVER": "#eba0ac",
    "COLOR_DANGER_ACTIVE": "#dc2626",
    "COLOR_DANGER_MUTED": "#8a5a6a",
    "COLOR_DANGER_BG": "#3a1f2a",

    # ── STATE: INFO ──
    "COLOR_INFO": "#89b4fa",
    "COLOR_INFO_HOVER": "#74c7ec",
    "COLOR_INFO_ACTIVE": "#89dceb",
    "COLOR_INFO_MUTED": "#5a6a8a",
    "COLOR_INFO_BG": "#1e2a3a",

    # ── SECONDARY BUTTON ──
    "COLOR_SECONDARY_BG": "#45475a",
    "COLOR_SECONDARY_HOVER": "#585b70",
    "COLOR_SECONDARY_TEXT": "#e5e8f0",     # was #cdd6f4 — matches primary text
    "COLOR_SECONDARY_ACTIVE": "#6c7086",

    # ── BORDERS ──
    "COLOR_BORDER": "#45475a",
    "COLOR_BORDER_LIGHT": "#38384a",
    "COLOR_BORDER_FOCUS": "#89b4fa",
    "COLOR_BORDER_DIALOG": "#45475a",
    "COLOR_BORDER_TABLE": "#45475a",
    "COLOR_BORDER_INPUT": "#45475a",

    # ── TABLES ──
    "COLOR_TABLE_GRIDLINE": "#45475a",
    "COLOR_TABLE_HEADER": "#313244",
    "COLOR_TABLE_ALT": "#282838",
    "COLOR_TABLE_GRID": "#45475a",
    "COLOR_TABLE_BORDER_LIGHT": "#585b70",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#45475a",

    # ── FORMS ──
    "COLOR_FORM_BORDER_LIGHT": "#585b70",
    "COLOR_FORM_TEXT_LIGHT": "#e5e8f0",

    # ── LIGHT-THEME-NAMED TOKENS (dark values) ──
    "COLOR_BG_LIGHT": "#313244",
    "COLOR_BG_LIGHT_SURFACE": "#313244",
    "COLOR_TEXT_LIGHT": "#e5e8f0",
    "COLOR_TEXT_SECONDARY_LIGHT": "#b8bdd0",
    "COLOR_TEXT_DIALOG": "#e5e8f0",
    "COLOR_BORDER_LIGHT_THEME": "#45475a",
    "COLOR_MUTED_LIGHT": "#7a7f96",
    "COLOR_BG_BUTTON_LIGHT": "#585b70",
    "COLOR_BG_BUTTON_SECONDARY": "#45475a",
    "COLOR_UI_DIVIDER_LIGHT": "#45475a",

    # ── STATUS INDICATORS ──
    "COLOR_STATUS_VALID": "#a6e3a1",
    "COLOR_STATUS_INVALID": "#f38ba8",
    "COLOR_STATUS_WARNING": "#fab387",
    "COLOR_STATUS_PENDING": "#f9e2af",

    # ── TYPOGRAPHY ──
    "COLOR_TEXT_TITLE": "#e5e8f0",
    "COLOR_HEADER_DARK": "#0f1118",

    # ── BRAND ──
    "COLOR_WHATSAPP": "#25D366",
}

_THEME_LIGHT = {
    # ── SURFACE COLORS ──
    "COLOR_BG_MAIN": "#edeef2",
    "COLOR_BG_SURFACE": "#ffffff",
    "COLOR_BG_ELEVATED": "#f4f5f8",
    "COLOR_BG_INPUT": "#ffffff",
    "COLOR_BG_CARD": "#ffffff",

    # ── CONTENT COLORS (high contrast against light surfaces) ──
    "COLOR_TEXT_PRIMARY": "#0d0f14",       # was #111217 — darker for max contrast
    "COLOR_TEXT_SECONDARY": "#3d3f56",     # unchanged — already good
    "COLOR_TEXT_MUTED": "#6b6e82",         # was #5a5d72 — slightly darker for readability
    "COLOR_TEXT_ON_PRIMARY": "#ffffff",    # white text on primary buttons
    "COLOR_TEXT_ON_SUCCESS": "#ffffff",    # white text on success badges
    "COLOR_TEXT_ON_WARNING": "#1a1508",    # dark text on warning (light bg)
    "COLOR_TEXT_ON_DANGER": "#ffffff",     # white text on danger badges

    # ── PRIMARY BRAND ──
    "COLOR_PRIMARY": "#3a7ae8",            # was #4a8ae8 — slightly darker for better text contrast
    "COLOR_PRIMARY_HOVER": "#2a6ad8",
    "COLOR_PRIMARY_ACTIVE": "#1a5ac8",
    "COLOR_PRIMARY_MUTED": "#9aa8c8",      # was #b0b8c8 — more visible when disabled

    # ── STATE: SUCCESS ──
    "COLOR_SUCCESS": "#168a4a",            # was #1a8a4a — slightly darker
    "COLOR_SUCCESS_HOVER": "#127a3f",
    "COLOR_SUCCESS_ACTIVE": "#0e6a34",
    "COLOR_SUCCESS_MUTED": "#8aa89a",
    "COLOR_SUCCESS_BG": "#e0f5ea",

    # ── STATE: WARNING ──
    "COLOR_WARNING": "#c47a06",            # was #d48806 — darker for contrast on light bg
    "COLOR_WARNING_HOVER": "#b06a05",
    "COLOR_WARNING_ACTIVE": "#985a04",
    "COLOR_WARNING_MUTED": "#a89878",
    "COLOR_WARNING_BG": "#fef3cd",

    # ── STATE: DANGER ──
    "COLOR_DANGER": "#c42a2a",             # was #d32f2f — slightly darker
    "COLOR_DANGER_HOVER": "#a71c1c",
    "COLOR_DANGER_ACTIVE": "#901818",
    "COLOR_DANGER_MUTED": "#a88888",
    "COLOR_DANGER_BG": "#fde8e8",

    # ── STATE: INFO ──
    "COLOR_INFO": "#2978b5",
    "COLOR_INFO_HOVER": "#236ba0",
    "COLOR_INFO_ACTIVE": "#1d5e8c",
    "COLOR_INFO_MUTED": "#8898a8",
    "COLOR_INFO_BG": "#eaf2f8",

    # ── SECONDARY BUTTON ──
    "COLOR_SECONDARY_BG": "#d4d5dc",
    "COLOR_SECONDARY_HOVER": "#c0c2cc",
    "COLOR_SECONDARY_TEXT": "#0d0f14",     # was #1a1b2e — matches primary text
    "COLOR_SECONDARY_ACTIVE": "#a8abb8",

    # ── BORDERS ──
    "COLOR_BORDER": "#6b6e82",
    "COLOR_BORDER_LIGHT": "#c0c2cc",
    "COLOR_BORDER_FOCUS": "#3a7ae8",
    "COLOR_BORDER_DIALOG": "#6b6e82",
    "COLOR_BORDER_TABLE": "#6b6e82",
    "COLOR_BORDER_INPUT": "#6b6e82",

    # ── TABLES ──
    "COLOR_TABLE_GRIDLINE": "#c8cad4",
    "COLOR_TABLE_HEADER": "#e8e9ef",
    "COLOR_TABLE_ALT": "#f6f7fa",
    "COLOR_TABLE_GRID": "#c8cad4",
    "COLOR_TABLE_BORDER_LIGHT": "#a0a3b8",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#e8e9ef",

    # ── FORMS ──
    "COLOR_FORM_BORDER_LIGHT": "#a0a3b8",
    "COLOR_FORM_TEXT_LIGHT": "#0d0f14",

    # ── LIGHT-THEME-NAMED TOKENS ──
    "COLOR_BG_LIGHT": "#edeef2",
    "COLOR_BG_LIGHT_SURFACE": "#ffffff",
    "COLOR_TEXT_LIGHT": "#0d0f14",
    "COLOR_TEXT_SECONDARY_LIGHT": "#3d3f56",
    "COLOR_TEXT_DIALOG": "#0d0f14",
    "COLOR_BORDER_LIGHT_THEME": "#a0a3b8",
    "COLOR_MUTED_LIGHT": "#6b6e82",
    "COLOR_BG_BUTTON_LIGHT": "#e2e3e8",
    "COLOR_BG_BUTTON_SECONDARY": "#d4d5dc",
    "COLOR_UI_DIVIDER_LIGHT": "#a0a3b8",

    # ── STATUS INDICATORS ──
    "COLOR_STATUS_VALID": "#168a4a",
    "COLOR_STATUS_INVALID": "#c42a2a",
    "COLOR_STATUS_WARNING": "#c47a06",
    "COLOR_STATUS_PENDING": "#c47a06",

    # ── TYPOGRAPHY ──
    "COLOR_TEXT_TITLE": "#0d0f14",
    "COLOR_HEADER_DARK": "#2c3e70",

    # ── BRAND ──
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

# Legacy color aliases (for backward compatibility)
COLOR_TEXT = COLOR_TEXT_PRIMARY
COLOR_BACKGROUND = COLOR_BG_MAIN

# Spacing constants (in pixels)
SPACING_NONE = 0
SPACING_XS = 4
SPACING_6 = 6
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 20
SPACING_XXL = 24

# Font sizes (in points — also used with px suffix in stylesheets)
FONT_SIZE_8 = 8
FONT_SIZE_XS = 9
FONT_SIZE_SM = 10
FONT_SIZE_MD = 11
FONT_SIZE_LG = 12
FONT_SIZE_XL = 13
FONT_SIZE_XXL = 14
FONT_SIZE_16 = 16
FONT_SIZE_TITLE = 18
FONT_SIZE_HEADER = 20
FONT_SIZE_SECTION = 22
FONT_SIZE_24 = 24
FONT_SIZE_28 = 28

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
BORDER_RADIUS_XL = 12
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

# ═══════════════════════════════════════════════════════════════
# SEMANTIC TYPOGRAPHY ROLES — single canonical source
# ═══════════════════════════════════════════════════════════════
# All screens MUST use these semantic roles.
# Do NOT use arbitrary FONT_SIZE_* values directly for text styling.
# These are the ONLY approved sizes for each semantic role.
# ═══════════════════════════════════════════════════════════════

# Display & headings
TEXT_DISPLAY = FONT_SIZE_28           # Hero/display text (rare)
TEXT_PAGE_TITLE = FONT_SIZE_HEADER    # Page-level title (20pt)
TEXT_SECTION_TITLE = FONT_SIZE_TITLE  # Section heading (18pt)
TEXT_CARD_TITLE = FONT_SIZE_16        # Card/group title (16pt)

# Body & content
TEXT_BODY = FONT_SIZE_MD              # Body/content text (11pt)
TEXT_BODY_SMALL = FONT_SIZE_SM        # Smaller body text (10pt)

# Labels & metadata
TEXT_LABEL = FONT_SIZE_MD             # Form labels (11pt)
TEXT_LABEL_SMALL = FONT_SIZE_SM       # Compact labels (10pt)
TEXT_TABLE = FONT_SIZE_SM             # Table cell text (10pt)
TEXT_TABLE_HEADER = FONT_SIZE_XS      # Table header text (9pt)

# Feedback & status
TEXT_HELPER = FONT_SIZE_XS            # Helper/description text (9pt)
TEXT_ERROR = FONT_SIZE_SM             # Error message text (10pt)
TEXT_BADGE = FONT_SIZE_XS             # Badge/chip text (9pt)

# Monospace
TEXT_MONO = FONT_SIZE_MD              # Code/data text (11pt)

# ═══════════════════════════════════════════════════════════════
# PHASE 15B: DENSITY ARCHITECTURE — 3-tier density model
# ═══════════════════════════════════════════════════════════════
# DENSITY_COMFORTABLE → dashboards, analytics, executive views
# DENSITY_STANDARD    → forms, CRUD screens, general operations
# DENSITY_COMPACT     → finance, tables, reports, dense data

# Base table row heights (original)
TABLE_ROW_HEIGHT_COMPACT = 26         # Financial tables, dense data
TABLE_ROW_HEIGHT_MD = 32              # Standard operational tables
TABLE_ROW_HEIGHT_RELAXED = 40         # Touch/kiosk interfaces

# Column header heights
TABLE_HEADER_HEIGHT_COMPACT = 28
TABLE_HEADER_HEIGHT_MD = 32
TABLE_HEADER_HEIGHT_RELAXED = 38

# Density tier: spacing multipliers
DENSITY_COMFORTABLE_SPACING = SPACING_XL    # 20px
DENSITY_STANDARD_SPACING = SPACING_MD       # 12px
DENSITY_COMPACT_SPACING = SPACING_SM        # 8px

# Density tier: table row heights (aliases for clarity)
DENSITY_COMFORTABLE_ROW = TABLE_ROW_HEIGHT_RELAXED   # 40px
DENSITY_STANDARD_ROW = TABLE_ROW_HEIGHT_MD           # 32px
DENSITY_COMPACT_ROW = TABLE_ROW_HEIGHT_COMPACT       # 26px

# Density tier: form input heights
DENSITY_COMFORTABLE_INPUT = INPUT_HEIGHT_LG   # 44px
DENSITY_STANDARD_INPUT = INPUT_HEIGHT_MD      # 38px
DENSITY_COMPACT_INPUT = INPUT_HEIGHT_SM       # 32px

# Density tier: KPI card heights
DENSITY_COMFORTABLE_KPI = 120     # Dashboard cards
DENSITY_STANDARD_KPI = 90         # Standard metrics
DENSITY_COMPACT_KPI = 60          # Compact metrics

# Density tier: page margins
DENSITY_COMFORTABLE_MARGIN = 32
DENSITY_STANDARD_MARGIN = MARGIN_PAGE    # 25
DENSITY_COMPACT_MARGIN = 16

# ═══════════════════════════════════════════════════════════════
# PHASE 15A: CONTRAST VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════
# Forbidden combinations (will fail contrast checks):
#   - COLOR_TEXT_MUTED on COLOR_PRIMARY background
#   - COLOR_TEXT_MUTED on COLOR_SUCCESS/DANGER/WARNING backgrounds
#   - COLOR_SECONDARY_TEXT on COLOR_SECONDARY_BG (light theme)
#
# Required minimum contrast ratios (WCAG AA equivalent):
#   - Normal text: 4.5:1
#   - Large text (18pt+): 3:1
#   - UI components: 3:1

# ═══════════════════════════════════════════════════════════════
# PHASE 2: STATE MESSAGE TOKENS
# ═══════════════════════════════════════════════════════════════

# Standardized state messages (use with StateHelper)
STATE_LOADING = "Loading\u2026"
STATE_EMPTY_TITLE = "No data available"
STATE_EMPTY_SUBTITLE = "Records will appear here once created"
STATE_ERROR_TITLE = "Unable to load data"
STATE_ERROR_RETRY = "Retry"
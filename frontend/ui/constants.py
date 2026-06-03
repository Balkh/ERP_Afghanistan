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
COLOR_BORDER_INPUT_HOVER: str = ""
COLOR_BORDER_FOCUS_RING: str = ""
COLOR_BORDER_SECTION: str = ""
COLOR_BG_DIALOG: str = ""
COLOR_BG_SECTION: str = ""
COLOR_BG_TOOLTIP: str = ""
COLOR_BG_HOVER: str = ""
COLOR_BG_FOCUS: str = ""
COLOR_FORM_LABEL: str = ""
COLOR_FORM_LABEL_REQUIRED: str = ""
COLOR_FORM_DESCRIPTION_BG: str = ""
COLOR_FORM_SECTION_TITLE: str = ""
COLOR_FORM_SECTION_DIVIDER: str = ""
COLOR_FORM_FOOTER_BORDER: str = ""
COLOR_FOCUS_RING: str = ""
COLOR_FOCUS_RING_ALPHA: str = ""
COLOR_HOVER_OVERLAY: str = ""
COLOR_PRESSED_OVERLAY: str = ""
COLOR_HELPER_TEXT: str = ""
COLOR_VALID_SUCCESS: str = ""
COLOR_VALID_WARNING: str = ""
COLOR_VALID_ERROR: str = ""
COLOR_VALID_BG_SUCCESS: str = ""
COLOR_VALID_BG_WARNING: str = ""
COLOR_VALID_BG_ERROR: str = ""
COLOR_INPUT_SUCCESS: str = ""
COLOR_INPUT_WARNING: str = ""
COLOR_INPUT_ERROR: str = ""
COLOR_TEXT: str = ""
COLOR_BACKGROUND: str = ""

# Dedicated table tokens (Phase 15.2)
TABLE_BG_PRIMARY: str = ""
TABLE_BG_SECONDARY: str = ""
TABLE_BG_HOVER: str = ""
TABLE_BG_SELECTED: str = ""
TABLE_GRID_COLOR: str = ""
TABLE_TEXT_PRIMARY: str = ""
TABLE_TEXT_MUTED: str = ""
TABLE_TEXT_SELECTED: str = ""
TABLE_HEADER_BG: str = ""
TABLE_HEADER_TEXT: str = ""
TABLE_SCROLLBAR_BG: str = ""
TABLE_SCROLLBAR_HANDLE: str = ""

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
    "COLOR_BG_INPUT": "#181825",
    "COLOR_BG_CARD": "#282838",
    "COLOR_BG_DIALOG": "#282838",
    "COLOR_BG_SECTION": "#282838",
    "COLOR_BG_TOOLTIP": "#313244",
    "COLOR_BG_HOVER": "#2a2a3c",
    "COLOR_BG_FOCUS": "#2e2e42",

    # ── CONTENT COLORS (high contrast against surfaces) ──
    "COLOR_TEXT_PRIMARY": "#e5e8f0",       # was #cdd6f4 — brighter for better contrast
    "COLOR_TEXT_SECONDARY": "#b8bdd0",     # was #a6adc8 — slightly brighter
    "COLOR_TEXT_MUTED": "#8a8fa6",         # raised from #7a7f96 — passes AA on dark surfaces (4.7:1)
    "COLOR_TEXT_ON_PRIMARY": "#0f1118",    # dark text on primary buttons
    "COLOR_TEXT_ON_SUCCESS": "#0f1a14",    # dark text on success badges
    "COLOR_TEXT_ON_WARNING": "#1a1508",    # dark text on warning badges
    "COLOR_TEXT_ON_DANGER": "#1a0f12",     # dark text on danger badges
    "COLOR_TEXT_ON_HEADER": "#e5e8f0",     # readable text on dark dialog headers (Phase Recovery)
    "COLOR_TEXT_DISABLED": "#9a9fb6",      # readable disabled text on dark (Phase Recovery)
    "COLOR_BG_DISABLED": "#2a2a3c",        # distinct disabled background (Phase Recovery)
    "COLOR_HELPER_TEXT_DARK": "#8a8fa6",   # AA-passing helper text on dark (Phase Recovery)
    "COLOR_SIDEBAR_ACTIVE_BG": "#364a6a",  # clear active sidebar item (Phase Recovery)
    "COLOR_SIDEBAR_ACTIVE_BORDER": "#89b4fa",  # left-border accent for active items (Phase Recovery)

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
    "COLOR_SUCCESS_BG": "#1e3a2e",

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
    "COLOR_BORDER_INPUT_HOVER": "#585b70",
    "COLOR_BORDER_FOCUS_RING": "#89b4fa",
    "COLOR_BORDER_SECTION": "#38384a",

    # ── TABLES ──
    "COLOR_TABLE_GRIDLINE": "#45475a",
    "COLOR_TABLE_HEADER": "#313244",
    "COLOR_TABLE_ALT": "#282838",
    "COLOR_TABLE_GRID": "#45475a",
    "COLOR_TABLE_BORDER_LIGHT": "#585b70",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#45475a",

    # ── DEDICATED TABLE TOKENS (Phase 15.2) ──
    "TABLE_BG_PRIMARY": "#1f2430",
    "TABLE_BG_SECONDARY": "#252b39",
    "TABLE_BG_HOVER": "#2f3548",
    "TABLE_BG_SELECTED": "#364a6a",
    "TABLE_GRID_COLOR": "#45475a",
    "TABLE_TEXT_PRIMARY": "#e5e8f0",
    "TABLE_TEXT_MUTED": "#7a7f96",
    "TABLE_TEXT_SELECTED": "#fff",
    "TABLE_HEADER_BG": "#282838",
    "TABLE_HEADER_TEXT": "#b8bdd0",
    "TABLE_SCROLLBAR_BG": "#1e1e2e",
    "TABLE_SCROLLBAR_HANDLE": "#45475a",

    # ── FORMS ──
    "COLOR_FORM_BORDER_LIGHT": "#585b70",
    "COLOR_FORM_TEXT_LIGHT": "#e5e8f0",
    "COLOR_FORM_LABEL": "#b8bdd0",
    "COLOR_FORM_LABEL_REQUIRED": "#f38ba8",
    "COLOR_FORM_DESCRIPTION_BG": "#242436",
    "COLOR_FORM_SECTION_TITLE": "#e5e8f0",
    "COLOR_FORM_SECTION_DIVIDER": "#38384a",
    "COLOR_FORM_FOOTER_BORDER": "#38384a",

    # ── INTERACTION ──
    "COLOR_FOCUS_RING": "#89b4fa",
    "COLOR_FOCUS_RING_ALPHA": "rgba(137, 180, 250, 0.25)",
    "COLOR_HOVER_OVERLAY": "rgba(255, 255, 255, 0.04)",
    "COLOR_PRESSED_OVERLAY": "rgba(255, 255, 255, 0.08)",

    # ── VALIDATION ──
    "COLOR_HELPER_TEXT": "#6c7086",
    "COLOR_VALID_SUCCESS": "#a6e3a1",
    "COLOR_VALID_WARNING": "#f9e2af",
    "COLOR_VALID_ERROR": "#f38ba8",
    "COLOR_VALID_BG_SUCCESS": "#1e3a2e",
    "COLOR_VALID_BG_WARNING": "#3a3520",
    "COLOR_VALID_BG_ERROR": "#3a1f2a",
    "COLOR_INPUT_SUCCESS": "#4a8a5a",
    "COLOR_INPUT_WARNING": "#8a7a3a",
    "COLOR_INPUT_ERROR": "#8a3a4a",

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
    "COLOR_BG_MAIN": "#f8fafc",            # Slate-50: Clean, modern off-white
    "COLOR_BG_SURFACE": "#fff",         # Pure white for cards/surfaces
    "COLOR_BG_ELEVATED": "#fff",        # Elevated surfaces
    "COLOR_BG_INPUT": "#fff",           # Pure white for inputs (better contrast)
    "COLOR_BG_CARD": "#fff",
    "COLOR_BG_DIALOG": "#fff",
    "COLOR_BG_SECTION": "#f1f5f9",         # Slate-100: Subtle distinction for sections
    "COLOR_BG_TOOLTIP": "#1e293b",         # Slate-800: Dark tooltip for light theme
    "COLOR_BG_HOVER": "#f1f5f9",           # Slate-100
    "COLOR_BG_FOCUS": "#e2e8f0",           # Slate-200

    # ── CONTENT COLORS (High contrast) ──
    "COLOR_TEXT_PRIMARY": "#020617",       # Slate-950: Almost black for maximum readability
    "COLOR_TEXT_SECONDARY": "#334155",     # Slate-700: Strong gray
    "COLOR_TEXT_MUTED": "#64748b",         # Slate-500: Muted but still readable
    "COLOR_TEXT_ON_PRIMARY": "#fff",
    "COLOR_TEXT_ON_SUCCESS": "#fff",
    "COLOR_TEXT_ON_WARNING": "#020617",
    "COLOR_TEXT_ON_DANGER": "#fff",

    # ── PRIMARY BRAND (Modern Indigo/Blue) ──
    "COLOR_PRIMARY": "#2563eb",            # Blue-600
    "COLOR_PRIMARY_HOVER": "#1d4ed8",      # Blue-700
    "COLOR_PRIMARY_ACTIVE": "#1e40af",    # Blue-800
    "COLOR_PRIMARY_MUTED": "#93c5fd",      # Blue-300
    "COLOR_PRIMARY_BG": "#eff6fe",        # Blue-50

    # ── STATE COLORS (Semantic) ──
    "COLOR_SUCCESS": "#059669",            # Emerald-600
    "COLOR_SUCCESS_HOVER": "#047857",      # Emerald-700
    "COLOR_SUCCESS_ACTIVE": "#065f46",
    "COLOR_SUCCESS_MUTED": "#6ee7b7",
    "COLOR_SUCCESS_BG": "#ecfdf5",         # Emerald-50

    # ── STATE: WARNING ──
    "COLOR_WARNING": "#d97706",            # Amber-600
    "COLOR_WARNING_HOVER": "#b45309",      # Amber-700
    "COLOR_WARNING_ACTIVE": "#92400e",
    "COLOR_WARNING_MUTED": "#fcd34d",
    "COLOR_WARNING_BG": "#fffbeb",         # Amber-50

    # ── STATE: DANGER ──
    "COLOR_DANGER": "#e11d48",             # Rose-600
    "COLOR_DANGER_HOVER": "#be123c",       # Rose-700
    "COLOR_DANGER_ACTIVE": "#9f1239",
    "COLOR_DANGER_MUTED": "#fda4af",
    "COLOR_DANGER_BG": "#fff1f2",         # Rose-50

    # ── STATE: INFO ──
    "COLOR_INFO": "#0ea5e9",               # Sky-500
    "COLOR_INFO_HOVER": "#0284c7",
    "COLOR_INFO_ACTIVE": "#0369a1",
    "COLOR_INFO_MUTED": "#7dd3fc",
    "COLOR_INFO_BG": "#f0f9ff",

    # ── BORDERS ──
    "COLOR_BORDER": "#cbd5e1",             # Slate-300: Visible border
    "COLOR_BORDER_LIGHT": "#e2e8f0",       # Slate-200
    "COLOR_BORDER_FOCUS": "#2563eb",
    "COLOR_BORDER_DIALOG": "#cbd5e1",
    "COLOR_BORDER_TABLE": "#cbd5e1",
    "COLOR_BORDER_INPUT": "#94a3b8",       # Slate-400: Clear input borders
    "COLOR_BORDER_INPUT_HOVER": "#64748b", # Slate-500
    "COLOR_BORDER_FOCUS_RING": "rgba(37, 99, 235, 0.2)",
    "COLOR_BORDER_SECTION": "#cbd5e1",

    # ── TABLES ──
    "COLOR_TABLE_GRIDLINE": "#e2e8f0",
    "COLOR_TABLE_HEADER": "#f1f5f9",
    "COLOR_TABLE_ALT": "#f8fafc",
    "COLOR_TABLE_GRID": "#e2e8f0",
    "COLOR_TABLE_BORDER_LIGHT": "#e2e8f0",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#f1f5f9",

    # ── DEDICATED TABLE TOKENS ──
    "TABLE_BG_PRIMARY": "#fff",
    "TABLE_BG_SECONDARY": "#f8fafc",
    "TABLE_BG_HOVER": "#f1f5f9",
    "TABLE_BG_SELECTED": "#eff6fe",
    "TABLE_GRID_COLOR": "#cbd5e1",         # Visible grid lines
    "TABLE_TEXT_PRIMARY": "#020617",
    "TABLE_TEXT_MUTED": "#475569",
    "TABLE_TEXT_SELECTED": "#2563eb",
    "TABLE_HEADER_BG": "#f1f5f9",          # Stronger header bg
    "TABLE_HEADER_TEXT": "#1e293b",
    "TABLE_SCROLLBAR_BG": "#f1f5f9",
    "TABLE_SCROLLBAR_HANDLE": "#94a3b8",

    # ── FORMS ──
    "COLOR_FORM_BORDER_LIGHT": "#cbd5e1",
    "COLOR_FORM_TEXT_LIGHT": "#020617",
    "COLOR_FORM_LABEL": "#1e293b",         # Strong label color
    "COLOR_FORM_LABEL_REQUIRED": "#be123c",
    "COLOR_FORM_DESCRIPTION_BG": "#f1f5f9",
    "COLOR_FORM_SECTION_TITLE": "#020617",
    "COLOR_FORM_SECTION_DIVIDER": "#cbd5e1",
    "COLOR_FORM_FOOTER_BORDER": "#cbd5e1",

    # ── INTERACTION ──
    "COLOR_FOCUS_RING": "#2563eb",
    "COLOR_FOCUS_RING_ALPHA": "rgba(37, 99, 235, 0.15)",
    "COLOR_HOVER_OVERLAY": "rgba(15, 23, 42, 0.02)",
    "COLOR_PRESSED_OVERLAY": "rgba(15, 23, 42, 0.05)",

    # ── VALIDATION ──
    "COLOR_HELPER_TEXT": "#475569",
    "COLOR_VALID_SUCCESS": "#065f46",      # Stronger Emerald
    "COLOR_VALID_WARNING": "#92400e",      # Stronger Amber
    "COLOR_VALID_ERROR": "#9f1239",        # Stronger Rose
    "COLOR_VALID_BG_SUCCESS": "#dcfce7",
    "COLOR_VALID_BG_WARNING": "#fef3c7",
    "COLOR_VALID_BG_ERROR": "#fee2e2",
    "COLOR_INPUT_SUCCESS": "#059669",
    "COLOR_INPUT_WARNING": "#d97706",
    "COLOR_INPUT_ERROR": "#e11d48",

    # ── LIGHT-THEME-NAMED TOKENS (for legacy support) ──
    "COLOR_BG_LIGHT": "#f8fafc",
    "COLOR_BG_LIGHT_SURFACE": "#fff",
    "COLOR_TEXT_LIGHT": "#0f172a",
    "COLOR_TEXT_SECONDARY_LIGHT": "#475569",
    "COLOR_TEXT_DIALOG": "#0f172a",
    "COLOR_BORDER_LIGHT_THEME": "#e2e8f0",
    "COLOR_MUTED_LIGHT": "#94a3b8",
    "COLOR_BG_BUTTON_LIGHT": "#f8fafc",
    "COLOR_BG_BUTTON_SECONDARY": "#f1f5f9",
    "COLOR_UI_DIVIDER_LIGHT": "#e2e8f0",

    # ── STATUS INDICATORS ──
    "COLOR_STATUS_VALID": "#059669",
    "COLOR_STATUS_INVALID": "#e11d48",
    "COLOR_STATUS_WARNING": "#d97706",
    "COLOR_STATUS_PENDING": "#64748b",

    # ── TYPOGRAPHY ──
    "COLOR_TEXT_TITLE": "#0f172a",
    "COLOR_HEADER_DARK": "#0f172a",

    # ── BRAND ──
    "COLOR_WHATSAPP": "#22c55e",
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
BUTTON_HEIGHT_MD = 38
BUTTON_HEIGHT_LG = 46
BUTTON_HEIGHT_XL = 50

# Input field heights
INPUT_HEIGHT_SM = 32
INPUT_HEIGHT_MD = 38
INPUT_HEIGHT_LG = 44
INPUT_HEIGHT_XL = 50

# Table row heights (legacy — use DENSITY_*_ROW for new code)
TABLE_ROW_HEIGHT_MD = 32
TABLE_ROW_HEIGHT_LG = 36

# Multiline text area heights
TEXT_AREA_MIN_HEIGHT = 80
TEXT_AREA_MAX_HEIGHT = 120
TEXT_AREA_DESCRIPTION_HEIGHT = 100

# Border radius
BORDER_RADIUS_SM = 4
BORDER_RADIUS_MD = 8        # Modern, softer radius
BORDER_RADIUS_LG = 12       # For cards and sections
BORDER_RADIUS_XL = 16
BORDER_RADIUS_PILL = 99     # Standard pill radius

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

# ═══════════════════════════════════════════════════════════════
# PHASE 15.8: DIALOG WIDTH GOVERNANCE
# ═══════════════════════════════════════════════════════════════
DIALOG_WIDTH_MIN = 400
DIALOG_WIDTH_PREFERRED = 580
DIALOG_WIDTH_MAX = 720
DIALOG_WIDTH_FORM_MIN = 520
DIALOG_WIDTH_FORM_PREFERRED = 580
DIALOG_WIDTH_WIDE = 900

# Adaptive breakpoints (in pixels)
BREAKPOINT_2COL = 600   # below this, 2-column collapses to 1-column

# ═══════════════════════════════════════════════════════════════
# PHASE 15.8: SECTION SPACING & VISUAL HIERARCHY
# ═══════════════════════════════════════════════════════════════
SECTION_VERTICAL_SPACING = SPACING_XXL  # 24px between sections
SECTION_TITLE_SPACING = SPACING_LG      # 16px below section title
SECTION_CONTENT_SPACING = SPACING_MD    # 12px within section content
SECTION_DIVIDER_HEIGHT = 1              # px

# Surface elevation (z-depth simulation via borders/shading)
# Higher number = visually closer to user
ELEVATION_DIALOG = 4     # Dialog windows (highest)
ELEVATION_SECTION = 2    # Form sections (medium)
ELEVATION_CARD = 1       # Cards (low)
ELEVATION_INPUT = 0      # Input fields (base)

# ═══════════════════════════════════════════════════════════════
# PHASE 15.8: INTERACTION TIMING
# ═══════════════════════════════════════════════════════════════
FOCUS_TRANSITION_MS = 150
HOVER_TRANSITION_MS = 100

# ═══════════════════════════════════════════════════════════════
# PHASE 15.9: LINE-HEIGHT RHYTHM
# ═══════════════════════════════════════════════════════════════
LINE_HEIGHT_TIGHT = 1.2
LINE_HEIGHT_NORMAL = 1.4
LINE_HEIGHT_RELAXED = 1.6
LINE_HEIGHT_SPACED = 1.8

# ═══════════════════════════════════════════════════════════════
# PHASE 15.9: VALIDATION STATE TOKENS
# ═══════════════════════════════════════════════════════════════
HELPER_TEXT_MARGIN_TOP = 2      # px above helper text
HELPER_TEXT_MARGIN_BOTTOM = 4   # px below helper text
VALIDATION_ICON_SIZE = 14       # px for inline validation icon
VALIDATION_MESSAGE_MAX_WIDTH = 300

# ═══════════════════════════════════════════════════════════════
# PHASE 15.9: DENSITY REFINEMENT
# ═══════════════════════════════════════════════════════════════
# Comfortable mode (dialogs, forms, settings)
FORM_LABEL_SPACING = SPACING_XS       # 4px between label and input
FORM_HELPER_SPACING = SPACING_XS       # 4px above helper text
SECTION_CONTENT_PADDING_V = SPACING_SM  # 8px vertical padding within section

# Compact mode (tables, sidebar, financial)
COMPACT_ROW_PADDING_H = SPACING_SM     # 8px horizontal padding in rows
COMPACT_ROW_PADDING_V = SPACING_XS     # 4px vertical padding in rows

# ═══════════════════════════════════════════════════════════════
# PHASE 15.9: MICRO-INTERACTION TIMING
# ═══════════════════════════════════════════════════════════════
SELECTION_TRANSITION_MS = 100
TABLE_HOVER_TRANSITION_MS = 80
SIDEBAR_HOVER_TRANSITION_MS = 120

# ═══════════════════════════════════════════════════════════════
# PHASE 15.9: EMPTY STATE CONSTANTS
# ═══════════════════════════════════════════════════════════════
EMPTY_STATE_ICON_SIZE = 32     # px for empty state indicator
EMPTY_STATE_SPACING = SPACING_SM  # spacing between empty state elements

# ═══════════════════════════════════════════════════════════════
# PHASE 5: TOKEN FOUNDATION EXPANSION (Workstream A)
# ═══════════════════════════════════════════════════════════════
# Added by Phase 5 Workstream A to close the tokenization gaps
# identified in Phase 4 audit (UI_GOVERNANCE_BASELINE_2026.md).
# All values are ADDITIVE — no existing tokens were modified or removed.
# These tokens form the foundation for Workstream B (inline style
# reduction) and Phase 5 God Object decompositions.
# ═══════════════════════════════════════════════════════════════

# ── BORDER RADIUS (additional sizes) ───────────────────────────
# Fills the 4px-to-12px gap left by SM/MD/LG; adds circular/elliptical
# variants and a "no radius" token for explicitly sharp corners.
BORDER_RADIUS_NONE = 0
BORDER_RADIUS_2XS = 2
BORDER_RADIUS_2XL = 20
BORDER_RADIUS_3XL = 24
BORDER_RADIUS_CIRCLE = "50%"
BORDER_RADIUS_FULL = 9999

# ── BORDER WIDTH ───────────────────────────────────────────────
# Standardized stroke widths. HAIRLINE is the default for most
# UI components; THICK/HEAVY reserved for emphasis (focus rings,
# active borders, dividers).
BORDER_WIDTH_NONE = 0
BORDER_WIDTH_HAIRLINE = 1
BORDER_WIDTH_MEDIUM = 2
BORDER_WIDTH_THICK = 3
BORDER_WIDTH_HEAVY = 4

# ── BORDER STYLE ───────────────────────────────────────────────
# CSS border-style values. SOLID is default; DASHED/DOTTED reserved
# for placeholder states and decorative dividers.
BORDER_STYLE_SOLID = "solid"
BORDER_STYLE_DASHED = "dashed"
BORDER_STYLE_DOTTED = "dotted"
BORDER_STYLE_NONE = "none"

# ── SPACING (additional sizes) ─────────────────────────────────
# Fills the 2px-2XL gap (SPACING_XS=4 → SPACING_XXL=24, missing 2px
# and anything ≥ 24px). 2XS=2, 3XL=32, 4XL=40, 5XL=48.
SPACING_2XS = 2
SPACING_3XL = 32
SPACING_4XL = 40
SPACING_5XL = 48

# ── MARGIN (additional sizes) ──────────────────────────────────
# TIGHT/RELAXED/LOOSE are density-agnostic semantic aliases.
# SECTION matches SECTION_VERTICAL_SPACING (32px) for major dividers.
MARGIN_NONE = 0
MARGIN_TIGHT = 8
MARGIN_RELAXED = 24
MARGIN_LOOSE = 32
MARGIN_SECTION = 32

# ── ICON SIZE ──────────────────────────────────────────────────
# Standardized icon dimensions. XS/SM for inline icons (in text),
# MD for toolbars, LG/XL/2XL for empty states and hero illustrations.
ICON_SIZE_XS = 12
ICON_SIZE_SM = 16
ICON_SIZE_MD = 20
ICON_SIZE_LG = 24
ICON_SIZE_XL = 32
ICON_SIZE_2XL = 48

# ── FONT FAMILY ────────────────────────────────────────────────
# Cross-platform font stacks. PRIMARY is the app default; SECONDARY
# matches the typography of the platform OS; MONOSPACE for code, IDs,
# phone numbers, and numeric data tables.
FONT_FAMILY_PRIMARY = "'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
FONT_FAMILY_SECONDARY = "'Inter', 'Segoe UI', sans-serif"
FONT_FAMILY_MONOSPACE = "'Consolas', 'Monaco', 'Courier New', monospace"

# ── FONT WEIGHT ────────────────────────────────────────────────
# Standardized weights. LIGHT/RARE for hero text; REGULAR for body;
# MEDIUM for labels; SEMIBOLD for sub-headings; BOLD for emphasis.
FONT_WEIGHT_LIGHT = 300
FONT_WEIGHT_REGULAR = 400
FONT_WEIGHT_MEDIUM = 500
FONT_WEIGHT_SEMIBOLD = 600
FONT_WEIGHT_BOLD = 700

# ── Z-INDEX (stacking order) ───────────────────────────────────
# Single source of truth for widget z-ordering. BASE=0 (normal
# flow); DROPDOWN/STICKY for popups and sticky elements; OVERLAY
# for backdrop scrims; MODAL/TOAST/TOOLTIP for elevated UI layers.
Z_INDEX_BASE = 0
Z_INDEX_DROPDOWN = 100
Z_INDEX_STICKY = 200
Z_INDEX_OVERLAY = 500
Z_INDEX_MODAL = 1000
Z_INDEX_TOAST = 2000
Z_INDEX_TOOLTIP = 3000

# ── OPACITY ────────────────────────────────────────────────────
# Standardized opacity values. DISABLED/HOVER/PRESSED for
# interaction states; OVERLAY for modal backdrops; MUTED/FULL
# for content emphasis.
OPACITY_DISABLED = 0.4
OPACITY_HOVER = 0.8
OPACITY_PRESSED = 0.6
OPACITY_OVERLAY = 0.5
OPACITY_MUTED = 0.6
OPACITY_FULL = 1.0

# ── LAYOUT DIMENSIONS ──────────────────────────────────────────
# Standardized layout boundaries. MAX_WIDTH_* caps form/page/wide
# content widths. NAV_WIDTH and SIDEBAR_WIDTH establish sidebar
# dimensions (vs. SCROLLBAR_WIDTH for inner scrollbars).
LAYOUT_MAX_WIDTH_FORM = 480
LAYOUT_MAX_WIDTH_PAGE = 1200
LAYOUT_MAX_WIDTH_WIDE = 1600
LAYOUT_NAV_WIDTH = 240
LAYOUT_SIDEBAR_WIDTH = 260
LAYOUT_TOPBAR_HEIGHT = 56
LAYOUT_FOOTER_HEIGHT = 32
LAYOUT_TOOLBAR_HEIGHT = 48

# ── ANIMATION DURATION & EASING ────────────────────────────────
# Generic animation timings. DURATION_FAST (100ms) for hover/focus;
# NORMAL (200ms) for state changes; SLOW (300ms) for transitions;
# SLOWER (500ms) for emphasis (page-to-page). EASING_* for CSS
# transition-timing-function.
ANIMATION_DURATION_FAST = 100
ANIMATION_DURATION_NORMAL = 200
ANIMATION_DURATION_SLOW = 300
ANIMATION_DURATION_SLOWER = 500
ANIMATION_EASING_DEFAULT = "ease"
ANIMATION_EASING_IN = "ease-in"
ANIMATION_EASING_OUT = "ease-out"
ANIMATION_EASING_IN_OUT = "ease-in-out"

# ── SHADOW / ELEVATION ─────────────────────────────────────────
# Box-shadow strings (CSS). NONE removes all elevation; SM/MD/LG/XL
# provide depth from cards to dialogs. Composable with ELEVATION_*
# tokens above (ELEVATION_INPUT=0, CARD=1, SECTION=2, DIALOG=4).
SHADOW_NONE = "none"
SHADOW_SM = "0 1px 2px rgba(0, 0, 0, 0.05)"
SHADOW_MD = "0 2px 4px rgba(0, 0, 0, 0.1)"
SHADOW_LG = "0 4px 8px rgba(0, 0, 0, 0.15)"
SHADOW_XL = "0 8px 16px rgba(0, 0, 0, 0.2)"

# ── TRANSITION SHORTCUTS ───────────────────────────────────────
# Reusable CSS transition strings. FAST/NORMAL/SLOW are "all
# properties Xms ease"; COLOR is restricted to color and
# background-color for performant hover effects.
TRANSITION_FAST = "all 100ms ease"
TRANSITION_NORMAL = "all 200ms ease"
TRANSITION_SLOW = "all 300ms ease"
TRANSITION_COLOR = "color 150ms ease, background-color 150ms ease"

# ── SCROLLBAR DIMENSIONS ───────────────────────────────────────
# Standardized scrollbar geometry. WIDTH is fixed; MIN_HEIGHT
# is the minimum draggable handle; HANDLE_RADIUS rounds the
# scrollbar handle.
SCROLLBAR_WIDTH = 12
SCROLLBAR_MIN_HEIGHT = 30
SCROLLBAR_HANDLE_RADIUS = 6

# ── AVATAR SIZE ────────────────────────────────────────────────
# Standardized user/contact avatar dimensions. XS for inline
# mentions; SM for table cells; MD for lists; LG for profile cards.
AVATAR_SIZE_XS = 24
AVATAR_SIZE_SM = 32
AVATAR_SIZE_MD = 40
AVATAR_SIZE_LG = 48
"""UI constants for consistent styling across the ERP application."""

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

# =====================================================
# DESIGN TOKEN SYSTEM - PHASE 1: COLOR TOKENIZATION
# =====================================================

# Primary colors
COLOR_PRIMARY = "#2563eb"           # Primary blue (buttons, links)
COLOR_PRIMARY_HOVER = "#3b82f6"     # Primary hover state
COLOR_PRIMARY_ACTIVE = "#1d4ed8"   # Primary active/pressed state
COLOR_PRIMARY_MUTED = "#93c5fd"    # Primary muted/disabled

# Semantic colors
COLOR_SUCCESS = "#16a34a"          # Success green
COLOR_SUCCESS_HOVER = "#22c55e"    # Success hover state
COLOR_SUCCESS_ACTIVE = "#15803d"   # Success active/pressed state
COLOR_SUCCESS_MUTED = "#86efac"   # Success muted/disabled state
COLOR_SUCCESS_BG = "#dcfce7"       # Success background
COLOR_WARNING = "#d97706"          # Warning yellow/orange
COLOR_WARNING_HOVER = "#f59e0b"    # Warning hover state
COLOR_WARNING_ACTIVE = "#b45309"   # Warning active state
COLOR_WARNING_MUTED = "#fde68a"    # Warning muted state
COLOR_WARNING_BG = "#fef3c7"       # Warning background
COLOR_DANGER = "#dc2626"           # Danger red
COLOR_DANGER_HOVER = "#ef4444"     # Danger hover state
COLOR_DANGER_ACTIVE = "#b91c1c"    # Danger active state
COLOR_DANGER_MUTED = "#fca5a5"     # Danger muted state
COLOR_DANGER_BG = "#fee2e2"        # Danger background
COLOR_INFO = "#2563eb"             # Info blue
COLOR_INFO_HOVER = "#3b82f6"       # Info hover state
COLOR_INFO_ACTIVE = "#1d4ed8"      # Info active state
COLOR_INFO_MUTED = "#93c5fd"       # Info muted state
COLOR_INFO_BG = "#dbeafe"         # Info background

# Background colors (light theme)
COLOR_BG_MAIN = "#f5f6fa"          # Main background (light base)
COLOR_BG_SURFACE = "#ffffff"       # Surface/cards
COLOR_BG_ELEVATED = "#ffffff"       # Elevated elements
COLOR_BG_INPUT = "#ffffff"         # Input fields background

# Text colors
COLOR_TEXT_PRIMARY = "#1f2937"     # Primary text (high contrast)
COLOR_TEXT_SECONDARY = "#4b5563"   # Secondary text (medium contrast)
COLOR_TEXT_MUTED = "#9ca3af"       # Muted/disabled text
COLOR_TEXT_ON_PRIMARY = "#ffffff"  # Text on primary color

# Light theme specific (for dialogs/forms on light backgrounds)
COLOR_BG_LIGHT = "#f5f6fa"         # Light background for dialogs
COLOR_BG_LIGHT_SURFACE = "#ffffff" # Light surface
COLOR_TEXT_LIGHT = "#1f2937"       # Text on light backgrounds
COLOR_TEXT_SECONDARY_LIGHT = "#4b5563"  # Secondary text light
COLOR_TEXT_DIALOG = "#374151"       # Dialog label text
COLOR_BORDER_LIGHT_THEME = "#d1d5db"   # Border for light theme
COLOR_MUTED_LIGHT = "#9ca3af"      # Muted text light
COLOR_BG_BUTTON_LIGHT = "#6b7280"   # Light theme button background
COLOR_BG_BUTTON_SECONDARY = "#e5e7eb"  # Secondary/secondary button

# Secondary button system
COLOR_SECONDARY_BG = "#e5e7eb"       # Secondary button background
COLOR_SECONDARY_HOVER = "#d1d5db"     # Secondary button hover
COLOR_SECONDARY_TEXT = "#374151"      # Secondary button text
COLOR_SECONDARY_ACTIVE = "#9ca3af"    # Secondary button active

# Border colors
COLOR_BORDER = "#d1d5db"           # Default border
COLOR_BORDER_LIGHT = "#e5e7eb"     # Light border
COLOR_BORDER_FOCUS = "#2563eb"     # Focus state border
COLOR_BORDER_LIGHT_THEME = "#d1d5db"  # Light theme border
COLOR_BORDER_DIALOG = "#e5e7eb"    # Dialog border
COLOR_BORDER_TABLE = "#e5e7eb"     # Table grid/border
COLOR_BORDER_INPUT = "#d1d5db"     # Input field border
COLOR_TABLE_GRIDLINE = "#e5e7eb"  # Table grid lines
COLOR_TEXT_TITLE = "#1f2937"       # Title text color
COLOR_HEADER_DARK = "#1e40af"     # Header background dark

# Table colors
COLOR_TABLE_HEADER = "#f3f4f6"    # Table header background
COLOR_TABLE_ALT = "#f9fafb"        # Table alternate row
COLOR_TABLE_GRID = "#e5e7eb"       # Table grid lines

# Status indicator colors
COLOR_STATUS_VALID = "#a6e3a1"     # Valid/active status
COLOR_STATUS_INVALID = "#f38ba8"   # Invalid/error status
COLOR_STATUS_WARNING = "#fab387"   # Warning status (orange)
COLOR_STATUS_PENDING = "#f9e2af"  # Pending status

# WhatsApp brand color (for document_action_dialog)
COLOR_WHATSAPP = "#25D366"

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
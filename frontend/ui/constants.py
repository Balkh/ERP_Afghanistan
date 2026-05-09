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
COLOR_PRIMARY = "#89b4fa"           # Primary blue (buttons, links)
COLOR_PRIMARY_HOVER = "#74c7ec"     # Primary hover state
COLOR_PRIMARY_ACTIVE = "#89dceb"   # Primary active/pressed state
COLOR_PRIMARY_MUTED = "#45475a"    # Primary muted/disabled

# Semantic colors
COLOR_SUCCESS = "#a6e3a1"          # Success green
COLOR_SUCCESS_HOVER = "#94e2d5"    # Success hover state
COLOR_SUCCESS_ACTIVE = "#74c7a0"   # Success active/pressed state
COLOR_SUCCESS_MUTED = "#45475a"   # Success muted/disabled state
COLOR_SUCCESS_BG = "#1e3a2f"       # Success background
COLOR_WARNING = "#f9e2af"          # Warning yellow/orange
COLOR_WARNING_HOVER = "#fab387"    # Warning hover state
COLOR_WARNING_ACTIVE = "#f38ba8"   # Warning active state
COLOR_WARNING_MUTED = "#45475a"    # Warning muted state
COLOR_WARNING_BG = "#3a3520"       # Warning background
COLOR_DANGER = "#f38ba8"           # Danger red
COLOR_DANGER_HOVER = "#eba0ac"     # Danger hover state
COLOR_DANGER_ACTIVE = "#dc2626"    # Danger active state
COLOR_DANGER_MUTED = "#45475a"     # Danger muted state
COLOR_DANGER_BG = "#3a1f2a"        # Danger background
COLOR_INFO = "#89b4fa"             # Info blue
COLOR_INFO_HOVER = "#74c7ec"       # Info hover state
COLOR_INFO_ACTIVE = "#89dceb"      # Info active state
COLOR_INFO_MUTED = "#45475a"       # Info muted state
COLOR_INFO_BG = "#1e2a3a"         # Info background

# Background colors (dark theme)
COLOR_BG_MAIN = "#1e1e2e"          # Main background (dark base)
COLOR_BG_SURFACE = "#282838"       # Surface/cards
COLOR_BG_ELEVATED = "#313244"       # Elevated elements
COLOR_BG_INPUT = "#1e1e2e"         # Input fields background

# Text colors
COLOR_TEXT_PRIMARY = "#cdd6f4"     # Primary text (high contrast)
COLOR_TEXT_SECONDARY = "#a6adc8"   # Secondary text (medium contrast)
COLOR_TEXT_MUTED = "#6c7086"       # Muted/disabled text
COLOR_TEXT_ON_PRIMARY = "#11111b"  # Text on primary color

# Light theme specific (for dialogs/forms on light backgrounds)
COLOR_BG_LIGHT = "#282838"         # Light background for dialogs
COLOR_BG_LIGHT_SURFACE = "#313244" # Light surface
COLOR_TEXT_LIGHT = "#cdd6f4"       # Text on light backgrounds
COLOR_TEXT_SECONDARY_LIGHT = "#a6adc8"  # Secondary text light
COLOR_TEXT_DIALOG = "#cdd6f4"       # Dialog label text
COLOR_BORDER_LIGHT_THEME = "#45475a"   # Border for light theme
COLOR_MUTED_LIGHT = "#6c7086"      # Muted text light
COLOR_BG_BUTTON_LIGHT = "#585b70"   # Light theme button background
COLOR_BG_BUTTON_SECONDARY = "#45475a"  # Secondary/secondary button

# Secondary button system
COLOR_SECONDARY_BG = "#45475a"       # Secondary button background
COLOR_SECONDARY_HOVER = "#585b70"     # Secondary button hover
COLOR_SECONDARY_TEXT = "#cdd6f4"      # Secondary button text
COLOR_SECONDARY_ACTIVE = "#6c7086"    # Secondary button active

# Border colors
COLOR_BORDER = "#45475a"           # Default border
COLOR_BORDER_LIGHT = "#38384a"     # Light border
COLOR_BORDER_FOCUS = "#89b4fa"     # Focus state border
COLOR_BORDER_LIGHT_THEME = "#45475a"  # Light theme border
COLOR_BORDER_DIALOG = "#45475a"    # Dialog border
COLOR_BORDER_TABLE = "#45475a"     # Table grid/border
COLOR_BORDER_INPUT = "#45475a"     # Input field border
COLOR_TABLE_GRIDLINE = "#45475a"  # Table grid lines
COLOR_TEXT_TITLE = "#cdd6f4"       # Title text color
COLOR_HEADER_DARK = "#11111b"     # Header background dark

# Table colors
COLOR_TABLE_HEADER = "#313244"    # Table header background
COLOR_TABLE_ALT = "#282838"        # Table alternate row
COLOR_TABLE_GRID = "#45475a"       # Table grid lines

# Status indicator colors
COLOR_STATUS_VALID = "#a6e3a1"     # Valid/active status
COLOR_STATUS_INVALID = "#f38ba8"   # Invalid/error status
COLOR_STATUS_WARNING = "#fab387"   # Warning status (orange)
COLOR_STATUS_PENDING = "#f9e2af"  # Pending status

# WhatsApp brand color (for document_action_dialog)
COLOR_WHATSAPP = "#25D366"

# =====================================================
# PHASE 3: LIGHT THEME READABILITY TOKENS (SAFE EXTENSION)
# =====================================================
# These tokens improve Light Theme readability without
# modifying existing tokens. Applied selectively to
# tables, forms, borders, and UI dividers.

COLOR_TABLE_BORDER_LIGHT = "#585b70"       # Clear table gridlines/borders
COLOR_TABLE_HEADER_BG_LIGHT = "#45475a"    # Distinct table header background
COLOR_FORM_BORDER_LIGHT = "#585b70"        # Visible input/control borders
COLOR_FORM_TEXT_LIGHT = "#cdd6f4"          # High-contrast form input text
COLOR_UI_DIVIDER_LIGHT = "#45475a"         # Visible section dividers

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
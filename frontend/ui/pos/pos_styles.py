"""Reusable style functions for POS screen widgets.

Eliminates ~100 lines of duplicated inline stylesheets across
_build_scan_zone, _build_product_search, _build_customer_zone,
_build_alerts_zone, _build_cart_table, and all status_label updates.
"""

from ui.constants import (
    SPACING_SM, SPACING_MD, SPACING_LG,
    TEXT_CARD_TITLE, TEXT_TABLE, TEXT_HELPER,
    BORDER_RADIUS_MD, BORDER_RADIUS_LG,
    COLOR_BG_INPUT, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING,
    COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_ON_SUCCESS, COLOR_TEXT_ON_WARNING,
    FONT_WEIGHT_BOLD, BORDER_WIDTH_HAIRLINE, BORDER_WIDTH_MEDIUM,
)


def group_box_stylesheet(border_color=COLOR_BORDER, border_width=BORDER_WIDTH_HAIRLINE):
    """Style for QGroupBox zones (scan, search, customer, alerts, cart)."""
    return (
        f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; "
        f"font-weight: {FONT_WEIGHT_BOLD}; border: {border_width}px solid {border_color}; "
        f"border-radius: {BORDER_RADIUS_LG}; "
        f"margin-top: {SPACING_MD}px; padding-top: {SPACING_LG}px; }}"
        f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
        f"padding: 0 {SPACING_SM}px;"
        + (f" color: {COLOR_PRIMARY};" if border_color == COLOR_PRIMARY else "")
        + " }"
    )


def input_stylesheet():
    """Style for text inputs (search, discount, tax, amount paid)."""
    return (
        f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
        f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; "
        f"border-radius: {BORDER_RADIUS_MD}; padding: 0 {SPACING_SM}px;"
    )


def scan_input_stylesheet():
    """Style for the large barcode scan input (highlighted border)."""
    return (
        f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
        f"border: {BORDER_WIDTH_MEDIUM}px solid {COLOR_PRIMARY}; "
        f"border-radius: {BORDER_RADIUS_MD}; padding: 0 {SPACING_MD}px;"
    )


# ---------------------------------------------------------------------------
# Status label helpers
# ---------------------------------------------------------------------------

def status_stylesheet(bg_color, fg_color):
    """Return the common status-label stylesheet for a given bg/fg pair."""
    return (
        f"background-color: {bg_color}; color: {fg_color}; "
        f"padding: {SPACING_SM}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}px; "
        f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
    )


# Pre-built presets so callers don't need to know the fg color.
STATUS_READY   = status_stylesheet(COLOR_SUCCESS, COLOR_TEXT_ON_SUCCESS)
STATUS_PROCESSING = status_stylesheet(COLOR_WARNING, COLOR_TEXT_ON_WARNING)
STATUS_COMPLETED  = status_stylesheet(COLOR_SUCCESS, COLOR_TEXT_ON_SUCCESS)
STATUS_FAILED     = status_stylesheet(COLOR_DANGER, COLOR_TEXT_ON_PRIMARY)
STATUS_ERROR      = STATUS_FAILED
STATUS_HELD       = status_stylesheet(COLOR_WARNING, COLOR_TEXT_ON_PRIMARY)

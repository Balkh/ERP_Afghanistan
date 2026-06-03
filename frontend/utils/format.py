"""Formatting and parsing utilities for the Pharmacy ERP frontend.

Centralizes the byte-for-byte duplicated _safe_float definitions that
previously lived in 9 separate files.
"""


def safe_float(value, default=0.0):
    """Safely convert a value to float.

    Returns ``default`` if the value is None or cannot be converted.

    Replaces the 9 byte-identical ``_safe_float`` helper methods that
    previously existed in finance/accounting screens.
    """
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

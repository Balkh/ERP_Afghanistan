"""Shared form helper functions for ERP dialogs.

Extracted from supplier_dialog.py, customer_dialog.py, and user_dialog.py
which all had identical _make_field() helpers.
"""
from PySide6.QtWidgets import QLineEdit
from ui.constants import INPUT_HEIGHT_MD


def make_field(placeholder, height=INPUT_HEIGHT_MD, echo_mode=None):
    """Create a styled QLineEdit with placeholder, height, and optional echo mode.

    Parameters
    ----------
    placeholder : str
        Placeholder text for the field.
    height : int
        Minimum height in pixels. Defaults to INPUT_HEIGHT_MD.
    echo_mode : QLineEdit.EchoMode or None
        Optional echo mode (e.g. QLineEdit.EchoMode.Password).
    """
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setMinimumHeight(height)
    if echo_mode is not None:
        field.setEchoMode(echo_mode)
    return field

"""Business action dispatchers for MainWindow.

Extracted from ui/main_window.py to reduce God Object responsibilities.
Contains the implementation logic for simple action methods (dialogs,
subprocess calls, navigation hints).  MainWindow retains thin delegator
methods so that menu_builder signal connections remain valid.

This is a **pure extraction** -- zero new abstractions, zero behavior changes.
"""

import subprocess

from ui.components.dialogs import AlertDialog
from ui.licensing.license_manager_dialog import LicenseManagerDialog


def show_about(main_window):
    """Show the about dialog."""
    AlertDialog.info(
        "About Pharmacy ERP",
        "Pharmacy ERP v1.0.0\n\n"
        "A comprehensive enterprise resource planning system\n"
        "for pharmaceutical distribution management.\n\n"
        "\u00a9 2026 Pharmacy ERP Solutions. All rights reserved.",
        main_window,
    )


def show_preferences(main_window):
    """Show preferences dialog."""
    AlertDialog.info("Preferences", "Preferences panel would open here.", main_window)


def show_license_manager(main_window):
    """Show the license manager dialog."""
    dialog = LicenseManagerDialog(main_window)
    dialog.exec()


def toggle_fullscreen(main_window):
    """Toggle fullscreen mode."""
    if main_window.isFullScreen():
        main_window.showNormal()
    else:
        main_window.showFullScreen()


def new_product(main_window):
    """Create new product."""
    AlertDialog.info("New Product", "Navigate to Products and click Add New.", main_window)
    main_window.navigate_to("products")


def show_stock_alerts(main_window):
    """Show low stock alerts."""
    AlertDialog.info("Stock Alerts", "Showing low stock items...", main_window)


def open_calculator(main_window):
    """Open system calculator."""
    try:
        subprocess.Popen('calc.exe')
    except Exception:
        AlertDialog.warning("Error", "Could not open calculator.", main_window)


def open_calendar(main_window):
    """Open system calendar."""
    try:
        subprocess.Popen('outlook.exe')
    except Exception:
        AlertDialog.info("Calendar", "Calendar integration not available.", main_window)

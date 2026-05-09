"""
Licensing dialogs for Pharmacy ERP.
Contains reusable dialogs for license activation, status, and warnings.
"""

from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import Qt


def show_activation_success(parent=None):
    """Show license activation success dialog."""
    QMessageBox.information(
        parent,
        "Activation Successful",
        "Pharmacy ERP has been successfully activated!\n\n"
        "The application will now restart to apply the license.",
        QMessageBox.Ok
    )


def show_activation_failure(parent=None, message=""):
    """Show license activation failure dialog."""
    QMessageBox.warning(
        parent,
        "Activation Failed",
        f"License activation failed:\n\n{message}\n\n"
        "Please check your license file and try again.",
        QMessageBox.Ok
    )


def show_license_error(parent=None, message=""):
    """Show license error dialog."""
    QMessageBox.critical(
        parent,
        "License Error",
        f"An error occurred with the license:\n\n{message}",
        QMessageBox.Ok
    )


def show_license_warning(parent=None, message=""):
    """Show license warning dialog."""
    QMessageBox.warning(
        parent,
        "License Warning",
        message,
        QMessageBox.Ok
    )


def show_license_info(parent=None, message=""):
    """Show license information dialog."""
    QMessageBox.information(
        parent,
        "License Information",
        message,
        QMessageBox.Ok
    )


def show_activation_required(parent=None):
    """Show dialog indicating activation is required."""
    reply = QMessageBox.question(
        parent,
        "Activation Required",
        "Pharmacy ERP requires activation to continue.\n\n"
        "Would you like to activate your license now?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )
    return reply == QMessageBox.Yes


def show_trial_mode_expired(parent=None):
    """Show dialog indicating trial mode has expired."""
    QMessageBox.critical(
        parent,
        "Trial Mode Expired",
        "Your trial mode for Pharmacy ERP has expired.\n\n"
        "Please activate a valid license to continue using the application.",
        QMessageBox.Ok
    )


def show_license_file_not_found(parent=None):
    """Show dialog indicating license file not found."""
    QMessageBox.warning(
        parent,
        "License File Not Found",
        "No license file was found.\n\n"
        "Please activate Pharmacy ERP with a valid license file.",
        QMessageBox.Ok
    )


def show_license_device_mismatch(expected_device_id, actual_device_id, parent=None):
    """Show dialog indicating license device mismatch."""
    QMessageBox.warning(
        parent,
        "License Device Mismatch",
        f"The license is not bound to this device.\n\n"
        f"Expected Device ID: {expected_device_id}\n"
        f"Actual Device ID: {actual_device_id}\n\n"
        "Please obtain a license for this device.",
        QMessageBox.Ok
    )


def show_license_expired(expiration_date, parent=None):
    """Show dialog indicating license has expired."""
    QMessageBox.warning(
        parent,
        "License Expired",
        f"Your license has expired on {expiration_date}.\n\n"
        "Please renew your license to continue using Pharmacy ERP.",
        QMessageBox.Ok
    )


def show_license_invalid_signature(parent=None):
    """Show dialog indicating license signature is invalid."""
    QMessageBox.critical(
        parent,
        "Invalid License",
        "The license file appears to be tampered with or corrupted.\n\n"
        "Please obtain a valid license file from the software provider.",
        QMessageBox.Ok
    )


def show_license_validation_failed(parent=None, message=""):
    """Show dialog indicating license validation failed."""
    QMessageBox.critical(
        parent,
        "License Validation Failed",
        f"License validation has failed too many times:\n\n{message}\n\n"
        "The application will now exit.",
        QMessageBox.Ok
    )
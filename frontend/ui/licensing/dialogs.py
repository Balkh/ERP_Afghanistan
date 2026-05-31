"""
Licensing dialogs for Pharmacy ERP.
Contains reusable dialogs for license activation, status, and warnings.
"""

from ui.components.dialogs import AlertDialog, ConfirmDialog


def show_activation_success(parent=None):
    """Show license activation success dialog."""
    AlertDialog.info(
        parent,
        "Activation Successful",
        "Pharmacy ERP has been successfully activated!\n\n"
        "The application will now restart to apply the license.",
    )


def show_activation_failure(parent=None, message=""):
    """Show license activation failure dialog."""
    AlertDialog.warning(
        parent,
        "Activation Failed",
        f"License activation failed:\n\n{message}\n\n"
        "Please check your license file and try again.",
    )


def show_license_error(parent=None, message=""):
    """Show license error dialog."""
    AlertDialog.error(
        parent,
        "License Error",
        f"An error occurred with the license:\n\n{message}",
    )


def show_license_warning(parent=None, message=""):
    """Show license warning dialog."""
    AlertDialog.warning(
        parent,
        "License Warning",
        message,
    )


def show_license_info(parent=None, message=""):
    """Show license information dialog."""
    AlertDialog.info(
        parent,
        "License Information",
        message,
    )


def show_activation_required(parent=None):
    """Show dialog indicating activation is required."""
    reply = ConfirmDialog.confirm(
        parent,
        "Activation Required",
        "Pharmacy ERP requires activation to continue.\n\n"
        "Would you like to activate your license now?",
    )
    return reply


def show_trial_mode_expired(parent=None):
    """Show dialog indicating trial mode has expired."""
    AlertDialog.error(
        parent,
        "Trial Mode Expired",
        "Your trial mode for Pharmacy ERP has expired.\n\n"
        "Please activate a valid license to continue using the application.",
    )


def show_license_file_not_found(parent=None):
    """Show dialog indicating license file not found."""
    AlertDialog.warning(
        parent,
        "License File Not Found",
        "No license file was found.\n\n"
        "Please activate Pharmacy ERP with a valid license file.",
    )


def show_license_device_mismatch(expected_device_id, actual_device_id, parent=None):
    """Show dialog indicating license device mismatch."""
    AlertDialog.warning(
        parent,
        "License Device Mismatch",
        "The license is not bound to this device.\n\n"
        f"Expected Device ID: {expected_device_id}\n"
        f"Actual Device ID: {actual_device_id}\n\n"
        "Please obtain a license for this device.",
    )


def show_license_expired(expiration_date, parent=None):
    """Show dialog indicating license has expired."""
    AlertDialog.warning(
        parent,
        "License Expired",
        f"Your license has expired on {expiration_date}.\n\n"
        "Please renew your license to continue using Pharmacy ERP.",
    )


def show_license_invalid_signature(parent=None):
    """Show dialog indicating license signature is invalid."""
    AlertDialog.error(
        parent,
        "Invalid License",
        "The license file appears to be tampered with or corrupted.\n\n"
        "Please obtain a valid license file from the software provider.",
    )


def show_license_validation_failed(parent=None, message=""):
    """Show dialog indicating license validation failed."""
    AlertDialog.error(
        parent,
        "License Validation Failed",
        f"License validation has failed too many times:\n\n{message}\n\n"
        "The application will now exit.",
    )
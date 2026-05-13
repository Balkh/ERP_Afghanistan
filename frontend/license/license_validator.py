"""
Runtime license validation system for Pharmacy ERP.
Provides continuous license validation with anti-tamper and rollback protection.
"""

import sys
import os
import time
import json
import threading
from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any
from PySide6.QtCore import QObject, Signal, QTimer

# Add paths for imports
frontend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, frontend_dir)
sys.path.insert(0, os.path.join(frontend_dir, 'license'))

from license_service import LicenseService
from utils.device_fingerprint import generate_device_id
from trust_anchor import LicenseTrustAnchor, InstallationLock, verify_checksum


class LicenseValidationResult:
    """Represents the result of a license validation check."""
    
    def __init__(self, is_valid: bool, message: str, license_data: Optional[Dict[str, Any]] = None):
        self.is_valid = is_valid
        self.message = message
        self.license_data = license_data
        self.timestamp = datetime.now()
    
    def __bool__(self):
        return self.is_valid


class LicenseValidator(QObject):
    """
    Runtime license validation system.
    Validates license at startup and periodically during application runtime.
    """
    
    # Signals for UI updates
    license_valid = Signal(bool, str)  # is_valid, message
    license_status_changed = Signal(str)  # status message
    
    def __init__(self, validation_interval_minutes: int = 60):
        """
        Initialize the license validator.
        
        Args:
            validation_interval_minutes: How often to re-validate license (minutes)
        """
        super().__init__()
        
        self.license_service = LicenseService()
        self.validation_interval_ms = validation_interval_minutes * 60 * 1000
        self.last_validation_result = None
        self.validation_timer = None
        self.startup_time = None
        self.last_system_time = None
        
        # Anti-tamper tracking
        self.known_good_system_time = None
        self.validation_count = 0
        self.failed_validations = 0
        
        # Initialize validation
        self._startup_validation()
        
    def _startup_validation(self):
        """Perform initial license validation at application startup."""
        self.startup_time = datetime.now()
        self.last_system_time = self.startup_time
        
        # Perform initial validation
        result = self.validate_license()
        self.last_validation_result = result
        
        # Emit signals
        self.license_valid.emit(result.is_valid, result.message)
        self.license_status_changed.emit(result.message)
        
        # Start periodic validation timer
        self._start_periodic_validation()
    
    def _start_periodic_validation(self):
        """Start the periodic validation timer."""
        self.validation_timer = QTimer()
        self.validation_timer.timeout.connect(self._periodic_validation)
        self.validation_timer.start(self.validation_interval_ms)
    
    def _stop_periodic_validation(self):
        """Stop the periodic validation timer."""
        if self.validation_timer:
            self.validation_timer.stop()
            self.validation_timer = None
    
    def _periodic_validation(self):
        """Perform periodic license validation."""
        self.validation_count += 1
        
        # Check for system rollback
        rollback_detected = self._check_system_rollback()
        if rollback_detected:
            result = LicenseValidationResult(
                False, 
                "System clock rollback detected. License validation failed."
            )
            self._handle_validation_failure(result)
            return
        
        # Perform license validation
        result = self.validate_license()
        self.last_validation_result = result
        
        if result.is_valid:
            self.failed_validations = 0  # Reset failure count on success
            self.license_valid.emit(True, result.message)
            self.license_status_changed.emit(f"License valid: {result.message}")
        else:
            self.failed_validations += 1
            self._handle_validation_failure(result)
    
    def _check_system_rollback(self) -> bool:
        """
        Check if system clock has been rolled back.
        
        Returns:
            True if rollback detected, False otherwise
        """
        current_time = datetime.now()
        
        # Initialize known good time on first check
        if self.known_good_system_time is None:
            self.known_good_system_time = current_time
            return False
        
        # Check if system time has gone backwards significantly
        # Allow for small clock adjustments (up to 1 minute)
        time_diff = (current_time - self.known_good_system_time).total_seconds()
        if time_diff < -60:  # More than 1 minute backwards
            return True
        
        # Update known good time if time has moved forward
        if time_diff > 0:
            self.known_good_system_time = current_time
            
        return False
    
    def _handle_validation_failure(self, result: LicenseValidationResult):
        """Handle a license validation failure."""
        self.license_valid.emit(False, result.message)
        self.license_status_changed.emit(f"LICENSE ERROR: {result.message}")
        
        # If we have too many consecutive failures, consider the license permanently invalid
        if self.failed_validations >= 3:
            self._stop_periodic_validation()
            # Emit critical failure signal
            self.license_valid.emit(False, "License validation failed too many times. Application may not function correctly.")
    
    def validate_license(self, license_file_path: Optional[str] = None) -> LicenseValidationResult:
        """
        Validate the license comprehensively.
        
        Args:
            license_file_path: Optional path to license file (uses default location if None)
            
        Returns:
            LicenseValidationResult object
        """
        try:
            # Load license from file if specified, otherwise use default location
            if license_file_path and os.path.exists(license_file_path):
                license_data = self.license_service.load_license_from_file(license_file_path)
            else:
                # Try to find license in default locations
                license_data = self._find_and_load_license()
                if license_data is None:
                    return LicenseValidationResult(
                        False, 
                        "No license file found. Please install a valid license."
                    )
            
            # Phase 5B.18: Trust anchor validation (anti-tamper + integrity chain + installation lock)
            trust = LicenseTrustAnchor()
            trust_result = trust.validate(license_data)
            if not trust_result["passed"]:
                return LicenseValidationResult(
                    False,
                    f"Trust anchor validation failed: {trust_result['reason']}",
                    license_data,
                )

            # Validate the license
            is_valid, message = self.license_service.validate_current_device_license(license_data)
            
            if is_valid:
                return LicenseValidationResult(
                    True, 
                    message, 
                    license_data
                )
            else:
                return LicenseValidationResult(
                    False, 
                    message, 
                    license_data
                )
                
        except Exception as e:
            return LicenseValidationResult(
                False, 
                f"License validation error: {str(e)}"
            )
    
    def _find_and_load_license(self) -> Optional[Dict[str, Any]]:
        """
        Find and load a license file from common locations.
        
        Returns:
            License data dictionary or None if not found
        """
        # Common license file locations to check
        possible_locations = [
            # Current directory
            os.path.join(os.getcwd(), "license.json"),
            os.path.join(os.getcwd(), "license.lic"),
            os.path.join(os.getcwd(), "pharmacy_erp.license"),
            
            # Application directory
            os.path.join(frontend_dir, "license.json"),
            os.path.join(frontend_dir, "license.lic"),
            os.path.join(frontend_dir, "pharmacy_erp.license"),
            
            # User's home directory
            os.path.join(os.path.expanduser("~"), ".pharmacy_erp", "license.json"),
            os.path.join(os.path.expanduser("~"), ".pharmacy_erp", "license.lic"),
            
            # License service keys directory
            os.path.join(self.license_service.keys_dir, "license.json"),
            os.path.join(self.license_service.keys_dir, "license.lic"),
        ]
        
        for location in possible_locations:
            if os.path.exists(location):
                try:
                    return self.license_service.load_license_from_file(location)
                except Exception:
                    # Continue to next location if this file is invalid
                    continue
        
        return None
    
    def get_license_status(self) -> Dict[str, Any]:
        """
        Get current license status information.
        
        Returns:
            Dictionary with license status details
        """
        if self.last_validation_result is None:
            return {
                "status": "unknown",
                "message": "License validation not yet performed",
                "is_valid": False,
                "validation_count": self.validation_count,
                "failed_validations": self.failed_validations
            }
        
        return {
            "status": "valid" if self.last_validation_result.is_valid else "invalid",
            "message": self.last_validation_result.message,
            "is_valid": self.last_validation_result.is_valid,
            "timestamp": self.last_validation_result.timestamp.isoformat(),
            "validation_count": self.validation_count,
            "failed_validations": self.failed_validations,
            "uptime_minutes": (datetime.now() - self.startup_time).total_seconds() / 60 if self.startup_time else 0
        }
    
    def force_revalidation(self) -> LicenseValidationResult:
        """
        Force an immediate license re-validation.
        
        Returns:
            LicenseValidationResult from the validation
        """
        result = self.validate_license()
        self.last_validation_result = result
        
        if result.is_valid:
            self.failed_validations = 0
        else:
            self.failed_validations += 1
        
        self.license_valid.emit(result.is_valid, result.message)
        self.license_status_changed.emit(result.message)
        
        return result
    
    def cleanup(self):
        """Cleanup resources when application is closing."""
        self._stop_periodic_validation()


# Global validator instance
_license_validator = None


def get_license_validator() -> LicenseValidator:
    """
    Get the global license validator instance.
    
    Returns:
        LicenseValidator instance
    """
    global _license_validator
    if _license_validator is None:
        _license_validator = LicenseValidator()
    return _license_validator


def initialize_license_validation() -> LicenseValidator:
    """
    Initialize the license validation system.
    Should be called at application startup.
    
    Returns:
        LicenseValidator instance
    """
    global _license_validator
    _license_validator = LicenseValidator()
    return _license_validator


# Example usage and testing
if __name__ == "__main__":
    # Test the license validator
    print("Testing License Validator...")
    
    validator = LicenseValidator(validation_interval_minutes=1)  # 1 minute for testing
    
    # Wait a bit to see validation in action
    import time
    time.sleep(3)
    
    # Check status
    status = validator.get_license_status()
    print(f"License Status: {status}")
    
    # Force revalidation
    result = validator.force_revalidation()
    print(f"Forced validation: {result.is_valid} - {result.message}")
    
    # Cleanup
    validator.cleanup()
    print("Test completed.")
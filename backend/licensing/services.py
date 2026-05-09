from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import DeviceLicense
from .providers import (
    DeviceFingerprintProvider,
    ProductionFingerprintProvider,
    get_fingerprint_provider,
)
from .rsa import create_signed_license, verify_signed_license


class LicenseValidationError(ValidationError):
    """Custom exception for license validation errors."""
    pass


# Global provider instance - defaults to production
_fingerprint_provider: DeviceFingerprintProvider = None


def set_fingerprint_provider(provider: DeviceFingerprintProvider) -> None:
    """
    Set the fingerprint provider (for testing).
    
    Args:
        provider: DeviceFingerprintProvider instance
    """
    global _fingerprint_provider
    _fingerprint_provider = provider


def get_fingerprint_provider_instance() -> DeviceFingerprintProvider:
    """
    Get the current fingerprint provider.
    
    Returns:
        DeviceFingerprintProvider: Current provider (production or mock)
    """
    global _fingerprint_provider
    if _fingerprint_provider is None:
        return ProductionFingerprintProvider()
    return _fingerprint_provider


class LicenseService:
    """
    Service for handling device-based licensing operations.
    
    Uses dependency injection for fingerprint providers to enable
    deterministic testing while maintaining production security.
    """
    
    @staticmethod
    def get_current_device_fingerprint():
        """
        Get the fingerprint of the current device.
        
        Returns:
            dict: Device fingerprint with cpu_id, mac_address, disk_serial, device_id
        """
        provider = get_fingerprint_provider_instance()
        return provider.get_fingerprint()
    
    @staticmethod
    def get_current_device_id():
        """
        Get the device ID of the current device.
        
        Returns:
            str: Device ID (hashed fingerprint)
        """
        fingerprint = LicenseService.get_current_device_fingerprint()
        return fingerprint['device_id']
    
    @staticmethod
    def validate_license(license_key=None):
        """
        Validate the license for the current device.
        
        Args:
            license_key: Optional specific license key to validate.
                        If None, finds the first matching license for current device.
        
        Returns:
            DeviceLicense: The validated license object
            
        Raises:
            LicenseValidationError: If license is invalid, expired, or not found
        """
        # Get current device fingerprint
        current_fingerprint = LicenseService.get_current_device_fingerprint()
        current_device_id = current_fingerprint['device_id']
        
        # Build query
        if license_key:
            # Look for specific license key
            try:
                license_obj = DeviceLicense.objects.get(
                    license_key=license_key,
                    is_active=True
                )
            except DeviceLicense.DoesNotExist:
                raise LicenseValidationError(f"License key '{license_key}' not found or inactive")
        else:
            # Find any active license that matches current device
            # First try to find by device_id directly (exact match)
            try:
                license_obj = DeviceLicense.objects.get(
                    device_id=current_device_id,
                    is_active=True
                )
            except DeviceLicense.DoesNotExist:
                # If no exact match, check all active licenses (less efficient but more flexible)
                active_licenses = DeviceLicense.objects.filter(is_active=True)
                for license_obj in active_licenses:
                    if license_obj.matches_device(current_fingerprint):
                        break
                else:
                    # No matching license found
                    raise LicenseValidationError(
                        "No valid license found for this device. "
                        "Please contact support to activate your Pharmacy ERP license."
                    )
        
        # Check if license is expired
        if license_obj.is_expired():
            raise LicenseValidationError(
                f"License expired on {license_obj.expires_date}. "
                "Please renew your license to continue using Pharmacy ERP."
            )
        
        # Verify the signed license data
        if license_obj.signed_license:
            verified_data = verify_signed_license(license_obj.signed_license)
            if not verified_data:
                raise LicenseValidationError(
                    "License signature verification failed. "
                    "The license may have been tampered with or is invalid."
                )
            
            # Additional validation: ensure the license actually matches current device
            # (in case device_id was changed or there was a data issue)
            if not license_obj.matches_device(current_fingerprint):
                raise LicenseValidationError(
                    "License does not match current device hardware. "
                    "Please contact support for license reactivation."
                )
            
            # Verify that the license key matches
            if verified_data.get('license_key') != license_obj.license_key:
                raise LicenseValidationError(
                    "License key mismatch. "
                    "The license data does not correspond to the stored license key."
                )
            
            # Verify that the device_id matches
            if verified_data.get('device_id') != license_obj.device_id:
                raise LicenseValidationError(
                    "Device ID mismatch. "
                    "The license data does not correspond to the stored device ID."
                )
        else:
            # Fallback to fingerprint matching for licenses created before signed license implementation
            if not license_obj.matches_device(current_fingerprint):
                raise LicenseValidationError(
                    "License does not match current device hardware. "
                    "Please contact support for license reactivation."
                )
        
        return license_obj
    
    @staticmethod
    def is_licensed(license_key=None):
        """
        Check if the current device has a valid license.
        
        Args:
            license_key: Optional specific license key to check
            
        Returns:
            bool: True if device is licensed, False otherwise
        """
        try:
            LicenseService.validate_license(license_key)
            return True
        except LicenseValidationError:
            return False
    
    @staticmethod
    def get_license_info(license_key=None):
        """
        Get information about the current license.
        
        Args:
            license_key: Optional specific license key
            
        Returns:
            dict: License information or None if not licensed
        """
        try:
            license_obj = LicenseService.validate_license(license_key)
            # Verify the signed license data if available
            signature_valid = False
            if license_obj.signed_license:
                verified_data = verify_signed_license(license_obj.signed_license)
                signature_valid = verified_data is not None
            
            return {
                'license_key': license_obj.license_key,
                'license_type': license_obj.license_type,
                'issued_to': license_obj.issued_to,
                'issued_date': license_obj.issued_date.isoformat() if license_obj.issued_date else None,
                'expires_date': license_obj.expires_date.isoformat() if license_obj.expires_date else None,
                'is_active': license_obj.is_active,
                'is_valid': license_obj.is_valid(),
                'days_remaining': (
                    (license_obj.expires_date - timezone.now().date()).days
                    if license_obj.expires_date else None
                ),
                'device_id': license_obj.device_id[:16] + '...',  # Truncate for display
                'has_signed_license': bool(license_obj.signed_license),
                'signature_valid': signature_valid
            }
        except LicenseValidationError as e:
            return {'error': str(e)}
    
    @staticmethod
    def create_license(license_key, issued_to=None, expires_date=None, notes=None):
        """
        Create a new device license for the current device.
        
        Args:
            license_key: Unique license key
            issued_to: Name/organization the license is issued to
            expires_date: Optional expiration date (None for perpetual)
            notes: Optional notes
            
        Returns:
            DeviceLicense: The created license object
            
        Raises:
            ValidationError: If license key already exists or validation fails
        """
        # Check if license key already exists
        if DeviceLicense.objects.filter(license_key=license_key).exists():
            raise ValidationError(f"License key '{license_key}' already exists")
        
        # Get current device fingerprint
        fingerprint = LicenseService.get_current_device_fingerprint()
        
        # Generate device_id from fingerprint
        from licensing.utils import generate_device_id_from_fingerprint
        device_id = generate_device_id_from_fingerprint(fingerprint)
        
        # Create license data for signing
        license_data = {
            'license_key': license_key,
            'device_id': device_id,
            'issued_to': issued_to or '',
            'issued_date': timezone.now().date().isoformat(),
            'expires_date': expires_date.isoformat() if expires_date else None,
            'license_type': 'pharmacy_erp',
            'created_at': timezone.now().isoformat()
        }
        
        # Create signed license using RSA
        signed_license = create_signed_license(license_data)
        
        # Create and save the license
        license_obj = DeviceLicense(
            license_key=license_key,
            device_fingerprint=fingerprint,
            device_id=device_id,
            signed_license=signed_license,
            issued_to=issued_to or '',
            expires_date=expires_date,
            notes=notes or '',
            is_active=True
        )
        license_obj.full_clean()  # Run validation
        license_obj.save()
        
        return license_obj
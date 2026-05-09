from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
import base64
from datetime import datetime
from .rsa import verify_signed_license


def validate_device_fingerprint(value):
    """Validate that the device fingerprint is a valid JSON object with required fields."""
    if not isinstance(value, dict):
        raise ValidationError('Device fingerprint must be a dictionary.')
    
    required_fields = ['cpu_id', 'mac_address', 'disk_serial', 'device_id']
    for field in required_fields:
        if field not in value:
            raise ValidationError(f'Device fingerprint missing required field: {field}')


class DeviceLicense(models.Model):
    """
    Model representing a device-specific license for the Pharmacy ERP system.
    """
    # License metadata
    license_key = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique license key"
    )
    
    # Device fingerprint (CPU ID, MAC address, Disk serial)
    device_fingerprint = models.JSONField(
        validators=[validate_device_fingerprint],
        help_text="Device hardware fingerprint"
    )
    
    # Device ID (hashed fingerprint)
    device_id = models.CharField(
        max_length=64,  # SHA256 produces 64 hex characters
        unique=True,
        help_text="Unique device identifier based on hardware fingerprint"
    )
    
    # Signed license data (encrypted and signed)
    signed_license = models.TextField(
        blank=True,
        help_text="RSA-signed license data for verification"
    )
    
    # License information
    license_type = models.CharField(
        max_length=50,
        default='pharmacy_erp',
        help_text="Type of license"
    )
    
    # Validity period
    issued_date = models.DateField(
        default=timezone.now,
        help_text="Date when license was issued"
    )
    
    expires_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when license expires (null for perpetual)"
    )
    
    # License status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the license is currently active"
    )
    
    # Additional metadata
    issued_to = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name or organization the license was issued to"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the license"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'licensing_devicelicense'
        verbose_name = 'Device License'
        verbose_name_plural = 'Device Licenses'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.license_key} - {self.device_id[:16]}..."
    
    def is_expired(self):
        """Check if the license has expired."""
        if self.expires_date is None:
            return False  # Perpetual license
        return timezone.now().date() > self.expires_date
    
    def is_valid(self):
        """Check if the license is valid (active and not expired)."""
        return self.is_active and not self.is_expired()
    
    def matches_device(self, fingerprint_dict):
        """
        Check if the given device fingerprint matches this license.
        
        Args:
            fingerprint_dict: Dictionary with cpu_id, mac_address, disk_serial
            
        Returns:
            bool: True if device matches, False otherwise
        """
        if not isinstance(fingerprint_dict, dict):
            return False
            
        # Check that all required fields are present
        required_fields = ['cpu_id', 'mac_address', 'disk_serial']
        for field in required_fields:
            if field not in fingerprint_dict:
                return False
        
        # Generate device ID from the provided fingerprint and compare
        from licensing.utils import generate_device_id
        provided_device_id = generate_device_id(
            fingerprint_dict['cpu_id'],
            fingerprint_dict['mac_address'],
            fingerprint_dict['disk_serial']
        )
        
        return self.device_id == provided_device_id
    
    def save(self, *args, **kwargs):
        # Ensure device_id is set from fingerprint if not already set
        if not self.device_id and self.device_fingerprint:
            from licensing.utils import generate_device_id
            fp = self.device_fingerprint
            self.device_id = generate_device_id(
                fp.get('cpu_id', ''),
                fp.get('mac_address', ''),
                fp.get('disk_serial', '')
            )
        super().save(*args, **kwargs)

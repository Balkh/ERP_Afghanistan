"""
License service for Pharmacy ERP.
Combines device fingerprinting with RSA license validation.
"""

import os
import json
from datetime import date
from typing import Optional, Dict, Any, Tuple

import sys

# Add the parent directory to sys.path to allow importing from utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.device_fingerprint import generate_device_id, is_device_id_valid
from rsa_utils import (
    load_private_key, 
    load_public_key, 
    create_signed_license, 
    is_license_valid
)


class LicenseService:
    """Main license service for Pharmacy ERP."""
    
    def __init__(self, keys_dir: str = None):
        """
        Initialize license service.
        
        Args:
            keys_dir: Directory containing RSA keys (default: ./keys relative to this file)
        """
        if keys_dir is None:
            # Default to keys directory in frontend/license/keys
            self.keys_dir = os.path.join(os.path.dirname(__file__), "keys")
        else:
            self.keys_dir = keys_dir
            
        self.public_key = None
        self.private_key = None
        self._load_keys()
    
    def _load_keys(self):
        """Load RSA public and private keys."""
        try:
            public_key_path = os.path.join(self.keys_dir, "public_key.pem")
            private_key_path = os.path.join(self.keys_dir, "private_key.pem")
            
            if os.path.exists(public_key_path) and os.path.exists(private_key_path):
                self.public_key = load_public_key(public_key_path)
                self.private_key = load_private_key(private_key_path)
            else:
                # Keys don't exist, generate them
                self.generate_keys()
        except Exception as e:
            print(f"Warning: Could not load RSA keys: {e}")
            print("Generating new key pair...")
            self.generate_keys()
    
    def generate_keys(self):
        """Generate and save RSA key pair."""
        if not os.path.exists(self.keys_dir):
            os.makedirs(self.keys_dir)
            
        from rsa_utils import generate_keypair, save_private_key, save_public_key
        self.public_key, self.private_key = generate_keypair()
        
        save_private_key(self.private_key, os.path.join(self.keys_dir, "private_key.pem"))
        save_public_key(self.public_key, os.path.join(self.keys_dir, "public_key.pem"))
        
        print(f"Generated new RSA key pair in {self.keys_dir}")
    
    def get_current_device_id(self) -> str:
        """
        Get the current device ID.
        
        Returns:
            Unique device identifier string
        """
        return generate_device_id()
    
    def create_license(self, 
                      device_id: Optional[str] = None,
                      expiration_date: Optional[date] = None,
                      features: Optional[list] = None,
                      license_type: str = "pharmacy_erp") -> Dict[str, Any]:
        """
        Create a new license for a device.
        
        Args:
            device_id: Target device ID (if None, uses current device)
            expiration_date: License expiration date
            features: List of enabled features
            license_type: Type of license
            
        Returns:
            Complete license dictionary with data and signature
        """
        if device_id is None:
            device_id = self.get_current_device_id()
        
        if not is_device_id_valid(device_id):
            raise ValueError(f"Invalid device ID format: {device_id}")
        
        if self.private_key is None:
            raise RuntimeError("Private key not available for signing")
        
        return create_signed_license(
            device_id=device_id,
            private_key=self.private_key,
            expiration_date=expiration_date,
            features=features,
            license_type=license_type
        )
    
    def validate_license(self, license_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a license.
        
        Args:
            license_data: License dictionary to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if self.public_key is None:
            return False, "Public key not available for verification"
        
        return is_license_valid(license_data, self.public_key)
    
    def validate_current_device_license(self, license_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a license for the current device.
        
        Args:
            license_data: License dictionary to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        # First validate the license signature and basic properties
        is_valid, message = self.validate_license(license_data)
        if not is_valid:
            return False, message
        
        # Then check device binding
        license_device_id = license_data.get("license_data", {}).get("device_id")
        current_device_id = self.get_current_device_id()
        
        if license_device_id != current_device_id:
            return False, f"License device mismatch: expected {current_device_id}, got {license_device_id}"
        
        return True, "License is valid for this device"
    
    def save_license_to_file(self, license_data: Dict[str, Any], filename: str):
        """
        Save license data to JSON file.
        
        Args:
            license_data: License dictionary to save
            filename: Output file path
        """
        with open(filename, 'w') as f:
            json.dump(license_data, f, indent=2)
    
    def load_license_from_file(self, filename: str) -> Dict[str, Any]:
        """
        Load license data from JSON file.
        
        Args:
            filename: Input file path
            
        Returns:
            License dictionary
        """
        with open(filename, 'r') as f:
            return json.load(f)


# Convenience functions for direct usage
def create_license_for_current_device(expiration_date: Optional[date] = None,
                                    features: Optional[list] = None) -> Dict[str, Any]:
    """
    Create a license for the current device.
    
    Args:
        expiration_date: License expiration date
        features: List of enabled features
        
    Returns:
        Complete license dictionary
    """
    service = LicenseService()
    return service.create_license(
        device_id=service.get_current_device_id(),
        expiration_date=expiration_date,
        features=features
    )


def validate_license_file(license_filename: str) -> Tuple[bool, str]:
    """
    Validate a license from file.
    
    Args:
        license_filename: Path to license JSON file
        
    Returns:
        Tuple of (is_valid, message)
    """
    service = LicenseService()
    try:
        license_data = service.load_license_from_file(license_filename)
        return service.validate_current_device_license(license_data)
    except Exception as e:
        return False, f"Failed to load or validate license: {str(e)}"


if __name__ == "__main__":
    # Example usage
    print("Pharmacy ERP License Service")
    print("=" * 40)
    
    # Initialize service (will generate keys if needed)
    service = LicenseService()
    
    # Show current device ID
    device_id = service.get_current_device_id()
    print(f"Current Device ID: {device_id}")
    
    # Create a sample license
    print("\nCreating sample license...")
    license_data = service.create_license(
        device_id=device_id,
        expiration_date=date(2027, 12, 31),
        features=["inventory", "sales", "purchases", "accounting", "reports"]
    )
    
    # Display license info
    print(f"License created for device: {license_data['license_data']['device_id']}")
    print(f"License expires: {license_data['license_data'].get('expiration_date', 'Never')}")
    print(f"Features: {license_data['license_data'].get('features', [])}")
    print(f"Signature: {license_data['signature'][:50]}...")
    
    # Validate the license
    print("\nValidating license...")
    is_valid, message = service.validate_current_device_license(license_data)
    print(f"Validation result: {is_valid}")
    print(f"Message: {message}")
    
    # Save license to file
    license_file = "sample_license.json"
    service.save_license_to_file(license_data, license_file)
    print(f"\nLicense saved to {license_file}")
    
    # Load and validate from file
    print(f"Loading and validating from {license_file}...")
    is_valid2, message2 = validate_license_file(license_file)
    print(f"File validation result: {is_valid2}")
    print(f"Message: {message2}")
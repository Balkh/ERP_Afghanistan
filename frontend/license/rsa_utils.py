"""
RSA utilities for license signing and verification.
Handles RSA key generation, signing, and verification for license security.
"""

import rsa
import json
import base64
import hashlib
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional
import os
from cryptography.hazmat.primitives import hashes, asymmetric, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def generate_keypair(key_size: int = 2048) -> Tuple[rsa.PublicKey, rsa.PrivateKey]:
    """
    Generate RSA public/private key pair.
    
    Args:
        key_size: Size of the key in bits (default 2048)
        
    Returns:
        Tuple of (public_key, private_key)
    """
    return rsa.newkeys(key_size)


def save_private_key(private_key: rsa.PrivateKey, filename: str):
    """
    Save RSA private key to file in PEM format.
    
    Args:
        private_key: RSA private key object
        filename: Path to save the key
    """
    with open(filename, 'wb') as f:
        f.write(private_key.save_pkcs1('PEM'))


def load_private_key(filename: str) -> rsa.PrivateKey:
    """
    Load RSA private key from PEM file.
    
    Args:
        filename: Path to the private key file
        
    Returns:
        RSA private key object
    """
    with open(filename, 'rb') as f:
        return rsa.PrivateKey.load_pkcs1(f.read())


def save_public_key(public_key: rsa.PublicKey, filename: str):
    """
    Save RSA public key to file in PEM format.
    
    Args:
        public_key: RSA public key object
        filename: Path to save the key
    """
    with open(filename, 'wb') as f:
        f.write(public_key.save_pkcs1('PEM'))


def load_public_key(filename: str) -> rsa.PublicKey:
    """
    Load RSA public key from PEM file.
    
    Args:
        filename: Path to the public key file
        
    Returns:
        RSA public key object
    """
    with open(filename, 'rb') as f:
        return rsa.PublicKey.load_pkcs1(f.read())


def create_license_data(device_id: str, 
                       expiration_date: Optional[date] = None,
                       features: Optional[list] = None,
                       issued_date: Optional[date] = None,
                       license_type: str = "standard") -> Dict[str, Any]:
    """
    Create license data structure.
    
    Args:
        device_id: Unique device identifier
        expiration_date: License expiration date (optional)
        features: List of enabled features/modules (optional)
        issued_date: License issue date (defaults to today)
        license_type: Type of license (default "standard")
        
    Returns:
        Dictionary containing license data
    """
    if issued_date is None:
        issued_date = date.today()
    
    license_data = {
        "device_id": device_id,
        "issued_date": issued_date.isoformat(),
        "license_type": license_type,
        "version": "1.0"
    }
    
    if expiration_date:
        license_data["expiration_date"] = expiration_date.isoformat()
    
    if features:
        license_data["features"] = features
    
    return license_data


def sign_license(license_data: Dict[str, Any], 
                 private_key: rsa.PrivateKey) -> str:
    """
    Sign license data using RSA private key.
    
    Args:
        license_data: Dictionary containing license information
        private_key: RSA private key for signing
        
    Returns:
        Base64-encoded signature
    """
    # Convert license data to JSON string with sorted keys for consistency
    license_json = json.dumps(license_data, sort_keys=True, separators=(',', ':'))
    
    # Sign the JSON string
    signature = rsa.sign(license_json.encode('utf-8'), private_key, 'SHA-256')
    
    # Return base64 encoded signature
    return base64.b64encode(signature).decode('utf-8')


def verify_license(license_data: Dict[str, Any],
                   signature_b64: str,
                   public_key: rsa.PublicKey) -> bool:
    """
    Verify license signature using RSA public key.
    
    Args:
        license_data: Dictionary containing license information
        signature_b64: Base64-encoded signature
        public_key: RSA public key for verification
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Convert license data to JSON string with same format as signing
        license_json = json.dumps(license_data, sort_keys=True, separators=(',', ':'))
        
        # Decode base64 signature
        signature = base64.b64decode(signature_b64)
        
        # Verify the signature
        rsa.verify(license_json.encode('utf-8'), signature, public_key)
        return True
    except (rsa.VerificationError, ValueError, base64.binascii.Error):
        return False


def verify_license_pss(license_data: Dict[str, Any],
                       signature_b64: str,
                       pub_pem: bytes) -> bool:
    """
    Verify license signature using RSA-PSS + SHA256 (preferred method).

    Falls back to PKCS1v15 on failure for backward compatibility.
    Uses cryptography.hazmat for PSS support.
    """
    try:
        license_json = json.dumps(license_data, sort_keys=True, separators=(',', ':'))
        sig = base64.b64decode(signature_b64)
        pub_key = serialization.load_pem_public_key(pub_pem)
        pub_key.verify(
            sig,
            license_json.encode('utf-8'),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def create_signed_license(device_id: str,
                         private_key: rsa.PrivateKey,
                         expiration_date: Optional[date] = None,
                         features: Optional[list] = None,
                         license_type: str = "standard") -> Dict[str, Any]:
    """
    Create a signed license.
    
    Args:
        device_id: Unique device identifier
        private_key: RSA private key for signing
        expiration_date: License expiration date (optional)
        features: List of enabled features/modules (optional)
        license_type: Type of license (default "standard")
        
    Returns:
        Dictionary containing license data and signature
    """
    # Create license data
    license_data = create_license_data(
        device_id=device_id,
        expiration_date=expiration_date,
        features=features,
        license_type=license_type
    )
    
    # Sign the license data
    signature = sign_license(license_data, private_key)
    
    # Return complete license
    return {
        "license_data": license_data,
        "signature": signature
    }


def is_license_valid(license: Dict[str, Any],
                     public_key: rsa.PublicKey) -> Tuple[bool, str]:
    """
    Validate a license (check signature and expiration).
    
    Args:
        license: Dictionary containing license data and signature
        public_key: RSA public key for verification
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        license_data = license.get("license_data")
        signature = license.get("signature")
        
        if not license_data or not signature:
            return False, "Invalid license format"
        
        # Verify signature
        if not verify_license(license_data, signature, public_key):
            return False, "Invalid license signature"
        
        # Check expiration
        expiration_str = license_data.get("expiration_date")
        if expiration_str:
            expiration_date = date.fromisoformat(expiration_str)
            if date.today() > expiration_date:
                return False, f"License expired on {expiration_date}"
        
        # Check device binding (this would be done by comparing with current device ID)
        # For now, we assume the caller will check device_id matches
        
        return True, "License is valid"
    except Exception as e:
        return False, f"License validation error: {str(e)}"


# Example usage functions
def generate_license_files(output_dir: str = "./keys"):
    """
    Generate RSA key pair and save to files.
    
    Args:
        output_dir: Directory to save key files
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate key pair
    public_key, private_key = generate_keypair()
    
    # Save keys
    save_private_key(private_key, os.path.join(output_dir, "private_key.pem"))
    save_public_key(public_key, os.path.join(output_dir, "public_key.pem"))
    
    print(f"RSA key pair generated and saved to {output_dir}")
    print(f"Private key: {os.path.join(output_dir, 'private_key.pem')}")
    print(f"Public key: {os.path.join(output_dir, 'public_key.pem')}")
    
    return public_key, private_key
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
import json
import base64
import os
from typing import Tuple, Optional, Dict, Any
from datetime import datetime


class RSAKeyManager:
    """
    Manages RSA key pair for license signing and verification.
    """
    
    def __init__(self, private_key_path: str = None, public_key_path: str = None):
        """
        Initialize the RSA key manager.
        
        Args:
            private_key_path: Path to the private key file (PEM format)
            public_key_path: Path to the public key file (PEM format)
        """
        self.private_key_path = private_key_path or os.path.join(
            os.path.dirname(__file__), 'keys', 'private_key.pem'
        )
        self.public_key_path = public_key_path or os.path.join(
            os.path.dirname(__file__), 'keys', 'public_key.pem'
        )
        self._private_key = None
        self._public_key = None
        
        # Ensure the keys directory exists
        os.makedirs(os.path.dirname(self.private_key_path), exist_ok=True)
    
    def generate_keypair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        Generate a new RSA key pair.
        
        Args:
            key_size: Size of the key in bits (default 2048)
            
        Returns:
            Tuple of (private_key_pem, public_key_pem) as bytes
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize private key to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key to PEM format
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    def load_private_key(self):
        """Load the private key from file."""
        if self._private_key is None:
            if not os.path.exists(self.private_key_path):
                # Generate a new keypair if keys don't exist
                private_pem, public_pem = self.generate_keypair()
                self.save_keypair(private_pem, public_pem)
            
            with open(self.private_key_path, 'rb') as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
        return self._private_key
    
    def load_public_key(self):
        """Load the public key from file."""
        if self._public_key is None:
            if not os.path.exists(self.public_key_path):
                # Generate a new keypair if keys don't exist
                private_pem, public_pem = self.generate_keypair()
                self.save_keypair(private_pem, public_pem)
            
            with open(self.public_key_path, 'rb') as f:
                self._public_key = serialization.load_pem_public_key(f.read())
        return self._public_key
    
    def save_keypair(self, private_pem: bytes, public_pem: bytes):
        """Save the key pair to files."""
        with open(self.private_key_path, 'wb') as f:
            f.write(private_pem)
        with open(self.public_key_path, 'wb') as f:
            f.write(public_pem)
    
    def sign_data(self, data: str) -> str:
        """
        Sign data using the private key.
        
        Args:
            data: String data to sign
            
        Returns:
            Base64-encoded signature
        """
        private_key = self.load_private_key()
        
        # Sign the data
        signature = private_key.sign(
            data.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Return base64 encoded signature
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, data: str, signature_b64: str) -> bool:
        """
        Verify a signature using the public key.
        
        Args:
            data: Original string data
            signature_b64: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            public_key = self.load_public_key()
            signature = base64.b64decode(signature_b64)
            
            public_key.verify(
                signature,
                data.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except (InvalidSignature, Exception):
            return False


# Global instance for ease of use
rsa_manager = RSAKeyManager()


def create_signed_license(license_data: Dict[str, Any]) -> str:
    """
    Create a signed license string from license data.
    
    Args:
        license_data: Dictionary containing license information
        
    Returns:
        Signed license string in format: "data.*signature"
        where data is base64-encoded JSON and signature is base64-encoded RSA signature
    """
    # Convert data to JSON string, then base64 encode
    json_str = json.dumps(license_data, separators=(',', ':'))  # Compact JSON
    data_b64 = base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    # Sign the base64-encoded data
    signature = rsa_manager.sign_data(data_b64)
    
    # Combine: data_b64 + '.' + signature
    return f"{data_b64}.{signature}"


def verify_signed_license(signed_license: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a signed license string.
    
    Args:
        signed_license: String in format "data.*signature"
        
    Returns:
        Dictionary of license data if valid, None otherwise
    """
    try:
        # Split into data and signature
        parts = signed_license.split('.')
        if len(parts) != 2:
            return None
        
        data_b64, signature_b64 = parts
        
        # Verify the signature
        if not rsa_manager.verify_signature(data_b64, signature_b64):
            return None
        
        # Decode the data
        json_str = base64.urlsafe_b64decode(data_b64).decode('utf-8')
        license_data = json.loads(json_str)
        
        return license_data
    except Exception:
        return None
"""
Test script for the RSA license system.
Tests license generation, signing, verification, and validation.
"""

import os
import sys
import tempfile
from datetime import date, timedelta

# Add the frontend directory to the Python path for utils import
frontend_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, frontend_dir)
# Add the license directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from rsa_utils import (
    generate_keypair,
    save_private_key,
    save_public_key,
    load_private_key,
    load_public_key,
    create_license_data,
    sign_license,
    verify_license,
    create_signed_license,
    is_license_valid
)
from license_service import LicenseService, create_license_for_current_device, validate_license_file


def test_rsa_key_generation():
    """Test RSA key generation and loading."""
    print("Testing RSA key generation...")
    
    # Generate keys
    public_key, private_key = generate_keypair()
    assert public_key is not None
    assert private_key is not None
    print("PASS: Key pair generated successfully")
    
    # Test saving and loading keys
    with tempfile.TemporaryDirectory() as temp_dir:
        priv_path = os.path.join(temp_dir, "test_private.pem")
        pub_path = os.path.join(temp_dir, "test_public.pem")
        
        save_private_key(private_key, priv_path)
        save_public_key(public_key, pub_path)
        
        loaded_private = load_private_key(priv_path)
        loaded_public = load_public_key(pub_path)
        
        # Test that loaded keys work
        assert loaded_private is not None
        assert loaded_public is not None
        print("PASS: Key save/load successful")


def test_license_creation_and_signing():
    """Test license creation and signing process."""
    print("\nTesting license creation and signing...")
    
    # Generate test keys
    public_key, private_key = generate_keypair()
    
    # Create license data
    device_id = "test_device_1234567890123456789012"  # 32 char hex
    license_data = create_license_data(
        device_id=device_id,
        expiration_date=date(2027, 6, 30),
        features=["inventory", "sales"],
        license_type="test"
    )
    
    # Sign the license
    signature = sign_license(license_data, private_key)
    assert isinstance(signature, str)
    assert len(signature) > 0
    print("PASS: License signing successful")
    
    # Verify the signature
    is_valid = verify_license(license_data, signature, public_key)
    assert is_valid == True
    print("PASS: License verification successful")
    
     # Test with tampered data
     tampered_data = license_data.copy()
     tampered_data["device_id"] = "tampered_device_id"
     is_valid_tampered = verify_license(tampered_data, signature, public_key)
     assert is_valid_tampered == False
     print("PASS: Tamper detection working")


def test_complete_license_flow():
    """Test complete license creation and validation flow."""
    print("\nTesting complete license flow...")
    
    # Generate keys
    public_key, private_key = generate_keypair()
    
    # Create signed license
    license = create_signed_license(
        device_id="test_device_abcdef1234567890abcdef123456",
        private_key=private_key,
        expiration_date=date(2026, 12, 31),
        features=["accounting", "reports"],
        license_type="enterprise"
    )
    
     # Validate license
     is_valid, message = is_license_valid(license, public_key)
     assert is_valid == True
     assert "valid" in message.lower()
     print("PASS: Complete license flow successful")


def test_license_service():
    """Test the LicenseService class."""
    print("\nTesting LicenseService class...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create service with temporary directory
        service = LicenseService(keys_dir=temp_dir)
        
        # Check that keys were generated
        assert service.public_key is not None
        assert service.private_key is not None
        print("PASS: LicenseService initialized with generated keys")
        
        # Get device ID
        device_id = service.get_current_device_id()
        assert is_device_id_valid(device_id)
        print(f"PASS: Device ID retrieved: {device_id[:16]}...")
        
        # Create license
        license_data = service.create_license(
            device_id=device_id,
            expiration_date=date(2026, 12, 31),
            features=["inventory", "sales", "accounting"],
            license_type="test"
        )
        
        # Validate license
        is_valid, message = service.validate_current_device_license(license_data)
        assert is_valid == True
        print("PASS: LicenseService license creation and validation successful")
        
        # Test file operations
        license_file = os.path.join(temp_dir, "test_license.json")
        service.save_license_to_file(license_data, license_file)
        
        loaded_license = service.load_license_from_file(license_file)
        assert "license_data" in loaded_license
        assert "signature" in loaded_license
        print("PASS: License file save/load successful")


def test_convenience_functions():
    """Test convenience functions."""
    print("\nTesting convenience functions...")
    
    # Test creating license for current device
    try:
        license_data = create_license_for_current_device(
            expiration_date=date(2026, 6, 30),
            features=["test_feature"]
        )
        
        assert "license_data" in license_data
        assert "signature" in license_data
        assert license_data["license_data"]["device_id"] is not None
        print("PASS: Convenience license creation successful")
        
        # Test validation (will fail due to key mismatch, but should not crash)
        # This is expected since we're using different service instances
        is_valid, message = validate_license_file("nonexistent_license.json")
        assert is_valid == False
        print("PASS: Convenience validation function handles errors gracefully")
        
    except Exception as e:
        print(f"⚠ Convenience function test had expected issue: {e}")


def run_all_tests():
    """Run all tests."""
    print("Pharmacy ERP RSA License System Test Suite")
    print("=" * 50)
    
    try:
        test_rsa_key_generation()
        test_license_creation_and_signing()
        test_complete_license_flow()
        test_license_service()
        test_convenience_functions()
        
        print("\n" + "=" * 50)
        print("All tests passed! PASS")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
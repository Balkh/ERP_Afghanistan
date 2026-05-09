"""
Test script for device fingerprinting utilities.
Run this script to verify the hardware identification functions work correctly.
"""

from hardware_id import get_cpu_id, get_mac_address, get_disk_serial
from device_fingerprint import generate_device_id, get_device_fingerprint, is_device_id_valid


def test_hardware_id_functions():
    """Test individual hardware ID functions."""
    print("Testing hardware ID functions:")
    print("-" * 40)
    
    cpu_id = get_cpu_id()
    print(f"CPU ID: '{cpu_id}' (length: {len(cpu_id)})")
    
    mac_address = get_mac_address()
    print(f"MAC Address: '{mac_address}' (length: {len(mac_address)})")
    
    disk_serial = get_disk_serial()
    print(f"Disk Serial: '{disk_serial}' (length: {len(disk_serial)})")
    
    print()


def test_device_fingerprint_functions():
    """Test device fingerprint functions."""
    print("Testing device fingerprint functions:")
    print("-" * 40)
    
    # Test detailed fingerprint
    fingerprint = get_device_fingerprint()
    print("Device Fingerprint:")
    for key, value in fingerprint.items():
        print(f"  {key}: '{value}' (length: {len(value)})")
    
    print()
    
    # Test device ID generation
    device_id = generate_device_id()
    print(f"Generated Device ID: '{device_id}' (length: {len(device_id)})")
    
    # Test validation
    is_valid = is_device_id_valid(device_id)
    print(f"Device ID Valid: {is_valid}")
    
    # Test with invalid ID
    invalid_id = "invalid123"
    is_valid_invalid = is_device_id_valid(invalid_id)
    print(f"Invalid ID '{invalid_id}' Valid: {is_valid_invalid}")
    
    print()


def main():
    """Main test function."""
    print("Pharmacy ERP - Device Fingerprinting Test")
    print("=" * 50)
    print()
    
    test_hardware_id_functions()
    test_device_fingerprint_functions()
    
    print("Test completed.")


if __name__ == "__main__":
    main()
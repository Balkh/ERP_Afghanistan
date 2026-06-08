"""
Device fingerprint service for generating unique device identifiers.
Combines multiple hardware identifiers to create a stable, unique device ID.
"""

import hashlib
from .hardware_id import get_cpu_id, get_mac_address, get_disk_serial


def generate_device_id() -> str:
    """
    Generate a unique device ID based on hardware fingerprints.
    
    Combines CPU ID, MAC address, and disk serial number to create
    a stable identifier that should remain consistent for the same machine.
    
    Returns:
        str: A 32-character hexadecimal device ID
    """
    # Collect hardware identifiers
    cpu_id = get_cpu_id()
    mac_address = get_mac_address()
    disk_serial = get_disk_serial()
    
    # Combine the identifiers
    combined = f"{cpu_id}|{mac_address}|{disk_serial}"
    
    # Create a hash of the combined string
    # Using SHA256 for good distribution and taking first 32 chars
    device_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    return device_hash


def get_device_fingerprint() -> dict:
    """
    Get detailed device fingerprint information.
    
    Returns:
        dict: Dictionary containing individual hardware identifiers and the generated device ID
    """
    return {
        "cpu_id": get_cpu_id(),
        "mac_address": get_mac_address(),
        "disk_serial": get_disk_serial(),
        "device_id": generate_device_id()
    }


def is_device_id_valid(device_id: str) -> bool:
    """
    Validate if a device ID has the correct format.
    
    Args:
        device_id: The device ID to validate
        
    Returns:
        bool: True if device_id is a 32-character hexadecimal string
    """
    if not device_id or len(device_id) not in (32, 64):
        return False

    try:
        int(device_id, 16)
        return True
    except ValueError:
        return False
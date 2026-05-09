"""
Device Fingerprint Provider Abstraction Layer

Provides abstraction for hardware fingerprint detection to enable:
- Production hardware fingerprinting
- Deterministic testing with mock fingerprints
- Security validation preservation

This module implements the provider pattern for device fingerprinting,
allowing dependency injection for testing while maintaining production security.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import hashlib


class DeviceFingerprintProvider(ABC):
    """
    Abstract base class for device fingerprint providers.
    
    This abstraction allows:
    - Production hardware fingerprinting
    - Mock fingerprinting for testing
    - Future provider implementations (e.g., cloud-based)
    """
    
    @abstractmethod
    def get_cpu_id(self) -> str:
        """Get CPU identifier."""
        pass
    
    @abstractmethod
    def get_mac_address(self) -> str:
        """Get MAC address of primary network interface."""
        pass
    
    @abstractmethod
    def get_disk_serial(self) -> str:
        """Get disk serial number."""
        pass
    
    def get_fingerprint(self) -> Dict[str, str]:
        """
        Get complete device fingerprint.
        
        Returns:
            dict: Fingerprint with cpu_id, mac_address, disk_serial, device_id
        """
        cpu_id = self.get_cpu_id()
        mac_addr = self.get_mac_address()
        disk_serial = self.get_disk_serial()
        device_id = self._generate_device_id(cpu_id, mac_addr, disk_serial)
        
        return {
            'cpu_id': cpu_id,
            'mac_address': mac_addr,
            'disk_serial': disk_serial,
            'device_id': device_id,
        }
    
    def _generate_device_id(self, cpu_id: str, mac_addr: str, disk_serial: str) -> str:
        """Generate device ID from fingerprint components."""
        combined = f"{cpu_id}|{mac_addr}|{disk_serial}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()


class ProductionFingerprintProvider(DeviceFingerprintProvider):
    """
    Production fingerprint provider using actual hardware.
    
    Uses licensing.utils functions to retrieve real hardware identifiers.
    This provider should be used in production environments.
    """
    
    def get_cpu_id(self) -> str:
        """Get CPU identifier from hardware."""
        from licensing.utils import get_cpu_id
        return get_cpu_id()
    
    def get_mac_address(self) -> str:
        """Get MAC address from hardware."""
        from licensing.utils import get_mac_address
        return get_mac_address()
    
    def get_disk_serial(self) -> str:
        """Get disk serial from hardware."""
        from licensing.utils import get_disk_serial
        return get_disk_serial()


class MockFingerprintProvider(DeviceFingerprintProvider):
    """
    Mock fingerprint provider for testing.
    
    Provides deterministic, reproducible fingerprints for automated testing.
    Does NOT access any hardware - returns predefined values.
    """
    
    def __init__(
        self,
        cpu_id: str = "MOCK_CPU_001",
        mac_address: str = "00:11:22:33:44:55",
        disk_serial: str = "MOCK_DISK_001",
    ):
        self._cpu_id = cpu_id
        self._mac_address = mac_address
        self._disk_serial = disk_serial
    
    def get_cpu_id(self) -> str:
        """Return mock CPU ID."""
        return self._cpu_id
    
    def get_mac_address(self) -> str:
        """Return mock MAC address."""
        return self._mac_address
    
    def get_disk_serial(self) -> str:
        """Return mock disk serial."""
        return self._disk_serial


class TestFingerprintProvider(MockFingerprintProvider):
    """
    Test fingerprint provider with configurable values.
    
    Extends MockFingerprintProvider for test fixtures that need
    specific hardware configurations.
    """
    
    @classmethod
    def from_device_id(cls, device_id: str) -> 'TestFingerprintProvider':
        """
        Create a provider that generates a specific device ID.
        
        Args:
            device_id: Desired device ID
            
        Returns:
            TestFingerprintProvider that produces the specified device_id
        """
        return cls(
            cpu_id=f"TEST_CPU_{device_id[:8]}",
            mac_address=f"00:11:22:33:44:{device_id[38:40]}",
            disk_serial=f"TEST_DISK_{device_id[16:24]}",
        )


def get_fingerprint_provider(use_mock: bool = False) -> DeviceFingerprintProvider:
    """
    Factory function to get appropriate fingerprint provider.
    
    Args:
        use_mock: If True, return mock provider for testing
        
    Returns:
        DeviceFingerprintProvider instance
    """
    if use_mock:
        return MockFingerprintProvider()
    return ProductionFingerprintProvider()
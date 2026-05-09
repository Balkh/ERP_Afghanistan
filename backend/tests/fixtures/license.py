"""
Licensing test fixtures for deterministic testing.

Provides reusable fixtures for licensing tests that use
mock fingerprint providers instead of real hardware.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import pytest

from licensing.models import DeviceLicense
from licensing.providers import (
    MockFingerprintProvider,
    TestFingerprintProvider,
    set_fingerprint_provider,
)
from licensing.services import LicenseService


# Standard test fingerprint values
TEST_CPU_ID = "TEST_CPU_12345678"
TEST_MAC_ADDRESS = "00:11:22:33:44:55"
TEST_DISK_SERIAL = "TEST_DISK_87654321"


class LicenseTestFixtures:
    """
    Reusable fixtures for licensing tests.
    
    Provides:
    - Mock provider setup/teardown
    - Test license creation
    - Fingerprint reset functionality
    """
    
    @staticmethod
    def setup_mock_provider():
        """Set up mock fingerprint provider for tests."""
        mock_provider = MockFingerprintProvider(
            cpu_id=TEST_CPU_ID,
            mac_address=TEST_MAC_ADDRESS,
            disk_serial=TEST_DISK_SERIAL,
        )
        set_fingerprint_provider(mock_provider)
    
    @staticmethod
    def setup_custom_provider(cpu_id: str, mac_address: str, disk_serial: str):
        """Set up custom mock provider with specific values."""
        mock_provider = MockFingerprintProvider(
            cpu_id=cpu_id,
            mac_address=mac_address,
            disk_serial=disk_serial,
        )
        set_fingerprint_provider(mock_provider)
    
    @staticmethod
    def setup_provider_from_device_id(device_id: str):
        """Set up provider that generates specific device ID."""
        provider = TestFingerprintProvider.from_device_id(device_id)
        set_fingerprint_provider(provider)
    
    @staticmethod
    def reset_provider():
        """Reset to production provider."""
        set_fingerprint_provider(None)
    
    @staticmethod
    def create_test_license(
        license_key: str = None,
        license_type: str = 'perpetual',
        issued_date: Optional[date] = None,
        expires_date: Optional[date] = None,
        is_active: bool = True,
    ) -> DeviceLicense:
        """
        Create a test license with mock fingerprint.
        
        Args:
            license_key: Unique license key (auto-generated if None)
            license_type: Type of license
            issued_date: Issue date (today if None)
            expires_date: Expiration date (None for perpetual)
            is_active: Whether license is active
            
        Returns:
            DeviceLicense: Created license object
        """
        if license_key is None:
            license_key = f"TEST-LICENSE-{uuid.uuid4().hex[:12].upper()}"
        
        if issued_date is None:
            issued_date = date.today()
        
        # Ensure provider is set before creating license
        if get_fingerprint_provider_instance() is None or isinstance(
            get_fingerprint_provider_instance(), type(ProductionFingerprintProvider())
        ):
            LicenseTestFixtures.setup_mock_provider()
        
        fingerprint = LicenseService.get_current_device_fingerprint()
        device_id = fingerprint['device_id']
        
        license_obj = DeviceLicense.objects.create(
            license_key=license_key,
            device_fingerprint=fingerprint,
            device_id=device_id,
            license_type=license_type,
            issued_date=issued_date,
            expires_date=expires_date,
            is_active=is_active,
        )
        
        return license_obj
    
    @staticmethod
    def create_expired_license(license_key: str = None) -> DeviceLicense:
        """Create an expired test license."""
        return LicenseTestFixtures.create_test_license(
            license_key=license_key,
            license_type='expiring',
            issued_date=date.today() - timedelta(days=400),
            expires_date=date.today() - timedelta(days=30),
        )
    
    @staticmethod
    def create_inactive_license(license_key: str = None) -> DeviceLicense:
        """Create an inactive test license."""
        return LicenseTestFixtures.create_test_license(
            license_key=license_key,
            is_active=False,
        )


@pytest.fixture
def mock_fingerprint_provider():
    """
    Pytest fixture that sets up mock fingerprint provider.
    
    Usage:
        def test_something(mock_fingerprint_provider):
            # Provider is already set up
            fingerprint = LicenseService.get_current_device_fingerprint()
            assert fingerprint['cpu_id'] == TEST_CPU_ID
    """
    LicenseTestFixtures.setup_mock_provider()
    yield
    LicenseTestFixtures.reset_provider()


@pytest.fixture
def test_license(mock_fingerprint_provider):
    """
    Pytest fixture that creates a test license.
    
    Usage:
        def test_validation(test_license):
            result = LicenseService.validate_license(test_license.license_key)
            assert result == test_license
    """
    return LicenseTestFixtures.create_test_license()


@pytest.fixture
def expired_test_license(mock_fingerprint_provider):
    """Pytest fixture for expired license."""
    return LicenseTestFixtures.create_expired_license()


@pytest.fixture
def inactive_test_license(mock_fingerprint_provider):
    """Pytest fixture for inactive license."""
    return LicenseTestFixtures.create_inactive_license()


# Import required for fixtures
from licensing.providers import ProductionFingerprintProvider


# Export for easy importing
__all__ = [
    'LicenseTestFixtures',
    'mock_fingerprint_provider',
    'test_license',
    'expired_test_license',
    'inactive_test_license',
    'TEST_CPU_ID',
    'TEST_MAC_ADDRESS',
    'TEST_DISK_SERIAL',
]
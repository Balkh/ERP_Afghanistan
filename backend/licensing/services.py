from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import DeviceLicense
from .providers import DeviceFingerprintProvider, ProductionFingerprintProvider, get_fingerprint_provider
from .rsa import create_signed_license, verify_signed_license
from .validator import LicenseValidator


class LicenseValidationError(ValidationError):
    pass


_fingerprint_provider: DeviceFingerprintProvider = None


def set_fingerprint_provider(provider):
    global _fingerprint_provider
    _fingerprint_provider = provider


def get_fingerprint_provider_instance():
    global _fingerprint_provider
    if _fingerprint_provider is None:
        return ProductionFingerprintProvider()
    return _fingerprint_provider


class LicenseService:
    """
    Lightweight license service facade.
    Delegates to LicenseValidator for state evaluation.
    """

    _validator = None

    @classmethod
    def _get_validator(cls) -> LicenseValidator:
        if cls._validator is None:
            cls._validator = LicenseValidator()
        return cls._validator

    @staticmethod
    def get_current_device_fingerprint():
        return get_fingerprint_provider_instance().get_fingerprint()

    @staticmethod
    def get_current_device_id():
        return LicenseService.get_current_device_fingerprint()['device_id']

    @staticmethod
    def validate_license(license_key=None):
        """Returns validated license, trial, or raises error."""
        val = LicenseService._get_validator()
        state = val.validate()

        if state == "dev":
            return None
        if state == "trial":
            return val._find_active_trial()
        if state == "licensed":
            return val._find_valid_license()

        info = val.get_info()
        raise LicenseValidationError(info.get("message", "License is not valid"))

    @staticmethod
    def is_licensed(license_key=None):
        try:
            result = LicenseService.validate_license(license_key)
            return result is not None
        except LicenseValidationError:
            return False

    @staticmethod
    def get_license_info(license_key=None):
        val = LicenseService._get_validator()
        val.validate()
        return val.get_info()

    @staticmethod
    def create_license(license_key, issued_to=None, expires_date=None, notes=None):
        if DeviceLicense.objects.filter(license_key=license_key).exists():
            raise ValidationError(f"License key '{license_key}' already exists")

        fingerprint = LicenseService.get_current_device_fingerprint()
        from licensing.utils import generate_device_id_from_fingerprint
        device_id = generate_device_id_from_fingerprint(fingerprint)

        license_data = {
            'license_key': license_key,
            'device_id': device_id,
            'issued_to': issued_to or '',
            'issued_date': timezone.now().date().isoformat(),
            'expires_date': expires_date.isoformat() if expires_date else None,
            'license_type': 'pharmacy_erp',
            'created_at': timezone.now().isoformat(),
        }
        signed_license = create_signed_license(license_data)

        lic = DeviceLicense(
            license_key=license_key,
            device_fingerprint=fingerprint,
            device_id=device_id,
            signed_license=signed_license,
            issued_to=issued_to or '',
            expires_date=expires_date,
            notes=notes or '',
            is_active=True,
        )
        lic.full_clean()
        lic.save()
        return lic

    @staticmethod
    def generate_activation_request():
        return LicenseService._get_validator().generate_activation_request()

    @staticmethod
    def import_license_file(lic_filepath):
        success, message = LicenseService._get_validator().import_license(lic_filepath)
        if not success:
            raise LicenseValidationError(message)
        return message

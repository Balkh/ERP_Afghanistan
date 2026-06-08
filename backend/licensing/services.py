from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import DeviceLicense
from .providers import DeviceFingerprintProvider, ProductionFingerprintProvider, get_fingerprint_provider
from .rsa import create_signed_license
from .validator import resolve_license, LicenseValidator


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
    Delegates to resolve_license() for all state evaluation.
    """

    @staticmethod
    def get_current_device_fingerprint():
        return get_fingerprint_provider_instance().get_fingerprint()

    @staticmethod
    def get_current_device_id():
        return LicenseService.get_current_device_fingerprint()['device_id']

    @staticmethod
    def validate_license(license_key=None):
        """Returns validated license, trial, or raises error."""
        resolved = resolve_license()

        if resolved['mode'] == 'dev':
            return None
        if resolved['mode'] == 'trial':
            return resolved.get('trial')
        if resolved['mode'] == 'licensed':
            lic = resolved.get('license')
            if lic and lic.is_valid():
                return lic
            raise LicenseValidationError('License has expired')

        raise LicenseValidationError(resolved.get('message', 'License is not valid'))

    @staticmethod
    def is_licensed(license_key=None):
        try:
            result = LicenseService.validate_license(license_key)
            return result is not None
        except LicenseValidationError:
            return False

    @staticmethod
    def get_license_info(license_key=None):
        resolved = resolve_license()
        mode = resolved['mode']
        info = {'mode': mode, 'is_valid': resolved['is_valid'], 'message': resolved['message']}
        if mode == 'licensed':
            lic = resolved.get('license')
            if lic:
                info.update({
                    'license_key': lic.license_key,
                    'issued_to': lic.issued_to,
                    'company_name': lic.company_name,
                    'license_type': lic.license_type,
                    'features': lic.features,
                    'max_branches': lic.max_branches,
                    'expires_date': lic.expires_date.isoformat() if lic.expires_date else None,
                })
        elif mode == 'trial':
            trial = resolved.get('trial')
            if trial:
                info.update({
                    'days_remaining': trial.days_remaining(),
                    'expires_at': trial.expires_at.isoformat(),
                    'started_at': trial.started_at.isoformat(),
                    'access_count': trial.access_count,
                })
        return info

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
        return LicenseValidator().generate_activation_request()

    @staticmethod
    def import_license_file(lic_filepath):
        success, message = LicenseValidator().import_license(lic_filepath)
        if not success:
            raise LicenseValidationError(message)
        return message

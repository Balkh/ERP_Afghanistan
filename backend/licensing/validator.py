import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from django.utils import timezone

from .crypto import LicenseCrypto
from .fingerprint import DeviceFingerprintEngine
from .models import DeviceLicense, TrialSession
from .rsa import verify_signed_license


VALID_MODES = ("dev", "trial", "limited", "licensed")


def get_license_max_branches() -> int:
    """Return max_branches from active license, or 0 if no license (unlimited)."""
    resolved = resolve_license()
    if resolved['mode'] in ('dev', 'trial'):
        return 0
    return resolved.get('max_branches', 0)


def has_license_feature(feature_name: str) -> bool:
    """Check if current active license includes a feature. Unrestricted in dev/trial."""
    resolved = resolve_license()
    if resolved['mode'] in ('dev', 'trial'):
        return True
    return feature_name in resolved.get('features', [])


def is_dev_mode() -> bool:
    """Check if system is in development mode (all checks bypassed)."""
    from django.conf import settings
    return (
        settings.DEBUG
        or os.environ.get('ENV') == 'DEV'
        or os.environ.get('PHARMACY_ERP_LICENSE_BYPASS', '').lower() in ('true', '1', 'yes')
    )


def _resolve_valid_license(fingerprint: dict, device_id: str) -> Optional[DeviceLicense]:
    """Find best matching valid license — deterministic, no crash on duplicates."""
    for lic in DeviceLicense.objects.filter(
        device_id=device_id, is_active=True
    ).order_by('-created_at'):
        if lic.signed_license and not verify_signed_license(lic.signed_license):
            continue
        return lic
    for lic in DeviceLicense.objects.filter(is_active=True).order_by('-created_at'):
        if lic.signed_license and not verify_signed_license(lic.signed_license):
            continue
        if lic.matches_device(fingerprint):
            return lic
    return None


def resolve_license(request=None) -> Dict[str, Any]:
    """
    Single source of truth for license resolution.

    Returns a dict with keys: mode, is_valid, license, trial,
    features, max_branches, message.

    Resolves fingerprint, checks license (with signature verification),
    checks trial (no DB write on check), creates trial lazily.
    """
    if request and hasattr(request, 'license_state'):
        return request.license_state

    if is_dev_mode():
        return {
            'mode': 'dev',
            'is_valid': True,
            'license': None,
            'trial': None,
            'features': [],
            'max_branches': 0,
            'message': 'Development mode — all license checks bypassed',
        }

    try:
        fingerprint = DeviceFingerprintEngine().get_fingerprint()
        device_id = fingerprint['device_id']

        lic = _resolve_valid_license(fingerprint, device_id)
        if lic and lic.is_valid():
            return {
                'mode': 'licensed',
                'is_valid': True,
                'license': lic,
                'trial': None,
                'features': lic.features or [],
                'max_branches': lic.max_branches,
                'message': 'License is valid',
            }
        if lic:
            return {
                'mode': 'licensed',
                'is_valid': False,
                'license': lic,
                'trial': None,
                'features': lic.features or [],
                'max_branches': lic.max_branches,
                'message': 'License has expired',
            }

        trial = TrialSession.get_active_trial(device_id)
        if trial:
            return {
                'mode': 'trial',
                'is_valid': True,
                'license': None,
                'trial': trial,
                'features': [],
                'max_branches': 0,
                'message': f'Trial active — {trial.days_remaining()} days remaining',
            }

        expired = TrialSession.objects.filter(device_id=device_id).first()
        if expired and expired.is_expired():
            return {
                'mode': 'limited',
                'is_valid': False,
                'license': None,
                'trial': expired,
                'features': [],
                'max_branches': 0,
                'message': 'Trial period has expired. Please activate a license.',
            }

        trial, _ = TrialSession.get_or_create_for_device(device_id, fingerprint)
        return {
            'mode': 'trial',
            'is_valid': True,
            'license': None,
            'trial': trial,
            'features': [],
            'max_branches': 0,
            'message': f'Trial just started — {trial.days_remaining()} days remaining',
        }

    except Exception:
        return {
            'mode': 'error',
            'is_valid': False,
            'license': None,
            'trial': None,
            'features': [],
            'max_branches': 0,
            'message': 'License validation unavailable',
        }


class LicenseValidator:
    """
    Lightweight 4-state license validator.

    Delegates to resolve_license() for all state evaluation.
    Maintains instance-level caching for single-request reuse.
    """

    def __init__(self):
        self.crypto = LicenseCrypto()
        self.fingerprint_engine = DeviceFingerprintEngine()
        self._cached_state = None

    def validate(self) -> str:
        """Evaluate and return current state string. Cached per instance."""
        if self._cached_state is not None:
            return self._cached_state
        resolved = resolve_license()
        self._cached_state = resolved['mode']
        return self._cached_state

    # ── Helpers ──────────────────────────────────────────────────

    def _find_valid_license(self) -> Optional[DeviceLicense]:
        resolved = resolve_license()
        return resolved.get('license')

    def _find_active_trial(self) -> Optional[TrialSession]:
        resolved = resolve_license()
        return resolved.get('trial')

    def _has_expired_trial(self) -> bool:
        resolved = resolve_license()
        return resolved['mode'] == 'limited'

    # ── Info ─────────────────────────────────────────────────────

    def get_info(self) -> Dict[str, Any]:
        """Get detailed state information for API responses."""
        resolved = resolve_license()
        state = resolved['mode']
        base = {
            "mode": state,
            "timestamp": timezone.now().isoformat(),
        }

        if state == "dev":
            base.update({
                "is_valid": True,
                "message": resolved['message'],
            })
        elif state == "trial":
            trial = resolved['trial']
            if trial:
                base.update({
                    "is_valid": True,
                    "message": resolved['message'],
                    "days_remaining": trial.days_remaining(),
                    "expires_at": trial.expires_at.isoformat(),
                    "started_at": trial.started_at.isoformat(),
                    "access_count": trial.access_count,
                })
            else:
                base.update({
                    "is_valid": True,
                    "message": "Trial just started",
                    "days_remaining": 10,
                })
        elif state == "limited":
            base.update({
                "is_valid": False,
                "message": resolved['message'],
                "restricted": True,
            })
        elif state == "licensed":
            lic = resolved['license']
            if lic:
                base.update({
                    "is_valid": True,
                    "license_key": lic.license_key,
                    "issued_to": lic.issued_to,
                    "company_name": lic.company_name,
                    "license_type": lic.license_type,
                    "features": lic.features,
                    "max_branches": lic.max_branches,
                    "expires_date": lic.expires_date.isoformat() if lic.expires_date else None,
                    "message": resolved['message'],
                })
            else:
                base.update({
                    "is_valid": True,
                    "message": "License is valid",
                })

        return base

    # ── Activation ──────────────────────────────────────────────

    def generate_activation_request(self) -> str:
        fingerprint = self.fingerprint_engine.get_fingerprint()
        return self.crypto.generate_activation_request(fingerprint)

    def import_license(self, lic_filepath: str) -> Tuple[bool, str]:
        data = self.crypto.import_license_file(lic_filepath)
        if data is None:
            return False, "License file is invalid or signature verification failed"

        stored_fp = data.get("device_fingerprint", {})
        if not self.fingerprint_engine.fingerprint_matches(stored_fp):
            return False, "License file does not match this device"

        device_fp = self.fingerprint_engine.get_fingerprint()
        device_id = device_fp["device_id"]
        license_key = data.get("license_key", f"OFFLINE-{device_id[:16]}")

        expires_date = data.get("expires_date")
        if isinstance(expires_date, str) and len(expires_date) >= 10:
            from datetime import datetime as dt
            expires_date = dt.strptime(expires_date[:10], "%Y-%m-%d").date()

        lic, created = DeviceLicense.objects.get_or_create(
            device_id=device_id,
            defaults={
                "license_key": license_key,
                "device_fingerprint": device_fp,
                "is_active": True,
                "issued_to": data.get("issued_to", data.get("customer_name", "")),
                "company_name": data.get("company_name", ""),
                "license_type": data.get("license_type", "annual"),
                "features": data.get("features", []),
                "max_branches": data.get("max_branches", 1),
                "expires_date": expires_date,
                "signed_license": data.get("signed_license", ""),
            }
        )
        if not created:
            lic.license_key = license_key
            lic.is_active = True
            lic.company_name = data.get("company_name", lic.company_name)
            lic.license_type = data.get("license_type", lic.license_type)
            lic.features = data.get("features", lic.features)
            lic.max_branches = data.get("max_branches", lic.max_branches)
            if expires_date:
                lic.expires_date = expires_date
            lic.save()

        return True, "License activated successfully"

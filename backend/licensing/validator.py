import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from django.utils import timezone

from .crypto import LicenseCrypto
from .fingerprint import DeviceFingerprintEngine
from .models import DeviceLicense, TrialSession


VALID_MODES = ("dev", "trial", "limited", "licensed")


def is_dev_mode() -> bool:
    """Check if system is in development mode (all checks bypassed)."""
    from django.conf import settings
    return (
        settings.DEBUG
        or os.environ.get('ENV') == 'DEV'
        or os.environ.get('PHARMACY_ERP_LICENSE_BYPASS', '').lower() in ('true', '1', 'yes')
    )


class LicenseValidator:
    """
    Lightweight 4-state license validator.
    
    States:
      dev      — Development mode, all checks bypassed
      trial    — 10-day auto trial active
      limited  — Trial expired, only license/settings screens accessible
      licensed — Valid purchased license file imported
    """

    def __init__(self):
        self.crypto = LicenseCrypto()
        self.fingerprint_engine = DeviceFingerprintEngine()

    def validate(self) -> str:
        """Evaluate and return current state string."""
        if is_dev_mode():
            return "dev"

        # Check for a valid purchased license first (takes priority)
        licensed = self._find_valid_license()
        if licensed:
            return "licensed"

        # Check for an active trial
        trial = self._find_active_trial()
        if trial:
            return "trial"

        # Check for expired trial
        if self._has_expired_trial():
            return "limited"

        # Auto-create trial on first run
        fingerprint = self.fingerprint_engine.get_fingerprint()
        device_id = fingerprint["device_id"]
        TrialSession.get_or_create_for_device(device_id, fingerprint)
        return "trial"

    # ── Helpers ──────────────────────────────────────────────────

    def _find_valid_license(self) -> Optional[DeviceLicense]:
        fingerprint = self.fingerprint_engine.get_fingerprint()
        device_id = fingerprint["device_id"]
        try:
            return DeviceLicense.objects.get(device_id=device_id, is_active=True)
        except DeviceLicense.DoesNotExist:
            for lic in DeviceLicense.objects.filter(is_active=True):
                if lic.matches_device(fingerprint):
                    return lic
        return None

    def _find_active_trial(self) -> Optional[TrialSession]:
        fingerprint = self.fingerprint_engine.get_fingerprint()
        device_id = fingerprint["device_id"]
        trial = TrialSession.get_active_trial(device_id)
        if trial:
            trial.access_count += 1
            trial.save(update_fields=["access_count"])
        return trial

    def _has_expired_trial(self) -> bool:
        fingerprint = self.fingerprint_engine.get_fingerprint()
        device_id = fingerprint["device_id"]
        trial = TrialSession.objects.filter(device_id=device_id).first()
        return bool(trial and trial.is_expired())

    # ── Info ─────────────────────────────────────────────────────

    def get_info(self) -> Dict[str, Any]:
        """Get detailed state information for API responses."""
        state = self.validate()
        base = {
            "mode": state,
            "timestamp": timezone.now().isoformat(),
        }

        if state == "dev":
            base.update({
                "is_valid": True,
                "message": "Development mode — all license checks bypassed",
            })
        elif state == "trial":
            trial = self._find_active_trial()
            if trial:
                base.update({
                    "is_valid": True,
                    "message": f"Trial active — {trial.days_remaining()} days remaining",
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
                "message": "Trial period has expired. Please activate a license.",
                "restricted": True,
            })
        elif state == "licensed":
            lic = self._find_valid_license()
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
                    "message": "License is valid",
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

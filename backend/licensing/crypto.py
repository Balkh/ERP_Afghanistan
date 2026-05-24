import json
import os
import base64
from datetime import datetime
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from .rsa import rsa_manager


LICENSE_FILE_MAGIC = b"PHARMACY_ERP_LIC_v1"


class LicenseCrypto:
    """
    Lightweight license crypto operations.
    - .lic file creation & verification
    - activation_request.json generation
    """

    def __init__(self):
        self.public_key = None
        self._load_public_key()

    def _load_public_key(self):
        pub_path = os.path.join(os.path.dirname(__file__), 'keys', 'public_key.pem')
        if os.path.exists(pub_path):
            with open(pub_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read())

    @property
    def has_public_key(self) -> bool:
        return self.public_key is not None

    def verify_signature(self, data: str, signature_b64: str) -> bool:
        if not self.has_public_key:
            return False
        try:
            sig = base64.b64decode(signature_b64)
            self.public_key.verify(
                sig, data.encode('utf-8'),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except (InvalidSignature, Exception):
            return False

    def verify_license_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Verify and parse a .lic file. Returns dict on success, None on failure."""
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'rb') as f:
                if f.read(len(LICENSE_FILE_MAGIC)) != LICENSE_FILE_MAGIC:
                    return None
                payload_len = int.from_bytes(f.read(4), 'big')
                payload = f.read(payload_len).decode('utf-8')
                sig = f.read().decode('utf-8').strip()
            return json.loads(payload) if self.verify_signature(payload, sig) else None
        except Exception:
            return None

    def create_license_file(self, license_data: Dict[str, Any], output_path: str) -> bool:
        """Create a signed .lic file (server-side, requires private key)."""
        payload = json.dumps(license_data, separators=(',', ':'))
        sig = rsa_manager.sign_data(payload)
        with open(output_path, 'wb') as f:
            f.write(LICENSE_FILE_MAGIC)
            pb = payload.encode('utf-8')
            f.write(len(pb).to_bytes(4, 'big'))
            f.write(pb)
            f.write(sig.encode('utf-8'))
            f.write(b'\n')
        return True

    def generate_activation_request(self, fingerprint: Dict[str, str],
                                     target_dir: str = None) -> str:
        """Generate activation_request.json for offline activation."""
        request = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "device_fingerprint": {
                "device_id": fingerprint.get("device_id", ""),
                "fingerprint_hash": fingerprint.get("fingerprint_hash", ""),
                "cpu_hash": fingerprint.get("cpu_hash", ""),
                "disk_hash": fingerprint.get("disk_hash", ""),
                "os_machine_id": fingerprint.get("os_machine_id", ""),
                "installation_uuid": fingerprint.get("installation_uuid", ""),
            },
        }
        if target_dir is None:
            target_dir = os.path.join(os.path.dirname(__file__), 'keys')
        os.makedirs(target_dir, exist_ok=True)
        out_path = os.path.join(target_dir, "activation_request.json")
        with open(out_path, 'w') as f:
            json.dump(request, f, indent=2)
        return out_path

    def import_license_file(self, lic_filepath: str, target_dir: str = None) -> Optional[Dict[str, Any]]:
        """Import and verify a .lic file, copy to canonical location."""
        data = self.verify_license_file(lic_filepath)
        if data is None:
            return None
        if target_dir is None:
            target_dir = os.path.join(os.path.dirname(__file__), 'keys')
        os.makedirs(target_dir, exist_ok=True)
        import shutil
        shutil.copy2(lic_filepath, os.path.join(target_dir, "license.lic"))
        return data

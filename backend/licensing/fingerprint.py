import hashlib
import os
import platform
import uuid
from typing import Dict, Optional

from licensing.utils import get_cpu_id, get_mac_address, get_disk_serial


INSTALLATION_UUID_FILE = ".pharmacy_erp_install_id"


class DeviceFingerprintEngine:
    """
    5-factor device fingerprint engine.
    Combines: CPU hash, disk hash, MAC hash, OS machine ID, installation UUID.
    Stable across restarts, tolerates minor OS changes.
    """

    def __init__(self, install_dir: Optional[str] = None):
        self.install_dir = install_dir or os.path.expanduser("~")

    def get_cpu_hash(self) -> str:
        return hashlib.sha256(get_cpu_id().encode('utf-8')).hexdigest()[:16]

    def get_disk_hash(self) -> str:
        return hashlib.sha256(get_disk_serial().encode('utf-8')).hexdigest()[:16]

    def get_mac_hash(self) -> str:
        return hashlib.sha256(get_mac_address().encode('utf-8')).hexdigest()[:16]

    def get_os_machine_id(self) -> str:
        if platform.system() == "Linux":
            for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                if os.path.exists(p):
                    try:
                        with open(p) as f:
                            return f.read().strip()
                    except Exception:
                        pass
        elif platform.system() == "Windows":
            try:
                import winreg
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\Microsoft\Cryptography")
                guid, _ = winreg.QueryValueEx(k, "MachineGuid")
                winreg.CloseKey(k)
                return guid.strip()
            except Exception:
                pass
        elif platform.system() == "Darwin":
            try:
                import subprocess
                r = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                                   capture_output=True, text=True, check=True)
                for line in r.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        return line.split('"')[3]
            except Exception:
                pass
        return platform.node()

    def get_installation_uuid(self) -> str:
        uuid_path = os.path.join(self.install_dir, INSTALLATION_UUID_FILE)
        if os.path.exists(uuid_path):
            try:
                val = open(uuid_path).read().strip()
                if val:
                    return val
            except Exception:
                pass
        install_id = str(uuid.uuid4())
        try:
            with open(uuid_path, 'w') as f:
                f.write(install_id)
        except Exception:
            pass
        return install_id

    def get_fingerprint(self) -> Dict[str, str]:
        cpu_hash = self.get_cpu_hash()
        disk_hash = self.get_disk_hash()
        mac_hash = self.get_mac_hash()
        os_machine_id = self.get_os_machine_id()
        install_uuid = self.get_installation_uuid()

        raw = f"{cpu_hash}|{disk_hash}|{mac_hash}|{os_machine_id}|{install_uuid}"
        fingerprint_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()

        legacy_raw = f"{cpu_hash}|{mac_hash}|{disk_hash}"
        device_id = hashlib.sha256(legacy_raw.encode('utf-8')).hexdigest()

        return {
            "cpu_hash": cpu_hash,
            "disk_hash": disk_hash,
            "mac_hash": mac_hash,
            "os_machine_id": os_machine_id,
            "installation_uuid": install_uuid,
            "fingerprint_hash": fingerprint_hash,
            "device_id": device_id,
            "cpu_id": get_cpu_id(),
            "mac_address": get_mac_address(),
            "disk_serial": get_disk_serial(),
        }

    def fingerprint_matches(self, stored_fp: Dict[str, str]) -> bool:
        """Check device fingerprint match (exact hash comparison)."""
        current = self.get_fingerprint()
        return current.get("fingerprint_hash") == stored_fp.get("fingerprint_hash")

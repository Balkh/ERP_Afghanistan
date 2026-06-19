import platform
import uuid
import hashlib
import os
import subprocess
import re
from typing import Optional


def get_cpu_id() -> str:
    """
    Get the CPU ID or processor information.
    Returns a string identifier for the CPU.
    """
    try:
        if platform.system() == "Windows":
            # Try to get CPU ID from Windows Registry
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_id, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                winreg.CloseKey(key)
                if cpu_id:
                    return cpu_id.strip()
            except ImportError:
                pass
            except FileNotFoundError:
                pass

            # Fallback to wmi if available
            try:
                import wmi
                c = wmi.WMI()
                for cpu in c.Win32_Processor():
                    return cpu.ProcessorId.strip()
            except ImportError:
                pass

        elif platform.system() == "Linux":
            # Try to read from /proc/cpuinfo
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
                        elif "Hardware" in line:
                            return line.split(":")[1].strip()
            except FileNotFoundError:
                pass

        elif platform.system() == "Darwin":  # macOS
            try:
                # Use sysctl to get CPU brand string
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        # Fallback to platform.processor()
        processor = platform.processor()
        if processor:
            return processor.strip()

        # Last resort: use machine and processor from platform
        return f"{platform.machine()}_{platform.processor()}"

    except Exception as e:
        # If all else fails, return a placeholder based on platform
        return f"unknown_cpu_{platform.system()}_{platform.machine()}"


def get_mac_address() -> str:
    """
    Get the MAC address of the primary network interface.
    Returns a string in the format 'XX:XX:XX:XX:XX:XX'.
    """
    try:
        # Method 1: Using uuid.getnode()
        mac = uuid.getnode()
        if mac:
            # Format as XX:XX:XX:XX:XX:XX
            mac_str = ':'.join(['{:02x}'.format((mac >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1])
            # Check if it's not a multicast or locally administered address (optional)
            # But we'll just return it
            return mac_str.upper()

        # Method 2: Try to get from platform (less reliable)
        # Note: platform.machine() doesn't give MAC
    except Exception:
        pass

    try:
        # Method 3: Platform-specific commands
        if platform.system() == "Windows":
            # Use getmac command
            result = subprocess.run(
                ["getmac", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                check=True
            )
            # Extract MAC address from output like: "00-1A-2B-3C-4D-5E \t\t\"Connection Name\""
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    # Take the first MAC address found
                    mac_part = line.split(',')[0].strip().replace('-', ':')
                    if re.match(r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', mac_part):
                        return mac_part.upper()
        elif platform.system() == "Linux":
            # Try to read from /sys/class/net/*/address
            interfaces = ['eth0', 'ens5', 'wlan0']  # Common interface names
            for iface in interfaces:
                path = f'/sys/class/net/{iface}/address'
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        mac = f.read().strip()
                        if mac:
                            return mac.upper()
            # Fallback: list all interfaces
            if os.path.exists('/sys/class/net'):
                for iface in os.listdir('/sys/class/net'):
                    if iface != 'lo':
                        path = f'/sys/class/net/{iface}/address'
                        if os.path.exists(path):
                            with open(path, 'r') as f:
                                mac = f.read().strip()
                                if mac:
                                    return mac.upper()
        elif platform.system() == "Darwin":
            # Use ifconfig or ipconfig getifaddr en0 (for IP, not MAC) - we need MAC
            # Use: ifconfig en0 | grep ether
            try:
                result = subprocess.run(
                    ["ifconfig", "en0"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                for line in result.stdout.split('\n'):
                    if 'ether' in line:
                        mac = line.split()[1]
                        return mac.upper()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

    except Exception:
        pass

    # Fallback: return a placeholder
    return "00:00:00:00:00:00"


def get_disk_serial() -> str:
    """
    Get the disk serial number of the primary disk.
    Returns a string identifier for the disk.
    """
    try:
        if platform.system() == "Windows":
            # Try to use wmi
            try:
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    if disk.SerialNumber:
                        return disk.SerialNumber.strip()
            except ImportError:
                pass

            # Fallback to wmic command
            try:
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "SerialNumber"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                lines = result.stdout.strip().split('\n')
                # Skip header
                for line in lines[1:]:
                    if line.strip():
                        return line.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        elif platform.system() == "Linux":
            # Try to read from /sys/block/*/device/serial
            try:
                # Get the first non-virtual block device (excluding loop, ram, etc.)
                block_devices = [d for d in os.listdir('/sys/block') if not d.startswith(('loop', 'ram'))]
                for device in block_devices:
                    serial_path = f'/sys/block/{device}/device/serial'
                    if os.path.exists(serial_path):
                        with open(serial_path, 'r') as f:
                            serial = f.read().strip()
                            if serial:
                                return serial
            except FileNotFoundError:
                pass

            # Fallback: use hdparm (requires root, not ideal) or look at /dev/disk/by-id
            try:
                # Look for disks by-id
                if os.path.exists('/dev/disk/by-id'):
                    for disk_id in os.listdir('/dev/disk/by-id'):
                        if 'ata' in disk_id or 'scsi' in disk_id:
                            # Read the link target to get the device name
                            link_path = f'/dev/disk/by-id/{disk_id}'
                            if os.path.islink(link_path):
                                # We can use the disk_id as a serial-like identifier
                                return disk_id
            except FileNotFoundError:
                pass

        elif platform.system() == "Darwin":
            # Use system_profiler or diskutil
            try:
                result = subprocess.run(
                    ["diskutil", "info", "/"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                for line in result.stdout.split('\n'):
                    if 'Device Identifier' in line:
                        # We want the serial number, not the identifier
                        continue
                    if 'Serial Number' in line:
                        return line.split(':')[1].strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

    except Exception:
        pass

    # Fallback: use the system's machine ID or generate a placeholder
    try:
        # Try to get machine-id from /etc/machine-id (Linux) or use platform-specific
        if platform.system() == "Linux" and os.path.exists('/etc/machine-id'):
            with open('/etc/machine-id', 'r') as f:
                return f.read().strip()
    except Exception:
        pass

    # Last resort: combine platform info
    return f"{platform.node()}_{platform.system()}_{platform.machine()}"


def generate_device_id(cpu_id: str = None, mac_addr: str = None, disk_serial: str = None) -> str:
    """
    Generate a unique device ID based on hardware fingerprint.
    Combines CPU ID, MAC address, and Disk serial, then hashes them.
    Returns a hexadecimal string (SHA256).
    
    Args:
        cpu_id: Optional CPU ID (if None, will be fetched)
        mac_addr: Optional MAC address (if None, will be fetched)
        disk_serial: Optional disk serial (if None, will be fetched)
    """
    # Get values if not provided
    if cpu_id is None:
        cpu_id = get_cpu_id()
    if mac_addr is None:
        mac_addr = get_mac_address()
    if disk_serial is None:
        disk_serial = get_disk_serial()

    # Combine the identifiers
    combined = f"{cpu_id}|{mac_addr}|{disk_serial}"
    
    # Create a hash (SHA256) for a fixed-length, consistent ID
    hash_object = hashlib.sha256(combined.encode('utf-8'))
    device_id = hash_object.hexdigest()
    
    return device_id


def generate_device_id_from_fingerprint(fingerprint: dict) -> str:
    """
    Generate a device ID from a fingerprint dictionary.
    
    Args:
        fingerprint: Dictionary with cpu_id, mac_address, disk_serial keys
        
    Returns:
        str: Device ID (hashed fingerprint)
    """
    return generate_device_id(
        fingerprint.get('cpu_id'),
        fingerprint.get('mac_address'),
        fingerprint.get('disk_serial')
    )


def get_device_fingerprint() -> dict:
    """
    Get the raw device fingerprint components.
    Returns a dictionary with the raw components.
    """
    return {
        'cpu_id': get_cpu_id(),
        'mac_address': get_mac_address(),
        'disk_serial': get_disk_serial(),
        'device_id': generate_device_id()
    }


if __name__ == "__main__":
    # For testing
    print("Device Fingerprint:")
    print(f"  CPU ID: {get_cpu_id()}")
    print(f"  MAC Address: {get_mac_address()}")
    print(f"  Disk Serial: {get_disk_serial()}")
    print(f"  Device ID: {generate_device_id()}")
    
    print("\nFull fingerprint:")
    import json
    print(json.dumps(get_device_fingerprint(), indent=2))
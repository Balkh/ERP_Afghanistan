"""
Hardware identification utilities for device fingerprinting.
Provides functions to collect hardware identifiers for generating a unique device ID.
"""

import subprocess
import re
import uuid
import platform


def get_cpu_id() -> str:
    """
    Get CPU ID/Processor ID.
    Returns empty string if unable to retrieve.
    """
    try:
        if platform.system() == "Windows":
            # Use wmic to get ProcessorId
            output = subprocess.check_output(
                "wmic cpu get ProcessorId", 
                shell=True, 
                stdin=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore')
            # Extract the ProcessorId value (skip header line)
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            if len(lines) >= 2:
                return lines[1]  # First data line after header
        elif platform.system() == "Linux":
            # Try to read from /proc/cpuinfo
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'serial' in line.lower():
                            return line.split(':')[1].strip()
            except FileNotFoundError:
                pass
        # Add other platforms if needed (macOS, etc.)
        return ""
    except Exception:
        return ""


def get_mac_address() -> str:
    """
    Get MAC address of the primary network interface.
    Returns formatted MAC address (xx:xx:xx:xx:xx:xx) or empty string if unable to retrieve.
    """
    try:
        # Get MAC address using uuid.getnode()
        mac_num = uuid.getnode()
        mac = ':'.join(['{:02x}'.format((mac_num >> i) & 0xff) 
                       for i in range(0, 8*6, 8)][::-1])
        return mac.upper()
    except Exception:
        return ""


def get_disk_serial() -> str:
    """
    Get disk serial number (primary boot drive).
    Returns empty string if unable to retrieve.
    """
    try:
        if platform.system() == "Windows":
            # Use wmic to get serial number of first disk drive
            output = subprocess.check_output(
                "wmic diskdrive get SerialNumber", 
                shell=True, 
                stdin=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore')
            # Extract the SerialNumber value (skip header line)
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            if len(lines) >= 2:
                # Take first non-empty line after header (first drive)
                for line in lines[1:]:
                    if line:
                        return line
        elif platform.system() == "Linux":
            # Try to get serial from first SATA disk
            try:
                output = subprocess.check_output(
                    ["hdparm", "-I", "/dev/sda"], 
                    stderr=subprocess.DEVNULL
                ).decode('utf-8', errors='ignore')
                match = re.search(r'Serial Number\s*:\s*(.+)', output)
                if match:
                    return match.group(1).strip()
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass
        return ""
    except Exception:
        return ""
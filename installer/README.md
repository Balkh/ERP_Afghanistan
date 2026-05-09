# Pharmacy ERP - Installer System Documentation

## Overview

This document describes the Windows installer system for Pharmacy ERP, including installation workflows, setup scripts, and configuration options.

## Installer Options

### Option 1: NSIS Installer (Recommended)

Creates a professional Windows installer executable.

**Requirements:**
- NSIS (Nullsoft Scriptable Install System) installed
- Application built with PyInstaller (dist/PharmacyERP/ exists)

**Build Process:**
```batch
installer\build_installer.bat
```

**Output:**
- `PharmacyERP-Setup-1.0.0.exe`

### Option 2: Python Installer

Alternative installer using Python (no NSIS required).

**Requirements:**
- Python 3.8+
- Administrator privileges
- Application built with PyInstaller

**Build Process:**
```bash
python installer\python_installer.py
```

## Installation Workflow

### 1. Pre-Installation Checks

The installer performs the following checks before installation:

| Check | Description | Action if Failed |
|-------|-------------|------------------|
| OS Version | Windows 7 or higher | Abort installation |
| Disk Space | 500 MB minimum | Abort installation |
| Admin Rights | Administrator privileges | Abort installation |
| Port Check | Port 8000 availability | Warning only |
| Existing Install | Previous version detection | Prompt user |

### 2. Installation Steps

1. **Create Directories**
   - Install directory: `C:\Program Files\PharmacyERP\`
   - Data directories in `%APPDATA%\PharmacyERP\`

2. **Copy Files**
   - All application files from build directory
   - Executables, libraries, resources

3. **Create Shortcuts**
   - Start Menu: `Start Menu\Programs\PharmacyERP\`
   - Desktop: `Desktop\Pharmacy ERP.lnk`
   - Uninstall shortcut

4. **Write Registry**
   - Application information
   - Uninstall entries
   - First-run flag

5. **Create Uninstaller**
   - Uninstaller script in install directory
   - Registry uninstall entries

6. **Set First-Run Flag**
   - Marks application for first-run setup

### 3. Post-Installation

After installation completes:

1. User can launch Pharmacy ERP from:
   - Start Menu
   - Desktop shortcut
   - Installation directory

2. First-run setup wizard will appear:
   - Database initialization
   - Admin user creation
   - Default data seeding
   - Configuration setup

## First-Run Setup

### Command-Line Setup

```bash
python installer\first_run_setup.py --username admin --password admin123 --email admin@pharmacyerp.com
```

### GUI Setup

```bash
python installer\first_run_setup.py --gui
```

### Setup Steps

1. **Database Initialization**
   - Run Django migrations
   - Create database tables
   - Set up database schema

2. **Admin User Creation**
   - Create superuser account
   - Set password (hashed)
   - Set email and details

3. **Default Data Seeding**
   - Chart of Accounts (37 accounts)
   - Payment methods (6 methods)
   - Payment accounts (5 accounts)

4. **Configuration Creation**
   - Save app configuration
   - Set default settings
   - Create config files

5. **Mark Setup Complete**
   - Create setup completion flag
   - Remove first-run flag

## Directory Structure

### Installation Directory

```
C:\Program Files\PharmacyERP\
├── PharmacyERP.exe          # Main executable
├── uninstall.bat            # Uninstaller script
├── README.txt               # User guide
└── [application files]      # Libraries, resources
```

### Application Data

```
%APPDATA%\PharmacyERP\
├── data\                    # Application data
│   └── pharmacy_erp.db     # SQLite database
├── logs\                    # Log files
│   ├── pharmacy_erp.log    # General logs
│   └── error.log           # Error logs
├── config\                  # Configuration files
│   ├── config.json         # App configuration
│   └── backend_port.txt    # Backend port
├── backups\                 # Backup files
├── media\                   # Media uploads
└── temp\                    # Temporary files
```

## Uninstallation

### Using Windows Settings
1. Open Settings > Apps > Apps & features
2. Find "Pharmacy ERP"
3. Click Uninstall

### Using Uninstaller Script
```batch
C:\Program Files\PharmacyERP\uninstall.bat
```

### Uninstall Options

| Option | Description |
|--------|-------------|
| Remove application files | Removes all installed files |
| Remove shortcuts | Removes Start Menu and Desktop shortcuts |
| Remove registry entries | Removes registry keys |
| Remove user data | Optional: removes database, logs, backups |

**Note:** User data is preserved by default during uninstallation.

## Configuration File

Location: `%APPDATA%\PharmacyERP\config\config.json`

```json
{
  "version": "1.0.0",
  "setup_date": "2026-04-30T...",
  "app_name": "Pharmacy ERP",
  "company_name": "Pharmacy ERP Solutions",
  "admin_username": "admin",
  "admin_email": "admin@pharmacyerp.com",
  "language": "en",
  "currency": "AFN",
  "timezone": "UTC",
  "database_path": "%APPDATA%\\PharmacyERP\\data\\pharmacy_erp.db",
  "log_level": "INFO",
  "backup_enabled": true,
  "backup_interval": "daily"
}
```

## Troubleshooting

### Installation Fails

1. **Administrator Rights Required**
   - Right-click installer > "Run as administrator"

2. **Insufficient Disk Space**
   - Free up at least 500 MB of disk space

3. **NSIS Not Found (for NSIS installer)**
   - Download and install NSIS from http://nsis.sourceforge.net/Download

4. **Build Directory Missing**
   - Run `python build_exe.py` first

### First-Run Setup Fails

1. **Database Locked**
   - Ensure no other instances are running
   - Delete `%APPDATA%\PharmacyERP\data\pharmacy_erp.db` and retry

2. **Migration Errors**
   - Check logs in `%APPDATA%\PharmacyERP\logs\`
   - Verify Python environment has all dependencies

### Post-Installation Issues

1. **Application Won't Start**
   - Check logs in `%APPDATA%\PharmacyERP\logs\`
   - Verify port 8000 is available
   - Try running as administrator

2. **Missing Features**
   - Re-run first-run setup: `python installer\first_run_setup.py`

## Registry Keys

| Key | Value | Description |
|-----|-------|-------------|
| `HKLM\Software\PharmacyERP\InstallLocation` | String | Installation directory |
| `HKLM\Software\PharmacyERP\Version` | String | Application version |
| `HKLM\Software\PharmacyERP\Publisher` | String | Publisher name |
| `HKLM\Software\PharmacyERP\FirstRun` | DWORD | First-run flag (1=yes) |

## Customization

### Custom Install Location

Modify `installer\installer_config.py`:
```python
'directories': {
    'install_dir': '{CUSTOM_PATH}\\PharmacyERP',
    ...
}
```

### Custom Shortcuts

Modify shortcut paths in configuration:
```python
'shortcuts': {
    'start_menu': '{CUSTOM_PATH}\\Pharmacy ERP.lnk',
    ...
}
```

### Pre-Installation Checks

Add custom checks in configuration:
```python
'pre_install_checks': [
    {
        'type': 'custom_check',
        'condition': '...',
        'message': '...',
    },
]
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-30 | Initial release |

## Support

For installation support:
- Check documentation: `PACKAGING.md`
- Check logs: `%APPDATA%\PharmacyERP\logs\`
- Contact: support@pharmacyerp.example.com
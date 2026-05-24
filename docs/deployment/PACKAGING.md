# Pharmacy ERP - Packaging Documentation

## Overview

This document describes the PyInstaller packaging process for the Pharmacy ERP application, including build configuration, executable structure, and deployment guidelines.

## Prerequisites

- Python 3.8 or higher
- PyInstaller 6.0 or higher
- All dependencies listed in `requirements.txt`

## Build Process

### Automated Build

Run the build script:

```bash
python build_exe.py
```

Or use the batch file:

```batch
build.bat
```

### Manual Build

```bash
pyinstaller pharmacy_erp.spec
```

## Configuration Files

### `pharmacy_erp.spec`

The PyInstaller specification file containing:
- Entry point configuration
- Hidden imports
- Data files inclusion
- Excluded modules
- Executable settings

### `main_executable.py`

The main entry point for the packaged application that:
- Sets up the environment
- Initializes Django backend
- Runs database migrations
- Starts backend server
- Launches PySide6 frontend

### `startup_config.py`

Comprehensive startup manager that handles:
- Environment initialization
- Database setup and migration
- Port allocation for backend server
- Process management
- Logging configuration

### `frontend/config/production_config.py`

Production configuration utilities:
- Path resolution for packaged apps
- Data directory management
- Database path handling
- Configuration storage
- Log directory setup
- Backup directory setup

## Directory Structure

### Development

```
Pharmacy_ERP/
├── backend/                 # Django backend
├── frontend/                # PySide6 frontend
│   ├── api/                # API client
│   ├── config/             # Configuration
│   ├── license/            # Licensing
│   ├── security/           # Security modules
│   ├── theme/              # UI themes
│   ├── ui/                 # User interface
│   ├── utils/              # Utilities
│   └── main.py             # Frontend entry point
├── main_executable.py      # Packaged entry point
├── startup_config.py       # Startup manager
└── pharmacy_erp.spec       # PyInstaller spec
```

### Packaged Application

```
PharmacyERP/
├── PharmacyERP.exe         # Main executable
├── data/                   # Application data
│   ├── pharmacy_erp.db    # SQLite database
│   ├── media/             # Media files
│   └── temp/              # Temporary files
├── logs/                   # Application logs
├── config/                 # Configuration files
├── backups/                # Backup files
└── README.txt             # User guide
```

## Production Path Handling

The application uses different paths for development and production:

### Development Paths
- Data: `Pharmacy_ERP/data/`
- Logs: `Pharmacy_ERP/logs/`
- Config: `Pharmacy_ERP/config/`
- Database: `Pharmacy_ERP/data/pharmacy_erp.db`

### Production Paths (Packaged)
- Data: `%APPDATA%\PharmacyERP\data\`
- Logs: `%APPDATA%\PharmacyERP\logs\`
- Config: `%APPDATA%\PharmacyERP\config\`
- Database: `%APPDATA%\PharmacyERP\data\pharmacy_erp.db`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PHARMACY_ERP_DEBUG` | Enable debug mode | False |
| `PHARMACY_ERP_SECRET_KEY` | Django secret key | Generated |
| `PHARMACY_ERP_DB` | Database filename | pharmacy_erp.db |
| `PHARMACY_ERP_ALLOWED_HOSTS` | Allowed hosts | localhost,127.0.0.1 |
| `PHARMACY_ERP_BACKEND_URL` | Backend URL | http://127.0.0.1:{port} |

## Database Management

### Default Admin User
- Username: `admin`
- Password: `admin123`
- **Important**: Change password immediately after first login

### Database Location
- Development: `backend/db.sqlite3`
- Production: `%APPDATA%\PharmacyERP\data\pharmacy_erp.db`

## Logging

Log files are stored in:
- Development: `Pharmacy_ERP/logs/`
- Production: `%APPDATA%\PharmacyERP\logs\`

Log files include:
- `pharmacy_erp.log` - General application logs
- `error.log` - Error-specific logs
- `startup.log` - Startup process logs
- `django.log` - Django framework logs

## Troubleshooting

### Common Issues

1. **Port in Use Error**
   - Backend server cannot start on port 8000
   - Solution: Application automatically finds available port

2. **Database Locked**
   - Multiple instances trying to access database
   - Solution: Close all instances and restart

3. **Missing Dependencies**
   - PyInstaller didn't include all modules
   - Solution: Add to hiddenimports in spec file

4. **Permission Errors**
   - Cannot write to data directory
   - Solution: Run as administrator or check folder permissions

### Log Analysis

Check log files for error details:
```
%APPDATA%\PharmacyERP\logs\error.log
```

## Security Considerations

- Secret key should be changed for production deployments
- Database file should be encrypted for sensitive data
- Log files may contain sensitive information
- Admin credentials should be changed immediately
- Firewall rules may be needed for backend server

## Distribution

### Creating Installer

After building the executable, use the Phase 6B installer system to create a Windows installer package.

### Distribution Checklist

- [ ] Build executable successfully
- [ ] Test on clean Windows installation
- [ ] Verify all features work
- [ ] Check log files for errors
- [ ] Test database initialization
- [ ] Verify backup functionality
- [ ] Test license validation
- [ ] Create installer package
- [ ] Document installation steps
- [ ] Prepare user guide

## Version Information

- Application Version: 1.0.0
- Build Date: [Auto-generated]
- Python Version: 3.8+
- PyInstaller Version: 6.0+
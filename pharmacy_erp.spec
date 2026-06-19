# -*- mode: python ; coding: utf-8 -*-
"""
Pharmacy ERP PyInstaller Specification File
Complete build configuration for Windows executable
"""

import os
from pathlib import Path

block_cipher = None

# Get project root
project_root = Path(__file__).parent

# Analysis
a = Analysis(
    ['main_executable.py'],
    pathex=[
        str(project_root),
        str(project_root / 'backend'),
        str(project_root / 'frontend'),
    ],
    binaries=[],
    datas=[
        # Include backend Django project
        (str(project_root / 'backend'), 'backend'),
        # Include frontend modules
        (str(project_root / 'frontend' / 'api'), 'frontend/api'),
        (str(project_root / 'frontend' / 'license'), 'frontend/license'),
        (str(project_root / 'frontend' / 'security'), 'frontend/security'),
        (str(project_root / 'frontend' / 'theme'), 'frontend/theme'),
        (str(project_root / 'frontend' / 'ui'), 'frontend/ui'),
        (str(project_root / 'frontend' / 'utils'), 'frontend/utils'),
        # Include configuration files
        (str(project_root / 'frontend' / 'config'), 'frontend/config'),
        # Include static files if they exist
        (str(project_root / 'frontend' / 'static'), 'frontend/static') if (project_root / 'frontend' / 'static').exists() else None,
        (str(project_root / 'backend' / 'static'), 'backend/static') if (project_root / 'backend' / 'static').exists() else None,
        (str(project_root / 'backend' / 'templates'), 'backend/templates') if (project_root / 'backend' / 'templates').exists() else None,
    ],
    hiddenimports=[
        # Django framework
        'django',
        'django.core',
        'django.core.handlers',
        'django.core.handlers.wsgi',
        'django.core.management',
        'django.db',
        'django.db.backends',
        'django.db.backends.sqlite3',
        'django.conf',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        
        # Third party
        'rest_framework',
        'corsheaders',
        'django_filters',
        'decouple',
        
        # PySide6
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        
        # Security module
        'security',
        'security.authentication',
        'security.permissions',
        'security.password_utils',
        'security.utils',
        
        # Backend applications
        'accounting',
        'accounting.models',
        'accounting.services',
        'accounting.services.account_hierarchy',
        'accounting.services.journal_engine',
        'accounting.services.financial_reports',
        'accounting.services.report_exporter',
        'accounting.views',
        'accounting.views_account',
        'accounting.serializers',
        'core',
        'core.models',
        'inventory',
        'inventory.models',
        'inventory.views',
        'inventory.views_integration',
        'inventory.service',
        'licensing',
        'licensing.models',
        'licensing.services',
        'licensing.utils',
        'licensing.middleware',
        'payments',
        'payments.models',
        'payments.services',
        'purchases',
        'purchases.models',
        'purchases.views',
        'sales',
        'sales.models',
        'sales.views',
        'reports',
        
        # Additional dependencies
        'pytz',
        'sqlparse',
        'asgiref',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'scipy',
        'pytest',
        'jupyter',
        'notebook',
        'IPython',
        'sphinx',
        'docutils',
        'pygments',
        'jinja2',
        'markupsafe',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Clean datas list (remove None values)
a.datas = [d for d in a.datas if d is not None]

# PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PharmacyERP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'frontend' / 'static' / 'icon.ico') if (project_root / 'frontend' / 'static' / 'icon.ico').exists() else None,
)

# Collection step
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PharmacyERP',
)
"""
Pharmacy ERP - PyInstaller Build Script
Builds a complete executable package for Windows
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def clean_build_dirs():
    """Clean previous build directories"""
    print("Cleaning previous build directories...")
    for dir_name in ['build', 'dist']:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed {dir_name}/")


def run_pyinstaller():
    """Run PyInstaller with appropriate settings"""
    print("Running PyInstaller...")
    
    cmd = [
        'pyinstaller',
        '--name', 'PharmacyERP',
        '--onedir',
        '--windowed',
        '--icon=frontend/static/icon.ico' if os.path.exists('frontend/static/icon.ico') else '',
        '--add-data', f'backend;backend',
        '--add-data', f'frontend/api;frontend/api',
        '--add-data', f'frontend/license;frontend/license',
        '--add-data', f'frontend/security;frontend/security',
        '--add-data', f'frontend/theme;frontend/theme',
        '--add-data', f'frontend/ui;frontend/ui',
        '--add-data', f'frontend/utils;frontend/utils',
        '--hidden-import', 'django',
        '--hidden-import', 'django.core.handlers.wsgi',
        '--hidden-import', 'rest_framework',
        '--hidden-import', 'corsheaders',
        '--hidden-import', 'PySide6.QtCore',
        '--hidden-import', 'PySide6.QtGui',
        '--hidden-import', 'PySide6.QtWidgets',
        '--hidden-import', 'security',
        '--hidden-import', 'security.authentication',
        '--hidden-import', 'security.permissions',
        '--exclude-module', 'tkinter',
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'scipy',
        '--specpath', '.',
        'main_executable.py'
    ]
    
    # Remove empty icon parameter if file doesn't exist
    cmd = [x for x in cmd if x]
    
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Build successful!")
        print(f"Output directory: dist/PharmacyERP/")
        return True
    else:
        print("Build failed!")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return False


def create_post_build_structure():
    """Create proper directory structure in the dist folder"""
    print("Creating post-build directory structure...")
    
    dist_path = Path('dist/PharmacyERP')
    if not dist_path.exists():
        print("Dist directory not found, build may have failed")
        return False
    
    # Create necessary subdirectories
    subdirs = [
        'data',
        'logs',
        'config',
        'backups',
        'media',
    ]
    
    for subdir in subdirs:
        (dist_path / subdir).mkdir(exist_ok=True)
        print(f"Created {dist_path / subdir}/")
    
    # Copy essential files
    essential_files = [
        ('.env.example', '.env.example'),
        ('README.txt', 'README.txt'),
    ]
    
    for src, dest in essential_files:
        if os.path.exists(src):
            shutil.copy2(src, dist_path / dest)
            print(f"Copied {src} to {dist_path / dest}")
    
    # Create README file
    readme_content = """Pharmacy ERP - Installation Guide
================================

1. First Run:
   - Double-click PharmacyERP.exe
   - The application will create necessary directories in %APPDATA%\\PharmacyERP\\
   - Database will be initialized automatically
   
2. Default Admin Account:
   - Username: admin
   - Password: admin123
   - Change this password immediately after first login
   
3. Configuration:
   - Edit the .env file in the application directory for custom settings
   - Database file: %APPDATA%\\PharmacyERP\\data\\pharmacy_erp.db
   - Logs: %APPDATA%\\PharmacyERP\\logs\\
   
4. Troubleshooting:
   - Check logs in %APPDATA%\\PharmacyERP\\logs\\ for errors
   - Ensure no other application is using port 8000
   
For support: [Your support contact information]
"""
    
    with open(dist_path / 'README.txt', 'w') as f:
        f.write(readme_content)
    
    print("Created README.txt")
    return True


def verify_build():
    """Verify the build was successful"""
    print("Verifying build...")
    
    dist_path = Path('dist/PharmacyERP')
    if not dist_path.exists():
        print("Build verification failed: dist/PharmacyERP/ not found")
        return False
    
    # Check for main executable
    exe_path = dist_path / 'PharmacyERP.exe'
    if not exe_path.exists():
        print("Build verification failed: PharmacyERP.exe not found")
        return False
    
    # Check for essential directories
    essential_dirs = ['data', 'logs', 'config']
    for dir_name in essential_dirs:
        if not (dist_path / dir_name).exists():
            print(f"Build verification warning: {dir_name}/ not found")
    
    print("Build verification passed!")
    return True


def main():
    """Main build process"""
    print("=" * 50)
    print("Pharmacy ERP - PyInstaller Build Process")
    print("=" * 50)
    
    # Step 1: Clean previous builds
    clean_build_dirs()
    
    # Step 2: Run PyInstaller
    if not run_pyinstaller():
        print("Build failed during PyInstaller execution")
        sys.exit(1)
    
    # Step 3: Create post-build structure
    if not create_post_build_structure():
        print("Failed to create post-build structure")
        sys.exit(1)
    
    # Step 4: Verify build
    if not verify_build():
        print("Build verification failed")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Build completed successfully!")
    print(f"Executable location: {Path('dist/PharmacyERP/PharmacyERP.exe')}")
    print("Ready for distribution")
    print("=" * 50)


if __name__ == "__main__":
    main()
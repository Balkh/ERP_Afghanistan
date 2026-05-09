"""
Pharmacy ERP Python Installer
Alternative installer using Python (no NSIS required)
Creates Windows installer-like experience
"""
import os
import sys
import shutil
import json
import ctypes
from pathlib import Path
from datetime import datetime


class PythonInstaller:
    """
    Python-based installer for Pharmacy ERP
    """
    
    def __init__(self):
        self.app_name = "Pharmacy ERP"
        self.app_version = "1.0.0"
        self.publisher = "Pharmacy ERP Solutions"
        
        # Directories
        self.program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
        self.install_dir = os.path.join(self.program_files, self.app_name)
        self.app_data = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
        self.data_dir = os.path.join(self.app_data, self.app_name, 'data')
        self.logs_dir = os.path.join(self.app_data, self.app_name, 'logs')
        self.config_dir = os.path.join(self.app_data, self.app_name, 'config')
        self.backups_dir = os.path.join(self.app_data, self.app_name, 'backups')
        
        # Source directory
        self.source_dir = os.path.join(os.path.dirname(__file__), '..', 'dist', 'PharmacyERP')
        
    def is_admin(self):
        """Check if running with administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def require_admin(self):
        """Require administrator privileges"""
        if not self.is_admin():
            print("Error: Administrator privileges are required!")
            print("Please run this installer as Administrator.")
            sys.exit(1)
    
    def check_prerequisites(self):
        """Check installation prerequisites"""
        print("Checking prerequisites...")
        
        # Check Windows version
        if sys.platform != 'win32':
            print("  ✗ Windows is required")
            return False
        print("  ✓ Windows OS detected")
        
        # Check disk space
        try:
            disk_usage = shutil.disk_usage(self.install_dir if os.path.exists(self.install_dir) else 'C:\\')
            free_space_mb = disk_usage.free / (1024 * 1024)
            if free_space_mb < 500:
                print(f"  ✗ Insufficient disk space ({free_space_mb:.0f} MB free, 500 MB required)")
                return False
            print(f"  ✓ Disk space: {free_space_mb:.0f} MB available")
        except:
            print("  ⚠ Could not check disk space")
        
        # Check source directory
        if not os.path.exists(self.source_dir):
            print(f"  ✗ Source directory not found: {self.source_dir}")
            print("    Please run build_exe.py first to create the executable.")
            return False
        print(f"  ✓ Source directory found")
        
        # Check for existing installation
        if os.path.exists(os.path.join(self.install_dir, 'PharmacyERP.exe')):
            print(f"  ⚠ Existing installation found at {self.install_dir}")
            choice = input("  Do you want to reinstall? (y/n): ")
            if choice.lower() != 'y':
                print("Installation cancelled.")
                return False
        
        return True
    
    def create_directories(self):
        """Create necessary directories"""
        print("\nCreating directories...")
        
        directories = [
            self.install_dir,
            self.data_dir,
            self.logs_dir,
            self.config_dir,
            self.backups_dir,
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"  ✓ {directory}")
            except Exception as e:
                print(f"  ✗ Failed to create {directory}: {e}")
                return False
        
        return True
    
    def copy_files(self):
        """Copy application files to installation directory"""
        print(f"\nCopying files to {self.install_dir}...")
        
        try:
            # Copy all files from source to install directory
            for item in os.listdir(self.source_dir):
                src = os.path.join(self.source_dir, item)
                dst = os.path.join(self.install_dir, item)
                
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                
                print(f"  ✓ {item}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Failed to copy files: {e}")
            return False
    
    def create_shortcuts(self):
        """Create Start Menu and Desktop shortcuts"""
        print("\nCreating shortcuts...")
        
        try:
            import win32com.client
            
            shell = win32com.client.Dispatch("WScript.Shell")
            
            # Start Menu
            start_menu = os.path.join(os.environ.get('APPDATA'), 
                                     'Microsoft\\Windows\\Start Menu\\Programs')
            app_menu = os.path.join(start_menu, self.app_name)
            os.makedirs(app_menu, exist_ok=True)
            
            # Application shortcut
            shortcut_path = os.path.join(app_menu, f"{self.app_name}.lnk")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = os.path.join(self.install_dir, 'PharmacyERP.exe')
            shortcut.WorkingDirectory = self.install_dir
            shortcut.Description = self.app_name
            shortcut.save()
            print(f"  ✓ Start Menu shortcut created")
            
            # Desktop shortcut
            desktop = shell.SpecialFolders("Desktop")
            desktop_shortcut = os.path.join(desktop, f"{self.app_name}.lnk")
            shortcut = shell.CreateShortCut(desktop_shortcut)
            shortcut.Targetpath = os.path.join(self.install_dir, 'PharmacyERP.exe')
            shortcut.WorkingDirectory = self.install_dir
            shortcut.Description = self.app_name
            shortcut.save()
            print(f"  ✓ Desktop shortcut created")
            
            return True
            
        except ImportError:
            print("  ⚠ pywin32 not available. Shortcuts not created.")
            print("    Install with: pip install pywin32")
            return False
        except Exception as e:
            print(f"  ✗ Failed to create shortcuts: {e}")
            return False
    
    def write_registry(self):
        """Write registry entries"""
        print("\nWriting registry entries...")
        
        try:
            import winreg
            
            # Application registry key
            key_path = f"Software\\{self.app_name}"
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, self.install_dir)
            winreg.SetValueEx(key, "Version", 0, winreg.REG_SZ, self.app_version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, self.publisher)
            winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, datetime.now().isoformat())
            winreg.SetValueEx(key, "FirstRun", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            print(f"  ✓ Application registry entries created")
            
            # Uninstall registry key
            uninstall_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_name}"
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, uninstall_path)
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, self.app_name)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, self.app_version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, self.publisher)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, 
                            f'"{self.install_dir}\\uninstall.exe"')
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ,
                            f'"{self.install_dir}\\PharmacyERP.exe"')
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, self.install_dir)
            winreg.CloseKey(key)
            print(f"  ✓ Uninstall registry entries created")
            
            return True
            
        except ImportError:
            print("  ⚠ winreg not available. Registry entries not created.")
            return False
        except Exception as e:
            print(f"  ✗ Failed to write registry: {e}")
            return False
    
    def create_uninstaller(self):
        """Create uninstaller script"""
        print("\nCreating uninstaller...")
        
        uninstaller_content = '''@echo off
echo ============================================
echo Pharmacy ERP Uninstaller
echo ============================================
echo.

set /p confirm="This will uninstall Pharmacy ERP. Continue? (y/n): "
if /i not "%confirm%"=="y" (
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

echo Stopping Pharmacy ERP processes...
taskkill /IM "PharmacyERP.exe" /F >nul 2>&1

echo Removing files...
rmdir /s /q "%~dp0"

echo Removing registry entries...
reg delete "HKLM\\Software\\Pharmacy ERP" /f >nul 2>&1
reg delete "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Pharmacy ERP" /f >nul 2>&1

echo Removing shortcuts...
del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Pharmacy ERP" /q >nul 2>&1
del "%USERPROFILE%\\Desktop\\Pharmacy ERP.lnk" /q >nul 2>&1

echo.
set /p remove_data="Do you want to remove all user data (database, logs, backups)? (y/n): "
if /i "%remove_data%"=="y" (
    echo Removing user data...
    rmdir /s /q "%APPDATA%\\Pharmacy ERP"
    echo User data removed.
) else (
    echo User data preserved in %%APPDATA%%\\Pharmacy ERP
)

echo.
echo Uninstallation complete!
pause
'''
        
        uninstaller_path = os.path.join(self.install_dir, 'uninstall.bat')
        with open(uninstaller_path, 'w') as f:
            f.write(uninstaller_content)
        
        print(f"  ✓ Uninstaller created")
        return True
    
    def create_readme(self):
        """Create README file"""
        print("\nCreating README...")
        
        readme_content = f"""Pharmacy ERP - Installation Complete
{'=' * 50}

Installation Directory: {self.install_dir}
Data Directory: {self.data_dir}
Logs Directory: {self.logs_dir}

First Run:
  - Double-click PharmacyERP.exe from the Start Menu or Desktop
  - The application will guide you through the first-run setup
  - Create your admin account during first run

Default Admin Credentials:
  - Username: admin
  - Password: admin123
  - IMPORTANT: Change the password immediately after first login!

Uninstall:
  - Run uninstall.bat from the installation directory
  - Or use Windows Settings > Apps > Pharmacy ERP

Support:
  - Check logs in {self.logs_dir} for troubleshooting
  - Contact support for assistance

Version: {self.app_version}
Install Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        readme_path = os.path.join(self.install_dir, 'README.txt')
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        print(f"  ✓ README created")
        return True
    
    def run(self):
        """Run the complete installation process"""
        print("=" * 60)
        print(f"Pharmacy ERP {self.app_version} - Installer")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\nInstallation cancelled due to failed prerequisites.")
            return False
        
        # Require admin
        self.require_admin()
        
        # Installation steps
        steps = [
            ("Creating directories", self.create_directories),
            ("Copying files", self.copy_files),
            ("Creating shortcuts", self.create_shortcuts),
            ("Writing registry", self.write_registry),
            ("Creating uninstaller", self.create_uninstaller),
            ("Creating README", self.create_readme),
        ]
        
        for step_name, step_func in steps:
            print(f"\n[Step] {step_name}")
            if not step_func():
                print(f"\n✗ Installation failed at: {step_name}")
                return False
        
        # Success
        print("\n" + "=" * 60)
        print("Installation completed successfully!")
        print("=" * 60)
        print(f"\nApplication installed to: {self.install_dir}")
        print(f"Data will be stored in: {self.data_dir}")
        print("\nLaunch Pharmacy ERP from:")
        print(f"  - Start Menu > {self.app_name}")
        print(f"  - Desktop shortcut")
        print(f"  - {self.install_dir}\\PharmacyERP.exe")
        print("\nRemember to complete the first-run setup on first launch!")
        print("=" * 60)
        
        return True


def main():
    """Main entry point"""
    installer = PythonInstaller()
    success = installer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
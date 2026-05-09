import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox, QDialog
from PySide6.QtCore import Qt
from theme.theme_manager import ThemeManager
from ui.main_window import MainWindow
from ui.role_manager import get_role_from_user_data
from utils.device_fingerprint import generate_device_id
from license.license_validator import initialize_license_validation
from security.obfuscator import Obfuscator
from security.encrypted_config import EncryptedConfig
from security.tamper_detector import TamperDetector
from api.client import APIClient


def check_session_valid(api_client):
    """Check if saved session is valid."""
    try:
        session_file = os.path.join(os.path.dirname(__file__), "..", "..", "session.dat")
        if os.path.exists(session_file):
            with open(session_file, "r") as f:
                data = f.read().split(":")
                if len(data) == 2:
                    username, token = data
                    api_client.set_auth_token(token)
                    # Verify token is valid - with timeout to not block
                    try:
                        from api.endpoints import get_endpoint
                        endpoint = get_endpoint("profile") or "/api/auth/profile/"
                        # Use short timeout
                        import requests
                        response = requests.get(
                            f"{api_client.base_url}{endpoint}",
                            headers=api_client.session.headers,
                            timeout=3
                        )
                        if response.status_code == 200:
                            return True, username
                    except Exception as e:
                        print(f"[WARN] Session check failed: {e}")
                        # Don't block - allow app to start anyway
                        pass
    except Exception as e:
        print(f"[WARN] Session validation error: {e}")
    return False, None


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Pharmacy ERP")
    app.setApplicationVersion("1.0.0")
    
    # Security hardening: tamper detection (skip in development)
    dev_mode = os.path.exists('DEVELOPMENT') or os.environ.get('PHARMACY_ERP_DEVELOPMENT', '').lower() in ('true', '1', 'yes')
    
    print(f"[DEBUG] Dev mode: {dev_mode}")
    print(f"[DEBUG] DEVELOPMENT file exists: {os.path.exists('DEVELOPMENT')}")
    print(f"[DEBUG] PHARMACY_ERP_DEVELOPMENT env: {os.environ.get('PHARMACY_ERP_DEVELOPMENT', 'NOT SET')}")
    
    if not dev_mode:
        critical_files = [
            'main.py',
            'ui/main_window.py',
            'license/license_validator.py',
            'license/license_service.py',
            'license/rsa_utils.py',
            'utils/device_fingerprint.py',
            'utils/hardware_id.py'
        ]
        base_dir = os.path.dirname(os.path.abspath(__file__))
        critical_files = [os.path.join(base_dir, f) for f in critical_files]
        
        detector = TamperDetector()
        for file_path in critical_files:
            if os.path.exists(file_path):
                detector.add_file(file_path)
        
        baseline_file = os.path.join(base_dir, 'security_baseline.json')
        if not os.path.exists(baseline_file):
            detector.save_baseline(baseline_file)
        else:
            detector.load_baseline(baseline_file)
        
        is_tampered, tampered_files = detector.check_integrity()
        if is_tampered:
            msg = "Security error: Tampering detected in critical files.\n"
            msg += "The following files have been modified:\n"
            for f in tampered_files:
                msg += f"  - {f}\n"
            msg += "The application will now exit for security reasons."
            QMessageBox.critical(None, "Security Error", msg)
            sys.exit(1)
    
    # Generate and set device ID for licensing
    device_id = generate_device_id()
    app.setProperty("deviceId", device_id)
    print(f"[DEBUG] Device ID: {device_id}")
    
    # Initialize theme manager
    theme_manager = ThemeManager()
    theme_manager.apply_theme("light")
    print("[DEBUG] Theme manager initialized")
    
    # Initialize license validation
    license_validator = initialize_license_validation()
    print("[DEBUG] License validator initialized")
    
    # Initialize API client
    api_client = APIClient()
    print("[DEBUG] API client initialized")
    
    # Authentication gateway
    authenticated = False
    user_data = {}
    
    print(f"[DEBUG] Dev mode check: {dev_mode}")
    
    if not dev_mode:
        # Try to restore saved session
        try:
            print("[DEBUG] Checking session validity...")
            session_valid, saved_username = check_session_valid(api_client)
            print(f"[DEBUG] Session valid: {session_valid}, Username: {saved_username}")
            
            if session_valid:
                print(f"[INFO] Session restored for user: {saved_username}")
                authenticated = True
                user_data = {"username": saved_username, "role": "admin"}  # Default role for session
            else:
                print("[INFO] No valid session found, showing login dialog")
                # Show login dialog
                from ui.auth.login_screen import LoginDialog
                login_dialog = LoginDialog(api_client)
                
                # Try to auto-fill username if we have saved session
                username, _ = login_dialog.load_session()
                print(f"[DEBUG] Loaded session username: {username}")
                if username:
                    login_dialog.username.setText(username)
                    print(f"[DEBUG] Pre-filled username: {username}")
                
                # Connect to login_successful signal to capture user data
                user_data_container = {}
                def on_login_success(data):
                    user_data_container["data"] = data
                login_dialog.login_successful.connect(on_login_success)
                
                print("[DEBUG] Showing login dialog...")
                result = login_dialog.exec()
                print(f"[DEBUG] Login dialog result: {result} (Accepted={QDialog.Accepted})")
                
                if result == QDialog.Accepted:
                    print("[INFO] Login successful")
                    authenticated = True
                    user_data = user_data_container.get("data", {})
                    print(f"[DEBUG] User data from login: {user_data}")
                else:
                    print("[INFO] Login cancelled or failed")
                    sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Auth error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        # Development mode - skip authentication
        print("[INFO] Development mode - authentication bypassed")
        authenticated = True
        # Set default admin role for development
        user_data = {"username": "admin", "role": "admin"}
        # Set a dev token for API calls
        api_client.set_auth_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6IiIsImV4cCI6MTc3ODI5ODQ1MSwiaWF0IjoxNzc4MjEyMDUxfQ.PzsR8WV6RGM-TZAmFpu5hGk7A3Y9-c2fK8JF_CSczcI")
    
    print(f"[DEBUG] Authenticated: {authenticated}")
    print(f"[DEBUG] User data: {user_data}")
    
    if not authenticated:
        print("[ERROR] Not authenticated, exiting")
        sys.exit(1)
    
    # Create and show main window
    try:
        print("[DEBUG] Creating main window...")
        window = MainWindow(license_validator=license_validator, user_data=user_data, api_client=api_client)
        print("[DEBUG] Main window created, showing...")
        window.show()
        print("[DEBUG] Main window shown")
    except Exception as e:
        print(f"[ERROR] Main window error: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.critical(None, "Error", f"Failed to start application: {e}")
    
    print("[DEBUG] Entering application event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
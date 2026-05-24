import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox, QDialog
from PySide6.QtCore import Qt, QTimer
from theme.theme_engine import ThemeEngine
from ui.main_window import MainWindow
from utils.device_fingerprint import generate_device_id
from license.license_validator import initialize_license_validation
from security.tamper_detector import TamperDetector
from api.client import APIClient
from security.auth_manager import AuthManager
from utils.logger import get_logger, init_logging, shutdown as log_shutdown, set_active_screen, get_active_screen, capture_health_snapshot, DiagnosticContext, record_error, emit_event
from security.session_store import load_session as session_store_load, _migrate_from_legacy

log = get_logger(__name__)


def _get_active_screen_context() -> str:
    """Get the currently active UI screen name for crash context."""
    try:
        app = QApplication.instance()
        if not app:
            return ""
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'pages') and hasattr(widget, 'header'):
                idx = widget.pages.currentIndex()
                page_title = widget.header.text() if widget.header else f"page_{idx}"
                return page_title
    except Exception:
        pass
    return ""


def global_excepthook(exc_type, exc_value, exc_traceback):
    """Global exception handler to prevent silent crashes."""
    import traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)
    screen = _get_active_screen_context() or get_active_screen()
    try:
        logger = get_logger('crash')
        extra = {'extra_fields': {'tags': ['crash', 'fatal']}}
        if screen:
            extra['extra_fields']['screen'] = screen
        diag = DiagnosticContext.get_snapshot()
        if diag:
            extra['extra_fields']['diagnostic'] = diag
        try:
            hs = capture_health_snapshot()
            extra['extra_fields']['health'] = hs
        except Exception:
            pass
        record_error(exc_type=exc_type.__name__, module='global_excepthook', category='ui')
        emit_event("crash_event", "exception", {"exception_type": exc_type.__name__, "message": str(exc_value)}, correlation_id=None)
        logger.critical(f"Unhandled exception: {exc_type.__name__}: {exc_value} | screen={screen}", extra=extra)
        logger.debug(f"Full traceback:\n{tb_text}", extra={'extra_fields': {'tags': ['crash']}})
    except Exception:
        pass
    print(f"[FATAL] Unhandled exception: {tb_text}", file=sys.stderr)
    try:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Unexpected Error",
            f"An unexpected error occurred:\n\n{exc_type.__name__}: {exc_value}\n\n"
            "The application may become unstable. Please restart."
        )
    except Exception:
        pass


def main():
    init_logging(level=logging.DEBUG)
    log.info("=== Application starting ===", extra={'extra_fields': {'tags': ['system', 'startup']}})
    try:
        hs = capture_health_snapshot()
        log.debug(f"Startup snapshot: {hs}",
                   extra={'extra_fields': {'tags': ['system', 'startup', 'diagnostic']}})
    except Exception:
        pass

    sys.excepthook = global_excepthook
    app = QApplication(sys.argv)
    
    app.setApplicationName("Pharmacy ERP")
    app.setApplicationVersion("1.0.0")
    
    # Dev mode detection: auto-activate when PHARMACY_ERP_DEVELOPMENT is set
    dev_mode = os.environ.get('PHARMACY_ERP_DEVELOPMENT', 'False').lower() in ('true', '1', 'yes')
    
    log.debug(f"Dev mode: {dev_mode}", extra={'extra_fields': {'tags': ['system']}})
    log.debug(f"DEVELOPMENT file exists: {os.path.exists('DEVELOPMENT')}", extra={'extra_fields': {'tags': ['system']}})
    
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
        
        # Perform tamper detection in a deferred singleShot to avoid startup delay
        # The app starts, then checks integrity. If failed, it exits.
        def run_integrity_check():
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
        
        QTimer.singleShot(1000, run_integrity_check)
    
    # Generate and set device ID for licensing
    device_id = generate_device_id()
    app.setProperty("deviceId", device_id)
    log.debug(f"Device ID: {device_id}", extra={'extra_fields': {'tags': ['system']}})

    # Initialize unified theme engine
    ThemeEngine.instance().apply_theme("dark")
    log.debug("Theme engine initialized", extra={'extra_fields': {'tags': ['theme']}})

    # Apply global stylesheet for dropdown readability (WCAG AA compliant)
    # ThemeEngine updates module constants; this stylesheet ensures QComboBox
    # popups have proper contrast in both light and dark themes.
    from theme.style_builder import UIStyleBuilder
    app.setStyleSheet(UIStyleBuilder.get_global_style())
    log.debug("Global dropdown stylesheet applied", extra={'extra_fields': {'tags': ['theme']}})

    # Initialize license validation (dev mode bypasses all checks)
    license_validator = initialize_license_validation(dev_mode=dev_mode)
    log.debug("License validator initialized", extra={'extra_fields': {'tags': ['license']}})

    # Initialize API client
    api_client = APIClient()
    log.debug("API client initialized", extra={'extra_fields': {'tags': ['api']}})

    # Initialize AuthManager (handles session restore automatically)
    auth_manager = AuthManager(api_client)
    log.debug("AuthManager initialized", extra={'extra_fields': {'tags': ['auth']}})

    # Authentication gateway
    authenticated = False
    user_data = {}

    log.debug(f"Dev mode check: {dev_mode}", extra={'extra_fields': {'tags': ['auth']}})

    if not dev_mode:
        try:
            # Check if AuthManager restored a valid session
            if auth_manager.is_authenticated:
                log.info(f"Session restored for user: {auth_manager.user.get('username', 'unknown')}",
                         extra={'extra_fields': {'tags': ['auth']}})
                authenticated = True
                user_data = auth_manager.user or {}
            else:
                log.info("No valid session found, showing login dialog", extra={'extra_fields': {'tags': ['auth']}})
                from ui.auth.login_screen import LoginDialog
                login_dialog = LoginDialog(api_client=api_client, auth_manager=auth_manager)

                username, _ = login_dialog.load_session()
                log.debug(f"Loaded session username: {username}", extra={'extra_fields': {'tags': ['auth']}})
                if username:
                    login_dialog.username.setText(username)
                    log.debug(f"Pre-filled username: {username}", extra={'extra_fields': {'tags': ['auth']}})

                user_data_container = {}
                def on_login_success(data):
                    user_data_container["data"] = data
                login_dialog.login_successful.connect(on_login_success)

                log.debug("Showing login dialog...", extra={'extra_fields': {'tags': ['auth']}})
                result = login_dialog.exec()
                log.debug(f"Login dialog result: {result} (Accepted={QDialog.Accepted})", extra={'extra_fields': {'tags': ['auth']}})

                if result == QDialog.Accepted:
                    log.info("Login successful", extra={'extra_fields': {'tags': ['auth']}})
                    authenticated = True
                    user_data = user_data_container.get("data", {})
                    log.debug(f"User data from login: {user_data}", extra={'extra_fields': {'tags': ['auth']}})
                else:
                    log.info("Login cancelled or failed", extra={'extra_fields': {'tags': ['auth']}})
                    sys.exit(0)
        except Exception as e:
            log.error(f"Auth error: {e}", exc_info=True, extra={'extra_fields': {'tags': ['auth']}})
            sys.exit(1)
    else:
        log.warning("DEVELOPMENT MODE — authentication bypassed (set PHARMACY_ERP_DEVELOPMENT to disable)",
                     extra={'extra_fields': {'tags': ['auth']}})
        authenticated = True
        user_data = {"username": "dev_admin", "role": "admin", "roles": ["Admin"]}
        dev_token = os.environ.get('PHARMACY_ERP_DEV_TOKEN')
        if dev_token:
            api_client.set_auth_token(dev_token)
        else:
            log.warning("No PHARMACY_ERP_DEV_TOKEN set — running without auth token (API calls will fail)",
                         extra={'extra_fields': {'tags': ['auth']}})

    log.debug(f"Authenticated: {authenticated}", extra={'extra_fields': {'tags': ['auth']}})
    log.debug(f"User data: {user_data}", extra={'extra_fields': {'tags': ['auth']}})

    if not authenticated:
        log.error("Not authenticated, exiting", extra={'extra_fields': {'tags': ['auth']}})
        sys.exit(1)

    try:
        log.debug("Creating main window...", extra={'extra_fields': {'tags': ['ui']}})
        window = MainWindow(license_validator=license_validator, user_data=user_data, api_client=api_client, auth_manager=auth_manager)
        log.debug("Main window created, showing...", extra={'extra_fields': {'tags': ['ui']}})
        window.show()
        log.debug("Main window shown", extra={'extra_fields': {'tags': ['ui']}})
    except Exception as e:
        log.critical(f"Main window error: {e}", exc_info=True, extra={'extra_fields': {'tags': ['ui']}})
        QMessageBox.critical(None, "Error", f"Failed to start application: {e}")

    log.debug("Entering application event loop", extra={'extra_fields': {'tags': ['system']}})
    result = app.exec()
    log_shutdown()
    sys.exit(result)


if __name__ == "__main__":
    main()
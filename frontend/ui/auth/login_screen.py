"""Login screen for ERP."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                 QLineEdit, QMessageBox, QCheckBox,
                                 QFrame)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.constants import (SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_HELPER, TEXT_DISPLAY,
                           BORDER_RADIUS_LG,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                           COLOR_BORDER, COLOR_BORDER_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                           COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from api.client import APIClient
from api.endpoints import get_endpoint
from security.session_store import save_session as encrypted_save_session, load_session as encrypted_load_session
from security.auth_manager import AuthManager
from utils.logger import get_logger

log = get_logger('auth')

# Design system imports
from ui.constants import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
    COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED, COLOR_DANGER
)


class LoginDialog(QDialog):
    """Professional login dialog with JWT authentication."""
    
    login_successful = Signal(dict)  # user data
    
    def __init__(self, api_client=None, auth_manager=None):
        super().__init__()
        self.api_client = api_client or APIClient()
        self.auth_manager = auth_manager or AuthManager(self.api_client)
        self.setWindowTitle("Pharmacy ERP - Login")
        self.setFixedSize(420, 520)
        self.setModal(True)
        self._loading = False
        self._attempts = 0
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_MAIN};
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QLineEdit {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG};
                padding: {SPACING_MD}px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_BODY}px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLOR_PRIMARY};
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BG_MAIN};
                border: none;
                border-radius: {BORDER_RADIUS_LG};
                padding: {SPACING_LG}px;
                font-size: {TEXT_BODY}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_PRIMARY_ACTIVE};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BORDER};
                color: {COLOR_TEXT_MUTED};
            }}
            QCheckBox {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XXL + SPACING_LG,  SPACING_XXL + SPACING_LG,  SPACING_XXL + SPACING_LG,  SPACING_XXL + SPACING_LG)
        layout.setSpacing(SPACING_NONE)
        
        # Header with logo
        header = QFrame()
        header.setFixedHeight(80)
        header_layout = QVBoxLayout(header)
        
        logo_label = QLabel("💊")
        logo_label.setStyleSheet(f"font-size: {TEXT_DISPLAY}pt; font-weight: 700; color: {COLOR_PRIMARY};")
        logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(logo_label)
        
        title = QLabel("Pharmacy ERP")
        title.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: {TEXT_SECTION_TITLE}pt; font-weight: 700;")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)

        subtitle = QLabel("Enterprise Management System")
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt;")
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        layout.addSpacing(30)
        
        # Login form
        form = QFrame()
        form_layout = QVBoxLayout(form)
        form_layout.setSpacing(SPACING_LG + SPACING_XS)
        
        # Username
        user_label = QLabel("Username")
        user_label.setStyleSheet(f"font-size: {TEXT_LABEL}pt; color: {COLOR_TEXT_PRIMARY};")
        form_layout.addWidget(user_label)
        
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter your username")
        self.username.setFixedHeight(48)
        self.username.returnPressed.connect(self.do_login)
        form_layout.addWidget(self.username)
        
        # Password
        pass_label = QLabel("Password")
        pass_label.setStyleSheet(f"font-size: {TEXT_LABEL}pt; color: {COLOR_TEXT_PRIMARY};")
        form_layout.addWidget(pass_label)
        
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Enter your password")
        self.password.setFixedHeight(48)
        self.password.returnPressed.connect(self.do_login)
        form_layout.addWidget(self.password)
        
        # Show password toggle
        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self.toggle_password)
        form_layout.addWidget(self.show_password)
        
        # Remember me
        self.remember = QCheckBox("Remember me")
        form_layout.addWidget(self.remember)
        
        layout.addWidget(form)
        
        layout.addSpacing(20)
        
        # Login button
        self.login_btn = EnterpriseButton(text="Sign In", variant=ButtonVariant.PRIMARY, size=ButtonSize.LARGE)
        self.login_btn.clicked.connect(self.do_login)
        layout.addWidget(self.login_btn)
        
        # Status message
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {COLOR_DANGER};")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Footer
        footer = QLabel("© 2026 Pharmacy ERP System")
        footer.setStyleSheet(f"font-size: {TEXT_HELPER}pt; color: {COLOR_TEXT_MUTED};")
        footer.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)
    
    def toggle_password(self, checked):
        """Toggle password visibility."""
        if checked:
            self.password.setEchoMode(QLineEdit.Normal)
        else:
            self.password.setEchoMode(QLineEdit.Password)
    
    def set_loading(self, loading):
        """Set loading state."""
        self._loading = loading
        self.login_btn.setEnabled(not loading)
        self.username.setEnabled(not loading)
        self.password.setEnabled(not loading)
        if loading:
            self.login_btn.setText("Authenticating...")
            self.status_label.setVisible(False)
        else:
            self.login_btn.setText("Sign In")
    
    def show_error(self, message):
        """Show error message."""
        self.status_label.setText(message)
        self.status_label.setVisible(True)
        self._attempts += 1
    
    def do_login(self):
        """Execute login."""
        if self._loading:
            return
            
        username = self.username.text().strip()
        password = self.password.text()
        
        if not username:
            self.show_error("Username is required")
            self.username.setFocus()
            return
        
        if not password:
            self.show_error("Password is required")
            self.password.setFocus()
            return
        
        self.set_loading(True)
        
        QTimer.singleShot(100, lambda: self._perform_login(username, password))
    
    def _perform_login(self, username, password):
        """Perform actual login API call via AuthManager."""
        try:
            log.info(f"Login attempt: user={username}",
                     extra={'extra_fields': {'tags': ['auth', 'login']}})
            
            success = self.auth_manager.login(username, password)
            self.set_loading(False)
            
            if success:
                user_data = self.auth_manager.user or {}
                token = self.auth_manager.api_client._auth_token

                if token:
                    if self.remember.isChecked():
                        encrypted_save_session(username, token, self.auth_manager.api_client._refresh_token or '')
                        log.info(f"Session persisted for user={username}",
                                 extra={'extra_fields': {'tags': ['auth', 'session']}})

                    user_data["token"] = token
                    log.info(f"Login successful: user={username}",
                             extra={'extra_fields': {'tags': ['auth', 'login']}})
                    self.login_successful.emit(user_data)
                    self.accept()
                    return
            
            # Handle error
            self.show_error("Invalid credentials")
                
        except Exception as e:
            self.set_loading(False)
            log.warning(f"Login connection error: user={username} error={e}",
                         extra={'extra_fields': {'tags': ['auth', 'login', 'error']}})
            self.show_error(f"Connection failed: {str(e)}")
    
    def _save_session(self, token, username):
        """Save session to encrypted file. Use encrypted_save_session instead."""
        encrypted_save_session(username, token)

    def load_session(self):
        """Load saved session from encrypted store with legacy fallback."""
        username, token, _ = encrypted_load_session()
        if username and token:
            return username, token
        return None, None
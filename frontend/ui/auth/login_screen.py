from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Login screen for ERP."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QPushButton, QMessageBox, QCheckBox,
                                QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush
from api.client import APIClient
from api.endpoints import get_endpoint

# Design system imports
from ui.constants import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
    COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED, COLOR_DANGER
)


class LoginDialog(QDialog):
    """Professional login dialog with JWT authentication."""
    
    login_successful = Signal(dict)  # user data
    
    def __init__(self, api_client=None):
        super().__init__()
        self.api_client = api_client or APIClient()
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
                border-radius: 8px;
                padding: 12px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLOR_PRIMARY};
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BG_MAIN};
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 14px;
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
        layout.setSpacing(0)
        
        # Header with logo
        header = QFrame()
        header.setFixedHeight(80)
        header_layout = QVBoxLayout(header)
        
        logo_label = QLabel("💊")
        logo_label.setFont(QFont("Segoe UI", 36))
        logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(logo_label)
        
        title = QLabel("Pharmacy ERP")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_PRIMARY};")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)

        subtitle = QLabel("Enterprise Management System")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
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
        user_label.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(user_label)
        
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter your username")
        self.username.setFixedHeight(48)
        self.username.returnPressed.connect(self.do_login)
        form_layout.addWidget(self.username)
        
        # Password
        pass_label = QLabel("Password")
        pass_label.setFont(QFont("Segoe UI", 11))
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
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(50)
        self.login_btn.clicked.connect(self.do_login)
        layout.addWidget(self.login_btn)
        
        # Status message
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {COLOR_DANGER};")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Footer
        footer = QLabel("© 2026 Pharmacy ERP System")
        footer.setFont(QFont("Segoe UI", 9))
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
        """Perform actual login API call."""
        try:
            endpoint = get_endpoint("login") or "/api/auth/login/"
            response = self.api_client.post(endpoint, {
                "username": username,
                "password": password
            })
            
            self.set_loading(False)
            
            if response and isinstance(response, dict):
                if response.get("success"):
                    token = response.get("token") or response.get("access")
                    user_data = response.get("user", {})
                    
                    if token:
                        self.api_client.set_auth_token(token)
                        
                        # Store session
                        if self.remember.isChecked():
                            self._save_session(token, username)
                        
                        user_data["token"] = token
                        self.login_successful.emit(user_data)
                        self.accept()
                        return
                
                # Handle error
                error = response.get("error", {})
                if isinstance(error, dict):
                    msg = error.get("message", "Login failed")
                else:
                    msg = str(error)
                self.show_error(msg)
                
            else:
                self.show_error("Invalid response from server")
                
        except Exception as e:
            self.set_loading(False)
            self.show_error(f"Connection failed: {str(e)}")
    
    def _save_session(self, token, username):
        """Save session to file."""
        try:
            import os
            session_file = os.path.join(os.path.dirname(__file__), "..", "..", "session.dat")
            with open(session_file, "w") as f:
                f.write(f"{username}:{token}")
        except:
            pass
    
    def load_session(self):
        """Load saved session."""
        try:
            import os
            session_file = os.path.join(os.path.dirname(__file__), "..", "..", "session.dat")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    data = f.read().split(":")
                    if len(data) == 2:
                        return data
        except:
            pass
        return None, None
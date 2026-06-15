"""Login screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                                 QLineEdit, QCheckBox, QFrame,
                                 QGraphicsDropShadowEffect, QWidget)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QColor
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, TEXT_PAGE_TITLE, TEXT_BODY, TEXT_BODY_SMALL,
                           TEXT_LABEL, TEXT_HELPER, TEXT_DISPLAY, BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_XL, PADDING_DIALOG, INPUT_HEIGHT_XL, BUTTON_HEIGHT_XL,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY,
                           COLOR_DANGER)
from api.client import APIClient
from security.session_store import load_session as encrypted_load_session
from security.auth_manager import AuthManager
from utils.logger import get_logger

log = get_logger('auth')


class LoginDialog(EnterpriseDialog):
    """Professional login dialog with JWT authentication."""
    
    login_successful = Signal(dict)  # user data
    
    def __init__(self, api_client=None, auth_manager=None, parent=None):
        self.api_client = api_client or APIClient()
        self.auth_manager = auth_manager or AuthManager(self.api_client)
        self._loading = False
        self._attempts = 0
        super().__init__("Pharmacy ERP - Login", DialogType.CUSTOM, parent)
        self.setMinimumSize(480, 640)
        self.setModal(True)
        content = self._build_content()
        self.set_content(content)
    
    def _create_button_area(self):
        return None
    
    def _build_content(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Background container to center the card
        container = QFrame()
        container.setObjectName("container")
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignCenter)
        
        # The Login Card
        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedSize(400, 560)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(PADDING_DIALOG, PADDING_DIALOG, PADDING_DIALOG, PADDING_DIALOG)
        card_layout.setSpacing(SPACING_LG)
        
        # Add shadow to the card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)
        
        # Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(SPACING_SM)
        header_layout.setAlignment(Qt.AlignCenter)
        
        logo_label = QLabel("💊")
        logo_label.setStyleSheet(f"font-size: {TEXT_DISPLAY}pt; margin-bottom: {SPACING_XS}px;")
        logo_label.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel("Welcome Back")
        title_label.setStyleSheet(f"""
            font-size: {TEXT_PAGE_TITLE}pt; 
            font-weight: bold; 
            color: {COLOR_TEXT_PRIMARY};
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("Sign in to your Pharmacy ERP")
        subtitle_label.setStyleSheet(f"font-size: {TEXT_BODY}pt; color: {COLOR_TEXT_MUTED};")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        card_layout.addLayout(header_layout)
        
        card_layout.addSpacing(SPACING_XL)
        
        # Form Section
        form_layout = QVBoxLayout()
        form_layout.setSpacing(SPACING_MD)
        
        # Username Input
        username_layout = QVBoxLayout()
        username_layout.setSpacing(SPACING_XS)
        username_label = QLabel("Username")
        username_label.setStyleSheet(f"font-size: {TEXT_LABEL}pt; color: {COLOR_TEXT_SECONDARY}; font-weight: 500;")
        self.username = QLineEdit()
        self.username.setPlaceholderText("e.g. admin")
        self.username.setFixedHeight(INPUT_HEIGHT_XL)
        self.username.setObjectName("authInput")
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username)
        form_layout.addLayout(username_layout)
        
        # Password Input
        password_layout = QVBoxLayout()
        password_layout.setSpacing(SPACING_XS)
        password_label = QLabel("Password")
        password_label.setStyleSheet(f"font-size: {TEXT_LABEL}pt; color: {COLOR_TEXT_SECONDARY}; font-weight: 500;")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("••••••••")
        self.password.setFixedHeight(INPUT_HEIGHT_XL)
        self.password.setObjectName("authInput")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password)
        form_layout.addLayout(password_layout)
        
        # Options Layout (Show Pass & Remember Me)
        options_layout = QHBoxLayout()
        self.show_password = QCheckBox("Show")
        self.show_password.setStyleSheet(f"font-size: {TEXT_BODY_SMALL}pt; color: {COLOR_TEXT_MUTED};")
        self.show_password.toggled.connect(self.toggle_password)
        
        self.remember = QCheckBox("Remember me")
        self.remember.setStyleSheet(f"font-size: {TEXT_BODY_SMALL}pt; color: {COLOR_TEXT_MUTED};")
        
        options_layout.addWidget(self.show_password)
        options_layout.addStretch()
        options_layout.addWidget(self.remember)
        form_layout.addLayout(options_layout)
        
        card_layout.addLayout(form_layout)
        
        card_layout.addSpacing(SPACING_MD)
        
        # Error Message
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY_SMALL}pt; font-weight: 500;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        card_layout.addWidget(self.status_label)
        
        # Login Button
        self.login_btn = EnterpriseButton(
            text="Sign In", 
            variant=ButtonVariant.PRIMARY, 
            size=ButtonSize.LARGE
        )
        self.login_btn.setFixedHeight(BUTTON_HEIGHT_XL)
        self.login_btn.clicked.connect(self.do_login)
        card_layout.addWidget(self.login_btn)
        
        card_layout.addStretch()
        
        # Footer
        footer_label = QLabel("Pharmacy ERP v2.0 © 2026")
        footer_label.setStyleSheet(f"font-size: {TEXT_HELPER}pt; color: {COLOR_TEXT_MUTED};")
        footer_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(footer_label)
        
        container_layout.addWidget(card)
        main_layout.addWidget(container)
        
        # Apply Stylesheet
        main_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BG_MAIN};
            }}
            #loginCard {{
                background-color: {COLOR_BG_SURFACE};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: {BORDER_RADIUS_XL}px;
            }}
            QLineEdit#authInput {{
                background-color: {COLOR_BG_INPUT};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                padding-left: {SPACING_MD}px;
                padding-right: {SPACING_MD}px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_BODY}pt;
            }}
            QLineEdit#authInput:focus {{
                border: 2px solid {COLOR_PRIMARY};
                background-color: {COLOR_BG_ELEVATED};
            }}
            QCheckBox {{
                spacing: {SPACING_XS}px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: {BORDER_RADIUS_SM}px;
                border: 1px solid {COLOR_BORDER};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLOR_PRIMARY};
                border: 1px solid {COLOR_PRIMARY};
            }}
        """)
        
        # Connect enter keys
        self.username.returnPressed.connect(self.do_login)
        self.password.returnPressed.connect(self.do_login)
        
        return main_widget
    
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
        """Session persistence is handled by AuthManager."""
        return None

    def load_session(self):
        """Load saved session from encrypted store with legacy fallback."""
        username, token, _ = encrypted_load_session()
        if username and token:
            return username, token
        return None, None
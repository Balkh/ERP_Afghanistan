"""Email Configuration Dialog for Offsite Replication."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
                                QLineEdit, QCheckBox, QGroupBox, QFormLayout,
                                QMessageBox)
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XXL, TEXT_SECTION_TITLE,
                           TEXT_BODY, BORDER_RADIUS_MD, COLOR_BG_INPUT,
                           COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_PRIMARY, COLOR_FORM_FOOTER_BORDER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType


class EmailConfigDialog(EnterpriseDialog):
    """Dialog for configuring SMTP offsite replication."""

    def __init__(self, api_client, parent=None):
        super().__init__("Email Configuration", DialogType.CUSTOM, parent)
        self.api_client = api_client
        self._config = {}
        content = self._build_content()
        self.set_content(content)
        self._load_config()

    def _build_content(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(SPACING_LG)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("SMTP Email Configuration")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_SECTION_TITLE}pt; font-weight: 700;")
        layout.addWidget(title)

        form_group = QGroupBox("SMTP Settings")
        form_group.setStyleSheet("""
            QGroupBox {{
                font-size: {TEXT_BODY}pt; font-weight: 700; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px;
                margin-top: 10px; padding-top: {SPACING_MD}px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }}
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(SPACING_MD)

        self.enabled_cb = QCheckBox("Enable offsite email replication")
        self.enabled_cb.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}pt;")
        form_layout.addRow(self.enabled_cb)

        self.smtp_host = QLineEdit()
        self.smtp_host.setPlaceholderText("smtp.gmail.com")
        self._style_input(self.smtp_host)
        form_layout.addRow("SMTP Host", self.smtp_host)

        self.smtp_port = QLineEdit()
        self.smtp_port.setPlaceholderText("587")
        self._style_input(self.smtp_port)
        form_layout.addRow("SMTP Port", self.smtp_port)

        self.smtp_user = QLineEdit()
        self.smtp_user.setPlaceholderText("your@email.com")
        self._style_input(self.smtp_user)
        form_layout.addRow("Username", self.smtp_user)

        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.Password)
        self.smtp_password.setPlaceholderText("App password")
        self._style_input(self.smtp_password)
        form_layout.addRow("Password", self.smtp_password)

        self.from_email = QLineEdit()
        self.from_email.setPlaceholderText("your@email.com")
        self._style_input(self.from_email)
        form_layout.addRow("From Email", self.from_email)

        self.recipients = QLineEdit()
        self.recipients.setPlaceholderText("admin@company.com, backup@company.com")
        self._style_input(self.recipients)
        form_layout.addRow("Recipients (comma-separated)", self.recipients)

        self.use_tls = QCheckBox("Use TLS")
        self.use_tls.setChecked(True)
        self.use_tls.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}pt;")
        form_layout.addRow(self.use_tls)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        return content

    def _create_button_area(self):
        button_area = QFrame()
        button_area.setFixedHeight(60)

        layout = QHBoxLayout(button_area)
        layout.setContentsMargins(SPACING_XXL, SPACING_SM, SPACING_XXL, SPACING_SM)

        self.test_btn = EnterpriseButton(text="Send Test Email", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.test_btn.clicked.connect(self._test_email)
        layout.addWidget(self.test_btn)

        layout.addStretch()

        cancel_btn = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        save_btn = EnterpriseButton(text="Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)

        button_area.setStyleSheet(f"""
            QFrame {{
                background-color: trnasparent;
                border-top: 1px solid {COLOR_FORM_FOOTER_BORDER};
            }}
        """)
        return button_area

    def _style_input(self, widget):
        widget.setStyleSheet("""
            QLineEdit {{
                background: {COLOR_BG_INPUT};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {SPACING_SM}px;
                padding: {SPACING_SM}px;
                font-size: {TEXT_BODY}pt;
            }}
            QLineEdit:focus {{ border-color: {COLOR_PRIMARY}; }}
        """)

    def _load_config(self):
        try:
            response = self.api_client.get("/api/backup/offsite-replication/config/")
            if isinstance(response, dict) and response.get('success'):
                self._config = response.get('data', {})
            elif isinstance(response, dict):
                self._config = response
            else:
                return

            self.enabled_cb.setChecked(self._config.get('enabled', False))
            self.smtp_host.setText(self._config.get('smtp_host', ''))
            self.smtp_port.setText(str(self._config.get('smtp_port', 587)))
            self.smtp_user.setText(self._config.get('smtp_user', ''))
            self.from_email.setText(self._config.get('from_email', ''))

            recipients = self._config.get('recipients', [])
            if isinstance(recipients, list):
                self.recipients.setText(', '.join(recipients))
            else:
                self.recipients.setText(str(recipients))

            self.use_tls.setChecked(self._config.get('smtp_use_tls', True))
        except Exception as e:
            print(f"Failed to load email config: {e}")

    def _test_email(self):
        recipient = self.from_email.text().strip()
        if not recipient:
            QMessageBox.warning(self, "Test Email", "Enter a From Email address first.")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("Sending...")

        try:
            response = self.api_client.post("/api/backup/offsite-replication/test-email/", {
                "recipient": recipient,
            })
            if isinstance(response, dict) and response.get('success'):
                QMessageBox.information(self, "Test Email", response.get('message', 'Test email sent successfully.'))
            else:
                err = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                category = response.get('error_category', '') if isinstance(response, dict) else ''
                hint = self._error_hint(category)
                QMessageBox.warning(self, "Test Failed", f"{err}\n\n{hint}")
        except Exception as e:
            QMessageBox.warning(self, "Test Failed", f"Failed: {e}")
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("Send Test Email")

    def _error_hint(self, category: str) -> str:
        hints = {
            'auth_failure': 'Check your SMTP username and password. For Gmail, use an App Password.',
            'network_failure': 'Verify the SMTP host and port. Check your internet connection.',
            'smtp_misconfiguration': 'Check SMTP settings. Some providers require specific ports (465/587).',
            'timeout': 'Connection timed out. Check host, port, and firewall settings.',
        }
        return hints.get(category, 'Review your SMTP configuration and try again.')

    def _save_config(self):
        config = {
            'enabled': self.enabled_cb.isChecked(),
            'smtp_host': self.smtp_host.text().strip(),
            'smtp_port': int(self.smtp_port.text().strip() or 587),
            'smtp_user': self.smtp_user.text().strip(),
            'smtp_password': self.smtp_password.text().strip(),
            'from_email': self.from_email.text().strip(),
            'recipients': [r.strip() for r in self.recipients.text().split(',') if r.strip()],
            'smtp_use_tls': self.use_tls.isChecked(),
        }

        if config['enabled'] and not config['smtp_host']:
            QMessageBox.warning(self, "Save", "SMTP Host is required when email is enabled.")
            return

        try:
            response = self.api_client.post("/api/backup/offsite-replication/save-config/", config)
            if isinstance(response, dict) and response.get('success'):
                QMessageBox.information(self, "Save", "Configuration saved successfully.")
                self.accept()
            else:
                err = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                QMessageBox.warning(self, "Save Failed", f"Failed: {err}")
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Failed: {e}")

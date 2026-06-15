"""Email configuration dialog for backup offsite replication."""
from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QWidget, QHBoxLayout
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.constants import SPACING_SM


class EmailConfigDialog(EnterpriseDialog):
    """Edit backup email transport settings through the backend API."""

    def __init__(self, api_client=None, parent=None):
        self.api_client = api_client
        super().__init__("Email Backup Configuration", DialogType.CUSTOM, parent)
        self.setMinimumWidth(520)
        self._build_content()
        self._load_config()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget(self)
        root = QVBoxLayout(widget)
        root.setSpacing(SPACING_SM)

        form = QFormLayout()
        self.host = QLineEdit()
        self.port = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.sender = QLineEdit()
        self.recipients = QLineEdit()
        self.use_tls = QCheckBox("Use TLS")

        form.addRow("SMTP Host:", self.host)
        form.addRow("SMTP Port:", self.port)
        form.addRow("Username:", self.username)
        form.addRow("Password:", self.password)
        form.addRow("Sender:", self.sender)
        form.addRow("Recipients:", self.recipients)
        form.addRow("", self.use_tls)
        root.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        save = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save_config)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self.set_content(widget)

    def _load_config(self):
        if not self.api_client:
            return
        self.run_api_request(
            "email_config:load",
            "GET",
            "/api/backup/offsite-replication/email-config/",
            on_success=self._apply_config,
            on_error=lambda _message: None,
        )

    def _apply_config(self, response):
        if not isinstance(response, dict):
            return
        data = response.get("data", response)
        if not isinstance(data, dict):
            return
        self.host.setText(str(data.get("smtp_host", data.get("host", "")) or ""))
        self.port.setText(str(data.get("smtp_port", data.get("port", "")) or ""))
        self.username.setText(str(data.get("username", "") or ""))
        self.sender.setText(str(data.get("sender", data.get("from_email", "")) or ""))
        recipients = data.get("recipients", data.get("to_emails", ""))
        if isinstance(recipients, list):
            recipients = ",".join(recipients)
        self.recipients.setText(str(recipients or ""))
        self.use_tls.setChecked(bool(data.get("use_tls", True)))

    def _payload(self):
        return {
            "smtp_host": self.host.text().strip(),
            "smtp_port": self.port.text().strip(),
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "sender": self.sender.text().strip(),
            "recipients": [x.strip() for x in self.recipients.text().split(",") if x.strip()],
            "use_tls": self.use_tls.isChecked(),
        }

    def _save_config(self):
        if not self.api_client:
            AlertDialog.warning("Email Config", "API client not available.", self)
            return
        self.run_api_request(
            "email_config:save",
            "POST",
            "/api/backup/offsite-replication/email-config/",
            data=self._payload(),
            on_success=self._on_saved,
            on_error=lambda message: AlertDialog.error("Email Config", f"Save failed: {message}", self),
        )

    def _on_saved(self, response):
        if isinstance(response, dict) and not response.get("success", True):
            AlertDialog.error("Email Config", str(response.get("error", "Save failed")), self)
            return
        AlertDialog.info("Email Config", "Email configuration saved.", self)
        self.accept()

"""TOTP 2FA Setup Dialog — scan QR code and verify first code."""

import base64
from io import BytesIO

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                 QLineEdit, QPushButton, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap

from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.constants import (
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL,
    TEXT_SECTION_TITLE, TEXT_BODY, TEXT_CARD_TITLE, TEXT_LABEL, TEXT_HELPER,
    BORDER_RADIUS_LG,
    COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BG_SURFACE, COLOR_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    COLOR_PRIMARY, COLOR_DANGER, COLOR_SUCCESS,
)
from api.client import APIClient
from utils.logger import get_logger

log = get_logger('auth')


class TOTPSetupDialog(QDialog):
    """Dialog to set up TOTP 2FA: show QR code, enter verification code."""

    setup_complete = Signal()

    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client or APIClient()
        self.setWindowTitle("Set Up Two-Factor Authentication")
        self.setFixedSize(450, 550)
        self.setModal(True)
        self.setup_ui()
        self._load_qr_code()

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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XXL, SPACING_XXL, SPACING_XXL, SPACING_XXL)
        layout.setSpacing(SPACING_LG)

        # Title
        title = QLabel("🔐 Two-Factor Authentication")
        title.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "1. Scan the QR code with your authenticator app\n"
            "2. Enter the 6-digit code below to verify"
        )
        instructions.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}px;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)

        # QR code display
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG};")
        layout.addWidget(self.qr_label)

        # Manual secret (fallback)
        self.secret_label = QLabel("")
        self.secret_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_HELPER}px; font-family: monospace;")
        self.secret_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.secret_label)

        # Verification code input
        code_label = QLabel("Verification Code")
        code_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(code_label)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter 6-digit code")
        self.code_input.setMaxLength(6)
        self.code_input.setFixedHeight(48)
        self.code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_input.setStyleSheet(f"font-size: {TEXT_CARD_TITLE}pt; letter-spacing: 8px;")
        self.code_input.returnPressed.connect(self._verify_code)
        layout.addWidget(self.code_input)

        # Verify button
        self.verify_btn = EnterpriseButton(text="Verify & Enable", variant=ButtonVariant.PRIMARY, size=ButtonSize.LARGE)
        self.verify_btn.clicked.connect(self._verify_code)
        layout.addWidget(self.verify_btn)

        # Status message
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_HELPER}px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Cancel button
        cancel_btn = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _load_qr_code(self):
        """Fetch TOTP setup data from backend."""
        try:
            result = self.api_client.post("/api/auth/totp/setup/", {})
            if result.get("success"):
                data = result.get("data", {})
                qr_b64 = data.get("qr_code_base64", "")
                secret = data.get("secret", "")

                if qr_b64:
                    img_data = base64.b64decode(qr_b64)
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    scaled = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.qr_label.setPixmap(scaled)

                self.secret_label.setText(f"Manual secret: {secret}")
            else:
                self._show_error("Failed to generate TOTP setup")
        except Exception as e:
            self._show_error(f"Connection error: {e}")

    def _verify_code(self):
        """Verify the entered TOTP code."""
        code = self.code_input.text().strip()
        if len(code) != 6 or not code.isdigit():
            self._show_error("Enter a valid 6-digit code")
            return

        self.verify_btn.setEnabled(False)
        self.verify_btn.setText("Verifying...")

        try:
            result = self.api_client.post("/api/auth/totp/verify/", {"code": code})
            self.verify_btn.setEnabled(True)
            self.verify_btn.setText("Verify & Enable")

            if result.get("success"):
                QMessageBox.information(self, "Success", "Two-factor authentication is now enabled!")
                self.setup_complete.emit()
                self.accept()
            else:
                self._show_error(result.get("error", {}).get("message", "Invalid code"))
        except Exception as e:
            self.verify_btn.setEnabled(True)
            self.verify_btn.setText("Verify & Enable")
            self._show_error(f"Connection error: {e}")

    def _show_error(self, msg: str):
        self.status_label.setText(msg)
        self.status_label.setVisible(True)

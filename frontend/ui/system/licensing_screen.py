from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                               QFormLayout, QFileDialog, QMessageBox, QPushButton)
from PySide6.QtCore import Qt, QTimer
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_LG, SPACING_MD, TEXT_PAGE_TITLE, TEXT_CARD_TITLE,
                           TEXT_BODY, TEXT_LABEL, COLOR_TEXT_PRIMARY, COLOR_SUCCESS,
                           COLOR_DANGER, COLOR_WARNING, COLOR_INFO, BORDER_RADIUS_MD,
                           COLOR_BG_ELEVATED, COLOR_BORDER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from api.client import APIClient


MODE_STYLES = {
    "dev": (COLOR_INFO, "DEV MODE"),
    "trial": (COLOR_WARNING, "TRIAL"),
    "limited": (COLOR_DANGER, "EXPIRED"),
    "licensed": (COLOR_SUCCESS, "LICENSED"),
}


class LicensingScreen(BaseScreen):
    """License management screen — shows mode, days left, import + fingerprint."""

    def __init__(self, parent=None, screen_id="licensing", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api = api_client or APIClient()
        self._state = {"mode": "unknown"}
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_LG)

        title = QLabel("License Management")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(title)

        # ── Status Group ──────────────────────────────────────
        status_group = QGroupBox("License Status")
        status_layout = QFormLayout(status_group)

        self.mode_label = QLabel("—")
        self.mode_label.setStyleSheet(f"font-size: {TEXT_CARD_TITLE}pt; font-weight: 700;")
        status_layout.addRow("Mode:", self.mode_label)

        self.days_label = QLabel("—")
        status_layout.addRow("Days Remaining:", self.days_label)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}pt;")
        status_layout.addRow("Message:", self.message_label)

        layout.addWidget(status_group)

        # ── Device Group ──────────────────────────────────────
        device_group = QGroupBox("Device Information")
        device_layout = QFormLayout(device_group)

        self.fingerprint_label = QLabel("—")
        self.fingerprint_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.fingerprint_label.setStyleSheet(f"font-size: {TEXT_LABEL}pt;")
        device_layout.addRow("Device ID:", self.fingerprint_label)

        self.os_label = QLabel("—")
        device_layout.addRow("OS:", self.os_label)

        layout.addWidget(device_group)

        # ── Actions ───────────────────────────────────────────
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)

        self.import_btn = EnterpriseButton(
            "Import License File", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM
        )
        self.import_btn.clicked.connect(self._import_license)
        actions_layout.addWidget(self.import_btn)

        self.fingerprint_btn = EnterpriseButton(
            "View Device Fingerprint", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM
        )
        self.fingerprint_btn.clicked.connect(self._show_fingerprint)
        actions_layout.addWidget(self.fingerprint_btn)

        layout.addWidget(actions_group)
        layout.addStretch()

        # Refresh timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(60000)

    def _refresh(self):
        try:
            resp = self._api.get("/api/licensing/info/")
            if resp and resp.get("success"):
                self._state = resp.get("data", {})
            self._update_display()
        except Exception:
            self.mode_label.setText("OFFLINE")
            self.mode_label.setStyleSheet(f"font-size: {TEXT_CARD_TITLE}pt; font-weight: 700; color: {COLOR_DANGER};")

    def _update_display(self):
        mode = self._state.get("mode", "unknown")
        color, label = MODE_STYLES.get(mode, (COLOR_DANGER, mode.upper()))

        self.mode_label.setText(label)
        self.mode_label.setStyleSheet(f"font-size: {TEXT_CARD_TITLE}pt; font-weight: 700; color: {color};")

        days = self._state.get("days_remaining")
        self.days_label.setText(str(days) if days is not None else "—")
        self.days_label.setStyleSheet(f"color: {COLOR_WARNING if days is not None and days <= 3 else COLOR_TEXT_PRIMARY};")

        self.message_label.setText(self._state.get("message", ""))
        self.fingerprint_label.setText(self._state.get("device_id", self._state.get("device_fingerprint", "—")))

    def _import_license(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select License File", "", "License files (*.lic);;All files (*.*)"
        )
        if not path:
            return
        try:
            resp = self._api.post("/api/licensing/import-license/", data={"file_path": path})
            if resp and resp.get("success"):
                QMessageBox.information(self, "Success", resp.get("message", "License activated"))
                self._refresh()
            else:
                msg = (resp or {}).get("error", "Import failed")
                QMessageBox.warning(self, "Error", msg)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _show_fingerprint(self):
        fp = self._state.get("device_id", self.fingerprint_label.text())
        QMessageBox.information(self, "Device Fingerprint",
                                f"Device ID:\n{fp}\n\n"
                                "This identifies your device for license binding.")

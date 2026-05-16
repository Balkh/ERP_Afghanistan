from PySide6.QtWidgets import (QVBoxLayout, QLabel, QLineEdit, QGroupBox, QFormLayout, QMessageBox)
from PySide6.QtCore import Qt
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_HELPER,
                           BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, BORDER_RADIUS_MD,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from api.client import APIClient

class LicensingScreen(BaseScreen):
    """Screen for managing ERP license and device registration."""
    
    def __init__(self, parent=None, screen_id="licensing", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client or APIClient()
        self._setup_ui()
        self.load_license_info()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_LG)

        # Header
        title_label = QLabel("License Management")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(title_label)

        # Device Info Group
        device_group = QGroupBox("Device Information")
        device_layout = QFormLayout(device_group)
        
        self.device_id_label = QLabel("Loading...")
        self.device_id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        device_layout.addRow("Unique Device ID:", self.device_id_label)
        
        self.os_label = QLabel("Loading...")
        device_layout.addRow("Operating System:", self.os_label)
        
        layout.addWidget(device_group)

        # License Status Group
        status_group = QGroupBox("Current License Status")
        status_layout = QFormLayout(status_group)
        
        self.status_label = QLabel("Unknown")
        self.status_label.setStyleSheet(f"font-size: {TEXT_CARD_TITLE}pt; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        status_layout.addRow("Status:", self.status_label)
        
        self.expiry_label = QLabel("N/A")
        status_layout.addRow("Expiry Date:", self.expiry_label)
        
        self.version_label = QLabel("Enterprise Edition")
        status_layout.addRow("Version:", self.version_label)
        
        layout.addWidget(status_group)

        # Activate New License
        activate_group = QGroupBox("Activate License")
        activate_layout = QVBoxLayout(activate_group)
        
        activate_layout.addWidget(QLabel("Enter your license key below to activate the system:"))
        
        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText("Enter license key...")
        self.license_key_input.setMinimumHeight(INPUT_HEIGHT_MD)
        activate_layout.addWidget(QLabel("License Key:"))
        activate_layout.addWidget(self.license_key_input)
        
        self.activate_btn = EnterpriseButton(text="Activate System", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.activate_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; font-weight: bold;")
        self.activate_btn.clicked.connect(self.activate_license)
        activate_layout.addWidget(self.activate_btn)
        
        layout.addWidget(activate_group)
        layout.addStretch()

    def load_license_info(self):
        try:
            response = self._api_client.get("/api/licensing/info/")
            if response and response.get('success'):
                data = response.get('data', {})
                self.device_id_label.setText(data.get('device_id', 'N/A'))
                self.os_label.setText(data.get('os_info', 'N/A'))
                
                status = data.get('license_status', 'Invalid')
                self.status_label.setText(status)
                if status == 'Active':
                    self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
                else:
                    self.status_label.setStyleSheet(f"color: {COLOR_DANGER};")
                    
                self.expiry_label.setText(data.get('expiry_date', 'Lifetime'))
        except Exception as e:
            print(f"Failed to load license info: {e}")

    def activate_license(self):
        key = self.license_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Validation", "Please enter a license key.")
            return
            
        try:
            response = self._api_client.post("/api/licensing/validate/", {"license_key": key})
            if response and response.get('success'):
                QMessageBox.information(self, "Success", "License activated successfully! Please restart the application.")
                self.load_license_info()
            else:
                error_msg = response.get('error', 'Activation failed.')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Activation failed.')
                QMessageBox.critical(self, "Error", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"API Error: {e}")

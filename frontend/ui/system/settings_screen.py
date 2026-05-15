"""Settings screen for ERP."""
import json
import os
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit, QComboBox, QGroupBox,
                                  QFormLayout, QCheckBox, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_HELPER,
                           BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD,
                           BORDER_RADIUS_MD,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize


SETTINGS_FILE = os.path.expanduser("~/.pharmacy_erp_settings.json")


class SettingsScreen(BaseScreen):
    """Settings screen with application configuration."""
    
    def __init__(self, parent=None, screen_id="settings", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from local file."""
        self._settings = {
            "company_name": "",
            "currency": "AFN - Afghani",
            "language": "English",
            "timezone": "Asia/Kabul (GMT+4:30)",
            "low_stock_threshold": 10,
            "auto_backup": True,
            "backup_frequency": "Daily",
            "email_notifications": False,
            "low_stock_alerts": True,
            "expiry_alerts": True
        }
        
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded = json.load(f)
                    self._settings.update(loaded)
            except:
                pass
    
    def _save_settings(self):
        """Save settings to local file."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save settings: {e}")
            return False
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)
        
        title_label = QLabel("Settings")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(title_label)
        
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()
        
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("Enter company name")
        self.company_name.setMinimumHeight(INPUT_HEIGHT_MD)
        self.company_name.setText(self._settings.get("company_name", ""))
        
        self.currency = QComboBox()
        self.currency.addItems(["AFN - Afghani", "USD - US Dollar", "EUR - Euro", "PKR - Pakistani Rupee"])
        self.currency.setCurrentText(self._settings.get("currency", "AFN - Afghani"))
        
        self.language = QComboBox()
        self.language.addItems(["English", "Dari", "Pashto"])
        self.language.setCurrentText(self._settings.get("language", "English"))
        
        self.timezone = QComboBox()
        self.timezone.addItems(["Asia/Kabul (GMT+4:30)", "UTC (GMT+0:00)", "Asia/Dubai (GMT+4)"])
        self.timezone.setCurrentText(self._settings.get("timezone", "Asia/Kabul (GMT+4:30)"))
        
        general_layout.addRow("Company Name:", self.company_name)
        general_layout.addRow("Currency:", self.currency)
        general_layout.addRow("Language:", self.language)
        general_layout.addRow("Timezone:", self.timezone)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        inventory_group = QGroupBox("Inventory Settings")
        inventory_layout = QFormLayout()
        
        self.low_stock_threshold = QSpinBox()
        self.low_stock_threshold.setRange(1, 1000)
        self.low_stock_threshold.setValue(self._settings.get("low_stock_threshold", 10))
        
        self.auto_backup = QCheckBox("Enable automatic backup")
        self.auto_backup.setChecked(self._settings.get("auto_backup", True))
        
        self.backup_frequency = QComboBox()
        self.backup_frequency.addItems(["Daily", "Weekly", "Monthly"])
        self.backup_frequency.setCurrentText(self._settings.get("backup_frequency", "Daily"))
        
        inventory_layout.addRow("Low Stock Threshold:", self.low_stock_threshold)
        inventory_layout.addRow("Auto Backup:", self.auto_backup)
        inventory_layout.addRow("Backup Frequency:", self.backup_frequency)
        
        inventory_group.setLayout(inventory_layout)
        layout.addWidget(inventory_group)
        
        notification_group = QGroupBox("Notifications")
        notification_layout = QFormLayout()
        
        self.email_notifications = QCheckBox("Enable email notifications")
        self.email_notifications.setChecked(self._settings.get("email_notifications", False))
        
        self.low_stock_alerts = QCheckBox("Low stock alerts")
        self.low_stock_alerts.setChecked(self._settings.get("low_stock_alerts", True))
        
        self.expiry_alerts = QCheckBox("Batch expiry alerts")
        self.expiry_alerts.setChecked(self._settings.get("expiry_alerts", True))
        
        notification_layout.addRow("Email:", self.email_notifications)
        notification_layout.addRow("Stock Alerts:", self.low_stock_alerts)
        notification_layout.addRow("Expiry Alerts:", self.expiry_alerts)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        
        save_button = EnterpriseButton(text="Save Settings", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_button.clicked.connect(self.save_settings)
        
        reset_button = EnterpriseButton(text="Reset to Defaults", variant=ButtonVariant.WARNING, size=ButtonSize.MEDIUM)
        reset_button.clicked.connect(self.reset_settings)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def save_settings(self):
        """Save settings to local file."""
        self._settings["company_name"] = self.company_name.text()
        self._settings["currency"] = self.currency.currentText()
        self._settings["language"] = self.language.currentText()
        self._settings["timezone"] = self.timezone.currentText()
        self._settings["low_stock_threshold"] = self.low_stock_threshold.value()
        self._settings["auto_backup"] = self.auto_backup.isChecked()
        self._settings["backup_frequency"] = self.backup_frequency.currentText()
        self._settings["email_notifications"] = self.email_notifications.isChecked()
        self._settings["low_stock_alerts"] = self.low_stock_alerts.isChecked()
        self._settings["expiry_alerts"] = self.expiry_alerts.isChecked()
        
        if self._save_settings():
            QMessageBox.information(self, "Settings", "Settings saved successfully!")
        else:
            QMessageBox.warning(self, "Settings", "Failed to save settings. Please check permissions.")
    
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.company_name.clear()
            self.currency.setCurrentIndex(0)
            self.language.setCurrentIndex(0)
            self.timezone.setCurrentIndex(0)
            self.low_stock_threshold.setValue(10)
            self.auto_backup.setChecked(True)
            self.backup_frequency.setCurrentIndex(0)
            self.email_notifications.setChecked(False)
            self.low_stock_alerts.setChecked(True)
            self.expiry_alerts.setChecked(True)
            self._settings = {
                "company_name": "",
                "currency": "AFN - Afghani",
                "language": "English",
                "timezone": "Asia/Kabul (GMT+4:30)",
                "low_stock_threshold": 10,
                "auto_backup": True,
                "backup_frequency": "Daily",
                "email_notifications": False,
                "low_stock_alerts": True,
                "expiry_alerts": True
            }
            self._save_settings()
            QMessageBox.information(self, "Settings", "Settings reset to defaults.")
    
    def on_show(self):
        """Called when screen is shown."""
        pass
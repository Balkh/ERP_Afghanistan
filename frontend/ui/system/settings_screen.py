"""Settings screen for ERP."""
import json
import os
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                   QLabel, QComboBox, QGroupBox, QFormLayout,
                                   QCheckBox, QSpinBox, QMessageBox)
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, TEXT_PAGE_TITLE, INPUT_HEIGHT_MD, COLOR_TEXT_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from theme.theme_engine import ThemeEngine


SETTINGS_FILE = os.path.expanduser("~/.pharmacy_erp_settings.json")

THEME_KEYS = ["theme", "language", "timezone", "low_stock_threshold",
              "auto_backup", "backup_frequency", "email_notifications",
              "low_stock_alerts", "expiry_alerts"]


class SettingsScreen(BaseScreen):
    """Settings screen with application configuration."""
    
    def __init__(self, parent=None, screen_id="settings", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._company_id = None  # Cached to avoid redundant API calls
        self._load_settings()
    
    def _load_settings(self):
        """Load settings — SystemConfig API is primary SSOT, local JSON is cache, defaults are final fallback."""
        # Try API first (SSOT). If it fails, try local cache. Defaults fill remaining gaps.
        self._settings = {}
        api_ok = self._load_from_api()
        if not api_ok:
            self._load_from_local_cache()
        self._apply_defaults()

    def _get_default_settings(self):
        """Return default settings dict (used as fallback when no API or cache available)."""
        return {
            "theme": "dark",
            "language": "English",
            "timezone": "Asia/Kabul (GMT+4:30)",
            "currency": "AFN",
            "low_stock_threshold": 10,
            "auto_backup": True,
            "backup_frequency": "Daily",
            "email_notifications": False,
            "low_stock_alerts": True,
            "expiry_alerts": True
        }

    def _apply_defaults(self):
        """Apply default values for any settings not already populated."""
        defaults = self._get_default_settings()
        for key, val in defaults.items():
            if self._settings.get(key) is None:
                self._settings[key] = val

    def _load_from_api(self):
        """Load settings from SystemConfig API as primary SSOT. Returns True on success."""
        if not self._api_client:
            return False
        try:
            resp = self._api_client.get("/api/system-config/by_keys/", params={"keys": THEME_KEYS})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    data = data["data"]
                self._merge_api_data(data)

            # Also load company default currency from Company API (SSOT)
            self._load_company_currency()
            return True
        except Exception as e:
            print(f"Failed to load settings from API: {e}")
        return False

    def _load_company_currency(self):
        """Load company default_currency from Company API."""
        if not self._api_client:
            return
        try:
            # Use /active/ endpoint which returns full company data including id
            resp = self._api_client.get("/api/core/companies/active/")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    data = data.get("data", data)
                self._company_id = data.get("id")
                currency = data.get("default_currency", "AFN")
                self._settings["currency"] = currency
            else:
                # Fallback to config endpoint (id not returned, but has currency)
                resp2 = self._api_client.get("/api/core/companies/config/")
                if resp2.status_code == 200:
                    data = resp2.json()
                    if data.get("success"):
                        data = data.get("data", data)
                    currency = data.get("default_currency", "AFN")
                    self._settings["currency"] = currency
        except Exception as e:
            print(f"Failed to load company currency: {e}")

    def _load_from_local_cache(self):
        """Load settings from local JSON cache file (fallback when API is unavailable)."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded = json.load(f)
                for key, val in loaded.items():
                    if key == "low_stock_threshold":
                        try:
                            self._settings[key] = int(val)
                        except (ValueError, TypeError):
                            pass
                    elif key in ("auto_backup", "email_notifications", "low_stock_alerts", "expiry_alerts"):
                        self._settings[key] = str(val).lower() in ("true", "1", "yes")
                    else:
                        self._settings[key] = val
            except Exception:
                pass

    def _merge_api_data(self, data):
        """Merge API response data into settings dict."""
        for key in THEME_KEYS:
            val = data.get(key)
            if val is not None:
                if key == "low_stock_threshold":
                    try:
                        self._settings[key] = int(val)
                    except (ValueError, TypeError):
                        pass
                elif key in ("auto_backup", "email_notifications", "low_stock_alerts", "expiry_alerts"):
                    self._settings[key] = str(val).lower() in ("true", "1", "yes")
                else:
                    self._settings[key] = val
    
    def _save_settings(self):
        """Save settings to local cache file (secondary). SystemConfig API is SSOT."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save settings: {e}")
            return False
    
    def _load_theme_from_api(self):
        """Load theme preference from backend SystemConfig. Called from on_show() to refresh."""
        self._load_from_api()
    
    def _save_theme_to_api(self):
        """Save settings to backend SystemConfig."""
        if not self._api_client:
            return False
        try:
            payload = {}
            for key in THEME_KEYS:
                payload[key] = self._settings.get(key, "")
            resp = self._api_client.post("/api/system-config/bulk_update/", json=payload)
            return resp.status_code in (200, 201)
        except Exception as e:
            print(f"Failed to save settings to API: {e}")
            return False
    
    def _apply_theme(self):
        """Apply the current theme from settings."""
        theme = self._settings.get("theme", "dark")
        engine = ThemeEngine.instance()
        engine.apply_theme(theme)
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)
        
        title_label = QLabel("Settings")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(title_label)
        
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        current_theme = self._settings.get("theme", "dark")
        self.theme_combo.setCurrentText(current_theme.capitalize())
        
        self.language = QComboBox()
        self.language.addItems(["English", "Dari", "Pashto"])
        self.language.setCurrentText(self._settings.get("language", "English"))
        
        self.timezone = QComboBox()
        self.timezone.addItems(["Asia/Kabul (GMT+4:30)", "UTC (GMT+0:00)", "Asia/Dubai (GMT+4)"])
        self.timezone.setCurrentText(self._settings.get("timezone", "Asia/Kabul (GMT+4:30)"))

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["AFN", "USD", "EUR", "PKR", "IRR"])
        self.currency_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        
        general_layout.addRow("Theme:", self.theme_combo)
        general_layout.addRow("Language:", self.language)
        general_layout.addRow("Timezone:", self.timezone)
        general_layout.addRow("Currency:", self.currency_combo)
        
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
        """Save settings to local file and backend API."""
        self._settings["theme"] = self.theme_combo.currentText().lower()
        self._settings["language"] = self.language.currentText()
        self._settings["timezone"] = self.timezone.currentText()
        self._settings["currency"] = self.currency_combo.currentText()
        self._settings["low_stock_threshold"] = self.low_stock_threshold.value()
        self._settings["auto_backup"] = self.auto_backup.isChecked()
        self._settings["backup_frequency"] = self.backup_frequency.currentText()
        self._settings["email_notifications"] = self.email_notifications.isChecked()
        self._settings["low_stock_alerts"] = self.low_stock_alerts.isChecked()
        self._settings["expiry_alerts"] = self.expiry_alerts.isChecked()
        
        local_ok = self._save_settings()
        api_ok = self._save_theme_to_api()
        __currency_ok = self._save_company_currency()
        
        self._apply_theme()
        
        if local_ok or api_ok:
            QMessageBox.information(self, "Settings", "Settings saved successfully!")
        else:
            QMessageBox.warning(self, "Settings", "Failed to save settings. Please check permissions.")

    def _save_company_currency(self):
        """Save default_currency to Company API (SSOT)."""
        if not self._api_client:
            return False
        try:
            # Use cached company_id or fetch it
            company_id = self._company_id
            if not company_id:
                self._load_company_currency()
                company_id = self._company_id
            if company_id:
                payload = {"default_currency": self.currency_combo.currentText()}
                resp = self._api_client.put(f"/api/core/companies/{company_id}/", payload)
                return resp.status_code in (200, 201)
            return False
        except Exception as e:
            print(f"Failed to save company currency: {e}")
            return False
    
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.theme_combo.setCurrentIndex(0)
            self.language.setCurrentIndex(0)
            self.timezone.setCurrentIndex(0)
            self.currency_combo.setCurrentIndex(0)
            self.low_stock_threshold.setValue(10)
            self.auto_backup.setChecked(True)
            self.backup_frequency.setCurrentIndex(0)
            self.email_notifications.setChecked(False)
            self.low_stock_alerts.setChecked(True)
            self.expiry_alerts.setChecked(True)
            self._settings = {
                "theme": "dark",
                "language": "English",
                "timezone": "Asia/Kabul (GMT+4:30)",
                "currency": "AFN",
                "low_stock_threshold": 10,
                "auto_backup": True,
                "backup_frequency": "Daily",
                "email_notifications": False,
                "low_stock_alerts": True,
                "expiry_alerts": True
            }
            self._save_settings()
            # Also reset company currency
            if self._api_client:
                try:
                    company_id = self._company_id
                    if not company_id:
                        self._load_company_currency()
                        company_id = self._company_id
                    if company_id:
                        self._api_client.put(f"/api/core/companies/{company_id}/", {"default_currency": "AFN"})
                except Exception:
                    pass
            self._apply_theme()
            QMessageBox.information(self, "Settings", "Settings reset to defaults.")
    
    def on_show(self):
        """Called when screen is shown."""
        self._load_theme_from_api()  # Also loads company currency via _load_company_currency()
        current_theme = self._settings.get("theme", "dark")
        self.theme_combo.setCurrentText(current_theme.capitalize())
        currency = self._settings.get("currency", "AFN")
        idx = self.currency_combo.findText(currency)
        if idx >= 0:
            self.currency_combo.setCurrentIndex(idx)
        self._apply_theme()

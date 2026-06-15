"""Settings screen for ERP."""
import json
import os
from utils.atomic_io import atomic_write_json
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                   QLabel, QComboBox, QGroupBox, QFormLayout,
                                   QCheckBox, QSpinBox)
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, TEXT_PAGE_TITLE, INPUT_HEIGHT_MD, COLOR_TEXT_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog, ConfirmDialog
from ui.components.forms import FormSection
from theme.theme_engine import ThemeEngine


SETTINGS_FILE = os.path.expanduser("~/.pharmacy_erp_settings.json")

THEME_KEYS = ["theme", "language", "timezone", "low_stock_threshold",
              "auto_backup", "backup_frequency", "email_notifications",
              "low_stock_alerts", "expiry_alerts", "date_format"]


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
            "expiry_alerts": True,
            "date_format": "gregorian"
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
            if isinstance(resp, dict) and resp.get("success"):
                data = resp.get("data", resp)
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
            if isinstance(resp, dict) and resp.get("success"):
                data = resp.get("data", resp)
                self._company_id = data.get("id")
                currency = data.get("default_currency", "AFN")
                self._settings["currency"] = currency
            else:
                # Fallback to config endpoint (id not returned, but has currency)
                resp2 = self._api_client.get("/api/core/companies/config/")
                if isinstance(resp2, dict) and resp2.get("success"):
                    data = resp2.get("data", resp2)
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
            atomic_write_json(SETTINGS_FILE, self._settings, indent=2)
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
            return isinstance(resp, dict) and resp.get("success")
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
        
        general_section = FormSection("General Settings")
        
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

        self.date_format_combo = QComboBox()
        self.date_format_combo.addItems(["Gregorian", "Jalali (Shamsi)"])
        date_fmt = self._settings.get("date_format", "gregorian")
        self.date_format_combo.setCurrentText("Jalali (Shamsi)" if date_fmt == "shamsi" else "Gregorian")
        self.date_format_combo.setMinimumHeight(INPUT_HEIGHT_MD)

        general_section.add_field(self.theme_combo, "Theme:")
        general_section.add_field(self.language, "Language:")
        general_section.add_field(self.timezone, "Timezone:")
        general_section.add_field(self.currency_combo, "Currency:")
        general_section.add_field(self.date_format_combo, "Date Format:")
        layout.addWidget(general_section)
        
        inventory_section = FormSection("Inventory Settings")
        
        self.low_stock_threshold = QSpinBox()
        self.low_stock_threshold.setRange(1, 1000)
        self.low_stock_threshold.setValue(self._settings.get("low_stock_threshold", 10))
        
        self.auto_backup = QCheckBox("Enable automatic backup")
        self.auto_backup.setChecked(self._settings.get("auto_backup", True))
        
        self.backup_frequency = QComboBox()
        self.backup_frequency.addItems(["Daily", "Weekly", "Monthly"])
        self.backup_frequency.setCurrentText(self._settings.get("backup_frequency", "Daily"))
        
        inventory_section.add_field(self.low_stock_threshold, "Low Stock Threshold:")
        inventory_section.add_field(self.auto_backup, "Auto Backup:")
        inventory_section.add_field(self.backup_frequency, "Backup Frequency:")
        layout.addWidget(inventory_section)
        
        notification_section = FormSection("Notifications")
        
        self.email_notifications = QCheckBox("Enable email notifications")
        self.email_notifications.setChecked(self._settings.get("email_notifications", False))
        
        self.low_stock_alerts = QCheckBox("Low stock alerts")
        self.low_stock_alerts.setChecked(self._settings.get("low_stock_alerts", True))
        
        self.expiry_alerts = QCheckBox("Batch expiry alerts")
        self.expiry_alerts.setChecked(self._settings.get("expiry_alerts", True))
        
        notification_section.add_field(self.email_notifications, "Email:")
        notification_section.add_field(self.low_stock_alerts, "Stock Alerts:")
        notification_section.add_field(self.expiry_alerts, "Expiry Alerts:")
        layout.addWidget(notification_section)
        
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
        self._settings["date_format"] = "shamsi" if self.date_format_combo.currentText() == "Jalali (Shamsi)" else "gregorian"
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
            AlertDialog.info("Settings", "Settings saved successfully!", self)
        else:
            AlertDialog.warning("Settings", "Failed to save settings. Please check permissions.", self)

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
                return isinstance(resp, dict) and resp.get("success")
            return False
        except Exception as e:
            print(f"Failed to save company currency: {e}")
            return False
    
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = ConfirmDialog.confirm(
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            self,
        )
        
        if reply:
            self.theme_combo.setCurrentIndex(0)
            self.language.setCurrentIndex(0)
            self.timezone.setCurrentIndex(0)
            self.currency_combo.setCurrentIndex(0)
            self.date_format_combo.setCurrentIndex(0)
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
                "expiry_alerts": True,
                "date_format": "gregorian"
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
            AlertDialog.info("Settings", "Settings reset to defaults.", self)
    
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

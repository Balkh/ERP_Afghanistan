"""
Centralized Settings Manager
Provides a unified interface for application settings.
"""

import os
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path

class SettingsManager:
    """Manages application settings from multiple sources."""
    
    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize the settings manager.
        
        Args:
            settings_file: Path to a JSON settings file. If None, looks for 'settings.json' in the config directory.
        """
        self._settings: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {
            "app": {
                "name": "Pharmacy ERP",
                "version": "1.0.0",
                "debug": False
            },
            "ui": {
                "theme": "dark",
                "language": "fa"
            },
            "currency": {
                "default": "AFN",
                "exchange_rates": {
                    "AFN_to_USD": 0.012,
                    "USD_to_AFN": 83.33
                }
            },
            "backup": {
                "enabled": True,
                "retention_days": 30,
                "auto_backup": True
            },
            "database": {
                "type": "sqlite",
                "path": "db.sqlite3"
            }
        }
        
        # Load defaults first
        self._settings = self._defaults.copy()
        
        # Then load from file if provided or found
        if settings_file is None:
            # Look for settings.json in the config directory
            config_dir = Path(__file__).parent.parent.parent.parent / "config"
            settings_file = config_dir / "settings.json"
        
        if settings_file and os.path.exists(settings_file):
            self.load_from_file(settings_file)
        
        # Finally, override with environment variables
        self._load_from_env()
    
    def load_from_file(self, file_path: Union[str, Path]) -> None:
        """
        Load settings from a JSON file.
        
        Args:
            file_path: Path to the JSON settings file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_settings = json.load(f)
            self._deep_update(self._settings, file_settings)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # If the file doesn't exist or is invalid, we keep the defaults
            # In a real application, you might want to log this
            pass
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save current settings to a JSON file.
        
        Args:
            file_path: Path where to save the settings file
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, indent=4, ensure_ascii=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key (using dot notation for nested keys).
        
        Args:
            key: Setting key (e.g., "app.name" or "currency.default")
            default: Default value if key is not found
            
        Returns:
            The setting value or default if not found
        """
        keys = key.split('.')
        value = self._settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value by key (using dot notation for nested keys).
        
        Args:
            key: Setting key (e.g., "app.name" or "currency.default")
            value: Value to set
        """
        keys = key.split('.')
        target = self._settings
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Set the value
        target[keys[-1]] = value
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively update a dictionary with another dictionary.
        
        Args:
            target: Dictionary to update
            source: Dictionary with updates
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _load_from_env(self) -> None:
        """Load settings from environment variables (with prefix 'PHARMACY_ERP_')."""
        prefix = "PHARMACY_ERP_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert environment variable key to settings key
                # Example: PHARMACY_ERP_APP_NAME -> app.name
                setting_key = key[len(prefix):].lower()
                # Replace double underscores with dots for nested settings
                # But be careful: we only want to replace __ with . and not single _
                # We'll split by __ and then join by .
                parts = setting_key.split('__')
                if len(parts) > 1:
                    setting_key = '.'.join(parts)
                else:
                    # If there's no __, we just use the key as is (but replace _ with . for nesting?)
                    # Actually, we want to support both: 
                    #   PHARMACY_ERP_APP_NAME -> app.name
                    #   PHARMACY_ERP_CURRENCY_DEFAULT -> currency.default
                    # So we replace every _ with . ? Not exactly, because we might have abbreviations.
                    # Instead, we'll use a simple approach: split by _ and then join by . 
                    # But that would turn APP_NAME into app.name (which is good) and CURRENCY_DEFAULT into currency.default (also good).
                    setting_key = '.'.join(parts[0].split('_')) if len(parts) == 1 else '.'.join(['_'.join(p.split('_')) for p in parts])
                    # Actually, let's do: replace every _ with . but then we have issues with words like "AFN" (no change) and "USD" (no change).
                    # We'll do: split the string by _ and then join by .
                    setting_key = '.'.join(setting_key.split('_'))
                
                # Try to convert the value to a proper type
                converted_value = self._convert_env_value(value)
                self.set(setting_key, converted_value)
    
    def _convert_env_value(self, value: str) -> Any:
        """
        Convert environment variable string to appropriate type.
        
        Args:
            value: String value from environment variable
            
        Returns:
            Converted value (bool, int, float, or string)
        """
        # Check for boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Check for integer
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass
        
        # Check for float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value

# Global settings instance
settings = SettingsManager()
"""
Example usage of the global settings system.
Demonstrates how to use the SettingsManager in application code.
"""

from .manager import settings

def demonstrate_settings_usage():
    """Show various ways to use the global settings system."""
    
    # Getting settings with dot notation
    app_name = settings.get("app.name")
    app_version = settings.get("app.version")
    debug_mode = settings.get("app.debug")
    
    print(f"Application: {app_name} v{app_version}")
    print(f"Debug mode: {debug_mode}")
    
    # Getting nested settings
    ui_theme = settings.get("ui.theme")
    ui_language = settings.get("ui.language")
    
    print(f"UI Theme: {ui_theme}")
    print(f"UI Language: {ui_language}")
    
    # Getting currency settings
    default_currency = settings.get("currency.default")
    afn_to_usd_rate = settings.get("currency.exchange_rates.AFN_to_USD")
    
    print(f"Default Currency: {default_currency}")
    print(f"AFN to USD Rate: {afn_to_usd_rate}")
    
    # Getting backup settings
    backup_enabled = settings.get("backup.enabled")
    retention_days = settings.get("backup.retention_days")
    
    print(f"Backup Enabled: {backup_enabled}")
    print(f"Retention Days: {retention_days}")
    
    # Getting database settings
    db_type = settings.get("database.type")
    db_path = settings.get("database.path")
    
    print(f"Database Type: {db_type}")
    print(f"Database Path: {db_path}")
    
    # Getting a non-existent setting with default
    nonexistent = settings.get("nonexistent.setting", "default_value")
    print(f"Non-existent setting (with default): {nonexistent}")
    
    # Setting a new setting (runtime override)
    settings.set("app.debug", True)
    print(f"After setting debug to True: {settings.get('app.debug')}")
    
    # Setting a nested setting
    settings.set("ui.custom_setting", "custom_value")
    print(f"Custom UI setting: {settings.get('ui.custom_setting')}")

if __name__ == "__main__":
    demonstrate_settings_usage()
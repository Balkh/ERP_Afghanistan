"""
DEPRECATED — Theme management system for ERP.
Use ``theme.theme_engine.ThemeEngine`` instead.
This module will be removed in a future release.
"""
import warnings
warnings.warn(
    "ui.theme.theme_manager is deprecated. Use theme.theme_engine.ThemeEngine instead.",
    DeprecationWarning,
    stacklevel=2,
)

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication
import json
import os


class ThemeManager(QObject):
    """DEPRECATED — Use theme.theme_engine.ThemeEngine instead."""
    
    theme_changed = Signal(str)  # Emits theme name when changed
    
    def __init__(self):
        super().__init__()
        self._current_theme = self.load_theme_preference()
        self._themes = {
            "light": self._create_light_theme(),
            "dark": self._create_dark_theme()
        }
        self.apply_theme(self._current_theme)
    
    def _create_light_theme(self):
        """Create light theme palette."""
        palette = QPalette()
        
        # Window
        palette.setColor(QPalette.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText, QColor(33, 33, 33))
        
        # Base
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.Text, QColor(33, 33, 33))
        
        # Button
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, QColor(33, 33, 33))
        
        # Highlight
        palette.setColor(QPalette.Highlight, QColor(33, 150, 243))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Disabled
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(117, 117, 117))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(117, 117, 117))
        
        return palette
    
    def _create_dark_theme(self):
        """Create dark theme palette."""
        palette = QPalette()
        
        # Window
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        
        # Base
        palette.setColor(QPalette.Base, QColor(42, 42, 42))
        palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        
        # Button
        palette.setColor(QPalette.Button, QColor(66, 66, 66))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        
        # Highlight
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Disabled
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
        
        return palette
    
    def apply_theme(self, theme_name):
        """Apply theme to application."""
        if theme_name in self._themes:
            QApplication.instance().setPalette(self._themes[theme_name])
            self._current_theme = theme_name
            self.save_theme_preference(theme_name)
            self.theme_changed.emit(theme_name)
    
    def get_current_theme(self):
        """Get current theme name."""
        return self._current_theme
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        new_theme = "dark" if self._current_theme == "light" else "light"
        self.apply_theme(new_theme)
    
    def load_theme_preference(self):
        """Load theme preference from persistent storage."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            theme_file = os.path.join(config_dir, "theme_preference.json")
            if os.path.exists(theme_file):
                with open(theme_file, 'r') as f:
                    data = json.load(f)
                    return data.get("theme", "light")
        except Exception:
            pass
        return "light"  # Default to light theme
    
    def save_theme_preference(self, theme_name):
        """Save theme preference to persistent storage."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            theme_file = os.path.join(config_dir, "theme_preference.json")
            with open(theme_file, 'w') as f:
                json.dump({"theme": theme_name}, f)
        except Exception:
            pass  # Silently fail if we can't save preference
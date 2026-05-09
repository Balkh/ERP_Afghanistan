from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

class ThemeManager(QObject):
    theme_changed = Signal(str)  # Emits the theme name when changed

    def __init__(self):
        super().__init__()
        self._current_theme = "light"
        self._themes = {
            "light": {
                "primary": QColor("#FF6B35"),  # Orange
                "secondary": QColor("#003366"), # Dark Blue
                "background": QColor("#FFFFFF"),
                "foreground": QColor("#212121"),
                "input_background": QColor("#F5F5F5"),
                "input_foreground": QColor("#212121"),
                "border": QColor("#E0E0E0"),
            },
            "dark": {
                "primary": QColor("#FF6B35"),  # Orange
                "secondary": QColor("#003366"), # Dark Blue
                "background": QColor("#212121"),
                "foreground": QColor("#FFFFFF"),
                "input_background": QColor("#424242"),
                "input_foreground": QColor("#FFFFFF"),
                "border": QColor("#616161"),
            }
        }

    def current_theme(self):
        return self._current_theme

    def set_theme(self, theme_name):
        if theme_name not in self._themes:
            raise ValueError(f"Unknown theme: {theme_name}")
        self._current_theme = theme_name
        self.apply_theme(theme_name)
        self.theme_changed.emit(theme_name)

    def apply_theme(self, theme_name):
        """Apply the theme to the QApplication instance."""
        if theme_name not in self._themes:
            return

        theme = self._themes[theme_name]
        app = QApplication.instance()
        if app is None:
            return

        palette = QPalette()

        # Set color roles
        palette.setColor(QPalette.Window, theme["background"])
        palette.setColor(QPalette.WindowText, theme["foreground"])
        palette.setColor(QPalette.Base, theme["input_background"])
        palette.setColor(QPalette.AlternateBase, theme["background"])
        palette.setColor(QPalette.ToolTipBase, theme["foreground"])
        palette.setColor(QPalette.ToolTipText, theme["foreground"])
        palette.setColor(QPalette.Text, theme["foreground"])
        palette.setColor(QPalette.Button, theme["input_background"])
        palette.setColor(QPalette.ButtonText, theme["foreground"])
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, theme["primary"])
        palette.setColor(QPalette.Highlight, theme["primary"])
        palette.setColor(QPalette.HighlightedText, Qt.white)

        app.setPalette(palette)

        # Also set the stylesheet for more complex styling
        app.setStyleSheet(self._generate_stylesheet(theme))

    def _generate_stylesheet(self, theme):
        """Generate a stylesheet based on the theme colors."""
        return f"""
            QWidget {{
                background-color: {theme["background"].name()};
                color: {theme["foreground"].name()};
            }}
            QPushButton {{
                background-color: {theme["primary"].name()};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme["primary"].darker(110).name()};
            }}
            QPushButton:pressed {{
                background-color: {theme["primary"].darker(120).name()};
            }}
            QPushButton:disabled {{
                background-color: {theme["border"].name()};
                color: {theme["foreground"].name()};
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {theme["input_background"].name()};
                color: {theme["input_foreground"].name()};
                border: 1px solid {theme["border"].name()};
                border-radius: 4px;
                padding: 6px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {theme["primary"].name()};
            }}
            QTableWidget {{
                background-color: {theme["background"].name()};
                alternate-background-color: {theme["input_background"].name()};
                gridline-color: {theme["border"].name()};
            }}
            QHeaderView::section {{
                background-color: {theme["secondary"].name()};
                color: white;
                padding: 6px;
                border: none;
            }}
            QMenuBar {{
                background-color: {theme["background"].name()};
                color: {theme["foreground"].name()};
            }}
            QMenuBar::item:selected {{
                background-color: {theme["primary"].name()};
            }}
            QMenu {{
                background-color: {theme["background"].name()};
                color: {theme["foreground"].name()};
                border: 1px solid {theme["border"].name()};
            }}
            QMenu::item:selected {{
                background-color: {theme["primary"].name()};
            }}
            QTabWidget::pane {{
                border: 1px solid {theme["border"].name()};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background-color: {theme["input_background"].name()};
                color: {theme["foreground"].name()};
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme["primary"].name()};
                color: white;
            }}
            QTabBar::tab:!selected {{
                margin-top: 2px;
            }}
        """

    def get_color(self, role, theme_name=None):
        """Get a color for a specific role from the current or specified theme."""
        if theme_name is None:
            theme_name = self._current_theme
        if theme_name not in self._themes:
            return QColor()
        return self._themes[theme_name].get(role, QColor())
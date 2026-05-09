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
        palette.setColor(QPalette.ToolTipBase, theme["input_background"])
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
        """Generate a stylesheet based on the theme colors.
        
        NOTE: No QWidget wildcard — per-widget explicit styling only.
        Light/dark themes both use the same selectors with different tokens.
        """
        bg = theme["background"].name()
        fg = theme["foreground"].name()
        primary = theme["primary"].name()
        secondary = theme["secondary"].name()
        inp_bg = theme["input_background"].name()
        inp_fg = theme["input_foreground"].name()
        border = theme["border"].name()

        return f"""
            /* Root container only — never use QWidget wildcard */
            QMainWindow {{
                background-color: {bg};
                color: {fg};
            }}

            /* --- BUTTONS --- */
            QPushButton {{
                background-color: {primary};
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
                background-color: {border};
                color: {fg};
            }}
            QToolButton {{
                background-color: transparent;
                color: {fg};
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {inp_bg};
            }}
            QToolButton:pressed {{
                background-color: {border};
            }}

            /* --- INPUTS --- */
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {inp_bg};
                color: {inp_fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 6px;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {primary};
            }}
            QComboBox {{
                background-color: {inp_bg};
                color: {inp_fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 6px;
            }}
            QComboBox:focus {{
                border: 2px solid {primary};
            }}
            QComboBox QAbstractItemView {{
                background-color: {inp_bg};
                color: {inp_fg};
                selection-background-color: {primary};
                selection-color: white;
                border: 1px solid {border};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0;
            }}

            /* --- LABELS --- */
            QLabel {{
                background-color: transparent;
                color: {fg};
            }}

            /* --- DIALOGS --- */
            QDialog {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
            }}

            /* --- GROUP BOX --- */
            QGroupBox {{
                background-color: transparent;
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                margin-top: 12px;
                padding: 12px 8px 8px 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                padding: 0 6px;
                color: {fg};
            }}

            /* --- CHECKBOX / RADIO --- */
            QCheckBox, QRadioButton {{
                color: {fg};
                spacing: 6px;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}

            /* --- SCROLL AREA / FRAME --- */
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QFrame {{
                background-color: transparent;
                color: {fg};
            }}

            /* --- TABLES --- */
            QTableWidget, QTableView, QTreeView {{
                background-color: {bg};
                alternate-background-color: {inp_bg};
                color: {fg};
                gridline-color: {border};
                selection-background-color: {primary};
                selection-color: white;
                border: 1px solid {border};
            }}
            QHeaderView::section {{
                background-color: {secondary};
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }}

            /* --- LISTS --- */
            QListWidget, QListView {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
            }}
            QListWidget::item:selected, QListView::item:selected {{
                background-color: {primary};
                color: white;
            }}

            /* --- MENU --- */
            QMenuBar {{
                background-color: {bg};
                color: {fg};
                border-bottom: 1px solid {border};
            }}
            QMenuBar::item:selected {{
                background-color: {primary};
                color: white;
            }}
            QMenu {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
            }}
            QMenu::item:selected {{
                background-color: {primary};
                color: white;
            }}

            /* --- TOOLBAR --- */
            QToolBar {{
                background-color: {bg};
                color: {fg};
                border: none;
                spacing: 4px;
                padding: 2px;
            }}
            QToolBar::separator {{
                width: 1px;
                background-color: {border};
                margin: 2px 4px;
            }}

            /* --- STATUS BAR --- */
            QStatusBar {{
                background-color: {bg};
                color: {fg};
                border-top: 1px solid {border};
            }}
            QStatusBar::item {{
                border: none;
            }}
            QStatusBar QLabel {{
                color: {fg};
            }}

            /* --- TABS --- */
            QTabWidget::pane {{
                border: 1px solid {border};
                border-radius: 4px;
                background-color: {bg};
            }}
            QTabBar::tab {{
                background-color: {inp_bg};
                color: {fg};
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {primary};
                color: white;
            }}
            QTabBar::tab:!selected {{
                margin-top: 2px;
            }}

            /* --- SCROLLBAR --- */
            QScrollBar:vertical {{
                background-color: {inp_bg};
                width: 10px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {border};
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {primary};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background-color: {inp_bg};
                height: 10px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {border};
                min-width: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {primary};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}

            /* --- PROGRESS BAR --- */
            QProgressBar {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {primary};
                border-radius: 3px;
            }}

            /* --- SPLITTER --- */
            QSplitter::handle {{
                background-color: {border};
                width: 2px;
                height: 2px;
            }}
        """

    def get_color(self, role, theme_name=None):
        """Get a color for a specific role from the current or specified theme."""
        if theme_name is None:
            theme_name = self._current_theme
        if theme_name not in self._themes:
            return QColor()
        return self._themes[theme_name].get(role, QColor())
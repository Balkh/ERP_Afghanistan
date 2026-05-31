from ui.constants import (
    SPACING_XS,
    SPACING_SM,
    SPACING_6,
    BORDER_RADIUS_SM,
    TEXT_LABEL,
    TEXT_SECTION_TITLE,
    COLOR_BG_ELEVATED,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY,
)
from ui.components.buttons import IconButton, ButtonSize

"""
Navigation Header Component.
Reusable header with back, home, close buttons, title, and breadcrumb.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

class NavigationHeader(QWidget):
    """
    Navigation header component with back/home/close buttons, title, and breadcrumb.
    """
    
    # Signals
    back_clicked = Signal()
    home_clicked = Signal()
    close_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the navigation header UI."""
        self.setStyleSheet(f"""
            QWidget {{ background-color: transparent; }}
            EnterpriseButton {{
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM};
                padding: {SPACING_6}px {SPACING_SM}px;
                font-size: {TEXT_SECTION_TITLE}px;
            }}
            EnterpriseButton:hover {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_PRIMARY};
            }}
            EnterpriseButton:pressed {{
                background-color: {COLOR_BORDER};
            }}
            EnterpriseButton:disabled {{
                color: {COLOR_BORDER_LIGHT};
                border: 1px solid {COLOR_BG_ELEVATED};
            }}
            QLabel {{
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(SPACING_SM,  0,  SPACING_SM,  0)
        main_layout.setSpacing(SPACING_SM + SPACING_XS)
        
        # --- LEFT: Back + Home buttons ---
        left_layout = QHBoxLayout()
        left_layout.setSpacing(SPACING_SM)
        
        self.back_btn = IconButton(icon="←", tooltip="Back (Alt+Left)", size=ButtonSize.SMALL)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        left_layout.addWidget(self.back_btn)

        self.home_btn = IconButton(icon="⌂", tooltip="Home (Ctrl+Home)", size=ButtonSize.SMALL)
        self.home_btn.clicked.connect(self.home_clicked.emit)
        left_layout.addWidget(self.home_btn)
        
        main_layout.addLayout(left_layout)
        
        # --- CENTER: Title + Breadcrumb ---
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(SPACING_XS)
        
        self.title_label = QLabel("")
        self.title_label.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        center_layout.addWidget(self.title_label)
        
        self.breadcrumb_label = QLabel("")
        self.breadcrumb_label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.breadcrumb_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        center_layout.addWidget(self.breadcrumb_label)
        
        main_layout.addLayout(center_layout, 1)  # Stretch to fill center
        
        # --- RIGHT: Close button ---
        self.close_btn = IconButton(icon="✕", tooltip="Close (Esc)", size=ButtonSize.SMALL)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        main_layout.addWidget(self.close_btn)
    
    def set_title(self, title: str):
        """Set the page title."""
        self.title_label.setText(title)
    
    def set_breadcrumb(self, breadcrumb: list):
        """Set breadcrumb path. Format: ['Home', 'Sales', 'Invoices']."""
        if breadcrumb:
            self.breadcrumb_label.setText(" / ".join(breadcrumb))
        else:
            self.breadcrumb_label.setText("")
    
    def set_back_enabled(self, enabled: bool):
        """Enable/disable back button."""
        self.back_btn.setEnabled(enabled)
    
    def set_home_enabled(self, enabled: bool):
        """Enable/disable home button."""
        self.home_btn.setEnabled(enabled)
    
    def set_close_enabled(self, enabled: bool):
        """Enable/disable close button."""
        self.close_btn.setEnabled(enabled)
    
    def hide_navigation(self):
        """Hide back and home buttons."""
        self.back_btn.setVisible(False)
        self.home_btn.setVisible(False)
    
    def show_navigation(self):
        """Show back and home buttons."""
        self.back_btn.setVisible(True)
        self.home_btn.setVisible(True)
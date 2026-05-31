from ui.constants import (COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_PRIMARY, BORDER_RADIUS_MD, BORDER_RADIUS_LG, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG)
"""
License manager dialog for Pharmacy ERP.
Provides a tabbed interface for license activation and status viewing.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget)
import sys
import os

# Add paths for imports
frontend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, frontend_dir)
sys.path.insert(0, os.path.join(frontend_dir, 'license'))

from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from .activation_screen import ActivationScreen
from .license_status_screen import LicenseStatusScreen


class LicenseManagerDialog(EnterpriseDialog):
    """Dialog for managing Pharmacy ERP licenses."""
    
    def __init__(self, parent=None):
        super().__init__("Pharmacy ERP License Manager", DialogType.CUSTOM, parent)
        self.setModal(True)
        self.resize(600, 500)
        content = self._build_content()
        self.set_content(content)
        
    def _create_button_area(self):
        return None
        
    def _build_content(self):
        """Build the user interface content."""
        widget = QWidget()
        
        # Set dark theme stylesheet
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BG_MAIN};
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QGroupBox {{
                color: {COLOR_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG};
                margin-top: {SPACING_MD}px;
                padding-top: {SPACING_MD}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {SPACING_XS}px;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLOR_BORDER};
                background-color: {COLOR_BG_MAIN};
            }}
            QTabBar::tab {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                padding: {SPACING_SM}px {SPACING_LG}px;
                border: none;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_BORDER};
            }}
        """)
        
        layout = QVBoxLayout(widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create activation screen tab
        self.activation_screen = ActivationScreen()
        self.activation_screen.activation_success.connect(self.on_activation_success)
        self.activation_screen.activation_failed.connect(self.on_activation_failed)
        self.tab_widget.addTab(self.activation_screen, "Activate License")
        
        # Create license status screen tab
        self.license_status_screen = LicenseStatusScreen()
        self.tab_widget.addTab(self.license_status_screen, "License Status")
        
        # Add close button
        from PySide6.QtWidgets import QHBoxLayout
        from ui.components.buttons import EnterpriseButton, ButtonVariant
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = EnterpriseButton("Close", variant=ButtonVariant.SECONDARY)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        return widget
        
    def on_activation_success(self):
        """Handle successful license activation."""
        AlertDialog.info(
            "Activation Successful",
            "Pharmacy ERP has been successfully activated!\n\n"
            "Please restart the application to apply the license.",
            self,
        )
        # Refresh the license status screen
        self.license_status_screen.license_validator.force_revalidation()
        self.license_status_screen.update_license_info()
        
    def on_activation_failed(self, message):
        """Handle failed license activation."""
        AlertDialog.warning(
            "Activation Failed",
            f"License activation failed:\n\n{message}",
            self,
        )


if __name__ == "__main__":
    # For testing the license manager dialog standalone
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = LicenseManagerDialog()
    dialog.exec()
    sys.exit(app.exec())
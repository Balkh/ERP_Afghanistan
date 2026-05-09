from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""
License manager dialog for Pharmacy ERP.
Provides a tabbed interface for license activation and status viewing.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QMessageBox)
from PySide6.QtCore import Qt
import sys
import os

# Add paths for imports
frontend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, frontend_dir)
sys.path.insert(0, os.path.join(frontend_dir, 'license'))

from .activation_screen import ActivationScreen
from .license_status_screen import LicenseStatusScreen


class LicenseManagerDialog(QDialog):
    """Dialog for managing Pharmacy ERP licenses."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pharmacy ERP License Manager")
        self.setModal(True)
        self.resize(600, 500)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        # Set dark theme stylesheet
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_MAIN};
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QGroupBox {{
                color: {COLOR_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLOR_BORDER};
                background-color: {COLOR_BG_MAIN};
            }}
            QTabBar::tab {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                padding: 8px 16px;
                border: none;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_BORDER};
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BG_MAIN};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        
        layout = QVBoxLayout(self)
        
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
        from PySide6.QtWidgets import QPushButton, QHBoxLayout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
    def on_activation_success(self):
        """Handle successful license activation."""
        QMessageBox.information(
            self,
            "Activation Successful",
            "Pharmacy ERP has been successfully activated!\n\n"
            "Please restart the application to apply the license.",
            QMessageBox.Ok
        )
        # Refresh the license status screen
        self.license_status_screen.license_validator.force_revalidation()
        self.license_status_screen.update_license_info()
        
    def on_activation_failed(self, message):
        """Handle failed license activation."""
        QMessageBox.warning(
            self,
            "Activation Failed",
            f"License activation failed:\n\n{message}",
            QMessageBox.Ok
        )


if __name__ == "__main__":
    # For testing the license manager dialog standalone
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = LicenseManagerDialog()
    dialog.exec()
    sys.exit(app.exec())
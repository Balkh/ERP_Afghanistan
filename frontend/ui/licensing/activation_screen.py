"""
Activation screen for Pharmacy ERP license management.
Allows users to activate the software using license files.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFileDialog, QGroupBox,
                               QApplication)
from PySide6.QtCore import Qt, Signal
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_SM, SPACING_LG, SPACING_XXL, TEXT_PAGE_TITLE, TEXT_CARD_TITLE, TEXT_BODY,
                           TEXT_HELPER, BORDER_RADIUS_MD, BORDER_RADIUS_SM, COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER)
import os
import sys

# Add paths for imports
frontend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, frontend_dir)
sys.path.insert(0, os.path.join(frontend_dir, 'license'))

from license_service import LicenseService
from utils.device_fingerprint import generate_device_id


class ActivationScreen(QWidget):
    """Screen for activating Pharmacy ERP with a license file."""
    
    # Signals
    activation_success = Signal()
    activation_failed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.license_service = LicenseService()
        self.device_id = generate_device_id()
        self.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XXL + SPACING_LG,  SPACING_XXL + SPACING_LG,  SPACING_XXL + SPACING_LG,  SPACING_XXL + SPACING_LG)
        layout.setSpacing(SPACING_LG + SPACING_XS)
        
        # Title
        title_label = QLabel("Pharmacy ERP License Activation")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Activate your copy of Pharmacy ERP using a valid license file")
        subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}pt;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(20)
        
        # Device Information Group
        device_group = QGroupBox("Device Information")
        device_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=False))
        device_layout = QVBoxLayout()

        device_id_label = QLabel(f"Device ID: {self.device_id}")
        device_id_label.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        device_id_label.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY}; padding: {SPACING_SM}px; border-radius: {BORDER_RADIUS_SM}px;")
        device_layout.addWidget(device_id_label)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        layout.addSpacing(20)
        
        # License File Group
        license_group = QGroupBox("License File")
        license_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=False))
        license_layout = QVBoxLayout()

        # Instructions
        instructions = QLabel("Click 'Select License File' to choose your license file (.json or .lic)")
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        license_layout.addWidget(instructions)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.select_button = EnterpriseButton(text="Select License File", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.select_button.clicked.connect(self.select_license_file)
        button_layout.addWidget(self.select_button)

        self.activate_button = EnterpriseButton(text="Activate License", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.activate_button.setEnabled(False)
        self.activate_button.clicked.connect(self.activate_license)
        button_layout.addWidget(self.activate_button)
        
        license_layout.addLayout(button_layout)
        
        # Selected file display
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet(f"font-family: Consolas; font-size: {TEXT_HELPER}pt; color: {COLOR_TEXT_PRIMARY};")
        self.file_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-style: italic; padding: {SPACING_SM}px;")
        self.file_label.setWordWrap(True)
        license_layout.addWidget(self.file_label)
        
        license_group.setLayout(license_layout)
        layout.addWidget(license_group)
        
        layout.addSpacing(20)
        
        # Status Group
        status_group = QGroupBox("Activation Status")
        status_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=False))
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Ready to activate")
        self.status_label.setStyleSheet(f"font-size: {TEXT_BODY}pt; color: {COLOR_TEXT_SECONDARY};")
        self.status_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: {SPACING_SM}px;")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        
        # Store selected license file path
        self.selected_license_file = None
        
    def select_license_file(self):
        """Open file dialog to select a license file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select License File",
            "",
            "License Files (*.json *.lic);;All Files (*)"
        )
        
        if file_path:
            self.selected_license_file = file_path
            file_name = os.path.basename(file_path)
            self.file_label.setText(f"Selected: {file_name}")
            self.file_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-family: Consolas; font-size: {TEXT_HELPER}pt; padding: {SPACING_SM}px;")
            self.activate_button.setEnabled(True)
            self.status_label.setText("License file selected. Ready to activate.")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-weight: bold; padding: {SPACING_SM}px;")
    
    def activate_license(self):
        """Activate the license using the selected file."""
        if not self.selected_license_file or not os.path.exists(self.selected_license_file):
            AlertDialog.warning("Error", "Please select a valid license file first.", self)
            return
        
        # Update UI
        self.status_label.setText("Activating license...")
        self.status_label.setStyleSheet(f"color: {COLOR_WARNING}; font-weight: bold; padding: {SPACING_SM}px;")
        self.activate_button.setEnabled(False)
        self.select_button.setEnabled(False)
        
        
        try:
            # Load and validate the license
            license_data = self.license_service.load_license_from_file(self.selected_license_file)
            is_valid, message = self.license_service.validate_current_device_license(license_data)
            
            if is_valid:
                # Save license to default location for automatic loading
                default_license_path = os.path.join(self.license_service.keys_dir, "license.json")
                self.license_service.save_license_to_file(license_data, default_license_path)
                
                self.status_label.setText("Activation successful!")
                self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-weight: bold; padding: {SPACING_SM}px;")
                
                AlertDialog.info("Activation Successful", "Pharmacy ERP has been successfully activated!\n\n"
                    "The application will now restart to apply the license.", self)
                
                self.activation_success.emit()
            else:
                self.status_label.setText(f"Activation failed: {message}")
                self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold; padding: {SPACING_SM}px;")
                
                AlertDialog.warning("Activation Failed", f"License activation failed:\n\n{message}\n\n"
                    "Please check your license file and try again.", self)
                
                self.activation_failed.emit(message)
                
        except Exception as e:
            self.status_label.setText(f"Activation error: {str(e)}")
            self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold; padding: {SPACING_SM}px;")
            
            AlertDialog.error("Activation Error", f"An error occurred during activation:\n\n{str(e)}", self)
            
            self.activation_failed.emit(str(e))
            
        finally:
            # Re-enable buttons
            self.activate_button.setEnabled(True)
            self.select_button.setEnabled(True)


if __name__ == "__main__":
    # For testing the activation screen standalone
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = ActivationScreen()
    window.setWindowTitle("Pharmacy ERP - License Activation")
    window.resize(500, 600)
    window.show()
    sys.exit(app.exec())
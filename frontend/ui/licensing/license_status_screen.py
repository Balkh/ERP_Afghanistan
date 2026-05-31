"""
License status screen for Pharmacy ERP.
Displays current license information and validation status.
"""

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, BORDER_RADIUS_MD, BORDER_RADIUS_SM, TEXT_BODY, TEXT_CARD_TITLE, TEXT_DISPLAY, TEXT_LABEL, TEXT_MONO, TEXT_SECTION_TITLE, TEXT_TABLE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_DANGER, COLOR_STATUS_VALID)

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QGroupBox, QTextEdit)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
import os
import sys
from datetime import datetime

# Add paths for imports
frontend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, frontend_dir)
sys.path.insert(0, os.path.join(frontend_dir, 'license'))

from license_service import LicenseService
from license_validator import LicenseValidator
from utils.device_fingerprint import generate_device_id


class LicenseStatusScreen(QWidget):
    """Screen for displaying current license status and information."""
    
    # Signals
    refresh_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.license_service = LicenseService()
        self.license_validator = LicenseValidator()
        self.device_id = generate_device_id()
        self.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        self.setup_ui()
        self.update_license_info()
        
        # Set up timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_license_info)
        self.update_timer.start(30000)  # Update every 30 seconds
        
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL + SPACING_MD,  SPACING_XL + SPACING_MD,  SPACING_XL + SPACING_MD,  SPACING_XL + SPACING_MD)
        layout.setSpacing(SPACING_LG + SPACING_XS)
        
        # Title
        title_label = QLabel("Pharmacy ERP License Status")
        title_label.setFont(QFont("Segoe UI", TEXT_DISPLAY, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title_label)

        # Device Information Group
        device_group = QGroupBox("Device Information")
        device_group.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        device_layout = QVBoxLayout()

        device_id_label = QLabel(f"Device ID: {self.device_id}")
        device_id_label.setFont(QFont("Consolas", TEXT_MONO))
        device_id_label.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY}; padding: {SPACING_MD}px; border-radius: {BORDER_RADIUS_MD}; border: 1px solid {COLOR_BORDER};")
        device_layout.addWidget(device_id_label)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # License Status Group
        status_group = QGroupBox("License Status")
        status_group.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        status_layout = QVBoxLayout()

        # Status indicator
        status_indicator_layout = QHBoxLayout()
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Segoe UI", TEXT_CARD_TITLE))
        self.status_indicator.setFixedWidth(20)
        status_indicator_layout.addWidget(self.status_indicator)

        self.status_label = QLabel("Checking license status...")
        self.status_label.setFont(QFont("Segoe UI", TEXT_BODY))
        self.status_label.setStyleSheet(f"font-weight: bold; color: {COLOR_TEXT_PRIMARY};")
        status_indicator_layout.addWidget(self.status_label)
        status_indicator_layout.addStretch()

        status_layout.addLayout(status_indicator_layout)

        # Status details
        self.status_details = QLabel("Initializing license validation...")
        self.status_details.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.status_details.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: {SPACING_SM}px 0px;")
        self.status_details.setWordWrap(True)
        status_layout.addWidget(self.status_details)

        # Last checked time
        self.last_checked_label = QLabel("Last checked: --")
        self.last_checked_label.setFont(QFont("Segoe UI", TEXT_TABLE))
        self.last_checked_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        status_layout.addWidget(self.last_checked_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # License Details Group
        details_group = QGroupBox("License Details")
        details_group.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        details_layout = QVBoxLayout()

        # Create a scrollable text area for license details
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(200)
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", TEXT_TABLE))
        self.details_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM};
                padding: {SPACING_MD}px;
            }}
        """)
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = EnterpriseButton("Refresh Status", variant=ButtonVariant.SECONDARY)
        self.refresh_button.clicked.connect(self.refresh_license_status)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch()

        self.view_license_button = EnterpriseButton("View License File", variant=ButtonVariant.SECONDARY)
        self.view_license_button.clicked.connect(self.view_license_file)
        self.view_license_button.setEnabled(False)
        button_layout.addWidget(self.view_license_button)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        # Store current license data
        self.current_license_data = None
        self.license_file_path = None
        
    def update_license_info(self):
        """Update the license status display."""
        # Update last checked time
        self.last_checked_label.setText(f"Last checked: {datetime.now().strftime('%H:%M:%S')}")
        
        # Get license status from validator
        status = self.license_validator.get_license_status()
        
        # Update status indicator and label
        if status["is_valid"]:
            self.status_indicator.setStyleSheet(f"color: {COLOR_SUCCESS};")  # Green
            self.status_label.setText("VALID")
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_VALID}; font-weight: bold;")
        else:
            self.status_indicator.setStyleSheet(f"color: {COLOR_DANGER};")  # Red
            self.status_label.setText("INVALID")
            self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold;")
        
        # Update status details
        self.status_details.setText(status["message"])
        
        # Try to load and display license details
        self.load_license_details()
        
    def load_license_details(self):
        """Load and display detailed license information."""
        try:
            # Try to find license file
            license_data = self.license_service._find_and_load_license()
            
            if license_data is None:
                self.details_text.setPlainText("No license file found.")
                self.view_license_button.setEnabled(False)
                return
            
            self.current_license_data = license_data
            
            # Format license details for display
            details = []
            details.append("LICENSE INFORMATION")
            details.append("=" * 50)
            
            license_info = license_data.get("license_data", {})
            details.append(f"Device ID: {license_info.get('device_id', 'N/A')}")
            details.append(f"License Type: {license_info.get('license_type', 'N/A')}")
            details.append(f"Issued Date: {license_info.get('issued_date', 'N/A')}")
            details.append(f"Expiration Date: {license_info.get('expiration_date', 'N/A')}")
            
            features = license_info.get("features", [])
            if features:
                details.append(f"Enabled Features: {', '.join(features)}")
            else:
                details.append("Enabled Features: None")
            
            details.append("")
            details.append("TECHNICAL DETAILS")
            details.append("=" * 50)
            details.append(f"Version: {license_info.get('version', 'N/A')}")
            
            signature = license_data.get("signature", "")
            if signature:
                details.append(f"Signature Length: {len(signature)} characters")
                details.append(f"Signature Preview: {signature[:32]}...")
            else:
                details.append("Signature: Not available")
            
            # Validation details
            details.append("")
            details.append("VALIDATION STATUS")
            details.append("=" * 50)
            details.append(f"Device Match: {'✓' if license_info.get('device_id') == self.device_id else '✗'}")
            
            expiration_str = license_info.get("expiration_date")
            if expiration_str:
                from datetime import date
                try:
                    exp_date = date.fromisoformat(expiration_str)
                    is_expired = date.today() > exp_date
                    details.append(f"Expired: {'Yes' if is_expired else 'No'} ({expiration_str})")
                except (ValueError, TypeError):
                    details.append(f"Expiration Date: {expiration_str} (Invalid format)")
            else:
                details.append("Expiration: Not set (Perpetual license)")
            
            # Check if we can verify signature (would need public key)
            details.append("Signature Verification: Available (checked at runtime)")
            
            self.details_text.setPlainText("\n".join(details))
            self.view_license_button.setEnabled(True)
            
        except Exception as e:
            self.details_text.setPlainText(f"Error loading license details:\n{str(e)}")
            self.view_license_button.setEnabled(False)
    
    def refresh_license_status(self):
        """Refresh the license status display."""
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")
        
        # Force revalidation
        self.license_validator.force_revalidation()
        
        # Update display
        self.update_license_info()
        
        # Re-enable button after short delay
        QTimer.singleShot(1000, self._reenable_refresh_button)
    
    def _reenable_refresh_button(self):
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText('Refresh Status')
    
    def view_license_file(self):
        """View the current license file in a dialog."""
        if not self.current_license_data:
            AlertDialog.info(self, "Info", "No license data available to view.")
            return
        
        # Create and show license details dialog
        dialog = LicenseDetailsDialog(self.current_license_data, self)
        dialog.exec()
        
    def cleanup(self):
        """Cleanup resources."""
        self.update_timer.stop()
        self.license_validator.cleanup()


class LicenseDetailsDialog(QWidget):
    """Dialog for displaying detailed license information."""
    
    def __init__(self, license_data, parent=None):
        super().__init__(parent)
        self.license_data = license_data
        self.setWindowTitle("License Details")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        self.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")

        # Title
        title = QLabel("License Details")
        title.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        # Details text
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setFont(QFont("Consolas", TEXT_BODY))
        details_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM};
                padding: {SPACING_MD}px;
            }}
        """)

        # Format the license data nicely
        import json
        formatted_json = json.dumps(self.license_data, indent=2)
        details_text.setPlainText(formatted_json)

        layout.addWidget(details_text)

        # Close button
        close_button = EnterpriseButton("Close", variant=ButtonVariant.SECONDARY)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)


if __name__ == "__main__":
    # For testing the license status screen standalone
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = LicenseStatusScreen()
    window.setWindowTitle("Pharmacy ERP - License Status")
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec())
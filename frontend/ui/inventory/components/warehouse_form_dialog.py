from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QTextEdit, QSpinBox, QDialogButtonBox,
                               QLabel, QComboBox)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)

class WarehouseFormDialog(QDialog):
    """Dialog for adding/editing warehouses."""
    
    def __init__(self, parent=None, warehouse_id=None, api_client=None):
        super().__init__(parent)
        self.warehouse_id = warehouse_id
        self.api_client = api_client
        self.setWindowTitle("Add Warehouse" if warehouse_id is None else "Edit Warehouse")
        self.setModal(True)
        self.resize(400, 300)
        self.setup_ui()
        if warehouse_id:
            self.load_warehouse_data()
    
    def setup_ui(self):
        """Setup the form UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        # Title
        title_label = QLabel(self.windowTitle())
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title_label)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(10)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter warehouse name")
        form_layout.addRow("Name*:", self.name_input)
        
        # Location
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Enter warehouse location")
        form_layout.addRow("Location:", self.location_input)
        
        # Capacity
        self.capacity_input = QSpinBox()
        self.capacity_input.setRange(0, 999999)
        self.capacity_input.setValue(1000)
        form_layout.addRow("Capacity:", self.capacity_input)
        
        # Is Active
        self.active_check = QComboBox()
        self.active_check.addItems(["No", "Yes"])
        self.active_check.setCurrentIndex(1)  # Default to Yes
        form_layout.addRow("Is Active:", self.active_check)
        
        layout.addLayout(form_layout)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_warehouse_data(self):
        """Load warehouse data for editing."""
        try:
            response = self.api_client.get(f"/api/inventory/warehouses/{self.warehouse_id}/")
            warehouse = {}
            if response.get('success'):
                warehouse = response.get('data', {})
            else:
                warehouse = response
            
            if warehouse:
                self.name_input.setText(warehouse.get("name") or "")
                self.location_input.setText(warehouse.get("location") or "")
                self.capacity_input.setValue(warehouse.get("capacity") or 0)
                self.active_check.setCurrentIndex(1 if warehouse.get("is_active") else 0)
        except Exception as e:
            print(f"Error loading warehouse data: {e}")
    
    def get_form_data(self):
        """Get the form data as a dictionary."""
        return {
            "name": self.name_input.text().strip(),
            "location": self.location_input.text().strip(),
            "capacity": self.capacity_input.value(),
            "is_active": self.active_check.currentText() == "Yes"
        }
    
    def accept(self):
        """Validate and accept the dialog."""
        # Basic validation
        name = self.name_input.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Warehouse name is required.")
            return
        
        data = self.get_form_data()
        
        try:
            if self.warehouse_id:
                # Update existing warehouse
                response = self.api_client.put(f"/api/inventory/warehouses/{self.warehouse_id}/", data=data)
            else:
                # Create new warehouse
                response = self.api_client.post("/api/inventory/warehouses/", data=data)
            
            if response.get('success') or 'id' in response:
                super().accept()
            else:
                from PySide6.QtWidgets import QMessageBox
                error_msg = response.get('error', {}).get('message', "Unknown error occurred.")
                QMessageBox.critical(self, "Error", f"Failed to save warehouse: {error_msg}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Server communication error: {e}")
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QComboBox, QTextEdit, QDialogButtonBox,
                               QLabel, QFrame, QSpinBox, QDoubleSpinBox)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)

class ProductFormDialog(QDialog):
    """Dialog for adding/editing products."""
    
    def __init__(self, parent=None, product_id=None, api_client=None):
        super().__init__(parent)
        self.product_id = product_id
        self.api_client = api_client
        self.setWindowTitle("Add Product" if product_id is None else "Edit Product")
        self.setModal(True)
        self.resize(500, 600)
        self.setup_ui()
        if product_id:
            self.load_product_data()
    
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
        self.name_input.setPlaceholderText("Enter product name")
        form_layout.addRow("Name*:", self.name_input)
        
        # Generic Name
        self.generic_name_input = QLineEdit()
        self.generic_name_input.setPlaceholderText("Enter generic name")
        form_layout.addRow("Generic Name:", self.generic_name_input)
        
        # Brand Name
        self.brand_name_input = QLineEdit()
        self.brand_name_input.setPlaceholderText("Enter brand name")
        form_layout.addRow("Brand Name:", self.brand_name_input)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(200)
        self.populate_categories()
        form_layout.addRow("Category*:", self.category_combo)
        
        # Unit
        self.unit_combo = QComboBox()
        self.unit_combo.setMinimumWidth(200)
        self.populate_units()
        form_layout.addRow("Unit*:", self.unit_combo)
        
        # Barcode
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Enter barcode")
        form_layout.addRow("Barcode:", self.barcode_input)
        
        # SKU
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("Enter SKU")
        form_layout.addRow("SKU:", self.sku_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Enter product description")
        form_layout.addRow("Description:", self.description_input)
        
        # Requires Prescription
        self.prescription_check = QComboBox()
        self.prescription_check.addItems(["No", "Yes"])
        form_layout.addRow("Requires Prescription:", self.prescription_check)
        
        # Controlled Substance
        self.controlled_check = QComboBox()
        self.controlled_check.addItems(["No", "Yes"])
        form_layout.addRow("Controlled Substance:", self.controlled_check)
        
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
    
    def populate_categories(self):
        """Populate category dropdown."""
        self.category_combo.addItem("Select Category", None)
        try:
            response = self.api_client.get("/api/inventory/categories/")
            categories = []
            if isinstance(response, list):
                categories = response
            elif isinstance(response, dict):
                categories = response.get('results', []) or response.get('data', [])
            
            for cat in categories:
                if isinstance(cat, dict):
                    self.category_combo.addItem(cat.get('name'), cat.get('id'))
        except Exception as e:
            print(f"Error fetching categories: {e}")
    
    def populate_units(self):
        """Populate unit dropdown."""
        # For now units might be hardcoded or from a smaller list
        # Standardizing units if there's no dedicated endpoint yet
        self.unit_combo.addItem("Select Unit", None)
        units = [
            {"id": "piece", "name": "Piece"},
            {"id": "box", "name": "Box"},
            {"id": "bottle", "name": "Bottle"},
            {"id": "vial", "name": "Vial"},
            {"id": "tube", "name": "Tube"},
            {"id": "tablet", "name": "Tablet"},
            {"id": "capsule", "name": "Capsule"}
        ]
        for unit in units:
            self.unit_combo.addItem(unit['name'], unit['id'])
    
    def load_product_data(self):
        """Load product data for editing."""
        try:
            response = self.api_client.get(f"/api/inventory/products/{self.product_id}/")
            product = {}
            if response.get('success'):
                product = response.get('data', {})
            else:
                product = response
                
            if product:
                self.name_input.setText(product.get("name") or "")
                self.generic_name_input.setText(product.get("generic_name") or "")
                self.brand_name_input.setText(product.get("brand_name") or "")
                self.barcode_input.setText(product.get("barcode") or "")
                self.sku_input.setText(product.get("sku") or "")
                self.description_input.setPlainText(product.get("description") or "")
                
                self.prescription_check.setCurrentIndex(1 if product.get("requires_prescription") else 0)
                self.controlled_check.setCurrentIndex(1 if product.get("is_controlled_substance") else 0)
                self.active_check.setCurrentIndex(1 if product.get("is_active") else 0)
                
                # Set category and unit
                cat_id = product.get("category")
                index = self.category_combo.findData(cat_id)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
                
                unit_id = product.get("unit")
                index = self.unit_combo.findData(unit_id)
                if index >= 0:
                    self.unit_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error loading product data: {e}")
    
    def get_form_data(self):
        """Get the form data as a dictionary."""
        return {
            "name": self.name_input.text().strip(),
            "generic_name": self.generic_name_input.text().strip(),
            "brand_name": self.brand_name_input.text().strip(),
            "category_id": self.category_combo.currentData(),
            "unit_id": self.unit_combo.currentData(),
            "barcode": self.barcode_input.text().strip(),
            "sku": self.sku_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "requires_prescription": self.prescription_check.currentText() == "Yes",
            "is_controlled_substance": self.controlled_check.currentText() == "Yes",
            "is_active": self.active_check.currentText() == "Yes"
        }
    
    def accept(self):
        """Validate and accept the dialog."""
        # Basic validation
        name = self.name_input.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Product name is required.")
            return
        
        category_id = self.category_combo.currentData()
        if category_id is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Please select a category.")
            return
            
        unit_id = self.unit_combo.currentData()
        if unit_id is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Please select a unit.")
            return
        
        # Prepare data
        data = self.get_form_data()
        
        try:
            if self.product_id:
                # Update existing product
                response = self.api_client.put(f"/api/inventory/products/{self.product_id}/", data=data)
            else:
                # Create new product
                response = self.api_client.post("/api/inventory/products/", data=data)
            
            if response.get('success') or 'id' in response:
                super().accept()
            else:
                from PySide6.QtWidgets import QMessageBox
                error_msg = response.get('error', {}).get('message', "Unknown error occurred.")
                QMessageBox.critical(self, "Error", f"Failed to save product: {error_msg}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Server communication error: {e}")
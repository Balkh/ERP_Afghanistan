from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox,
                               QDialogButtonBox, QLabel)
from PySide6.QtCore import Qt, Slot, QDate
from PySide6.QtGui import QFont
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, TEXT_DISPLAY)

class BatchFormDialog(QDialog):
    """Dialog for adding/editing batches."""
    
    def __init__(self, parent=None, batch_id=None, api_client=None):
        super().__init__(parent)
        self.batch_id = batch_id
        self.api_client = api_client
        self.setWindowTitle("Add Batch" if batch_id is None else "Edit Batch")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
        if batch_id:
            self.load_batch_data()
    
    def setup_ui(self):
        """Setup the form UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        # Title
        title_label = QLabel(self.windowTitle())
        title_font = QFont("Segoe UI", TEXT_DISPLAY)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(10)
        
        # Product
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(200)
        self.populate_products()
        form_layout.addRow("Product*:", self.product_combo)
        
        # Batch Number
        self.batch_number_input = QLineEdit()
        self.batch_number_input.setPlaceholderText("Enter batch number")
        form_layout.addRow("Batch Number*:", self.batch_number_input)
        
        # Expiry Date
        self.expiry_date_input = QDateEdit()
        self.expiry_date_input.setCalendarPopup(True)
        self.expiry_date_input.setDate(QDate.currentDate().addYears(1))  # Default to 1 year from now
        form_layout.addRow("Expiry Date*:", self.expiry_date_input)
        
        # Quantity
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 999999)
        self.quantity_input.setValue(0)
        form_layout.addRow("Quantity:", self.quantity_input)
        
        # Warehouse
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setMinimumWidth(200)
        self.populate_warehouses()
        form_layout.addRow("Warehouse*:", self.warehouse_combo)
        
        layout.addLayout(form_layout)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def populate_products(self):
        """Populate product dropdown."""
        self.product_combo.addItem("Select Product", None)
        try:
            response = self.api_client.get("/api/inventory/products/")
            products = []
            if isinstance(response, list):
                products = response
            elif isinstance(response, dict):
                products = response.get('results', []) or response.get('data', [])
            
            for prod in products:
                if isinstance(prod, dict):
                    self.product_combo.addItem(prod.get('name'), prod.get('id'))
        except Exception as e:
            print(f"Error fetching products: {e}")
    
    def populate_warehouses(self):
        """Populate warehouse dropdown."""
        self.warehouse_combo.addItem("Select Warehouse", None)
        try:
            response = self.api_client.get("/api/inventory/warehouses/")
            warehouses = []
            if isinstance(response, list):
                warehouses = response
            elif isinstance(response, dict):
                warehouses = response.get('results', []) or response.get('data', [])
            
            for wh in warehouses:
                if isinstance(wh, dict):
                    self.warehouse_combo.addItem(wh.get('name'), wh.get('id'))
        except Exception as e:
            print(f"Error fetching warehouses: {e}")
    
    def load_batch_data(self):
        """Load batch data for editing."""
        try:
            response = self.api_client.get(f"/api/inventory/batches/{self.batch_id}/")
            batch = {}
            if response.get('success'):
                batch = response.get('data', {})
            else:
                batch = response
            
            if batch:
                prod_id = batch.get("product")
                index = self.product_combo.findData(prod_id)
                if index >= 0:
                    self.product_combo.setCurrentIndex(index)
                
                self.batch_number_input.setText(batch.get("batch_number") or "")
                
                expiry_str = batch.get("expiry_date")
                if expiry_str:
                    self.expiry_date_input.setDate(QDate.fromString(expiry_str, "yyyy-MM-dd"))
                
                self.quantity_input.setValue(int(float(batch.get("quantity") or 0)))
                
                wh_id = batch.get("warehouse")
                index = self.warehouse_combo.findData(wh_id)
                if index >= 0:
                    self.warehouse_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error loading batch data: {e}")
    
    def get_form_data(self):
        """Get the form data as a dictionary."""
        return {
            "product_id": self.product_combo.currentData(),
            "batch_number": self.batch_number_input.text().strip(),
            "expiry_date": self.expiry_date_input.date().toString("yyyy-MM-dd"),
            "quantity": self.quantity_input.value(),
            "warehouse_id": self.warehouse_combo.currentData()
        }
    
    def accept(self):
        """Validate and accept the dialog."""
        # Basic validation
        if not self.batch_number_input.text().strip():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Batch number is required.")
            return
        
        if self.product_combo.currentData() is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Please select a product.")
            return
            
        if self.warehouse_combo.currentData() is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Please select a warehouse.")
            return
        
        data = self.get_form_data()
        
        try:
            if self.batch_id:
                # Update existing batch
                response = self.api_client.put(f"/api/inventory/batches/{self.batch_id}/", data=data)
            else:
                # Create new batch
                response = self.api_client.post("/api/inventory/batches/", data=data)
            
            if response.get('success') or 'id' in response:
                super().accept()
            else:
                from PySide6.QtWidgets import QMessageBox
                error_msg = response.get('error', {}).get('message', "Unknown error occurred.")
                QMessageBox.critical(self, "Error", f"Failed to save batch: {error_msg}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Server communication error: {e}")
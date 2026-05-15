from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QTextEdit, QComboBox, QDialogButtonBox,
                               QLabel, QFrame)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, TEXT_DISPLAY)

class CategoryFormDialog(QDialog):
    """Dialog for adding/editing categories."""
    
    def __init__(self, parent=None, category_id=None, api_client=None):
        super().__init__(parent)
        self.category_id = category_id
        self.api_client = api_client
        self.setWindowTitle("Add Category" if category_id is None else "Edit Category")
        self.setModal(True)
        self.resize(400, 300)
        self.setup_ui()
        if category_id:
            self.load_category_data()
    
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
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter category name")
        form_layout.addRow("Name*:", self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Enter category description")
        form_layout.addRow("Description:", self.description_input)
        
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
    
    def load_category_data(self):
        """Load category data for editing."""
        try:
            response = self.api_client.get(f"/api/inventory/categories/{self.category_id}/")
            category = {}
            if response.get('success'):
                category = response.get('data', {})
            else:
                category = response
            
            if category:
                self.name_input.setText(category.get("name") or "")
                self.description_input.setPlainText(category.get("description") or "")
                self.active_check.setCurrentIndex(1 if category.get("is_active") else 0)
        except Exception as e:
            print(f"Error loading category data: {e}")
    
    def get_form_data(self):
        """Get the form data as a dictionary."""
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "is_active": self.active_check.currentText() == "Yes"
        }
    
    def accept(self):
        """Validate and accept the dialog."""
        # Basic validation
        name = self.name_input.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Category name is required.")
            return
        
        data = self.get_form_data()
        
        try:
            if self.category_id:
                # Update existing category
                response = self.api_client.put(f"/api/inventory/categories/{self.category_id}/", data=data)
            else:
                # Create new category
                response = self.api_client.post("/api/inventory/categories/", data=data)
            
            if response.get('success') or 'id' in response:
                super().accept()
            else:
                from PySide6.QtWidgets import QMessageBox
                error_msg = response.get('error', {}).get('message', "Unknown error occurred.")
                QMessageBox.critical(self, "Error", f"Failed to save category: {error_msg}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Server communication error: {e}")
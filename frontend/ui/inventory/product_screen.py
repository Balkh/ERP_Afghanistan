import logging
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.operator_safety import DestructiveActionGuard
from .base_screen import BaseInventoryScreen
from api.client import APIClient
from api.endpoints import get_endpoint
from PySide6.QtCore import Slot

logger = logging.getLogger(__name__)

class ProductScreen(BaseInventoryScreen):
    """Screen for managing products."""
    
    def __init__(self, api_client=None):
        super().__init__("Product Management")
        self.api_client = api_client or APIClient()
        self.products = []  # Cache of products
        self.setup_table()
        
        # Connect signals to slots
        self.add_requested.connect(self.on_add_requested)
        self.edit_requested.connect(self.on_edit_requested)
        self.delete_requested.connect(self.on_delete_requested)
        self.refresh_requested.connect(self.on_refresh_requested)
        self.search_text_changed.connect(self.on_search_text_changed)
        self.filter_changed.connect(self.on_filter_changed)
        
        self.load_products()
        
    def setup_table(self):
        """Setup the products table."""
        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("name", "Name", width=150),
            TableColumn("generic_name", "Generic Name", width=120),
            TableColumn("brand_name", "Brand", width=100),
            TableColumn("category_name", "Category", width=100),
            TableColumn("unit_name", "Unit", width=60),
            TableColumn("barcode", "Barcode", width=120),
            TableColumn("sku", "SKU", width=100),
        ]
        self.table = EnterpriseTable(columns)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        
        self.set_table_widget(self.table)
    
    def populate_filter_options(self):
        """Populate filter options for products."""
        self.filter_combo.addItem("All", "")
        self.filter_combo.addItem("Active Only", "active")
        self.filter_combo.addItem("Inactive Only", "inactive")
        self.filter_combo.addItem("Requires Prescription", "prescription")
        self.filter_combo.addItem("Controlled Substance", "controlled")
    
    @Slot()
    def load_products(self):
        """Load products from the API."""
        try:
            endpoint = get_endpoint("products")
            params = {}
            filter_value = self.filter_combo.currentData()
            if filter_value == "active":
                params["is_active"] = "true"
            elif filter_value == "inactive":
                params["is_active"] = "false"
            elif filter_value == "prescription":
                params["requires_prescription"] = "true"
            elif filter_value == "controlled":
                params["is_controlled_substance"] = "true"
            
            search_text = self.search_input.text().strip()
            if search_text:
                params["search"] = search_text
            
            response = self.api_client.get(endpoint, params=params)
            self.products = []
            if isinstance(response, list):
                self.products = [p for p in response if isinstance(p, dict)]
            elif isinstance(response, dict):
                if response.get('success'):
                    data = response.get('data', [])
                    if isinstance(data, list):
                        self.products = [p for p in data if isinstance(p, dict)]
                    elif isinstance(data, dict):
                        if 'results' in data:
                            self.products = [p for p in data.get('results', []) if isinstance(p, dict)]
                        elif 'id' in data:
                            self.products = [data]
            
            self.update_table()
        except Exception as e:
            logger.error(f"Error loading products: {e}")
            self.products = []
            self.update_table()
    
    def update_table(self):
        """Update the table with current products."""
        if not self.products:
            self.table.set_data([])
            return
        data = []
        for product in self.products:
            if not isinstance(product, dict):
                continue
            data.append({
                "id": str(product.get("id") or ""),
                "name": product.get("name") or "",
                "generic_name": product.get("generic_name") or "",
                "brand_name": product.get("brand_name") or "",
                "category_name": product.get("category_name") or "",
                "unit_name": product.get("unit_name") or "",
                "barcode": product.get("barcode") or "",
                "sku": product.get("sku") or "",
            })
        self.table.set_data(data)
    
    @Slot()
    def on_selection_changed(self):
        """Handle table selection change."""
        selected_rows = self.table.selectionModel().selectedRows()
        self.set_selection_enabled(len(selected_rows) > 0)
    
    # Implement the slots for the signals from base class
    @Slot()
    def on_add_requested(self):
        """Handle add request."""
        self.show_product_form()
    
    @Slot(object)
    def on_edit_requested(self, product_id):
        """Handle edit request."""
        if product_id:
            self.show_product_form(product_id)
    
    @Slot(object)
    def on_delete_requested(self, product_id):
        """Handle delete request."""
        if product_id:
            if DestructiveActionGuard.confirm_delete(self, f"product ID {product_id}"):
                self.delete_product(product_id)
    
    @Slot()
    def on_refresh_requested(self):
        """Handle refresh request."""
        self.load_products()
    
    @Slot(str)
    def on_search_text_changed(self, text):
        """Handle search text change."""
        # Implement debounce if needed
        self.load_products()
    
    @Slot(str)
    def on_filter_changed(self, filter_value):
        """Handle filter change."""
        self.load_products()
    
    def show_product_form(self, product_id=None):
        """Show the product form dialog."""
        from .components.product_form import ProductFormDialog
        dialog = ProductFormDialog(self, product_id=product_id, api_client=self.api_client)
        if dialog.exec():
            self.load_products()
    
    def delete_product(self, product_id):
        """Delete a product."""
        try:
            self.api_client.delete(f"/api/inventory/products/{product_id}/")
            self.load_products()
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
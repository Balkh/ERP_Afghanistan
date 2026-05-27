from api.client import APIClient
from api.endpoints import get_endpoint
from PySide6.QtCore import Slot

from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.operator_safety import DestructiveActionGuard
from .base_screen import BaseInventoryScreen

class WarehouseScreen(BaseInventoryScreen):
    """Screen for managing warehouses."""

    def __init__(self, api_client=None):
        super().__init__("Warehouse Management")
        self.api_client = api_client or APIClient()
        self.warehouses = []  # Cache of warehouses
        self.setup_table()
        
        # Connect signals to slots
        self.add_requested.connect(self.on_add_requested)
        self.edit_requested.connect(self.on_edit_requested)
        self.delete_requested.connect(self.on_delete_requested)
        self.refresh_requested.connect(self.on_refresh_requested)
        self.search_text_changed.connect(self.on_search_text_changed)
        self.filter_changed.connect(self.on_filter_changed)
        
        self.load_warehouses()

    def setup_table(self):
        """Setup the warehouses table."""
        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("name", "Name", width=150),
            TableColumn("location", "Location", width=200),
            TableColumn("capacity", "Capacity", width=100, align="right"),
            TableColumn("is_active", "Is Active", width=80, align="center"),
        ]
        self.table = EnterpriseTable(columns)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        self.set_table_widget(self.table)

    def populate_filter_options(self):
        """Populate filter options for warehouses."""
        self.filter_combo.addItem("All", "")
        self.filter_combo.addItem("Active Only", "active")
        self.filter_combo.addItem("Inactive Only", "inactive")

    @Slot()
    def load_warehouses(self):
        """Load warehouses from the API."""
        try:
            endpoint = get_endpoint("warehouses")
            params = {}
            filter_value = self.filter_combo.currentData()
            if filter_value == "active":
                params["is_active"] = "true"
            elif filter_value == "inactive":
                params["is_active"] = "false"

            search_text = self.search_input.text().strip()
            if search_text:
                params["search"] = search_text

            response = self.api_client.get(endpoint, params=params)
            self.warehouses = []
            if isinstance(response, list):
                self.warehouses = [w for w in response if isinstance(w, dict)]
            elif isinstance(response, dict):
                if response.get('success'):
                    data = response.get('data', [])
                    if isinstance(data, list):
                        self.warehouses = [w for w in data if isinstance(w, dict)]
                    elif isinstance(data, dict):
                        if 'results' in data:
                            self.warehouses = [w for w in data.get('results', []) if isinstance(w, dict)]
                        elif 'id' in data:
                            self.warehouses = [data]

            self.update_table()
        except Exception as e:
            print(f"Error loading warehouses: {e}")
            self.warehouses = []
            self.update_table()

    def update_table(self):
        """Update the table with current warehouses."""
        data = []
        for warehouse in self.warehouses:
            is_active = warehouse.get("is_active", False)
            data.append({
                "id": str(warehouse.get("id", "")),
                "name": warehouse.get("name", ""),
                "location": warehouse.get("location", ""),
                "capacity": str(warehouse.get("capacity", "")),
                "is_active": "Yes" if is_active else "No",
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
        self.show_warehouse_form()

    @Slot(object)
    def on_edit_requested(self, warehouse_id):
        """Handle edit request."""
        if warehouse_id:
            self.show_warehouse_form(warehouse_id)

    @Slot(object)
    def on_delete_requested(self, warehouse_id):
        """Handle delete request."""
        if warehouse_id:
            if DestructiveActionGuard.confirm_delete(self, f"warehouse ID {warehouse_id}"):
                self.delete_warehouse(warehouse_id)

    @Slot()
    def on_refresh_requested(self):
        """Handle refresh request."""
        self.load_warehouses()

    @Slot(str)
    def on_search_text_changed(self, text):
        """Handle search text change."""
        self.load_warehouses()

    @Slot(str)
    def on_filter_changed(self, filter_value):
        """Handle filter change."""
        self.load_warehouses()

    def show_warehouse_form(self, warehouse_id=None):
        """Show the warehouse form dialog."""
        from .components.warehouse_form_dialog import WarehouseFormDialog
        dialog = WarehouseFormDialog(self, warehouse_id=warehouse_id, api_client=self.api_client)
        if dialog.exec():
            self.load_warehouses()

    def delete_warehouse(self, warehouse_id):
        """Delete a warehouse."""
        try:
            self.api_client.delete(f"/api/inventory/warehouses/{warehouse_id}/")
            self.load_warehouses()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to delete warehouse: {e}")
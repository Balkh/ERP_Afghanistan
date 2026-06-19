import logging
from api.client import APIClient
from api.endpoints import get_endpoint
from PySide6.QtCore import Slot

from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.operator_safety import DestructiveActionGuard
from .base_screen import BaseInventoryScreen

class BatchScreen(BaseInventoryScreen):
    """Screen for managing batches."""

    def __init__(self, api_client=None):
        super().__init__("Batch Management")
        self.api_client = api_client or APIClient()
        self.batches = []  # Cache of batches
        self.setup_table()
        
        # Connect signals to slots
        self.add_requested.connect(self.on_add_requested)
        self.edit_requested.connect(self.on_edit_requested)
        self.delete_requested.connect(self.on_delete_requested)
        self.refresh_requested.connect(self.on_refresh_requested)
        self.search_text_changed.connect(self.on_search_text_changed)
        self.filter_changed.connect(self.on_filter_changed)
        
        self.load_batches()

    def setup_table(self):
        """Setup the batches table."""
        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("product_name", "Product", width=150),
            TableColumn("batch_number", "Batch No", width=120),
            TableColumn("expiry_date", "Expiry", width=100, align="center"),
            TableColumn("quantity", "Qty", width=60, align="right"),
            TableColumn("warehouse_name", "Warehouse", width=120),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.table = EnterpriseTable(columns)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        self.set_table_widget(self.table)

    def populate_filter_options(self):
        """Populate filter options for batches."""
        self.filter_combo.addItem("All", "")
        self.filter_combo.addItem("Active Only", "active")
        self.filter_combo.addItem("Expired", "expired")
        self.filter_combo.addItem("Expiring Soon", "expiring_soon")

    @Slot()
    def load_batches(self):
        """Load batches from the API."""
        try:
            endpoint = get_endpoint("batches")
            params = {}
            filter_value = self.filter_combo.currentData()
            if filter_value == "active":
                params["is_active"] = "true"
            elif filter_value == "expired":
                params["is_expired"] = "true"
            elif filter_value == "expiring_soon":
                params["is_expiring_soon"] = "true"

            search_text = self.search_input.text().strip()
            if search_text:
                params["search"] = search_text

            response = self.api_client.get(endpoint, params=params)
            self.batches = []
            if isinstance(response, list):
                self.batches = [b for b in response if isinstance(b, dict)]
            elif isinstance(response, dict):
                if response.get('success'):
                    data = response.get('data', [])
                    if isinstance(data, list):
                        self.batches = [b for b in data if isinstance(b, dict)]
                    elif isinstance(data, dict):
                        if 'results' in data:
                            self.batches = [b for b in data.get('results', []) if isinstance(b, dict)]
                        elif 'id' in data:
                            self.batches = [data]

            self.update_table()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading batches: {e}")
            self.batches = []
            self.update_table()

    def update_table(self):
        """Update the table with current batches."""
        if not self.batches:
            self.table.set_data([])
            return
        data = []
        for batch in self.batches:
            if not isinstance(batch, dict):
                continue
            status = batch.get("status") or "unknown"
            data.append({
                "id": str(batch.get("id") or ""),
                "product_name": batch.get("product_name") or "",
                "batch_number": batch.get("batch_number") or "",
                "expiry_date": batch.get("expiry_date") or "",
                "quantity": str(batch.get("quantity") or ""),
                "warehouse_name": batch.get("warehouse_name") or "",
                "status": status.capitalize(),
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
        self.show_batch_form()

    @Slot(object)
    def on_edit_requested(self, batch_id):
        """Handle edit request."""
        if batch_id:
            self.show_batch_form(batch_id)

    @Slot(object)
    def on_delete_requested(self, batch_id):
        """Handle delete request."""
        if batch_id:
            if DestructiveActionGuard.confirm_delete(self, f"batch ID {batch_id}"):
                self.delete_batch(batch_id)

    @Slot()
    def on_refresh_requested(self):
        """Handle refresh request."""
        self.load_batches()

    @Slot(str)
    def on_search_text_changed(self, text):
        """Handle search text change."""
        self.load_batches()

    @Slot(str)
    def on_filter_changed(self, filter_value):
        """Handle filter change."""
        self.load_batches()

    def show_batch_form(self, batch_id=None):
        """Show the batch form dialog."""
        from .components.batch_form_dialog import BatchFormDialog
        dialog = BatchFormDialog(self, batch_id=batch_id, api_client=self.api_client)
        if dialog.exec():
            self.load_batches()

    def delete_batch(self, batch_id):
        """Delete a batch."""
        try:
            self.api_client.delete(f"/api/inventory/batches/{batch_id}/")
            self.load_batches()
        except Exception as e:
            from ui.components.dialogs import AlertDialog
            AlertDialog.error("Error", f"Failed to delete batch: {e}", self)
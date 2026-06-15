from api.client import APIClient
from api.endpoints import get_endpoint
from PySide6.QtCore import Slot

from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.operator_safety import DestructiveActionGuard
from .base_screen import BaseInventoryScreen

class CategoryScreen(BaseInventoryScreen):
    """Screen for managing categories."""

    def __init__(self, api_client=None):
        super().__init__("Category Management")
        self.api_client = api_client or APIClient()
        self.categories = []  # Cache of categories
        self.setup_table()
        
        # Connect signals to slots
        self.add_requested.connect(self.on_add_requested)
        self.edit_requested.connect(self.on_edit_requested)
        self.delete_requested.connect(self.on_delete_requested)
        self.refresh_requested.connect(self.on_refresh_requested)
        self.search_text_changed.connect(self.on_search_text_changed)
        self.filter_changed.connect(self.on_filter_changed)
        
        self.load_categories()

    def setup_table(self):
        """Setup the categories table."""
        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("name", "Name", width=200),
            TableColumn("description", "Description", width=300),
            TableColumn("is_active", "Is Active", width=80, align="center"),
        ]
        self.table = EnterpriseTable(columns)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        self.set_table_widget(self.table)

    def populate_filter_options(self):
        """Populate filter options for categories."""
        self.filter_combo.addItem("All", "")
        self.filter_combo.addItem("Active Only", "active")
        self.filter_combo.addItem("Inactive Only", "inactive")

    @Slot()
    def load_categories(self):
        """Load categories from the API."""
        try:
            endpoint = get_endpoint("categories")
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
            self.categories = []
            if isinstance(response, list):
                self.categories = [c for c in response if isinstance(c, dict)]
            elif isinstance(response, dict):
                if response.get('success'):
                    data = response.get('data', [])
                    if isinstance(data, list):
                        self.categories = [c for c in data if isinstance(c, dict)]
                    elif isinstance(data, dict):
                        if 'results' in data:
                            self.categories = [c for c in data.get('results', []) if isinstance(c, dict)]
                        elif 'id' in data:
                            self.categories = [data]

            self.update_table()
        except Exception as e:
            print(f"Error loading categories: {e}")
            self.categories = []
            self.update_table()

    def update_table(self):
        """Update the table with current categories."""
        data = []
        for category in self.categories:
            is_active = category.get("is_active", False)
            data.append({
                "id": str(category.get("id", "")),
                "name": category.get("name", ""),
                "description": category.get("description", ""),
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
        self.show_category_form()

    @Slot(object)
    def on_edit_requested(self, category_id):
        """Handle edit request."""
        if category_id:
            self.show_category_form(category_id)

    @Slot(object)
    def on_delete_requested(self, category_id):
        """Handle delete request."""
        if category_id:
            if DestructiveActionGuard.confirm_delete(self, f"category ID {category_id}"):
                self.delete_category(category_id)

    @Slot()
    def on_refresh_requested(self):
        """Handle refresh request."""
        self.load_categories()

    @Slot(str)
    def on_search_text_changed(self, text):
        """Handle search text change."""
        self.load_categories()

    @Slot(str)
    def on_filter_changed(self, filter_value):
        """Handle filter change."""
        self.load_categories()

    def show_category_form(self, category_id=None):
        """Show the category form dialog."""
        from .components.category_form_dialog import CategoryFormDialog
        dialog = CategoryFormDialog(self, category_id=category_id, api_client=self.api_client)
        if dialog.exec():
            self.load_categories()

    def delete_category(self, category_id):
        """Delete a category."""
        try:
            self.api_client.delete(f"/api/inventory/categories/{category_id}/")
            self.load_categories()
        except Exception as e:
            from ui.components.dialogs import AlertDialog
            AlertDialog.error("Error", f"Failed to delete category: {e}", self)
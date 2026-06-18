from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLineEdit,
                                QLabel, QComboBox, QWidget)
from PySide6.QtCore import Signal
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.dialogs import EnterpriseDialog, DialogType, ConfirmDialog
from ui.components.tables import EnterpriseTable, TableColumn
from PySide6.QtGui import QFont
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_LG, TEXT_TABLE, TEXT_CARD_TITLE)


class BatchSelectionDialog(EnterpriseDialog):
    """Dialog for selecting batches for a product."""

    batch_selected = Signal(dict)

    def __init__(self, parent=None, product_id=None, product_name="", required_quantity=0, api_client=None):
        self.product_id = product_id
        self.product_name = product_name
        self.required_quantity = required_quantity
        self.api_client = api_client
        self.batches = []
        self.selected_batch = None
        super().__init__(f"Select Batch - {product_name}", DialogType.CUSTOM, parent)
        self.setModal(True)
        self.resize(800, 500)
        self._build_content()
        self.load_batches()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel(f"Batches for: {self.product_name}")
        title_label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Search and filter
        filter_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search batch number...")
        self.search_input.textChanged.connect(self.filter_batches)

        warehouse_label = QLabel("Warehouse:")
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.addItem("All Warehouses", None)
        self.populate_warehouses()
        self.warehouse_combo.currentIndexChanged.connect(self.filter_batches)

        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.search_input, 1)
        filter_layout.addWidget(warehouse_label)
        filter_layout.addWidget(self.warehouse_combo)
        layout.addLayout(filter_layout)

        # Batch table
        columns = [
            TableColumn("selected", "Select", width=70, align="center"),
            TableColumn("batch_number", "Batch #", width=150),
            TableColumn("expiry_date", "Expiry Date", width=110, align="center"),
            TableColumn("remaining_quantity", "Remaining Qty", width=110, align="right"),
            TableColumn("location", "Location", width=140),
            TableColumn("unit_cost", "Unit Cost", width=100, align="right"),
            TableColumn("status", "Status", width=120, align="center"),
        ]
        self.table = EnterpriseTable(columns, density="compact")
        self.table.selection_changed.connect(lambda _rows: self.on_selection_changed())

        layout.addWidget(self.table, 1)

        # Info bar
        info_layout = QHBoxLayout()
        self.info_label = QLabel(f"Required: {self.required_quantity}")
        self.info_label.setFont(QFont("Segoe UI", TEXT_TABLE, QFont.Weight.Bold))
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()

        layout.addLayout(info_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.select_button = EnterpriseButton("Select Batch", variant=ButtonVariant.PRIMARY)
        self.select_button.clicked.connect(self.accept_selection)
        self.select_button.setEnabled(False)

        cancel_button = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.select_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.set_content(widget)

    def populate_warehouses(self):
        self.warehouse_combo.addItem("Main Warehouse", "warehouse-1")
        self.warehouse_combo.addItem("Cold Storage", "warehouse-2")

    def load_batches(self):
        if not self.product_id:
            return

        # Sample data - in production, fetch from API
        self._all_batches = [
            {
                "id": "batch-1",
                "batch_number": "BATCH-2024-001",
                "expiry_date": "2025-06-15",
                "remaining_quantity": 500,
                "location": "Main Warehouse",
                "unit_cost": 45.00,
                "is_expired": False,
                "days_until_expiry": 45,
            },
            {
                "id": "batch-2",
                "batch_number": "BATCH-2024-002",
                "expiry_date": "2025-12-31",
                "remaining_quantity": 1000,
                "location": "Cold Storage",
                "unit_cost": 42.50,
                "is_expired": False,
                "days_until_expiry": 250,
            },
            {
                "id": "batch-3",
                "batch_number": "BATCH-2024-003",
                "expiry_date": "2025-03-01",
                "remaining_quantity": 200,
                "location": "Main Warehouse",
                "unit_cost": 48.00,
                "is_expired": False,
                "days_until_expiry": 5,
            },
        ]
        self.batches = list(self._all_batches)
        self.update_table()

    def update_table(self):
        rows = []
        for batch in self.batches:
            days = batch.get("days_until_expiry", 0)
            if batch.get("is_expired"):
                status = "Expired"
            elif days <= 30:
                status = "Expiring Soon"
            else:
                status = "Active"
            rows.append({
                **batch,
                "selected": "✓" if batch.get("selected") else "",
                "remaining_quantity": str(batch.get("remaining_quantity", 0)),
                "unit_cost": f"${float(batch.get('unit_cost', 0) or 0):.2f}",
                "status": status,
            })
        self.table.set_data(rows)

    def filter_batches(self):
        search_text = self.search_input.text().lower()
        warehouse = self.warehouse_combo.currentData()

        filtered = []
        source = getattr(self, "_all_batches", self.batches)
        for batch in source:
            match_search = search_text in batch["batch_number"].lower() or search_text in batch["location"].lower()
            match_warehouse = warehouse is None or batch["location"] == self.warehouse_combo.currentText()

            if match_search and match_warehouse:
                filtered.append(batch)

        self.batches = filtered
        self.update_table()

    def on_selection_changed(self):
        self.select_button.setEnabled(bool(self.table.get_selected_data()))

    def accept_selection(self):
        selected = self.table.get_selected_data()
        if not selected:
            return

        batch = selected[0]

        if batch["remaining_quantity"] < self.required_quantity:
            if not ConfirmDialog.confirm(
                self,
                "Insufficient Stock",
                f"Batch has {batch['remaining_quantity']} units but {self.required_quantity} required.\n\nSelect anyway?",
            ):
                return

        self.selected_batch = batch
        self.batch_selected.emit(batch)
        self.accept()

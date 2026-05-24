from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QPushButton, QLineEdit,
                               QLabel, QHeaderView, QAbstractItemView, QComboBox,
                               QMessageBox)
from PySide6.QtCore import Qt, Signal
from ui.components.buttons import EnterpriseButton, ButtonVariant
from PySide6.QtGui import QFont
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_LG, TEXT_TABLE, TEXT_CARD_TITLE)


class BatchSelectionDialog(QDialog):
    """Dialog for selecting batches for a product."""

    batch_selected = Signal(dict)

    def __init__(self, parent=None, product_id=None, product_name="", required_quantity=0, api_client=None):
        super().__init__(parent)
        self.product_id = product_id
        self.product_name = product_name
        self.required_quantity = required_quantity
        self.api_client = api_client
        self.batches = []
        self.selected_batch = None

        self.setWindowTitle(f"Select Batch - {product_name}")
        self.setModal(True)
        self.resize(800, 500)
        self.setup_ui()
        self.load_batches()

    def setup_ui(self):
        layout = QVBoxLayout(self)
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
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Select", "Batch #", "Expiry Date", "Remaining Qty", "Location", "Unit Cost", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

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

    def populate_warehouses(self):
        self.warehouse_combo.addItem("Main Warehouse", "warehouse-1")
        self.warehouse_combo.addItem("Cold Storage", "warehouse-2")

    def load_batches(self):
        if not self.product_id:
            return

        # Sample data - in production, fetch from API
        self.batches = [
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
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.batches))
        for row, batch in enumerate(self.batches):
            # Select checkbox
            select_item = QTableWidgetItem("✓" if batch.get("selected") else "")
            select_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, select_item)

            self.table.setItem(row, 1, QTableWidgetItem(batch["batch_number"]))
            self.table.setItem(row, 2, QTableWidgetItem(batch["expiry_date"]))

            qty_item = QTableWidgetItem(str(batch["remaining_quantity"]))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, qty_item)

            self.table.setItem(row, 4, QTableWidgetItem(batch["location"]))

            cost_item = QTableWidgetItem(f"${batch['unit_cost']:.2f}")
            cost_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, cost_item)

            # Status
            days = batch.get("days_until_expiry", 0)
            if batch.get("is_expired"):
                status = "Expired"
            elif days <= 30:
                status = "Expiring Soon"
            else:
                status = "Active"

            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, status_item)

            # Highlight expiring soon
            if days <= 30 and not batch.get("is_expired"):
                for col in range(7):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(Qt.yellow)

    def filter_batches(self):
        search_text = self.search_input.text().lower()
        warehouse = self.warehouse_combo.currentData()

        filtered = []
        for batch in self.batches:
            match_search = search_text in batch["batch_number"].lower() or search_text in batch["location"].lower()
            match_warehouse = warehouse is None or batch["location"] == self.warehouse_combo.currentText()

            if match_search and match_warehouse:
                filtered.append(batch)

        self.batches = filtered
        self.update_table()

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        self.select_button.setEnabled(len(selected_rows) > 0)

    def accept_selection(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        batch = self.batches[row]

        if batch["remaining_quantity"] < self.required_quantity:
            reply = QMessageBox.question(
                self,
                "Insufficient Stock",
                f"Batch has {batch['remaining_quantity']} units but {self.required_quantity} required.\n\nSelect anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.selected_batch = batch
        self.batch_selected.emit(batch)
        self.accept()

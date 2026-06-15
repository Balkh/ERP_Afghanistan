from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLineEdit,
                                QTableWidget, QTableWidgetItem, QHeaderView,
                                QLabel, QAbstractItemView, QWidget)
from PySide6.QtCore import Qt, QTimer
from ui.constants import COLOR_SUCCESS
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.dialogs import EnterpriseDialog, DialogType
from ui.components.tables import build_table_stylesheet

class ProductSelectionDialog(EnterpriseDialog):
    """Professional product selection dialog with search."""
    
    def __init__(self, parent=None, api_client=None):
        self._api_client = api_client
        self.selected_product = None
        super().__init__("Select Product", DialogType.CUSTOM, parent)
        self.setMinimumSize(700, 500)
        self._build_content()
        
        # Search debounce
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        # Initial load
        self.perform_search()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, generic name, barcode, or SKU...")
        self.search_input.textChanged.connect(lambda: self.search_timer.start(300))
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setStyleSheet(build_table_stylesheet())
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Generic Name", "Barcode", "Price", "Stock"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept_selection)
        layout.addWidget(self.table)
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.select_btn = EnterpriseButton("Select", variant=ButtonVariant.PRIMARY)
        self.select_btn.clicked.connect(self.accept_selection)
        btns.addWidget(self.select_btn)
        
        self.cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        
        layout.addLayout(btns)
        
        self.set_content(widget)

    def perform_search(self):
        if not self._api_client:
            return
            
        query = self.search_input.text()
        try:
            # We use the search endpoint
            result = self._api_client.get("/api/inventory/products/", params={'search': query})
            if result and result.get('success'):
                products = result['data'].get('results', [])
                self._populate_table(products)
        except Exception as e:
            print(f"Product search error: {e}")

    def _populate_table(self, products):
        self.table.setRowCount(0)
        for p in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            name_item = QTableWidgetItem(p.get('name', ''))
            name_item.setData(Qt.UserRole, p)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(p.get('generic_name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(p.get('barcode', '')))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.get('sale_price', 0):.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(str(p.get('total_stock', 0))))

    def accept_selection(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.selected_product = self.table.item(current_row, 0).data(Qt.UserRole)
            self.accept()

    def done(self, result):
        """Stop the search timer on dialog close.

        The QTimer lives as long as the dialog and would otherwise keep
        its single-shot queued events. F-26 timer hygiene fix (Phase 5.6).
        """
        if hasattr(self, 'search_timer') and self.search_timer is not None:
            if self.search_timer.isActive():
                self.search_timer.stop()
        super().done(result)

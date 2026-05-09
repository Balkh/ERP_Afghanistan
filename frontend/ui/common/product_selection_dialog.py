from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QPushButton, QLabel, QAbstractItemView)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)

class ProductSelectionDialog(QDialog):
    """Professional product selection dialog with search."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self._api_client = api_client
        self.selected_product = None
        
        self.setWindowTitle("Select Product")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        
        # Search debounce
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        # Initial load
        self.perform_search()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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
        
        self.select_btn = QPushButton("Select")
        self.select_btn.clicked.connect(self.accept_selection)
        self.select_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; font-weight: bold;")
        btns.addWidget(self.select_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        
        layout.addLayout(btns)

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
            
            name_item = QTableWidgetItem(p['name'])
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

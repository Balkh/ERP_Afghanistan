import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLineEdit,
                                QLabel, QWidget)
from PySide6.QtCore import QTimer
from ui.constants import COLOR_SUCCESS
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.dialogs import EnterpriseDialog, DialogType
from ui.components.tables import EnterpriseTable, TableColumn

class ProductSelectionDialog(EnterpriseDialog):
    """Professional product selection dialog with search."""
    
    def __init__(self, parent=None, api_client=None):
        self._api_client = api_client
        self.selected_product = None
        super().__init__("Select Product", DialogType.CUSTOM, parent)
        self.setMinimumSize(700, 500)
        self._build_content()
        
        # Search debounce
        self.search_timer = QTimer(self)
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
        columns = [
            TableColumn("name", "Name", width=180),
            TableColumn("generic_name", "Generic Name", width=150),
            TableColumn("barcode", "Barcode", width=130),
            TableColumn("sale_price", "Price", width=90, align="right"),
            TableColumn("total_stock", "Stock", width=80, align="right"),
        ]
        self.table = EnterpriseTable(columns, density="compact")
        self.table.row_double_clicked.connect(lambda _row, _data: self.accept_selection())
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
                data = result.get('data', {})
                products = data.get('results', []) if isinstance(data, dict) else data if isinstance(data, list) else []
                self._populate_table(products)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Product search error: {e}")

    def _populate_table(self, products):
        rows = []
        for p in products:
            rows.append({
                **p,
                "name": p.get("name", ""),
                "generic_name": p.get("generic_name", ""),
                "barcode": p.get("barcode", ""),
                "sale_price": f"{float(p.get('sale_price', 0) or 0):.2f}",
                "total_stock": str(p.get("total_stock", 0)),
            })
        self.table.set_data(rows)

    def accept_selection(self):
        selected = self.table.get_selected_data()
        if selected:
            self.selected_product = selected[0]
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

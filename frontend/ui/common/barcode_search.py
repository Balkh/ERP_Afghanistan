from PySide6.QtWidgets import (QLineEdit, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QVBoxLayout,
                               QFrame, QLabel, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class BarcodeSearchLineEdit(QLineEdit):
    """LineEdit with barcode scanning support and debounce."""

    barcode_scanned = Signal(str)
    product_selected = Signal(dict)

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self._api_client = api_client
        self.setPlaceholderText("Scan barcode or search product...")

        # Debounce timer for typing (not for barcode scans)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        self.textChanged.connect(self.on_text_changed)

    def set_api_client(self, api_client):
        """Set API client for barcode lookups."""
        self._api_client = api_client

    def on_text_changed(self, text):
        if len(text) >= 8:
            # Likely a barcode scan (barcodes are usually 8+ chars)
            self.barcode_scanned.emit(text)
            self.search_timer.stop()
            self.perform_barcode_search(text)
        elif len(text) >= 2:
            # Regular search with debounce
            self.search_timer.start(300)  # 300ms debounce
        else:
            self.search_timer.stop()

    def perform_barcode_search(self, barcode):
        """Search for product by barcode."""
        if not self._api_client:
            return
        
        try:
            result = self._api_client.lookup_barcode(barcode)
            if result.get('success') and result.get('data'):
                data = result['data']
                product = data.get('product', {})
                product['batches'] = data.get('batches', [])
                product['total_stock'] = data.get('total_stock', 0)
                self.product_selected.emit(product)
                self.clear()
            else:
                # Product not found - try general search
                self.perform_search()
        except Exception as e:
            print(f"Barcode search error: {e}")
            self.perform_search()

    def perform_search(self):
        text = self.text()
        if len(text) < 2:
            return

        if not self._api_client:
            return

        try:
            result = self._api_client.search_products(text)
            if result.get('success') and result.get('data'):
                products = result['data'].get('results', [])
                if products:
                    # Emit the first product for quick selection
                    self.product_selected.emit(products[0])
        except Exception as e:
            print(f"Product search error: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            text = self.text()
            if len(text) >= 8:
                self.barcode_scanned.emit(text)
                self.perform_barcode_search(text)
        super().keyPressEvent(event)


class SearchResultsDropdown(QFrame):
    """Dropdown frame for search results."""

    item_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setMaximumHeight(300)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.results_list)

    def show_results(self, results):
        self.results_list.clear()
        for product in results:
            item = QListWidgetItem(f"{product['name']} - ${product.get('sale_price', 0):.2f}")
            item.setData(Qt.UserRole, product)
            self.results_list.addItem(item)

        if results:
            self.show()
        else:
            self.hide()

    def on_item_clicked(self, item):
        product = item.data(Qt.UserRole)
        self.item_selected.emit(product)
        self.hide()

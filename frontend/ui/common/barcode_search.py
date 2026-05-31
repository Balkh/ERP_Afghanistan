from PySide6.QtWidgets import (QLineEdit, QVBoxLayout, QFrame,
                               QListWidget, QListWidgetItem, QLabel)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QFont
from ui.constants import TEXT_BODY, TEXT_HELPER, SPACING_XS


class BarcodeSearchLineEdit(QLineEdit):
    """LineEdit with barcode scanning support, USB HID timing detection, and debounce."""

    barcode_scanned = Signal(str)
    product_selected = Signal(dict)
    scan_error = Signal(str)

    SCANNER_THRESHOLD_MS = 30
    MIN_BARCODE_LENGTH = 6
    SCANNER_SUFFIX_KEYS = {Qt.Key_Return, Qt.Key_Enter}

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self._api_client = api_client
        self.setPlaceholderText("Scan barcode or search product...")
        self.setFont(QFont("Consolas", TEXT_BODY))

        self._scan_buffer = ""
        self._scan_timer = QTimer()
        self._scan_timer.setSingleShot(True)
        self._scan_timer.timeout.connect(self._finalize_scan)

        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)

        self._last_key_time = 0
        self._is_scanning = False

        self.textChanged.connect(self._on_text_changed)

    def set_api_client(self, api_client):
        """Set API client for barcode lookups."""
        self._api_client = api_client

    def _on_text_changed(self, text):
        if self._is_scanning:
            return

    def event(self, event):
        if event.type() == QEvent.KeyPress:
            key_event = event
            if key_event.key() in self.SCANNER_SUFFIX_KEYS:
                if self._is_scanning and len(self._scan_buffer) >= self.MIN_BARCODE_LENGTH:
                    self._finalize_scan()
                    return True
            elif key_event.key() not in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt,
                                          Qt.Key_Meta, Qt.Key_CapsLock, Qt.Key_Tab):
                import time
                now = int(time.time() * 1000)
                if self._last_key_time > 0:
                    delta = now - self._last_key_time
                    if delta < self.SCANNER_THRESHOLD_MS:
                        if not self._is_scanning:
                            self._is_scanning = True
                            self._scan_buffer = self.text()
                    else:
                        self._is_scanning = False
                        self._scan_buffer = ""
                self._last_key_time = now

        return super().event(event)

    def _finalize_scan(self):
        barcode = self._scan_buffer or self.text()
        if len(barcode) >= self.MIN_BARCODE_LENGTH:
            self.barcode_scanned.emit(barcode)
            self._lookup_barcode(barcode)
        self._scan_buffer = ""
        self._is_scanning = False
        self.clear()

    def _lookup_barcode(self, barcode):
        if not self._api_client:
            self.scan_error.emit("No API client configured")
            return

        try:
            result = self._api_client.lookup_barcode(barcode)
            if result.get('success') and result.get('data'):
                data = result['data']
                product = data.get('product', {})
                product['batches'] = data.get('batches', [])
                product['total_stock'] = data.get('total_stock', 0)
                self.product_selected.emit(product)
                return

            batch_result = self._api_client.lookup_batch_barcode(barcode)
            if batch_result.get('success') and batch_result.get('data'):
                data = batch_result['data']
                product = data.get('product', {})
                product['batch'] = data.get('batch', {})
                product['source'] = 'batch_barcode'
                self.product_selected.emit(product)
                return

            sku_result = self._api_client.lookup_sku(barcode)
            if sku_result.get('success') and sku_result.get('data'):
                data = sku_result['data']
                product = data.get('product', {})
                product['batches'] = data.get('batches', [])
                product['total_stock'] = data.get('total_stock', 0)
                self.product_selected.emit(product)
                return

            self.scan_error.emit(f"Product not found: {barcode}")
        except Exception as e:
            self.scan_error.emit(f"Lookup failed: {e}")

    def _perform_search(self):
        text = self.text()
        if len(text) < 2 or not self._api_client:
            return

        try:
            result = self._api_client.search_products(text)
            if result.get('success') and result.get('data'):
                products = result['data'].get('results', [])
                if products:
                    self.product_selected.emit(products[0])
        except Exception as e:
            print(f"Product search error: {e}")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            text = self.text()
            if len(text) >= self.MIN_BARCODE_LENGTH:
                self.barcode_scanned.emit(text)
                self._lookup_barcode(text)
                self.clear()
                return
        super().keyPressEvent(event)


class SearchResultsDropdown(QFrame):
    """Dropdown frame for search results with optional status display."""

    item_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setMaximumHeight(300)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)

        self.status_label = QLabel()
        self.status_label.setFont(QFont("Segoe UI", TEXT_HELPER, QFont.Weight.Bold))
        self.status_label.hide()
        layout.addWidget(self.status_label)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.results_list)

    def show_results(self, results):
        self.results_list.clear()
        for product in results:
            name = product.get('name', product.get('generic_name', 'Unknown'))
            price = product.get('sale_price', 0)
            stock = product.get('total_stock', product.get('quantity', 0))
            text = f"{name} — {price:.2f} AFN (Stock: {stock})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, product)
            self.results_list.addItem(item)

        if results:
            self.show()
        else:
            self.hide()

    def show_status(self, message, error=False):
        self.status_label.setText(message)
        from ui.constants import COLOR_DANGER, COLOR_SUCCESS
        self.status_label.setStyleSheet(f"color: {COLOR_DANGER if error else COLOR_SUCCESS};")
        self.status_label.show()
        self.hide()

    def hide_status(self):
        self.status_label.hide()

    def _on_item_clicked(self, item):
        product = item.data(Qt.UserRole)
        self.item_selected.emit(product)
        self.hide()

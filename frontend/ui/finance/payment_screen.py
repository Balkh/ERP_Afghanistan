from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT)
"""Payments screen for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                QHeaderView, QAbstractItemView, QComboBox, QGroupBox,
                                QDateEdit, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.constants import (BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, FONT_SIZE_MD)


class PaymentScreen(QWidget):
    """Payments management screen."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client or APIClient()
        self.payments = []
        self._is_loading = False
        self.setup_ui()
        self.load_payments()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Payment Transactions")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setMinimumHeight(35)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_PRIMARY}};
                border: none;
                border-radius: 5px;
                padding: {SPACING_XS} {SPACING_MD};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {{COLOR_PRIMARY_HOVER}};
            }}
        """)
        self.btn_refresh.clicked.connect(self.load_payments)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Filter bar
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading payments...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: 40px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No payments found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: 40px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table section
        self.table = self._create_table()
        layout.addWidget(self.table)

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 10px; color: {COLOR_TEXT_PRIMARY}; }}")
        layout = QHBoxLayout(bar)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Type filter
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("All", "")
        self.type_combo.addItem("Receipt", "RECEIPT")
        self.type_combo.addItem("Payment", "PAYMENT")
        self.type_combo.addItem("Transfer", "TRANSFER")
        self.type_combo.addItem("Refund", "REFUND")
        self.type_combo.setMinimumWidth(120)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Status filter
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("All", "")
        self.status_combo.addItem("Completed", "COMPLETED")
        self.status_combo.addItem("Pending", "PENDING")
        self.status_combo.addItem("Failed", "FAILED")
        self.status_combo.setMinimumWidth(120)
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)

        # Search
        search_layout = QVBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ref # or description...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMinimumHeight(30)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                padding: 5px 10px;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {COLOR_TEXT_MUTED};
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_PRIMARY};
            }}
        """)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Apply button
        self.btn_apply = QPushButton("Apply Filters")
        self.btn_apply.setMinimumHeight(35)
        self.btn_apply.setMinimumWidth(100)
        self.btn_apply.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; border: none; padding: 5px 15px;")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self.load_payments)
        
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        # Apply dark theme to combo boxes
        combo_style = """
            QComboBox {
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                padding: 5px 10px;
                color: {COLOR_TEXT_PRIMARY};
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLOR_TEXT_PRIMARY};
            }
            QComboBox QAbstractItemView {
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_BORDER};
            }
        """
        self.type_combo.setStyleSheet(combo_style)
        self.status_combo.setStyleSheet(combo_style)

        return bar

    def _create_table(self):
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "ID", "Date", "Type", "Amount", "Method", "Account", "Reference", "Status"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                gridline-color: {COLOR_BORDER};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {COLOR_BORDER};
                padding: 10px;
                border: none;
                border-bottom: 2px solid {COLOR_BORDER_LIGHT};
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 10px;
                color: {COLOR_TEXT_PRIMARY};
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_BORDER};
                color: white;
            }}
            QTableWidget alternatingRowColors {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
            }}
            QScrollBar:vertical {{
                background: {COLOR_BG_ELEVATED};
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                border-radius: 4px;
            }}
        """)
        
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)

        return table

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self._is_loading = show
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.btn_refresh.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_empty(self, message="No payments found"):
        """Show empty state."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def _safe_float(self, value, default=0.0):
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def load_payments(self):
        """Load payments from API."""
        self._show_loading()
        try:
            endpoint = get_endpoint("payments")
            if not endpoint:
                endpoint = "/api/payments/transactions/"

            response = self.api_client.get(endpoint)
            self.payments = self._parse_response(response)
            self.update_table()
        except Exception as e:
            print(f"Error loading payments: {e}")
            self.payments = []
            self._show_empty(f"Error loading payments: {e}")

    def _parse_response(self, response):
        """Parse API response."""
        if isinstance(response, list):
            return [p for p in response if isinstance(p, dict)]
        elif isinstance(response, dict):
            if response.get('success'):
                data = response.get('data', [])
                if isinstance(data, list):
                    return [p for p in data if isinstance(p, dict)]
                elif isinstance(data, dict) and 'results' in data:
                    return [p for p in data.get('results', []) if isinstance(p, dict)]
        return []

    def update_table(self):
        """Update table with payment data."""
        if not self.payments:
            self._show_empty("No payments found")
            return

        self._show_data()
        self.table.setRowCount(len(self.payments))
        for row, payment in enumerate(self.payments):
            if not isinstance(payment, dict):
                continue
            self.table.setItem(row, 0, QTableWidgetItem(str(payment.get('id') or '')[:8]))
            self.table.setItem(row, 1, QTableWidgetItem(str(payment.get('transaction_date') or '')[:10]))
            self.table.setItem(row, 2, QTableWidgetItem(payment.get('transaction_type') or ''))
            self.table.setItem(row, 3, QTableWidgetItem(f"{self._safe_float(payment.get('amount')):,.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(payment.get('payment_method') or ''))
            self.table.setItem(row, 5, QTableWidgetItem(payment.get('account_name') or ''))
            self.table.setItem(row, 6, QTableWidgetItem(payment.get('reference_number') or ''))
            self.table.setItem(row, 7, QTableWidgetItem(payment.get('status') or ''))
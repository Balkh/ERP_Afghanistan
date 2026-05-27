"""Payments screen for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QLineEdit, QHeaderView,
                                QAbstractItemView, QComboBox, QGroupBox, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           TEXT_LABEL, BORDER_RADIUS_SM, BORDER_RADIUS_LG, COLOR_BORDER, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


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
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_payments)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Filter bar
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading payments...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No payments found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table section
        self.table = self._create_table()
        layout.addWidget(self.table)

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar_font = QFont("Segoe UI", TEXT_LABEL)
        bar_font.setWeight(QFont.Weight.Bold)
        bar.setFont(bar_font)
        bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; margin-top: {PADDING_INPUT_H}px; padding-top: {PADDING_INPUT_H}px; color: {COLOR_TEXT_PRIMARY}; }}")
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
        self.search_input.setStyleSheet("""
            QLineEdit {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM};
                padding: {SPACING_XS}px {SPACING_SM}px;
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
        self.btn_apply = EnterpriseButton(text="Apply Filters", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_apply.clicked.connect(self.load_payments)
        
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        # Apply dark theme to combo boxes
        combo_style = """
            QComboBox {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM};
                padding: {SPACING_XS}px {SPACING_SM}px;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLOR_TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_BORDER};
            }}
        """
        self.type_combo.setStyleSheet(combo_style)
        self.status_combo.setStyleSheet(combo_style)

        return bar

    def _create_table(self):
        columns = [
            TableColumn("id", "ID", width=60),
            TableColumn("date", "Date", width=100, align="center"),
            TableColumn("type", "Type", width=80),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("method", "Method", width=100),
            TableColumn("account", "Account", width=120),
            TableColumn("reference", "Reference", width=120),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        table = EnterpriseTable(columns)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        table.setSelectionMode(QAbstractItemView.SingleSelection)
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
        data = []
        for payment in self.payments:
            if not isinstance(payment, dict):
                continue
            data.append({
                "id": str(payment.get('id') or '')[:8],
                "date": str(payment.get('transaction_date') or '')[:10],
                "type": payment.get('transaction_type') or '',
                "amount": f"{self._safe_float(payment.get('amount')):,.2f}",
                "method": payment.get('payment_method') or '',
                "account": payment.get('account_name') or '',
                "reference": payment.get('reference_number') or '',
                "status": payment.get('status') or '',
            })
        self.table.set_data(data)
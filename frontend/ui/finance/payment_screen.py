"""Payments screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                QLabel, QLineEdit, QHeaderView,
                                QAbstractItemView, QComboBox, QGroupBox, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                            TEXT_LABEL, BORDER_RADIUS_SM, BORDER_RADIUS_LG, COLOR_BORDER, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from utils.format import safe_float
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.state_helper import StateHelper
from ui.screens.base_screen import BaseScreen


class PaymentScreen(BaseScreen):
    """Payments management screen."""

    def __init__(self, parent=None, api_client=None):
        self.api_client = api_client or APIClient()
        self.payments = []
        self._is_loading = False
        super().__init__(parent)

    def _on_screen_shown(self):
        pass

    def load_data(self, params=None):
        self.load_payments()
        super().load_data(params)

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Enterprise header
        header = PageHeader(
            "Payment Transactions",
            "Monitor receipts, payments, transfers and refunds without blocking the operator workspace.",
            "FINANCE OPERATIONS",
        )
        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_payments)
        header.add_action(self.btn_refresh)
        layout.addWidget(header)

        # Filter bar
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        # Table section
        self.table = self._create_table()
        layout.addWidget(self.table)

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar_font = QFont("Segoe UI", TEXT_LABEL)
        bar_font.setWeight(QFont.Weight.Bold)
        bar.setFont(bar_font)
        bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-left: 4px solid {COLOR_PRIMARY}; border-radius: {BORDER_RADIUS_LG}px; margin-top: {PADDING_INPUT_H}px; padding-top: {PADDING_INPUT_H}px; color: {COLOR_TEXT_PRIMARY}; }}")
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
        combo_style = f"""
            QComboBox {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM}px;
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
        if show:
            self.state_helper.show_loading("Loading payments...")
            self.table.setVisible(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.state_helper.hide()
            self.table.setVisible(True)
            self.btn_refresh.setEnabled(True)

    def _show_empty(self, message="No payments found"):
        """Show empty state."""
        self._is_loading = False
        self.state_helper.show_empty(title=message)
        self.table.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_error(self, message="Error loading payments"):
        """Show error state."""
        self._is_loading = False
        self.state_helper.show_error(message, on_retry=self.load_payments)
        self.table.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self._is_loading = False
        self.state_helper.hide()
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)


    def load_payments(self):
        """Load payments from API."""
        self._show_loading()
        try:
            endpoint = get_endpoint("payments")
            if not endpoint:
                endpoint = "/api/payments/transactions/"

            if not hasattr(self, "_async_payments_response"):
                self.run_api_request(
                    "payments:list", "GET", endpoint,
                    on_success=lambda r: self._resume_api_request("_async_payments_response", self.load_payments, r),
                    on_error=lambda m: self._resume_api_request("_async_payments_response", self.load_payments, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_payments_response")
            self.payments = extract_list(response)
            self.update_table()
        except Exception as e:
            self.payments = []
            self._show_error(f"Error loading payments: {e}")

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
                "amount": f"{safe_float(payment.get('amount')):,.2f}",
                "method": payment.get('payment_method') or '',
                "account": payment.get('account_name') or '',
                "reference": payment.get('reference_number') or '',
                "status": payment.get('status') or '',
            })
        self.table.set_data(data)
"""Phase 20: Payment Allocation Explorer screen."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox,
)
from PySide6.QtCore import Qt

from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE,
    TEXT_PAGE_TITLE, TEXT_BODY, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_BG_ELEVATED, COLOR_BORDER,
    BORDER_RADIUS_SM,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.kpi_cards import MiniMetricCard, SectionHeader
from ui.components.state_helper import StateHelper
from ui.components.styles import combo_stylesheet
from utils.format import safe_float
from ui.screens.base_screen import BaseScreen


class PaymentAllocationExplorer(BaseScreen):
    """Payment allocation explorer - trace payment allocations across invoices."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="allocation_explorer")
        self.api_client = api_client or APIClient()
        self.entity_type = "customer"
        self.entity_id = None
        self._is_loading = False
        self.setup_ui()
        self._load_entities()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load in __init__."""

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Payment Allocation Explorer")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.entity_type_combo = QComboBox()
        self.entity_type_combo.addItem("Customer", "customer")
        self.entity_type_combo.addItem("Supplier", "supplier")
        self.entity_type_combo.currentIndexChanged.connect(self._on_entity_type_changed)
        self.entity_type_combo.setStyleSheet(combo_stylesheet(min_height=30, custom_arrow=False))
        header_layout.addWidget(QLabel("Type:"))
        header_layout.addWidget(self.entity_type_combo)

        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(250)
        self.entity_combo.setStyleSheet(combo_stylesheet(min_height=30, custom_arrow=False))
        self.entity_combo.currentIndexChanged.connect(self._on_entity_selected)
        header_layout.addWidget(QLabel("Entity:"))
        header_layout.addWidget(self.entity_combo)

        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.refresh)
        header_layout.addWidget(self.btn_refresh)

        layout.addLayout(header_layout)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        # Content
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(SPACING_LG)

        # KPI row
        kpi_layout = QGridLayout()
        kpi_layout.setSpacing(SPACING_MD)
        self.kpi_total_payments = MiniMetricCard("Total Payments", "0", COLOR_PRIMARY)
        self.kpi_total_allocated = MiniMetricCard("Total Allocated", "0.00", COLOR_SUCCESS)
        self.kpi_unallocated = MiniMetricCard("Unallocated", "0.00", COLOR_DANGER)
        kpi_layout.addWidget(self.kpi_total_payments, 0, 0)
        kpi_layout.addWidget(self.kpi_total_allocated, 0, 1)
        kpi_layout.addWidget(self.kpi_unallocated, 0, 2)
        content_layout.addLayout(kpi_layout)

        # Payment trace table
        section = SectionHeader("Payment Allocation Trace")
        content_layout.addWidget(section)

        columns = [
            TableColumn("payment_number", "Payment #", width=120),
            TableColumn("payment_date", "Date", width=100, align="center"),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("allocated", "Allocated", width=100, align="right"),
            TableColumn("unallocated", "Unallocated", width=100, align="right"),
            TableColumn("method", "Method", width=100),
            TableColumn("invoices_paid", "Invoices Paid", width=100, align="center"),
        ]
        self.trace_table = EnterpriseTable(columns)
        self.trace_table.set_density("compact")
        content_layout.addWidget(self.trace_table)

        layout.addWidget(self.content_widget)
        self.content_widget.setVisible(False)

    def _load_entities(self):
        """Load entities for dropdown."""
        self._on_entity_type_changed()

    def _on_entity_type_changed(self):
        """Handle entity type change."""
        self.entity_type = self.entity_type_combo.currentData()
        self.entity_combo.clear()
        self.entity_combo.addItem("-- Select --", None)

        try:
            endpoint = get_endpoint(f"{self.entity_type}s") or f"/api/{self.entity_type}s/{self.entity_type}s/"
            response = self.api_client.get(endpoint, params={"page_size": 100})
            entities = extract_list(response)
            for e in entities:
                self.entity_combo.addItem(e.get("name", ""), e.get("id"))
        except Exception as e:
            print(f"Error loading {self.entity_type}s: {e}")

    def _on_entity_selected(self, index):
        """Handle entity selection."""
        entity_id = self.entity_combo.itemData(index)
        if entity_id:
            self.entity_id = entity_id
            self.load_allocations(entity_id)

    def load_allocations(self, entity_id):
        """Load payment allocation trace."""
        self._show_loading()
        try:
            endpoint = f"/api/v1/payment-operations/{self.entity_type}s/{entity_id}/payment-trace/"
            response = self.api_client.get(endpoint)
            if response and response.get("success"):
                data = response.get("data", {})
                self._update_display(data)
            else:
                self._show_error("Failed to load allocations")
        except Exception as e:
            print(f"Error loading allocations: {e}")
            self._show_error(f"Error: {e}")
        self._show_data()

    def _update_display(self, data):
        """Update display with allocation data."""
        payments = data.get("payment_trace", [])
        total_payments = data.get("total_payments", len(payments))
        total_allocated = sum(safe_float(p.get("allocated_amount", 0)) for p in payments)
        total_unallocated = sum(safe_float(p.get("unallocated_amount", 0)) for p in payments)

        self.kpi_total_payments.update_value(str(total_payments))
        self.kpi_total_allocated.update_value(f"{total_allocated:,.2f}")
        self.kpi_unallocated.update_value(f"{total_unallocated:,.2f}")

        # Update table
        table_data = []
        for p in payments:
            table_data.append({
                "payment_number": p.get("payment_number", ""),
                "payment_date": str(p.get("payment_date", ""))[:10],
                "amount": f"{safe_float(p.get('amount', 0)):,.2f}",
                "allocated": f"{safe_float(p.get('allocated_amount', 0)):,.2f}",
                "unallocated": f"{safe_float(p.get('unallocated_amount', 0)):,.2f}",
                "method": p.get("payment_method", ""),
                "invoices_paid": str(p.get("invoices_paid_count", 0)),
            })
        self.trace_table.set_data(table_data)

    def _show_loading(self, show=True):
        self._is_loading = show
        if show:
            self.state_helper.show_loading("Loading allocations...")
            self.content_widget.setVisible(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.state_helper.hide()
            self.content_widget.setVisible(True)
            self.btn_refresh.setEnabled(True)

    def _show_empty(self, message="No data to display"):
        self._is_loading = False
        self.state_helper.show_empty(title=message)
        self.content_widget.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        self._is_loading = False
        self.state_helper.hide()
        self.content_widget.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def _show_error(self, message):
        self._is_loading = False
        self.state_helper.show_error(message, on_retry=self.refresh)
        self.content_widget.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def refresh(self):
        """Refresh allocations."""
        if self.entity_id:
            self.load_allocations(self.entity_id)


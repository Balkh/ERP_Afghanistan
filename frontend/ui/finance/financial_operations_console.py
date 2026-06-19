"""Phase 20: Unified Financial Operations Console - cohesive dashboard for all financial operations."""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt

from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (
    SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_INFO, COLOR_BG_CARD, COLOR_BORDER,
    BORDER_RADIUS_LG,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from utils.format import safe_float
from ui.components.kpi_cards import MiniMetricCard, SectionHeader
from ui.components.state_helper import StateHelper
from ui.screens.base_screen import BaseScreen


class FinancialOperationsConsole(BaseScreen):
    """Unified financial operations console - single pane of glass for all financial operations."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="operations_console")
        self.api_client = api_client or APIClient()
        self._is_loading = False
        self.setup_ui()
        self.load_dashboard()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load in __init__."""

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        main_layout.setSpacing(SPACING_LG)

        # Enterprise header
        header = PageHeader(
            "Financial Operations Console",
            "Single-pane oversight for payments, allocations, returns and financial health signals.",
            "FINANCIAL COMMAND",
        )

        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_dashboard)
        header.add_action(self.btn_refresh)

        main_layout.addWidget(header)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(main_layout)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setSpacing(SPACING_XL)

        # Section 1: Payment Operations
        payment_section = self._create_payment_section()
        content_layout.addWidget(payment_section)

        # Section 2: Allocation Status
        allocation_section = self._create_allocation_section()
        content_layout.addWidget(allocation_section)

        # Section 3: Returns & Reversals
        returns_section = self._create_returns_section()
        content_layout.addWidget(returns_section)

        # Section 4: Financial Health
        health_section = self._create_health_section()
        content_layout.addWidget(health_section)

        content_layout.addStretch()

        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

        self.content_widget.setVisible(False)

    def _create_card(self, title, content_widget):
        """Create a standard card with title and content."""
        card = QFrame()
        card.setObjectName("financeCard")
        card.setStyleSheet(f"""
            QFrame#financeCard {{
                background-color: {COLOR_BG_CARD};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG}px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        header = SectionHeader(title)
        layout.addWidget(header)
        layout.addWidget(content_widget)

        return card

    def _create_payment_section(self):
        """Create payment operations section."""
        content = QWidget()
        layout = QGridLayout(content)
        layout.setSpacing(SPACING_MD)

        self.pay_kpi_1 = MiniMetricCard("Customer Payments Today", "0", COLOR_SUCCESS)
        self.pay_kpi_2 = MiniMetricCard("Supplier Payments Today", "0", COLOR_PRIMARY)
        self.pay_kpi_3 = MiniMetricCard("Pending Receipts", "0", COLOR_WARNING)
        self.pay_kpi_4 = MiniMetricCard("Total Volume", "0.00", COLOR_INFO)
        layout.addWidget(self.pay_kpi_1, 0, 0)
        layout.addWidget(self.pay_kpi_2, 0, 1)
        layout.addWidget(self.pay_kpi_3, 0, 2)
        layout.addWidget(self.pay_kpi_4, 0, 3)

        return self._create_card("Payment Operations", content)

    def _create_allocation_section(self):
        """Create allocation status section."""
        content = QWidget()
        layout = QGridLayout(content)
        layout.setSpacing(SPACING_MD)

        self.alloc_kpi_1 = MiniMetricCard("Unallocated Customer", "0.00", COLOR_WARNING)
        self.alloc_kpi_2 = MiniMetricCard("Unallocated Supplier", "0.00", COLOR_DANGER)
        self.alloc_kpi_3 = MiniMetricCard("Allocations Today", "0", COLOR_SUCCESS)
        self.alloc_kpi_4 = MiniMetricCard("FIFO Efficiency", "100%", COLOR_PRIMARY)
        layout.addWidget(self.alloc_kpi_1, 0, 0)
        layout.addWidget(self.alloc_kpi_2, 0, 1)
        layout.addWidget(self.alloc_kpi_3, 0, 2)
        layout.addWidget(self.alloc_kpi_4, 0, 3)

        return self._create_card("Allocation Status", content)

    def _create_returns_section(self):
        """Create returns & reversals section."""
        content = QWidget()
        layout = QGridLayout(content)
        layout.setSpacing(SPACING_MD)

        self.ret_kpi_1 = MiniMetricCard("Returns Today", "0", COLOR_WARNING)
        self.ret_kpi_2 = MiniMetricCard("Returns Value", "0.00", COLOR_DANGER)
        self.ret_kpi_3 = MiniMetricCard("Journals Reversed", "0", COLOR_INFO)
        self.ret_kpi_4 = MiniMetricCard("Pending Reconciliation", "0", COLOR_PRIMARY)
        layout.addWidget(self.ret_kpi_1, 0, 0)
        layout.addWidget(self.ret_kpi_2, 0, 1)
        layout.addWidget(self.ret_kpi_3, 0, 2)
        layout.addWidget(self.ret_kpi_4, 0, 3)

        return self._create_card("Returns & Reversals", content)

    def _create_health_section(self):
        """Create financial health section."""
        content = QWidget()
        layout = QGridLayout(content)
        layout.setSpacing(SPACING_MD)

        self.health_kpi_1 = MiniMetricCard("AR Balance", "0.00", COLOR_PRIMARY)
        self.health_kpi_2 = MiniMetricCard("AP Balance", "0.00", COLOR_DANGER)
        self.health_kpi_3 = MiniMetricCard("Net Position", "0.00", COLOR_SUCCESS)
        self.health_kpi_4 = MiniMetricCard("Cash Position", "0.00", COLOR_INFO)
        layout.addWidget(self.health_kpi_1, 0, 0)
        layout.addWidget(self.health_kpi_2, 0, 1)
        layout.addWidget(self.health_kpi_3, 0, 2)
        layout.addWidget(self.health_kpi_4, 0, 3)

        return self._create_card("Financial Health", content)

    def _show_loading(self, show=True):
        self._is_loading = show
        if show:
            self.state_helper.show_loading("Loading dashboard...")
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
        self.state_helper.show_error(message, on_retry=self.load_dashboard)
        self.content_widget.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def load_dashboard(self):
        """Load all dashboard data."""
        self._show_loading()
        try:
            self._load_payment_data()
            self._load_allocation_data()
            self._load_returns_data()
            self._load_health_data()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading dashboard: {e}")
            self._show_error(f"Error: {e}")
        self._show_data()

    def _load_payment_data(self):
        """Load payment metrics."""
        try:
            endpoint = "/api/payments/transactions/"
            if not hasattr(self, "_async_ops_payments_response"):
                self.run_api_request(
                    "operations_console:payments", "GET", endpoint, params={"page_size": 100},
                    on_success=lambda r: self._resume_api_request("_async_ops_payments_response", self._load_payment_data, r),
                    on_error=lambda m: self._resume_api_request("_async_ops_payments_response", self._load_payment_data, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_ops_payments_response")
            payments = extract_list(response)
            self.pay_kpi_1.update_value(str(len([p for p in payments if p.get("transaction_type") == "RECEIPT"])))
            self.pay_kpi_2.update_value(str(len([p for p in payments if p.get("transaction_type") == "PAYMENT"])))
            self.pay_kpi_3.update_value(str(len([p for p in payments if p.get("status") == "PENDING"])))
            total = sum(safe_float(p.get("amount", 0)) for p in payments)
            self.pay_kpi_4.update_value(f"{total:,.2f}")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading payment data: {e}")

    def _load_allocation_data(self):
        """Load allocation metrics."""
        # Placeholder - would call allocation endpoints
        self.alloc_kpi_1.update_value("0.00")
        self.alloc_kpi_2.update_value("0.00")
        self.alloc_kpi_3.update_value("0")
        self.alloc_kpi_4.update_value("100%")

    def _load_returns_data(self):
        """Load returns metrics."""
        try:
            endpoint = get_endpoint("returns") or "/api/returns/orders/"
            if not hasattr(self, "_async_ops_returns_response"):
                self.run_api_request(
                    "operations_console:returns", "GET", endpoint, params={"page_size": 100},
                    on_success=lambda r: self._resume_api_request("_async_ops_returns_response", self._load_returns_data, r),
                    on_error=lambda m: self._resume_api_request("_async_ops_returns_response", self._load_returns_data, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_ops_returns_response")
            returns = extract_list(response)
            self.ret_kpi_1.update_value(str(len(returns)))
            total = sum(safe_float(r.get("total_amount", 0)) for r in returns)
            self.ret_kpi_2.update_value(f"{total:,.2f}")
            self.ret_kpi_3.update_value(str(len([r for r in returns if r.get("journal_entry_reversed")])))
            self.ret_kpi_4.update_value(str(len([r for r in returns if r.get("status") == "PENDING"])))
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading returns data: {e}")

    def _load_health_data(self):
        """Load financial health metrics."""
        # Placeholder - would call SSOT/FCUE endpoints
        self.health_kpi_1.update_value("0.00")
        self.health_kpi_2.update_value("0.00")
        self.health_kpi_3.update_value("0.00")
        self.health_kpi_4.update_value("0.00")

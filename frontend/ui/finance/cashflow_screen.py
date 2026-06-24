"""Cashflow management screen."""
import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QComboBox,
                                  QGroupBox, QTabWidget, QProgressBar,
                                  QApplication, QFrame, QWidget)
from PySide6.QtCore import Qt
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY_SMALL,
                           BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TABLE_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY,
                           COLOR_SUCCESS, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.state_helper import StateHelper


class CashflowScreen(BaseScreen):
    """Screen for managing cash flow."""

    def __init__(self, parent=None, screen_id="cashflow", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self.api_client = api_client or APIClient()
        self._cashflow_data = []
        self._forecast_data = []
        self._position_data = []
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Enterprise header
        header = PageHeader(
            "Cash Flow Management",
            "Track liquidity, forecast movement and monitor cash position in one controlled workspace.",
            "TREASURY CONTROL",
        )
        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header.add_action(self.btn_refresh)
        layout.addWidget(header)

        # Summary Cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(SPACING_MD + SPACING_XS)

        self.inflow_card = self._create_summary_card("Cash Inflow", "0.00 AFN", COLOR_SUCCESS)
        self.outflow_card = self._create_summary_card("Cash Outflow", "0.00 AFN", COLOR_DANGER)
        self.net_card = self._create_summary_card("Net Cash Flow", "0.00 AFN", COLOR_PRIMARY)

        summary_layout.addWidget(self.inflow_card)
        summary_layout.addWidget(self.outflow_card)
        summary_layout.addWidget(self.net_card)
        layout.addLayout(summary_layout)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; background: {COLOR_BG_SURFACE}; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; padding: {SPACING_MD}px {SPACING_XL}px; border-top-left-radius: {BORDER_RADIUS_MD}px; border-top-right-radius: {BORDER_RADIUS_MD}px; }}
            QTabBar::tab:selected {{ background: {COLOR_BG_SURFACE}; border-bottom-color: {COLOR_BG_SURFACE}; font-weight: bold; }}
        """)

        # Cash Flow Statement Tab
        self.statement_tab = QWidget()
        self._setup_statement_tab()
        self.tabs.addTab(self.statement_tab, "Cash Flow Statement")

        # Forecast Tab
        self.forecast_tab = QWidget()
        self._setup_forecast_tab()
        self.tabs.addTab(self.forecast_tab, "Cash Forecast")

        # Cash Position Tab
        self.position_tab = QWidget()
        self._setup_position_tab()
        self.tabs.addTab(self.position_tab, "Cash Position")

        layout.addWidget(self.tabs)

    def _create_summary_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_SURFACE};
                border-left: 5px solid {color};
                border-radius: {BORDER_RADIUS_LG}px;
                border-top: 1px solid {COLOR_TABLE_BORDER_LIGHT};
                border-right: 1px solid {COLOR_TABLE_BORDER_LIGHT};
                border-bottom: 1px solid {COLOR_TABLE_BORDER_LIGHT};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-weight: bold; font-size: {TEXT_BODY_SMALL}pt;")
        
        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setStyleSheet(f"color: {color}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        value_label.setWordWrap(True)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card

    def _update_summary_card(self, card, value):
        label = card.findChild(QLabel, "value_label")
        if label:
            label.setText(value)

    def _create_table(self, columns):
        return EnterpriseTable(columns)

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        if show:
            self.state_helper.show_loading("Loading cash flow data...")
            self.tabs.setVisible(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.state_helper.hide()
            self.tabs.setVisible(True)
            self.btn_refresh.setEnabled(True)

    def _show_empty(self, message="No cash flow data available"):
        """Show empty state."""
        self.state_helper.show_empty(title=message)
        self.tabs.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_error(self, message="Error loading cash flow data"):
        """Show error state."""
        self.state_helper.show_error(message, on_retry=self.load_data)
        self.tabs.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data tabs."""
        self.state_helper.hide()
        self.tabs.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def load_data(self):
        """Main load data method."""
        self._load_cashflow_data()

    def _load_cashflow_data(self):
        """Load cash flow data from API."""
        self._show_loading()
        try:
            endpoint = get_endpoint("cashflow")
            if not endpoint:
                endpoint = "/api/cashflow/items/"

            if not hasattr(self, "_async_cashflow_response"):
                self.run_api_request(
                    "cashflow:data", "GET", endpoint,
                    on_success=lambda r: self._resume_api_request("_async_cashflow_response", self._load_cashflow_data, r),
                    on_error=lambda m: self._resume_api_request("_async_cashflow_response", self._load_cashflow_data, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_cashflow_response")
            if response and isinstance(response, dict) and response.get('success'):
                data = response.get('data', {})
                self._cashflow_data = data.get('cash_flow', []) or data.get('entries', []) or []
                self._update_summary_cards_from_data(data)
            else:
                self._cashflow_data = []

            self._load_statement()
            self._load_forecast()
            self._load_position()
            self._show_data()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading cashflow: {e}")
            self._cashflow_data = []
            self._show_empty(f"Error loading cash flow data: {e}")

    def _update_summary_cards_from_data(self, data):
        """Update summary cards with real data."""
        inflow = data.get('total_inflow', 0)
        outflow = data.get('total_outflow', 0)
        net = data.get('net_cash_flow', 0)
        
        self._update_summary_card(self.inflow_card, f"{float(inflow):,.2f} AFN")
        self._update_summary_card(self.outflow_card, f"{float(outflow):,.2f} AFN")
        self._update_summary_card(self.net_card, f"{float(net):,.2f} AFN")
    
    def _setup_statement_tab(self):
        layout = QVBoxLayout(self.statement_tab)
        layout.setSpacing(SPACING_MD)
        
        filter_layout = QHBoxLayout()
        self.period_filter = QComboBox()
        self.period_filter.addItems(["May 2026", "April 2026", "Q1 2026", "Year 2026"])
        filter_layout.addWidget(QLabel("Period:"))
        filter_layout.addWidget(self.period_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        columns = [
            TableColumn("category", "Category", width=200),
            TableColumn("this_str", "This Period", width=120, align="right"),
            TableColumn("prev_str", "Previous Period", width=120, align="right"),
            TableColumn("change_str", "Change", width=80, align="center"),
        ]
        self.statement_table = self._create_table(columns)
    
    def _setup_forecast_tab(self):
        layout = QVBoxLayout(self.forecast_tab)
        layout.setSpacing(SPACING_MD)
        
        forecast_group = QGroupBox("30-Day Cash Forecast")
        forecast_layout = QVBoxLayout()
        self.forecast_progress = QProgressBar()
        self.forecast_progress.setValue(0)
        forecast_layout.addWidget(self.forecast_progress)
        self.forecast_label = QLabel("Projected Ending Cash: 0.00 AFN")
        forecast_layout.addWidget(self.forecast_label)
        forecast_group.setLayout(forecast_layout)
        layout.addWidget(forecast_group)
        
        columns = [
            TableColumn("date", "Date", width=90, align="center"),
            TableColumn("inflow", "Expected Inflows", width=120, align="right"),
            TableColumn("outflow", "Expected Outflows", width=120, align="right"),
            TableColumn("net", "Net", width=100, align="right"),
            TableColumn("balance", "Running Balance", width=120, align="right"),
        ]
        self.forecast_table = self._create_table(columns)
        layout.addWidget(self.forecast_table)
    
    def _setup_position_tab(self):
        layout = QVBoxLayout(self.position_tab)
        layout.setSpacing(SPACING_MD)
        
        columns = [
            TableColumn("date", "Date", width=90, align="center"),
            TableColumn("desc", "Description", width=200),
            TableColumn("re", "Reference", width=100),
            TableColumn("type", "Type", width=80),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("balance", "Balance", width=100, align="right"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.position_table = self._create_table(columns)
        layout.addWidget(self.position_table)

    def _load_statement(self):
        if not self._cashflow_data:
            mock_data = [
                {"category": "Operating Activities", "this_str": "1,800,000", "prev_str": "1,500,000", "change_str": "+20%"},
                {"category": "Investing Activities", "this_str": "-150,000", "prev_str": "-200,000", "change_str": "-25%"},
                {"category": "Financing Activities", "this_str": "-50,000", "prev_str": "-50,000", "change_str": "0%"},
            ]
        else:
            mock_data = [] # Use real data mapping here
            
        self.statement_table.set_data(mock_data)

    def _load_forecast(self):
        self.forecast_table.setRowCount(0)
        try:
            endpoint = get_endpoint("cashflow_forecasts") or "/api/cashflow/forecasts/"
            if not hasattr(self, "_async_forecast_response"):
                self.run_api_request(
                    "cashflow:forecast", "GET", endpoint,
                    on_success=lambda r: self._resume_api_request("_async_forecast_response", self._load_forecast, r),
                    on_error=lambda m: self._resume_api_request("_async_forecast_response", self._load_forecast, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_forecast_response")
            if response and isinstance(response, dict) and response.get("success"):
                raw_data = response.get("data", [])
                data = raw_data.get("results", []) if isinstance(raw_data, dict) else raw_data
            else:
                data = []
            
            if not data:
                data = [
                    {"date": "2026-05-06", "expected_inflow": "50000", "expected_outflow": "30000", "net": "20000", "running_balance": "620000"},
                    {"date": "2026-05-07", "expected_inflow": "80000", "expected_outflow": "45000", "net": "35000", "running_balance": "655000"},
                ]
        except Exception:
            data = [
                {"date": "2026-05-06", "expected_inflow": "50000", "expected_outflow": "30000", "net": "20000", "running_balance": "620000"},
                {"date": "2026-05-07", "expected_inflow": "80000", "expected_outflow": "45000", "net": "35000", "running_balance": "655000"},
            ]
        
        table_data = []
        for item in data:
            table_data.append({
                "date": item.get("date", ""),
                "inflow": item.get("expected_inflow", "0"),
                "outflow": item.get("expected_outflow", "0"),
                "net": item.get("net", "0"),
                "balance": item.get("running_balance", "0"),
            })
        self.forecast_table.set_data(table_data)

    def _load_position(self):
        self.position_table.setRowCount(0)
        try:
            endpoint = get_endpoint("cashflow_items") or "/api/cashflow/items/"
            if not hasattr(self, "_async_position_response"):
                self.run_api_request(
                    "cashflow:position", "GET", endpoint,
                    on_success=lambda r: self._resume_api_request("_async_position_response", self._load_position, r),
                    on_error=lambda m: self._resume_api_request("_async_position_response", self._load_position, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_position_response")
            if response and isinstance(response, dict) and response.get("success"):
                raw_data = response.get("data", [])
                data = raw_data.get("results", []) if isinstance(raw_data, dict) else raw_data
            else:
                data = []
            
            if not data:
                data = [
                    {"date": "2026-05-05", "description": "Sales Invoice Payment", "reference": "INV-001", "item_type": "Inflow", "amount": "50000", "balance_after": "600000", "status": "Cleared"},
                ]
        except Exception:
            data = [
                {"date": "2026-05-05", "description": "Sales Invoice Payment", "reference": "INV-001", "item_type": "Inflow", "amount": "50000", "balance_after": "600000", "status": "Cleared"},
            ]
        
        table_data = []
        for item in data:
            table_data.append({
                "date": item.get("date", ""),
                "desc": item.get("description", ""),
                "re": item.get("reference", ""),
                "type": item.get("item_type", ""),
                "amount": item.get("amount", "0"),
                "balance": item.get("balance_after", "0"),
                "status": item.get("status", ""),
            })
        self.position_table.set_data(table_data)

    def _on_screen_shown(self):
        """Called when screen is shown.

        P-REC: super()._on_screen_shown() already loads data ONCE (via the
        _data_loaded_once guard in BaseScreen). The previous explicit
        self.load_data() here re-fetched cashflow on every navigation visit.
        Use refresh_data() to force a reload.
        """
        super()._on_screen_shown()

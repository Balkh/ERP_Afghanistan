"""Tax management screen."""
import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QComboBox, QWidget,
                                  QTabWidget, QApplication)
from PySide6.QtCore import Qt
from api.client import APIClient
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           BORDER_RADIUS_MD, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.state_helper import StateHelper


class TaxScreen(BaseScreen):
    """Screen for managing tax configurations and filings."""
    
    def __init__(self, parent=None, screen_id="tax", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self.api_client = api_client or APIClient()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Enterprise header
        header = PageHeader(
            "Tax Management",
            "Govern tax rates, filings and withholding activity from one compliance workspace.",
            "COMPLIANCE CONTROL",
        )
        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header.add_action(self.btn_refresh)
        layout.addWidget(header)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; background: {COLOR_BG_SURFACE}; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; padding: {SPACING_MD}px {SPACING_XL}px; border-top-left-radius: {BORDER_RADIUS_MD}px; border-top-right-radius: {BORDER_RADIUS_MD}px; }}
            QTabBar::tab:selected {{ background: {COLOR_BG_SURFACE}; border-bottom-color: {COLOR_BG_SURFACE}; font-weight: bold; }}
        """)
        
        # Tax Configuration Tab
        self.config_tab = QWidget()
        self._setup_config_tab()
        self.tabs.addTab(self.config_tab, "Tax Configuration")
        
        # Tax Returns Tab
        self.returns_tab = QWidget()
        self._setup_returns_tab()
        self.tabs.addTab(self.returns_tab, "Tax Returns")
        
        # Withholding Tab
        self.withholding_tab = QWidget()
        self._setup_withholding_tab()
        self.tabs.addTab(self.withholding_tab, "Withholding")
        
        layout.addWidget(self.tabs)
    
    def _setup_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        self.add_rate_btn = EnterpriseButton(text="+ Add Tax Rate", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        action_layout.addWidget(self.add_rate_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("name", "Tax Name", width=150),
            TableColumn("rate", "Rate %", width=60, align="center"),
            TableColumn("type", "Type", width=100),
            TableColumn("code", "Code", width=80),
            TableColumn("effective_from", "Effective From", width=100, align="center"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.config_table = self._create_table(columns)
        
        self._load_config()

    def _create_table(self, columns):
        table = EnterpriseTable(columns)
        return table

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        if show:
            self.state_helper.show_loading("Loading tax data...")
            self.tabs.setVisible(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.state_helper.hide()
            self.tabs.setVisible(True)
            self.btn_refresh.setEnabled(True)

    def _show_empty(self, message="No tax data found"):
        """Show empty state."""
        self.state_helper.show_empty(title=message)
        self.tabs.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_error(self, message="Error loading tax data"):
        """Show error state."""
        self.state_helper.show_error(message, on_retry=self.load_data)
        self.tabs.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self.state_helper.hide()
        self.tabs.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def load_data(self):
        """Load all tax data."""
        self._load_config()
        self._load_returns()
        self._load_withholding()

    def _load_config(self):
        self._show_loading()
        try:
            if not hasattr(self, "_async_tax_rates_response"):
                self.run_api_request(
                    "tax:rates", "GET", "/api/tax/rates/",
                    on_success=lambda r: self._resume_api_request("_async_tax_rates_response", self._load_config, r),
                    on_error=lambda m: self._resume_api_request("_async_tax_rates_response", self._load_config, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_tax_rates_response")
            if response and response.get('success'):
                data = response.get('data', {})
                rates = data.get('results', data) if isinstance(data, dict) else data
                
                if not rates:
                    self._show_empty()
                    return
                
                self._show_data()
                config_data = []
                for rate in rates:
                    status = "Active" if rate.get('is_active') else "Inactive"
                    config_data.append({
                        "name": rate.get('name', ''),
                        "rate": f"{rate.get('rate_percentage', '0.00')}%",
                        "type": rate.get('tax_type', ''),
                        "code": rate.get('code', ''),
                        "effective_from": rate.get('effective_from', ''),
                        "status": status,
                    })
                self.config_table.set_data(config_data)
            else:
                self._show_empty()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading tax config: {e}")
            self._show_error(f"Error: {e}")
    
    def _setup_returns_tab(self):
        layout = QVBoxLayout(self.returns_tab)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "DRAFT", "SUBMITTED", "PAID", "OVERDUE"])
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        
        self.generate_btn = EnterpriseButton(text="Generate Return", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        filter_layout.addWidget(self.generate_btn)
        layout.addLayout(filter_layout)
        
        columns = [
            TableColumn("period", "Period", width=160),
            TableColumn("taxable_sales", "Taxable Sales", width=100, align="right"),
            TableColumn("output_tax", "Output Tax", width=100, align="right"),
            TableColumn("input_tax", "Input Tax", width=100, align="right"),
            TableColumn("net_tax", "Net Tax", width=100, align="right"),
            TableColumn("due_date", "Due Date", width=90, align="center"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.returns_table = self._create_table(columns)
        layout.addWidget(self.returns_table)
        
        self._load_returns()
    
    def _setup_withholding_tab(self):
        layout = QVBoxLayout(self.withholding_tab)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Withholding Certificates"))
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("cert_no", "Certificate No", width=120),
            TableColumn("vendor", "Vendor", width=150),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("date", "Date", width=90, align="center"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.withholding_table = self._create_table(columns)
        layout.addWidget(self.withholding_table)
        
        self._load_withholding()
    
    def _load_returns(self):
        params = {}
        status_f = self.status_filter.currentText()
        if status_f != "All Status":
            params['status'] = status_f
            
        try:
            if not hasattr(self, "_async_tax_returns_response"):
                self.run_api_request(
                    "tax:returns", "GET", "/api/tax/returns/", params=params,
                    on_success=lambda r: self._resume_api_request("_async_tax_returns_response", self._load_returns, r),
                    on_error=lambda m: self._resume_api_request("_async_tax_returns_response", self._load_returns, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_tax_returns_response")
            if response and response.get('success'):
                data = response.get('data', {})
                returns = data.get('results', data) if isinstance(data, dict) else data
                
                ret_data = []
                for ret in returns:
                    period = f"{ret.get('period_start')} to {ret.get('period_end')}"
                    status = ret.get('status', '')
                    ret_data.append({
                        "period": period,
                        "taxable_sales": f"{ret.get('taxable_sales', '0.00')} AFN",
                        "output_tax": f"{ret.get('output_tax', '0.00')} AFN",
                        "input_tax": f"{ret.get('input_tax', '0.00')} AFN",
                        "net_tax": f"{ret.get('net_tax', '0.00')} AFN",
                        "due_date": ret.get('period_end', ''),
                        "status": status,
                    })
                self.returns_table.set_data(ret_data)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading tax returns: {e}")

    def _load_withholding(self):
        try:
            if not hasattr(self, "_async_tax_transactions_response"):
                self.run_api_request(
                    "tax:transactions", "GET", "/api/tax/transactions/",
                    on_success=lambda r: self._resume_api_request("_async_tax_transactions_response", self._load_withholding, r),
                    on_error=lambda m: self._resume_api_request("_async_tax_transactions_response", self._load_withholding, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_tax_transactions_response")
            if response and response.get('success'):
                data = response.get('data', {})
                withholding = data.get('results', data) if isinstance(data, dict) else data
                wh_data = []
                for item in withholding:
                    wh_data.append({
                        "cert_no": item.get('certificate_no', ''),
                        "vendor": item.get('vendor_name', ''),
                        "amount": item.get('amount', ''),
                        "date": item.get('transaction_date', ''),
                        "status": item.get('status', ''),
                    })
                self.withholding_table.set_data(wh_data)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading tax transactions: {e}")
    
    def _on_screen_shown(self):
        """Called when screen is shown (overrides BaseScreen)."""
        super()._on_screen_shown()
        self.load_data()
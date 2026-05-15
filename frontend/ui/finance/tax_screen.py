"""Tax management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QGroupBox,
                                  QFormLayout, QDialog, QDialogButtonBox, QTabWidget,
                                  QDoubleSpinBox, QCheckBox, QFrame, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_TABLE, TEXT_TABLE_HEADER, TEXT_HELPER,
                           BUTTON_HEIGHT_MD, TABLE_ROW_HEIGHT_MD,
                           BORDER_RADIUS_MD, BORDER_RADIUS_LG,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                           COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                           COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


from api.client import APIClient


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

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Tax Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Loading and Empty states
        self.loading_label = QLabel("Loading tax data...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No tax data found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading tax data")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
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
        self.loading_label.setVisible(show)
        self.tabs.setVisible(not show)
        self.empty_label.setVisible(False)
        self.error_label.setVisible(False)
        self.btn_refresh.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_empty(self, message="No tax data found"):
        """Show empty state."""
        self.loading_label.setVisible(False)
        self.tabs.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.error_label.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.error_label.setVisible(False)
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
            response = self.api_client.get('/api/tax/rates/')
            if response and response.get('success'):
                data = response['data']
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
            print(f"Error loading tax config: {e}")
            self._show_empty(f"Error: {e}")
            self.error_label.setVisible(True)
    
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
            response = self.api_client.get('/api/tax/returns/', params=params)
            if response and response.get('success'):
                data = response['data']
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
            print(f"Error loading tax returns: {e}")

    def _load_withholding(self):
        try:
            response = self.api_client.get('/api/tax/transactions/')
            if response and response.get('success'):
                data = response['data']
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
            print(f"Error loading tax transactions: {e}")
    
    def _on_screen_shown(self):
        """Called when screen is shown (overrides BaseScreen)."""
        super()._on_screen_shown()
        self.load_data()
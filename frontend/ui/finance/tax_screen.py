from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Tax management screen."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QGroupBox,
                                  QFormLayout, QDialog, QDialogButtonBox, QTabWidget,
                                  QDoubleSpinBox, QCheckBox, QFrame, QAbstractItemView,
                                  QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, FONT_SIZE_XL, BUTTON_HEIGHT_MD, TABLE_ROW_HEIGHT_MD)


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
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setMinimumHeight(35)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_BG_ELEVATED}};
                border: 1px solid {{COLOR_BORDER_LIGHT}};
                border-radius: 5px;
                padding: {SPACING_XS} {SPACING_MD};
                color: {{COLOR_TEXT_SECONDARY}};
            }}
            QPushButton:hover {{
                background-color: {{COLOR_BG_ELEVATED}};
            }}
        """)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Loading and Empty states
        self.loading_label = QLabel("Loading tax data...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No tax data found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading tax data")
        self.error_label.setFont(QFont("Segoe UI", 12))
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #e74c3c; padding: 40px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: 5px; background: white; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; padding: 10px 20px; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
            QTabBar::tab:selected {{ background: white; border-bottom-color: white; font-weight: bold; }}
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
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        self.add_rate_btn = QPushButton("+ Add Tax Rate")
        self.add_rate_btn.setMinimumHeight(38)
        self.add_rate_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; border-radius: 5px; font-weight: bold; padding: 0 15px;")
        action_layout.addWidget(self.add_rate_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.config_table = self._create_modern_table()
        self.config_table.setColumnCount(6)
        self.config_table.setHorizontalHeaderLabels(["Tax Name", "Rate %", "Type", "Code", "Effective From", "Status"])
        layout.addWidget(self.config_table)
        
        self._load_config()

    def _create_modern_table(self):
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{ border: none; gridline-color: {{COLOR_BG_ELEVATED}}; }}
            QHeaderView::section {{ background-color: {{COLOR_BG_ELEVATED}}; padding: {SPACING_SM}; border: none; border-bottom: 2px solid {{COLOR_BORDER_LIGHT}}; font-weight: bold; }}
            QTableWidget::item {{ padding: {SPACING_SM}; }}
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
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
        self.config_table.setRowCount(0)
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
                self.config_table.setRowCount(len(rates))
                for i, rate in enumerate(rates):
                    self.config_table.setItem(i, 0, QTableWidgetItem(rate.get('name', '')))
                    self.config_table.setItem(i, 1, QTableWidgetItem(f"{rate.get('rate_percentage', '0.00')}%"))
                    self.config_table.setItem(i, 2, QTableWidgetItem(rate.get('tax_type', '')))
                    self.config_table.setItem(i, 3, QTableWidgetItem(rate.get('code', '')))
                    self.config_table.setItem(i, 4, QTableWidgetItem(rate.get('effective_from', '')))
                    
                    status = "Active" if rate.get('is_active') else "Inactive"
                    status_item = QTableWidgetItem(status)
                    if not rate.get('is_active'): status_item.setForeground(QColor("COLOR_DANGER"))
                    self.config_table.setItem(i, 5, status_item)
                    
                    self.config_table.setRowHeight(i, TABLE_ROW_HEIGHT_MD)
            else:
                self._show_empty()
        except Exception as e:
            print(f"Error loading tax config: {e}")
            self._show_empty(f"Error: {e}")
            self.error_label.setVisible(True)
    
    def _setup_returns_tab(self):
        layout = QVBoxLayout(self.returns_tab)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "DRAFT", "SUBMITTED", "PAID", "OVERDUE"])
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        
        self.generate_btn = QPushButton("Generate Return")
        self.generate_btn.setMinimumHeight(38)
        self.generate_btn.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; font-weight: bold; padding: 0 15px;")
        filter_layout.addWidget(self.generate_btn)
        layout.addLayout(filter_layout)
        
        self.returns_table = self._create_modern_table()
        self.returns_table.setColumnCount(7)
        self.returns_table.setHorizontalHeaderLabels(["Period", "Taxable Sales", "Output Tax", "Input Tax", "Net Tax", "Due Date", "Status"])
        layout.addWidget(self.returns_table)
        
        self._load_returns()
    
    def _setup_withholding_tab(self):
        layout = QVBoxLayout(self.withholding_tab)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Withholding Certificates"))
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.withholding_table = self._create_modern_table()
        self.withholding_table.setColumnCount(5)
        self.withholding_table.setHorizontalHeaderLabels(["Certificate No", "Vendor", "Amount", "Date", "Status"])
        layout.addWidget(self.withholding_table)
        
        self._load_withholding()
    
    def _load_returns(self):
        self.returns_table.setRowCount(0)
        params = {}
        status_f = self.status_filter.currentText()
        if status_f != "All Status":
            params['status'] = status_f
            
        try:
            response = self.api_client.get('/api/tax/returns/', params=params)
            if response and response.get('success'):
                data = response['data']
                returns = data.get('results', data) if isinstance(data, dict) else data
                
                self.returns_table.setRowCount(len(returns))
                for i, ret in enumerate(returns):
                    period = f"{ret.get('period_start')} to {ret.get('period_end')}"
                    self.returns_table.setItem(i, 0, QTableWidgetItem(period))
                    self.returns_table.setItem(i, 1, QTableWidgetItem(f"{ret.get('taxable_sales', '0.00')} AFN"))
                    self.returns_table.setItem(i, 2, QTableWidgetItem(f"{ret.get('output_tax', '0.00')} AFN"))
                    self.returns_table.setItem(i, 3, QTableWidgetItem(f"{ret.get('input_tax', '0.00')} AFN"))
                    self.returns_table.setItem(i, 4, QTableWidgetItem(f"{ret.get('net_tax', '0.00')} AFN"))
                    self.returns_table.setItem(i, 5, QTableWidgetItem(ret.get('period_end', ''))) # Simplified due date
                    
                    status = ret.get('status', '')
                    status_item = QTableWidgetItem(status)
                    if status == 'PAID': status_item.setForeground(QColor("COLOR_STATUS_VALID"))
                    elif status == 'DRAFT': status_item.setForeground(QColor("COLOR_WARNING"))
                    self.returns_table.setItem(i, 6, status_item)
                    
                    self.returns_table.setRowHeight(i, TABLE_ROW_HEIGHT_MD)
        except Exception as e:
            print(f"Error loading tax returns: {e}")

    def _load_withholding(self):
        self.withholding_table.setRowCount(0)
        try:
            response = self.api_client.get('/api/tax/transactions/')
            if response and response.get('success'):
                data = response['data']
                withholding = data.get('results', data) if isinstance(data, dict) else data
                self.withholding_table.setRowCount(len(withholding))
        except Exception as e:
            print(f"Error loading tax transactions: {e}")
    
    def _on_screen_shown(self):
        """Called when screen is shown (overrides BaseScreen)."""
        super()._on_screen_shown()
        self.load_data()
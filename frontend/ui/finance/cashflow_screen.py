from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Cashflow management screen."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QGroupBox,
                                  QFormLayout, QDialog, QDialogButtonBox, QTabWidget,
                                  QDateEdit, QProgressBar, QApplication, QFrame, QAbstractItemView)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_MD, FONT_SIZE_XL, FONT_SIZE_LG, BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD)


class CashflowScreen(BaseScreen):
    """Screen for managing cash flow."""

    def __init__(self, parent=None, screen_id="cashflow", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self.api_client = api_client or APIClient()
        self._cashflow_data = []
        self._forecast_data = []
        self._position_data = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Cash Flow Management")
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

        # Summary Cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(SPACING_MD + SPACING_XS)

        self.inflow_card = self._create_summary_card("Cash Inflow", "0.00 AFN", "{COLOR_SUCCESS}")
        self.outflow_card = self._create_summary_card("Cash Outflow", "0.00 AFN", "{COLOR_DANGER}")
        self.net_card = self._create_summary_card("Net Cash Flow", "0.00 AFN", "{COLOR_PRIMARY}")

        summary_layout.addWidget(self.inflow_card)
        summary_layout.addWidget(self.outflow_card)
        summary_layout.addWidget(self.net_card)
        layout.addLayout(summary_layout)

        # Loading and Empty labels
        self.loading_label = QLabel("Loading cash flow data...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No cash flow data available")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: 5px; background: white; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; padding: 10px 20px; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
            QTabBar::tab:selected {{ background: white; border-bottom-color: white; font-weight: bold; }}
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
                background-color: white;
                border-left: 5px solid {color};
                border-radius: 8px;
                border-top: 1px solid #dee2e6;
                border-right: 1px solid #dee2e6;
                border-bottom: 1px solid #dee2e6;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-weight: bold; font-size: 10pt;")
        
        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card

    def _update_summary_card(self, card, value):
        label = card.findChild(QLabel, "value_label")
        if label:
            label.setText(value)

    def _create_modern_table(self):
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{ border: none; gridline-color: #f1f2f6; }}
            QHeaderView::section {{ background-color: {COLOR_TABLE_HEADER_BG_LIGHT}; padding: 8px; border: none; border-bottom: 2px solid {COLOR_TABLE_BORDER_LIGHT}; font-weight: bold; }}
            QTableWidget::item {{ padding: 10px; }}
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
        self.btn_refresh.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_empty(self, message="No cash flow data available"):
        """Show empty state."""
        self.loading_label.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.tabs.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data tabs."""
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
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
                endpoint = "/api/analytics/cash-flow/"

            response = self.api_client.get(endpoint)
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
            print(f"Error loading cashflow: {e}")
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
        
        self.statement_table = self._create_modern_table()
        self.statement_table.setColumnCount(4)
        self.statement_table.setHorizontalHeaderLabels(["Category", "This Period", "Previous Period", "Change"])
        layout.addWidget(self.statement_table)
    
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
        
        self.forecast_table = self._create_modern_table()
        self.forecast_table.setColumnCount(5)
        self.forecast_table.setHorizontalHeaderLabels(["Date", "Expected Inflows", "Expected Outflows", "Net", "Running Balance"])
        layout.addWidget(self.forecast_table)
    
    def _setup_position_tab(self):
        layout = QVBoxLayout(self.position_tab)
        layout.setSpacing(SPACING_MD)
        
        self.position_table = self._create_modern_table()
        self.position_table.setColumnCount(7)
        self.position_table.setHorizontalHeaderLabels(["Date", "Description", "Reference", "Type", "Amount", "Balance", "Status"])
        layout.addWidget(self.position_table)

    def _load_statement(self):
        self.statement_table.setRowCount(0)
        if not self._cashflow_data:
            mock_data = [
                {"category": "Operating Activities", "this": "1,800,000", "prev": "1,500,000", "change": "+20%"},
                {"category": "Investing Activities", "this": "-150,000", "prev": "-200,000", "change": "-25%"},
                {"category": "Financing Activities", "this": "-50,000", "prev": "-50,000", "change": "0%"},
            ]
        else:
            mock_data = [] # Use real data mapping here
            
        for item in mock_data:
            row = self.statement_table.rowCount()
            self.statement_table.insertRow(row)
            self.statement_table.setItem(row, 0, QTableWidgetItem(item["category"]))
            self.statement_table.setItem(row, 1, QTableWidgetItem(item["this"]))
            self.statement_table.setItem(row, 2, QTableWidgetItem(item["prev"]))
            self.statement_table.setItem(row, 3, QTableWidgetItem(item["change"]))

    def _load_forecast(self):
        self.forecast_table.setRowCount(0)
        mock_data = [
            {"date": "2026-05-06", "inflow": "50000", "outflow": "30000", "net": "20000", "balance": "620000"},
            {"date": "2026-05-07", "inflow": "80000", "outflow": "45000", "net": "35000", "balance": "655000"},
        ]
        for item in mock_data:
            row = self.forecast_table.rowCount()
            self.forecast_table.insertRow(row)
            self.forecast_table.setItem(row, 0, QTableWidgetItem(item["date"]))
            self.forecast_table.setItem(row, 1, QTableWidgetItem(item["inflow"]))
            self.forecast_table.setItem(row, 2, QTableWidgetItem(item["outflow"]))
            self.forecast_table.setItem(row, 3, QTableWidgetItem(item["net"]))
            self.forecast_table.setItem(row, 4, QTableWidgetItem(item["balance"]))

    def _load_position(self):
        self.position_table.setRowCount(0)
        mock_data = [
            {"date": "2026-05-05", "desc": "Sales Invoice Payment", "ref": "INV-001", "type": "Inflow", "amount": "50000", "balance": "600000", "status": "Cleared"},
        ]
        for item in mock_data:
            row = self.position_table.rowCount()
            self.position_table.insertRow(row)
            self.position_table.setItem(row, 0, QTableWidgetItem(item["date"]))
            self.position_table.setItem(row, 1, QTableWidgetItem(item["desc"]))
            self.position_table.setItem(row, 2, QTableWidgetItem(item["ref"]))
            self.position_table.setItem(row, 3, QTableWidgetItem(item["type"]))
            self.position_table.setItem(row, 4, QTableWidgetItem(item["amount"]))
            self.position_table.setItem(row, 5, QTableWidgetItem(item["balance"]))
            self.position_table.setItem(row, 6, QTableWidgetItem(item["status"]))

    def _on_screen_shown(self):
        """Called when screen is shown."""
        super()._on_screen_shown()
        self.load_data()

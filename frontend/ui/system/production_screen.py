from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, 
                                  QHeaderView, QMessageBox, QGroupBox, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, SPACING_LG, FONT_SIZE_LG, FONT_SIZE_XL,
                          BUTTON_HEIGHT_MD)
from api.client import APIClient
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)

class ProductionScreen(BaseScreen):
    """Screen for managing pharmaceutical production and manufacturing."""
    
    def __init__(self, parent=None, screen_id="production", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client or APIClient()
        self.production_orders = []
        self._setup_ui()
        self.load_orders()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Production & Manufacturing")
        title_label.setFont(QFont("Segoe UI", FONT_SIZE_XL, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.new_order_btn = QPushButton("+ New Production Order")
        self.new_order_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.new_order_btn.setStyleSheet("background-color: #9b59b6; color: white; font-weight: bold;")
        self.new_order_btn.clicked.connect(self.show_new_order_dialog)
        header_layout.addWidget(self.new_order_btn)
        
        layout.addLayout(header_layout)

        # Status Summary
        summary_group = QGroupBox("Production Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.addWidget(QLabel("Active Orders: 0"))
        summary_layout.addWidget(QLabel("Completed Today: 0"))
        summary_layout.addWidget(QLabel("Optimization Status: Optimal"))
        layout.addWidget(summary_group)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Order #", "Product", "Quantity", "Start Date", "End Date", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_orders(self):
        # Placeholder for loading orders from API
        pass

    def show_new_order_dialog(self):
        QMessageBox.information(self, "Production", "Manufacturing module is currently in read-only mode.")

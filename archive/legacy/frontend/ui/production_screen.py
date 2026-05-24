from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, 
                                  QHeaderView, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_TABLE, TEXT_TABLE_HEADER, TEXT_HELPER,
                           BUTTON_HEIGHT_MD, BORDER_RADIUS_MD,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from api.client import APIClient

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
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Production & Manufacturing")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.new_order_btn = EnterpriseButton(text="+ New Production Order", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.new_order_btn.clicked.connect(self.show_new_order_dialog)
        header_layout.addWidget(self.new_order_btn)
        
        layout.addLayout(header_layout)

        # Status Summary
        summary_group = QGroupBox("Production Summary")
        summary_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {TEXT_CARD_TITLE}pt;
                font-weight: 700;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
        """)
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.addWidget(QLabel("Active Orders: 0"))
        summary_layout.addWidget(QLabel("Completed Today: 0"))
        summary_layout.addWidget(QLabel("Optimization Status: Optimal"))
        layout.addWidget(summary_group)

        # Table
        columns = [
            TableColumn("order_no", "Order #", width=100),
            TableColumn("product", "Product", width=200),
            TableColumn("quantity", "Quantity", width=80, align="right"),
            TableColumn("start_date", "Start Date", width=100, align="center"),
            TableColumn("end_date", "End Date", width=100, align="center"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.table = EnterpriseTable(columns)
        layout.addWidget(self.table)

    def load_orders(self):
        # Placeholder for loading orders from API
        pass

    def show_new_order_dialog(self):
        QMessageBox.information(self, "Production", "Manufacturing module is currently in read-only mode.")

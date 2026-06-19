"""Phase 20: Returns Explainability UI - explains why returns were processed."""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
    TEXT_LABEL, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_BG_SURFACE, COLOR_BORDER, BORDER_RADIUS_MD, BORDER_RADIUS_LG,
)
from utils.format import safe_float
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.kpi_cards import MiniMetricCard, SectionHeader
from ui.components.state_helper import StateHelper
from ui.screens.base_screen import BaseScreen


class ReturnsExplainabilityScreen(BaseScreen):
    """Returns explainability screen - shows why returns were processed with context."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="returns_explainability")
        self.api_client = api_client or APIClient()
        self.returns = []
        self._is_loading = False
        self.setup_ui()
        self.load_returns()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load in __init__."""

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        # Enterprise header
        header = PageHeader(
            "Returns Explainability",
            "Review return value, reversal context and reason trails with audit-ready explanations.",
            "RETURN CONTROL",
        )

        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_returns)
        header.add_action(self.btn_refresh)

        layout.addWidget(header)

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
        self.kpi_total_returns = MiniMetricCard("Total Returns", "0", COLOR_WARNING)
        self.kpi_total_value = MiniMetricCard("Total Value", "0.00", COLOR_DANGER)
        self.kpi_explained = MiniMetricCard("Explained", "0", COLOR_SUCCESS)
        kpi_layout.addWidget(self.kpi_total_returns, 0, 0)
        kpi_layout.addWidget(self.kpi_total_value, 0, 1)
        kpi_layout.addWidget(self.kpi_explained, 0, 2)
        content_layout.addLayout(kpi_layout)

        # Returns table
        section = SectionHeader("Return Orders with Explanation")
        content_layout.addWidget(section)

        columns = [
            TableColumn("return_number", "Return #", width=120),
            TableColumn("date", "Date", width=100, align="center"),
            TableColumn("customer", "Customer", width=150),
            TableColumn("reason", "Reason", width=150),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("status", "Status", width=80, align="center"),
            TableColumn("journal_reversed", "Journal Reversed", width=120, align="center"),
        ]
        self.returns_table = EnterpriseTable(columns)
        self.returns_table.set_density("compact")
        self.returns_table.row_double_clicked.connect(self._show_return_details)
        content_layout.addWidget(self.returns_table)

        # Explanation panel
        self.explanation_group = QGroupBox("Return Explanation")
        self.explanation_group.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.explanation_group.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; "
            f"margin-top: {SPACING_SM}px; padding-top: {SPACING_SM}px; color: {COLOR_TEXT_PRIMARY}; }}"
        )
        explanation_layout = QVBoxLayout(self.explanation_group)

        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_BG_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: {SPACING_MD}px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_BODY}pt;
            }}
        """)
        self.explanation_text.setPlainText("Select a return to view explanation.")
        explanation_layout.addWidget(self.explanation_text)

        content_layout.addWidget(self.explanation_group)

        layout.addWidget(self.content_widget)
        self.content_widget.setVisible(False)

    def _show_loading(self, show=True):
        self._is_loading = show
        if show:
            self.state_helper.show_loading("Loading returns...")
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
        self.state_helper.show_error(message, on_retry=self.load_returns)
        self.content_widget.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def load_returns(self):
        """Load returns data."""
        self._show_loading()
        try:
            endpoint = get_endpoint("returns") or "/api/returns/orders/"
            if not hasattr(self, "_async_returns_explainability_response"):
                self.run_api_request(
                    "returns_explainability:list", "GET", endpoint,
                    params={"page_size": 100},
                    on_success=lambda r: self._resume_api_request("_async_returns_explainability_response", self.load_returns, r),
                    on_error=lambda m: self._resume_api_request("_async_returns_explainability_response", self.load_returns, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_returns_explainability_response")
            self.returns = extract_list(response)
            self._update_display()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading returns: {e}")
            self._show_error(f"Error: {e}")
        self._show_data()

    def _update_display(self):
        """Update display with returns data."""
        total_value = sum(safe_float(r.get("total_amount", 0)) for r in self.returns)
        self.kpi_total_returns.update_value(str(len(self.returns)))
        self.kpi_total_value.update_value(f"{total_value:,.2f}")
        self.kpi_explained.update_value(str(len([r for r in self.returns if r.get("reason")])))

        table_data = []
        for r in self.returns:
            table_data.append({
                "return_number": r.get("return_number", ""),
                "date": str(r.get("return_date", ""))[:10],
                "customer": r.get("customer_name", ""),
                "reason": r.get("reason", "")[:30] + "..." if len(r.get("reason", "")) > 30 else r.get("reason", ""),
                "amount": f"{safe_float(r.get('total_amount', 0)):,.2f}",
                "status": r.get("status", ""),
                "journal_reversed": "Yes" if r.get("journal_entry_reversed") else "No",
            })
        self.returns_table.set_data(table_data)

    def _show_return_details(self, row):
        """Show detailed explanation for selected return."""
        if row < len(self.returns):
            ret = self.returns[row]
            explanation = (
                f"Return: {ret.get('return_number', '')}\n"
                f"Date: {ret.get('return_date', '')}\n"
                f"Customer: {ret.get('customer_name', '')}\n"
                f"Reason: {ret.get('reason', 'N/A')}\n"
                f"Amount: {safe_float(ret.get('total_amount', 0)):,.2f}\n"
                f"Status: {ret.get('status', '')}\n"
                f"Journal Reversed: {'Yes' if ret.get('journal_entry_reversed') else 'No'}\n"
                f"\nNotes: {ret.get('notes', 'No additional notes.')}"
            )
            self.explanation_text.setPlainText(explanation)

"""Phase 20: Journal Reversal Explorer - tracks journal entry reversals."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel,
)
from PySide6.QtCore import Qt

from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (
    SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY,
    COLOR_SUCCESS, COLOR_DANGER,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.kpi_cards import MiniMetricCard, SectionHeader
from ui.components.state_helper import StateHelper
from utils.format import safe_float
from ui.screens.base_screen import BaseScreen


class JournalReversalExplorer(BaseScreen):
    """Journal reversal explorer - tracks and explains journal entry reversals."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="journal_reversals")
        self.api_client = api_client or APIClient()
        self.journal_entries = []
        self._is_loading = False
        self.setup_ui()
        self.load_reversals()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load in __init__."""

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Journal Reversal Explorer")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_reversals)
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
        self.kpi_total_entries = MiniMetricCard("Total Entries", "0", COLOR_PRIMARY)
        self.kpi_reversed = MiniMetricCard("Reversed", "0", COLOR_DANGER)
        self.kpi_pending = MiniMetricCard("Pending Reversal", "0", COLOR_SUCCESS)
        kpi_layout.addWidget(self.kpi_total_entries, 0, 0)
        kpi_layout.addWidget(self.kpi_reversed, 0, 1)
        kpi_layout.addWidget(self.kpi_pending, 0, 2)
        content_layout.addLayout(kpi_layout)

        # Journal entries table
        section = SectionHeader("Journal Entries with Reversal Status")
        content_layout.addWidget(section)

        columns = [
            TableColumn("entry_number", "Entry #", width=100),
            TableColumn("date", "Date", width=100, align="center"),
            TableColumn("description", "Description", width=200),
            TableColumn("total_debit", "Total Debit", width=100, align="right"),
            TableColumn("total_credit", "Total Credit", width=100, align="right"),
            TableColumn("status", "Status", width=100, align="center"),
            TableColumn("reversed", "Reversed", width=80, align="center"),
            TableColumn("reversal_reason", "Reversal Reason", width=200),
        ]
        self.journal_table = EnterpriseTable(columns)
        self.journal_table.set_density("compact")
        content_layout.addWidget(self.journal_table)

        layout.addWidget(self.content_widget)
        self.content_widget.setVisible(False)

    def _show_loading(self, show=True):
        self._is_loading = show
        if show:
            self.state_helper.show_loading("Loading journal entries...")
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
        self.state_helper.show_error(message, on_retry=self.load_reversals)
        self.content_widget.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def load_reversals(self):
        """Load journal entries with reversal status."""
        self._show_loading()
        try:
            endpoint = get_endpoint("journal_entries") or "/api/accounting/journal-entries/"
            response = self.api_client.get(endpoint, params={"page_size": 200})
            self.journal_entries = extract_list(response)
            self._update_display()
        except Exception as e:
            print(f"Error loading journal entries: {e}")
            self._show_error(f"Error: {e}")
        self._show_data()

    def _update_display(self):
        """Update display with journal data."""
        reversed_count = len([j for j in self.journal_entries if j.get("is_reversed")])
        self.kpi_total_entries.update_value(str(len(self.journal_entries)))
        self.kpi_reversed.update_value(str(reversed_count))
        self.kpi_pending.update_value(str(len(self.journal_entries) - reversed_count))

        table_data = []
        for j in self.journal_entries:
            table_data.append({
                "entry_number": j.get("entry_number", ""),
                "date": str(j.get("entry_date", ""))[:10],
                "description": (j.get("description", "") or "")[:50],
                "total_debit": f"{safe_float(j.get('total_debit', 0)):,.2f}",
                "total_credit": f"{safe_float(j.get('total_credit', 0)):,.2f}",
                "status": j.get("status", ""),
                "reversed": "Yes" if j.get("is_reversed") else "No",
                "reversal_reason": (j.get("reversal_reason", "") or "")[:50],
            })
        self.journal_table.set_data(table_data)

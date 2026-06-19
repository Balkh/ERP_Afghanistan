"""
Phase 5B.6 — Event Store Viewer Screen.
Browse events, verify claims, and view Event Store state.
"""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                                 QLineEdit, QComboBox)
from PySide6.QtGui import QFont
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.page_header import PageHeader
from ui.screens.base_screen import BaseScreen

from api.client import APIClient
from api.truth_client import TruthAPIClient
from ui.components.tables import EnterpriseTable, TableColumn
from ui.constants import (COLOR_BG_SURFACE, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
                           COLOR_PRIMARY, COLOR_WARNING, COLOR_BORDER,
                           TEXT_LABEL, TEXT_PAGE_TITLE, SPACING_LG,
    SPACING_SM, MARGIN_PAGE,
                           SPACING_6, BORDER_RADIUS_MD)


class EventStoreScreen(BaseScreen):
    """Screen for browsing the Event Store and verifying claims."""

    def __init__(self, api_client: APIClient = None):
        self._api = TruthAPIClient(api_client or APIClient())
        super().__init__()
        self._setup_screen()

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = PageHeader(
            "Event Store Browser",
            "Browse event history, filter aggregates and verify operational claims.",
            "TRUTH CONTROL",
        )
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["", "inventory", "accounting", "hr", "sales_purchase", "fixed_assets"])
        self.domain_combo.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE}; padding: {SPACING_6}px;")
        toolbar.addWidget(QLabel("Domain:"))
        toolbar.addWidget(self.domain_combo)

        self.agg_input = QLineEdit()
        self.agg_input.setPlaceholderText("Aggregate ID...")
        self.agg_input.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE}; padding: {SPACING_6}px; border: 1px solid {COLOR_BORDER};")
        toolbar.addWidget(QLabel("Aggregate:"))
        toolbar.addWidget(self.agg_input)

        refresh_btn = EnterpriseButton("⟳ Refresh", variant=ButtonVariant.PRIMARY)
        refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(refresh_btn)

        verify_btn = EnterpriseButton("✓ Verify Claim", variant=ButtonVariant.WARNING)
        verify_btn.clicked.connect(self._verify)
        toolbar.addWidget(verify_btn)

        layout.addLayout(toolbar)

        # Summary bar
        self.summary_label = QLabel("Loading...")
        self.summary_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_LABEL}pt;")
        layout.addWidget(self.summary_label)

        # Event table
        columns = [
            TableColumn("event_id_short", "Event ID", width=110),
            TableColumn("event_type", "Type", width=160),
            TableColumn("domain", "Domain", width=120),
            TableColumn("aggregate_id", "Aggregate", width=180),
            TableColumn("timestamp_short", "Timestamp", width=160),
        ]
        self.table = EnterpriseTable(columns, density="compact")
        layout.addWidget(self.table)

    def _on_screen_shown(self):
        pass

    def load_data(self, params=None):
        self._refresh()

    def _refresh(self):
        try:
            domain = self.domain_combo.currentText() or None
            aggregate = self.agg_input.text().strip() or None
            events = self._api.list_events(domain=domain, aggregate_id=aggregate, limit=200)
            rows = []
            for evt in events:
                rows.append({
                    **evt,
                    "event_id_short": evt.get("event_id", "")[:12],
                    "event_type": evt.get("event_type", ""),
                    "domain": evt.get("domain", ""),
                    "aggregate_id": evt.get("aggregate_id", ""),
                    "timestamp_short": evt.get("timestamp", "")[:19],
                })
            self.table.set_data(rows)
            self.summary_label.setText(f"Total events: {len(events)}")
        except Exception as e:
            self.summary_label.setText(f"Error: {e}")

    def _verify(self):
        aggregate = self.agg_input.text().strip()
        domain = self.domain_combo.currentText() or "inventory"
        if not aggregate:
            return
        try:
            result = self._api.verify_claim("stock_movement", aggregate, domain)
            verified = result.get("data", {}).get("verified", False) if isinstance(result, dict) else False
            self.summary_label.setText(
                f"✓ Verified: {verified} | Aggregate: {aggregate}"
            )
        except Exception as e:
            self.summary_label.setText(f"Verification error: {e}")

    def set_api_client(self, client: APIClient):
        self._api = TruthAPIClient(client)

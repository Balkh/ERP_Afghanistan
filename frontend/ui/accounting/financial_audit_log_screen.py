"""Financial Audit Log Screen.

Displays the structured audit trail for all financial events: balance syncs,
credit overrides, integrity fixes, FIFO allocations, and return voids.
Uses the existing AuditTrail model filtered by financial action types.
"""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                                QWidget, QFrame, QScrollArea, QGroupBox, QComboBox,
                                QDateEdit)
from PySide6.QtCore import QDate
from PySide6.QtGui import QFont
from api.client import APIClient

from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, MARGIN_PAGE, TEXT_SECTION_TITLE,
                           TEXT_BODY_SMALL, COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, BORDER_RADIUS_MD)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.screens.base_screen import BaseScreen


FINANCIAL_ACTIONS = [
    ("All Actions", ""),
    ("Balance Sync", "BALANCE_SYNC"),
    ("Credit Override", "CREDIT_OVERRIDE"),
    ("Credit Block", "CREDIT_BLOCK"),
    ("Integrity Fix", "INTEGRITY_FIX"),
    ("FIFO Allocate", "FIFO_ALLOCATE"),
    ("Payment Adjust", "PAYMENT_ADJUST"),
    ("Return Void", "RETURN_VOID"),
    ("Refund Process", "REFUND_PROCESS"),
    ("Reconciliation Mismatch", "RECONCILIATION_MISMATCH"),
    ("Credit Policy Block", "CREDIT_POLICY_BLOCK"),
    ("Allocation Auto", "ALLOCATION_AUTO"),
    ("Balance Derived", "BALANCE_DERIVED"),
    ("Journal Create", "JOURNAL_CREATE"),
    ("Journal Post", "JOURNAL_POST"),
    ("Journal Reverse", "JOURNAL_REVERSE"),
]


class FinancialAuditLogScreen(BaseScreen):
    """Screen displaying the financial audit trail."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="financial_audit")
        self.api_client = api_client or APIClient()
        self.setup_ui()
        self.load_logs()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load in __init__."""

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Financial Audit Log")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(title)

        # Filters
        header_layout.addSpacing(SPACING_LG)
        header_layout.addWidget(QLabel("Action:"))
        self.action_filter = QComboBox()
        for label, value in FINANCIAL_ACTIONS:
            self.action_filter.addItem(label, value)
        self.action_filter.currentIndexChanged.connect(self.load_logs)
        header_layout.addWidget(self.action_filter)

        header_layout.addSpacing(SPACING_SM)
        header_layout.addWidget(QLabel("From:"))
        self.date_filter = QDateEdit()
        self.date_filter.setDate(QDate.currentDate().addDays(-30))
        self.date_filter.setCalendarPopup(True)
        self.date_filter.dateChanged.connect(self.load_logs)
        header_layout.addWidget(self.date_filter)

        header_layout.addStretch()

        self.refresh_btn = EnterpriseButton(
            text="Refresh",
            variant=ButtonVariant.PRIMARY,
            size=ButtonSize.SMALL,
        )
        self.refresh_btn.clicked.connect(self.load_logs)
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # Summary bar
        self.summary_bar = QLabel("Loading audit logs...")
        self.summary_bar.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY_SMALL}pt;")
        layout.addWidget(self.summary_bar)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(SPACING_LG)

        # Audit log table
        log_group = QGroupBox("Audit Entries")
        log_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {TEXT_SECTION_TITLE}pt;
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                margin-top: {SPACING_MD};
                padding-top: {SPACING_MD};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: {SPACING_MD}; padding: 0 {SPACING_SM}; }}
        """)
        log_layout = QVBoxLayout(log_group)

        self.audit_table = EnterpriseTable(columns=[
            TableColumn("Timestamp", "timestamp", 160),
            TableColumn("Action", "action", 130),
            TableColumn("Entity", "entity", 100),
            TableColumn("Description", "description", 300),
            TableColumn("Before", "before", 100),
            TableColumn("After", "after", 100),
            TableColumn("User", "user", 100),
        ])
        log_layout.addWidget(self.audit_table)

        content_layout.addWidget(log_group)
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def load_logs(self):
        """Load financial audit logs from the backend."""
        try:
            params = {}
            action = self.action_filter.currentData()
            if action:
                params['action'] = action

            from_date = self.date_filter.date().toPython()
            params['from_date'] = from_date.isoformat()

            response = self.api_client.get("/api/audit/logs/", params=params)
            if response and response.get("success", True):
                data = response.get("data", response)
                results = data.get("results", []) if isinstance(data, dict) else data
                self._update_table(results)
                self.summary_bar.setText(
                    f"Showing {len(results)} financial audit entries "
                    f"(filtered from {data.get('count', len(results))} total)"
                )
            else:
                self.summary_bar.setText(f"Failed to load logs: {response}")
        except Exception as e:
            self.summary_bar.setText(f"Error loading logs: {e}")

    def _update_table(self, logs):
        """Update the audit table with log entries."""
        rows = []
        for log in logs:
            action = log.get("action", "")
            if action not in [a[1] for a in FINANCIAL_ACTIONS if a[1]]:
                continue

            changes = log.get("changes", {})
            old_vals = log.get("old_values", {})
            new_vals = log.get("new_values", {})

            entity_type = changes.get("entity_type", log.get("model_name", ""))
            entity_id = changes.get("entity_id", log.get("object_id", ""))
            entity = f"{entity_type}:{entity_id}" if entity_type and entity_id else log.get("object_repr", "")

            before = old_vals.get("balance", old_vals.get("amount", ""))
            after = new_vals.get("balance", new_vals.get("amount", ""))

            rows.append({
                "timestamp": log.get("created_at", "")[:19].replace("T", " "),
                "action": action.replace("_", " ").title(),
                "entity": entity[:30],
                "description": log.get("object_repr", "")[:80],
                "before": str(before) if before else "",
                "after": str(after) if after else "",
                "user": log.get("username", ""),
            })

        self.audit_table.set_data(rows)
        if not rows:
            self.audit_table.set_data([])

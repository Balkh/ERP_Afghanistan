"""
Phase 5B.7 — Financial Control Tower Screen.

Accounting Dashboard → Ledger → Journal → Trial Balance → P&L → Balance Sheet → Consistency.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QTextEdit, QSplitter, QTableWidget,
                                 QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from api.client import APIClient
from api.truth_client import TruthAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE, BORDER_RADIUS_MD)
from ui.constants import TEXT_SECTION_TITLE, TEXT_BODY


class FinancialControlTowerScreen(QWidget):
    """Financial control tower: Ledger → Journal → TB → P&L → BS → Consistency."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = api_client or APIClient()
        self._truth = TruthAPIClient(self._api)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("Financial Control Tower")
        header_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        for label, cb in [
            ("📊 Ledger", self._load_ledger),
            ("📝 Journal", self._load_journal),
            ("⚖ Trial Balance", self._load_tb),
            ("📈 P&L", self._load_tb),
            ("📋 Balance Sheet", self._load_tb),
            ("✅ Consistency", self._load_consistency),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 12px;
                font-size: {TEXT_BODY}px; }}
                QPushButton:hover {{ background: {COLOR_PRIMARY}; color: white; }}
            """)
            btn.clicked.connect(cb)
            toolbar.addWidget(btn)
        layout.addLayout(toolbar)

        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px;
            font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        layout.addWidget(self.content)

    def _load_ledger(self):
        try:
            r = self._truth.get_ledger()
            d = r.get("data", r) if isinstance(r, dict) else r
            accts = d.get("accounts", [])
            text = f"Ledger Balances ({len(accts)} accounts):\n"
            for a in accts[:20]:
                text += f"  {a.get('account_code','')} {a.get('account_name',''):30s} "
                text += f"Dr:{a.get('total_debits','0'):>10s} Cr:{a.get('total_credits','0'):>10s} "
                text += f"Bal:{a.get('balance','0')}\n"
            self.content.setPlainText(text)
        except Exception as e:
            self.content.setPlainText(f"Ledger error: {e}")

    def _load_journal(self):
        try:
            r = self._truth.get_ledger()
            # Use verify endpoint for simplicity
            summary = self._truth.get_summary()
            d = summary.get("data", summary) if isinstance(summary, dict) else summary
            self.content.setPlainText(f"Event Store Summary:\n{d}")
        except Exception as e:
            self.content.setPlainText(f"Journal error: {e}")

    def _load_tb(self):
        try:
            r = self._truth.get_trial_balance()
            d = r.get("data", r) if isinstance(r, dict) else r
            text = f"Trial Balance:\n"
            text += f"  Total Debits: {d.get('total_debits', 'N/A')}\n"
            text += f"  Total Credits: {d.get('total_credits', 'N/A')}\n"
            text += f"  Balanced: {d.get('is_balanced', 'N/A')}\n"
            text += f"  Difference: {d.get('difference', 'N/A')}\n"
            text += f"  Accounts: {d.get('account_count', 0)}"
            self.content.setPlainText(text)
        except Exception as e:
            self.content.setPlainText(f"TB error: {e}")

    def _load_consistency(self):
        try:
            r = self._truth.check_consistency()
            d = r.get("data", r) if isinstance(r, dict) else r
            text = f"Event Store Consistency:\n"
            text += f"  Consistent: {d.get('consistent', 'N/A')}\n"
            text += f"  Total Events: {d.get('total_events', 0)}\n"
            text += f"  Sequence Gaps: {d.get('sequence_gaps', 0)}\n"
            text += f"  Timestamp Anomalies: {d.get('timestamp_anomalies', 0)}\n"
            for domain, count in d.get("events_by_domain", {}).items():
                text += f"  {domain}: {count}\n"
            self.content.setPlainText(text)
        except Exception as e:
            self.content.setPlainText(f"Consistency error: {e}")

    def set_api_client(self, client: APIClient):
        self._api = client
        self._truth = TruthAPIClient(client)

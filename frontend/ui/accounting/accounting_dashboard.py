from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QFrame, QPushButton, QScrollArea,
                                QGroupBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import extract_list
from datetime import date
from runtime.timer_registry import register_timer, unregister_owner

# Design tokens
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)  # noqa: F401


class AccountingDashboard(QWidget):
    """Accounting dashboard with financial overview and quick actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.setup_ui()
        self.load_data()
        self._start_reconciliation_timer()

    def _start_reconciliation_timer(self):
        self._recon_timer = QTimer(self)
        self._recon_timer.timeout.connect(self.load_data)
        self._recon_timer.start(300000)
        register_timer("acct_dashboard", self._recon_timer)

    def cleanup(self):
        unregister_owner("acct_dashboard")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(SPACING_MD + SPACING_XS)

        self.summary_cards = self._create_summary_cards()
        content_layout.addWidget(self.summary_cards)

        self.inventory_valuation = self._create_inventory_valuation()
        content_layout.addWidget(self.inventory_valuation)

        self.quick_actions = self._create_quick_actions()
        content_layout.addWidget(self.quick_actions)

        self.recent_entries = self._create_recent_entries()
        content_layout.addWidget(self.recent_entries)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_summary_cards(self):
        card_widget = QWidget()
        card_layout = QGridLayout(card_widget)
        card_layout.setSpacing(SPACING_MD)

        self.card_labels = {}
        card_configs = [
            ("total_assets", "Total Assets", "0.00", COLOR_PRIMARY),
            ("total_liabilities", "Total Liabilities", "0.00", COLOR_DANGER),
            ("total_equity", "Total Equity", "0.00", COLOR_SUCCESS),
            ("net_income", "Net Income (YTD)", "0.00", COLOR_WARNING),
            ("cash_balance", "Cash Balance", "0.00", COLOR_INFO),
            ("ar_outstanding", "AR Outstanding", "0.00", COLOR_PRIMARY),
            ("ap_outstanding", "AP Outstanding", "0.00", COLOR_TEXT_SECONDARY),
            ("journal_count", "Journal Entries", "0", COLOR_TEXT_MUTED),
            ("reconciliation_status", "Reconciliation", "Checking...", COLOR_TEXT_MUTED),
        ]

        for i, (key, title, value, color) in enumerate(card_configs):
            card = self._create_summary_card(key, title, value, color)
            row, col = divmod(i, 4)
            card_layout.addWidget(card, row, col)
            self.card_labels[key] = card.findChild(QLabel, f"value_{key}")

        return card_widget

    def _create_summary_card(self, key, title, value, accent_color):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setMinimumHeight(90)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(SPACING_MD,  SPACING_SM,  SPACING_MD,  SPACING_SM)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Medium))
        title_label.setStyleSheet(f"color: {accent_color};")

        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        value_label.setObjectName(f"value_{key}")
        value_label.setAlignment(Qt.AlignRight)
        value_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_MAIN};
                border-radius: 8px;
                border-left: 4px solid {accent_color};
            }}
        """)

        return frame

    def _create_inventory_valuation(self):
        group = QGroupBox("Inventory Valuation")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout = QVBoxLayout(group)

        self.inventory_value_label = QLabel("Loading...")
        self.inventory_value_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.inventory_value_label)

        self.inventory_diff_label = QLabel("")
        self.inventory_diff_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.inventory_diff_label)

        return group

    def _load_inventory_valuation(self):
        try:
            result = self.api_client.get("/api/inventory/stock-movements/stock_valuation/")
            if result:
                total_value = result.get("total_inventory_value", "0")
                accounting_balance = result.get("accounting_inventory_balance", "N/A")
                diff = result.get("reconciliation_diff", "N/A")

                self.inventory_value_label.setText(f"AFN {float(total_value):,.2f}")

                if diff != "N/A":
                    diff_val = float(diff)
                    if abs(diff_val) < 0.02:
                        self.inventory_diff_label.setText("✓ In sync with accounting")
                        self.inventory_diff_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
                    else:
                        self.inventory_diff_label.setText(f"⚠ Diff: AFN {diff_val:,.2f}")
                        self.inventory_diff_label.setStyleSheet(f"color: {COLOR_WARNING};")
                else:
                    self.inventory_diff_label.setText("Accounting balance unavailable")
        except Exception as e:
            print(f"Error loading inventory valuation: {e}")
            self.inventory_value_label.setText("N/A")

    def _create_quick_actions(self):
        group = QGroupBox("Quick Actions")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout = QHBoxLayout(group)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        actions = [
            ("New Journal Entry", COLOR_PRIMARY),
            ("Trial Balance", COLOR_SUCCESS),
            ("Profit & Loss", COLOR_WARNING),
            ("Balance Sheet", COLOR_INFO),
            ("Account Ledger", COLOR_INFO),
            ("AR Aging", COLOR_DANGER),
        ]

        for title, color in actions:
            btn = QPushButton(title)
            btn.setMinimumHeight(40)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border-radius: 6px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {color}dd;
                }}
            """)
            layout.addWidget(btn)

        return group

    def _create_recent_entries(self):
        group = QGroupBox("Recent Journal Entries")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout = QVBoxLayout(group)
        layout.setSpacing(SPACING_XS + 1)

        self.entries_table = self._create_entries_table()
        layout.addWidget(self.entries_table)

        return group

    def _create_entries_table(self):
        from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Entry #", "Date", "Type", "Description", "Debit", "Credit"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)

        return table

    def load_data(self):
        self._load_summary_data()
        self._load_recent_entries()
        self._load_inventory_valuation()

    def _load_summary_data(self):
        try:
            today = date.today().isoformat()
            summary = self.api_client.get(
                "/api/accounting/accounts/account_summary/",
                params={"as_of_date": today}
            )

            if "ASSET" in summary:
                self._set_card_value("total_assets", summary["ASSET"]["net_balance"])
            if "LIABILITY" in summary:
                self._set_card_value("total_liabilities", summary["LIABILITY"]["net_balance"])
            if "EQUITY" in summary:
                self._set_card_value("total_equity", summary["EQUITY"]["net_balance"])
            if "REVENUE" in summary and "EXPENSE" in summary:
                net = summary["REVENUE"]["net_balance"] - summary["EXPENSE"]["net_balance"]
                self._set_card_value("net_income", net)

        except Exception as e:
            print(f"Error loading summary: {e}")

        try:
            ar_aging = self.api_client.get("/api/accounting/accounts/ar_aging/")
            if "totals" in ar_aging:
                self._set_card_value("ar_outstanding", ar_aging["totals"]["total"])
        except Exception:
            pass

        try:
            ap_aging = self.api_client.get("/api/accounting/accounts/ap_aging/")
            if "totals" in ap_aging:
                self._set_card_value("ap_outstanding", ap_aging["totals"]["total"])
        except Exception:
            pass

        try:
            entries = self.api_client.get("/api/accounting/journal-entries/", params={"page_size": 1})
            count = 0
            if isinstance(entries, dict):
                data = entries.get("data", {})
                if isinstance(data, dict):
                    count = data.get("count", 0)
            self._set_card_value("journal_count", count)
        except Exception:
            pass

        # Load reconciliation status
        self._load_reconciliation_status()

    def _load_reconciliation_status(self):
        """Load accounting reconciliation status and update indicator."""
        try:
            result = self.api_client.get("/api/accounting/accounts/reconciliation/")
            if result:
                is_healthy = result.get("is_healthy", False)
                summary = result.get("summary", {})
                self._set_card_value(
                    "reconciliation_status",
                    f"{summary.get('passed', 0)}/{summary.get('total_checks', 0)}"
                )
                # Update card color based on health
                if "reconciliation_status" in self.card_labels:
                    label = self.card_labels["reconciliation_status"]
                    if is_healthy:
                        label.setStyleSheet(
                            f"color: {COLOR_SUCCESS}; font-weight: bold; font-size: 20px;"
                        )
                    else:
                        label.setStyleSheet(
                            f"color: {COLOR_DANGER}; font-weight: bold; font-size: 20px;"
                        )
        except Exception as e:
            print(f"Error loading reconciliation status: {e}")
            try:
                self._set_card_value("reconciliation_status", "N/A")
            except Exception:
                pass

    def _set_card_value(self, key, value):
        if key in self.card_labels:
            label = self.card_labels[key]
            if key == "journal_count":
                label.setText(str(value))
            else:
                label.setText(f"{float(value):,.2f}")

    def _load_recent_entries(self):
        try:
            entries = self.api_client.get("/api/accounting/journal-entries/", params={"page_size": 10})
            results = extract_list(entries)

            self.entries_table.setRowCount(len(results))
            for row, entry in enumerate(results):
                self.entries_table.setItem(row, 0, self._item(entry.get("entry_number", "")))
                self.entries_table.setItem(row, 1, self._item(entry.get("entry_date", "")))
                self.entries_table.setItem(row, 2, self._item(entry.get("entry_type", "")))
                self.entries_table.setItem(row, 3, self._item(entry.get("description", "")))
                self.entries_table.setItem(row, 4, self._item(str(entry.get("total_debit", "0.00"))))
                self.entries_table.setItem(row, 5, self._item(str(entry.get("total_credit", "0.00"))))

                posted = entry.get("is_posted", False)
                status_color = COLOR_SUCCESS if posted else COLOR_WARNING
                for col in range(6):
                    item = self.entries_table.item(row, col)
                    if item:
                        item.setData(Qt.UserRole, {"id": entry.get("id"), "is_posted": posted})

        except Exception as e:
            print(f"Error loading recent entries: {e}")

    def _item(self, text):
        from PySide6.QtWidgets import QTableWidgetItem
        return QTableWidgetItem(str(text))

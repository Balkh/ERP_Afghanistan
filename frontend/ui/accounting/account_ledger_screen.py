import logging
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QDateEdit,
                               QGroupBox)
from PySide6.QtCore import Qt, QDate
from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from utils.company_config import get_cached_config
from utils.format import safe_float
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_LG, SPACING_XL, TEXT_PAGE_TITLE, TEXT_BODY, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.components.tables import EnterpriseTable, TableColumn
from ui.screens.base_screen import BaseScreen
from theme.style_builder import UIStyleBuilder


class AccountLedgerScreen(BaseScreen):
    """Account Ledger screen with date range and running balance."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="account_ledger")
        self.api_client = api_client or APIClient()
        self.accounts = []
        self._is_loading = False
        self.setup_ui()
        self.load_accounts()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load in __init__."""

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        header = QLabel("Account Ledger")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)

        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("Account:"))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(250)
        self.account_combo.addItem("Select an account...", None)
        filter_layout.addWidget(self.account_combo)

        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(self.date_to)

        filter_layout.addStretch()

        self.btn_load = EnterpriseButton(text="Load Ledger", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_load.clicked.connect(self.load_ledger)
        filter_layout.addWidget(self.btn_load)

        self.btn_export_csv = EnterpriseButton(text="Export CSV", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_export_csv.clicked.connect(self.export_csv)
        filter_layout.addWidget(self.btn_export_csv)

        self.btn_print = EnterpriseButton(text="Print Preview", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_print.clicked.connect(self.print_preview)
        filter_layout.addWidget(self.btn_print)

        layout.addWidget(filter_group)

        info_group = QGroupBox("Account Information")
        info_layout = QHBoxLayout(info_group)

        self.info_code = QLabel("")
        self.info_name = QLabel("")
        self.info_type = QLabel("")
        self.info_opening = QLabel("Opening: 0.00")
        self.info_closing = QLabel("Closing: 0.00")

        for label in [self.info_code, self.info_name, self.info_type]:
            label.setStyleSheet(f"font-size: {TEXT_BODY}pt; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
            info_layout.addWidget(label)
        info_layout.addStretch()
        info_layout.addWidget(self.info_opening)
        info_layout.addWidget(self.info_closing)

        layout.addWidget(info_group)

        # Loading and Empty states
        self.loading_label = QLabel("Loading ledger...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(UIStyleBuilder.get_state_label_style("loading"))
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("Select an account and load the ledger.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(UIStyleBuilder.get_state_label_style("empty"))
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.table = self._create_table()
        layout.addWidget(self.table)

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self._is_loading = show
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.btn_load.setEnabled(not show)

    def _show_empty(self, message="No ledger data available"):
        """Show empty state."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.btn_load.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.table.setVisible(True)
        self.btn_load.setEnabled(True)


    def _create_table(self):
        columns = [
            TableColumn("entry_number", "Entry #", width=80),
            TableColumn("entry_date", "Date", width=100, align="center"),
            TableColumn("entry_type", "Type", width=80),
            TableColumn("description", "Description", width=250),
            TableColumn("debit", "Debit", width=100, align="right"),
            TableColumn("credit", "Credit", width=100, align="right"),
            TableColumn("balance", "Balance", width=100, align="right"),
        ]
        table = EnterpriseTable(columns, density="compact")
        return table

    def load_accounts(self):
        try:
            endpoint = get_endpoint("leaf_accounts")
            response = self.api_client.get(endpoint)
            self.accounts = extract_list(response)
            self.account_combo.clear()
            self.account_combo.addItem("Select an account...", None)
            for acc in sorted(self.accounts, key=lambda x: x.get("code") or ""):
                code = acc.get("code") or ""
                name = acc.get("name") or "Unknown"
                acc_id = acc.get("id")
                if acc_id:
                    self.account_combo.addItem(f"{code} - {name}", acc_id)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading accounts: {e}")
            self.accounts = []

    def load_ledger(self):
        account_id = self.account_combo.currentData()
        if not account_id:
            AlertDialog.warning("Warning", "Please select an account.", self)
            return

        self._show_loading()
        params = {"account_id": account_id}

        from PySide6.QtCore import QDate
        from_date = self.date_from.date()
        to_date = self.date_to.date()

        if from_date != QDate():
            params["start_date"] = from_date.toString("yyyy-MM-dd")
        if to_date != QDate():
            params["end_date"] = to_date.toString("yyyy-MM-dd")

        try:
            endpoint = get_endpoint("ledger")
            data = self.api_client.get(endpoint, params=params)
            if data and isinstance(data, dict):
                self._populate_table(data)
            else:
                self._show_empty("Failed to load ledger data")
        except Exception as e:
            self._show_empty(f"Error loading ledger: {e}")

    def _populate_table(self, data):
        self.ledger_data = data # Store for export
        if not isinstance(data, dict):
            self._show_empty("Invalid ledger data")
            return

        if "error" in data:
            self._show_empty(data.get("error", "Unknown error"))
            return

        self.info_code.setText(f"Code: {data.get('account_code') or ''}")
        self.info_name.setText(f"Name: {data.get('account_name') or ''}")
        self.info_type.setText(f"Type: {data.get('account_type') or ''}")

        opening = safe_float(data.get("opening_balance"))
        closing = safe_float(data.get("closing_balance"))
        self.info_opening.setText(f"Opening: {opening:,.2f}")
        self.info_closing.setText(f"Closing: {closing:,.2f}")

        entries = data.get("entries", [])
        if not entries:
            self._show_empty("No ledger entries for selected period")
            return

        if not isinstance(entries, list):
            entries = []

        self._show_data()
        ledger_data = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            debit = safe_float(entry.get("debit"))
            credit = safe_float(entry.get("credit"))
            balance = safe_float(entry.get("running_balance"))
            ledger_data.append({
                "entry_number": entry.get("entry_number") or "",
                "entry_date": entry.get("entry_date") or "",
                "entry_type": entry.get("entry_type") or "",
                "description": entry.get("description") or "",
                "debit": f"{debit:,.2f}",
                "credit": f"{credit:,.2f}",
                "balance": f"{balance:,.2f}",
            })
        self.table.set_data(ledger_data)

    def export_csv(self):
        if not hasattr(self, 'ledger_data') or not self.ledger_data:
            AlertDialog.warning("Warning", "Load the ledger first.", self)
            return

        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", f"Ledger_{self.ledger_data.get('account_code', 'Report')}.csv", "CSV Files (*.csv)"
        )
        if file_path:
            try:
                # Use same params as load_ledger but with format=csv
                account_id = self.account_combo.currentData()
                params = {"account_id": account_id, "format": "csv"}
                
                from PySide6.QtCore import QDate
                if self.date_from.date() != QDate():
                    params["start_date"] = self.date_from.date().toString("yyyy-MM-dd")
                if self.date_to.date() != QDate():
                    params["end_date"] = self.date_to.date().toString("yyyy-MM-dd")

                endpoint = get_endpoint("ledger")
                csv_data = self.api_client.get(endpoint, params=params)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(csv_data if isinstance(csv_data, str) else str(csv_data))
                AlertDialog.info("Success", f"Ledger exported to {file_path}", self)
            except Exception as e:
                AlertDialog.error("Error", f"Failed to export: {e}", self)

    def print_preview(self):
        if not hasattr(self, 'ledger_data') or not self.ledger_data:
            AlertDialog.warning("Warning", "Load the ledger first.", self)
            return

        try:
            # Use same params but with format=text
            account_id = self.account_combo.currentData()
            params = {"account_id": account_id, "format": "text"}
            
            from PySide6.QtCore import QDate
            if self.date_from.date() != QDate():
                params["start_date"] = self.date_from.date().toString("yyyy-MM-dd")
            if self.date_to.date() != QDate():
                params["end_date"] = self.date_to.date().toString("yyyy-MM-dd")

            endpoint = get_endpoint("ledger")
            text_data = self.api_client.get(endpoint, params=params)

            from ui.accounting.components.report_preview_dialog import ReportPreviewDialog
            from datetime import datetime
            config = get_cached_config()
            company_name = config.name if config else "Pharmacy ERP"
            report_meta = {
                "report_name": f"Ledger - {self.ledger_data.get('account_name', 'N/A')}",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "company": company_name,
                "period": f"{self.date_from.date().toString('yyyy-MM-dd')} to {self.date_to.date().toString('yyyy-MM-dd')}" if self.date_from.date() != QDate() else "All time",
            }
            dialog = ReportPreviewDialog(self, f"Ledger - {self.ledger_data.get('account_name')}", text_data, report_meta)
            dialog.exec()
        except Exception as e:
            AlertDialog.error("Error", f"Failed to generate preview: {e}", self)

from PySide6.QtWidgets import QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ui.accounting.base_report_screen import BaseReportScreen
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


class TrialBalanceScreen(BaseReportScreen):
    """Trial Balance Report Screen."""

    report_api_endpoint = "/api/accounting/accounts/trial_balance/"

    def __init__(self, parent=None):
        super().__init__("Trial Balance", parent)
        self._configure_table()

    def _configure_table(self):
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Code", "Account Name", "Type", "Debit", "Credit", "Net Balance", "Balance Type"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

    def run_report(self):
        self._show_loading()
        try:
            params = self._get_report_params()
            self.report_data = self.api_client.get(self.report_api_endpoint, params=params)
            self._populate_table()
        except Exception as e:
            self._show_empty(f"Error loading trial balance: {e}")

    def _populate_table(self):
        if not isinstance(self.report_data, dict):
            self._show_empty("No data available")
            return

        accounts = self.report_data.get("accounts", [])
        if not accounts:
            self._show_empty("No account data available")
            return

        if not isinstance(accounts, list):
            accounts = []

        self.table.setRowCount(len(accounts) + 2)

        for row, acc in enumerate(accounts):
            if not isinstance(acc, dict):
                continue
            self.table.setItem(row, 0, self._item(acc.get("account_code") or ""))
            self.table.setItem(row, 1, self._item(acc.get("account_name") or ""))
            self.table.setItem(row, 2, self._item(acc.get("account_type") or ""))

            debit = self._safe_float(acc.get("total_debit"))
            credit = self._safe_float(acc.get("total_credit"))
            net = self._safe_float(acc.get("net_balance"))

            debit_item = self._item(f"{debit:,.2f}")
            if debit > 0:
                debit_item.setForeground(QColor("COLOR_SUCCESS"))
            self.table.setItem(row, 3, debit_item)

            credit_item = self._item(f"{credit:,.2f}")
            if credit > 0:
                credit_item.setForeground(QColor("COLOR_DANGER"))
            self.table.setItem(row, 4, credit_item)

            self.table.setItem(row, 5, self._item(f"{net:,.2f}"))
            self.table.setItem(row, 6, self._item(acc.get("balance_type") or ""))

        last_row = len(accounts)
        total_debit = self._safe_float(self.report_data.get("total_debit"))
        total_credit = self._safe_float(self.report_data.get("total_credit"))

        self.table.setItem(last_row, 0, self._bold_item(""))
        self.table.setItem(last_row, 1, self._bold_item("TOTALS"))
        self.table.setItem(last_row, 2, self._bold_item(""))
        self.table.setItem(last_row, 3, self._bold_item(f"{total_debit:,.2f}"))
        self.table.setItem(last_row, 4, self._bold_item(f"{total_credit:,.2f}"))

        is_balanced = bool(self.report_data.get("is_balanced", False))
        diff = self._safe_float(self.report_data.get("difference"))
        status_text = "BALANCED" if is_balanced else f"NOT BALANCED (diff: {diff:,.2f})"
        status_item = self._bold_item(status_text)
        if is_balanced:
            status_item.setForeground(QColor("COLOR_SUCCESS"))
        else:
            status_item.setForeground(QColor("COLOR_DANGER"))
        self.table.setItem(last_row, 5, status_item)
        self.table.setItem(last_row, 6, self._bold_item(""))

        self._show_data()
        self.summary_label.setText(
            f"Total Debit: {total_debit:,.2f} | Total Credit: {total_credit:,.2f} | "
            f"{'BALANCED' if is_balanced else 'NOT BALANCED'}"
        )

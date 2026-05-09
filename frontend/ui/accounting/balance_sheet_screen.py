from PySide6.QtWidgets import QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ui.accounting.base_report_screen import BaseReportScreen

# Design tokens
from ui.constants import COLOR_PRIMARY
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


class BalanceSheetScreen(BaseReportScreen):
    """Balance Sheet Report Screen."""

    report_api_endpoint = "/api/accounting/accounts/balance_sheet/"

    def __init__(self, parent=None):
        super().__init__("Balance Sheet", parent)
        self._configure_table()

    def _configure_table(self):
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Account", "Category", "Amount"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def run_report(self):
        self._show_loading()
        try:
            params = self._get_report_params()
            params["format"] = "json"
            self.report_data = self.api_client.get(self.report_api_endpoint, params=params)
            self._populate_table()
        except Exception as e:
            self._show_empty(f"Error loading balance sheet: {e}")

    def _populate_table(self):
        if not isinstance(self.report_data, dict):
            self._show_empty("No data available")
            return

        assets_data = self.report_data.get("assets") or {}
        liabilities_data = self.report_data.get("liabilities") or {}
        equity_data = self.report_data.get("equity") or {}

        if not assets_data and not liabilities_data and not equity_data:
            self._show_empty("No balance sheet data available")
            return

        rows = []

        rows.append(("ASSETS", "", None))
        assets_sections = assets_data.get("sections") or []
        for section in assets_sections:
            if isinstance(section, dict):
                rows.append((f"  {section.get('category') or ''}", "", section.get("total") or 0))
                for acc in section.get("accounts", []):
                    if isinstance(acc, dict):
                        code = acc.get("account_code") or ""
                        name = acc.get("account_name") or ""
                        rows.append((f"    {code} - {name}", acc.get("category") or "", acc.get("amount") or 0))
        rows.append(("Total Assets", "", assets_data.get("total") or 0))
        rows.append(("", "", None))

        rows.append(("LIABILITIES", "", None))
        liabilities_sections = liabilities_data.get("sections") or []
        for section in liabilities_sections:
            if isinstance(section, dict):
                rows.append((f"  {section.get('category') or ''}", "", section.get("total") or 0))
                for acc in section.get("accounts", []):
                    if isinstance(acc, dict):
                        code = acc.get("account_code") or ""
                        name = acc.get("account_name") or ""
                        rows.append((f"    {code} - {name}", acc.get("category") or "", acc.get("amount") or 0))
        rows.append(("Total Liabilities", "", liabilities_data.get("total") or 0))
        rows.append(("", "", None))

        rows.append(("EQUITY", "", None))
        equity_sections = equity_data.get("sections") or []
        for section in equity_sections:
            if isinstance(section, dict):
                rows.append((f"  {section.get('category') or ''}", "", section.get("total") or 0))
                for acc in section.get("accounts", []):
                    if isinstance(acc, dict):
                        code = acc.get("account_code") or ""
                        name = acc.get("account_name") or ""
                        rows.append((f"    {code} - {name}", acc.get("category") or "", acc.get("amount") or 0))
        rows.append(("Total Equity", "", equity_data.get("total") or 0))
        rows.append(("", "", None))

        total_le = self.report_data.get("total_liabilities_equity") or 0
        rows.append(("TOTAL LIABILITIES + EQUITY", "", total_le))

        if not rows or len(rows) <= 3:
            self._show_empty("No balance sheet data available")
            return

        self.table.setRowCount(len(rows))
        for row, (account, category, amount) in enumerate(rows):
            if amount is None:
                item = self._bold_item(account)
                item.setForeground(QColor(COLOR_PRIMARY))
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, self._item(category))
                self.table.setItem(row, 2, self._item(""))
            else:
                amt = self._safe_float(amount)
                is_total = "Total" in account or account == account.upper()
                item = self._item(account)
                if is_total:
                    item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, self._item(category))
                amt_item = self._item(f"{amt:,.2f}")
                if is_total:
                    amt_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.table.setItem(row, 2, amt_item)

        self._show_data()
        is_balanced = bool(self.report_data.get("is_balanced"))
        diff = self._safe_float(self.report_data.get("difference"))
        total_assets = self._safe_float(assets_data.get("total"))
        total_le_val = self._safe_float(total_le)

        self.summary_label.setText(
            f"Assets: {total_assets:,.2f} | L+E: {total_le_val:,.2f} | "
            f"{'BALANCED' if is_balanced else f'NOT BALANCED (diff: {diff:,.2f})'}"
        )

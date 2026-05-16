from PySide6.QtWidgets import QHeaderView, QMessageBox, QLabel
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from ui.accounting.base_report_screen import BaseReportScreen

# Design tokens
from ui.constants import COLOR_SUCCESS, COLOR_DANGER
    TEXT_BODY, TEXT_BODY_SMALL,
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.constants import TEXT_BODY, TEXT_BODY_SMALL


class ProfitAndLossScreen(BaseReportScreen):
    """Profit & Loss Report Screen."""

    report_api_endpoint = "/api/accounting/accounts/income_statement/"

    def __init__(self, parent=None):
        super().__init__("Profit & Loss", parent)
        self._update_toolbar()
        self._configure_table()

    def _update_toolbar(self):
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QDateEdit, QPushButton, QGroupBox
        toolbar = self.findChild(QGroupBox, "Parameters")
        if toolbar:
            layout = toolbar.layout()
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

            layout.addWidget(QLabel("From:"))
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDisplayFormat("yyyy-MM-dd")
            self.date_from.setDate(QDate.currentDate().addMonths(-1))
            layout.addWidget(self.date_from)

            layout.addWidget(QLabel("To:"))
            self.date_to = QDateEdit()
            self.date_to.setCalendarPopup(True)
            self.date_to.setDisplayFormat("yyyy-MM-dd")
            self.date_to.setDate(QDate.currentDate())
            layout.addWidget(self.date_to)

            layout.addStretch()

            self.btn_run = QPushButton("Run Report")
            self.btn_run.setMinimumHeight(32)
            self.btn_run.clicked.connect(self.run_report)
            layout.addWidget(self.btn_run)

            self.btn_export_csv = QPushButton("Export CSV")
            self.btn_export_csv.setMinimumHeight(32)
            self.btn_export_csv.clicked.connect(self.export_csv)
            layout.addWidget(self.btn_export_csv)

            self.btn_print = QPushButton("Print Preview")
            self.btn_print.setMinimumHeight(32)
            self.btn_print.clicked.connect(self.print_preview)
            layout.addWidget(self.btn_print)

    def _configure_table(self):
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Account", "Category", "Amount"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def run_report(self):
        self._show_loading()
        try:
            params = {}
            from PySide6.QtCore import QDate
            if self.date_from.date() != QDate():
                params["start_date"] = self.date_from.date().toString("yyyy-MM-dd")
            if self.date_to.date() != QDate():
                params["end_date"] = self.date_to.date().toString("yyyy-MM-dd")
            params["format"] = "json"

            self.report_data = self.api_client.get(self.report_api_endpoint, params=params)
            if isinstance(self.report_data, dict):
                self.report_data = self.report_data.get("data", self.report_data)
            self._populate_table()
        except Exception as e:
            self._show_empty(f"Error loading P&L: {e}")

    def _populate_table(self):
        if not isinstance(self.report_data, dict):
            self._show_empty("No data available")
            return

        revenue = self.report_data.get("revenue") or []
        cogs = self.report_data.get("cogs") or []
        expenses = self.report_data.get("expenses") or []

        if not revenue and not cogs and not expenses:
            self._show_empty("No P&L data available for selected period")
            return

        rows = []
        rows.append(("REVENUE", "", None))
        for section in revenue:
            if isinstance(section, dict) and "accounts" in section:
                rows.append((f"  {section.get('category') or ''}", "", section.get("total") or 0))
                for acc in section.get("accounts", []):
                    if isinstance(acc, dict):
                        code = acc.get("account_code") or ""
                        name = acc.get("account_name") or ""
                        rows.append((f"    {code} - {name}", acc.get("category") or "", acc.get("amount") or 0))
            elif isinstance(section, dict):
                code = section.get("account_code") or ""
                name = section.get("account_name") or ""
                rows.append((f"    {code} - {name}", section.get("category") or "", section.get("amount") or 0))

        rows.append(("Total Revenue", "", self.report_data.get("total_revenue") or 0))
        rows.append(("", "", None))

        rows.append(("COST OF GOODS SOLD", "", None))
        for section in cogs:
            if isinstance(section, dict) and "accounts" in section:
                for acc in section.get("accounts", []):
                    if isinstance(acc, dict):
                        code = acc.get("account_code") or ""
                        name = acc.get("account_name") or ""
                        rows.append((f"    {code} - {name}", acc.get("category") or "", acc.get("amount") or 0))

        rows.append(("Total COGS", "", self.report_data.get("total_cogs") or 0))
        rows.append(("", "", None))

        gross_profit = self.report_data.get("gross_profit") or 0
        rows.append(("GROSS PROFIT", "", gross_profit))
        rows.append(("", "", None))

        rows.append(("EXPENSES", "", None))
        for section in expenses:
            if isinstance(section, dict) and "accounts" in section:
                rows.append((f"  {section.get('category') or ''}", "", section.get("total") or 0))
                for acc in section.get("accounts", []):
                    if isinstance(acc, dict):
                        code = acc.get("account_code") or ""
                        name = acc.get("account_name") or ""
                        rows.append((f"    {code} - {name}", acc.get("category") or "", acc.get("amount") or 0))
            elif isinstance(section, dict):
                code = section.get("account_code") or ""
                name = section.get("account_name") or ""
                rows.append((f"    {code} - {name}", section.get("category") or "", section.get("amount") or 0))

        rows.append(("Total Expenses", "", self.report_data.get("total_expenses") or 0))
        rows.append(("", "", None))

        net_income = self.report_data.get("net_income") or 0
        rows.append(("NET INCOME", "", net_income))

        if not rows or len(rows) <= 3:
            self._show_empty("No P&L data available for selected period")
            return

        self.table.setRowCount(len(rows))
        for row, (account, category, amount) in enumerate(rows):
            if amount is None:
                self.table.setItem(row, 0, self._item(account))
                self.table.setItem(row, 1, self._item(category))
                self.table.setItem(row, 2, self._item(""))
            else:
                amt = self._safe_float(amount)
                item = self._item(account)
                if account.startswith("    "):
                    pass
                elif account.startswith("  "):
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                elif account == account.upper():
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, self._item(category))
                amt_item = self._item(f"{amt:,.2f}")
                if account == "NET INCOME":
                    net_font = QFont("Segoe UI", TEXT_BODY)
                    net_font.setWeight(QFont.Weight.Bold)
                    amt_item.setFont(net_font)
                    if amt >= 0:
                        amt_item.setForeground(QColor(COLOR_SUCCESS))
                    else:
                        amt_item.setForeground(QColor(COLOR_DANGER))
                elif "Total" in account or "GROSS" in account:
                    total_font = QFont("Segoe UI", TEXT_BODY_SMALL)
                    total_font.setWeight(QFont.Weight.Bold)
                    amt_item.setFont(total_font)
                self.table.setItem(row, 2, amt_item)

        self._show_data()
        total_revenue = self._safe_float(self.report_data.get("total_revenue"))
        total_expenses = self._safe_float(self.report_data.get("total_expenses"))
        net_income_val = self._safe_float(net_income)

        self.summary_label.setText(
            f"Revenue: {total_revenue:,.2f} | "
            f"Expenses: {total_expenses:,.2f} | "
            f"Net Income: {net_income_val:,.2f}"
        )

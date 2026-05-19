from PySide6.QtWidgets import QHeaderView, QMessageBox
from PySide6.QtGui import QFont, QColor
from ui.accounting.base_report_screen import BaseReportScreen

# Design tokens
from ui.constants import (COLOR_DANGER, COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.constants import TEXT_TABLE


class ARAPAgeingScreen(BaseReportScreen):
    """AR/AP Ageing Report Screen (handles both)."""

    def __init__(self, report_type="ar", parent=None):
        self.report_type = report_type
        title = "Accounts Receivable Ageing" if report_type == "ar" else "Accounts Payable Ageing"
        self.report_api_endpoint = "/api/accounting/accounts/ar_aging/" if report_type == "ar" else "/api/accounting/accounts/ap_aging/"
        super().__init__(title, parent)
        self._configure_table()

    def _configure_table(self):
        self.table.setColumnCount(7)
        party_label = "Customer" if self.report_type == "ar" else "Supplier"
        self.table.setHorizontalHeaderLabels([
            party_label, "Current", "1-30 Days", "31-60 Days", "61-90 Days", "90+ Days", "Total"
        ])

    def run_report(self):
        self._show_loading()
        try:
            params = self._get_report_params()
            params["format"] = "json"
            self.report_data = self.api_client.get(self.report_api_endpoint, params=params)
            if isinstance(self.report_data, dict):
                self.report_data = self.report_data.get("data", self.report_data)
            self._populate_table()
        except Exception as e:
            self._show_empty(f"Error loading report: {e}")

    def _populate_table(self):
        if not isinstance(self.report_data, dict):
            self._show_empty("No data available")
            return

        rows = self.report_data.get("ageing_rows", [])
        if not rows:
            self._show_empty("No ageing data available")
            return

        if not isinstance(rows, list):
            rows = []

        totals = self.report_data.get("totals", {}) or {}

        self.table.setRowCount(len(rows) + 1)

        for row, entry in enumerate(rows):
            if not isinstance(entry, dict):
                continue
            self.table.setItem(row, 0, self._item(entry.get("party_name", "")))
            self.table.setItem(row, 1, self._item(f"{self._safe_float(entry.get('current')):,.2f}"))
            self.table.setItem(row, 2, self._item(f"{self._safe_float(entry.get('age_1_30')):,.2f}"))
            self.table.setItem(row, 3, self._item(f"{self._safe_float(entry.get('age_31_60')):,.2f}"))
            self.table.setItem(row, 4, self._item(f"{self._safe_float(entry.get('age_61_90')):,.2f}"))
            self.table.setItem(row, 5, self._item(f"{self._safe_float(entry.get('age_90_plus')):,.2f}"))
            total_item = self._item(f"{self._safe_float(entry.get('total')):,.2f}")
            total_font = QFont("Segoe UI", TEXT_TABLE)
            total_font.setWeight(QFont.Weight.Bold)
            total_item.setFont(total_font)
            self.table.setItem(row, 6, total_item)

        last_row = len(rows)
        self.table.setItem(last_row, 0, self._bold_item("TOTAL"))
        self.table.setItem(last_row, 1, self._bold_item(f"{self._safe_float(totals.get('current')):,.2f}"))
        self.table.setItem(last_row, 2, self._bold_item(f"{self._safe_float(totals.get('age_1_30')):,.2f}"))
        self.table.setItem(last_row, 3, self._bold_item(f"{self._safe_float(totals.get('age_31_60')):,.2f}"))
        self.table.setItem(last_row, 4, self._bold_item(f"{self._safe_float(totals.get('age_61_90')):,.2f}"))
        self.table.setItem(last_row, 5, self._bold_item(f"{self._safe_float(totals.get('age_90_plus')):,.2f}"))
        total_item = self._bold_item(f"{self._safe_float(totals.get('total')):,.2f}")
        total_item.setForeground(QColor(COLOR_DANGER))
        self.table.setItem(last_row, 6, total_item)

        self._show_data()
        total_outstanding = self._safe_float(totals.get('total'))
        self.summary_label.setText(
            f"Total Outstanding: {total_outstanding:,.2f} | "
            f"{'Customers' if self.report_type == 'ar' else 'Suppliers'} with balance: {len(rows)}"
        )

"""
Consolidated Report Browser — replaces 13 individual report screens.
Supports Accounting, HR, and Payroll report types via configuration.
"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                                QDateEdit, QGroupBox, QFileDialog)
from PySide6.QtCore import Qt, QDate
from datetime import date
from api.client import APIClient
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_CARD_TITLE, TEXT_BODY,
                           BORDER_RADIUS_MD, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED)
from ui.screens.base_screen import BaseScreen
from ui.components.dialogs import AlertDialog, ConfirmDialog
from ui.utils.signal_utils import connect_unique


REPORT_TYPES = {
    "trial_balance": {
        "title": "Trial Balance",
        "api": "/api/accounting/accounts/trial_balance/",
        "columns": [
            TableColumn("account_code", "Code", width=80),
            TableColumn("account_name", "Account Name", width=250),
            TableColumn("account_type", "Type", width=80),
            TableColumn("total_debit", "Debit", width=100, align="right"),
            TableColumn("total_credit", "Credit", width=100, align="right"),
            TableColumn("net_balance", "Net Balance", width=100, align="right"),
            TableColumn("balance_type", "Balance Type", width=80),
        ],
        "data_key": "accounts",
    },
    "profit_loss": {
        "title": "Profit & Loss",
        "api": "/api/accounting/accounts/profit_loss/",
        "columns": [
            TableColumn("account_code", "Code", width=80),
            TableColumn("account_name", "Account Name", width=250),
            TableColumn("account_type", "Type", width=80),
            TableColumn("balance", "Balance", width=100, align="right"),
        ],
        "data_key": "accounts",
    },
    "balance_sheet": {
        "title": "Balance Sheet",
        "api": "/api/accounting/accounts/balance_sheet/",
        "columns": [
            TableColumn("account_code", "Code", width=80),
            TableColumn("account_name", "Account Name", width=250),
            TableColumn("account_type", "Type", width=80),
            TableColumn("balance", "Balance", width=100, align="right"),
        ],
        "data_key": "accounts",
    },
    "cash_flow": {
        "title": "Cash Flow Statement",
        "api": "/api/accounting/accounts/cash_flow/",
        "columns": [
            TableColumn("category", "Category", width=250),
            TableColumn("amount", "Amount", width=100, align="right"),
        ],
        "data_key": "items",
    },
    "ar_aging": {
        "title": "AR Ageing",
        "api": "/api/accounting/accounts/ar_aging/",
        "columns": [
            TableColumn("customer_name", "Customer", width=200),
            TableColumn("current", "Current", width=100, align="right"),
            TableColumn("days_30", "1-30 Days", width=100, align="right"),
            TableColumn("days_60", "31-60 Days", width=100, align="right"),
            TableColumn("days_90", "61-90 Days", width=100, align="right"),
            TableColumn("days_90_plus", "90+ Days", width=100, align="right"),
            TableColumn("total", "Total", width=100, align="right"),
        ],
        "data_key": "customers",
    },
    "ap_aging": {
        "title": "AP Ageing",
        "api": "/api/accounting/accounts/ap_aging/",
        "columns": [
            TableColumn("supplier_name", "Supplier", width=200),
            TableColumn("current", "Current", width=100, align="right"),
            TableColumn("days_30", "1-30 Days", width=100, align="right"),
            TableColumn("days_60", "31-60 Days", width=100, align="right"),
            TableColumn("days_90", "61-90 Days", width=100, align="right"),
            TableColumn("days_90_plus", "90+ Days", width=100, align="right"),
            TableColumn("total", "Total", width=100, align="right"),
        ],
        "data_key": "suppliers",
    },
    "employee_summary": {
        "title": "Employee Summary",
        "api": "/api/hr/reports/employee-summary/",
        "columns": [
            TableColumn("status", "Status", width=200),
            TableColumn("count", "Count", width=100, align="center"),
        ],
        "data_key": None,
    },
    "attendance_report": {
        "title": "Attendance Report",
        "api": "/api/hr/reports/attendance-summary/",
        "columns": [
            TableColumn("date", "Date", width=120),
            TableColumn("present", "Present", width=80, align="center"),
            TableColumn("absent", "Absent", width=80, align="center"),
        ],
        "data_key": "records",
    },
    "leave_report": {
        "title": "Leave Report",
        "api": "/api/hr/reports/leave-summary/",
        "columns": [
            TableColumn("employee", "Employee", width=200),
            TableColumn("leave_type", "Leave Type", width=100),
            TableColumn("start_date", "Start Date", width=100, align="center"),
            TableColumn("end_date", "End Date", width=100, align="center"),
            TableColumn("total_days", "Days", width=60, align="center"),
            TableColumn("status", "Status", width=80),
        ],
        "data_key": "records",
    },
    "overtime_report": {
        "title": "Overtime Report",
        "api": "/api/hr/reports/overtime-summary/",
        "columns": [
            TableColumn("employee", "Employee", width=200),
            TableColumn("hours", "Overtime Hours", width=100, align="center"),
            TableColumn("amount", "Amount", width=100, align="right"),
        ],
        "data_key": "records",
    },
    "payroll_summary": {
        "title": "Payroll Summary",
        "api": "/api/payroll/reports/yearly-summary/",
        "columns": [
            TableColumn("metric", "Metric", width=200),
            TableColumn("value", "Value", width=100, align="right"),
        ],
        "data_key": None,
    },
    "payroll_trend": {
        "title": "Payroll Trend",
        "api": "/api/payroll/reports/trend/",
        "columns": [
            TableColumn("period", "Period", width=120),
            TableColumn("gross", "Gross", width=100, align="right"),
            TableColumn("net", "Net", width=100, align="right"),
        ],
        "data_key": "trend",
    },
    "payroll_dept_cost": {
        "title": "Department Payroll Cost",
        "api": "/api/payroll/reports/department-cost/",
        "columns": [
            TableColumn("department", "Department", width=200),
            TableColumn("total", "Total Cost", width=100, align="right"),
            TableColumn("percentage", "Percentage", width=80, align="center"),
        ],
        "data_key": "departments",
    },
    "payroll_emp_history": {
        "title": "Employee Payroll History",
        "api": "/api/payroll/reports/employee-history/",
        "columns": [
            TableColumn("employee", "Employee", width=200),
            TableColumn("period", "Period", width=100),
            TableColumn("gross", "Gross", width=100, align="right"),
            TableColumn("net", "Net", width=100, align="right"),
            TableColumn("status", "Status", width=80),
        ],
        "data_key": "records",
    },
}


class ReportBrowser(BaseScreen):
    """Consolidated report browser — handles all accounting/HR/payroll reports."""

    DATE_RANGE_REPORTS = {"profit_loss", "cash_flow"}

    def __init__(self, parent=None, report_type="trial_balance", api_client=None):
        super().__init__(parent, screen_id=f"report_{report_type}")
        self.api_client = api_client or APIClient()
        self.report_type = report_type
        self.report_data = {}
        self._build_ui()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — report data comes from Run Report."""

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        config = REPORT_TYPES.get(self.report_type, REPORT_TYPES["trial_balance"])

        header = QLabel(config["title"])
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)

        # Toolbar with type selector + date + actions
        toolbar = QGroupBox("Parameters")
        toolbar.setStyleSheet(f"""
            QGroupBox {{
                font-size: {TEXT_CARD_TITLE}pt; font-weight: 700;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                margin-top: {SPACING_SM}px; padding-top: {SPACING_SM}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {SPACING_XS}px;
            }}
        """)
        bar_layout = QHBoxLayout(toolbar)

        self.type_selector = QComboBox()
        groups = [
            ("-- Accounting Reports --", ["trial_balance", "profit_loss", "balance_sheet", "cash_flow", "ar_aging", "ap_aging"]),
            ("-- HR Reports --", ["employee_summary", "attendance_report", "leave_report", "overtime_report"]),
            ("-- Payroll Reports --", ["payroll_summary", "payroll_trend", "payroll_dept_cost", "payroll_emp_history"]),
        ]
        for group_label, keys in groups:
            self.type_selector.addItem(group_label, None)
            for k in keys:
                self.type_selector.addItem(REPORT_TYPES[k]["title"], k)

        idx = self.type_selector.findData(self.report_type)
        if idx >= 0:
            self.type_selector.setCurrentIndex(idx)
        connect_unique(self.type_selector.currentIndexChanged, self._on_type_changed)
        bar_layout.addWidget(QLabel("Report:"))
        bar_layout.addWidget(self.type_selector)

        self._is_date_range = self.report_type in self.DATE_RANGE_REPORTS
        if self._is_date_range:
            bar_layout.addWidget(QLabel("From:"))
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDisplayFormat("yyyy-MM-dd")
            self.date_from.setDate(QDate(date.today().year, date.today().month, date.today().day).addMonths(-1))
            bar_layout.addWidget(self.date_from)

            bar_layout.addWidget(QLabel("To:"))
            self.date_to = QDateEdit()
            self.date_to.setCalendarPopup(True)
            self.date_to.setDisplayFormat("yyyy-MM-dd")
            self.date_to.setDate(QDate(date.today().year, date.today().month, date.today().day))
            bar_layout.addWidget(self.date_to)
        else:
            bar_layout.addWidget(QLabel("Date:"))
            self.date_input = QDateEdit()
            self.date_input.setCalendarPopup(True)
            self.date_input.setDisplayFormat("yyyy-MM-dd")
            self.date_input.setDate(QDate(date.today().year, date.today().month, date.today().day))
            bar_layout.addWidget(self.date_input)

        bar_layout.addStretch()

        self.btn_run = EnterpriseButton(text="Run Report", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        connect_unique(self.btn_run.clicked, self.run_report)
        bar_layout.addWidget(self.btn_run)

        self.btn_export = EnterpriseButton(text="Export CSV", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        connect_unique(self.btn_export.clicked, self._export_csv)
        bar_layout.addWidget(self.btn_export)

        layout.addWidget(toolbar)

        # Loading / Empty
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("Run the report to generate data.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table
        self.table = EnterpriseTable(config["columns"], density="compact")
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}pt;")
        self.summary_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.summary_label)

    def _on_type_changed(self, idx):
        key = self.type_selector.currentData()
        if key and key in REPORT_TYPES:
            self.report_type = key
            config = REPORT_TYPES[key]
            self._is_date_range = self.report_type in self.DATE_RANGE_REPORTS
            self._rebuild_toolbar()
            self._rebuild_table(config)

    def _rebuild_toolbar(self):
        toolbar = self.findChild(QGroupBox, "Parameters")
        if not toolbar:
            return
        bar_layout = toolbar.layout()
        while bar_layout.count() > 0:
            item = bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.type_selector = QComboBox()
        groups = [
            ("-- Accounting Reports --", ["trial_balance", "profit_loss", "balance_sheet", "cash_flow", "ar_aging", "ap_aging"]),
            ("-- HR Reports --", ["employee_summary", "attendance_report", "leave_report", "overtime_report"]),
            ("-- Payroll Reports --", ["payroll_summary", "payroll_trend", "payroll_dept_cost", "payroll_emp_history"]),
        ]
        for group_label, keys in groups:
            self.type_selector.addItem(group_label, None)
            for k in keys:
                self.type_selector.addItem(REPORT_TYPES[k]["title"], k)
            idx = self.type_selector.findData(self.report_type)
        if idx >= 0:
            self.type_selector.setCurrentIndex(idx)
        connect_unique(self.type_selector.currentIndexChanged, self._on_type_changed)
        bar_layout.addWidget(QLabel("Report:"))
        bar_layout.addWidget(self.type_selector)

        if self._is_date_range:
            bar_layout.addWidget(QLabel("From:"))
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDisplayFormat("yyyy-MM-dd")
            self.date_from.setDate(QDate.currentDate().addMonths(-1))
            bar_layout.addWidget(self.date_from)

            bar_layout.addWidget(QLabel("To:"))
            self.date_to = QDateEdit()
            self.date_to.setCalendarPopup(True)
            self.date_to.setDisplayFormat("yyyy-MM-dd")
            self.date_to.setDate(QDate.currentDate())
            bar_layout.addWidget(self.date_to)
        else:
            bar_layout.addWidget(QLabel("Date:"))
            self.date_input = QDateEdit()
            self.date_input.setCalendarPopup(True)
            self.date_input.setDisplayFormat("yyyy-MM-dd")
            self.date_input.setDate(QDate.currentDate())
            bar_layout.addWidget(self.date_input)

        bar_layout.addStretch()

        self.btn_run = EnterpriseButton(text="Run Report", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        connect_unique(self.btn_run.clicked, self.run_report)
        bar_layout.addWidget(self.btn_run)

        self.btn_export = EnterpriseButton(text="Export CSV", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        connect_unique(self.btn_export.clicked, self._export_csv)
        bar_layout.addWidget(self.btn_export)

    def _rebuild_table(self, config):
        old = self.table
        self.table = EnterpriseTable(config["columns"], density="compact")
        widget_idx = self.layout().indexOf(old)
        self.layout().insertWidget(widget_idx, self.table)
        old.deleteLater()
        self.report_data = {}
        self.summary_label.setText("")

    def run_report(self):
        config = REPORT_TYPES.get(self.report_type)
        if not config:
            return
        
        self._set_loading(True)
        
        params = {}
        if self._is_date_range:
            if hasattr(self, 'date_from') and self.date_from.date() != QDate():
                params["start_date"] = self.date_from.date().toString("yyyy-MM-dd")
            if hasattr(self, 'date_to') and self.date_to.date() != QDate():
                params["end_date"] = self.date_to.date().toString("yyyy-MM-dd")
        else:
            if hasattr(self, 'date_input') and self.date_input.date() != QDate():
                params["as_of_date"] = self.date_input.date().toString("yyyy-MM-dd")
        
        started = self.run_api_request(
            "run_report",
            "GET",
            config["api"],
            params=params,
            on_success=lambda resp, cfg=config: self._on_report_finished(resp, cfg),
            on_error=self._on_report_error,
        )
        if not started:
            self._set_loading(False)

    def _on_report_finished(self, resp, config):
        self.report_data = resp.get("data", resp) if isinstance(resp, dict) else resp
        self._populate_table(config)
        self._set_loading(False)

    def _on_report_error(self, err_msg):
        self._set_loading(False)
        self._set_empty(f"Error: {err_msg}")

    def _populate_table(self, config):
        data = self.report_data
        items = self._extract_items(data, config)

        if not isinstance(items, list):
            items = []

        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            row = {}
            for col in config["columns"]:
                val = item.get(col.key, "")
                row[col.key] = str(val) if not isinstance(val, str) else val
            rows.append(row)
        self.table.set_data(rows)
        self.summary_label.setText(f"Total rows: {len(rows)}")

    def _extract_items(self, data, config):
        """Extract the correct list of items from the API response based on report type."""
        if not isinstance(data, dict):
            return data if isinstance(data, list) else []

        if self.report_type == "balance_sheet":
            return self._extract_balance_sheet_items(data)
        elif self.report_type == "profit_loss":
            return self._extract_profit_loss_items(data)
        elif self.report_type == "cash_flow":
            return self._extract_cash_flow_items(data)
        elif self.report_type in ("ar_aging", "ap_aging"):
            return data.get("aging_rows", [])
        elif config["data_key"]:
            return data.get(config["data_key"], [])
        else:
            return [data]

    def _extract_balance_sheet_items(self, data):
        """Convert balance sheet nested structure to flat rows."""
        rows = []
        for section_key in ("assets", "liabilities", "equity"):
            section_data = data.get(section_key, {})
            rows.append({
                "account_code": "",
                "account_name": section_key.upper(),
                "account_type": "",
                "balance": "",
            })
            for section in section_data.get("sections", []):
                rows.append({
                    "account_code": "",
                    "account_name": f"  {section.get('category', '')}",
                    "account_type": "",
                    "balance": str(section.get('total', 0)),
                })
                for acc in section.get("accounts", []):
                    rows.append({
                        "account_code": acc.get("account_code", ""),
                        "account_name": f"    {acc.get('account_name', '')}",
                        "account_type": acc.get("category", ""),
                        "balance": str(acc.get('amount', 0)),
                    })
            rows.append({
                "account_code": "",
                "account_name": f"Total {section_key.title()}",
                "account_type": "",
                "balance": str(section_data.get('total', 0)),
            })
            rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

        is_balanced = data.get("is_balanced", False)
        diff = data.get("difference", 0)
        rows.append({
            "account_code": "",
            "account_name": "BALANCED" if is_balanced else f"NOT BALANCED (diff: {diff})",
            "account_type": "",
            "balance": "",
        })
        return rows

    def _extract_profit_loss_items(self, data):
        """Convert P&L nested structure to flat rows."""
        rows = []
        rows.append({"account_code": "", "account_name": "REVENUE", "account_type": "", "balance": ""})
        for section in data.get("revenue", []):
            if isinstance(section, dict) and "accounts" in section:
                rows.append({
                    "account_code": "",
                    "account_name": f"  {section.get('category', '')}",
                    "account_type": "",
                    "balance": str(section.get('total', 0)),
                })
                for acc in section.get("accounts", []):
                    rows.append({
                        "account_code": acc.get("account_code", ""),
                        "account_name": f"    {acc.get('account_name', '')}",
                        "account_type": acc.get("category", ""),
                        "balance": str(acc.get('amount', 0)),
                    })
        rows.append({"account_code": "", "account_name": "Total Revenue", "account_type": "", "balance": str(data.get('total_revenue', 0))})
        rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

        rows.append({"account_code": "", "account_name": "COST OF GOODS SOLD", "account_type": "", "balance": ""})
        for section in data.get("cogs", []):
            if isinstance(section, dict) and "accounts" in section:
                for acc in section.get("accounts", []):
                    rows.append({
                        "account_code": acc.get("account_code", ""),
                        "account_name": f"    {acc.get('account_name', '')}",
                        "account_type": acc.get("category", ""),
                        "balance": str(acc.get('amount', 0)),
                    })
        rows.append({"account_code": "", "account_name": "Total COGS", "account_type": "", "balance": str(data.get('total_cogs', 0))})
        rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

        rows.append({"account_code": "", "account_name": "GROSS PROFIT", "account_type": "", "balance": str(data.get('gross_profit', 0))})
        rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

        rows.append({"account_code": "", "account_name": "EXPENSES", "account_type": "", "balance": ""})
        for section in data.get("expenses", []):
            if isinstance(section, dict) and "accounts" in section:
                rows.append({
                    "account_code": "",
                    "account_name": f"  {section.get('category', '')}",
                    "account_type": "",
                    "balance": str(section.get('total', 0)),
                })
                for acc in section.get("accounts", []):
                    rows.append({
                        "account_code": acc.get("account_code", ""),
                        "account_name": f"    {acc.get('account_name', '')}",
                        "account_type": acc.get("category", ""),
                        "balance": str(acc.get('amount', 0)),
                    })
        rows.append({"account_code": "", "account_name": "Total Expenses", "account_type": "", "balance": str(data.get('total_expenses', 0))})
        rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

        rows.append({"account_code": "", "account_name": "NET INCOME", "account_type": "", "balance": str(data.get('net_income', 0))})
        return rows

    def _extract_cash_flow_items(self, data):
        """Convert cash flow nested structure to flat rows."""
        rows = []
        operating = data.get("operating_activities", {})
        rows.append({"category": "Operating Activities", "amount": ""})
        rows.append({"category": "  Net Income", "amount": str(operating.get('net_income', 0))})
        for wc in operating.get("working_capital_changes", []):
            rows.append({"category": f"  {wc.get('description', '')}", "amount": str(wc.get('change', 0))})
        rows.append({"category": "  Net Cash from Operations", "amount": str(operating.get('net_cash_from_operations', 0))})
        rows.append({"category": "", "amount": ""})

        investing = data.get("investing_activities", {})
        rows.append({"category": "Investing Activities", "amount": ""})
        for item in investing.get("items", []):
            rows.append({"category": f"  {item.get('description', '')}", "amount": str(item.get('change', 0))})
        rows.append({"category": "  Net Cash from Investing", "amount": str(investing.get('net_cash_from_investing', 0))})
        rows.append({"category": "", "amount": ""})

        financing = data.get("financing_activities", {})
        rows.append({"category": "Financing Activities", "amount": ""})
        for item in financing.get("items", []):
            rows.append({"category": f"  {item.get('description', '')}", "amount": str(item.get('change', 0))})
        rows.append({"category": "  Net Cash from Financing", "amount": str(financing.get('net_cash_from_financing', 0))})
        rows.append({"category": "", "amount": ""})

        rows.append({"category": "NET CHANGE IN CASH", "amount": str(data.get('net_change_in_cash', 0))})
        rows.append({"category": "Opening Cash Balance", "amount": str(data.get('opening_cash_balance', 0))})
        rows.append({"category": "Closing Cash Balance", "amount": str(data.get('closing_cash_balance', 0))})
        return rows

    def _set_loading(self, show):
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.btn_run.setEnabled(not show)

    def _set_empty(self, msg):
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(msg)
        self.empty_label.setVisible(True)
        self.btn_run.setEnabled(True)

    def _export_csv(self):
        if not self.report_data:
            AlertDialog.warning(self, "Warning", "Run the report first.")
            return
        config = REPORT_TYPES.get(self.report_type)
        if not config:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export {config['title']}",
            f"{config['title'].replace(' ', '_')}.csv",
            "CSV Files (*.csv)",
        )
        if file_path:
            try:
                if self._is_date_range:
                    params = {"format": "csv"}
                    if hasattr(self, 'date_from') and self.date_from.date() != QDate():
                        params["start_date"] = self.date_from.date().toString("yyyy-MM-dd")
                    if hasattr(self, 'date_to') and self.date_to.date() != QDate():
                        params["end_date"] = self.date_to.date().toString("yyyy-MM-dd")
                else:
                    params = {"format": "csv"}
                    if hasattr(self, 'date_input') and self.date_input.date() != QDate():
                        params["as_of_date"] = self.date_input.date().toString("yyyy-MM-dd")
                resp = self.api_client.get(config["api"], params=params)
                with open(file_path, "w", encoding="utf-8") as f:
                    content = resp if isinstance(resp, str) else str(resp)
                    f.write(content)
                AlertDialog.info(self, "Success", f"Exported to {file_path}")
            except Exception as e:
                AlertDialog.error(self, "Error", f"Export failed: {e}")

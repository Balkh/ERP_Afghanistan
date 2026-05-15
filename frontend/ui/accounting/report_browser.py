"""
Consolidated Report Browser — replaces 13 individual report screens.
Supports Accounting, HR, and Payroll report types via configuration.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                                QDateEdit, QGroupBox, QMessageBox, QFileDialog,
                                QApplication)
from PySide6.QtCore import Qt, QDate
from datetime import date
from api.client import APIClient
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_HELPER,
                           BORDER_RADIUS_MD, BORDER_RADIUS_LG,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BORDER, COLOR_BORDER_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


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


class ReportBrowser(QWidget):
    """Consolidated report browser — handles all accounting/HR/payroll reports."""

    def __init__(self, parent=None, report_type="trial_balance"):
        super().__init__(parent)
        self.api_client = APIClient()
        self.report_type = report_type
        self.report_data = {}
        self._build_ui()

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
                margin-top: 10px; padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
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
        self.type_selector.currentIndexChanged.connect(self._on_type_changed)
        bar_layout.addWidget(QLabel("Report:"))
        bar_layout.addWidget(self.type_selector)

        bar_layout.addWidget(QLabel("Date:"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(date.today())
        bar_layout.addWidget(self.date_input)

        bar_layout.addStretch()

        self.btn_run = EnterpriseButton(text="Run Report", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_run.clicked.connect(self.run_report)
        bar_layout.addWidget(self.btn_run)

        self.btn_export = EnterpriseButton(text="Export CSV", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_export.clicked.connect(self._export_csv)
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
            header = self.parent() or self
            self._rebuild_table(config)

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
        try:
            params = {}
            if self.date_input.date() != QDate():
                params["as_of_date"] = self.date_input.date().toString("yyyy-MM-dd")
            resp = self.api_client.get(config["api"], params=params)
            self.report_data = resp.get("data", resp) if isinstance(resp, dict) else resp
            self._populate_table(config)
            self._set_loading(False)
        except Exception as e:
            self._set_empty(f"Error: {e}")

    def _populate_table(self, config):
        data = self.report_data
        if isinstance(data, dict):
            if config["data_key"]:
                items = data.get(config["data_key"], [])
            else:
                items = [data]
        elif isinstance(data, list):
            items = data
        else:
            items = []

        # Convert flat dicts to row lists
        if not isinstance(items, list):
            items = [items]

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

    def _set_loading(self, show):
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.btn_run.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _set_empty(self, msg):
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(msg)
        self.empty_label.setVisible(True)
        self.btn_run.setEnabled(True)

    def _export_csv(self):
        if not self.report_data:
            QMessageBox.warning(self, "Warning", "Run the report first.")
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
                params = {"format": "csv", "as_of_date": self.date_input.date().toString("yyyy-MM-dd")}
                resp = self.api_client.get(config["api"], params=params)
                with open(file_path, "w", encoding="utf-8") as f:
                    content = resp if isinstance(resp, str) else str(resp)
                    f.write(content)
                QMessageBox.information(self, "Success", f"Exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")

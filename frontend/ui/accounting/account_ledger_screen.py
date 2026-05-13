from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QPushButton, QComboBox, QLineEdit, QDateEdit,
                               QMessageBox, QGroupBox, QFormLayout, QDialog, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


class AccountLedgerScreen(QFrame):
    """Account Ledger screen with date range and running balance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.accounts = []
        self._is_loading = False
        self.setup_ui()
        self.load_accounts()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        header = QLabel("Account Ledger")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
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
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.date_to)

        filter_layout.addStretch()

        self.btn_load = QPushButton("Load Ledger")
        self.btn_load.setMinimumHeight(32)
        self.btn_load.clicked.connect(self.load_ledger)
        filter_layout.addWidget(self.btn_load)

        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.setMinimumHeight(32)
        self.btn_export_csv.clicked.connect(self.export_csv)
        filter_layout.addWidget(self.btn_export_csv)

        self.btn_print = QPushButton("Print Preview")
        self.btn_print.setMinimumHeight(32)
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
            label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            info_layout.addWidget(label)
        info_layout.addStretch()
        info_layout.addWidget(self.info_opening)
        info_layout.addWidget(self.info_closing)

        layout.addWidget(info_group)

        self.loading_label = QLabel("Loading ledger...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: 20px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("Select an account and click Load Ledger")
        self.empty_label.setFont(QFont("Segoe UI", 11))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: 20px;")
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
        QApplication.processEvents()

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

    def _safe_float(self, value, default=0.0):
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def _create_table(self):
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Entry #", "Date", "Type", "Description", "Debit", "Credit", "Running Balance"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                background-color: {COLOR_BG_SURFACE};
                gridline-color: {COLOR_TABLE_BORDER_LIGHT};
            }}
            QHeaderView::section {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                padding: 8px;
                font-weight: bold;
                border: none;
            }}
        """)

        return table

    def load_accounts(self):
        try:
            endpoint = get_endpoint("leaf_accounts")
            response = self.api_client.get(endpoint)
            self.accounts = [a for a in extract_list(response) if isinstance(a, dict)]
            self.account_combo.clear()
            self.account_combo.addItem("Select an account...", None)
            for acc in sorted(self.accounts, key=lambda x: x.get("code") or ""):
                code = acc.get("code") or ""
                name = acc.get("name") or "Unknown"
                acc_id = acc.get("id")
                if acc_id:
                    self.account_combo.addItem(f"{code} - {name}", acc_id)
        except Exception as e:
            print(f"Error loading accounts: {e}")
            self.accounts = []

    def load_ledger(self):
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "Warning", "Please select an account.")
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

        opening = self._safe_float(data.get("opening_balance"))
        closing = self._safe_float(data.get("closing_balance"))
        self.info_opening.setText(f"Opening: {opening:,.2f}")
        self.info_closing.setText(f"Closing: {closing:,.2f}")

        entries = data.get("entries", [])
        if not entries:
            self._show_empty("No ledger entries for selected period")
            return

        if not isinstance(entries, list):
            entries = []

        self._show_data()
        self.table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            self.table.setItem(row, 0, QTableWidgetItem(entry.get("entry_number") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("entry_date") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(entry.get("entry_type") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(entry.get("description") or ""))

            debit = self._safe_float(entry.get("debit"))
            credit = self._safe_float(entry.get("credit"))
            balance = self._safe_float(entry.get("running_balance"))

            debit_item = QTableWidgetItem(f"{debit:,.2f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if debit > 0:
                debit_item.setForeground(QColor(COLOR_SUCCESS))
            self.table.setItem(row, 4, debit_item)

            credit_item = QTableWidgetItem(f"{credit:,.2f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if credit > 0:
                credit_item.setForeground(QColor(COLOR_DANGER))
            self.table.setItem(row, 5, credit_item)

            balance_item = QTableWidgetItem(f"{balance:,.2f}")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if balance < 0:
                balance_item.setForeground(QColor(COLOR_DANGER))
            self.table.setItem(row, 6, balance_item)

    def export_csv(self):
        if not hasattr(self, 'ledger_data') or not self.ledger_data:
            QMessageBox.warning(self, "Warning", "Load the ledger first.")
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
                QMessageBox.information(self, "Success", f"Ledger exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def print_preview(self):
        if not hasattr(self, 'ledger_data') or not self.ledger_data:
            QMessageBox.warning(self, "Warning", "Load the ledger first.")
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
            dialog = ReportPreviewDialog(self, f"Ledger - {self.ledger_data.get('account_name')}", text_data)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate preview: {e}")

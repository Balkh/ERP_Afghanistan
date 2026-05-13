from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                                QTableWidgetItem, QHeaderView, QAbstractItemView,
                                QPushButton, QComboBox, QDateEdit, QGroupBox,
                                QScrollArea, QMessageBox, QFileDialog, QMenu,
                                QApplication)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from api.client import APIClient
from datetime import date
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


class BaseReportScreen(QFrame):
    """Base class for financial report screens."""

    def __init__(self, report_title="", parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.report_title = report_title
        self.report_data = {}
        self._is_loading = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        header = QLabel(self.report_title)
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(header)

        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        self.loading_label = QLabel("Loading...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: 20px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No data available. Run the report to generate data.")
        self.empty_label.setFont(QFont("Segoe UI", 11))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: 20px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.table = self._create_table()
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.summary_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.summary_label)

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self._is_loading = show
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.btn_run.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_empty(self, message="No data available. Run the report to generate data."):
        """Show empty state."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.btn_run.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.table.setVisible(True)
        self.btn_run.setEnabled(True)

    def _safe_float(self, value, default=0.0):
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def _create_toolbar(self):
        toolbar = QGroupBox("Parameters")
        toolbar.setObjectName("Parameters")
        layout = QHBoxLayout(toolbar)

        layout.addWidget(QLabel("As of:"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(date.today())
        layout.addWidget(self.date_input)

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

        return toolbar

    def _create_table(self):
        table = QTableWidget()
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    def run_report(self):
        raise NotImplementedError

    def export_csv(self):
        if not self.report_data:
            QMessageBox.warning(self, "Warning", "Run the report first.")
            return
        self._do_export("csv", "CSV Files (*.csv)")

    def export_excel(self):
        if not self.report_data:
            QMessageBox.warning(self, "Warning", "Run the report first.")
            return
        self._do_export("excel", "Excel Files (*.xlsx)")

    def export_pdf(self):
        if not self.report_data:
            QMessageBox.warning(self, "Warning", "Run the report first.")
            return
        self._do_export("pdf", "PDF Files (*.pdf)")

    def export_json(self):
        if not self.report_data:
            QMessageBox.warning(self, "Warning", "Run the report first.")
            return
        self._do_export("json", "JSON Files (*.json)")

    def _do_export(self, fmt: str, file_filter: str):
        ext_map = {"csv": "csv", "excel": "xlsx", "pdf": "pdf", "json": "json"}
        ext = ext_map.get(fmt, fmt)
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export as {fmt.upper()}",
            f"{self.report_title.replace(' ', '_')}.{ext}", file_filter,
        )
        if file_path:
            try:
                params = self._get_report_params()
                params["format"] = fmt
                resp = self.api_client.get(self.report_api_endpoint, params=params)
                if fmt in ("excel", "pdf"):
                    if hasattr(resp, 'content'):
                        with open(file_path, "wb") as f:
                            f.write(resp.content)
                    else:
                        QMessageBox.critical(self, "Error", "Binary export not available from this endpoint. Use CSV instead.")
                        return
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        content = resp if isinstance(resp, str) else str(resp)
                        f.write(content)
                QMessageBox.information(self, "Success", f"Exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def print_preview(self):
        if not self.report_data:
            QMessageBox.warning(self, "Warning", "Run the report first.")
            return

        try:
            params = self._get_report_params()
            params["format"] = "text"
            text_data = self.api_client.get(self.report_api_endpoint, params=params)

            from ui.accounting.components.report_preview_dialog import ReportPreviewDialog
            dialog = ReportPreviewDialog(self, self.report_title, text_data)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate preview: {e}")

    def _get_report_params(self):
        from PySide6.QtCore import QDate
        params = {}
        if self.date_input.date() != QDate():
            params["as_of_date"] = self.date_input.date().toString("yyyy-MM-dd")
        return params

    def _item(self, text):
        return QTableWidgetItem(str(text))

    def _bold_item(self, text):
        item = QTableWidgetItem(str(text))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        return item

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QGroupBox, QFrame, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, BORDER_RADIUS_SM, BORDER_RADIUS_LG)
from ui.constants import (TEXT_LABEL, TEXT_BODY, TEXT_SECTION_TITLE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT)
from ui.rendering.button_renderer import ButtonRenderer, ButtonStyle
from ui.rendering.table_renderer import TableRenderer


class JournalEntryDetailDialog(QDialog):
    """Dialog to view a journal entry detail with its lines."""

    def __init__(self, parent=None, entry_data=None, api_client=None):
        super().__init__(parent)
        self.setWindowTitle("Entry Details")
        self.api_client = api_client
        self.entry_data = entry_data or {}
        self.lines = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setMinimumWidth(850)
        self.setMinimumHeight(600)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLOR_BG_MAIN}; }}
            QGroupBox {{ 
                font-weight: bold; 
                border: 1px solid {COLOR_BORDER}; 
                border-radius: {BORDER_RADIUS_LG}; 
                margin-top: 15px;
                padding-top: 15px;
                background-color: {COLOR_BG_SURFACE};
            }}
            QLabel {{ color: {COLOR_TEXT_PRIMARY}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        title = QLabel("Journal Entry Details")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        # Entry Information
        info_group = QGroupBox("General Information")
        info_layout = QFormLayout(info_group)
        info_layout.setLabelAlignment(Qt.AlignRight)
        info_layout.setSpacing(SPACING_SM + SPACING_XS)

        self.entry_number = QLabel("")
        self.entry_number.setStyleSheet(f"font-weight: bold; color: {COLOR_PRIMARY};")
        info_layout.addRow("Entry #:", self.entry_number)

        self.entry_date = QLabel("")
        info_layout.addRow("Date:", self.entry_date)

        self.entry_type = QLabel("")
        info_layout.addRow("Type:", self.entry_type)

        self.description = QLabel("")
        self.description.setWordWrap(True)
        info_layout.addRow("Description:", self.description)

        self.reference = QLabel("")
        info_layout.addRow("Reference:", self.reference)

        self.is_posted = QLabel("")
        status_font = QFont("Segoe UI", TEXT_LABEL)
        status_font.setWeight(QFont.Weight.Bold)
        self.is_posted.setFont(status_font)
        info_layout.addRow("Status:", self.is_posted)

        layout.addWidget(info_group)

        # Journal Lines
        lines_group = QGroupBox("Journal Lines (Articles)")
        lines_layout = QVBoxLayout(lines_group)

        self.lines_table = QTableWidget()
        self.lines_table.setColumnCount(4)
        self.lines_table.setHorizontalHeaderLabels(["Account", "Line Description", "Debit", "Credit"])
        
        header = self.lines_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        TableRenderer.style(self.lines_table)
        lines_layout.addWidget(self.lines_table)

        # Totals
        totals_frame = QFrame()
        totals_frame.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_XS}px;")
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.addStretch()
        
        totals_layout.addWidget(QLabel("Total Debit:"))
        self.total_debit_label = QLabel("0.00")
        debit_font = QFont("Segoe UI", TEXT_BODY)
        debit_font.setWeight(QFont.Weight.Bold)
        self.total_debit_label.setFont(debit_font)
        self.total_debit_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
        totals_layout.addWidget(self.total_debit_label)
        
        totals_layout.addSpacing(20)
        
        totals_layout.addWidget(QLabel("Total Credit:"))
        self.total_credit_label = QLabel("0.00")
        credit_font = QFont("Segoe UI", TEXT_BODY)
        credit_font.setWeight(QFont.Weight.Bold)
        self.total_credit_label.setFont(credit_font)
        self.total_credit_label.setStyleSheet(f"color: {COLOR_DANGER};")
        totals_layout.addWidget(self.total_credit_label)
        
        lines_layout.addLayout(totals_layout)
        layout.addWidget(lines_group)

        # Footer Actions
        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton("Close")
        ButtonRenderer.style(close_btn, ButtonStyle.PRIMARY, "sm")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def load_data(self):
        self.entry_number.setText(self.entry_data.get("entry_number", ""))
        self.entry_date.setText(self.entry_data.get("entry_date", ""))
        self.entry_type.setText(self.entry_data.get("entry_type", ""))
        self.description.setText(self.entry_data.get("description", ""))
        self.reference.setText(self.entry_data.get("reference", ""))

        posted = self.entry_data.get("is_posted", False)
        self.is_posted.setText("Posted" if posted else "Draft")
        if posted:
            self.is_posted.setStyleSheet(f"color: {COLOR_SUCCESS};")
        else:
            self.is_posted.setStyleSheet(f"color: {COLOR_WARNING};")

        self._load_lines()

    def _load_lines(self):
        entry_id = self.entry_data.get("id")
        if not entry_id or not self.api_client:
            return

        try:
            self.lines = self.api_client.get(f"/api/accounting/journal-entries/{entry_id}/")
            lines_data = self.lines.get("lines", []) if isinstance(self.lines, dict) else []

            self.lines_table.setRowCount(len(lines_data))
            total_debit = 0.0
            total_credit = 0.0

            for row, line in enumerate(lines_data):
                account = line.get("account", {})
                account_str = f"{account.get('code', '')} - {account.get('name', '')}"
                self.lines_table.setItem(row, 0, QTableWidgetItem(account_str))
                self.lines_table.setItem(row, 1, QTableWidgetItem(line.get("description", "")))

                debit = float(line.get("debit", 0))
                credit = float(line.get("credit", 0))
                total_debit += debit
                total_credit += credit

                debit_item = QTableWidgetItem(f"{debit:,.2f}")
                debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                debit_item.setForeground(QColor(COLOR_SUCCESS))
                self.lines_table.setItem(row, 2, debit_item)

                credit_item = QTableWidgetItem(f"{credit:,.2f}")
                credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                credit_item.setForeground(QColor(COLOR_DANGER))
                self.lines_table.setItem(row, 3, credit_item)

            self.total_debit_label.setText(f"{total_debit:,.2f}")
            self.total_credit_label.setText(f"{total_credit:,.2f}")

        except Exception as e:
            print(f"Error loading journal lines: {e}")

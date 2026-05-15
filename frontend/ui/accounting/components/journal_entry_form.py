from decimal import Decimal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QComboBox, QTextEdit, QPushButton,
                               QLabel, QMessageBox, QDateEdit, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QGroupBox, QDoubleSpinBox, QCheckBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.client import APIClient
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_WARNING,
    COLOR_DANGER, COLOR_INFO, COLOR_BG_MAIN, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_BORDER_LIGHT_THEME, COLOR_TEXT_ON_PRIMARY, BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG, TEXT_SECTION_TITLE, TEXT_CARD_TITLE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BG_LIGHT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_SUCCESS_BG, COLOR_WARNING, COLOR_DANGER, COLOR_DANGER_BG, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.rendering.button_renderer import ButtonRenderer, ButtonStyle
from ui.rendering.table_renderer import TableRenderer


class JournalEntryFormDialog(QDialog):
    """Dialog for creating a new journal entry with line items."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Journal Entry")
        self.api_client = api_client or APIClient()
        self.accounts = []
        self.line_items = []
        self.setup_ui()
        self.load_accounts()

    def setup_ui(self):
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLOR_BG_LIGHT}; }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                margin-top: {SPACING_LG};
                padding-top: {SPACING_LG};
                background-color: {COLOR_BG_MAIN};
            }}
            QLabel {{ color: {COLOR_TEXT_PRIMARY}; }}
            QLineEdit, QComboBox, QTextEdit, QDateEdit, QDoubleSpinBox {{
                background-color: {COLOR_BG_INPUT};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM};
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        title = QLabel("Create Journal Entry")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        # Header Information
        header_group = QGroupBox("General Information")
        header_layout = QFormLayout(header_group)
        header_layout.setLabelAlignment(Qt.AlignRight)
        header_layout.setSpacing(SPACING_MD + SPACING_XS)

        self.entry_type = QComboBox()
        self.entry_type.setMinimumHeight(30)
        for t in ["SALE", "PURCHASE", "PAYMENT", "RECEIPT", "ADJUSTMENT", "TRANSFER", "OPENING", "CLOSING"]:
            self.entry_type.addItem(t, t)
        header_layout.addRow("Entry Type:", self.entry_type)

        self.entry_date = QDateEdit()
        self.entry_date.setMinimumHeight(30)
        self.entry_date.setCalendarPopup(True)
        self.entry_date.setDisplayFormat("yyyy-MM-dd")
        from datetime import date
        self.entry_date.setDate(date.today())
        header_layout.addRow("Entry Date:", self.entry_date)

        self.description = QTextEdit()
        self.description.setMaximumHeight(80)
        self.description.setPlaceholderText("Enter overall entry description...")
        header_layout.addRow("Description:", self.description)

        self.reference = QLineEdit()
        self.reference.setMinimumHeight(30)
        self.reference.setPlaceholderText("Reference number (optional)")
        header_layout.addRow("Reference:", self.reference)

        self.auto_post = QCheckBox("Auto-post after creation")
        self.auto_post.setStyleSheet("margin-left: 5px;")
        header_layout.addRow("", self.auto_post)

        layout.addWidget(header_group)

        # Journal Lines
        lines_group = QGroupBox("Journal Lines (Articles)")
        lines_layout = QVBoxLayout(lines_group)

        self.lines_table = QTableWidget()
        self.lines_table.setColumnCount(5)
        self.lines_table.setHorizontalHeaderLabels(["Account", "Line Description", "Debit", "Credit", ""])
        TableRenderer.style(self.lines_table)
        self.lines_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.lines_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.lines_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.lines_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.lines_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.lines_table.setColumnWidth(4, 40)
        lines_layout.addWidget(self.lines_table)

        line_buttons = QHBoxLayout()
        self.btn_add_line = QPushButton("+ Add Line")
        ButtonRenderer.style(self.btn_add_line, ButtonStyle.PRIMARY, "sm")
        self.btn_remove_line = QPushButton("- Remove Selected Lines")
        ButtonRenderer.style(self.btn_remove_line, ButtonStyle.GHOST, "sm")
        line_buttons.addWidget(self.btn_add_line)
        line_buttons.addWidget(self.btn_remove_line)
        line_buttons.addStretch()
        lines_layout.addLayout(line_buttons)

        layout.addWidget(lines_group)

        # Totals and Balance
        bottom_layout = QHBoxLayout()
        
        totals_frame = QFrame()
        totals_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG};")
        totals_layout = QHBoxLayout(totals_frame)
        
        totals_layout.addWidget(QLabel("Total Debit:"))
        self.total_debit_label = QLabel("0.00")
        debit_font = QFont("Segoe UI", TEXT_CARD_TITLE)
        debit_font.setWeight(QFont.Weight.Bold)
        self.total_debit_label.setFont(debit_font)
        self.total_debit_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
        totals_layout.addWidget(self.total_debit_label)

        totals_layout.addSpacing(20)

        totals_layout.addWidget(QLabel("Total Credit:"))
        self.total_credit_label = QLabel("0.00")
        credit_font = QFont("Segoe UI", TEXT_CARD_TITLE)
        credit_font.setWeight(QFont.Weight.Bold)
        self.total_credit_label.setFont(credit_font)
        self.total_credit_label.setStyleSheet(f"color: {COLOR_DANGER};")
        totals_layout.addWidget(self.total_credit_label)

        totals_layout.addSpacing(30)

        self.balance_label = QLabel("BALANCED")
        balance_font = QFont("Segoe UI", TEXT_CARD_TITLE)
        balance_font.setWeight(QFont.Weight.Bold)
        self.balance_label.setFont(balance_font)
        self.balance_label.setStyleSheet(f"color: {COLOR_SUCCESS}; padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; background-color: {COLOR_SUCCESS_BG};")
        totals_layout.addWidget(self.balance_label)
        
        bottom_layout.addWidget(totals_frame)
        layout.addLayout(bottom_layout)

        # Actions
        action_buttons = QHBoxLayout()
        action_buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        ButtonRenderer.style(cancel_btn, ButtonStyle.GHOST)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Entry")
        ButtonRenderer.style(save_btn, ButtonStyle.SUCCESS)
        save_btn.setMinimumWidth(150)
        save_btn.clicked.connect(self.save)

        action_buttons.addWidget(cancel_btn)
        action_buttons.addWidget(save_btn)

        layout.addLayout(action_buttons)

        self.btn_add_line.clicked.connect(self._add_line)
        self.btn_remove_line.clicked.connect(self._remove_line)

        # Start with 2 lines
        self._add_line()
        self._add_line()

    def load_accounts(self):
        try:
            self.accounts = self.api_client.get("/api/accounting/accounts/leaf_accounts/")
            # Refresh all existing account combos
            for row in range(self.lines_table.rowCount()):
                combo = self.lines_table.cellWidget(row, 0)
                if isinstance(combo, QComboBox):
                    current_idx = combo.currentIndex()
                    combo.clear()
                    combo.addItem("Select Account...", None)
                    for acc in sorted(self.accounts, key=lambda x: x.get("code", "")):
                        combo.addItem(f"{acc['code']} - {acc['name']}", acc["id"])
                    combo.setCurrentIndex(current_idx)
        except Exception:
            self.accounts = []

    def _add_line(self):
        row = self.lines_table.rowCount()
        self.lines_table.insertRow(row)
        self.lines_table.setRowHeight(row, 45)

        account_combo = QComboBox()
        account_combo.addItem("Select Account...", None)
        for acc in sorted(self.accounts, key=lambda x: x.get("code", "")):
            account_combo.addItem(f"{acc['code']} - {acc['name']}", acc["id"])
        self.lines_table.setCellWidget(row, 0, account_combo)

        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Line description")
        self.lines_table.setCellWidget(row, 1, desc_input)

        debit_spin = QDoubleSpinBox()
        debit_spin.setMaximum(999999999.99)
        debit_spin.setDecimals(2)
        debit_spin.setButtonSymbols(QAbstractItemView.NoButtons)
        debit_spin.setAlignment(Qt.AlignRight)
        debit_spin.valueChanged.connect(self._update_totals)
        self.lines_table.setCellWidget(row, 2, debit_spin)

        credit_spin = QDoubleSpinBox()
        credit_spin.setMaximum(999999999.99)
        credit_spin.setDecimals(2)
        credit_spin.setButtonSymbols(QAbstractItemView.NoButtons)
        credit_spin.setAlignment(Qt.AlignRight)
        credit_spin.valueChanged.connect(self._update_totals)
        self.lines_table.setCellWidget(row, 3, credit_spin)

        remove_btn = QPushButton("✕")
        remove_btn.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold; border: none; background: transparent;")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda checked, r=row: self._remove_line_at(r))
        self.lines_table.setCellWidget(row, 4, remove_btn)

    def _remove_line(self):
        selected = self.lines_table.selectionModel().selectedRows()
        if selected:
            for idx in sorted([r.row() for r in selected], reverse=True):
                self.lines_table.removeRow(idx)
            self._update_totals()

    def _remove_line_at(self, row):
        # Need to find the actual row index because rows might have shifted
        # A better way is to find which row the button belongs to
        button = self.sender()
        if button:
            index = self.lines_table.indexAt(button.pos())
            if index.isValid():
                self.lines_table.removeRow(index.row())
                self._update_totals()

    def _update_totals(self):
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for row in range(self.lines_table.rowCount()):
            debit_widget = self.lines_table.cellWidget(row, 2)
            credit_widget = self.lines_table.cellWidget(row, 3)
            if debit_widget:
                total_debit += Decimal(str(debit_widget.value()))
            if credit_widget:
                total_credit += Decimal(str(credit_widget.value()))

        self.total_debit_label.setText(f"{total_debit:,.2f}")
        self.total_credit_label.setText(f"{total_credit:,.2f}")

        if total_debit == total_credit and total_debit > 0:
            self.balance_label.setText("BALANCED")
            self.balance_label.setStyleSheet(f"color: {COLOR_SUCCESS}; padding: {SPACING_XS}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}; background-color: {COLOR_SUCCESS_BG};")
        elif total_debit == 0 and total_credit == 0:
            self.balance_label.setText("EMPTY")
            self.balance_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: {SPACING_XS}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}; background-color: {COLOR_BG_LIGHT};")
        else:
            diff = abs(total_debit - total_credit)
            self.balance_label.setText(f"UNBALANCED ({diff:,.2f})")
            self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; padding: {SPACING_XS}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}; background-color: {COLOR_DANGER_BG};")

    def save(self):
        data = self.get_entry_data()

        if not data["description"]:
            QMessageBox.warning(self, "Validation Error", "Description is required.")
            return
        if len(data["lines"]) < 2:
            QMessageBox.warning(self, "Validation Error", "At least 2 lines are required for the entry.")
            return

        # Check balance
        total_debit = sum(line["debit"] for line in data["lines"])
        total_credit = sum(line["credit"] for line in data["lines"])
        if abs(total_debit - total_credit) > 0.001:
            QMessageBox.warning(self, "Validation Error", "Entry is unbalanced. Total debit and credit must be equal.")
            return

        try:
            response = self.api_client.post("/api/accounting/journal-entries/", data=data)
            if response.get("success") or "id" in response:
                self.accept()
            else:
                errors = response.get("errors", response.get("error", "Unknown error"))
                if isinstance(errors, list):
                    errors = "\n".join(errors)
                QMessageBox.critical(self, "Error", f"Failed to save entry:\n{errors}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Server communication error: {e}")

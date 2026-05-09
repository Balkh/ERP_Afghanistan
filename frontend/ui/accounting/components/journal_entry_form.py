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
    COLOR_BORDER_LIGHT_THEME, COLOR_TEXT_ON_PRIMARY, BORDER_RADIUS_SM, BORDER_RADIUS_MD)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


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
                border: 1px solid {COLOR_TEXT_SECONDARY_LIGHT};
                border-radius: {BORDER_RADIUS_MD};
                margin-top: {SPACING_LG};
                padding-top: {SPACING_LG};
                background-color: {COLOR_BG_MAIN};
            }}
            QLabel {{ color: {COLOR_TEXT_LIGHT}; }}
            QPushButton#save_btn {{
                background-color: {COLOR_SUCCESS};
                color: {COLOR_TEXT_ON_PRIMARY};
                font-weight: bold;
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_LG} {SPACING_XL * 2};
            }}
            QPushButton#save_btn:hover {{
                background-color: {COLOR_SUCCESS_HOVER};
            }}
            QPushButton#cancel_btn {{
                background-color: {COLOR_MUTED_LIGHT};
                color: white;
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_LG} {SPACING_XL * 2};
            }}
            QPushButton#cancel_btn:hover {{
                background-color: {COLOR_TEXT_SECONDARY_LIGHT};
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM} {SPACING_LG};
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
            QLineEdit, QComboBox, QTextEdit, QDateEdit, QDoubleSpinBox {{
                background-color: {COLOR_BG_INPUT};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER_LIGHT_THEME};
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM};
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
            QTableWidget {{
                background-color: {COLOR_BG_MAIN};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_TEXT_SECONDARY};
                gridline-color: {COLOR_TEXT_SECONDARY};
            }}
            QHeaderView::section {{
                background-color: {COLOR_TEXT_SECONDARY};
                color: {COLOR_TEXT_PRIMARY};
                padding: {SPACING_SM};
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: {SPACING_SM};
                border-bottom: 1px solid {COLOR_TEXT_SECONDARY};
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        title = QLabel("Create Journal Entry")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: #2c3e50;")
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
        
        header = self.lines_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.lines_table.setColumnWidth(4, 40)
        
        self.lines_table.setAlternatingRowColors(True)
        self.lines_table.setStyleSheet(f"""
            QTableWidget {{ border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}
            QHeaderView::section {{ background-color: {COLOR_BG_ELEVATED}; padding: 5px; font-weight: bold; }}
        """)
        lines_layout.addWidget(self.lines_table)

        line_buttons = QHBoxLayout()
        self.btn_add_line = QPushButton("+ Add Line")
        self.btn_add_line.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: white;
                border-radius: 4px;
                padding: 5px 15px;
                font-weight: bold;
            }}
        """)
        self.btn_remove_line = QPushButton("- Remove Selected Lines")
        self.btn_remove_line.setStyleSheet(f"""
            QPushButton {{
                background-color: #f1f2f6;
                color: #2f3640;
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 5px 15px;
            }}
        """)
        line_buttons.addWidget(self.btn_add_line)
        line_buttons.addWidget(self.btn_remove_line)
        line_buttons.addStretch()
        lines_layout.addLayout(line_buttons)

        layout.addWidget(lines_group)

        # Totals and Balance
        bottom_layout = QHBoxLayout()
        
        totals_frame = QFrame()
        totals_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 8px;")
        totals_layout = QHBoxLayout(totals_frame)
        
        totals_layout.addWidget(QLabel("Total Debit:"))
        self.total_debit_label = QLabel("0.00")
        self.total_debit_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.total_debit_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
        totals_layout.addWidget(self.total_debit_label)

        totals_layout.addSpacing(20)

        totals_layout.addWidget(QLabel("Total Credit:"))
        self.total_credit_label = QLabel("0.00")
        self.total_credit_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.total_credit_label.setStyleSheet("color: #c0392b;")
        totals_layout.addWidget(self.total_credit_label)

        totals_layout.addSpacing(30)

        self.balance_label = QLabel("BALANCED")
        self.balance_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.balance_label.setStyleSheet("color: #2ecc71; padding: 5px 15px; border-radius: 4px; background-color: #e8f5e9;")
        totals_layout.addWidget(self.balance_label)
        
        bottom_layout.addWidget(totals_frame)
        layout.addLayout(bottom_layout)

        # Actions
        action_buttons = QHBoxLayout()
        action_buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Entry")
        save_btn.setObjectName("save_btn")
        save_btn.setMinimumWidth(150)
        save_btn.setCursor(Qt.PointingHandCursor)
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
            self.balance_label.setStyleSheet("color: #2ecc71; padding: 5px 15px; border-radius: 4px; background-color: #e8f5e9;")
        elif total_debit == 0 and total_credit == 0:
            self.balance_label.setText("EMPTY")
            self.balance_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: 5px 15px; border-radius: 4px; background-color: #f1f2f6;")
        else:
            diff = abs(total_debit - total_credit)
            self.balance_label.setText(f"UNBALANCED ({diff:,.2f})")
            self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; padding: 5px 15px; border-radius: 4px; background-color: #fdecea;")

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

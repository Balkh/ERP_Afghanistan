from decimal import Decimal
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, QFrame,
                               QLineEdit, QComboBox, QTextEdit, QWidget,
                               QLabel, QDateEdit,
                               QHeaderView, QGroupBox,
                               QDoubleSpinBox, QCheckBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from api.client import APIClient
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    MARGIN_PAGE, COLOR_SUCCESS, COLOR_DANGER, COLOR_BG_SURFACE,
    COLOR_BG_INPUT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_BORDER, COLOR_BORDER_INPUT, COLOR_BORDER_INPUT_HOVER,
    COLOR_SUCCESS_BG, COLOR_DANGER_BG, COLOR_FORM_SECTION_TITLE, COLOR_FORM_SECTION_DIVIDER,
    BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG, TEXT_SECTION_TITLE,
    TEXT_CARD_TITLE, TEXT_LABEL, INPUT_HEIGHT_MD, DIALOG_WIDTH_WIDE,
    SECTION_TITLE_SPACING)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import DataEntryGrid
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.forms import FormSection


class JournalEntryFormDialog(EnterpriseDialog):
    """Dialog for creating a new journal entry with line items."""

    def __init__(self, parent=None, api_client=None):
        self._api_client = api_client or APIClient()
        self.accounts = []
        self.line_items = []
        self._submitting = False
        super().__init__("Create New Journal Entry", DialogType.CUSTOM, parent)
        self.setMinimumWidth(DIALOG_WIDTH_WIDE)
        self.setMinimumHeight(700)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save)
        self.load_accounts()

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        title = QLabel("Create Journal Entry")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        # Header Information
        header_section = FormSection("General Information", primary=True)

        self.entry_type = QComboBox()
        self.entry_type.setMinimumHeight(INPUT_HEIGHT_MD)
        for t in ["SALE", "PURCHASE", "PAYMENT", "RECEIPT", "ADJUSTMENT", "TRANSFER", "OPENING", "CLOSING"]:
            self.entry_type.addItem(t, t)
        header_section.add_field(self.entry_type, "Entry Type:")

        self.entry_date = QDateEdit()
        self.entry_date.setMinimumHeight(INPUT_HEIGHT_MD)
        self.entry_date.setCalendarPopup(True)
        self.entry_date.setDisplayFormat("yyyy-MM-dd")
        from datetime import date
        self.entry_date.setDate(date.today())
        header_section.add_field(self.entry_date, "Entry Date:")

        self.description = QTextEdit()
        self.description.setMaximumHeight(80)
        self.description.setMinimumHeight(INPUT_HEIGHT_MD)
        self.description.setPlaceholderText("Enter overall entry description...")
        header_section.add_field(self.description, "Description:")

        self.reference = QLineEdit()
        self.reference.setMinimumHeight(INPUT_HEIGHT_MD)
        self.reference.setPlaceholderText("Reference number (optional)")
        header_section.add_field(self.reference, "Reference:")

        self.auto_post = QCheckBox("Auto-post after creation")
        self.auto_post.setStyleSheet(f"margin-left: {SPACING_SM}px; color: {COLOR_TEXT_PRIMARY};")
        header_section.add_field(self.auto_post, "")

        layout.addWidget(header_section)

        # Journal Lines
        lines_group = QGroupBox("Journal Lines (Articles)")
        lines_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: 700;
                font-size: {TEXT_LABEL}pt;
                color: {COLOR_FORM_SECTION_TITLE};
                border: 1px solid {COLOR_FORM_SECTION_DIVIDER};
                border-radius: {BORDER_RADIUS_LG}px;
                margin-top: {SECTION_TITLE_SPACING}px;
                padding-top: {SECTION_TITLE_SPACING + 6}px;
                background-color: {COLOR_BG_SURFACE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {SPACING_MD}px;
                color: {COLOR_FORM_SECTION_TITLE};
            }}
        """)
        lines_layout = QVBoxLayout(lines_group)
        lines_layout.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)

        self.lines_table = DataEntryGrid(["Account", "Line Description", "Debit", "Credit", ""])
        self.lines_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.lines_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.lines_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.lines_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.lines_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.lines_table.setColumnWidth(4, 40)
        lines_layout.addWidget(self.lines_table)

        line_buttons = QHBoxLayout()
        self.btn_add_line = EnterpriseButton("+ Add Line", variant=ButtonVariant.PRIMARY, size=ButtonSize.SMALL)
        self.btn_remove_line = EnterpriseButton("- Remove Selected", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        line_buttons.addWidget(self.btn_add_line)
        line_buttons.addWidget(self.btn_remove_line)
        line_buttons.addStretch()
        lines_layout.addLayout(line_buttons)

        layout.addWidget(lines_group)

        # Totals and Balance
        bottom_layout = QHBoxLayout()

        totals_frame = QFrame()
        totals_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px;")
        totals_layout = QHBoxLayout(totals_frame)

        totals_layout.addWidget(QLabel("Total Debit:"))
        self.total_debit_label = QLabel("0.00")
        debit_font = QFont("Segoe UI", TEXT_CARD_TITLE)
        debit_font.setWeight(QFont.Weight.Bold)
        self.total_debit_label.setFont(debit_font)
        self.total_debit_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
        totals_layout.addWidget(self.total_debit_label)

        totals_layout.addSpacing(SPACING_XL)

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
        self.balance_label.setStyleSheet(f"color: {COLOR_SUCCESS}; padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}px; background-color: {COLOR_SUCCESS_BG};")
        totals_layout.addWidget(self.balance_label)

        bottom_layout.addWidget(totals_frame)
        layout.addLayout(bottom_layout)

        # Actions
        action_buttons = QHBoxLayout()
        action_buttons.addStretch()

        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.GHOST, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)

        save_btn = EnterpriseButton("Save Entry", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self.save)

        action_buttons.addWidget(cancel_btn)
        action_buttons.addWidget(save_btn)

        layout.addLayout(action_buttons)

        self.btn_add_line.clicked.connect(self._add_line)
        self.btn_remove_line.clicked.connect(self._remove_line)

        # Start with 2 lines
        self._add_line()
        self._add_line()

        return widget

    def _create_button_area(self):
        return None

    def load_accounts(self):
        try:
            self.accounts = self._api_client.get("/api/accounting/accounts/leaf_accounts/")
            for row in range(self.lines_table.rowCount()):
                combo = self.lines_table.cell_widget(row, 0)
                if isinstance(combo, QComboBox):
                    current_idx = combo.currentIndex()
                    combo.clear()
                    combo.addItem("Select Account...", None)
                    for acc in sorted(self.accounts, key=lambda x: x.get("code", "")):
                        combo.addItem(f"{acc.get('code', '')} - {acc.get('name', '')}", acc.get('id'))
                    combo.setCurrentIndex(current_idx)
        except Exception:
            self.accounts = []

    def _add_line(self):
        self.lines_table.add_row()
        row = self.lines_table.rowCount() - 1
        self.lines_table.set_row_height(row, 45)

        account_combo = QComboBox()
        account_combo.addItem("Select Account...", None)
        for acc in sorted(self.accounts, key=lambda x: x.get("code", "")):
            account_combo.addItem(f"{acc.get('code', '')} - {acc.get('name', '')}", acc.get('id'))
        self.lines_table.set_cell_widget(row, 0, account_combo)

        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Line description")
        self.lines_table.set_cell_widget(row, 1, desc_input)

        debit_spin = QDoubleSpinBox()
        debit_spin.setMaximum(999999999.99)
        debit_spin.setDecimals(2)
        debit_spin.setAlignment(Qt.AlignRight)
        debit_spin.valueChanged.connect(self._update_totals)
        self.lines_table.set_cell_widget(row, 2, debit_spin)

        credit_spin = QDoubleSpinBox()
        credit_spin.setMaximum(999999999.99)
        credit_spin.setDecimals(2)
        credit_spin.setAlignment(Qt.AlignRight)
        credit_spin.valueChanged.connect(self._update_totals)
        self.lines_table.set_cell_widget(row, 3, credit_spin)

        remove_btn = EnterpriseButton("x", variant=ButtonVariant.GHOST)
        remove_btn.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold;")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(self._on_remove_line_btn_clicked)
        self.lines_table.set_cell_widget(row, 4, remove_btn)

    def _remove_line(self):
        selected = self.lines_table.selectionModel().selectedRows()
        if selected:
            for idx in sorted([r.row() for r in selected], reverse=True):
                self.lines_table.remove_row(idx)
            self._update_totals()

    def _on_remove_line_btn_clicked(self):
        """Find owning row via sender() to handle row reindexing correctly."""
        button = self.sender()
        if not button:
            return
        for row in range(self.lines_table.rowCount()):
            if self.lines_table.cell_widget(row, 4) is button:
                self.lines_table.remove_row(row)
                self._update_totals()
                return

    def _update_totals(self):
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for row in range(self.lines_table.rowCount()):
            debit_widget = self.lines_table.cell_widget(row, 2)
            credit_widget = self.lines_table.cell_widget(row, 3)
            if debit_widget:
                total_debit += Decimal(str(debit_widget.value()))
            if credit_widget:
                total_credit += Decimal(str(credit_widget.value()))

        self.total_debit_label.setText(f"{total_debit:,.2f}")
        self.total_credit_label.setText(f"{total_credit:,.2f}")

        if total_debit == total_credit and total_debit > 0:
            self.balance_label.setText("BALANCED")
            self.balance_label.setStyleSheet(f"color: {COLOR_SUCCESS}; padding: {SPACING_XS}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}px; background-color: {COLOR_SUCCESS_BG};")
        elif total_debit == 0 and total_credit == 0:
            self.balance_label.setText("EMPTY")
            self.balance_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: {SPACING_XS}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}px; background-color: {COLOR_BG_SURFACE};")
        else:
            diff = abs(total_debit - total_credit)
            self.balance_label.setText(f"UNBALANCED ({diff:,.2f})")
            self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; padding: {SPACING_XS}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}px; background-color: {COLOR_DANGER_BG};")

    def get_entry_data(self):
        data = {
            "entry_type": self.entry_type.currentData(),
            "entry_date": self.entry_date.date().toString("yyyy-MM-dd"),
            "description": self.description.toPlainText().strip(),
            "reference": self.reference.text().strip(),
            "auto_post": self.auto_post.isChecked(),
            "lines": [],
        }
        for row in range(self.lines_table.rowCount()):
            account_combo = self.lines_table.cell_widget(row, 0)
            desc_input = self.lines_table.cell_widget(row, 1)
            debit_spin = self.lines_table.cell_widget(row, 2)
            credit_spin = self.lines_table.cell_widget(row, 3)
            account_id = account_combo.currentData() if account_combo else None
            if account_id is None:
                continue
            data["lines"].append({
                "account_id": account_id,
                "description": desc_input.text().strip() if desc_input else "",
                "debit": debit_spin.value() if debit_spin else 0.0,
                "credit": credit_spin.value() if credit_spin else 0.0,
            })
        return data

    def save(self):
        if self._submitting:
            return
        self._submitting = True
        data = self.get_entry_data()

        if not data["description"]:
            self._submitting = False
            AlertDialog.warning("Validation Error", "Description is required.", self)
            return
        if len(data["lines"]) < 2:
            AlertDialog.warning("Validation Error", "At least 2 lines are required for the entry.", self)
            self._submitting = False
            return

        total_debit = sum(line["debit"] for line in data["lines"])
        total_credit = sum(line["credit"] for line in data["lines"])
        if abs(total_debit - total_credit) > 0.001:
            AlertDialog.warning("Validation Error", "Entry is unbalanced. Total debit and credit must be equal.", self)
            self._submitting = False
            return

        try:
            response = self._api_client.post("/api/accounting/journal-entries/", data=data)
            if response.get("success") or "id" in response:
                self._submitting = False
                self.accept()
            else:
                errors = response.get("errors", response.get("error", "Unknown error"))
                if isinstance(errors, list):
                    errors = "\n".join(errors)
                AlertDialog.error("Error", f"Failed to save entry:\n{errors}", self)
                self._submitting = False
        except Exception as e:
            AlertDialog.error("Error", f"Server communication error: {e}", self)
            self._submitting = False

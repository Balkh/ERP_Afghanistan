import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QGroupBox, QFrame, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.constants import (
    SPACING_XS,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
    MARGIN_PAGE,
    BORDER_RADIUS_SM,
    BORDER_RADIUS_LG,
    TEXT_BODY,
    TEXT_LABEL,
    TEXT_SECTION_TITLE,
    COLOR_BG_MAIN,
    COLOR_BG_SURFACE,
    COLOR_BG_ELEVATED,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_TABLE_BORDER_LIGHT,
    COLOR_TABLE_HEADER_BG_LIGHT,
)

from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.dialogs import EnterpriseDialog, DialogType
from ui.components.forms import FormSection

class JournalEntryDetailDialog(EnterpriseDialog):
    """Dialog to view a journal entry detail with its lines."""

    def __init__(self, parent=None, entry_data=None, api_client=None):
        self.api_client = api_client
        self.entry_data = entry_data or {}
        self.lines = []
        super().__init__("Entry Details", DialogType.CUSTOM, parent)
        self._build_content()
        self.load_data()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        self.setMinimumWidth(850)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        title = QLabel("Journal Entry Details")
        title.setStyleSheet(UIStyleBuilder.get_page_header_style())
        layout.addWidget(title)

        # Entry Information
        info_section = FormSection("General Information", primary=True)

        self.entry_number = QLabel("")
        self.entry_number.setStyleSheet(f"font-weight: bold; color: {COLOR_PRIMARY};")
        info_section.add_field(self.entry_number, "Entry #:")

        self.entry_date = QLabel("")
        info_section.add_field(self.entry_date, "Date:")

        self.entry_type = QLabel("")
        info_section.add_field(self.entry_type, "Type:")

        self.description = QLabel("")
        self.description.setWordWrap(True)
        info_section.add_field(self.description, "Description:")

        self.reference = QLabel("")
        info_section.add_field(self.reference, "Reference:")

        self.is_posted = QLabel("")
        self.is_posted.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        self.is_posted.setStyleSheet(f"font-weight: bold;")
        info_section.add_field(self.is_posted, "Status:")

        layout.addWidget(info_section)

        # Journal Lines
        lines_group = QGroupBox("Journal Lines (Articles)")
        lines_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=False))
        lines_layout = QVBoxLayout(lines_group)

        columns = [
            TableColumn("account", "Account", width=220),
            TableColumn("description", "Line Description", width=260),
            TableColumn("debit", "Debit", width=110, align="right"),
            TableColumn("credit", "Credit", width=110, align="right"),
        ]
        self.lines_table = EnterpriseTable(columns, density="compact")
        lines_layout.addWidget(self.lines_table)

        # Totals
        totals_frame = QFrame()
        totals_frame.setStyleSheet(UIStyleBuilder.get_card_style())
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.addStretch()
        
        totals_layout.addWidget(QLabel("Total Debit:"))
        self.total_debit_label = QLabel("0.00")
        self.total_debit_label.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        self.total_debit_label.setStyleSheet(f"font-weight: bold; color: {COLOR_SUCCESS};")
        totals_layout.addWidget(self.total_debit_label)
        
        totals_layout.addSpacing(20)
        
        totals_layout.addWidget(QLabel("Total Credit:"))
        self.total_credit_label = QLabel("0.00")
        self.total_credit_label.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        self.total_credit_label.setStyleSheet(f"font-weight: bold; color: {COLOR_DANGER};")
        totals_layout.addWidget(self.total_credit_label)
        
        lines_layout.addLayout(totals_layout)
        layout.addWidget(lines_group)

        # Footer Actions
        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = EnterpriseButton(text="Close", variant=ButtonVariant.PRIMARY, size=ButtonSize.SMALL)
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.set_content(widget)
        return widget

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

            total_debit = 0.0
            total_credit = 0.0
            rows = []

            for line in lines_data:
                account = line.get("account", {})
                account_str = f"{account.get('code', '')} - {account.get('name', '')}"
                debit = float(line.get("debit", 0) or 0)
                credit = float(line.get("credit", 0) or 0)
                total_debit += debit
                total_credit += credit
                rows.append({
                    "account": account_str,
                    "description": line.get("description", ""),
                    "debit": f"{debit:,.2f}",
                    "credit": f"{credit:,.2f}",
                })

            self.lines_table.set_data(rows)
            self.total_debit_label.setText(f"{total_debit:,.2f}")
            self.total_credit_label.setText(f"{total_credit:,.2f}")

        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading journal lines: {e}")

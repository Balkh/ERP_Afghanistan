from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QHeaderView, QAbstractItemView,
                               QComboBox, QLineEdit, QDateEdit,
                               QGroupBox, QApplication)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from utils.format import safe_float
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           TEXT_LABEL, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS,
                           COLOR_WARNING, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.components.operator_safety import DestructiveActionGuard
from ui.components.tables import EnterpriseTable, TableColumn
from ui.screens.base_screen import BaseScreen


class JournalEntryScreen(BaseScreen):
    """Journal Entry list screen with filtering and actions."""

    entry_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, screen_id="journal_entries")
        self.api_client = api_client or APIClient()
        self.entries = []
        self._is_loading = False
        self.setup_ui()
        try:
            self.load_entries()
        except Exception as e:
            self.empty_label.setText(f"Initial load failed: {e}")
            self.empty_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
            self.empty_label.setVisible(True)

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load in __init__."""

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section with title and refresh button
        header_layout = QHBoxLayout()
        header = QLabel("Journal Entries")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(
            text="\u27f3 Refresh",
            variant=ButtonVariant.SECONDARY,
            size=ButtonSize.MEDIUM
        )
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Toolbar for actions
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Filter section
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading journal entries...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No journal entries found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table section
        self.table = self._create_table()
        layout.addWidget(self.table)

    def _create_toolbar(self):
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background-color: {COLOR_BG_MAIN}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG};")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        self.btn_new = EnterpriseButton(text="New Entry", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.btn_view = EnterpriseButton(text="View Details", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_post = EnterpriseButton(text="Post", variant=ButtonVariant.WARNING, size=ButtonSize.MEDIUM)
        self.btn_unpost = EnterpriseButton(text="Unpost", variant=ButtonVariant.WARNING, size=ButtonSize.MEDIUM)
        self.btn_reverse = EnterpriseButton(text="Reverse", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)

        for btn in [self.btn_new, self.btn_view, self.btn_post, self.btn_unpost, self.btn_reverse]:
            btn.setMinimumWidth(130)
            layout.addWidget(btn)

        for btn in [self.btn_view, self.btn_post, self.btn_unpost, self.btn_reverse]:
            btn.setEnabled(False)

        layout.addStretch()

        self.btn_new.clicked.connect(self._on_new)
        self.btn_view.clicked.connect(self._on_view)
        self.btn_post.clicked.connect(self._on_post)
        self.btn_unpost.clicked.connect(self._on_unpost)
        self.btn_reverse.clicked.connect(self._on_reverse)
        self.btn_refresh.clicked.connect(self.load_entries)

        return toolbar

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG};
                margin-top: {SPACING_SM}px;
                padding-top: {SPACING_SM}px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_LABEL}pt;
                font-weight: 700;
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Type filter
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Entry Type:"))
        self.type_filter = QComboBox()
        self.type_filter.setStyleSheet(f"""
            QComboBox {{ background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; padding: {SPACING_XS}px {SPACING_SM}px; }}
            QComboBox QAbstractItemView {{ background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY}; selection-color: {COLOR_TEXT_ON_PRIMARY};
                border: 1px solid {COLOR_BORDER}; }}
        """)
        self.type_filter.addItem("All", "")
        for t in ["SALE", "PURCHASE", "PAYMENT", "RECEIPT", "ADJUSTMENT", "TRANSFER", "OPENING", "CLOSING", "REVERSAL"]:
            self.type_filter.addItem(t, t)
        self.type_filter.setMinimumWidth(120)
        type_layout.addWidget(self.type_filter)
        layout.addLayout(type_layout)

        # Status filter
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.setStyleSheet(f"""
            QComboBox {{ background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; padding: {SPACING_XS}px {SPACING_SM}px; }}
            QComboBox QAbstractItemView {{ background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY}; selection-color: {COLOR_TEXT_ON_PRIMARY};
                border: 1px solid {COLOR_BORDER}; }}
        """)
        self.status_filter.addItem("All", "")
        self.status_filter.addItem("Posted", "posted")
        self.status_filter.addItem("Draft", "draft")
        self.status_filter.setMinimumWidth(100)
        status_layout.addWidget(self.status_filter)
        layout.addLayout(status_layout)

        # Date range
        date_layout = QVBoxLayout()
        date_label_layout = QHBoxLayout()
        date_label_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        date_label_layout.addWidget(self.date_from)
        
        date_label_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        date_label_layout.addWidget(self.date_to)
        date_layout.addLayout(date_label_layout)
        layout.addLayout(date_layout)

        # Search
        search_layout = QVBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Entry # or description...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMinimumHeight(30)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Apply button
        self.btn_apply = EnterpriseButton(
            text="Apply Filters",
            variant=ButtonVariant.SECONDARY,
            size=ButtonSize.MEDIUM
        )
        self.btn_apply.clicked.connect(self.load_entries)
        
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        return bar

    def _create_table(self):
        columns = [
            TableColumn("entry_number", "Entry #", width=80, align="center"),
            TableColumn("entry_date", "Date", width=90, align="center"),
            TableColumn("entry_type", "Type", width=80, align="center"),
            TableColumn("description", "Description", width=300),
            TableColumn("debit", "Debit", width=100, align="right"),
            TableColumn("credit", "Credit", width=100, align="right"),
            TableColumn("status", "Status", width=70, align="center"),
            TableColumn("reference", "Reference", width=150),
        ]
        table = EnterpriseTable(columns, density="compact")
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.itemSelectionChanged.connect(self._on_selection_changed)
        table.itemDoubleClicked.connect(self._on_view)

        return table

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self._is_loading = show
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.btn_refresh.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_empty(self, message="No entries found"):
        """Show empty state."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)


    def load_entries(self):
        self._show_loading()
        params = {"page_size": 100}

        type_val = self.type_filter.currentData()
        if type_val:
            params["entry_type"] = type_val

        status_val = self.status_filter.currentData()
        if status_val == "posted":
            params["is_posted"] = "true"
        elif status_val == "draft":
            params["is_posted"] = "false"

        search = self.search_input.text().strip()
        if search:
            params["search"] = search

        try:
            endpoint = get_endpoint("journal_entries")
            data = self.api_client.get(endpoint, params=params)
            raw_entries = extract_list(data)
            self.entries = [e for e in raw_entries if isinstance(e, dict)]
            self._populate_table()
        except Exception as e:
            self.entries = []
            self._populate_table()
            self.empty_label.setText(f"Error loading entries: {e}")
            self.empty_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
            self.empty_label.setVisible(True)

    def _populate_table(self):
        if not self.entries:
            self.table.set_data([])
            self._show_empty("No journal entries found matching these criteria.")
            return

        self._show_data()
        entries_data = []
        for entry in self.entries:
            if not isinstance(entry, dict):
                continue

            is_posted = entry.get("is_posted") or False
            debit = safe_float(entry.get("total_debit"))
            credit = safe_float(entry.get("total_credit"))
            description = entry.get("description") or ""
            entries_data.append({
                "entry_number": entry.get("entry_number") or "",
                "entry_date": entry.get("entry_date") or "",
                "entry_type": entry.get("entry_type") or "",
                "description": description[:60] if len(description) > 60 else description,
                "debit": f"{debit:,.2f}",
                "credit": f"{credit:,.2f}",
                "status": "Posted" if is_posted else "Draft",
                "reference": entry.get("reference") or "",
                "id": entry.get("id"),
                "is_posted": is_posted,
                "_debit_value": debit,
                "_credit_value": credit,
            })

        self.table.set_data(entries_data)

        # Apply foreground colors after data is set
        for row in range(self.table.rowCount()):
            entry_data = self.table.get_row_data(row)
            if not entry_data:
                continue

            # Debit (green)
            debit_item = self.table.item(row, 4)
            if debit_item:
                debit_item.setForeground(QColor(COLOR_SUCCESS))

            # Credit (red)
            credit_item = self.table.item(row, 5)
            if credit_item:
                credit_item.setForeground(QColor(COLOR_DANGER))

            # Status color
            status_item = self.table.item(row, 6)
            if status_item:
                if entry_data.get("is_posted"):
                    status_item.setForeground(QColor(COLOR_SUCCESS))
                    status_item.setFont(self.table.font())
                else:
                    status_item.setForeground(QColor(COLOR_WARNING))

    def _on_selection_changed(self):
        rows = self.table.get_selected_rows()
        has_selection = bool(rows)
        self.btn_view.setEnabled(has_selection)

        if has_selection:
            entry = self.table.get_row_data(rows[0])
            is_posted = entry.get("is_posted", False) if entry else False
            self.btn_post.setEnabled(not is_posted)
            self.btn_unpost.setEnabled(is_posted)
            self.btn_reverse.setEnabled(is_posted)

    def _on_new(self):
        from ui.accounting.components.journal_entry_form import JournalEntryFormDialog
        dialog = JournalEntryFormDialog(self, api_client=self.api_client)
        if dialog.exec():
            self.load_entries()

    def _get_selected_entry(self):
        rows = self.table.get_selected_rows()
        if not rows:
            return None
        return self.table.get_row_data(rows[0])

    def _on_view(self):
        entry = self._get_selected_entry()
        if entry:
            self._show_entry_detail(entry)

    def _on_post(self):
        entry = self._get_selected_entry()
        if not entry:
            return

        if DestructiveActionGuard.confirm_irreversible(
            self, "Confirm Post",
            f"Are you sure you want to post journal entry {entry.get('entry_number')}?"
        ):
            try:
                self.api_client.post(f"/api/accounting/journal-entries/{entry['id']}/post_entry/")
                self.load_entries()
                AlertDialog.info("Success", "Journal entry posted successfully.", self)
            except Exception as e:
                AlertDialog.error("Error", f"Failed to post entry: {e}", self)

    def _on_unpost(self):
        entry = self._get_selected_entry()
        if not entry:
            return

        if DestructiveActionGuard.confirm_irreversible(
            self, "Confirm Unpost",
            f"Are you sure you want to unpost journal entry {entry.get('entry_number')}?"
        ):
            try:
                self.api_client.post(f"/api/accounting/journal-entries/{entry['id']}/unpost_entry/")
                self.load_entries()
                AlertDialog.info("Success", "Journal entry unposted successfully.", self)
            except Exception as e:
                AlertDialog.error("Error", f"Failed to unpost entry: {e}", self)

    def _on_reverse(self):
        entry = self._get_selected_entry()
        if not entry:
            return

        if DestructiveActionGuard.confirm_accounting_reversal(
            self, f"journal entry {entry.get('entry_number')}"
        ):
            try:
                self.api_client.post(
                    f"/api/accounting/journal-entries/{entry['id']}/reverse_entry/",
                    data={"reason": "Reversed from UI"}
                )
                self.load_entries()
                AlertDialog.info("Success", "Journal entry reversed successfully.", self)
            except Exception as e:
                AlertDialog.error("Error", f"Failed to reverse entry: {e}", self)

    def _show_entry_detail(self, entry):
        from ui.accounting.components.journal_entry_detail import JournalEntryDetailDialog
        dialog = JournalEntryDetailDialog(self, entry, self.api_client)
        dialog.exec()

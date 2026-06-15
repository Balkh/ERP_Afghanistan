from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit,
                                  QComboBox, QDateEdit, QGroupBox,
                                   QTextEdit, QApplication, QWidget)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from ui.screens.base_screen import BaseScreen
from ui.utils.debounce import Debouncer
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           TEXT_LABEL, BORDER_RADIUS_LG, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_DANGER)
from api.client import APIClient
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.forms import FormSection
from ui.components.state_helper import StateHelper

class ExpenseScreen(BaseScreen):
    """Screen for managing pharmacy expenses."""
    
    def __init__(self, parent=None, screen_id="expenses", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self.api_client = api_client or APIClient()
        self.expenses_data = []
        self.setup_ui()
        self.load_expenses()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Pharmacy Expenses")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_expenses)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Action section
        action_layout = QHBoxLayout()
        self.add_btn = EnterpriseButton(text="+ Record Expense", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.add_btn.clicked.connect(self.show_add_expense_dialog)
        action_layout.addWidget(self.add_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Filters
        filter_bar = QGroupBox("Filter Expenses")
        filter_font = QFont("Segoe UI", TEXT_LABEL)
        filter_font.setWeight(QFont.Weight.Bold)
        filter_bar.setFont(filter_font)
        filter_bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; margin-top: {PADDING_INPUT_H}px; padding-top: {PADDING_INPUT_H}px; color: {COLOR_TEXT_PRIMARY}; }}")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search expenses...")
        self.search_input.setMinimumHeight(30)
        self.search_input.setMinimumWidth(200)
        self._expense_search_debounce = Debouncer(self.load_expenses, 300)
        self.search_input.textChanged.connect(self._expense_search_debounce)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setMinimumHeight(30)
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMinimumHeight(30)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.date_to)
        
        layout.addWidget(filter_bar)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        # Table
        columns = [
            TableColumn("date", "Date", width=90, align="center"),
            TableColumn("expense_number", "Expense #", width=100),
            TableColumn("category", "Category", width=120),
            TableColumn("payment_account", "Payment Method", width=120),
            TableColumn("payee", "Payee", width=120),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("description", "Description", width=200),
        ]
        self.table = EnterpriseTable(columns)
        layout.addWidget(self.table)

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        if show:
            self.state_helper.show_loading("Loading expenses...")
            self.table.setVisible(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.state_helper.hide()
            self.table.setVisible(True)
            self.btn_refresh.setEnabled(True)

    def _show_empty(self, message="No expenses found"):
        """Show empty state."""
        self.state_helper.show_empty(title=message)
        self.table.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_error(self, message="Error loading expenses"):
        """Show error state."""
        self.state_helper.show_error(message, on_retry=self.load_expenses)
        self.table.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self.state_helper.hide()
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def load_expenses(self):
        self._show_loading()
        try:
            params = {
                'search': self.search_input.text(),
                'start_date': self.date_from.date().toString("yyyy-MM-dd"),
                'end_date': self.date_to.date().toString("yyyy-MM-dd")
            }
            if not hasattr(self, "_async_expenses_response"):
                self.run_api_request(
                    "expenses:list", "GET", "/api/expenses/", params=params,
                    on_success=lambda r: self._resume_api_request("_async_expenses_response", self.load_expenses, r),
                    on_error=lambda m: self._resume_api_request("_async_expenses_response", self.load_expenses, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_expenses_response")
            if response and response.get('success'):
                self.expenses_data = response['data'].get('results', [])
                if not self.expenses_data:
                    self._show_empty()
                else:
                    self._show_data()
                    self._populate_table()
            else:
                self._show_empty()
        except Exception as e:
            self._show_error(f"Failed to load expenses: {e}")

    def _populate_table(self):
        data = []
        for exp in self.expenses_data:
            data.append({
                "date": exp.get('date', ''),
                "expense_number": exp.get('expense_number', ''),
                "category": exp.get('expense_account_name', ''),
                "payment_account": exp.get('payment_account_name', ''),
                "payee": exp.get('payee', ''),
                "amount": f"{float(exp.get('amount', 0)):,.2f}",
                "description": exp.get('description', ''),
            })
        self.table.set_data(data)

    def show_add_expense_dialog(self):
        dialog = AddExpenseDialog(self, api_client=self.api_client)
        if dialog.exec():
            self.load_expenses()

class AddExpenseDialog(EnterpriseDialog):
    """Dialog to record a new expense."""
    
    def __init__(self, parent=None, api_client=None):
        self.api_client = api_client
        super().__init__("Record Pharmacy Expense", DialogType.CUSTOM, parent)
        self.setMinimumWidth(450)
        self._build_content()
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save_expense)
        self._load_accounts()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        section = FormSection("Expense Details", primary=True)
        
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(QDate.currentDate())
        section.add_field(self.date, "Date:")
        
        self.expense_account = QComboBox()
        section.add_field(self.expense_account, "Expense Category:")
        
        self.payment_account = QComboBox()
        section.add_field(self.payment_account, "Paid From:")
        
        self.amount = QLineEdit()
        self.amount.setPlaceholderText("0.00")
        section.add_field(self.amount, "Amount:")
        
        self.payee = QLineEdit()
        self.payee.setPlaceholderText("e.g. Landlord, Electric Co.")
        section.add_field(self.payee, "Payee:")
        
        self.description = QTextEdit()
        self.description.setMaximumHeight(80)
        section.add_field(self.description, "Description:")
        
        layout.addWidget(section)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(SPACING_SM)
        btn_layout.addStretch()
        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        ok_btn.clicked.connect(self.save_expense)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        self.set_content(widget)

    def _load_accounts(self):
        self.run_api_request(
            "expense_dialog:expense_accounts", "GET", "/api/accounting/accounts/", params={'account_type': 'EXPENSE'},
            on_success=self._populate_expense_accounts,
            on_error=lambda m: print(f"Failed to load expense accounts: {m}"),
        )
        self.run_api_request(
            "expense_dialog:payment_accounts", "GET", "/api/payments/accounts/",
            on_success=self._populate_payment_accounts,
            on_error=lambda m: print(f"Failed to load payment accounts: {m}"),
        )

    def _populate_expense_accounts(self, exp_res):
        if exp_res and exp_res.get('success'):
            data = exp_res['data']
            results = data.get('results', data) if isinstance(data, dict) else data
            for acc in results:
                self.expense_account.addItem(f"{acc['code']} - {acc['name']}", acc['id'])

    def _populate_payment_accounts(self, pay_res):
        if pay_res and pay_res.get('success'):
            data = pay_res['data']
            results = data.get('results', data) if isinstance(data, dict) else data
            for acc in results:
                self.payment_account.addItem(acc['name'], acc['id'])

    def save_expense(self):
        try:
            amount = float(self.amount.text())
            if amount <= 0:
                raise ValueError("Amount must be positive.")
                
            data = {
                "date": self.date.date().toString("yyyy-MM-dd"),
                "expense_account": self.expense_account.currentData(),
                "payment_account": self.payment_account.currentData(),
                "amount": amount,
                "payee": self.payee.text(),
                "description": self.description.toPlainText()
            }
            
            if not hasattr(self, "_async_save_expense_response"):
                self.run_api_request(
                    "expense_dialog:save", "POST", "/api/expenses/", data=data,
                    on_success=lambda r: self._resume_api_request("_async_save_expense_response", self.save_expense, r),
                    on_error=lambda m: self._resume_api_request("_async_save_expense_response", self.save_expense, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_save_expense_response")
            if response and response.get('id'):
                self.accept()
            else:
                AlertDialog.error("Error", "Failed to save expense.", self)
        except ValueError as e:
            AlertDialog.warning("Validation Error", str(e), self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to save: {e}", self)

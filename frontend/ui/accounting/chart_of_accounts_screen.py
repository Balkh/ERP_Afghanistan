from PySide6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMessageBox, QHeaderView,
                               QAbstractItemView, QPushButton, QHBoxLayout, QFrame,
                               QComboBox, QLineEdit, QLabel)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, MARGIN_TOOLBAR)


class ChartOfAccountsScreen(QFrame):
    """Chart of Accounts with tree view and CRUD operations."""

    account_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.accounts = []
        self.setup_ui()
        self.load_accounts()

    def setup_ui(self):
        layout = self._setup_layout()

        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        self.tree = self._create_tree()
        layout.addWidget(self.tree)

        self._connect_signals()

    def _setup_layout(self):
        from PySide6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        header = QLabel("Chart of Accounts")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(header)

        return layout

    def _create_toolbar(self):
        toolbar = QFrame()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(SPACING_NONE, MARGIN_TOOLBAR, SPACING_NONE, MARGIN_TOOLBAR)

        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", "")
        for acc_type in ["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"]:
            self.type_filter.addItem(acc_type, acc_type)
        self.type_filter.setMaximumWidth(150)
        toolbar_layout.addWidget(QLabel("Type:"))
        toolbar_layout.addWidget(self.type_filter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search accounts...")
        self.search_input.setMaximumWidth(250)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addStretch()

        self.btn_add = QPushButton("Add Account")
        self.btn_edit = QPushButton("Edit")
        self.btn_delete = QPushButton("Delete")
        self.btn_refresh = QPushButton("Refresh")

        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)

        for btn in [self.btn_add, self.btn_edit, self.btn_delete, self.btn_refresh]:
            btn.setMinimumHeight(32)
            toolbar_layout.addWidget(btn)

        return toolbar

    def _create_tree(self):
        tree = QTreeWidget()
        tree.setHeaderLabels([
            "Code", "Account Name", "Type", "Category", "Balance", "Status"
        ])
        tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        tree.setSelectionMode(QAbstractItemView.SingleSelection)
        tree.setSortingEnabled(True)
        tree.setAlternatingRowColors(True)
        tree.itemSelectionChanged.connect(self._on_selection_changed)
        tree.itemDoubleClicked.connect(self._on_double_click)

        return tree

    def _connect_signals(self):
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_refresh.clicked.connect(self.load_accounts)
        self.search_input.textChanged.connect(self._filter_accounts)
        self.type_filter.currentTextChanged.connect(self._filter_accounts)

    def load_accounts(self):
        try:
            endpoint = get_endpoint("accounts")
            response = self.api_client.get(endpoint, params={"include_inactive": "true"})
            self.accounts = extract_list(response)
            self._populate_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load accounts: {e}")

    def _populate_tree(self):
        self.tree.clear()

        type_icons = {
            "ASSET": "💰",
            "LIABILITY": "📋",
            "EQUITY": "📊",
            "REVENUE": "📈",
            "EXPENSE": "📉",
        }

        root_nodes = {}

        for account in sorted(self.accounts, key=lambda x: x.get("code", "")):
            acc_type = account.get("account_type", "")
            if acc_type not in root_nodes:
                root_item = QTreeWidgetItem(self.tree)
                root_item.setText(0, acc_type)
                root_item.setText(1, f"{type_icons.get(acc_type, '')} {acc_type}")
                root_item.setExpanded(True)
                font = root_item.font(0)
                font.setBold(True)
                font.setPointSize(11)
                root_item.setFont(0, font)
                root_item.setFont(1, font)
                root_nodes[acc_type] = root_item

            parent_id = account.get("parent")
            parent_item = None

            if parent_id:
                parent_item = self.tree.findItems(str(parent_id), Qt.UserRole | Qt.MatchExactly, 0)
                if parent_item:
                    parent_item = parent_item[0].parent() or parent_item[0]

            if parent_item is None:
                parent_item = root_nodes.get(acc_type)

            if parent_item:
                item = QTreeWidgetItem(parent_item)
            else:
                item = QTreeWidgetItem(self.tree)

            item.setText(0, account.get("code", ""))
            item.setText(1, account.get("name", ""))
            item.setText(2, account.get("account_type", ""))
            item.setText(3, account.get("account_category", "") or "")
            item.setText(4, str(account.get("balance", "0.00")))
            item.setText(5, "Active" if account.get("is_active") else "Inactive")

            item.setData(0, Qt.UserRole, account.get("id"))
            item.setData(0, Qt.DisplayRole + 1000, account)

            if account.get("parent"):
                item.setExpanded(False)

    def _filter_accounts(self):
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentData()

        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            root.setHidden(False)

            for j in range(root.childCount()):
                child = root.child(j)
                account_data = child.data(0, Qt.DisplayRole + 1000) or {}

                matches_type = not type_filter or account_data.get("account_type") == type_filter
                matches_search = not search_text or (
                    search_text in account_data.get("code", "").lower() or
                    search_text in account_data.get("name", "").lower()
                )

                child.setHidden(not (matches_type and matches_search))

            has_visible_child = any(not root.child(j).isHidden() for j in range(root.childCount()))
            root.setHidden(not has_visible_child)

    def _on_selection_changed(self):
        selected = self.tree.selectedItems()
        self.btn_edit.setEnabled(bool(selected))
        self.btn_delete.setEnabled(bool(selected))
        if selected:
            acc_id = selected[0].data(0, Qt.UserRole)
            self.account_selected.emit(str(acc_id))

    def _on_double_click(self, item):
        self._on_edit()

    def _on_add(self):
        from ui.accounting.components.account_form_dialog import AccountFormDialog
        dialog = AccountFormDialog(self, api_client=self.api_client)
        if dialog.exec():
            self.load_accounts()

    def _on_edit(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        acc_id = selected[0].data(0, Qt.UserRole)
        if not acc_id:
            return

        from ui.accounting.components.account_form_dialog import AccountFormDialog
        dialog = AccountFormDialog(self, account_id=acc_id, api_client=self.api_client)
        if dialog.exec():
            self.load_accounts()

    def _on_delete(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        acc_id = selected[0].data(0, Qt.UserRole)
        if not acc_id:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this account?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.api_client.delete(f"/api/accounting/accounts/{acc_id}/")
                self.load_accounts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete account: {e}")

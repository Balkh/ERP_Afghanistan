from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLineEdit, QLabel, QFrame, QSizePolicy,
                              QComboBox, QMessageBox)
from PySide6.QtCore import Qt, Signal
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_LABEL,
                           COLOR_TEXT_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize

class BaseInventoryScreen(QWidget):
    """Base class for inventory management screens."""
    
    # Signals
    add_requested = Signal()
    edit_requested = Signal(object)  # item_id
    delete_requested = Signal(object)  # item_id
    refresh_requested = Signal()
    search_text_changed = Signal(str)
    filter_changed = Signal(str)
    
    def __init__(self, title="Inventory Screen"):
        super().__init__()
        self.setWindowTitle(title)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the base UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE,  MARGIN_PAGE,  MARGIN_PAGE,  MARGIN_PAGE)
        layout.setSpacing(SPACING_SM + SPACING_XS)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel(self.windowTitle())
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Search bar
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.textChanged.connect(self.search_text_changed.emit)
        
        # Filter bar
        filter_label = QLabel("Filter:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All", "")
        # Subclasses should populate filter options
        self.populate_filter_options()
        self.filter_combo.currentTextChanged.connect(
            lambda text: self.filter_changed.emit(self.filter_combo.currentData())
        )
        
        header_layout.addWidget(search_label)
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(filter_label)
        header_layout.addWidget(self.filter_combo)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Button bar
        button_layout = QHBoxLayout()
        self.add_button = EnterpriseButton(text="Add", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.edit_button = EnterpriseButton(text="Edit", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.delete_button = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.refresh_button = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        
        self.add_button.clicked.connect(self.add_requested.emit)
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Table placeholder - subclasses will set their own table
        self.table_frame = QFrame()
        self.table_frame.setFrameStyle(QFrame.StyledPanel)
        self.table_layout = QVBoxLayout(self.table_frame)
        layout.addWidget(self.table_frame, 1)  # Take remaining space
        
        # Initially disable edit/delete buttons
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
    
    def populate_filter_options(self):
        """Subclasses should override to populate filter options."""
        pass
    
    def _on_edit_clicked(self):
        """Handle edit button click."""
        if hasattr(self, 'table'):
            selected_rows = self.table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                item = self.table.item(row, 0)
                if item is not None:
                    item_id = item.text()
                    self.edit_requested.emit(item_id)
    
    def _on_delete_clicked(self):
        """Handle delete button click."""
        if hasattr(self, 'table'):
            selected_rows = self.table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                item = self.table.item(row, 0)
                if item is not None:
                    item_id = item.text()
                    self.delete_requested.emit(item_id)
    
    def set_table_widget(self, widget):
        """Set the table widget for this screen."""
        # Clear existing layout
        while self.table_layout.count():
            item = self.table_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.table_layout.addWidget(widget)
    
    def set_selection_enabled(self, enabled):
        """Enable or disable edit/delete buttons based on selection."""
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
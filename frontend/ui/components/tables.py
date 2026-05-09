"""
Enterprise Table Component.
Professional data table with sorting, filtering, and pagination.
"""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QComboBox
)
from PySide6.QtCore import Signal, Qt, QModelIndex, QSortFilterProxyModel, QTimer
from PySide6.QtGui import QColor, QFont
from typing import List, Dict, Any, Callable, Optional, Tuple
from enum import Enum
from ui.constants import SPACING_XS


class TableSelectionMode(Enum):
    """Table selection modes."""
    SINGLE = "single"
    MULTI = "multi"
    EXTENDED = "extended"
    NONE = "none"


class TableColumn:
    """Table column definition."""
    
    def __init__(
        self,
        key: str,
        title: str,
        width: int = 100,
        align: str = "left",
        sortable: bool = True,
        filterable: bool = True,
        format_func: Optional[Callable] = None
    ):
        self.key = key
        self.title = title
        self.width = width
        self.align = align  # "left", "center", "right"
        self.sortable = sortable
        self.filterable = filterable
        self.format_func = format_func


class EnterpriseTable(QTableWidget):
    """
    Enterprise-grade data table with advanced features.
    """
    
    # Signals
    row_selected = Signal(int, object)
    row_double_clicked = Signal(int, object)
    selection_changed = Signal(list)
    sort_changed = Signal(str, str)  # column, order
    filter_changed = Signal(dict)
    data_requested = Signal(int, int)  # page, page_size
    
    def __init__(
        self,
        columns: List[TableColumn],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._columns = columns
        self._data: List[Dict] = []
        self._filtered_data: List[Dict] = []
        self._current_sort_column: str = ""
        self._current_sort_order: str = "asc"
        self._selection_mode = TableSelectionMode.MULTI
        self._page = 1
        self._page_size = 50
        self._total_count = 0
        self._enable_pagination = True
        self._enable_sorting = True
        self._enable_filtering = True
        
        self._setup_table()
        
    def _setup_table(self):
        """Setup table properties."""
        # Set column count
        self.setColumnCount(len(self._columns))
        
        # Set headers
        headers = [col.title for col in self._columns]
        self.setHorizontalHeaderLabels(headers)
        
        # Configure horizontal header
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Set column properties
        for i, col in enumerate(self._columns):
            self.setColumnWidth(i, col.width)
            
            # Apply alignment
            alignment = {
                'left': Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                'center': Qt.AlignmentFlag.AlignCenter,
                'right': Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            }.get(col.align, Qt.AlignmentFlag.AlignLeft)
            
            if col.sortable:
                header.setSortIndicatorShown(True)
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                
        # Configure vertical header
        self.verticalHeader().setVisible(True)
        self.verticalHeader().setDefaultSectionSize(30)
        
        # Set selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(self._get_selection_mode())
        
        # Enable alternating row colors
        self.setAlternatingRowColors(True)
        
        # Enable sorting
        if self._enable_sorting:
            self.setSortingEnabled(True)
            self.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)
            
        # Connect signals
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Set table properties
        self.setShowGrid(True)
        self.setCornerButtonEnabled(True)
        self.setWordWrap(False)
        
    def _get_selection_mode(self) -> QAbstractItemView.SelectionMode:
        """Get Qt selection mode from TableSelectionMode."""
        modes = {
            TableSelectionMode.SINGLE: QAbstractItemView.SelectionMode.SingleSelection,
            TableSelectionMode.MULTI: QAbstractItemView.SelectionMode.MultiSelection,
            TableSelectionMode.EXTENDED: QAbstractItemView.SelectionMode.ExtendedSelection,
            TableSelectionMode.NONE: QAbstractItemView.SelectionMode.NoSelection
        }
        return modes.get(self._selection_mode, QAbstractItemView.SelectionMode.ExtendedSelection)
        
    def set_data(self, data: List[Dict], total_count: Optional[int] = None):
        """Set table data."""
        self._data = data
        self._filtered_data = data
        
        if total_count is not None:
            self._total_count = total_count
        else:
            self._total_count = len(data)
            
        self._refresh_display()
        
    def _refresh_display(self):
        """Refresh table display."""
        self.blockSignals(True)
        self.setRowCount(0)
        
        for row_idx, row_data in enumerate(self._filtered_data):
            self.insertRow(row_idx)
            
            for col_idx, col in enumerate(self._columns):
                value = row_data.get(col.key, "")
                
                # Apply format function if provided
                if col.format_func:
                    display_value = col.format_func(value)
                else:
                    display_value = str(value) if value is not None else ""
                    
                item = QTableWidgetItem(display_value)
                
                # Apply alignment
                alignment = {
                    'left': Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    'center': Qt.AlignmentFlag.AlignCenter,
                    'right': Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                }.get(col.align, Qt.AlignmentFlag.AlignLeft)
                
                item.setTextAlignment(alignment)
                
                # Store row data reference
                item.setData(Qt.ItemDataRole.UserRole, row_data)
                
                self.setItem(row_idx, col_idx, item)
                
        self.blockSignals(False)
        
    def set_selection_mode(self, mode: TableSelectionMode):
        """Set selection mode."""
        self._selection_mode = mode
        self.setSelectionMode(self._get_selection_mode())
        
    def get_selected_rows(self) -> List[int]:
        """Get selected row indices."""
        return [index.row() for index in self.selectedIndexes()]
        
    def get_selected_data(self) -> List[Dict]:
        """Get selected row data."""
        selected_data = []
        for row in self.get_selected_rows():
            if 0 <= row < len(self._filtered_data):
                selected_data.append(self._filtered_data[row])
        return selected_data
        
    def get_row_data(self, row: int) -> Optional[Dict]:
        """Get data for specific row."""
        if 0 <= row < len(self._filtered_data):
            return self._filtered_data[row]
        return None
        
    def clear_selection(self):
        """Clear table selection."""
        self.clearSelection()
        
    def select_row(self, row: int):
        """Select specific row."""
        if 0 <= row < self.rowCount():
            self.selectRow(row)
            
    def select_all(self):
        """Select all rows."""
        self.selectAll()
        
    def sort_by_column(self, column_key: str, order: str = "asc"):
        """Sort table by column."""
        for i, col in enumerate(self._columns):
            if col.key == column_key:
                sort_order = Qt.SortOrder.AscendingOrder if order == "asc" else Qt.SortOrder.DescendingOrder
                self.sortByColumn(i, sort_order)
                break
                
    def filter_data(self, filters: Dict[str, Any]):
        """Apply filters to data."""
        self._filtered_data = self._data.copy()
        
        for key, value in filters.items():
            if value:
                self._filtered_data = [
                    row for row in self._filtered_data
                    if str(row.get(key, "")).lower().find(str(value).lower()) >= 0
                ]
                
        self._refresh_display()
        self.filter_changed.emit(filters)
        
    def clear_filters(self):
        """Clear all filters."""
        self._filtered_data = self._data.copy()
        self._refresh_display()
        
    def set_page_size(self, page_size: int):
        """Set page size for pagination."""
        self._page_size = page_size
        self._refresh_display()
        
    def get_pagination_info(self) -> Dict[str, Any]:
        """Get pagination info."""
        total_pages = (self._total_count + self._page_size - 1) // self._page_size
        return {
            'current_page': self._page,
            'total_pages': total_pages,
            'page_size': self._page_size,
            'total_count': self._total_count,
            'has_next': self._page < total_pages,
            'has_previous': self._page > 1
        }
        
    def _on_selection_changed(self):
        """Handle selection change."""
        selected_rows = self.get_selected_rows()
        selected_data = self.get_selected_data()
        
        self.selection_changed.emit(selected_data)
        
        if selected_data:
            self.row_selected.emit(selected_rows[0], selected_data[0])
            
    def _on_item_double_clicked(self, item: QTableWidgetItem):
        """Handle item double click."""
        row = item.row()
        if 0 <= row < len(self._filtered_data):
            self.row_double_clicked.emit(row, self._filtered_data[row])
            
    def _on_sort_changed(self, column: int, order: Qt.SortOrder):
        """Handle sort change."""
        if 0 <= column < len(self._columns):
            col = self._columns[column]
            sort_order = "asc" if order == Qt.SortOrder.AscendingOrder else "desc"
            self._current_sort_column = col.key
            self._current_sort_order = sort_order
            self.sort_changed.emit(col.key, sort_order)
            
    def set_column_visibility(self, column_key: str, visible: bool):
        """Set column visibility."""
        for i, col in enumerate(self._columns):
            if col.key == column_key:
                self.setColumnHidden(i, not visible)
                break
                
    def resizeColumnsToContents(self):
        """Resize columns to fit contents."""
        self.resizeColumnsToContents()
        
    def resizeColumnsToSection(self):
        """Resize columns to section size."""
        for i in range(self.columnCount()):
            self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)


class PaginationWidget(QWidget):
    """
    Pagination controls for table.
    """
    
    page_changed = Signal(int)
    page_size_changed = Signal(int)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup pagination UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)
        
        # Info label
        self.info_label = QLabel("Page 1 of 1 (0 items)")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        # Page size selector
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "25", "50", "100"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        layout.addWidget(QLabel("Per page:"))
        layout.addWidget(self.page_size_combo)
        
        # Navigation buttons
        self.first_btn = QPushButton("<<")
        self.prev_btn = QPushButton("<")
        self.next_btn = QPushButton(">")
        self.last_btn = QPushButton(">>")
        
        self.first_btn.clicked.connect(lambda: self.page_changed.emit(1))
        self.prev_btn.clicked.connect(self._on_prev_page)
        self.next_btn.clicked.connect(self._on_next_page)
        self.last_btn.clicked.connect(self._on_last_page)
        
        layout.addWidget(self.first_btn)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.last_btn)
        
    def update_pagination(self, current_page: int, total_pages: int, total_count: int):
        """Update pagination display."""
        self.info_label.setText(
            f"Page {current_page} of {total_pages} ({total_count} items)"
        )
        
        self.first_btn.setEnabled(current_page > 1)
        self.prev_btn.setEnabled(current_page > 1)
        self.next_btn.setEnabled(current_page < total_pages)
        self.last_btn.setEnabled(current_page < total_pages)
        
    def _on_page_size_changed(self, text: str):
        """Handle page size change."""
        try:
            self.page_size_changed.emit(int(text))
        except ValueError:
            pass
            
    def _on_prev_page(self):
        """Go to previous page."""
        # This should be connected to current page - 1
        pass
        
    def _on_next_page(self):
        """Go to next page."""
        pass
        
    def _on_last_page(self):
        """Go to last page."""
        pass
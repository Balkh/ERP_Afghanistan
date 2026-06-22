"""
Enterprise Table Component.
Professional data table with sorting, filtering, and pagination.
"""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QWidget, QHBoxLayout, QLabel, QComboBox
)
from PySide6.QtCore import Signal, Qt
from typing import List, Dict, Any, Callable, Optional, Tuple
from enum import Enum
from ui.constants import (
    SPACING_XS, BORDER_RADIUS_SM, TABLE_ROW_HEIGHT_COMPACT,
    TABLE_ROW_HEIGHT_MD, TABLE_ROW_HEIGHT_RELAXED,
    TABLE_BG_PRIMARY, TABLE_BG_SECONDARY, TABLE_BG_HOVER,
    TABLE_BG_SELECTED, TABLE_GRID_COLOR,
    TABLE_TEXT_PRIMARY, TABLE_TEXT_MUTED, TABLE_TEXT_SELECTED, TABLE_HEADER_BG,
    TABLE_HEADER_TEXT, TABLE_SCROLLBAR_BG, TABLE_SCROLLBAR_HANDLE, TEXT_TABLE,
    TEXT_TABLE_HEADER, COLOR_BORDER,
    COLOR_BORDER_INPUT_HOVER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize


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
        self.align = align
        self.sortable = sortable
        self.filterable = filterable
        self.format_func = format_func


def build_table_stylesheet(
    bg_primary: str = TABLE_BG_PRIMARY,
    bg_secondary: str = TABLE_BG_SECONDARY,
    bg_hover: str = TABLE_BG_HOVER,
    bg_selected: str = TABLE_BG_SELECTED,
    grid_color: str = TABLE_GRID_COLOR,
    text_primary: str = TABLE_TEXT_PRIMARY,
    text_muted: str = TABLE_TEXT_MUTED,
    text_selected: str = TABLE_TEXT_SELECTED,
    header_bg: str = TABLE_HEADER_BG,
    header_text: str = TABLE_HEADER_TEXT,
    scrollbar_bg: str = TABLE_SCROLLBAR_BG,
    scrollbar_handle: str = TABLE_SCROLLBAR_HANDLE,
    border_radius: int = BORDER_RADIUS_SM,
    focus_color: str = "",
) -> str:
    """
    Deprecated: use UIStyleBuilder.get_table_style() instead.
    Delegates to UIStyleBuilder.get_table_style().
    """
    from theme.style_builder import UIStyleBuilder
    return UIStyleBuilder.get_table_style()


def ensure_contrast(fg: str, bg: str, threshold: float = 4.5) -> Tuple[str, bool]:
    """
    Validate WCAG contrast ratio between fg and bg.
    Returns (color, passed) where color is corrected if below threshold.
    """
    def _relative_luminance(hex_color: str) -> float:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return 0.0
        r, g, b = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _luminance(hex_color: str) -> float:
        val = _relative_luminance(hex_color)
        return val

    l1 = _luminance(fg)
    l2 = _luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)

    if ratio >= threshold:
        return fg, True

    # Correct: if fg is too light on light bg, darken it
    # These use COLOR_TEXT_PRIMARY and COLOR_BG_SURFACE token-based
    # fallbacks instead of raw hex values.
    if l1 > l2:
        return COLOR_TEXT_PRIMARY, False
    else:
        return COLOR_TEXT_MUTED, False


def _looks_numeric(value: str) -> bool:
    """Check if a display value looks numeric (for auto-alignment)."""
    if not value:
        return False
    stripped = value.strip().replace(",", "").replace(".", "").replace("-", "").replace(" ", "")
    return stripped.isdigit() and len(stripped) > 0


class EnterpriseTable(QTableWidget):
    """
    Enterprise-grade data table with advanced features.

    Density tiers:
    - "compact" (26px): Financial tables, dense numerical data
    - "medium" (32px): Standard operational tables (default)
    - "relaxed" (40px): Touch/kiosk interfaces
    """

    # Signals
    row_selected = Signal(int, object)
    row_double_clicked = Signal(int, object)
    selection_changed = Signal(list)
    sort_changed = Signal(str, str)
    filter_changed = Signal(dict)
    data_requested = Signal(int, int)

    MAX_ROWS_WITHOUT_CHUNKING = 2000
    MAX_SAFE_ROWS = 50000

    DENSITY_HEIGHTS = {
        "compact": TABLE_ROW_HEIGHT_COMPACT,
        "medium": TABLE_ROW_HEIGHT_MD,
        "relaxed": TABLE_ROW_HEIGHT_RELAXED,
    }

    HEADER_HEIGHTS = {
        "compact": 28,
        "medium": 32,
        "relaxed": 38,
    }

    def __init__(
        self,
        columns: List[TableColumn],
        density: str = "medium",
        empty_state_text: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._columns = columns
        self._density = density
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
        self._empty_state_text = empty_state_text
        self._double_click_guard_ts: float = 0.0
        self._double_click_guard_interval: float = 0.3

        self._setup_table()

    def _build_stylesheet(self) -> str:
        """Build canonical stylesheet from centralized UIStyleBuilder."""
        from theme.style_builder import UIStyleBuilder
        return UIStyleBuilder.get_table_style()

    def _setup_table(self):
        """Setup table properties and apply canonical stylesheet."""
        self.setColumnCount(len(self._columns))

        headers = [col.title for col in self._columns]
        self.setHorizontalHeaderLabels(headers)

        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        for i, col in enumerate(self._columns):
            self.setColumnWidth(i, col.width)
            if col.sortable:
                header.setSortIndicatorShown(True)
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self.verticalHeader().setVisible(True)
        self._apply_density()

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(self._get_selection_mode())
        self.setAlternatingRowColors(True)

        if self._enable_sorting:
            self.setSortingEnabled(True)
            self.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setShowGrid(True)
        self.setCornerButtonEnabled(True)
        self.setWordWrap(False)

        self.setStyleSheet(self._build_stylesheet())

    def _get_selection_mode(self) -> QAbstractItemView.SelectionMode:
        modes = {
            TableSelectionMode.SINGLE: QAbstractItemView.SelectionMode.SingleSelection,
            TableSelectionMode.MULTI: QAbstractItemView.SelectionMode.MultiSelection,
            TableSelectionMode.EXTENDED: QAbstractItemView.SelectionMode.ExtendedSelection,
            TableSelectionMode.NONE: QAbstractItemView.SelectionMode.NoSelection,
        }
        return modes.get(self._selection_mode, QAbstractItemView.SelectionMode.ExtendedSelection)

    def _apply_density(self):
        height = self.DENSITY_HEIGHTS.get(self._density, TABLE_ROW_HEIGHT_MD)
        self.verticalHeader().setDefaultSectionSize(height)
        header_height = self.HEADER_HEIGHTS.get(self._density, 32)
        self.horizontalHeader().setFixedHeight(header_height)

    def set_density(self, density: str):
        if density in self.DENSITY_HEIGHTS:
            self._density = density
            self._apply_density()

    @property
    def density(self) -> str:
        return self._density

    def set_data(self, data: List[Dict], total_count: Optional[int] = None):
        import time as _time
        _st = _time.time()
        
        # Row count safety: warn on large datasets, force chunking if excessive
        if len(data) > self.MAX_SAFE_ROWS:
            import logging
            logging.getLogger(__name__).warning(
                f"EnterpriseTable received {len(data)} rows (max safe: {self.MAX_SAFE_ROWS}). "
                "Consider server-side pagination."
            )
            data = data[:self.MAX_SAFE_ROWS]
        
        self._data = data
        self._filtered_data = data
        if total_count is not None:
            self._total_count = total_count
        else:
            self._total_count = len(data)
        
        # Auto-chunk large datasets to prevent UI freeze
        if len(data) > self.MAX_ROWS_WITHOUT_CHUNKING:
            self.set_data_chunked(data)
        else:
            self._refresh_display()
        
        _dur = (_time.time() - _st) * 1000
        from runtime.ux_telemetry import record_table_render
        record_table_render(len(data), _dur)

    def set_data_deferred(self, data: List[Dict], total_count: Optional[int] = None):
        """Load data on next event-loop cycle — keeps UI responsive."""
        from runtime.deferred_renderer import defer
        defer(self.set_data, data, total_count)

    def set_data_chunked(self, data: List[Dict], chunk_size: int = 50):
        """Load large datasets in chunks to avoid UI freeze."""
        existing_timer = getattr(self, '_chunk_timer', None)
        if existing_timer is not None and existing_timer.isActive():
            existing_timer.stop()
            existing_timer.deleteLater()
            self._chunk_timer = None
        if len(data) <= chunk_size:
            self.set_data(data)
            return
        self.blockSignals(True)
        self.setRowCount(0)
        self._data = data
        self._filtered_data = data
        self._total_count = len(data)
        self._chunk_index = 0
        self._chunk_size = chunk_size
        from PySide6.QtCore import QTimer
        self._chunk_timer = QTimer(self)
        self._chunk_timer.timeout.connect(self._render_next_chunk)
        self._chunk_timer.start(5)

    def _render_next_chunk(self):
        end = min(self._chunk_index + self._chunk_size, len(self._filtered_data))
        for row_idx in range(self._chunk_index, end):
            row_data = self._filtered_data[row_idx]
            self.insertRow(row_idx)
            for col_idx, col in enumerate(self._columns):
                value = row_data.get(col.key, "")
                if col.format_func:
                    display_value = col.format_func(value)
                else:
                    display_value = str(value) if value is not None else ""
                item = QTableWidgetItem(display_value)
                if col.align == "right" or _looks_numeric(display_value):
                    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                elif col.align == "center":
                    align = Qt.AlignmentFlag.AlignCenter
                else:
                    align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                item.setTextAlignment(align)
                item.setData(Qt.ItemDataRole.UserRole, row_data)
                self.setItem(row_idx, col_idx, item)
        self._chunk_index = end
        if self._chunk_index >= len(self._filtered_data):
            self._chunk_timer.stop()
            self._chunk_timer.deleteLater()
            self._chunk_timer = None
            self.blockSignals(False)

    def _refresh_display(self):
        self.blockSignals(True)
        self.setRowCount(0)

        for row_idx, row_data in enumerate(self._filtered_data):
            self.insertRow(row_idx)
            for col_idx, col in enumerate(self._columns):
                value = row_data.get(col.key, "")
                if col.format_func:
                    display_value = col.format_func(value)
                else:
                    display_value = str(value) if value is not None else ""

                item = QTableWidgetItem(display_value)
                # Numeric auto-detect: right-align numeric-like values
                if col.align == "right" or _looks_numeric(display_value):
                    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                elif col.align == "center":
                    align = Qt.AlignmentFlag.AlignCenter
                else:
                    align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                item.setTextAlignment(align)
                item.setData(Qt.ItemDataRole.UserRole, row_data)
                self.setItem(row_idx, col_idx, item)

        self.blockSignals(False)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            rows = self.get_selected_rows()
            if rows:
                row = rows[0]
                data = self.get_row_data(row)
                if data is not None:
                    self.row_double_clicked.emit(row, data)
            return
        super().keyPressEvent(event)

    def set_selection_mode(self, mode: TableSelectionMode):
        self._selection_mode = mode
        self.setSelectionMode(self._get_selection_mode())

    def get_selected_rows(self) -> List[int]:
        rows = set()
        for index in self.selectedIndexes():
            rows.add(index.row())
        return sorted(rows)

    def get_selected_data(self) -> List[Dict]:
        selected_data = []
        for row in self.get_selected_rows():
            if 0 <= row < len(self._filtered_data):
                selected_data.append(self._filtered_data[row])
        return selected_data

    def get_row_data(self, row: int) -> Optional[Dict]:
        if 0 <= row < len(self._filtered_data):
            return self._filtered_data[row]
        return None

    def clear_selection(self):
        self.clearSelection()

    def select_row(self, row: int):
        if 0 <= row < self.rowCount():
            self.selectRow(row)

    def select_all(self):
        self.selectAll()

    def sort_by_column(self, column_key: str, order: str = "asc"):
        for i, col in enumerate(self._columns):
            if col.key == column_key:
                sort_order = Qt.SortOrder.AscendingOrder if order == "asc" else Qt.SortOrder.DescendingOrder
                self.sortByColumn(i, sort_order)
                break

    def filter_data(self, filters: Dict[str, Any]):
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
        self._filtered_data = self._data.copy()
        self._refresh_display()

    def set_page_size(self, page_size: int):
        self._page_size = page_size
        self._refresh_display()

    def get_pagination_info(self) -> Dict[str, Any]:
        total_pages = max(1, (self._total_count + self._page_size - 1) // self._page_size)
        return {
            'current_page': self._page,
            'total_pages': total_pages,
            'page_size': self._page_size,
            'total_count': self._total_count,
            'has_next': self._page < total_pages,
            'has_previous': self._page > 1,
        }

    def _on_selection_changed(self):
        selected_rows = self.get_selected_rows()
        selected_data = self.get_selected_data()
        self.selection_changed.emit(selected_data)
        if selected_data:
            self.row_selected.emit(selected_rows[0], selected_data[0])

    def _on_item_double_clicked(self, item: QTableWidgetItem):
        import time as _time
        now = _time.time()
        if now - self._double_click_guard_ts < self._double_click_guard_interval:
            return
        self._double_click_guard_ts = now
        
        row = item.row()
        if 0 <= row < len(self._filtered_data):
            self.row_double_clicked.emit(row, self._filtered_data[row])

    def _on_sort_changed(self, column: int, order: Qt.SortOrder):
        if 0 <= column < len(self._columns):
            col = self._columns[column]
            sort_order = "asc" if order == Qt.SortOrder.AscendingOrder else "desc"
            self._current_sort_column = col.key
            self._current_sort_order = sort_order
            self.sort_changed.emit(col.key, sort_order)

    def set_column_visibility(self, column_key: str, visible: bool):
        for i, col in enumerate(self._columns):
            if col.key == column_key:
                self.setColumnHidden(i, not visible)
                break

    def resizeColumnsToContents(self):
        super().resizeColumnsToContents()

    def resizeColumnsToSection(self):
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

        self._current_page = 1
        self._total_pages = 1
        self._total_count = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)

        self.info_label = QLabel("Page 1 of 1 (0 items)")
        layout.addWidget(self.info_label)

        layout.addStretch()

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "25", "50", "100"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        layout.addWidget(QLabel("Per page:"))
        layout.addWidget(self.page_size_combo)

        self.first_btn = EnterpriseButton("<<", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self.prev_btn = EnterpriseButton("<", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self.next_btn = EnterpriseButton(">", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self.last_btn = EnterpriseButton(">>", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)

        self.first_btn.clicked.connect(lambda: self.page_changed.emit(1))
        self.prev_btn.clicked.connect(self._on_prev_page)
        self.next_btn.clicked.connect(self._on_next_page)
        self.last_btn.clicked.connect(self._on_last_page)

        layout.addWidget(self.first_btn)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.last_btn)

    def update_pagination(self, current_page: int, total_pages: int, total_count: int):
        self._current_page = current_page
        self._total_pages = total_pages
        self._total_count = total_count

        self.info_label.setText(
            f"Page {current_page} of {total_pages} ({total_count} items)"
        )

        self.first_btn.setEnabled(current_page > 1)
        self.prev_btn.setEnabled(current_page > 1)
        self.next_btn.setEnabled(current_page < total_pages)
        self.last_btn.setEnabled(current_page < total_pages)

    def _on_page_size_changed(self, text: str):
        try:
            self.page_size_changed.emit(int(text))
        except ValueError:
            pass

    def _on_prev_page(self):
        if self._current_page > 1:
            self.page_changed.emit(self._current_page - 1)

    def _on_next_page(self):
        if self._current_page < self._total_pages:
            self.page_changed.emit(self._current_page + 1)

    def _on_last_page(self):
        self.page_changed.emit(self._total_pages)


class DataEntryGrid(QTableWidget):
    """
    Lightweight editable ERP grid.

    Standardized QTableWidget wrapper for interactive line-item data entry.
    Uses the same canonical table stylesheet as EnterpriseTable.

    Supports both text-only cells (via add_row/set_row_values) and
    widget cells (via set_cell_widget/cell_widget) for combo boxes,
    spin boxes, and action buttons.

    Signals:
        cell_value_changed(int, int, object) — emitted when cell text or widget value changes
        row_added(int) — emitted after a row is inserted
        row_removed(int) — emitted before a row is removed
    """

    cell_value_changed = Signal(int, int, object)
    row_added = Signal(int)
    row_removed = Signal(int)

    def __init__(self, columns: List, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._column_keys = []
        self._row_data: Dict[int, Dict[str, Any]] = {}
        self._widget_signal_handlers: Dict[tuple, Any] = {}
        headers = []
        for col in columns:
            if isinstance(col, (list, tuple)):
                headers.append(col[0])
                self._column_keys.append(len(self._column_keys))
            else:
                headers.append(str(col))
                self._column_keys.append(len(self._column_keys))

        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT_MD)
        self.setStyleSheet(self._build_stylesheet())
        self.cellChanged.connect(self._on_cell_text_changed)

    def _build_stylesheet(self) -> str:
        from theme.style_builder import UIStyleBuilder
        return UIStyleBuilder.get_table_style()

    def _on_cell_text_changed(self, row: int, col: int):
        item = self.item(row, col)
        value = item.text() if item else None
        self.cell_value_changed.emit(row, col, value)

    def _disconnect_widget_handler(self, row: int, col: int):
        key = (row, col)
        handler = self._widget_signal_handlers.pop(key, None)
        widget = self.cellWidget(row, col)
        if handler is not None and widget is not None:
            for sig_name in ("valueChanged", "currentIndexChanged", "textChanged", "stateChanged"):
                sig = getattr(widget, sig_name, None)
                if sig is not None:
                    try:
                        sig.disconnect(handler)
                    except (RuntimeError, TypeError):
                        pass

    def add_remove_column(self, header: str = "") -> int:
        col = self.columnCount()
        self.setColumnCount(col + 1)
        self.setHorizontalHeaderItem(col, QTableWidgetItem(header or "Remove"))
        return col

    def add_row(self, values: Optional[List[str]] = None) -> int:
        row = self.rowCount()
        self.insertRow(row)
        if values:
            for col, val in enumerate(values):
                if col < self.columnCount():
                    item = QTableWidgetItem(str(val))
                    self.setItem(row, col, item)
        self.row_added.emit(row)
        return row

    def remove_row(self, row: int) -> None:
        if row < 0 or row >= self.rowCount():
            return
        for col in range(self.columnCount()):
            self._disconnect_widget_handler(row, col)
        self._row_data.pop(row, None)
        self.row_removed.emit(row)
        self.removeRow(row)
        for r in sorted(self._row_data.keys()):
            if r > row:
                self._row_data[r - 1] = self._row_data.pop(r)

    def get_row_values(self, row: int) -> List[str]:
        return [
            self.item(row, col).text() if self.item(row, col) else ""
            for col in range(self.columnCount())
        ]

    def set_row_values(self, row: int, values: List[str]) -> None:
        for col, val in enumerate(values):
            if col < self.columnCount():
                item = self.item(row, col)
                if item:
                    item.setText(str(val))
                else:
                    self.setItem(row, col, QTableWidgetItem(str(val)))

    def set_cell_widget(self, row: int, col: int, widget: QWidget) -> None:
        if row < 0 or col < 0 or row >= self.rowCount() or col >= self.columnCount():
            return
        self._disconnect_widget_handler(row, col)

        def _make_handler(r, c, w):
            def _handler(*args):
                for sig_name in ("value", "currentText", "text", "isChecked"):
                    getter = getattr(w, sig_name, None)
                    if callable(getter):
                        try:
                            value = getter()
                        except Exception:
                            value = None
                        self.cell_value_changed.emit(r, c, value)
                        return
            return _handler

        handler = _make_handler(row, col, widget)
        self._widget_signal_handlers[(row, col)] = handler
        connected = False
        for sig_name in ("valueChanged", "currentIndexChanged", "textChanged", "stateChanged", "toggled"):
            sig = getattr(widget, sig_name, None)
            if sig is not None:
                try:
                    sig.connect(handler)
                    connected = True
                    break
                except (RuntimeError, TypeError):
                    continue
        self.setCellWidget(row, col, widget)

    def cell_widget(self, row: int, col: int) -> Optional[QWidget]:
        if row < 0 or col < 0 or row >= self.rowCount() or col >= self.columnCount():
            return None
        return self.cellWidget(row, col)

    def set_row_data(self, row: int, data: Dict[str, Any]) -> None:
        if row < 0 or row >= self.rowCount():
            return
        self._row_data[row] = dict(data)

    def get_row_data(self, row: int) -> Dict[str, Any]:
        if row < 0 or row >= self.rowCount():
            return {}
        return dict(self._row_data.get(row, {}))

    def clear_all_rows(self) -> None:
        for row in range(self.rowCount() - 1, -1, -1):
            self.remove_row(row)

    def set_row_height(self, row: int, height: int) -> None:
        if 0 <= row < self.rowCount():
            self.setRowHeight(row, height)

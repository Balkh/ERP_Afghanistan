from typing import Dict, Any, Optional

from ui.constants import (
    SPACING_NONE, SPACING_2XS, SPACING_XS, SPACING_SM, SPACING_MD,
    SPACING_LG, SPACING_XL,
    BORDER_RADIUS_MD, BORDER_RADIUS_LG,
    COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY,
    FONT_NAME_PRIMARY,
    TEXT_BODY, TEXT_LABEL, TEXT_SECTION_TITLE,
    COLOR_BG_MAIN, COLOR_BG_INPUT, COLOR_TABLE_ALT, COLOR_TEXT_SECONDARY,
    COLOR_BORDER_FOCUS,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QWidget,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor


class SearchPalette(QFrame):
    """Ctrl+K global search overlay — frameless popup with fuzzy matching."""

    navigate_requested = Signal(str, int)  # page_id, page_index

    def __init__(self, search_index: Optional[Dict[str, tuple]] = None, parent=None):
        super().__init__(parent)
        self._search_index = search_index or {}
        self._filtered_items: list[tuple[str, str, int]] = []
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)
        self._debounce_timer.timeout.connect(self._perform_search)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            SearchPalette {{
                background-color: rgba(0, 0, 0, 140);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_NONE, SPACING_NONE, SPACING_NONE, SPACING_NONE)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._container = QFrame(self)
        self._container.setFixedSize(500, 400)
        self._container.setStyleSheet(f"""
            QFrame#paletteContainer {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG}px;
            }}
        """)
        self._container.setObjectName("paletteContainer")

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(SPACING_NONE, SPACING_NONE, SPACING_NONE, SPACING_NONE)
        container_layout.setSpacing(SPACING_NONE)

        self._search_input = QLineEdit(self._container)
        self._search_input.setPlaceholderText("Search screens, records...  (Ctrl+K)")
        self._search_input.setClearButtonEnabled(True)
        font = QFont(FONT_NAME_PRIMARY, TEXT_SECTION_TITLE)
        self._search_input.setFont(font)
        self._search_input.setMinimumHeight(48)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BG_INPUT};
                color: {COLOR_TEXT_PRIMARY};
                border: none;
                border-bottom: 1px solid {COLOR_BORDER};
                border-top-left-radius: {BORDER_RADIUS_LG}px;
                border-top-right-radius: {BORDER_RADIUS_LG}px;
                padding: {SPACING_SM}px {SPACING_LG}px;
                selection-background-color: {COLOR_PRIMARY};
                selection-color: {COLOR_BG_MAIN};
            }}
            QLineEdit:focus {{
                border-bottom: 2px solid {COLOR_BORDER_FOCUS};
            }}
        """)
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self._on_return_pressed)

        container_layout.addWidget(self._search_input)

        self._results_list = QListWidget(self._container)
        self._results_list.setFont(QFont(FONT_NAME_PRIMARY, TEXT_BODY))
        self._results_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                border: none;
                border-bottom-left-radius: {BORDER_RADIUS_LG}px;
                border-bottom-right-radius: {BORDER_RADIUS_LG}px;
                outline: none;
                padding: {SPACING_XL}px;
            }}
            QListWidget::item {{
                padding: {SPACING_SM}px {SPACING_MD}px;
                border-radius: {BORDER_RADIUS_MD}px;
                min-height: 40px;
            }}
            QListWidget::item:selected {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_PRIMARY};
            }}
            QListWidget::item:hover {{
                background-color: {COLOR_BG_SURFACE};
            }}
            QListWidget::item:alternate {{
                background-color: {COLOR_TABLE_ALT};
            }}
        """)
        self._results_list.setAlternatingRowColors(True)
        self._results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._results_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self._results_list.itemClicked.connect(self._on_item_clicked)

        container_layout.addWidget(self._results_list, 1)

        layout.addWidget(self._container)

    def show(self):
        super().show()
        self._search_input.setFocus()
        self._results_list.clear()
        self._filtered_items = []
        if self._search_input.text():
            self._search_input.selectAll()
        self._center_on_parent()

    def set_search_index(self, search_index: Dict[str, tuple]):
        self._search_index = search_index

    def _center_on_parent(self):
        parent = self.parentWidget()
        if parent:
            parent_rect = parent.rect()
            x = parent_rect.center().x() - self._container.width() // 2
            y = parent_rect.center().y() - self._container.height() // 2
            self._container.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_on_parent()

    def _on_text_changed(self, text: str):
        self._debounce_timer.stop()
        if text:
            self._debounce_timer.start()
        else:
            self._results_list.clear()
            self._filtered_items = []

    def _perform_search(self):
        query = self._search_input.text()
        matches = []
        for display_name, (page_id, page_index) in self._search_index.items():
            score = self._fuzzy_score(display_name, query)
            if score > 0:
                matches.append((score, display_name, page_id, page_index))
        matches.sort(key=lambda x: (-x[0], x[1]))

        self._results_list.clear()
        self._filtered_items = []
        for score, display_name, page_id, page_index in matches:
            self._filtered_items.append((display_name, page_id, page_index))
            item = QListWidgetItem()
            self._results_list.addItem(item)

            widget = self._make_result_widget(display_name, page_id)
            item.setSizeHint(widget.sizeHint())
            self._results_list.setItemWidget(item, widget)

        if self._results_list.count() > 0:
            self._results_list.setCurrentRow(0)

    def _fuzzy_score(self, text: str, query: str) -> float:
        text_lower = text.lower()
        query_lower = query.lower()

        if not query:
            return 0.0
        if query_lower == text_lower:
            return 100.0
        if text_lower.startswith(query_lower):
            return 80.0
        if query_lower in text_lower:
            return 60.0
        qi = 0
        for ch in text_lower:
            if qi < len(query_lower) and ch == query_lower[qi]:
                qi += 1
        if qi == len(query_lower):
            return 40.0
        return 0.0

    def _make_result_widget(self, display_name: str, page_id: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_SM, SPACING_XL // 2, SPACING_SM, SPACING_XL // 2)
        layout.setSpacing(SPACING_2XS)

        title_label = QLabel(display_name)
        title_label.setFont(QFont(FONT_NAME_PRIMARY, TEXT_BODY))
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")

        subtitle_label = QLabel(page_id)
        subtitle_label.setFont(QFont(FONT_NAME_PRIMARY, TEXT_LABEL))
        subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none;")

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return widget

    def _on_item_clicked(self, item: QListWidgetItem):
        row = self._results_list.row(item)
        self._activate_item(row)

    def _on_return_pressed(self):
        current = self._results_list.currentRow()
        if current >= 0:
            self._activate_item(current)
        elif self._filtered_items:
            self._activate_item(0)

    def _activate_item(self, row: int):
        if 0 <= row < len(self._filtered_items):
            _name, page_id, page_index = self._filtered_items[row]
            self.navigate_requested.emit(page_id, page_index)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Down:
            current = self._results_list.currentRow()
            next_row = current + 1 if current < self._results_list.count() - 1 else 0
            self._results_list.setCurrentRow(next_row)
            event.accept()
        elif event.key() == Qt.Key.Key_Up:
            current = self._results_list.currentRow()
            prev_row = current - 1 if current > 0 else self._results_list.count() - 1
            self._results_list.setCurrentRow(prev_row)
            event.accept()
        else:
            super().keyPressEvent(event)

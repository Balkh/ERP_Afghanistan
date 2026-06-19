"""
Pagination Footer Component.
Reusable widget showing page navigation, item count, and page size selector.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from ui.constants import (
    SPACING_SM, SPACING_MD, SPACING_LG,
    BORDER_RADIUS_SM,
    COLOR_BG_SURFACE, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_TEXT_ON_PRIMARY,
    COLOR_BG_ELEVATED,
    TEXT_LABEL, FONT_NAME_PRIMARY,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize


class PaginationFooter(QWidget):
    """
    Reusable pagination footer with prev/next buttons, page info, and page size selector.

    Usage:
        footer = PaginationFooter()
        footer.set_total_count(150)
        footer.page_changed.connect(my_handler)
    """

    page_changed = Signal(int)      # New page number (1-based)
    page_size_changed = Signal(int) # New page size

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 1
        self._page_size = 50
        self._total_count = 0
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            PaginationFooter {{
                background-color: {COLOR_BG_SURFACE};
                border-top: 1px solid {COLOR_BORDER};
            }}
        """)
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        # Left: item count
        self._info_label = QLabel("0 items")
        self._info_label.setFont(QFont(FONT_NAME_PRIMARY, TEXT_LABEL))
        self._info_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(self._info_label)

        layout.addStretch(1)

        # Center: page navigation
        self._prev_btn = EnterpriseButton("‹ Prev", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self._prev_btn.clicked.connect(self._on_prev)
        layout.addWidget(self._prev_btn)

        self._page_label = QLabel("1 / 1")
        self._page_label.setFont(QFont(FONT_NAME_PRIMARY, TEXT_LABEL))
        self._page_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self._page_label.setMinimumWidth(60)
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._page_label)

        self._next_btn = EnterpriseButton("Next ›", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self._next_btn.clicked.connect(self._on_next)
        layout.addWidget(self._next_btn)

        layout.addStretch(1)

        # Right: page size selector
        size_label = QLabel("Show:")
        size_label.setFont(QFont(FONT_NAME_PRIMARY, TEXT_LABEL))
        size_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(size_label)

        self._size_combo = QComboBox()
        self._size_combo.addItems(["25", "50", "100", "200"])
        self._size_combo.setCurrentText("50")
        self._size_combo.setFixedWidth(70)
        self._size_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM}px;
                padding: {SPACING_SM}px;
                font-size: {TEXT_LABEL}pt;
            }}
        """)
        self._size_combo.currentTextChanged.connect(self._on_size_changed)
        layout.addWidget(self._size_combo)

    def set_total_count(self, count: int):
        """Set total number of items."""
        self._total_count = count
        self._update_display()

    def set_current_page(self, page: int):
        """Set current page (1-based)."""
        self._current_page = max(1, page)
        self._update_display()

    def set_page_size(self, size: int):
        """Set page size."""
        self._page_size = max(1, size)
        self._size_combo.setCurrentText(str(size))
        self._update_display()

    @property
    def total_pages(self) -> int:
        return max(1, (self._total_count + self._page_size - 1) // self._page_size)

    def _on_prev(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._update_display()
            self.page_changed.emit(self._current_page)

    def _on_next(self):
        if self._current_page < self.total_pages:
            self._current_page += 1
            self._update_display()
            self.page_changed.emit(self._current_page)

    def _on_size_changed(self, text: str):
        try:
            self._page_size = int(text)
        except ValueError:
            self._page_size = 50
        self._current_page = 1
        self._update_display()
        self.page_size_changed.emit(self._page_size)

    def _update_display(self):
        total = self.total_pages
        start = (self._current_page - 1) * self._page_size + 1
        end = min(self._current_page * self._page_size, self._total_count)

        if self._total_count == 0:
            self._info_label.setText("0 items")
        else:
            self._info_label.setText(f"{start}–{end} of {self._total_count}")

        self._page_label.setText(f"{self._current_page} / {total}")
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < total)

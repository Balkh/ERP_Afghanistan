"""
Skeleton Loader Component — lightweight animated placeholder for perceived performance.
Replaces full-screen spinners with content-shaped placeholders during load.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter
from typing import Optional
from ui.constants import (
    SPACING_SM, SPACING_MD, BORDER_RADIUS_SM, COLOR_BG_ELEVATED, COLOR_BORDER
)


class SkeletonRow(QWidget):
    """A single animated skeleton row mimicking a table row."""

    def __init__(self, columns: int = 5, height: int = 32, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._opacity = 0.3
        self.setFixedHeight(height)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, 2, SPACING_SM, 2)
        layout.setSpacing(SPACING_MD)

        for _ in range(columns):
            bar = QFrame()
            bar.setFixedHeight(height - 8)
            bar.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLOR_BG_ELEVATED};
                    border-radius: {BORDER_RADIUS_SM}px;
                }}
            """)
            layout.addWidget(bar)

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._pulse)
        self._anim.start(800)
        self._direction = 1

    def _pulse(self):
        self._opacity += 0.05 * self._direction
        if self._opacity > 0.6:
            self._direction = -1
        elif self._opacity < 0.2:
            self._direction = 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        super().paintEvent(event)

    def stop(self):
        self._anim.stop()


class SkeletonTable(QWidget):
    """Skeleton placeholder that mimics a table layout during data loading."""

    def __init__(self, rows: int = 8, columns: int = 5, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._rows = rows
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self._row_widgets = []
        for _ in range(rows):
            row = SkeletonRow(columns=columns, height=32)
            self._row_widgets.append(row)
            layout.addWidget(row)

        layout.addStretch()

    def stop(self):
        for row in self._row_widgets:
            row.stop()

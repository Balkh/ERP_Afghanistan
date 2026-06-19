"""
Skeleton Loading Components.
Animated placeholder widgets shown while data is loading.

Provides SkeletonRow, SkeletonTable, and SkeletonWidget — lightweight
QFrame-based placeholders that pulse via a QTimer-driven opacity cycle.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer, Property, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QColor, QPainter

from ui.constants import (
    COLOR_BG_SURFACE,
    COLOR_BORDER_LIGHT,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
    BORDER_RADIUS_MD,
)


class _SkeletonPulse(QFrame):
    """A single animated skeleton bar with a pulsing gradient effect."""

    def __init__(self, width: int = 200, height: int = 16, parent=None):
        super().__init__(parent)
        self._width = width
        self._height = height
        self._opacity = 0.3
        self._phase = 0

        self.setFixedSize(width, height)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(80)

    def _animate(self):
        """Cycle opacity between 0.15 and 0.45."""
        self._phase += 1
        import math
        self._opacity = 0.30 + 0.15 * math.sin(self._phase * 0.3)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = QColor(COLOR_BG_SURFACE)
        r, g, b, _ = base.getRgb()
        alpha = int(self._opacity * 255)
        painter.setBrush(QColor(r, g, b, alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), BORDER_RADIUS_MD, BORDER_RADIUS_MD)
        painter.end()

    def stop(self):
        self._timer.stop()

    def start(self):
        self._timer.start(80)


class SkeletonRow(QFrame):
    """A row of skeleton bars simulating a single data row."""

    def __init__(self, columns: list = None, parent=None):
        """
        Args:
            columns: list of (width_ratio, height) tuples.
                     Default: 3 columns — name(0.4), date(0.25), amount(0.2).
        """
        super().__init__(parent)
        self._skeletons = []
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_MD)

        if columns is None:
            columns = [(0.4, 16), (0.25, 16), (0.2, 16)]

        total_width = 800
        for ratio, height in columns:
            bar = _SkeletonPulse(int(total_width * ratio), height)
            self._skeletons.append(bar)
            layout.addWidget(bar)
        layout.addStretch(1)

    def stop(self):
        for s in self._skeletons:
            s.stop()

    def start(self):
        for s in self._skeletons:
            s.start()


class SkeletonTable(QFrame):
    """A skeleton table showing multiple skeleton rows."""

    def __init__(self, rows: int = 5, columns: list = None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._skeleton_rows = []
        for _ in range(rows):
            row = SkeletonRow(columns)
            self._skeleton_rows.append(row)
            layout.addWidget(row)
        layout.addStretch(1)

    def stop(self):
        for r in self._skeleton_rows:
            r.stop()

    def start(self):
        for r in self._skeleton_rows:
            r.start()


class SkeletonWidget(QWidget):
    """Full-page skeleton overlay that replaces screen content during loading."""

    def __init__(self, rows: int = 8, columns: list = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        self._skeleton_table = SkeletonTable(rows, columns)
        layout.addWidget(self._skeleton_table)
        layout.addStretch(1)

    def start(self):
        """Start all skeleton animations."""
        self._skeleton_table.start()
        self.setVisible(True)

    def stop(self):
        """Stop all skeleton animations."""
        self._skeleton_table.stop()
        self.setVisible(False)

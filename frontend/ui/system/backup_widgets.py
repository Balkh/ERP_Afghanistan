"""Reusable widgets for the Backup & Recovery Control Center."""

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD,
                           TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY,
                           COLOR_TEXT_MUTED, COLOR_SUCCESS, COLOR_WARNING,
                           COLOR_DANGER, COLOR_INFO)


# ---------------------------------------------------------------------------
# Status indicator color map (shared across widgets)
# ---------------------------------------------------------------------------
_STATUS_COLOR_MAP = {
    'healthy': COLOR_SUCCESS,
    'warning': COLOR_WARNING,
    'critical': COLOR_DANGER,
    'enabled': COLOR_SUCCESS,
    'disabled': COLOR_TEXT_MUTED,
    'pending': COLOR_WARNING,
    'failure': COLOR_DANGER,
    'CERTIFIED': COLOR_SUCCESS,
    'CONDITIONAL': COLOR_WARNING,
    'FAILED': COLOR_DANGER,
    'locked': COLOR_DANGER,
    'unlocked': COLOR_SUCCESS,
}

_RESTORE_STATE_COLOR_MAP = {
    'IDLE': COLOR_SUCCESS,
    'VALIDATING': COLOR_INFO,
    'SNAPSHOT_CREATED': COLOR_INFO,
    'RESTORING': COLOR_WARNING,
    'VERIFYING': COLOR_INFO,
    'COMPLETED': COLOR_SUCCESS,
    'FAILED': COLOR_DANGER,
    'ROLLBACK_TRIGGERED': COLOR_DANGER,
}


class StatusIndicator(QFrame):
    """Lightweight status indicator card — no graphs, no heavy visualization."""

    def __init__(self, label: str, value: str, status: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_XS)

        from theme.style_builder import UIStyleBuilder

        lbl = QLabel(label)
        lbl.setStyleSheet(UIStyleBuilder.get_label_style("muted"))
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        self._val_lbl = QLabel(value)
        self._val_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._val_lbl)

        self.update_status(value, status)

    def update_status(self, value: str, status: str):
        """Update indicator value and color using governed styles."""
        from theme.style_builder import UIStyleBuilder
        color = _STATUS_COLOR_MAP.get(status, COLOR_INFO)
        self.setStyleSheet(UIStyleBuilder.get_status_indicator_style(color))
        self._val_lbl.setText(value)
        self._val_lbl.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_CARD_TITLE, 700))


class WarningBanner(QFrame):
    """Warning/error banner for critical conditions."""

    def __init__(self, message: str, level: str = 'warning', parent=None):
        super().__init__(parent)
        from theme.style_builder import UIStyleBuilder
        self.setStyleSheet(UIStyleBuilder.get_warning_banner_style(level))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)

        color = COLOR_WARNING if level == 'warning' else COLOR_DANGER
        icon = "!" if level == 'warning' else "X"
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_SECTION_TITLE))
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)


class RestoreStateBadge(QFrame):
    """Shows current restore state machine state."""

    def __init__(self, state: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(SPACING_MD, SPACING_XS, SPACING_MD, SPACING_XS)
        self.update_state(state)

    def update_state(self, state: str):
        """Update badge state, color, and label in-place."""
        from theme.style_builder import UIStyleBuilder

        # Clear previous children
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        color = _RESTORE_STATE_COLOR_MAP.get(state, COLOR_TEXT_MUTED)
        self.setStyleSheet(UIStyleBuilder.get_badge_style(color))

        dot = QLabel("●")
        dot.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_BODY))
        self._layout.addWidget(dot)

        lbl = QLabel(state.replace('_', ' '))
        lbl.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_BODY, 600))
        self._layout.addWidget(lbl)
        self._layout.addStretch()

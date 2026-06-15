"""
Enterprise Notifications System.
Unified notification layer combining Toast-style (simple message) and
Notification-style (title+message) transient UI feedback.
Phase 16.2: Merged ToastManager capabilities, added keyboard dismiss,
accessibility support, and governance-compliant IconButton close.
"""
from ui.constants import (
    TEXT_TABLE, TEXT_LABEL, TEXT_CARD_TITLE, TEXT_BODY,
    SPACING_XS, SPACING_SM, SPACING_MD, BORDER_RADIUS_LG,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO, COLOR_TEXT_ON_SUCCESS,
    COLOR_TEXT_ON_DANGER, COLOR_TEXT_ON_WARNING, COLOR_TEXT_ON_PRIMARY, COLOR_BG_ELEVATED,
)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QAccessible, QAccessibleEvent
from enum import Enum
from typing import Optional, Callable

from ui.components.buttons import IconButton, ButtonVariant, ButtonSize

import logging

logger = logging.getLogger(__name__)

# ── Workflow Reassurance Messages ──
WORKFLOW_SAVED = "{} saved successfully"
WORKFLOW_UPDATED = "{} updated"
WORKFLOW_DELETED = "{} deleted"
WORKFLOW_CREATED = "{} created"
WORKFLOW_POSTED = "{} posted"
WORKFLOW_PAID = "Payment of {} recorded"
WORKFLOW_CANCELLED = "{} cancelled"
WORKFLOW_EXPORTED = "{} exported"

class NotificationType(Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class NotificationDuration(Enum):
    """Notification display duration."""
    SHORT = 3000
    MEDIUM = 5000
    LONG = 8000
    PERMANENT = 0

# Adaptive text contrast: same pattern as ToastManager._TOAST_CONFIGS
_NOTIFICATION_STYLES = {
    NotificationType.SUCCESS: {"bg": COLOR_SUCCESS, "text": COLOR_TEXT_ON_SUCCESS},
    NotificationType.ERROR:   {"bg": COLOR_DANGER,  "text": COLOR_TEXT_ON_DANGER},
    NotificationType.WARNING: {"bg": COLOR_WARNING, "text": COLOR_TEXT_ON_WARNING},
    NotificationType.INFO:    {"bg": COLOR_INFO,    "text": COLOR_TEXT_ON_PRIMARY},
}

class NotificationItem(QWidget):
    """
    Single notification widget with animation, keyboard dismiss, and accessibility support.
    Supports two modes:
      - Title+message (default, via title/message kwargs)
      - Simple message-only (via show_message style)
    """

    closed = Signal()

    def __init__(
        self,
        title: str = "",
        message: str = "",
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
        _simple_message: bool = False,
    ):
        super().__init__(parent)

        self._title = title
        self._message = message
        self._type = notification_type
        self._duration = duration
        self._action_callback = action_callback
        self._simple_message = _simple_message

        self._setup_ui()
        self._start_auto_close()

    def _setup_ui(self):
        """Setup notification UI."""

        style = _NOTIFICATION_STYLES.get(self._type, _NOTIFICATION_STYLES[NotificationType.INFO])
        bg_color = style["bg"]
        text_color = style["text"]

        if self._simple_message:
            self.setFixedHeight(50)
            self.setMinimumWidth(260)
            self.setMaximumWidth(420)
        else:
            self.setFixedHeight(80)
            self.setMinimumWidth(300)
            self.setMaximumWidth(400)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: {BORDER_RADIUS_LG}px;
                color: {text_color};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        if self._simple_message:
            msg_label = QLabel(self._message if self._message else self._title)
            msg_label.setFont(QFont("Segoe UI", TEXT_BODY))
            msg_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
            msg_label.setWordWrap(True)
            msg_label.setMaximumWidth(320)
            layout.addWidget(msg_label)
        else:
            content = QVBoxLayout()
            content.setSpacing(SPACING_XS)

            title_label = QLabel(self._title)
            title_label.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
            title_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
            content.addWidget(title_label)

            message_label = QLabel(self._message)
            message_label.setFont(QFont("Segoe UI", TEXT_TABLE))
            message_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
            message_label.setWordWrap(True)
            message_label.setMaximumWidth(320)
            content.addWidget(message_label)

            layout.addLayout(content)

        layout.addStretch()

        # Close button using governed IconButton
        close_btn = IconButton(
            icon="✕",
            tooltip="Dismiss",
            variant=ButtonVariant.GHOST,
            size=ButtonSize.SMALL,
        )
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            IconButton {{
                background-color: transparent;
                border: none;
                color: {text_color};
                font-size: {TEXT_CARD_TITLE}pt;
            }}
            IconButton:hover {{
                background-color: {COLOR_BG_ELEVATED};
                border-radius: {BORDER_RADIUS_LG}px;
            }}
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def _start_auto_close(self):
        """Start auto-close timer."""
        if self._duration > 0:
            QTimer.singleShot(self._duration, self.close)

    def keyPressEvent(self, event):
        """Dismiss on Escape key."""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle close event — emit signal and update accessibility."""
        self.closed.emit()
        QAccessible.updateAccessibility(QAccessibleEvent(self, QAccessible.Event.Alert))
        super().closeEvent(event)

class NotificationManager(QWidget):
    """
    Central notification manager with toast container.
    Unified system for both simple message (Toast-style) and
    title+message (Notification-style) transient UI feedback.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._notifications: list = []
        self._max_visible = 5
        self._position = "top-right"

        self._setup_ui()

    def _setup_ui(self):
        """Setup notification container."""
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.NoDropShadowWindowHint
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(SPACING_SM)

        if "right" in self._position:
            self._layout.addStretch()

        self._container = QVBoxLayout()
        self._container.setSpacing(SPACING_SM)
        self._layout.addLayout(self._container)

    # ── Primary API (title+message) ──

    def show_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        action_callback: Optional[Callable] = None
    ):
        """Show a title+message notification."""
        self._show_item(
            title=title,
            message=message,
            notification_type=notification_type,
            duration=duration,
            action_callback=action_callback,
            _simple_message=False,
        )

    # ── Simple message API (Toast-style) ──

    def show_message(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 4000,
    ):
        """Show a simple message notification (Toast-style, no title)."""
        self._show_item(
            title=message,
            message="",
            notification_type=notification_type,
            duration=duration,
            action_callback=None,
            _simple_message=True,
        )

    def show_success(self, message: str, duration: int = 4000):
        """Show a simple success message."""
        self.show_message(message, NotificationType.SUCCESS, duration)

    def show_error(self, message: str, duration: int = 8000):
        """Show a simple error message (longer default duration)."""
        self.show_message(message, NotificationType.ERROR, duration)

    def show_warning(self, message: str, duration: int = 5000):
        """Show a simple warning message."""
        self.show_message(message, NotificationType.WARNING, duration)

    def show_info(self, message: str, duration: int = 4000):
        """Show a simple info message."""
        self.show_message(message, NotificationType.INFO, duration)

    # ── Internal ──

    def _show_item(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        action_callback: Optional[Callable] = None,
        _simple_message: bool = False,
    ):
        """Internal: create and display a notification item."""
        while len(self._notifications) >= self._max_visible:
            oldest = self._notifications.pop(0)
            oldest.deleteLater()

        notification = NotificationItem(
            title=title,
            message=message,
            notification_type=notification_type,
            duration=duration,
            action_callback=action_callback,
            _simple_message=_simple_message,
        )

        notification.closed.connect(lambda: self._remove_notification(notification))

        self._notifications.append(notification)
        self._container.addWidget(notification)

        self._update_position()
        self.show()

        logger.info(f"Notification shown: {title}")

    def _remove_notification(self, notification: NotificationItem):
        """Remove notification from list."""
        if notification in self._notifications:
            self._notifications.remove(notification)
        if not self._notifications:
            self.hide()

    def _update_position(self):
        """Update notification position on screen."""
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_geo = screen.availableGeometry()

        if self._position == "top-right":
            x = screen_geo.right() - self.width() - 20
            y = screen_geo.top() + 20
        elif self._position == "top-left":
            x = screen_geo.left() + 20
            y = screen_geo.top() + 20
        elif self._position == "bottom-right":
            x = screen_geo.right() - self.width() - 20
            y = screen_geo.bottom() - self.height() - 20
        else:
            x = screen_geo.left() + 20
            y = screen_geo.bottom() - self.height() - 20

        self.move(x, y)

    def info(self, title: str, message: str, duration: int = 5000):
        """Show info notification (title+message)."""
        self.show_notification(title, message, NotificationType.INFO, duration)

    def success(self, title: str, message: str, duration: int = 5000):
        """Show success notification (title+message)."""
        self.show_notification(title, message, NotificationType.SUCCESS, duration)

    def warning(self, title: str, message: str, duration: int = 5000):
        """Show warning notification (title+message)."""
        self.show_notification(title, message, NotificationType.WARNING, duration)

    def error(self, title: str, message: str, duration: int = 8000):
        """Show error notification (title+message)."""
        self.show_notification(title, message, NotificationType.ERROR, duration)

    def clear_all(self):
        """Clear all notifications."""
        for notification in self._notifications:
            notification.deleteLater()
        self._notifications.clear()
        self.hide()

# ── Global singleton ──

_global_notification_manager: Optional[NotificationManager] = None

def get_notification_manager() -> NotificationManager:
    """Get global notification manager."""
    global _global_notification_manager
    if _global_notification_manager is None:
        _global_notification_manager = NotificationManager()
    return _global_notification_manager

# ── Module-level convenience functions (title+message mode) ──

def notify_info(title: str, message: str, duration: int = 5000):
    """Show info notification using global manager."""
    get_notification_manager().info(title, message, duration)

def notify_success(title: str, message: str, duration: int = 5000):
    """Show success notification using global manager."""
    get_notification_manager().success(title, message, duration)

def notify_warning(title: str, message: str, duration: int = 5000):
    """Show warning notification using global manager."""
    get_notification_manager().warning(title, message, duration)

def notify_error(title: str, message: str, duration: int = 8000):
    """Show error notification using global manager."""
    get_notification_manager().error(title, message, duration)

# ── Module-level convenience functions (simple message / Toast-style mode) ──

def show_success(message: str, duration: int = 4000):
    """Show success message using global manager."""
    get_notification_manager().show_success(message, duration)

def show_error(message: str, duration: int = 8000):
    """Show error message using global manager."""
    get_notification_manager().show_error(message, duration)

def show_warning(message: str, duration: int = 5000):
    """Show warning message using global manager."""
    get_notification_manager().show_warning(message, duration)

def show_info(message: str, duration: int = 4000):
    """Show info message using global manager."""
    get_notification_manager().show_info(message, duration)

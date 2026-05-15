from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, BORDER_RADIUS_LG)
from ui.constants import (COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO)
from ui.constants import TEXT_TABLE, TEXT_LABEL, TEXT_CARD_TITLE
"""
Enterprise Notifications System.
Toast notifications and notification center.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect, QStackedWidget
)
from PySide6.QtCore import Signal, Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QIcon
from enum import Enum
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


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


class NotificationItem(QWidget):
    """
    Single notification widget with animation support.
    """
    
    closed = Signal()
    
    def __init__(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._title = title
        self._message = message
        self._type = notification_type
        self._duration = duration
        self._action_callback = action_callback
        self._close_callback = None
        
        self._setup_ui()
        self._start_auto_close()
        
    def _setup_ui(self):
        """Setup notification UI."""
        self.setFixedHeight(80)
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
        
        # Set background color based on type
        colors = {
            NotificationType.INFO: COLOR_INFO,
            NotificationType.SUCCESS: COLOR_SUCCESS,
            NotificationType.WARNING: COLOR_WARNING,
            NotificationType.ERROR: COLOR_DANGER
        }
        
        bg_color = colors.get(self._type, COLOR_INFO)
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: {BORDER_RADIUS_LG};
                color: white;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: white;
                font-size: {TEXT_CARD_TITLE}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255,255,255,0.2);
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(SPACING_SM)
        
        # Content
        content = QVBoxLayout()
        content.setSpacing(SPACING_XS)
        
        title_label = QLabel(self._title)
        title_label.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        content.addWidget(title_label)
        
        message_label = QLabel(self._message)
        message_label.setFont(QFont("Segoe UI", TEXT_TABLE))
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(320)
        content.addWidget(message_label)
        
        layout.addLayout(content)
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
    def _start_auto_close(self):
        """Start auto-close timer."""
        if self._duration > 0:
            QTimer.singleShot(self._duration, self.close)
            
    def closeEvent(self, event):
        """Handle close event."""
        self.closed.emit()
        super().closeEvent(event)


class NotificationManager(QWidget):
    """
    Central notification manager with toast container.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._notifications: list = []
        self._max_visible = 5
        self._position = "top-right"  # top-right, top-left, bottom-right, bottom-left
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup notification container."""
        # Make this widget a floating overlay
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(
            Qt.WindowType.ToolTip | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        
        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(SPACING_SM)
        
        # Align based on position
        if "right" in self._position:
            self._layout.addStretch()
            
        # Create container for notifications
        self._container = QVBoxLayout()
        self._container.setSpacing(SPACING_SM)
        self._layout.addLayout(self._container)
        
    def show_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        action_callback: Optional[Callable] = None
    ):
        """Show a notification."""
        # Remove old notifications if at max
        while len(self._notifications) >= self._max_visible:
            oldest = self._notifications.pop(0)
            oldest.deleteLater()
            
        # Create notification
        notification = NotificationItem(
            title=title,
            message=message,
            notification_type=notification_type,
            duration=duration,
            action_callback=action_callback
        )
        
        notification.closed.connect(lambda: self._remove_notification(notification))
        
        self._notifications.append(notification)
        self._container.addWidget(notification)
        
        # Position window
        self._update_position()
        
        # Show window
        self.show()
        
        logger.info(f"Notification shown: {title} - {message}")
        
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
        
        # Position based on setting
        if self._position == "top-right":
            x = screen_geo.right() - self.width() - 20
            y = screen_geo.top() + 20
        elif self._position == "top-left":
            x = screen_geo.left() + 20
            y = screen_geo.top() + 20
        elif self._position == "bottom-right":
            x = screen_geo.right() - self.width() - 20
            y = screen_geo.bottom() - self.height() - 20
        else:  # bottom-left
            x = screen_geo.left() + 20
            y = screen_geo.bottom() - self.height() - 20
            
        self.move(x, y)
        
    def info(self, title: str, message: str, duration: int = 5000):
        """Show info notification."""
        self.show_notification(title, message, NotificationType.INFO, duration)
        
    def success(self, title: str, message: str, duration: int = 5000):
        """Show success notification."""
        self.show_notification(title, message, NotificationType.SUCCESS, duration)
        
    def warning(self, title: str, message: str, duration: int = 5000):
        """Show warning notification."""
        self.show_notification(title, message, NotificationType.WARNING, duration)
        
    def error(self, title: str, message: str, duration: int = 8000):
        """Show error notification."""
        self.show_notification(title, message, NotificationType.ERROR, duration)
        
    def clear_all(self):
        """Clear all notifications."""
        for notification in self._notifications:
            notification.deleteLater()
        self._notifications.clear()
        self.hide()


# Global notification manager
_global_notification_manager: Optional[NotificationManager] = None

def get_notification_manager() -> NotificationManager:
    """Get global notification manager."""
    global _global_notification_manager
    if _global_notification_manager is None:
        _global_notification_manager = NotificationManager()
    return _global_notification_manager


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
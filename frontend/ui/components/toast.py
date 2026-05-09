from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Toast notification system for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout,
                                QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PySide6.QtGui import QFont, QColor, QPalette


class Toast(QFrame):
    """Individual toast notification."""
    
    def __init__(self, message, toast_type="info", parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QFrame {
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
            QLabel {
                color: white;
                font-size: 13px;
            }
        """)
        
        # Set background color based on type
        colors = {
            "success": "COLOR_SUCCESS",
            "error": "#f44336",
            "warning": "#ff9800",
            "info": "COLOR_PRIMARY"
        }
        bg_color = colors.get(toast_type, "COLOR_PRIMARY")
        self.setStyleSheet(self.styleSheet() + f"background-color: {bg_color};")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        icon_label.setAlignment(Qt.AlignCenter)
        icons = {
            "success": "✓",
            "error": "✕",
            "warning": "⚠",
            "info": "ℹ"
        }
        icon_label.setText(icons.get(toast_type, "ℹ"))
        icon_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)

        self.message_label = QLabel(message)
        self.message_label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.message_label)
        layout.addStretch()
        
        # Setup fade animation
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.deleteLater)
        
        # Auto-hide timer
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)
        self.timer.start(3000)  # Hide after 3 seconds
    
    def start_fade_out(self):
        """Start fade out animation."""
        self.timer.stop()
        self.fade_animation.start()


class ToastManager(QWidget):
    """Manages toast notifications."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.toasts = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(SPACING_SM)
        layout.addStretch()
        self.setLayout(layout)
    
    def show_toast(self, message, toast_type="info"):
        """Show a toast notification."""
        toast = Toast(message, toast_type, self)
        self.layout().insertWidget(0, toast)
        self.toasts.append(toast)
        
        # Remove toast from list when deleted
        toast.destroyed.connect(lambda: self.toasts.remove(toast) if toast in self.toasts else None)
        
        # Limit toasts to prevent overflow
        if len(self.toasts) > 5:
            oldest = self.toasts.pop(0)
            oldest.deleteLater()
    
    def show_success(self, message):
        """Show success toast."""
        self.show_toast(message, "success")
    
    def show_error(self, message):
        """Show error toast."""
        self.show_toast(message, "error")
    
    def show_warning(self, message):
        """Show warning toast."""
        self.show_toast(message, "warning")
    
    def show_info(self, message):
        """Show info toast."""
        self.show_toast(message, "info")


# Global toast manager instance
toast_manager = None


def get_toast_manager():
    """Get or create the global toast manager."""
    global toast_manager
    if toast_manager is None:
        toast_manager = ToastManager()
    return toast_manager
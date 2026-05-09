from ui.constants import (SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, MARGIN_CARD, MARGIN_COMPACT_H, MARGIN_COMPACT_V, COLOR_HEADER_DARK)
"""
Enterprise Dialog Components.
Professional dialog windows with standard patterns.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter
from typing import Optional, Callable, Dict, Any
from enum import Enum


class DialogType(Enum):
    """Dialog types."""
    CONFIRM = "confirm"
    ALERT = "alert"
    INPUT = "input"
    CUSTOM = "custom"


class DialogButton(Enum):
    """Standard dialog buttons."""
    OK = "ok"
    CANCEL = "cancel"
    YES = "yes"
    NO = "no"
    SAVE = "save"
    DELETE = "delete"
    CLOSE = "close"


class EnterpriseDialog(QDialog):
    """
    Base enterprise dialog with standard styling and buttons.
    """
    
    def __init__(
        self,
        title: str = "Dialog",
        dialog_type: DialogType = DialogType.CUSTOM,
        parent: Optional[QWidget] = None,
        flags: Qt.WindowType = None
    ):
        super().__init__(parent)
        
        self._title = title
        self._dialog_type = dialog_type
        self._result_data: Dict[str, Any] = {}
        
        if flags:
            self.setWindowFlags(flags)
        else:
            self.setWindowFlags(
                Qt.WindowType.Dialog | 
                Qt.WindowType.WindowTitleHint |
                Qt.WindowType.CloseButtonHint
            )
            
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle(self._title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        
        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(SPACING_NONE)
        self._main_layout.setContentsMargins(SPACING_NONE,  SPACING_NONE,  SPACING_NONE,  SPACING_NONE)
        
        # Header
        self._header = self._create_header()
        if self._header:
            self._main_layout.addWidget(self._header)
            
        # Content area
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setSpacing(SPACING_MD)
        self._content_layout.setContentsMargins(MARGIN_CARD, MARGIN_CARD, MARGIN_CARD, MARGIN_CARD)
        self._main_layout.addWidget(self._content_widget, 1)
        
        # Button area
        self._button_area = self._create_button_area()
        if self._button_area:
            self._main_layout.addWidget(self._button_area)
            
    def _create_header(self) -> Optional[QWidget]:
        """Create dialog header."""
        header = QFrame()
        header.setFixedHeight(50)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(MARGIN_COMPACT_H, MARGIN_COMPACT_V, MARGIN_COMPACT_H, MARGIN_COMPACT_V)
        
        title_label = QLabel(self._title)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        header.setStyleSheet(f"""
            QFrame {
                background-color: {COLOR_HEADER_DARK};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QLabel {
                color: white;
            }
        """)
        
        return header
        
    def _create_button_area(self) -> Optional[QWidget]:
        """Create button area."""
        button_area = QFrame()
        button_area.setFixedHeight(60)
        
        layout = QHBoxLayout(button_area)
        layout.setContentsMargins(MARGIN_COMPACT_H, MARGIN_COMPACT_V, MARGIN_COMPACT_H, MARGIN_COMPACT_V)
        
        layout.addStretch()
        
        # Default buttons based on dialog type
        if self._dialog_type == DialogType.CONFIRM:
            self._yes_btn = QPushButton("Yes")
            self._no_btn = QPushButton("No")
            
            self._yes_btn.clicked.connect(self.accept)
            self._no_btn.clicked.connect(self.reject)
            
            layout.addWidget(self._no_btn)
            layout.addWidget(self._yes_btn)
            
        elif self._dialog_type == DialogType.ALERT:
            self._ok_btn = QPushButton("OK")
            self._ok_btn.clicked.connect(self.accept)
            layout.addWidget(self._ok_btn)
            
        else:
            self._cancel_btn = QPushButton("Cancel")
            self._save_btn = QPushButton("Save")
            
            self._cancel_btn.clicked.connect(self.reject)
            self._save_btn.clicked.connect(self.accept)
            
            layout.addWidget(self._cancel_btn)
            layout.addWidget(self._save_btn)
            
        button_area.setStyleSheet(f"""
            QFrame {{
                background-color: {{{COLOR_BG_MAIN}}};
                border-top: 1px solid {{{COLOR_BORDER}}};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QPushButton {{
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: 600;
            }}
            QPushButton[text="Save"] {{
                background-color: {{{COLOR_PRIMARY}}};
                color: white;
            }}
            QPushButton[text="OK"] {{
                background-color: {{{COLOR_PRIMARY}}};
                color: white;
            }}
            QPushButton[text="Yes"] {{
                background-color: {{{COLOR_PRIMARY}}};
                color: white;
            }}
        """)
        
        return button_area
    
    def set_content(self, widget: QWidget):
        """Set main content widget."""
        # Clear existing content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
                
        self._content_layout.addWidget(widget)
        
    def set_title(self, title: str):
        """Set dialog title."""
        self._title = title
        self.setWindowTitle(title)
        
        # Update header title if exists
        if hasattr(self, '_header'):
            for child in self._header.children():
                if isinstance(child, QLabel) and child.font().pointSize() == 14:
                    child.setText(title)
                    
    def get_result(self) -> Dict[str, Any]:
        """Get dialog result data."""
        return self._result_data
        
    def set_result(self, data: Dict[str, Any]):
        """Set dialog result data."""
        self._result_data = data


class ConfirmDialog(EnterpriseDialog):
    """
    Confirmation dialog with yes/no buttons.
    """
    
    confirmed = Signal()
    cancelled = Signal()
    
    def __init__(
        self,
        title: str = "Confirm",
        message: str = "Are you sure?",
        parent: Optional[QWidget] = None
    ):
        super().__init__(title, DialogType.CONFIRM, parent)
        
        # Add message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setFont(QFont("Segoe UI", 11))
        self.set_content(message_label)
        
        # Connect signals
        self.accepted.connect(self._on_confirmed)
        self.rejected.connect(self._on_cancelled)
        
    def _on_confirmed(self):
        """Handle confirmed."""
        self.confirmed.emit()
        
    def _on_cancelled(self):
        """Handle cancelled."""
        self.cancelled.emit()
        
    @staticmethod
    def confirm(title: str, message: str, parent: Optional[QWidget] = None) -> bool:
        """Show confirm dialog and return result."""
        dialog = ConfirmDialog(title, message, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted


class AlertDialog(EnterpriseDialog):
    """
    Alert dialog with single OK button.
    """
    
    def __init__(
        self,
        title: str = "Alert",
        message: str = "",
        alert_type: str = "info",
        parent: Optional[QWidget] = None
    ):
        super().__init__(title, DialogType.ALERT, parent)
        
        # Add message with styling
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setFont(QFont("Segoe UI", 11))
        self.set_content(message_label)
        
    @staticmethod
    def show(title: str, message: str, alert_type: str = "info", parent: Optional[QWidget] = None):
        """Show alert dialog."""
        dialog = AlertDialog(title, message, alert_type, parent)
        dialog.exec()
        
    @staticmethod
    def info(title: str, message: str, parent: Optional[QWidget] = None):
        """Show info alert."""
        AlertDialog.show(title, message, "info", parent)
        
    @staticmethod
    def warning(title: str, message: str, parent: Optional[QWidget] = None):
        """Show warning alert."""
        AlertDialog.show(title, message, "warning", parent)
        
    @staticmethod
    def error(title: str, message: str, parent: Optional[QWidget] = None):
        """Show error alert."""
        AlertDialog.show(title, message, "error", parent)


class LoadingDialog(EnterpriseDialog):
    """
    Loading dialog with spinner.
    """
    
    def __init__(
        self,
        message: str = "Loading...",
        parent: Optional[QWidget] = None
    ):
        super().__init__("", DialogType.CUSTOM, parent)
        
        # Remove title bar
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        
        # Add message
        self._message_label = QLabel(message)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setFont(QFont("Segoe UI", 12))
        self.set_content(self._message_label)
        
        self.setMinimumWidth(200)
        self.setMinimumHeight(100)


def confirm_dialog(parent, title: str, message: str) -> bool:
    """
    Helper function to show a confirmation dialog and return result.
    Returns True if user confirmed, False otherwise.
    """
    dialog = ConfirmDialog(title, message, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
        
    def set_message(self, message: str):
        """Update loading message."""
        self._message_label.setText(message)
from ui.constants import (
    SPACING_NONE, SPACING_SM, SPACING_MD, SPACING_LG,
    COLOR_BG_DIALOG, COLOR_BG_MAIN, COLOR_HEADER_DARK, COLOR_FORM_FOOTER_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_ON_HEADER,
    COLOR_BG_SECTION, COLOR_BORDER,
    BORDER_RADIUS_LG,
    DIALOG_WIDTH_MIN, DIALOG_WIDTH_PREFERRED, DIALOG_WIDTH_MAX,
    TEXT_CARD_TITLE, TEXT_BODY, TEXT_LABEL, MARGIN_CARD, MARGIN_COMPACT_H, MARGIN_COMPACT_V,
)

"""
Enterprise Dialog Components.
Professional dialog windows with standard patterns.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from typing import Optional, Dict, Any
from enum import Enum
import time

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
        
        self._open_ts: float = 0.0

        if flags:
            self.setWindowFlags(flags)
        else:
            self.setWindowFlags(
                Qt.WindowType.Dialog | 
                Qt.WindowType.WindowTitleHint |
                Qt.WindowType.WindowCloseButtonHint
            )
            
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle(self._title)
        
        # ── Width Governance ──
        self.setMinimumWidth(DIALOG_WIDTH_MIN)
        self.setMaximumWidth(DIALOG_WIDTH_MAX)
        self.resize(DIALOG_WIDTH_PREFERRED, 400)
        
        # ── Surface layering: dialog background ──
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_DIALOG};
            }}
        """)
        
        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(SPACING_NONE)
        self._main_layout.setContentsMargins(SPACING_NONE, SPACING_NONE, SPACING_NONE, SPACING_NONE)
        
        # Header
        self._header = self._create_header()
        if self._header:
            self._main_layout.addWidget(self._header)
            
        # Content area (elevated surface)
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
        title_label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_HEADER_DARK};
                border-top-left-radius: {BORDER_RADIUS_LG}px;
                border-top-right-radius: {BORDER_RADIUS_LG}px;
            }}
            QLabel {{
                color: {COLOR_TEXT_ON_HEADER};
            }}
        """)
        
        return header
        
    def _create_button_area(self) -> Optional[QWidget]:
        """Create button area with anchored footer."""
        from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
        
        button_area = QFrame()
        button_area.setFixedHeight(60)
        
        layout = QHBoxLayout(button_area)
        layout.setContentsMargins(MARGIN_CARD, SPACING_SM, MARGIN_CARD, SPACING_SM)
        
        layout.addStretch()
        
        # Default buttons based on dialog type
        if self._dialog_type == DialogType.CONFIRM:
            self._yes_btn = EnterpriseButton("Yes", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
            self._no_btn = EnterpriseButton("No", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
            
            self._yes_btn.clicked.connect(self.accept)
            self._no_btn.clicked.connect(self.reject)
            
            layout.addWidget(self._no_btn)
            layout.addWidget(self._yes_btn)
            
        elif self._dialog_type == DialogType.ALERT:
            self._ok_btn = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
            self._ok_btn.clicked.connect(self.accept)
            layout.addWidget(self._ok_btn)
            
        else:
            self._cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
            self._save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
            
            self._cancel_btn.clicked.connect(self.reject)
            self._save_btn.clicked.connect(self.accept)
            
            layout.addWidget(self._cancel_btn)
            layout.addWidget(self._save_btn)
            
        button_area.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_MAIN};
                border-top: 1px solid {COLOR_FORM_FOOTER_BORDER};
                border-bottom-left-radius: {BORDER_RADIUS_LG}px;
                border-bottom-right-radius: {BORDER_RADIUS_LG}px;
            }}
        """)
        
        return button_area
    
    def showEvent(self, event):
        super().showEvent(event)
        self._open_ts = time.time()

    def done(self, code):
        if self._open_ts:
            duration_ms = (time.time() - self._open_ts) * 1000
            from runtime.ux_telemetry import record_dialog
            record_dialog(self._dialog_type.value, duration_ms)
        super().done(code)

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
        message_label.setFont(QFont("Segoe UI", TEXT_LABEL))
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
        message_label.setFont(QFont("Segoe UI", TEXT_LABEL))
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
        self._message_label.setFont(QFont("Segoe UI", TEXT_BODY))
        self.set_content(self._message_label)
        
        self.setMinimumWidth(200)
        self.setMinimumHeight(100)

    def set_message(self, message: str):
        """Update loading message."""
        self._message_label.setText(message)

def confirm_dialog(parent, title: str, message: str) -> bool:
    """
    Helper function to show a confirmation dialog and return result.
    Returns True if user confirmed, False otherwise.
    """
    dialog = ConfirmDialog(title, message, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted

LoadingDialog.set_message = lambda self, message: self._message_label.setText(message)
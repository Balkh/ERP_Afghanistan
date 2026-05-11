"""
Enterprise Button Component.
Professional button widget with multiple variants and states.
"""

from PySide6.QtWidgets import QPushButton, QSizePolicy
from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtGui import QPainter, QColor, QFontMetrics
from enum import Enum
from typing import Optional
from ui.constants import SPACING_SM


class ButtonVariant(Enum):
    """Button variant types."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"
    GHOST = "ghost"


class ButtonSize(Enum):
    """Button size options."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class EnterpriseButton(QPushButton):
    """
    Enterprise-grade button with multiple variants and states.
    """
    
    clicked_with_data = Signal(object)  # Emit clicked with custom data
    
    def __init__(
        self,
        text: str = "",
        variant: ButtonVariant = ButtonVariant.PRIMARY,
        size: ButtonSize = ButtonSize.MEDIUM,
        icon: Optional[str] = None,
        icon_position: str = "left",
        data: Optional[object] = None,
        parent: Optional[QPushButton] = None
    ):
        super().__init__(text, parent)
        
        self._variant = variant
        self._size = size
        self._icon = icon
        self._icon_position = icon_position
        self._data = data
        self._loading = False
        self._full_width = False
        
        self._setup_button()
        self.clicked.connect(self._on_clicked)
        
    def _setup_button(self):
        """Setup button properties based on variant and size."""
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Set fixed height based on size
        size_config = {
            ButtonSize.SMALL: 28,
            ButtonSize.MEDIUM: 36,
            ButtonSize.LARGE: 44
        }
        self.setFixedHeight(size_config.get(self._size, 36))
        
        # Set minimum width based on size
        min_widths = {
            ButtonSize.SMALL: 60,
            ButtonSize.MEDIUM: 80,
            ButtonSize.LARGE: 100
        }
        self.setMinimumWidth(min_widths.get(self._size, 80))
        
        # Apply variant styles
        self._apply_variant_style()
        
        # Set focus policy
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
    def _apply_variant_style(self):
        """Apply variant-specific styles."""
        from ui.constants import (COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                                  COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_SUCCESS_ACTIVE,
                                  COLOR_SUCCESS_MUTED, COLOR_DANGER, COLOR_DANGER_HOVER,
                                  COLOR_DANGER_ACTIVE, COLOR_DANGER_MUTED,
                                  COLOR_WARNING, COLOR_WARNING_HOVER, COLOR_WARNING_ACTIVE,
                                  COLOR_WARNING_MUTED,
                                  COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_MUTED,
                                  COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_BG_ELEVATED)
        variant_styles = {
            ButtonVariant.PRIMARY: f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_PRIMARY_ACTIVE};
                }}
                QPushButton:disabled {{
                    background-color: {COLOR_BORDER};
                    color: {COLOR_TEXT_MUTED};
                }}
            """,
            ButtonVariant.SECONDARY: f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_PRIMARY_ACTIVE};
                }}
                QPushButton:disabled {{
                    background-color: {COLOR_BORDER};
                    color: {COLOR_TEXT_MUTED};
                }}
            """,
            ButtonVariant.SUCCESS: f"""
                QPushButton {{
                    background-color: {COLOR_SUCCESS};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_SUCCESS_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_SUCCESS_ACTIVE};
                }}
                QPushButton:disabled {{
                    background-color: {COLOR_SUCCESS_MUTED};
                    color: {COLOR_TEXT_MUTED};
                }}
            """,
            ButtonVariant.DANGER: f"""
                QPushButton {{
                    background-color: {COLOR_DANGER};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_DANGER_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_DANGER_ACTIVE};
                }}
                QPushButton:disabled {{
                    background-color: {COLOR_DANGER_MUTED};
                    color: {COLOR_TEXT_MUTED};
                }}
            """,
            ButtonVariant.WARNING: f"""
                QPushButton {{
                    background-color: {COLOR_WARNING};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_WARNING_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_WARNING_ACTIVE};
                }}
                QPushButton:disabled {{
                    background-color: {COLOR_WARNING_MUTED};
                    color: {COLOR_TEXT_MUTED};
                }}
            """,
            ButtonVariant.GHOST: f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLOR_PRIMARY};
                    border: 1px solid {COLOR_BORDER};
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BG_ELEVATED};
                    border: 1px solid {COLOR_PRIMARY};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_BORDER_LIGHT};
                    border: 1px solid {COLOR_PRIMARY_ACTIVE};
                }}
                QPushButton:disabled {{
                    color: {COLOR_TEXT_MUTED};
                    border: 1px solid {COLOR_BORDER_LIGHT};
                }}
            """
        }
        
        style = variant_styles.get(self._variant, "")
        self.setStyleSheet(style)
        
    def set_variant(self, variant: ButtonVariant):
        """Set button variant."""
        self._variant = variant
        self._apply_variant_style()
        
    def get_variant(self) -> ButtonVariant:
        """Get button variant."""
        return self._variant
    
    def set_size(self, size: ButtonSize):
        """Set button size."""
        self._size = size
        self._setup_button()
        
    def get_size(self) -> ButtonSize:
        """Get button size."""
        return self._size
    
    def set_loading(self, loading: bool):
        """Set loading state."""
        self._loading = loading
        self.setEnabled(not loading)
        if loading:
            self.setText("Loading...")
        else:
            self._original_text = ""
            
    def is_loading(self) -> bool:
        """Check if button is loading."""
        return self._loading
    
    def set_full_width(self, full_width: bool):
        """Set button to expand to full width."""
        self._full_width = full_width
        if full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            
    def set_data(self, data: object):
        """Set button data."""
        self._data = data
        
    def get_data(self) -> Optional[object]:
        """Get button data."""
        return self._data
    
    def _on_clicked(self):
        """Handle click with data emission."""
        if self._data is not None:
            self.clicked_with_data.emit(self._data)


class IconButton(EnterpriseButton):
    """
    Icon-only button for toolbar actions.
    """
    
    def __init__(
        self,
        icon: str,
        tooltip: str = "",
        variant: ButtonVariant = ButtonVariant.GHOST,
        size: ButtonSize = ButtonSize.MEDIUM,
        parent: Optional[QPushButton] = None
    ):
        super().__init__(
            text="",
            variant=variant,
            size=size,
            icon=icon,
            parent=parent
        )
        
        if tooltip:
            self.setToolTip(tooltip)
            
        # Make square for icon-only buttons
        self.setMinimumSize(self.height(), self.height())
        self.setIconSize(QSize(20, 20))


class SplitButton(QPushButton):
    """
    Split button with dropdown menu.
    """
    
    split_clicked = Signal()
    dropdown_clicked = Signal()
    
    def __init__(
        self,
        text: str = "",
        parent: Optional[QPushButton] = None
    ):
        super().__init__(text, parent)
        self.setPopupMode(QPushButton.MenuButtonPopup)
        
        # Style the split button
        from ui.constants import COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_TEXT_ON_PRIMARY
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
                border: none;
                padding: {SPACING_SM} 16px;
                border-radius: 4px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
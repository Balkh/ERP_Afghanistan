"""
Base widget classes for enterprise UI architecture.
Provides reusable foundation for all UI components.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout
from PySide6.QtCore import Signal, Property, Qt
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BaseWidget(QWidget):
    """
    Base widget class for all UI components.
    Provides common functionality for theming, localization, and state management.
    """
    
    # Signals for common events
    state_changed = Signal(dict)
    error_occurred = Signal(str)
    data_loaded = Signal(object)
    
    def __init__(self, parent: Optional[QWidget] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self._config = config or {}
        self._is_loading = False
        self._theme_enabled = True
        self._initialized = False
        self._setup_base_widget()
        
    def _setup_base_widget(self):
        """Initialize base widget properties."""
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_StyledBackground)
        
    def set_loading(self, loading: bool):
        """Set loading state."""
        self._is_loading = loading
        self.setEnabled(not loading)
        
    def is_loading(self) -> bool:
        """Get loading state."""
        return self._is_loading
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any):
        """Set configuration value."""
        self._config[key] = value
        
    def initialize(self):
        """Initialize widget after construction."""
        if not self._initialized:
            self._initialize_ui()
            self._connect_signals()
            self._initialized = True
            
    def _initialize_ui(self):
        """Override in subclasses to initialize UI."""
        pass
    
    def _connect_signals(self):
        """Override in subclasses to connect signals."""
        pass
    
    def reset(self):
        """Reset widget to initial state."""
        pass
    
    def validate(self) -> tuple[bool, str]:
        """Validate widget data. Returns (is_valid, error_message)."""
        return True, ""
    
    def get_data(self) -> Dict[str, Any]:
        """Get widget data as dictionary."""
        return {}
    
    def set_data(self, data: Dict[str, Any]):
        """Set widget data from dictionary."""
        pass


class BaseContainerWidget(BaseWidget):
    """
    Base container widget with common layout management.
    """
    
    def __init__(self, parent: Optional[QWidget] = None, config: Optional[Dict] = None):
        self._layout_type = self._config.get('layout', 'vertical')
        super().__init__(parent, config)
        
    def _setup_base_widget(self):
        super()._setup_base_widget()
        self._setup_layout()
        
    def _setup_layout(self):
        if self._layout_type == 'horizontal':
            self._container_layout = QHBoxLayout()
        elif self._layout_type == 'grid':
            self._container_layout = QGridLayout()
        else:
            self._container_layout = QVBoxLayout()
            
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(self._config.get('spacing', 4))
        self.setLayout(self._container_layout)
        
    def add_widget(self, widget: QWidget, stretch: int = 0):
        """Add widget to container."""
        self._container_layout.addWidget(widget, stretch)
        
    def remove_widget(self, widget: QWidget):
        """Remove widget from container."""
        self._container_layout.removeWidget(widget)
        
    def clear(self):
        """Remove all widgets from container."""
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()


class BaseFormWidget(BaseWidget):
    """
    Base widget for form elements with validation support.
    """
    
    value_changed = Signal(object)
    
    def __init__(self, parent: Optional[QWidget] = None, config: Optional[Dict] = None):
        self._value = None
        self._required = config.get('required', False) if config else False
        self._placeholder = config.get('placeholder', '') if config else ''
        self._label = config.get('label', '') if config else ''
        self._error_message = ''
        super().__init__(parent, config)
        
    def set_value(self, value: Any):
        """Set widget value."""
        old_value = self._value
        self._value = value
        if old_value != value:
            self.value_changed.emit(value)
            self._on_value_changed()
            
    def get_value(self) -> Any:
        """Get widget value."""
        return self._value
    
    def _on_value_changed(self):
        """Handle value change."""
        self.validate()
        
    def set_required(self, required: bool):
        """Set required state."""
        self._required = required
        
    def is_required(self) -> bool:
        """Get required state."""
        return self._required
    
    def validate(self) -> tuple[bool, str]:
        """Validate form field."""
        if self._required and (self._value is None or self._value == ''):
            return False, f"{self._label or 'This field'} is required"
        return True, ""
    
    def set_error(self, message: str):
        """Set error message."""
        self._error_message = message
        self._update_error_display()
        
    def clear_error(self):
        """Clear error message."""
        self._error_message = ''
        self._update_error_display()
        
    def _update_error_display(self):
        """Override in subclasses to update error display."""
        pass


class BaseListWidget(BaseWidget):
    """
    Base widget for list/table displays with selection support.
    """
    
    item_selected = Signal(object)
    item_double_clicked = Signal(object)
    selection_changed = Signal(list)
    
    def __init__(self, parent: Optional[QWidget] = None, config: Optional[Dict] = None):
        self._items: List = []
        self._selected_items: List = []
        self._multi_select = config.get('multi_select', False) if config else False
        super().__init__(parent, config)
        
    def set_items(self, items: List):
        """Set list items."""
        self._items = items
        self._refresh_display()
        
    def get_items(self) -> List:
        """Get all items."""
        return self._items
    
    def add_item(self, item):
        """Add single item."""
        self._items.append(item)
        self._refresh_display()
        
    def remove_item(self, item):
        """Remove item."""
        if item in self._items:
            self._items.remove(item)
            self._refresh_display()
            
    def clear_items(self):
        """Clear all items."""
        self._items = []
        self._selected_items = []
        self._refresh_display()
        
    def select_item(self, item):
        """Select item."""
        if self._multi_select:
            if item not in self._selected_items:
                self._selected_items.append(item)
        else:
            self._selected_items = [item]
        self.selection_changed.emit(self._selected_items)
        self.item_selected.emit(item)
        
    def get_selected_items(self) -> List:
        """Get selected items."""
        return self._selected_items
    
    def clear_selection(self):
        """Clear selection."""
        self._selected_items = []
        self.selection_changed.emit([])
        
    def _refresh_display(self):
        """Override in subclasses to refresh display."""
        pass


class BaseDialogWidget(BaseWidget):
    """
    Base widget for dialog windows.
    """
    
    accepted = Signal()
    rejected = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None, config: Optional[Dict] = None):
        self._dialog_title = config.get('title', 'Dialog') if config else 'Dialog'
        self._dialog_width = config.get('width', 400)
        self._dialog_height = config.get('height', 300)
        super().__init__(parent, config)
        
    def accept(self):
        """Accept dialog."""
        self.accepted.emit()
        
    def reject(self):
        """Reject dialog."""
        self.rejected.emit()
        
    def get_result(self):
        """Get dialog result."""
        return self._result if hasattr(self, '_result') else None
    
    def set_result(self, result):
        """Set dialog result."""
        self._result = result
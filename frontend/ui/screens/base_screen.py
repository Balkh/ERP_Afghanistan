"""
Base screen class for all application screens.
Provides consistent screen lifecycle, navigation, and state management.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect
from PySide6.QtCore import Signal, Qt, QTimer, QPropertyAnimation, QRect
from PySide6.QtGui import QFont, QColor, QPalette
from typing import Optional, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


class ScreenState:
    """Screen state constants."""
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    EMPTY = "empty"


class BaseScreen(QWidget):
    """
    Base class for all application screens.
    Provides consistent lifecycle, navigation, and state management.
    """
    
    # Signals for screen events
    screen_shown = Signal()
    screen_hidden = Signal()
    data_requested = Signal(dict)
    navigation_requested = Signal(str, dict)
    state_changed = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None, screen_id: str = "", config: Optional[Dict] = None):
        super().__init__(parent)
        self._screen_id = screen_id
        self._config = config or {}
        self._state = ScreenState.LOADING
        self._api_client = None
        self._navigation_manager = None
        self._data_cache: Dict[str, Any] = {}
        self._is_visible = False
        self._refresh_timer: Optional[QTimer] = None
        self._auto_refresh_interval = 0
        
        self._setup_screen()
        
    def _setup_screen(self):
        """Setup screen structure."""
        self.setAttribute(Qt.WA_StyledBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        
    @property
    def screen_id(self) -> str:
        """Get screen identifier."""
        return self._screen_id
    
    @property
    def state(self) -> str:
        """Get current screen state."""
        return self._state
    
    def set_state(self, new_state: str):
        """Set screen state."""
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(new_state)
            self._on_state_changed(new_state)
            
    def _on_state_changed(self, new_state: str):
        """Handle state change."""
        pass
    
    def set_api_client(self, client):
        """Set API client for data operations."""
        self._api_client = client
        
    def get_api_client(self):
        """Get API client."""
        return self._api_client
    
    def set_navigation_manager(self, nav_manager):
        """Set navigation manager."""
        self._navigation_manager = nav_manager
        
    def navigate_to(self, screen_id: str, params: Optional[Dict] = None):
        """Navigate to another screen."""
        if self._navigation_manager:
            self._navigation_manager.navigate_to(screen_id, params or {})
        else:
            self.navigation_requested.emit(screen_id, params or {})
            
    def showEvent(self, event):
        """Handle screen show event."""
        super().showEvent(event)
        if not self._is_visible:
            self._is_visible = True
            self._on_screen_shown()
            self.screen_shown.emit()
            
    def hideEvent(self, event):
        """Handle screen hide event."""
        super().hideEvent(event)
        if self._is_visible:
            self._is_visible = False
            self._on_screen_hidden()
            self.screen_hidden.emit()
            
    def _on_screen_shown(self):
        """Handle screen shown. Override in subclasses."""
        self.load_data()
        
    def _on_screen_hidden(self):
        """Handle screen hidden. Override in subclasses."""
        pass
    
    def load_data(self, params: Optional[Dict] = None):
        """Load screen data. Override in subclasses."""
        self.set_state(ScreenState.READY)
        
    def refresh_data(self):
        """Refresh screen data."""
        self.load_data()
        
    def set_auto_refresh(self, interval_seconds: int):
        """Set auto-refresh interval. 0 to disable."""
        self._auto_refresh_interval = interval_seconds
        
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer.deleteLater()
            self._refresh_timer = None
            
        if interval_seconds > 0:
            self._refresh_timer = QTimer(self)
            self._refresh_timer.timeout.connect(self.refresh_data)
            self._refresh_timer.start(interval_seconds * 1000)
            
    def cache_data(self, key: str, data: Any):
        """Cache data for quick access."""
        self._data_cache[key] = data
        
    def get_cached_data(self, key: str, default: Any = None) -> Any:
        """Get cached data."""
        return self._data_cache.get(key, default)
        
    def clear_cache(self):
        """Clear data cache."""
        self._data_cache.clear()
        
    def set_loading(self, loading: bool):
        """Set loading state."""
        if loading:
            self.set_state(ScreenState.LOADING)
        else:
            self.set_state(ScreenState.READY)
            
    def show_error(self, message: str):
        """Show error message."""
        logger.error(f"Screen {self._screen_id} error: {message}")
        self.set_state(ScreenState.ERROR)
        
    def show_empty(self, message: str = "No data available"):
        """Show empty state."""
        logger.info(f"Screen {self._screen_id} empty: {message}")
        self.set_state(ScreenState.EMPTY)
        
    def show_loading(self, message: str = "Loading..."):
        """Show loading state with optional message."""
        logger.debug(f"Screen {self._screen_id} loading: {message}")
        self.set_state(ScreenState.LOADING)
        # Emit a signal that can be connected to show skeleton loaders or spinners
        self.data_requested.emit({"action": "show_loading", "message": message})
        
    def show_skeleton_loader(self, show: bool = True):
        """Show or hide skeleton loader."""
        logger.debug(f"Screen {self._screen_id} skeleton loader: {show}")
        # This would typically trigger showing skeleton UI elements
        self.data_requested.emit({"action": "set_skeleton_visible", "visible": show})


class BaseFormScreen(BaseScreen):
    """
    Base class for form-based screens (create/edit forms).
    """
    
    form_submitted = Signal(dict)
    form_validated = Signal(dict)
    form_cancelled = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None, screen_id: str = "", config: Optional[Dict] = None):
        self._form_data: Dict[str, Any] = {}
        self._original_data: Optional[Dict] = None
        self._is_edit_mode = False
        super().__init__(parent, screen_id, config)
        
    def set_edit_mode(self, is_edit: bool, original_data: Optional[Dict] = None):
        """Set edit mode and original data."""
        self._is_edit_mode = is_edit
        self._original_data = original_data
        if is_edit and original_data:
            self._populate_form(original_data)
            
    def is_edit_mode(self) -> bool:
        """Check if in edit mode."""
        return self._is_edit_mode
    
    def _populate_form(self, data: Dict):
        """Populate form with data."""
        self._form_data = data.copy()
        
    def get_form_data(self) -> Dict[str, Any]:
        """Get form data."""
        return self._form_data
    
    def set_form_field(self, field: str, value: Any):
        """Set form field value."""
        self._form_data[field] = value
        
    def get_form_field(self, field: str, default: Any = None) -> Any:
        """Get form field value."""
        return self._form_data.get(field, default)
        
    def validate_form(self) -> tuple[bool, Dict[str, str]]:
        """Validate entire form. Returns (is_valid, errors_dict)."""
        return True, {}
        
    def submit_form(self):
        """Submit form data."""
        is_valid, errors = self.validate_form()
        
        if is_valid:
            self.form_validated.emit(self._form_data)
            self.form_submitted.emit(self._form_data)
            return True
        else:
            for field, error in errors.items():
                self.show_field_error(field, error)
            return False
            
    def show_field_error(self, field: str, error: str):
        """Show field error."""
        logger.warning(f"Form field error - {field}: {error}")
        
    def reset_form(self):
        """Reset form to initial state."""
        self._form_data.clear()
        self._original_data = None
        self._is_edit_mode = False
        
    def cancel_form(self):
        """Cancel form operation."""
        self.form_cancelled.emit()


class BaseListScreen(BaseScreen):
    """
    Base class for list-based screens (tables, grids).
    """
    
    item_selected = Signal(object)
    item_action_requested = Signal(str, object)
    bulk_action_requested = Signal(str, list)
    
    def __init__(self, parent: Optional[QWidget] = None, screen_id: str = "", config: Optional[Dict] = None):
        self._items: list = []
        self._filtered_items: list = []
        self._selected_items: list = []
        self._sort_column: str = ""
        self._sort_order: str = "asc"
        self._filters: Dict[str, Any] = {}
        self._search_query: str = ""
        self._page: int = 1
        self._page_size: int = 50
        self._total_count: int = 0
        
        config = config or {}
        config.setdefault('pagination', True)
        config.setdefault('sorting', True)
        config.setdefault('filtering', True)
        config.setdefault('selection', True)
        
        super().__init__(parent, screen_id, config)
        
    @property
    def items(self) -> list:
        """Get all items."""
        return self._items
    
    @property
    def filtered_items(self) -> list:
        """Get filtered items."""
        return self._filtered_items
    
    @property
    def selected_items(self) -> list:
        """Get selected items."""
        return self._selected_items
    
    def set_items(self, items: list):
        """Set items."""
        self._items = items
        self._apply_filters()
        
    def get_item_at(self, index: int) -> Optional[Any]:
        """Get item at index."""
        if 0 <= index < len(self._filtered_items):
            return self._filtered_items[index]
        return None
    
    def select_item(self, item):
        """Select item."""
        if item not in self._selected_items:
            self._selected_items.append(item)
            self.item_selected.emit(item)
            
    def deselect_item(self, item):
        """Deselect item."""
        if item in self._selected_items:
            self._selected_items.remove(item)
            
    def clear_selection(self):
        """Clear selection."""
        self._selected_items.clear()
        
    def select_all(self):
        """Select all filtered items."""
        self._selected_items = self._filtered_items.copy()
        
    def is_all_selected(self) -> bool:
        """Check if all filtered items are selected."""
        return len(self._selected_items) == len(self._filtered_items) > 0
    
    def set_filter(self, key: str, value: Any):
        """Set filter."""
        self._filters[key] = value
        self._page = 1
        self._apply_filters()
        
    def clear_filters(self):
        """Clear all filters."""
        self._filters.clear()
        self._page = 1
        self._apply_filters()
        
    def set_search(self, query: str):
        """Set search query."""
        self._search_query = query
        self._page = 1
        self._apply_filters()
        
    def sort_by(self, column: str, order: str = "asc"):
        """Sort by column."""
        self._sort_column = column
        self._sort_order = order
        self._apply_filters()
        
    def set_page(self, page: int):
        """Set current page."""
        self._page = page
        self._apply_filters()
        
    def next_page(self):
        """Go to next page."""
        max_page = (self._total_count + self._page_size - 1) // self._page_size
        if self._page < max_page:
            self._page += 1
            self._apply_filters()
            
    def previous_page(self):
        """Go to previous page."""
        if self._page > 1:
            self._page -= 1
            self._apply_filters()
            
    def get_pagination_info(self) -> Dict[str, Any]:
        """Get pagination info."""
        max_page = max(1, (self._total_count + self._page_size - 1) // self._page_size)
        return {
            'current_page': self._page,
            'total_pages': max_page,
            'page_size': self._page_size,
            'total_count': self._total_count,
            'has_next': self._page < max_page,
            'has_previous': self._page > 1
        }
    
    def _apply_filters(self):
        """Apply filters and search to items."""
        self._filtered_items = self._items.copy()
        # Override in subclasses for actual filtering
        
    def refresh_list(self):
        """Refresh list data."""
        self.load_data()
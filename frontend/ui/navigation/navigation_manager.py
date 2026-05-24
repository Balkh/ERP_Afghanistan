"""
Navigation Manager for page routing and history management.
Provides consistent navigation across all screens.
"""

from PySide6.QtCore import Signal, QObject
from typing import Optional, Dict, Callable, Any
import logging

logger = logging.getLogger(__name__)


class NavigationHistory:
    """Navigation history manager."""
    
    def __init__(self, max_size: int = 50):
        self._max_size = max_size
        self._back_stack: list = []
        self._forward_stack: list = []
        
    def push(self, screen_id: str, params: Dict = None):
        """Push new navigation to back stack."""
        self._back_stack.append({'screen_id': screen_id, 'params': params or {}})
        self._forward_stack.clear()
        
        if len(self._back_stack) > self._max_size:
            self._back_stack.pop(0)
            
    def back(self) -> Optional[Dict]:
        """Navigate back."""
        if not self._back_stack:
            return None
            
        current = self._back_stack.pop()
        self._forward_stack.append(current)
        
        if self._back_stack:
            return self._back_stack[-1]
        return None
        
    def forward(self) -> Optional[Dict]:
        """Navigate forward."""
        if not self._forward_stack:
            return None
            
        next_nav = self._forward_stack.pop()
        self._back_stack.append(next_nav)
        return next_nav
        
    def can_go_back(self) -> bool:
        """Check if can go back."""
        return len(self._back_stack) > 1
        
    def can_go_forward(self) -> bool:
        """Check if can go forward."""
        return len(self._forward_stack) > 0
        
    def clear(self):
        """Clear history."""
        self._back_stack.clear()
        self._forward_stack.clear()
        
    def get_back_count(self) -> int:
        """Get back stack size."""
        return len(self._back_stack)
        
    def get_forward_count(self) -> int:
        """Get forward stack size."""
        return len(self._forward_stack)


class NavigationManager(QObject):
    """
    Navigation manager for managing screen transitions and history.
    """
    
    # Signals for navigation events
    navigation_changed = Signal(str, dict)
    screen_changed = Signal(str, dict)
    history_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_screen: Optional[str] = None
        self._current_params: Dict = {}
        self._history = NavigationHistory()
        self._screen_factory: Optional[Callable] = None
        self._screen_cache: Dict[str, Any] = {}
        self._preserve_screen_state = True
        
    def set_screen_factory(self, factory: Callable):
        """Set screen factory function."""
        self._screen_factory = factory
        
    def navigate_to(self, screen_id: str, params: Dict = None):
        """Navigate to screen."""
        params = params or {}
        
        logger.info(f"Navigating to {screen_id} with params: {params}")
        
        # Add to history
        if self._current_screen:
            self._history.push(self._current_screen, self._current_params)
            
        # Update current
        __old_screen = self._current_screen
        self._current_screen = screen_id
        self._current_params = params
        
        # Emit signals
        self.navigation_changed.emit(screen_id, params)
        self.screen_changed.emit(screen_id, params)
        self.history_changed.emit()
        
    def go_back(self):
        """Navigate back in history."""
        if self._history.can_go_back():
            prev = self._history.back()
            if prev:
                self._current_screen = prev['screen_id']
                self._current_params = prev['params']
                self.screen_changed.emit(self._current_screen, self._current_params)
                self.history_changed.emit()
                
    def go_forward(self):
        """Navigate forward in history."""
        if self._history.can_go_forward():
            next_nav = self._history.forward()
            if next_nav:
                self._current_screen = next_nav['screen_id']
                self._current_params = next_nav['params']
                self.screen_changed.emit(self._current_screen, self._current_params)
                self.history_changed.emit()
                
    def can_go_back(self) -> bool:
        """Check if can go back."""
        return self._history.can_go_back()
        
    def can_go_forward(self) -> bool:
        """Check if can go forward."""
        return self._history.can_go_forward()
        
    @property
    def current_screen(self) -> Optional[str]:
        """Get current screen ID."""
        return self._current_screen
        
    @property
    def current_params(self) -> Dict:
        """Get current navigation params."""
        return self._current_params.copy()
        
    def get_screen(self, screen_id: str, params: Dict = None) -> Any:
        """Get or create screen instance."""
        params = params or {}
        
        if self._screen_factory:
            return self._screen_factory(screen_id, params)
        return None
        
    def cache_screen(self, screen_id: str, screen_instance: Any):
        """Cache screen instance."""
        self._screen_cache[screen_id] = screen_instance
        
    def get_cached_screen(self, screen_id: str) -> Optional[Any]:
        """Get cached screen."""
        return self._screen_cache.get(screen_id)
        
    def clear_cache(self):
        """Clear screen cache."""
        self._screen_cache.clear()
        
    def set_preserve_state(self, preserve: bool):
        """Set whether to preserve screen state."""
        self._preserve_screen_state = preserve
        
    def reset(self):
        """Reset navigation."""
        self._current_screen = None
        self._current_params = {}
        self._history.clear()
        self.history_changed.emit()


class NavigationHelper:
    """Helper class for common navigation operations."""
    
    @staticmethod
    def create_dashboard_navigation() -> Dict[str, Any]:
        """Create dashboard navigation config."""
        return {'screen_id': 'dashboard', 'params': {}}
        
    @staticmethod
    def create_screen_navigation(screen_id: str, params: Dict = None) -> Dict[str, Any]:
        """Create screen navigation config."""
        return {'screen_id': screen_id, 'params': params or {}}
        
    @staticmethod
    def create_back_navigation() -> Dict[str, Any]:
        """Create back navigation config."""
        return {'action': 'back'}
        
    @staticmethod
    def create_refresh_navigation() -> Dict[str, Any]:
        """Create refresh navigation config."""
        return {'action': 'refresh'}
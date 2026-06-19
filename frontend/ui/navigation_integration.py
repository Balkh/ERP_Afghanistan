"""
Navigation Integration — Recent Items tracking.

This module previously monkey-patched NavigationHistory.push() and provided
convenience functions. Both are now removed:
- The monkey-patch caused triple writes per navigation event.
- Convenience functions were dead code (never called by production code).

The single write point is main_window.py:change_page() → storage.add_screen().
"""

from .navigation_history import NavigationHistory


class NavigationIntegration:
    """Integration layer for recent items functionality.
    
    NOTE: This class is intentionally minimal. The actual recent item write
    happens in main_window.py:change_page() via a direct call to
    recent_items_storage.add_screen(). This class exists only for backward
    compatibility with existing imports.
    """
    
    def __init__(self, navigation_history: NavigationHistory, storage=None):
        self._navigation_history = navigation_history
        self._storage = storage

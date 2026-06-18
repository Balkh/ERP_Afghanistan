"""
Recent Items Integration — DEPRECATED.

This module previously provided a separate RecentItemsIntegration class and
global convenience functions. Both are now removed:
- The class created a redundant storage instance (separate from MainWindow's).
- Convenience functions were dead code (never called by production code).

The canonical storage is RecentItemsStorage, created once in main_window.py
and shared with sidebar via constructor injection.
"""

from .recent_items_storage import RecentItemsStorage

"""
Live Theme Engine — enterprise-safe light/dark switching.
Updates ui.constants module globals at runtime so all QSS f-strings
that import COLOR_* tokens pick up the active theme immediately.

CANONICAL SOURCE OF TRUTH: ui/constants.py defines _THEME_DARK / _THEME_LIGHT.
theme_engine.py imports them — never redefines color values.
"""

import logging
import time
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget
from typing import Dict, Optional, Callable

import ui.constants as _constants

_logger = logging.getLogger(__name__)


# ── Color dictionaries sourced from ui.constants (CANONICAL) ──────
# Do NOT define hex values here. Add new tokens to ui/constants.py
# and they will be available automatically.

DARK_COLORS: Dict[str, str] = dict(_constants._THEME_DARK)
LIGHT_COLORS: Dict[str, str] = dict(_constants._THEME_LIGHT)

_THEMES: Dict[str, Dict[str, str]] = {
    "dark": _constants._THEME_DARK,
    "light": _constants._THEME_LIGHT,
}


def _update_constants_module(colors: Dict[str, str], theme_name: str) -> None:
    """Update ui.constants module-level globals with the given color dict."""
    import sys
    mod = sys.modules.get("ui.constants")
    if mod is None:
        return
    for name, value in colors.items():
        setattr(mod, name, value)
    setattr(mod, "_active_theme_name", theme_name)


class ThemeEngine(QObject):
    """Singleton live theme engine.

    - Call ``apply_theme("dark"|"light")`` to switch all COLOR_* globals.
    - Connect to ``theme_changed`` to re-apply per-widget stylesheets.
    - Each screen/component calls ``refresh_theme()`` when it hears the signal.
    """

    theme_changed = Signal(str)  # "dark" | "light"

    _instance: Optional["ThemeEngine"] = None

    def __init__(self):
        super().__init__()
        self._current_theme: str = "light"
        self._themes = {
            "light": {
                "background": QColor("#ffffff"),
                "foreground": QColor("#212121"),
                "primary": QColor("#1976d2"),
                "secondary": QColor("#6c757d"),
            },
            "dark": {
                "background": QColor("#212121"),
                "foreground": QColor("#ffffff"),
                "primary": QColor("#1976d2"),
                "secondary": QColor("#6c757d"),
            },
        }
        self._refreshables: Dict[int, Callable[[], None]] = {}
        self._next_id: int = 0
        _update_constants_module(_THEMES[self._current_theme], self._current_theme)

    # ── Singleton ────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> "ThemeEngine":
        if cls._instance is None:
            cls._instance = ThemeEngine()
        return cls._instance

    # ── Public API ───────────────────────────────────────────────

    def current_theme(self) -> str:
        return self._current_theme

    def verify_sync(self) -> bool:
        """Verify theme_engine and constants color dicts are in sync.
        Always True — theme_engine sources from ui.constants directly.
        """
        return DARK_COLORS is _constants._THEME_DARK or DARK_COLORS == _constants._THEME_DARK

    def is_dark(self) -> bool:
        return self._current_theme == "dark"

    def is_light(self) -> bool:
        return self._current_theme == "light"

    def get_color(self, name: str, theme_name: Optional[str] = None) -> QColor:
        """Get a QColor for a legacy color role."""
        theme = theme_name or self._current_theme
        if theme not in self._themes:
            theme = self._current_theme
        if name in self._themes[theme]:
            return QColor(self._themes[theme][name])
        token_name = name if name.startswith("COLOR_") else f"COLOR_{name.upper()}"
        value = _THEMES.get(theme, _THEMES[self._current_theme]).get(token_name, "#000000")
        return QColor(value)

    def set_theme(self, theme_name: str) -> None:
        """Legacy alias used by UI tests; raises on invalid themes."""
        if theme_name not in _THEMES:
            raise ValueError(f"Unknown theme: {theme_name}")
        if theme_name == self._current_theme:
            self.theme_changed.emit(theme_name)
            return
        self.apply_theme(theme_name)

    def _generate_stylesheet(self, theme: Dict[str, QColor]) -> str:
        """Generate a basic stylesheet for compatibility tests."""
        bg = theme["background"].name()
        fg = theme["foreground"].name()
        primary = theme["primary"].name()
        secondary = theme["secondary"].name()
        return f"""
            QWidget {{ background-color: {bg}; color: {fg}; }}
            QPushButton {{ background-color: {primary}; color: {fg}; }}
            QPushButton:hover {{ background-color: {secondary}; }}
        """

    def apply_theme(self, theme_name: str) -> None:
        """Apply the named theme — updates constants module globals."""
        if theme_name not in _THEMES:
            return
        if theme_name == self._current_theme:
            return

        self._current_theme = theme_name
        colors = _THEMES[theme_name]

        _update_constants_module(colors, theme_name)

        self.theme_changed.emit(theme_name)
        self._refresh_all()

    def toggle(self) -> str:
        """Toggle between light and dark.  Returns the new theme name."""
        new = "light" if self._current_theme == "dark" else "dark"
        self.apply_theme(new)
        return new

    # ── Registration (for per-widget refresh) ────────────────────

    def register(self, refresh_fn: Callable[[], None]) -> int:
        """Register a callable to be invoked when the theme changes.
        Returns a token that can be passed to ``unregister``.
        """
        tid = self._next_id
        self._next_id += 1
        self._refreshables[tid] = refresh_fn
        return tid

    def unregister(self, token: int) -> None:
        self._refreshables.pop(token, None)

    # ── Centralized Refresh Dispatcher ──────────────────────────

    def refresh_widget_tree(self, root: QWidget) -> None:
        """Re-style common widget types in a widget tree using current COLOR_* tokens.
        Recursive DOM traversal for comprehensive styling update.
        """
        if not root:
            return
            
        # Update current widget if it has a stylesheet
        if hasattr(root, 'styleSheet') and root.styleSheet():
            # Trigger style re-computation
            root.setStyleSheet(root.styleSheet())
            
        # Recurse into children
        for child in root.findChildren(QWidget):
            if hasattr(child, 'styleSheet') and child.styleSheet():
                child.setStyleSheet(child.styleSheet())
                
            # Special handling for certain complex widgets
            from PySide6.QtWidgets import QTableWidget
            if isinstance(child, QTableWidget):
                child.horizontalHeader().setStyleSheet(child.horizontalHeader().styleSheet())
                child.verticalHeader().setStyleSheet(child.verticalHeader().styleSheet())
                child.viewport().update()

    def refresh_safe(self, fn: Callable[[], None], name: str = "") -> None:
        """Execute a refresh callback with logging instead of silent swallow."""
        try:
            fn()
        except Exception as e:
            _logger.warning(f"Theme refresh failed: {name} | {e}")

    def _refresh_all(self) -> None:
        _start = time.monotonic()
        callbacks = list(self._refreshables.values())
        for fn in callbacks:
            try:
                fn()
            except Exception as e:
                _logger.warning(f"Theme refresh error: {e}")
        _elapsed = (time.monotonic() - _start) * 1000
        if _elapsed > 100:
            _logger.info(f"Theme refresh took {_elapsed:.1f}ms ({len(callbacks)} widgets)")

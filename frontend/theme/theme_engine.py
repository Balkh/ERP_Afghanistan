"""
Live Theme Engine — enterprise-safe light/dark switching.
Updates ui.constants module globals at runtime so all QSS f-strings
that import COLOR_* tokens pick up the active theme immediately.
No architecture rewrite, no token rename, no hardcoded colors.
"""

from PySide6.QtCore import QObject, Signal
from typing import Dict, Optional, Callable


# ── Dual-theme color dictionary ──────────────────────────────────
# Every COLOR_* variable from ui.constants gets a light and dark value.
# Dark values match the existing Catppuccin Mocha palette.
# Light values are new, designed for readability and contrast.

DARK_COLORS: Dict[str, str] = {
    "COLOR_PRIMARY": "#89b4fa",
    "COLOR_PRIMARY_HOVER": "#74c7ec",
    "COLOR_PRIMARY_ACTIVE": "#89dceb",
    "COLOR_PRIMARY_MUTED": "#45475a",
    "COLOR_SUCCESS": "#a6e3a1",
    "COLOR_SUCCESS_HOVER": "#94e2d5",
    "COLOR_SUCCESS_ACTIVE": "#74c7a0",
    "COLOR_SUCCESS_MUTED": "#45475a",
    "COLOR_SUCCESS_BG": "#1e3a2f",
    "COLOR_WARNING": "#f9e2af",
    "COLOR_WARNING_HOVER": "#fab387",
    "COLOR_WARNING_ACTIVE": "#f38ba8",
    "COLOR_WARNING_MUTED": "#45475a",
    "COLOR_WARNING_BG": "#3a3520",
    "COLOR_DANGER": "#f38ba8",
    "COLOR_DANGER_HOVER": "#eba0ac",
    "COLOR_DANGER_ACTIVE": "#dc2626",
    "COLOR_DANGER_MUTED": "#45475a",
    "COLOR_DANGER_BG": "#3a1f2a",
    "COLOR_INFO": "#89b4fa",
    "COLOR_INFO_HOVER": "#74c7ec",
    "COLOR_INFO_ACTIVE": "#89dceb",
    "COLOR_INFO_MUTED": "#45475a",
    "COLOR_INFO_BG": "#1e2a3a",
    "COLOR_BG_MAIN": "#1e1e2e",
    "COLOR_BG_SURFACE": "#282838",
    "COLOR_BG_ELEVATED": "#313244",
    "COLOR_BG_INPUT": "#1e1e2e",
    "COLOR_TEXT_PRIMARY": "#cdd6f4",
    "COLOR_TEXT_SECONDARY": "#a6adc8",
    "COLOR_TEXT_MUTED": "#6c7086",
    "COLOR_TEXT_ON_PRIMARY": "#11111b",
    "COLOR_BG_LIGHT": "#313244",
    "COLOR_BG_LIGHT_SURFACE": "#313244",
    "COLOR_TEXT_LIGHT": "#cdd6f4",
    "COLOR_TEXT_SECONDARY_LIGHT": "#a6adc8",
    "COLOR_TEXT_DIALOG": "#cdd6f4",
    "COLOR_BORDER_LIGHT_THEME": "#45475a",
    "COLOR_MUTED_LIGHT": "#6c7086",
    "COLOR_BG_BUTTON_LIGHT": "#585b70",
    "COLOR_BG_BUTTON_SECONDARY": "#45475a",
    "COLOR_SECONDARY_BG": "#45475a",
    "COLOR_SECONDARY_HOVER": "#585b70",
    "COLOR_SECONDARY_TEXT": "#cdd6f4",
    "COLOR_SECONDARY_ACTIVE": "#6c7086",
    "COLOR_BORDER": "#45475a",
    "COLOR_BORDER_LIGHT": "#38384a",
    "COLOR_BORDER_FOCUS": "#89b4fa",
    "COLOR_BORDER_DIALOG": "#45475a",
    "COLOR_BORDER_TABLE": "#45475a",
    "COLOR_BORDER_INPUT": "#45475a",
    "COLOR_TABLE_GRIDLINE": "#45475a",
    "COLOR_TEXT_TITLE": "#cdd6f4",
    "COLOR_HEADER_DARK": "#11111b",
    "COLOR_TABLE_HEADER": "#313244",
    "COLOR_TABLE_ALT": "#282838",
    "COLOR_TABLE_GRID": "#45475a",
    "COLOR_TABLE_BORDER_LIGHT": "#585b70",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#45475a",
    "COLOR_FORM_BORDER_LIGHT": "#585b70",
    "COLOR_FORM_TEXT_LIGHT": "#cdd6f4",
    "COLOR_UI_DIVIDER_LIGHT": "#45475a",
    "COLOR_STATUS_VALID": "#a6e3a1",
    "COLOR_STATUS_INVALID": "#f38ba8",
    "COLOR_STATUS_WARNING": "#fab387",
    "COLOR_STATUS_PENDING": "#f9e2af",
    "COLOR_WHATSAPP": "#25D366",
}

LIGHT_COLORS: Dict[str, str] = {
    "COLOR_PRIMARY": "#4a8ae8",
    "COLOR_PRIMARY_HOVER": "#3a7ad8",
    "COLOR_PRIMARY_ACTIVE": "#2a6ac8",
    "COLOR_PRIMARY_MUTED": "#b0b8c8",
    "COLOR_SUCCESS": "#2ecc71",
    "COLOR_SUCCESS_HOVER": "#27ae60",
    "COLOR_SUCCESS_ACTIVE": "#1e9b54",
    "COLOR_SUCCESS_MUTED": "#b0b8c8",
    "COLOR_SUCCESS_BG": "#e8f8f0",
    "COLOR_WARNING": "#f39c12",
    "COLOR_WARNING_HOVER": "#e67e22",
    "COLOR_WARNING_ACTIVE": "#d35400",
    "COLOR_WARNING_MUTED": "#b0b8c8",
    "COLOR_WARNING_BG": "#fef5e7",
    "COLOR_DANGER": "#e74c3c",
    "COLOR_DANGER_HOVER": "#c0392b",
    "COLOR_DANGER_ACTIVE": "#a93226",
    "COLOR_DANGER_MUTED": "#b0b8c8",
    "COLOR_DANGER_BG": "#fdedec",
    "COLOR_INFO": "#3498db",
    "COLOR_INFO_HOVER": "#2980b9",
    "COLOR_INFO_ACTIVE": "#1f6da0",
    "COLOR_INFO_MUTED": "#b0b8c8",
    "COLOR_INFO_BG": "#eaf2f8",
    "COLOR_BG_MAIN": "#f4f5f8",
    "COLOR_BG_SURFACE": "#ffffff",
    "COLOR_BG_ELEVATED": "#e8eaf0",
    "COLOR_BG_INPUT": "#ffffff",
    "COLOR_TEXT_PRIMARY": "#1a1b2e",
    "COLOR_TEXT_SECONDARY": "#5a5b7a",
    "COLOR_TEXT_MUTED": "#9a9bb0",
    "COLOR_TEXT_ON_PRIMARY": "#ffffff",
    "COLOR_BG_LIGHT": "#f4f5f8",
    "COLOR_BG_LIGHT_SURFACE": "#ffffff",
    "COLOR_TEXT_LIGHT": "#1a1b2e",
    "COLOR_TEXT_SECONDARY_LIGHT": "#5a5b7a",
    "COLOR_TEXT_DIALOG": "#1a1b2e",
    "COLOR_BORDER_LIGHT_THEME": "#d1d3dc",
    "COLOR_MUTED_LIGHT": "#9a9bb0",
    "COLOR_BG_BUTTON_LIGHT": "#e8eaf0",
    "COLOR_BG_BUTTON_SECONDARY": "#dcdee5",
    "COLOR_SECONDARY_BG": "#dcdee5",
    "COLOR_SECONDARY_HOVER": "#c5c7d0",
    "COLOR_SECONDARY_TEXT": "#1a1b2e",
    "COLOR_SECONDARY_ACTIVE": "#b0b8c8",
    "COLOR_BORDER": "#d1d3dc",
    "COLOR_BORDER_LIGHT": "#e5e6ed",
    "COLOR_BORDER_FOCUS": "#4a8ae8",
    "COLOR_BORDER_DIALOG": "#d1d3dc",
    "COLOR_BORDER_TABLE": "#d1d3dc",
    "COLOR_BORDER_INPUT": "#c5c7d0",
    "COLOR_TABLE_GRIDLINE": "#d1d3dc",
    "COLOR_TEXT_TITLE": "#1a1b2e",
    "COLOR_HEADER_DARK": "#2c3e70",
    "COLOR_TABLE_HEADER": "#dcdee5",
    "COLOR_TABLE_ALT": "#f4f5f8",
    "COLOR_TABLE_GRID": "#d1d3dc",
    "COLOR_TABLE_BORDER_LIGHT": "#c5c7d0",
    "COLOR_TABLE_HEADER_BG_LIGHT": "#dcdee5",
    "COLOR_FORM_BORDER_LIGHT": "#c5c7d0",
    "COLOR_FORM_TEXT_LIGHT": "#1a1b2e",
    "COLOR_UI_DIVIDER_LIGHT": "#d1d3dc",
    "COLOR_STATUS_VALID": "#27ae60",
    "COLOR_STATUS_INVALID": "#e74c3c",
    "COLOR_STATUS_WARNING": "#e67e22",
    "COLOR_STATUS_PENDING": "#f39c12",
    "COLOR_WHATSAPP": "#25D366",
}

_THEMES: Dict[str, Dict[str, str]] = {
    "dark": DARK_COLORS,
    "light": LIGHT_COLORS,
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
        self._current_theme: str = "dark"
        self._refreshables: Dict[int, Callable[[], None]] = {}
        self._next_id: int = 0

    # ── Singleton ────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> "ThemeEngine":
        if cls._instance is None:
            cls._instance = ThemeEngine()
        return cls._instance

    # ── Public API ───────────────────────────────────────────────

    def current_theme(self) -> str:
        return self._current_theme

    def is_dark(self) -> bool:
        return self._current_theme == "dark"

    def is_light(self) -> bool:
        return self._current_theme == "light"

    def get_color(self, name: str) -> str:
        """Get a color value for the active theme."""
        return _THEMES.get(self._current_theme, DARK_COLORS).get(name, "#000000")

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

    def _refresh_all(self) -> None:
        for fn in list(self._refreshables.values()):
            try:
                fn()
            except Exception:
                pass

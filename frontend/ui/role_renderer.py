"""
Role-Based UI Renderer — dynamically shows/hides sidebar items, screens, and actions
based on the user's ui_scopes from the AuthManager.

Usage:
    renderer = RoleRenderer(auth_manager, sidebar, main_window)
    renderer.apply_scopes()  # Call after login or ui_scopes_changed signal
"""

from typing import Dict, List

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from utils.logger import get_logger

log = get_logger('role_renderer')


class RoleRenderer(QObject):
    """Applies role-based visibility rules to UI components."""

    def __init__(self, auth_manager, sidebar=None, main_window=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.sidebar = sidebar
        self.main_window = main_window
        self._screen_registry: Dict[str, QWidget] = {}
        self._action_registry: Dict[str, QWidget] = {}

    def register_screen(self, screen_name: str, widget: QWidget) -> None:
        """Register a screen widget for visibility control."""
        self._screen_registry[screen_name] = widget

    def register_action(self, action_key: str, widget: QWidget) -> None:
        """Register an action widget (button, menu item) for visibility control."""
        self._action_registry[action_key] = widget

    def apply_scopes(self) -> None:
        """Apply current ui_scopes to all registered components."""
        if not self.auth_manager.is_authenticated:
            self._hide_all()
            return

        self._apply_sidebar()
        self._apply_screens()
        self._apply_actions()

    def is_module_visible(self, module: str) -> bool:
        """Check if a module should be visible."""
        return self.auth_manager.has_access(module)

    def is_screen_visible(self, screen: str) -> bool:
        """Check if a screen should be visible."""
        return self.auth_manager.has_screen_access(screen)

    def is_action_visible(self, module: str, action: str) -> bool:
        """Check if an action should be visible."""
        return self.auth_manager.has_action(module, action)

    # ── Internal ──

    def _apply_sidebar(self) -> None:
        """Show/hide sidebar items based on visible modules."""
        if not self.sidebar:
            return

        visible = set(self.auth_manager.get_visible_modules())
        hidden = set(self.auth_manager.get_hidden_modules())

        try:
            if hasattr(self.sidebar, 'set_module_visibility'):
                for module in hidden:
                    self.sidebar.set_module_visibility(module, False)
                for module in visible:
                    self.sidebar.set_module_visibility(module, True)
            elif hasattr(self.sidebar, 'items'):
                for item in self.sidebar.items:
                    module = getattr(item, 'module_name', None)
                    if module:
                        item.setVisible(module in visible)
        except Exception as e:
            log.error(f"Error applying sidebar scopes: {e}")

    def _apply_screens(self) -> None:
        """Show/hide registered screen widgets."""
        for screen_name, widget in self._screen_registry.items():
            is_visible = self.auth_manager.has_screen_access(screen_name)
            widget.setVisible(is_visible)
            widget.setEnabled(is_visible)

    def _apply_actions(self) -> None:
        """Show/hide registered action widgets."""
        for action_key, widget in self._action_registry.items():
            parts = action_key.split(":")
            if len(parts) == 2:
                module, action = parts
                is_visible = self.auth_manager.has_action(module, action)
            else:
                is_visible = self.auth_manager.has_access(action_key)
            widget.setVisible(is_visible)
            widget.setEnabled(is_visible)

    def _hide_all(self) -> None:
        """Hide all registered components (logged-out state)."""
        for widget in self._screen_registry.values():
            widget.setVisible(False)
            widget.setEnabled(False)
        for widget in self._action_registry.values():
            widget.setVisible(False)
            widget.setEnabled(False)

    def filter_menu_items(self, items: List[Dict]) -> List[Dict]:
        """Filter a list of menu items to only include visible ones.

        Each item dict should have a 'module' or 'screen' key.
        """
        result = []
        for item in items:
            module = item.get("module")
            screen = item.get("screen")
            if module and self.auth_manager.has_access(module):
                result.append(item)
            elif screen and self.auth_manager.has_screen_access(screen):
                result.append(item)
        return result

"""
Unit tests for extracted sidebar modules:
  - ui.sidebar.navigation_data
  - ui.sidebar.sidebar_styles
  - ui.sidebar.group_renderer
"""

import inspect
import re
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────
# Navigation Data Tests
# ─────────────────────────────────────────────────────────────────────

class TestNavigationGroups:
    """Tests for NAVIGATION_GROUPS structure and data integrity."""

    def test_all_groups_have_title_and_items(self):
        from ui.sidebar.navigation_data import NAVIGATION_GROUPS
        for group_name, group_data in NAVIGATION_GROUPS.items():
            assert "title" in group_data, f"{group_name} missing 'title'"
            assert "items" in group_data, f"{group_name} missing 'items'"
            assert isinstance(group_data["title"], str)
            assert isinstance(group_data["items"], list)
            assert len(group_data["items"]) > 0, f"{group_name} has no items"

    def test_all_items_are_3_tuples(self):
        from ui.sidebar.navigation_data import NAVIGATION_GROUPS
        for group_name, group_data in NAVIGATION_GROUPS.items():
            for item in group_data["items"]:
                assert isinstance(item, tuple), f"{group_name}: item is not a tuple"
                assert len(item) == 3, f"{group_name}: item {item} is not a 3-tuple"
                title, page_id, page_index = item
                assert isinstance(title, str) and len(title) > 0
                assert isinstance(page_id, str) and len(page_id) > 0
                assert isinstance(page_index, int) and page_index >= 0

    def test_all_page_indices_are_unique(self):
        from ui.sidebar.navigation_data import NAVIGATION_GROUPS
        seen_indices = {}
        for group_name, group_data in NAVIGATION_GROUPS.items():
            for title, page_id, page_index in group_data["items"]:
                if page_index in seen_indices:
                    prev = seen_indices[page_index]
                    pytest.fail(
                        f"Duplicate page_index {page_index}: "
                        f"'{page_id}' in {group_name} conflicts with "
                        f"'{prev[1]}' in {prev[0]}"
                    )
                seen_indices[page_index] = (group_name, page_id)

    def test_all_page_ids_are_unique(self):
        from ui.sidebar.navigation_data import NAVIGATION_GROUPS
        seen_ids = {}
        for group_name, group_data in NAVIGATION_GROUPS.items():
            for title, page_id, page_index in group_data["items"]:
                if page_id in seen_ids:
                    prev = seen_ids[page_id]
                    pytest.fail(
                        f"Duplicate page_id '{page_id}': "
                        f"index {page_index} in {group_name} conflicts with "
                        f"index {prev[1]} in {prev[0]}"
                    )
                seen_ids[page_id] = (group_name, page_index)

    def test_expected_groups_exist(self):
        from ui.sidebar.navigation_data import NAVIGATION_GROUPS
        expected = {
            "inventory", "sales", "purchases", "returns",
            "accounting", "reports", "finance", "hr",
            "hr_reports", "payroll_reports", "system",
        }
        assert set(NAVIGATION_GROUPS.keys()) == expected

    def test_dashboard_index_zero(self):
        from ui.sidebar.navigation_data import NAVIGATION_GROUPS
        # Dashboard is standalone, not in groups — verify it's not in any group
        for group_name, group_data in NAVIGATION_GROUPS.items():
            for title, page_id, page_index in group_data["items"]:
                assert page_id != "dashboard", "dashboard should not be in any group"

    def test_specific_group_sizes(self):
        from ui.sidebar.navigation_data import NAVIGATION_GROUPS
        assert len(NAVIGATION_GROUPS["inventory"]["items"]) == 4
        assert len(NAVIGATION_GROUPS["sales"]["items"]) == 3
        assert len(NAVIGATION_GROUPS["purchases"]["items"]) == 2
        assert len(NAVIGATION_GROUPS["finance"]["items"]) == 12
        assert len(NAVIGATION_GROUPS["system"]["items"]) == 14
        assert len(NAVIGATION_GROUPS["hr"]["items"]) == 5


class TestNavigationStandalone:
    """Tests for NAVIGATION_STANDALONE."""

    def test_dashboard_and_settings_present(self):
        from ui.sidebar.navigation_data import NAVIGATION_STANDALONE
        page_ids = [item[1] for item in NAVIGATION_STANDALONE]
        assert "dashboard" in page_ids
        assert "settings" in page_ids

    def test_dashboard_index_zero(self):
        from ui.sidebar.navigation_data import NAVIGATION_STANDALONE
        dashboard = next(item for item in NAVIGATION_STANDALONE if item[1] == "dashboard")
        assert dashboard[2] == 0

    def test_standalone_items_are_3_tuples(self):
        from ui.sidebar.navigation_data import NAVIGATION_STANDALONE
        for item in NAVIGATION_STANDALONE:
            assert len(item) == 3
            assert isinstance(item[0], str)
            assert isinstance(item[1], str)
            assert isinstance(item[2], int)


class TestDefaultExpandedState:
    """Tests for DEFAULT_EXPANDED_STATE."""

    def test_all_groups_collapsed_by_default(self):
        from ui.sidebar.navigation_data import DEFAULT_EXPANDED_STATE, NAVIGATION_GROUPS
        assert set(DEFAULT_EXPANDED_STATE.keys()) == set(NAVIGATION_GROUPS.keys())
        for group_name, expanded in DEFAULT_EXPANDED_STATE.items():
            assert expanded is False, f"{group_name} should be False by default"

    def test_all_values_are_false(self):
        from ui.sidebar.navigation_data import DEFAULT_EXPANDED_STATE
        assert all(v is False for v in DEFAULT_EXPANDED_STATE.values())


class TestGroupPageIds:
    """Tests for GROUP_PAGE_IDS derived mapping."""

    def test_matches_navigation_groups(self):
        from ui.sidebar.navigation_data import GROUP_PAGE_IDS, NAVIGATION_GROUPS
        assert set(GROUP_PAGE_IDS.keys()) == set(NAVIGATION_GROUPS.keys())

    def test_page_ids_are_sets(self):
        from ui.sidebar.navigation_data import GROUP_PAGE_IDS
        for group_name, page_ids in GROUP_PAGE_IDS.items():
            assert isinstance(page_ids, set), f"{group_name} page_ids is not a set"

    def test_includes_all_items(self):
        from ui.sidebar.navigation_data import GROUP_PAGE_IDS, NAVIGATION_GROUPS
        for group_name, group_data in NAVIGATION_GROUPS.items():
            expected_ids = {item[1] for item in group_data["items"]}
            assert GROUP_PAGE_IDS[group_name] == expected_ids

    def test_inventory_page_ids(self):
        from ui.sidebar.navigation_data import GROUP_PAGE_IDS
        assert GROUP_PAGE_IDS["inventory"] == {"products", "categories", "warehouses", "batches"}


# ─────────────────────────────────────────────────────────────────────
# Sidebar Styles Tests
# ─────────────────────────────────────────────────────────────────────

class TestScrollAreaStyle:
    """Tests for SCROLL_AREA_STYLE constant."""

    def test_is_string(self):
        from ui.sidebar.sidebar_styles import SCROLL_AREA_STYLE
        assert isinstance(SCROLL_AREA_STYLE, str)

    def test_contains_scroll_area_selector(self):
        from ui.sidebar.sidebar_styles import SCROLL_AREA_STYLE
        assert "QScrollArea" in SCROLL_AREA_STYLE

    def test_contains_border_none(self):
        from ui.sidebar.sidebar_styles import SCROLL_AREA_STYLE
        assert "border: none" in SCROLL_AREA_STYLE

    def test_contains_scrollbar_styling(self):
        from ui.sidebar.sidebar_styles import SCROLL_AREA_STYLE
        assert "QScrollBar" in SCROLL_AREA_STYLE


class TestStyleFunctions:
    """Tests for all style generator functions."""

    def test_nav_button_style_returns_string(self):
        from ui.sidebar.sidebar_styles import nav_button_style
        style = nav_button_style()
        assert isinstance(style, str)
        assert len(style) > 50

    def test_nav_button_style_contains_selectors(self):
        from ui.sidebar.sidebar_styles import nav_button_style
        style = nav_button_style()
        assert "EnterpriseButton" in style
        assert ":hover" in style
        assert ":pressed" in style

    def test_nav_button_active_style_returns_string(self):
        from ui.sidebar.sidebar_styles import nav_button_active_style
        style = nav_button_active_style()
        assert isinstance(style, str)
        assert "border-left" in style
        assert ":hover" in style

    def test_nav_button_active_vs_default_different(self):
        from ui.sidebar.sidebar_styles import nav_button_style, nav_button_active_style
        assert nav_button_style() != nav_button_active_style()

    def test_group_header_style_returns_string(self):
        from ui.sidebar.sidebar_styles import group_header_style
        style = group_header_style()
        assert isinstance(style, str)
        assert "font-weight: bold" in style

    def test_sidebar_container_style_returns_string(self):
        from ui.sidebar.sidebar_styles import sidebar_container_style
        style = sidebar_container_style()
        assert isinstance(style, str)
        assert "Sidebar" in style
        assert "border-right" in style

    def test_group_header_theme_style_returns_string(self):
        from ui.sidebar.sidebar_styles import group_header_theme_style
        style = group_header_theme_style()
        assert isinstance(style, str)
        assert "EnterpriseButton" in style

    def test_logout_button_style_returns_string(self):
        from ui.sidebar.sidebar_styles import logout_button_style
        style = logout_button_style()
        assert isinstance(style, str)
        assert ":hover" in style
        assert ":pressed" in style

    def test_style_source_uses_tokens(self):
        """Verify style functions source code references ui.constants tokens, not hardcoded hex."""
        import inspect, re
        from ui.sidebar import sidebar_styles
        style_fns = [
            sidebar_styles.nav_button_style,
            sidebar_styles.nav_button_active_style,
            sidebar_styles.group_header_style,
            sidebar_styles.sidebar_container_style,
            sidebar_styles.group_header_theme_style,
            sidebar_styles.logout_button_style,
        ]
        for fn in style_fns:
            source = inspect.getsource(fn)
            hex_in_source = re.findall(r"#[0-9a-fA-F]{6}\b", source)
            assert len(hex_in_source) == 0, (
                f"{fn.__name__} source has hardcoded hex: {hex_in_source}"
            )

    def test_scroll_area_style_source_uses_tokens(self):
        import re
        from ui.sidebar import sidebar_styles
        source = inspect.getsource(sidebar_styles) if hasattr(sidebar_styles, '__file__') else ''
        # SCROLL_AREA_STYLE is defined at module level — verify it uses f-string tokens
        # by checking the source file directly
        import pathlib, inspect as _insp
        mod_file = pathlib.Path(_insp.getfile(sidebar_styles))
        mod_source = mod_file.read_text(encoding='utf-8')
        # Find the SCROLL_AREA_STYLE definition block
        start = mod_source.find('SCROLL_AREA_STYLE')
        end = mod_source.find('"""', start + 20)
        style_block = mod_source[start:end]
        hex_in_source = re.findall(r"#[0-9a-fA-F]{6}\b", style_block)
        assert len(hex_in_source) == 0, f"SCROLL_AREA_STYLE has hardcoded hex: {hex_in_source}"


# ─────────────────────────────────────────────────────────────────────
# Group Renderer Tests
# ─────────────────────────────────────────────────────────────────────

# Ensure QApplication exists for widget operations
_qapp = None


def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        if QApplication.instance():
            _qapp = QApplication.instance()
        else:
            _qapp = QApplication([])
    return _qapp


def _safe_btn_factory(title, page_id, page_index):
    """Create a QWidget stub that layout.addWidget will accept."""
    from PySide6.QtWidgets import QWidget
    btn = QWidget()
    btn.setProperty("page_id", page_id)
    btn.setProperty("page_index", page_index)
    btn._page_id = page_id
    btn._page_index = page_index
    return btn


def _make_sidebar_stub():
    """Create a minimal sidebar-like object with _toggle_group."""
    sidebar = MagicMock()
    sidebar._toggle_group = MagicMock()
    return sidebar


class TestCreateGroup:
    """Tests for group_renderer.create_group()."""

    def test_creates_group_widget(self):
        from PySide6.QtWidgets import QVBoxLayout, QWidget
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = _make_sidebar_stub()
        expanded = {"test": False}
        group_widgets = {}
        nav_items = {}

        parent = QVBoxLayout()
        items = [("Item A", "item_a", 10), ("Item B", "item_b", 20)]

        create_group(
            parent, "Test Group", "test", items,
            expanded, group_widgets, nav_items, _safe_btn_factory, sidebar,
        )

        assert "test" in group_widgets
        assert isinstance(group_widgets["test"], QWidget)

    def test_collapsed_by_default(self):
        from PySide6.QtWidgets import QVBoxLayout, QWidget
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = _make_sidebar_stub()
        expanded = {"test": False}
        group_widgets = {}
        nav_items = {}

        parent = QVBoxLayout()
        items = [("A", "a", 1)]

        create_group(
            parent, "T", "test", items,
            expanded, group_widgets, nav_items, _safe_btn_factory, sidebar,
        )

        gw = group_widgets["test"]
        assert gw.maximumHeight() == 42

    def test_expanded_when_state_true(self):
        from PySide6.QtWidgets import QVBoxLayout
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = _make_sidebar_stub()
        expanded = {"test": True}
        group_widgets = {}
        nav_items = {}

        parent = QVBoxLayout()
        items = [("A", "a", 1)]

        create_group(
            parent, "T", "test", items,
            expanded, group_widgets, nav_items, _safe_btn_factory, sidebar,
        )

        gw = group_widgets["test"]
        assert gw.maximumHeight() == 16777215

    def test_arrow_shows_collapsed(self):
        from PySide6.QtWidgets import QVBoxLayout
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = _make_sidebar_stub()
        expanded = {"test": False}
        group_widgets = {}
        nav_items = {}

        parent = QVBoxLayout()

        create_group(
            parent, "My Group", "test", [("A", "a", 1)],
            expanded, group_widgets, nav_items, _safe_btn_factory, sidebar,
        )

        header = getattr(sidebar, "_test_header", None)
        assert header is not None
        header_text = header.text()
        assert "▶" in header_text

    def test_arrow_shows_expanded(self):
        from PySide6.QtWidgets import QVBoxLayout
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = _make_sidebar_stub()
        expanded = {"test": True}
        group_widgets = {}
        nav_items = {}

        parent = QVBoxLayout()

        create_group(
            parent, "My Group", "test", [("A", "a", 1)],
            expanded, group_widgets, nav_items, _safe_btn_factory, sidebar,
        )

        header = getattr(sidebar, "_test_header", None)
        assert "▼" in header.text()

    def test_creates_buttons_for_all_items(self):
        from PySide6.QtWidgets import QVBoxLayout
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = _make_sidebar_stub()
        expanded = {"test": False}
        group_widgets = {}
        nav_items = {}
        created = []

        def track_button(title, page_id, page_index):
            created.append((title, page_id, page_index))
            return _safe_btn_factory(title, page_id, page_index)

        parent = QVBoxLayout()
        items = [("A", "a", 1), ("B", "b", 2), ("C", "c", 3)]

        create_group(
            parent, "G", "test", items,
            expanded, group_widgets, nav_items, track_button, sidebar,
        )

        assert len(created) == 3
        assert created[0] == ("A", "a", 1)
        assert created[2] == ("C", "c", 3)

    def test_header_set_on_sidebar(self):
        from PySide6.QtWidgets import QVBoxLayout, QWidget
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = _make_sidebar_stub()
        expanded = {"inv": False}
        group_widgets = {}
        nav_items = {}

        parent = QVBoxLayout()

        create_group(
            parent, "Inventory", "inv", [("P", "p", 1)],
            expanded, group_widgets, nav_items, _safe_btn_factory, sidebar,
        )

        # create_group calls setattr(sidebar, "_inv_header", header_btn)
        header = getattr(sidebar, "_inv_header", None)
        assert header is not None
        assert isinstance(header, QWidget)


class TestToggleGroup:
    """Tests for group_renderer.toggle_group()."""

    def _create_collapsed_group(self):
        """Helper: create a collapsed group and return the components."""
        from PySide6.QtWidgets import QVBoxLayout
        from ui.sidebar.group_renderer import create_group
        _ensure_qapp()

        sidebar = MagicMock()
        sidebar._toggle_group = MagicMock()
        expanded = {"test": False}
        group_widgets = {}
        nav_items = {}

        parent = QVBoxLayout()
        create_group(
            parent, "Test", "test", [("A", "a", 1)],
            expanded, group_widgets, nav_items, _safe_btn_factory, sidebar,
        )
        return sidebar, expanded, group_widgets

    def test_toggle_expands_collapsed_group(self):
        from ui.sidebar.group_renderer import toggle_group
        sidebar, expanded, group_widgets = self._create_collapsed_group()

        toggle_group("test", expanded, group_widgets, sidebar)

        assert expanded["test"] is True
        assert group_widgets["test"].maximumHeight() == 16777215

    def test_toggle_collapses_expanded_group(self):
        from ui.sidebar.group_renderer import toggle_group
        sidebar, expanded, group_widgets = self._create_collapsed_group()
        # First expand
        toggle_group("test", expanded, group_widgets, sidebar)
        assert expanded["test"] is True

        # Then collapse
        toggle_group("test", expanded, group_widgets, sidebar)
        assert expanded["test"] is False
        assert group_widgets["test"].maximumHeight() == 42

    def test_toggle_updates_arrow_collapsed(self):
        from ui.sidebar.group_renderer import toggle_group
        sidebar, expanded, group_widgets = self._create_collapsed_group()
        # Expand then collapse
        toggle_group("test", expanded, group_widgets, sidebar)
        toggle_group("test", expanded, group_widgets, sidebar)

        header = getattr(sidebar, "_test_header", None)
        assert "▶" in header.text()

    def test_toggle_updates_arrow_expanded(self):
        from ui.sidebar.group_renderer import toggle_group
        sidebar, expanded, group_widgets = self._create_collapsed_group()
        toggle_group("test", expanded, group_widgets, sidebar)

        header = getattr(sidebar, "_test_header", None)
        assert "▼" in header.text()

    def test_toggle_nonexistent_group_no_crash(self):
        from ui.sidebar.group_renderer import toggle_group
        sidebar = MagicMock()
        expanded = {}
        group_widgets = {}

        # Should not raise
        toggle_group("nonexistent", expanded, group_widgets, sidebar)
        assert expanded["nonexistent"] is True

    def test_double_toggle_restores_state(self):
        from ui.sidebar.group_renderer import toggle_group
        sidebar, expanded, group_widgets = self._create_collapsed_group()
        original_height = group_widgets["test"].maximumHeight()

        toggle_group("test", expanded, group_widgets, sidebar)
        toggle_group("test", expanded, group_widgets, sidebar)

        assert group_widgets["test"].maximumHeight() == original_height
        assert expanded["test"] is False

    def test_toggle_preserves_title_text(self):
        from ui.sidebar.group_renderer import toggle_group
        sidebar, expanded, group_widgets = self._create_collapsed_group()

        # Expand
        toggle_group("test", expanded, group_widgets, sidebar)
        header = getattr(sidebar, "_test_header", None)
        # Title should still contain "Test"
        assert "Test" in header.text()

        # Collapse
        toggle_group("test", expanded, group_widgets, sidebar)
        assert "Test" in header.text()

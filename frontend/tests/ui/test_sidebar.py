"""Tests for sidebar navigation."""
import pytest
pytest.importorskip("PySide6", reason="PySide6 not available")
from unittest.mock import patch, MagicMock
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest


pytestmark = pytest.mark.navigation


class TestSidebarNavigation:
    """Test sidebar navigation functionality."""
    
    def test_sidebar_creates_navigation_items(self, sidebar_widget):
        """Sidebar should create navigation items on init."""
        assert sidebar_widget.nav_list.count() > 0
    
    def test_navigation_items_count(self, sidebar_widget):
        """Sidebar should have expected number of items."""
        # 21 items from setup_navigation
        assert sidebar_widget.nav_list.count() == 21
    
    def test_group_headers_are_not_selectable(self, sidebar_widget):
        """Group headers should not be selectable."""
        for index in sidebar_widget.group_items:
            item = sidebar_widget.nav_list.item(index)
            flags = item.flags()
            assert not (flags & Qt.ItemIsSelectable), f"Item {index} should not be selectable"
    
    def test_dashboard_is_first_item(self, sidebar_widget):
        """Dashboard should be the first item."""
        item = sidebar_widget.nav_list.item(0)
        assert "Dashboard" in item.text()
    
    def test_set_active_item(self, sidebar_widget):
        """Should be able to set active item programmatically."""
        sidebar_widget.set_active_item(2)
        assert sidebar_widget.nav_list.currentRow() == 2
    
    def test_set_active_item_out_of_bounds(self, sidebar_widget):
        """Setting out of bounds index should not crash."""
        sidebar_widget.set_active_item(100)
        # Should stay within bounds
        assert sidebar_widget.nav_list.currentRow() < sidebar_widget.nav_list.count()
    
    def test_set_active_item_negative(self, sidebar_widget):
        """Setting negative index should not crash."""
        sidebar_widget.set_active_item(-1)
        # Should stay within bounds
        assert sidebar_widget.nav_list.currentRow() >= 0


class TestSidebarSignals:
    """Test sidebar signals."""
    
    def test_page_changed_signal_emitted_on_navigation(self, sidebar_widget):
        """Page changed signal should emit on navigation."""
        received_signals = []
        
        def on_page_changed(index, title):
            received_signals.append((index, title))
        
        sidebar_widget.page_changed.connect(on_page_changed)
        sidebar_widget.set_active_item(2)
        QTest.qWait(50)
        
        assert len(received_signals) > 0
        assert received_signals[-1][0] == 2
    
    def test_page_changed_not_emitted_for_group_headers(self, sidebar_widget):
        """Page changed signal should not emit for group headers."""
        received_signals = []
        
        def on_page_changed(index, title):
            received_signals.append((index, title))
        
        sidebar_widget.page_changed.connect(on_page_changed)
        
        # Try to navigate to group headers
        for index in sidebar_widget.group_items:
            sidebar_widget.set_active_item(index)
        
        QTest.qWait(50)
        
        # Group headers should not emit signals (they are not selectable)
        assert len(received_signals) == 0


class TestSidebarStatePreservation:
    """Test navigation state preservation."""
    
    def test_state_preserves_active_index(self, sidebar_widget):
        """Active index should be preserved in state."""
        # Navigate to a page
        sidebar_widget.set_active_item(5)
        active_index = sidebar_widget.nav_list.currentRow()
        
        # Verify state
        assert active_index == 5
    
    def test_active_item_updates_on_navigation(self, sidebar_widget):
        """Active item should update on navigation."""
        sidebar_widget.set_active_item(0)
        item = sidebar_widget.nav_list.item(0)
        assert item.isSelected()
    
    def test_navigation_cycles_through_pages(self, sidebar_widget):
        """Should be able to navigate through multiple pages."""
        indices = [0, 2, 3, 4, 5, 6, 7, 11, 12, 15]
        
        for idx in indices:
            sidebar_widget.set_active_item(idx)
            QTest.qWait(10)
            assert sidebar_widget.nav_list.currentRow() == idx
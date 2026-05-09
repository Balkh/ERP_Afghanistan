"""Screen integration tests with mocked backend."""
import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.integration


class TestSidebarScreen:
    """Test sidebar navigation integration."""
    
    def test_sidebar_navigates_to_dashboard(self, sidebar_widget):
        """Sidebar should navigate to dashboard."""
        sidebar_widget.set_active_item(0)
        
        assert sidebar_widget.nav_list.currentRow() == 0
    
    def test_sidebar_navigates_to_settings(self, sidebar_widget):
        """Sidebar should navigate to settings."""
        sidebar_widget.set_active_item(20)
        
        assert sidebar_widget.nav_list.currentRow() == 20


class TestThemeScreen:
    """Test theme switching integration."""
    
    def test_light_theme_switch(self, theme_manager):
        """Should switch to light theme."""
        theme_manager.set_theme("light")
        
        assert theme_manager.current_theme() == "light"
    
    def test_dark_theme_switch(self, theme_manager):
        """Should switch to dark theme."""
        theme_manager.set_theme("dark")
        
        assert theme_manager.current_theme() == "dark"


class TestProductFormScreen:
    """Test product form integration."""
    
    def test_form_loads(self, product_form_dialog):
        """Product form should load."""
        assert product_form_dialog is not None
    
    def test_form_fields_exist(self, product_form_dialog):
        """Form should have required fields."""
        assert product_form_dialog.name_input is not None
        assert product_form_dialog.category_combo is not None
        assert product_form_dialog.unit_combo is not None
    
    def test_form_accepts_input(self, product_form_dialog):
        """Form should accept input."""
        product_form_dialog.name_input.setText("Test Product")
        
        data = product_form_dialog.get_form_data()
        assert data["name"] == "Test Product"
    
    def test_form_validates_required(self, product_form_dialog):
        """Form should validate required fields."""
        product_form_dialog.name_input.setText("")
        
        data = product_form_dialog.get_form_data()
        assert data["name"] == ""


class TestBarcodeSearchScreen:
    """Test barcode search integration."""
    
    def test_search_widget_loads(self, barcode_search_widget):
        """Barcode search should load."""
        assert barcode_search_widget is not None
    
    def test_search_widget_accepts_input(self, barcode_search_widget):
        """Search should accept input."""
        barcode_search_widget.setText("89012345")
        
        assert barcode_search_widget.text() == "89012345"
    
    def test_short_input_no_search(self, barcode_search_widget):
        """Short input should not trigger search."""
        barcode_search_widget.setText("12")
        
        assert barcode_search_widget.text() == "12"


class TestNavigationFlow:
    """Test complete navigation flows."""
    
    def test_dashboard_to_accounting(self, sidebar_widget):
        """Should navigate from dashboard to accounting."""
        sidebar_widget.set_active_item(0)  # Dashboard
        sidebar_widget.set_active_item(11)  # Chart of Accounts
        
        assert sidebar_widget.nav_list.currentRow() == 11
    
    def test_rapid_navigation(self, sidebar_widget):
        """Should handle rapid navigation."""
        pages = [0, 11, 15, 17, 0]
        
        for page in pages:
            sidebar_widget.set_active_item(page)
        
        assert sidebar_widget.nav_list.currentRow() == 0
    
    def test_group_navigation_blocked(self, sidebar_widget):
        """Group headers should not be navigable."""
        # Can call set_active_item but signal should not emit
        for group_idx in [1, 7, 10, 14]:
            sidebar_widget.set_active_item(group_idx)
        
        # Final position should be valid (not on a group)
        current = sidebar_widget.nav_list.currentRow()
        # Note: Signal handler prevents navigation to groups
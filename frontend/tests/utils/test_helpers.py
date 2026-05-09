"""Reusable test utilities for frontend UI testing."""
import pytest
from unittest.mock import MagicMock


class NavigationHelper:
    """Helper for navigation testing - logic only."""
    
    NAV_MAP = {
        "dashboard": 0,
        "products": 2,
        "categories": 3,
        "warehouses": 4,
        "batches": 5,
        "sales_invoice": 6,
        "purchase_invoice": 7,
        "customers": 8,
        "suppliers": 9,
        "chart_of_accounts": 11,
        "journal_entries": 12,
        "account_ledger": 13,
        "trial_balance": 15,
        "profit_loss": 16,
        "balance_sheet": 17,
        "ar_ageing": 18,
        "ap_ageing": 19,
        "settings": 20,
    }
    
    GROUP_INDICES = {1, 7, 10, 14}
    
    def navigate_to(self, page_name):
        """Navigate to a page by name."""
        return self.NAV_MAP.get(page_name)
    
    def is_valid_navigation(self, index):
        """Check if navigation index is valid."""
        return index in self.NAV_MAP.values()
    
    def is_group_header(self, index):
        """Check if index is a group header."""
        return index in self.GROUP_INDICES


class ThemeHelper:
    """Helper for theme testing - logic only."""
    
    THEMES = ["light", "dark"]
    
    def validate_theme_name(self, theme_name):
        """Validate theme name."""
        return theme_name in self.THEMES
    
    def get_theme_colors(self, theme_name):
        """Get theme colors (placeholder for logic)."""
        if theme_name == "light":
            return {"background": "#ffffff", "foreground": "#212121"}
        elif theme_name == "dark":
            return {"background": "#212121", "foreground": "#ffffff"}
        return {}


class FormValidator:
    """Helper for form validation - logic only."""
    
    @staticmethod
    def is_required_field_valid(value):
        """Validate required field."""
        return bool(value and value.strip())
    
    @staticmethod
    def is_numeric_valid(value):
        """Validate numeric field."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_barcode_valid(barcode):
        """Validate barcode (8-14 digits)."""
        return barcode.isdigit() and 8 <= len(barcode) <= 14
    
    @staticmethod
    def is_date_valid(date_str):
        """Validate date (YYYY-MM-DD format)."""
        import re
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        return bool(re.match(pattern, date_str))


@pytest.fixture
def navigation_helper():
    """Create a navigation helper."""
    return NavigationHelper()


@pytest.fixture
def theme_helper():
    """Create a theme helper."""
    return ThemeHelper()


@pytest.fixture
def form_validator():
    """Create a form validator."""
    return FormValidator()
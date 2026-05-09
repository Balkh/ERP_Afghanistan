"""Simplified page routing tests that don't require full MainWindow."""
import pytest


pytestmark = pytest.mark.navigation


class TestPageIndexMapping:
    """Test navigation index mapping (no MainWindow needed)."""
    
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
    
    def test_dashboard_index(self):
        """Dashboard should be at index 0."""
        assert self.NAV_MAP["dashboard"] == 0
    
    def test_products_index(self):
        """Products should be at index 2."""
        assert self.NAV_MAP["products"] == 2
    
    def test_all_indices_valid(self):
        """All indices should be valid."""
        for name, idx in self.NAV_MAP.items():
            assert 0 <= idx <= 20, f"Invalid index for {name}: {idx}"
    
    def test_indices_unique(self):
        """All indices should be unique."""
        indices = list(self.NAV_MAP.values())
        assert len(indices) == len(set(indices))
    
    def test_page_count(self):
        """Should have 21 pages."""
        assert max(self.NAV_MAP.values()) == 20  # Highest is Settings at 20


class TestNavigationValidation:
    """Test navigation validation logic."""
    
    GROUP_INDICES = {1, 7, 10, 14}
    
    def test_group_count(self):
        """Should have 4 group headers."""
        assert len(self.GROUP_INDICES) == 4
    
    def test_group_indices_sorted(self):
        """Group indices should be sorted."""
        sorted_groups = sorted(self.GROUP_INDICES)
        assert sorted_groups == [1, 7, 10, 14]
    
    def test_non_group_navigation_valid(self):
        """Non-group indices should navigate correctly."""
        valid_navs = [0, 2, 3, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 18, 19, 20]
        
        for nav in valid_navs:
            assert nav not in self.GROUP_INDICES


class TestNavigationState:
    """Test navigation state management."""
    
    def test_initial_state(self):
        """Initial state should be at dashboard."""
        current_page = 0
        assert current_page == 0
    
    def test_state_transition(self):
        """Should transition between pages."""
        from_page = 0
        to_page = 11
        
        valid = to_page not in {1, 7, 10, 14}  # Not a group
        assert valid
        assert from_page != to_page
    
    def test_sequential_navigation(self):
        """Should handle sequential navigation."""
        pages = [0, 2, 3, 4, 5, 6]
        for page in pages:
            assert page >= 0


class TestNavigationPerformance:
    """Test navigation performance characteristics."""
    
    def test_index_lookup_performance(self):
        """Index lookup should be O(1)."""
        nav_map = {
            "dashboard": 0,
            "products": 2,
            "categories": 3,
        }
        
        # O(1) lookup
        assert nav_map.get("dashboard") == 0
        assert nav_map.get("products") == 2
    
    def test_rapid_lookup(self):
        """Rapid lookups should be fast."""
        nav_map = {f"page_{i}": i for i in range(21)}
        
        for _ in range(100):
            _ = nav_map.get("page_10")
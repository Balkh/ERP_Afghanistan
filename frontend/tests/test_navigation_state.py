"""Unit tests for ui.navigation_state PAGE_REGISTRY and derived lookup maps.

Verifies:
- Entry count and structural integrity
- Derived map consistency (ID_TO_INDEX, INDEX_TO_MODULE)
- get_load_method correctness
- build_breadcrumb correctness
- No duplicate IDs or indices
"""

import pytest
from ui.navigation_state import (
    PAGE_REGISTRY,
    ID_TO_INDEX,
    INDEX_TO_MODULE,
    get_load_method,
    build_breadcrumb,
)


# ---------------------------------------------------------------------------
# Structural integrity
# ---------------------------------------------------------------------------

class TestPageRegistryStructure:
    """Verify PAGE_REGISTRY has correct shape and no duplicates."""

    def test_entry_count(self):
        """Registry should have exactly 62 entries."""
        assert len(PAGE_REGISTRY) == 62

    def test_all_entries_have_required_keys(self):
        """Every entry must have id, name, module, group, load."""
        required = {"id", "name", "module", "group", "load"}
        for idx, entry in PAGE_REGISTRY.items():
            assert required.issubset(entry.keys()), (
                f"Index {idx} missing keys: {required - entry.keys()}"
            )

    def test_all_ids_are_strings(self):
        for idx, entry in PAGE_REGISTRY.items():
            assert isinstance(entry["id"], str), f"Index {idx}: id is not str"

    def test_all_names_are_strings(self):
        for idx, entry in PAGE_REGISTRY.items():
            assert isinstance(entry["name"], str), f"Index {idx}: name is not str"

    def test_all_modules_are_strings(self):
        valid_modules = {"dashboard", "inventory", "sales", "purchases",
                         "returns", "accounting", "reports", "finance",
                         "hr", "system"}
        for idx, entry in PAGE_REGISTRY.items():
            assert entry["module"] in valid_modules, (
                f"Index {idx}: module '{entry['module']}' not in {valid_modules}"
            )

    def test_no_duplicate_ids(self):
        ids = [e["id"] for e in PAGE_REGISTRY.values()]
        assert len(ids) == len(set(ids)), "Duplicate page IDs found"

    def test_no_negative_indices(self):
        for idx in PAGE_REGISTRY:
            assert idx >= 0, f"Negative index: {idx}"


# ---------------------------------------------------------------------------
# Derived map consistency
# ---------------------------------------------------------------------------

class TestDerivedMaps:
    """Verify derived lookup maps are consistent with PAGE_REGISTRY."""

    def test_id_to_index_count(self):
        assert len(ID_TO_INDEX) == len(PAGE_REGISTRY)

    def test_id_to_index_values_match(self):
        for idx, entry in PAGE_REGISTRY.items():
            assert ID_TO_INDEX[entry["id"]] == idx, (
                f"ID_TO_INDEX['{entry['id']}'] = {ID_TO_INDEX[entry['id']]}, expected {idx}"
            )

    def test_index_to_module_count(self):
        assert len(INDEX_TO_MODULE) == len(PAGE_REGISTRY)

    def test_index_to_module_values_match(self):
        for idx, entry in PAGE_REGISTRY.items():
            assert INDEX_TO_MODULE[idx] == entry["module"], (
                f"INDEX_TO_MODULE[{idx}] = '{INDEX_TO_MODULE[idx]}', expected '{entry['module']}'"
            )

    def test_all_indices_in_derived_maps(self):
        for idx in PAGE_REGISTRY:
            assert idx in ID_TO_INDEX.values()
            assert idx in INDEX_TO_MODULE


# ---------------------------------------------------------------------------
# get_load_method
# ---------------------------------------------------------------------------

class TestGetLoadMethod:
    """Verify get_load_method returns correct load tuples."""

    def test_known_loadable_screen(self):
        result = get_load_method(1)  # products
        assert result == ("load_products", "products")

    def test_known_non_loadable_screen(self):
        result = get_load_method(5)  # sales_invoice
        assert result is None

    def test_unknown_index(self):
        result = get_load_method(999)
        assert result is None

    def test_dashboard_has_no_load(self):
        result = get_load_method(0)
        assert result is None

    def test_expenses_has_load(self):
        result = get_load_method(34)
        assert result == ("load_expenses", "expenses")

    def test_all_load_tuples_are_two_element(self):
        for idx, entry in PAGE_REGISTRY.items():
            load = entry["load"]
            if load is not None:
                assert isinstance(load, tuple) and len(load) == 2, (
                    f"Index {idx}: load={load} is not a 2-tuple"
                )
                assert isinstance(load[0], str), f"Index {idx}: method name not str"
                assert isinstance(load[1], str), f"Index {idx}: tag not str"


# ---------------------------------------------------------------------------
# build_breadcrumb
# ---------------------------------------------------------------------------

class TestBuildBreadcrumb:
    """Verify build_breadcrumb returns correct path lists."""

    def test_dashboard_breadcrumb(self):
        result = build_breadcrumb(0)
        assert result == ["Home", "Dashboard"]

    def test_inventory_screen(self):
        result = build_breadcrumb(1)
        assert result == ["Home", "Inventory", "Products"]

    def test_sales_screen(self):
        result = build_breadcrumb(5)
        assert result == ["Home", "Sales", "Sales Invoice"]

    def test_purchases_screen(self):
        result = build_breadcrumb(6)
        assert result == ["Home", "Purchases", "Purchase Invoice"]

    def test_returns_screen(self):
        result = build_breadcrumb(9)
        assert result == ["Home", "Returns", "Returns"]

    def test_accounting_screen(self):
        result = build_breadcrumb(10)
        assert result == ["Home", "Accounting", "Chart of Accounts"]

    def test_reports_screen(self):
        result = build_breadcrumb(13)
        assert result == ["Home", "Reports", "Trial Balance"]

    def test_finance_screen(self):
        result = build_breadcrumb(18)
        assert result == ["Home", "Finance", "Payments"]

    def test_hr_screen(self):
        result = build_breadcrumb(23)
        assert result == ["Home", "HR", "Employees"]

    def test_system_screen(self):
        result = build_breadcrumb(27)
        assert result == ["Home", "System", "Backup"]

    def test_unknown_index_returns_fallback(self):
        result = build_breadcrumb(999, "Custom Title")
        assert result == ["Home", "Custom Title"]

    def test_unknown_index_empty_fallback(self):
        result = build_breadcrumb(999)
        assert result == ["Home", ""]

    def test_all_entries_have_at_least_two_element_breadcrumb(self):
        """All registered pages produce at least a 2-element breadcrumb [Home, ...]."""
        for idx in PAGE_REGISTRY:
            result = build_breadcrumb(idx)
            assert len(result) >= 2, (
                f"Index {idx}: breadcrumb has {len(result)} elements, expected >= 2"
            )

    def test_all_breadcrumbs_start_with_home(self):
        for idx in PAGE_REGISTRY:
            result = build_breadcrumb(idx)
            assert result[0] == "Home", f"Index {idx}: breadcrumb doesn't start with Home"


# ---------------------------------------------------------------------------
# Module groupings
# ---------------------------------------------------------------------------

class TestModuleGroupings:
    """Verify module assignments match expected groupings."""

    def test_dashboard_module(self):
        assert PAGE_REGISTRY[0]["module"] == "dashboard"

    def test_inventory_indices(self):
        for idx in [1, 2, 3, 4]:
            assert PAGE_REGISTRY[idx]["module"] == "inventory"

    def test_sales_indices(self):
        for idx in [5, 7, 37]:
            assert PAGE_REGISTRY[idx]["module"] == "sales"

    def test_purchases_indices(self):
        for idx in [6, 8]:
            assert PAGE_REGISTRY[idx]["module"] == "purchases"

    def test_accounting_indices(self):
        for idx in [10, 11, 12, 58, 59]:
            assert PAGE_REGISTRY[idx]["module"] == "accounting"

    def test_reports_indices(self):
        for idx in [13, 14, 15, 16, 17]:
            assert PAGE_REGISTRY[idx]["module"] == "reports"

    def test_hr_indices(self):
        for idx in [23, 24, 25, 26, 67, 49, 50, 51, 52, 53, 54, 55, 56]:
            assert PAGE_REGISTRY[idx]["module"] == "hr"

    def test_reconciliation_defaults_to_dashboard(self):
        """Index 57 (Reconciliation) must default to 'dashboard' module
        to preserve original access-control fallback behavior."""
        assert PAGE_REGISTRY[57]["module"] == "dashboard"

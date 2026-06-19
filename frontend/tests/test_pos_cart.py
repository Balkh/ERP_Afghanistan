"""Unit tests for pos_cart.py pure functions."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from ui.pos.pos_cart import add_to_cart, find_cart_item, remove_item


# ─── find_cart_item ──────────────────────────────────────────────────────────

class TestFindCartItem:
    def test_finds_matching_item(self):
        items = [
            {"product_id": "p1", "batch_number": "B001"},
            {"product_id": "p2", "batch_number": "B002"},
        ]
        result = find_cart_item(items, "p1", "B001")
        assert result is items[0]

    def test_returns_none_when_not_found(self):
        items = [{"product_id": "p1", "batch_number": "B001"}]
        result = find_cart_item(items, "p99", "B999")
        assert result is None

    def test_empty_cart(self):
        result = find_cart_item([], "p1", "B001")
        assert result is None

    def test_matches_product_and_batch(self):
        items = [
            {"product_id": "p1", "batch_number": "B001"},
            {"product_id": "p1", "batch_number": "B002"},
        ]
        result = find_cart_item(items, "p1", "B002")
        assert result is items[1]


# ─── remove_item ─────────────────────────────────────────────────────────────

class TestRemoveItem:
    def test_removes_valid_index(self):
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        assert remove_item(items, 1) is True
        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 3

    def test_returns_false_for_invalid_index(self):
        items = [{"id": 1}]
        assert remove_item(items, 5) is False
        assert len(items) == 1

    def test_returns_false_for_negative_index(self):
        items = [{"id": 1}]
        assert remove_item(items, -1) is False

    def test_removes_first_item(self):
        items = [{"id": 1}, {"id": 2}]
        assert remove_item(items, 0) is True
        assert len(items) == 1
        assert items[0]["id"] == 2


# ─── add_to_cart ─────────────────────────────────────────────────────────────

def _make_product(**overrides):
    """Create a product dict with sensible defaults."""
    defaults = {
        "id": "prod-1",
        "name": "Paracetamol 500mg",
        "sale_price": 10.0,
        "total_stock": 50,
        "batches": [{"batch_number": "B001", "sale_price": 10.0, "remaining_quantity": 50}],
        "requires_prescription": False,
        "is_controlled_substance": False,
    }
    defaults.update(overrides)
    return defaults


class TestAddToCart:
    def test_empty_product_returns_no_change(self):
        items = []
        result_items, msg, level = add_to_cart(items, None)
        assert result_items is items
        assert msg is None

    def test_adds_new_item_to_empty_cart(self):
        items = []
        product = _make_product()
        result_items, msg, level = add_to_cart(items, product)
        assert len(result_items) == 1
        assert result_items[0]["product_id"] == "prod-1"
        assert result_items[0]["quantity"] == 1
        assert result_items[0]["price"] == Decimal("10.0")

    def test_out_of_stock_returns_danger_alert(self):
        items = []
        product = _make_product(total_stock=0)
        result_items, msg, level = add_to_cart(items, product)
        assert len(result_items) == 0
        assert "Out of stock" in msg
        assert level == "danger"

    def test_increments_existing_item(self):
        items = [{"product_id": "prod-1", "batch_number": "B001", "quantity": 1, "price": Decimal("10"), "total": Decimal("10")}]
        product = _make_product()
        result_items, msg, level = add_to_cart(items, product)
        assert result_items[0]["quantity"] == 2
        assert result_items[0]["total"] == Decimal("20")

    def test_insufficient_stock_returns_warning(self):
        items = [{"product_id": "prod-1", "batch_number": "B001", "quantity": 50, "price": Decimal("10"), "total": Decimal("500"), "max_stock": Decimal("50")}]
        product = _make_product()
        result_items, msg, level = add_to_cart(items, product)
        assert result_items[0]["quantity"] == 50  # unchanged (50 + 1 > 50)
        assert "Insufficient stock" in msg
        assert level == "warning"

    def test_prescription_required_alert(self):
        items = []
        product = _make_product(requires_prescription=True)
        result_items, msg, level = add_to_cart(items, product)
        assert "Prescription required" in msg
        assert level == "warning"

    def test_controlled_substance_alert(self):
        items = []
        product = _make_product(is_controlled_substance=True)
        result_items, msg, level = add_to_cart(items, product)
        assert "Controlled substance" in msg
        assert level == "danger"

    def test_no_batches_returns_no_change(self):
        items = []
        product = _make_product(batches=[])
        result_items, msg, level = add_to_cart(items, product)
        assert len(result_items) == 0

    def test_single_batch_no_dialog(self):
        items = []
        product = _make_product(batches=[{"batch_number": "B001", "sale_price": 15.0, "remaining_quantity": 30}])
        result_items, msg, level = add_to_cart(items, product)
        assert len(result_items) == 1
        assert result_items[0]["batch_number"] == "B001"
        assert result_items[0]["price"] == Decimal("15.0")

    def test_batch_price_overrides_product_price(self):
        items = []
        product = _make_product(sale_price=10.0, batches=[{"batch_number": "B001", "sale_price": 25.0, "remaining_quantity": 10}])
        result_items, msg, level = add_to_cart(items, product)
        assert result_items[0]["price"] == Decimal("25.0")

"""Unit tests for pos_payment.py pure functions."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from ui.pos.pos_payment import update_totals, calculate_change, build_invoice_data


def _make_item(price=10.0, quantity=2):
    """Create a cart item dict with sensible defaults."""
    return {
        "product_id": "prod-1",
        "product_name": "Test Product",
        "batch_number": "B001",
        "quantity": quantity,
        "price": Decimal(str(price)),
        "total": Decimal(str(price)) * quantity,
    }


def _mock_input(text="0"):
    """Create a mock input widget with text()."""
    mock = MagicMock()
    mock.text.return_value = text
    return mock


# ─── update_totals ───────────────────────────────────────────────────────────

class TestUpdateTotals:
    def test_empty_cart(self):
        result = update_totals([])
        assert result["subtotal"] == Decimal("0")
        assert result["discount"] == Decimal("0")
        assert result["tax"] == Decimal("0")
        assert result["total"] == Decimal("0")

    def test_single_item_no_discount_tax(self):
        items = [_make_item(price=10.0, quantity=3)]
        result = update_totals(items)
        assert result["subtotal"] == Decimal("30.0")
        assert result["discount"] == Decimal("0")
        assert result["tax"] == Decimal("0")
        assert result["total"] == Decimal("30.0")

    def test_multiple_items(self):
        items = [_make_item(price=10.0, quantity=2), _make_item(price=25.0, quantity=1)]
        result = update_totals(items)
        assert result["subtotal"] == Decimal("45.0")

    def test_with_discount(self):
        items = [_make_item(price=100.0, quantity=1)]
        discount_input = _mock_input("10")  # 10%
        result = update_totals(items, discount_input=discount_input)
        assert result["subtotal"] == Decimal("100.0")
        assert result["discount"] == Decimal("10.0")
        assert result["total"] == Decimal("90.0")

    def test_with_tax(self):
        items = [_make_item(price=100.0, quantity=1)]
        tax_input = _mock_input("5")  # 5%
        result = update_totals(items, tax_input=tax_input)
        assert result["subtotal"] == Decimal("100.0")
        assert result["tax"] == Decimal("5.0")
        assert result["total"] == Decimal("105.0")

    def test_with_discount_and_tax(self):
        items = [_make_item(price=200.0, quantity=1)]
        discount_input = _mock_input("10")  # 10%
        tax_input = _mock_input("5")  # 5%
        result = update_totals(items, discount_input=discount_input, tax_input=tax_input)
        assert result["subtotal"] == Decimal("200.0")
        assert result["discount"] == Decimal("20.0")
        # taxable = 200 - 20 = 180, tax = 180 * 5/100 = 9
        assert result["tax"] == Decimal("9.0")
        assert result["total"] == Decimal("189.0")

    def test_invalid_discount_input(self):
        items = [_make_item(price=100.0, quantity=1)]
        discount_input = _mock_input("abc")
        result = update_totals(items, discount_input=discount_input)
        assert result["discount"] == Decimal("0")

    def test_empty_discount_input(self):
        items = [_make_item(price=100.0, quantity=1)]
        discount_input = _mock_input("")
        result = update_totals(items, discount_input=discount_input)
        assert result["discount"] == Decimal("0")

    def test_no_inputs(self):
        items = [_make_item(price=50.0, quantity=2)]
        result = update_totals(items, discount_input=None, tax_input=None)
        assert result["subtotal"] == Decimal("100.0")
        assert result["total"] == Decimal("100.0")


# ─── calculate_change ────────────────────────────────────────────────────────

class TestCalculateChange:
    def test_exact_payment(self):
        change, text, is_negative = calculate_change(Decimal("100"), "100")
        assert change == Decimal("0")
        assert "0.00" in text
        assert is_negative is False

    def test_overpayment(self):
        change, text, is_negative = calculate_change(Decimal("80"), "100")
        assert change == Decimal("20")
        assert "20.00" in text
        assert is_negative is False

    def test_underpayment(self):
        change, text, is_negative = calculate_change(Decimal("100"), "50")
        assert change == Decimal("-50")
        assert "-50.00" in text
        assert is_negative is True

    def test_empty_input(self):
        change, text, is_negative = calculate_change(Decimal("100"), "")
        assert change == Decimal("-100")
        assert is_negative is True

    def test_invalid_input(self):
        change, text, is_negative = calculate_change(Decimal("100"), "abc")
        assert change == Decimal("-100")
        assert is_negative is True

    def test_zero_total(self):
        change, text, is_negative = calculate_change(Decimal("0"), "50")
        assert change == Decimal("50")
        assert is_negative is False


# ─── build_invoice_data ──────────────────────────────────────────────────────

class TestBuildInvoiceData:
    def test_basic_invoice(self):
        items = [_make_item(price=10.0, quantity=2)]
        result = build_invoice_data(items, customer_id=None, discount_text="0", tax_text="0", payment_method_text="Cash")
        assert result["customer"] is None
        assert result["payment_method"] == "cash"
        assert len(result["items"]) == 1
        assert result["items"][0]["product"] == "prod-1"
        assert result["items"][0]["quantity"] == "2"

    def test_with_customer(self):
        items = [_make_item()]
        result = build_invoice_data(items, customer_id=42, discount_text="0", tax_text="0", payment_method_text="Card")
        assert result["customer"] == 42
        assert result["payment_method"] == "card"

    def test_with_discount_and_tax(self):
        items = [_make_item()]
        result = build_invoice_data(items, customer_id=None, discount_text="10", tax_text="5", payment_method_text="Cash")
        assert result["discount_percent"] == "10"
        assert result["tax_percent"] == "5"

    def test_multiple_items(self):
        items = [_make_item(price=10.0, quantity=1), _make_item(price=20.0, quantity=3)]
        result = build_invoice_data(items, customer_id=None, discount_text="0", tax_text="0", payment_method_text="Cash")
        assert len(result["items"]) == 2

    def test_has_date_fields(self):
        items = [_make_item()]
        result = build_invoice_data(items, customer_id=None, discount_text="0", tax_text="0", payment_method_text="Cash")
        assert "invoice_date" in result
        assert "due_date" in result

    def test_empty_cart(self):
        result = build_invoice_data([], customer_id=None, discount_text="0", tax_text="0", payment_method_text="Cash")
        assert result["items"] == []

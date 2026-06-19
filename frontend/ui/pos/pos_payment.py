"""POS Payment and totals logic — extracted from POSScreen.

Pure functions for calculating totals, building invoice data, and updating display.
"""
from decimal import Decimal
from datetime import date


def update_totals(cart_items, discount_input=None, tax_input=None):
    """Calculate invoice totals from cart items.

    Returns dict with keys: subtotal, discount, tax, total, discount_pct, tax_pct
    """
    subtotal = sum(item["total"] for item in cart_items)

    discount_pct = Decimal("0")
    if discount_input is not None:
        try:
            discount_pct = Decimal(discount_input.text() or "0")
        except Exception:
            discount_pct = Decimal("0")

    tax_pct = Decimal("0")
    if tax_input is not None:
        try:
            tax_pct = Decimal(tax_input.text() or "0")
        except Exception:
            tax_pct = Decimal("0")

    discount = subtotal * discount_pct / Decimal("100")
    taxable = subtotal - discount
    tax = taxable * tax_pct / Decimal("100")
    total = taxable + tax

    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": total,
        "discount_pct": discount_pct,
        "tax_pct": tax_pct,
    }


def calculate_change(total, amount_paid_text):
    """Calculate change from amount paid text. Returns (change, formatted_string, is_negative)."""
    try:
        paid = Decimal(amount_paid_text or "0")
    except Exception:
        paid = Decimal("0")

    change = paid - total
    return change, f"Change: {change:.2f} AFN", change < 0


def build_invoice_data(cart_items, customer_id, discount_text, tax_text, payment_method_text):
    """Build invoice data dict for API submission."""
    invoice_data = {
        "customer": customer_id,
        "invoice_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "items": [],
        "payment_method": payment_method_text.lower(),
        "discount_percent": str(discount_text or "0"),
        "tax_percent": str(tax_text or "0"),
    }

    for item in cart_items:
        invoice_data["items"].append({
            "product": item["product_id"],
            "quantity": str(item["quantity"]),
            "batch_number": item["batch_number"],
            "unit_price": str(item["price"]),
        })

    return invoice_data


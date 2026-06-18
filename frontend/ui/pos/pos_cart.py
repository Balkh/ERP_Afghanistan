"""POS Cart management — extracted from POSScreen.

Pure functions that operate on cart_items list.
"""
from decimal import Decimal

from ui.common.batch_selection import BatchSelectionDialog


def add_to_cart(cart_items, product, api_client=None, parent=None):
    """Add a product to the cart, handling batch selection and stock checks.

    Returns (updated cart_items, alert_message_or_None, alert_level_or_None).
    """
    if not product:
        return cart_items, None, None

    product_id = product.get("id")
    product_name = product.get("name", product.get("generic_name", "Unknown"))
    sale_price = Decimal(str(product.get("sale_price", 0)))
    total_stock = product.get("total_stock", 0)
    batches = product.get("batches", [])

    if total_stock <= 0:
        return cart_items, f"Out of stock: {product_name}", "danger"

    selected_batch = _select_batch(batches, sale_price, api_client, parent)
    if not selected_batch:
        return cart_items, None, None

    batch_number = selected_batch.get("batch_number", "")
    batch_price = Decimal(str(selected_batch.get("sale_price", sale_price)))
    batch_stock = Decimal(str(selected_batch.get("remaining_quantity", 0)))

    existing = find_cart_item(cart_items, product_id, batch_number)
    if existing:
        if existing["quantity"] + 1 > batch_stock:
            return cart_items, f"Insufficient stock for batch {batch_number}", "warning"
        existing["quantity"] += 1
        existing["total"] = existing["quantity"] * existing["price"]
    else:
        cart_items.append({
            "product_id": product_id,
            "product_name": product_name,
            "batch_number": batch_number,
            "quantity": 1,
            "price": batch_price,
            "total": batch_price,
            "max_stock": batch_stock,
            "requires_prescription": product.get("requires_prescription", False),
            "is_controlled": product.get("is_controlled_substance", False),
            "expiry_date": selected_batch.get("expiry_date", ""),
        })

    # Stock/batch alerts take priority over prescription/controlled alerts
    alert_msg = None
    alert_level = None
    if product.get("requires_prescription"):
        alert_msg = f"Prescription required: {product_name}"
        alert_level = "warning"
    if product.get("is_controlled_substance"):
        alert_msg = f"Controlled substance: {product_name} — Pharmacist approval needed"
        alert_level = "danger"

    return cart_items, alert_msg, alert_level


def _select_batch(batches, fallback_price, api_client=None, parent=None):
    """Show batch selection dialog if needed; returns selected batch or None."""
    if len(batches) == 1:
        return batches[0]
    if len(batches) > 1 and parent:
        dialog = BatchSelectionDialog(parent, batches, api_client=api_client)
        if dialog.exec():
            return dialog.selected_batch
    return None


def find_cart_item(cart_items, product_id, batch_number):
    """Return existing cart item matching product+batch, or None."""
    for item in cart_items:
        if item["product_id"] == product_id and item["batch_number"] == batch_number:
            return item
    return None


def remove_item(cart_items, index):
    """Remove item at index from cart_items."""
    if 0 <= index < len(cart_items):
        cart_items.pop(index)
        return True
    return False

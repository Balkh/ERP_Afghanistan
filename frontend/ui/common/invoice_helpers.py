"""Shared pure utility functions for sales and purchase invoice screens.

Extracted from SalesInvoiceScreen and PurchaseInvoiceScreen to eliminate
~200 lines of duplicated logic across both files.
"""

import json
import os
from decimal import Decimal


# ---------------------------------------------------------------------------
# API response parsing (used in load_customers, load_suppliers, load_warehouses)
# ---------------------------------------------------------------------------

def parse_api_list_response(response, fallback=None):
    """Parse a DRF-style paginated or list response into a plain list of dicts.

    Handles:
      - Raw list:            [{…}, {…}]
      - StandardizedJSONRenderer envelope: {"success": true, "data": …}
      - Paginated wrapper:   {"results": [{…}]}
      - Single object:       {"id": …}

    Returns *fallback* (default ``[]``) when nothing parseable is found.
    """
    fallback = fallback if fallback is not None else []

    if isinstance(response, list):
        return [r for r in response if isinstance(r, dict)]

    if not isinstance(response, dict):
        return fallback

    data = response.get("data", response)

    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]

    if isinstance(data, dict):
        if "results" in data:
            return [r for r in data["results"] if isinstance(r, dict)]
        if "id" in data:
            return [data]

    return fallback


# ---------------------------------------------------------------------------
# Date format helpers
# ---------------------------------------------------------------------------

def load_date_format():
    """Load date format preference (``'gregorian'`` | ``'shamsi'``) from the
    theme config file.  Returns ``'gregorian'`` on any failure."""
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'config', 'theme_preference.json'
        )
        if os.path.exists(config_path):
            with open(config_path) as f:
                cfg = json.load(f)
            return cfg.get('date_format', 'gregorian')
    except Exception:
        pass
    return 'gregorian'


def apply_date_format_to_edits(date_edits, fmt):
    """Apply display format to a list of QDateEdit widgets.

    *fmt* should be ``'shamsi'`` or ``'gregorian'`` (or anything else for
    the default).
    """
    display = "yyyy/MM/dd" if fmt == "shamsi" else "yyyy-MM-dd"
    for w in date_edits:
        w.setDisplayFormat(display)


# ---------------------------------------------------------------------------
# Invoice totals calculation (pure function — no Qt dependency)
# ---------------------------------------------------------------------------

def calculate_line_total(qty, price, discount):
    """Return the line total for a single invoice item."""
    return qty * price - discount


def calculate_invoice_totals(
    line_subtotal,
    overall_discount=Decimal("0"),
    tax_rate=Decimal("0"),
    tax_enabled=False,
    paid=Decimal("0"),
):
    """Compute invoice totals from a pre-summed line subtotal.

    Returns a dict with keys:
        taxable, tax_amount, total, balance
    """
    taxable = line_subtotal - overall_discount
    tax_amount = taxable * tax_rate / Decimal("100") if tax_enabled else Decimal("0")
    total = taxable + tax_amount
    balance = total - paid

    return {
        "taxable": taxable,
        "tax_amount": tax_amount,
        "total": total,
        "balance": balance,
    }

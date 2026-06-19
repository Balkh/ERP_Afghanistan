"""Dashboard section builders and widget helpers.

Extracted from dashboard.py — role-specific section builders that convert
API data into QFrame/QGridLayout widgets.  Pure data→UI transformations
with no state management.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PySide6.QtGui import QFont
from ui.constants import (FONT_NAME_PRIMARY, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_6,
                           MARGIN_PAGE, BORDER_RADIUS_MD, BORDER_RADIUS_SM,
                           TEXT_HELPER, TEXT_CARD_TITLE, TEXT_SECTION_TITLE, TEXT_TABLE,
                           COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_BORDER_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_WARNING)
from ui.dashboard_colors import DashboardColorScheme


def make_role_frame():
    """Create the role overview card frame."""
    frame = QFrame()
    frame.setObjectName("roleCard")
    frame.setStyleSheet(f"QFrame#roleCard {{ background: {COLOR_BG_ELEVATED}; border-radius: 12px; }}")
    stack = QVBoxLayout(frame)
    stack.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
    stack.setSpacing(SPACING_SM + SPACING_XS)
    return frame, stack


def make_alert_frame():
    """Create the alerts card frame."""
    frame = QFrame()
    frame.setObjectName("alertCard")
    frame.setStyleSheet(f"QFrame#alertCard {{ background: {COLOR_BG_ELEVATED}; border-radius: 12px; }}")
    stack = QVBoxLayout(frame)
    stack.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
    stack.setSpacing(SPACING_SM)
    return frame, stack


def make_actions_frame():
    """Create the quick actions card frame."""
    frame = QFrame()
    frame.setObjectName("actionsCard")
    frame.setStyleSheet(f"QFrame#actionsCard {{ background: {COLOR_BG_ELEVATED}; border-radius: 12px; }}")
    return frame


def mini_card(label, value, color_key, is_currency=False):
    """Create a small stat card widget."""
    c = DashboardColorScheme.get(color_key)
    f = QFrame()
    f.setStyleSheet(f"QFrame {{ background: {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; }}")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
    lay.setSpacing(SPACING_XS)

    lbl = QLabel(label)
    lbl.setFont(QFont(FONT_NAME_PRIMARY, TEXT_HELPER))
    lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
    lay.addWidget(lbl)

    if is_currency:
        try:
            display = f"AFN {float(value):,.2f}"
        except (ValueError, TypeError):
            display = "AFN 0.00"
    else:
        display = str(value)

    v = QLabel(display)
    v.setFont(QFont(FONT_NAME_PRIMARY, TEXT_CARD_TITLE, QFont.Weight.Bold))
    v.setStyleSheet(f"color: {c};")
    v.setWordWrap(True)
    lay.addWidget(v)

    return f


def alert_line(label, status, color_key):
    """Create a single alert status line widget."""
    c = DashboardColorScheme.get(color_key)
    box = QFrame()
    box.setStyleSheet(f"""
        QFrame {{
            background-color: {COLOR_BORDER};
            border: 1px solid {COLOR_BORDER_LIGHT};
            border-left: 3px solid {c};
            border-radius: {BORDER_RADIUS_SM}px;
        }}
    """)
    row = QHBoxLayout(box)
    row.setContentsMargins(SPACING_SM, SPACING_6, SPACING_SM, SPACING_6)
    row.setSpacing(SPACING_SM)

    dot = QLabel("●")
    dot.setFont(QFont(FONT_NAME_PRIMARY, TEXT_TABLE))
    dot.setStyleSheet(f"color: {c};")
    row.addWidget(dot)

    txt = f"{label}: {status}" if label else status
    lbl = QLabel(txt)
    lbl.setFont(QFont(FONT_NAME_PRIMARY, TEXT_TABLE))
    lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
    row.addWidget(lbl)
    row.addStretch()
    return box


def clear_layout(layout):
    """Recursively clear all widgets from a layout."""
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        elif item.layout():
            clear_layout(item.layout())


def build_financial_section(fin):
    """Build the financial overview grid for ADMIN/ACCOUNTANT roles."""
    bal = fin.get('balance_summary', {}) or {}
    pend = fin.get('pending_counts', {}) or {}
    jour = fin.get('journal_status', {}) or {}
    today = fin.get('today_activity', {}) or {}

    items = [
        ("Total Assets",      bal.get('total_assets', 0),      'green',  True),
        ("Total Liabilities", bal.get('total_liabilities', 0),  'red',    True),
        ("Equity",            bal.get('total_equity', 0),       'blue',   True),
        ("Sales Today",       today.get('sales', 0),            'green',  True),
        ("Purchases Today",   today.get('purchases', 0),        'red',    True),
        ("Pending Sales",     pend.get('sales_invoices', 0),    'peach',  False),
        ("Pending Purchases", pend.get('purchase_bills', 0),    'peach',  False),
        ("Posted JE",         jour.get('posted', 0),            'teal',   False),
        ("Unposted JE",       jour.get('unposted', 0),          'red',    False),
    ]
    grid = QGridLayout()
    grid.setSpacing(SPACING_SM)
    for i, (lbl, val, ck, is_cur) in enumerate(items):
        grid.addWidget(mini_card(lbl, val, ck, is_cur), i // 3, i % 3)
    return grid


def build_inventory_section(inv):
    """Build the inventory overview grid for WAREHOUSE role."""
    ov = inv.get('overview', {}) or {}
    al = inv.get('stock_alerts', {}) or {}
    act = inv.get('activity', {}) or {}

    items = [
        ("Products",         ov.get('total_products', 0),      'blue',   False),
        ("Batches",          ov.get('total_batches', 0),       'mauve',  False),
        ("Warehouses",       ov.get('active_warehouses', 0),   'teal',   False),
        ("Out of Stock",     al.get('out_of_stock', 0),        'red',    False),
        ("Low Stock",        al.get('low_stock', 0),           'peach',  False),
        ("Expiring",         al.get('expiring_soon', 0),       'yellow', False),
        ("Movements Today",  act.get('movements_today', 0),    'green',  False),
    ]
    grid = QGridLayout()
    grid.setSpacing(SPACING_SM)
    for i, (lbl, val, ck, _) in enumerate(items):
        grid.addWidget(mini_card(lbl, val, ck, False), i // 3, i % 3)
    return grid


def build_hr_section(hr):
    """Build the HR overview grid for HR role."""
    ov = hr.get('overview', {}) or {}
    att = hr.get('today_attendance', {}) or {}

    items = [
        ("Active Employees", ov.get('active_employees', 0), 'blue',  False),
        ("Departments",      ov.get('departments', 0),      'mauve', False),
        ("Present Today",    att.get('present', 0),         'green', False),
        ("Absent Today",     att.get('absent', 0),          'red',   False),
        ("On Leave",         att.get('on_leave', 0),        'peach', False),
    ]
    grid = QGridLayout()
    grid.setSpacing(SPACING_SM)
    for i, (lbl, val, ck, _) in enumerate(items):
        grid.addWidget(mini_card(lbl, val, ck, False), i // 3, i % 3)
    return grid


def build_role_section(role, data):
    """Build the role-specific overview section. Returns (title_label, grid_layout)."""
    from ui.role_manager import UserRole

    fin = data.get('financial', {}) or {}
    inv = data.get('inventory', {}) or {}
    hr = data.get('hr', {}) or {}

    titles = {
        UserRole.ADMIN: "Financial Overview",
        UserRole.ACCOUNTANT: "Accounting Overview",
        UserRole.WAREHOUSE: "Inventory Overview",
        UserRole.HR: "HR Overview",
    }
    title = titles.get(role, "Overview")

    if role in (UserRole.ADMIN, UserRole.ACCOUNTANT):
        grid = build_financial_section(fin)
    elif role == UserRole.WAREHOUSE:
        grid = build_inventory_section(inv)
    elif role == UserRole.HR:
        grid = build_hr_section(hr)
    else:
        grid = build_inventory_section(inv)

    return title, grid


def build_alert_section(data):
    """Build the alerts section. Returns list of (label, status, color_key) tuples."""
    ops = data.get('operations', {}) or {}
    al_data = ops.get('alerts', {}) or {}
    recent = al_data.get('recent', []) if isinstance(al_data, dict) else []
    rcount = al_data.get('recent_count', 0) if isinstance(al_data, dict) else 0

    health = data.get('health', {}) or {}
    db = health.get('database', {}) or {}
    db_ok = db.get('status', '') == 'ok'

    lines = [
        ("API", "Connected", 'green'),
        ("Database", "Healthy" if db_ok else "Issue", 'green' if db_ok else 'red'),
    ]

    if rcount > 0 and isinstance(recent, list):
        for a in recent[:3]:
            msg = a.get('message', '') if isinstance(a, dict) else str(a)
            sev = a.get('severity', 'info') if isinstance(a, dict) else 'info'
            ck = DashboardColorScheme.for_severity(sev)
            lines.append(("", msg, ck))
    else:
        lines.append(("System", "No current alerts", 'blue'))

    return lines

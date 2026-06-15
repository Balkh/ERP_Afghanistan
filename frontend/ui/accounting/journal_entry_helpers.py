"""Helpers for the Journal Entry screen."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QComboBox, QLineEdit
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.constants import SPACING_SM, SPACING_XS, BORDER_RADIUS_LG, COLOR_BG_MAIN, COLOR_BORDER
from utils.format import safe_float


def build_filter_bar():
    bar = QFrame()
    bar.setStyleSheet(
        f"background-color: {COLOR_BG_MAIN}; border: 1px solid {COLOR_BORDER}; "
        f"border-radius: {BORDER_RADIUS_LG};"
    )
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
    layout.setSpacing(SPACING_SM + SPACING_XS)

    type_filter = QComboBox()
    type_filter.addItem("All Types", "")
    for value in ("GENERAL", "SALE", "PURCHASE", "PAYMENT", "RECEIPT", "ADJUSTMENT", "RETURN"):
        type_filter.addItem(value.title(), value)

    status_filter = QComboBox()
    status_filter.addItem("All Status", "")
    status_filter.addItem("Posted", "posted")
    status_filter.addItem("Draft", "draft")

    search_input = QLineEdit()
    search_input.setPlaceholderText("Search entry #, description, reference...")
    search_input.setMinimumWidth(240)

    btn_apply = EnterpriseButton(text="Apply", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)

    layout.addWidget(QLabel("Type:"))
    layout.addWidget(type_filter)
    layout.addWidget(QLabel("Status:"))
    layout.addWidget(status_filter)
    layout.addWidget(QLabel("Search:"))
    layout.addWidget(search_input)
    layout.addWidget(btn_apply)
    layout.addStretch()

    return bar, {
        "type_filter": type_filter,
        "status_filter": status_filter,
        "date_from": None,
        "date_to": None,
        "search_input": search_input,
        "btn_apply": btn_apply,
    }


def build_filter_params(type_filter, status_filter, search_input):
    params = {}
    entry_type = type_filter.currentData() if type_filter else ""
    status = status_filter.currentData() if status_filter else ""
    search = search_input.text().strip() if search_input else ""
    if entry_type:
        params["entry_type"] = entry_type
    if status == "posted":
        params["is_posted"] = "true"
    elif status == "draft":
        params["is_posted"] = "false"
    if search:
        params["search"] = search
    return params


def transform_entries(entries):
    rows = []
    for entry in entries:
        lines = entry.get("lines") or entry.get("journalentryline_set") or []
        debit = entry.get("total_debit")
        credit = entry.get("total_credit")
        if debit is None:
            debit = sum(safe_float(line.get("debit", 0)) for line in lines if isinstance(line, dict))
        if credit is None:
            credit = sum(safe_float(line.get("credit", 0)) for line in lines if isinstance(line, dict))
        is_posted = bool(entry.get("is_posted", entry.get("posted", False)))
        rows.append({
            **entry,
            "entry_number": entry.get("entry_number") or entry.get("number") or str(entry.get("id", "")),
            "entry_date": str(entry.get("entry_date") or entry.get("date") or entry.get("created_at") or "")[:10],
            "entry_type": entry.get("entry_type") or entry.get("type") or "",
            "description": entry.get("description") or "",
            "debit": f"{safe_float(debit):,.2f}",
            "credit": f"{safe_float(credit):,.2f}",
            "status": "Posted" if is_posted else "Draft",
            "reference": entry.get("reference") or entry.get("reference_number") or "",
            "is_posted": is_posted,
        })
    return rows

"""Shared footer (Zone 3) builder for sales and purchase invoice screens.

Extracted from SalesInvoiceScreen._build_footer and
PurchaseInvoiceScreen._build_footer which were ~130 lines of nearly
identical code differing only in the entity label ("Customer" vs "Supplier").
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QFrame, QLabel, QDoubleSpinBox, QCheckBox, QTextEdit, QMenu,
)
from PySide6.QtCore import Qt

from ui.constants import (
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XXL,
    TEXT_CARD_TITLE, TEXT_BODY, TEXT_TABLE,
    BORDER_RADIUS_SM, BORDER_RADIUS_LG,
    COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_SUCCESS, COLOR_DANGER,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize


def build_invoice_footer(parent, entity_type="customer", on_print=None, on_save=None,
                         on_clear=None):
    """Build the Zone 3 summary panel and attach widget references to *parent*.

    Widget references set on *parent* (via ``setattr``):

    Generic (both screens):
        entity_phone, entity_address, credit_limit_label, balance_label,
        subtotal_label, discount_input, tax_enabled_cb, tax_input,
        tax_amount_label, total_label, paid_input, notes_input,
        save_btn, confirm_btn, more_btn, return_btn,
        submit_wf_btn, approve_wf_btn, reject_wf_btn, post_wf_btn

    Parameters
    ----------
    parent : QWidget
        The invoice screen instance that will own these widgets.
    entity_type : str
        ``"customer"`` (sales) or ``"supplier"`` (purchase).
        Controls label text only.
    on_print, on_save, on_clear : callable or None
        Optional callbacks wired to the More menu actions.
    """
    zone3 = QFrame()
    zone3.setObjectName("zoneSummary")
    zone3.setStyleSheet(
        f"QFrame#zoneSummary {{ background: {COLOR_BG_ELEVATED}; "
        f"border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; }}"
    )
    zone3_layout = QHBoxLayout(zone3)
    zone3_layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
    zone3_layout.setSpacing(SPACING_XXL)

    _label = entity_type.title()  # "Customer" or "Supplier"

    # ---- Left: Entity details ----
    details_form = QFormLayout()
    details_form.setSpacing(SPACING_XS)
    details_form.setContentsMargins(0, 0, 0, 0)
    details_form.setLabelAlignment(Qt.AlignRight)

    entity_phone = QLabel("—")
    entity_phone.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
    details_form.addRow("Phone:", entity_phone)

    credit_limit_label = QLabel("—")
    credit_limit_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
    details_form.addRow("Credit Limit:", credit_limit_label)

    balance_label = QLabel("0.00")
    balance_label.setStyleSheet(
        f"color: {COLOR_DANGER}; font-size: {TEXT_TABLE}px; font-weight: bold;"
    )
    details_form.addRow("Balance:", balance_label)

    entity_address = QTextEdit()
    entity_address.setReadOnly(True)
    entity_address.setMaximumHeight(40)
    entity_address.setStyleSheet(
        f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px; "
        f"border: none; background: transparent;"
    )
    details_form.addRow("Address:", entity_address)

    zone3_layout.addLayout(details_form)
    zone3_layout.addSpacing(SPACING_LG)

    # ---- Center: Totals ----
    totals_layout = QFormLayout()
    totals_layout.setSpacing(SPACING_XS)
    totals_layout.setContentsMargins(0, 0, 0, 0)
    totals_layout.setLabelAlignment(Qt.AlignRight)

    subtotal_label = QLabel("0.00")
    subtotal_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}px;")
    totals_layout.addRow("Subtotal:", subtotal_label)

    discount_input = QDoubleSpinBox()
    discount_input.setRange(0, 999999)
    discount_input.setValue(0)
    discount_input.setMaximumWidth(120)
    totals_layout.addRow("Discount:", discount_input)

    tax_enabled_cb = QCheckBox()
    tax_enabled_cb.setChecked(False)
    totals_layout.addRow("Enable Tax:", tax_enabled_cb)

    tax_input = QDoubleSpinBox()
    tax_input.setRange(0, 100)
    tax_input.setValue(0)
    tax_input.setSuffix("%")
    tax_input.setMaximumWidth(120)
    tax_input.setEnabled(False)
    totals_layout.addRow("Tax Rate:", tax_input)

    tax_amount_label = QLabel("0.00")
    tax_amount_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
    totals_layout.addRow("Tax Amt:", tax_amount_label)

    total_label = QLabel("0.00")
    total_label.setStyleSheet(
        f"color: {COLOR_SUCCESS}; font-size: {TEXT_CARD_TITLE}px; font-weight: 700;"
    )
    totals_layout.addRow("Total:", total_label)

    paid_input = QDoubleSpinBox()
    paid_input.setRange(0, 999999)
    paid_input.setValue(0)
    paid_input.setMaximumWidth(120)
    totals_layout.addRow("Paid:", paid_input)

    notes_input = QTextEdit()
    notes_input.setPlaceholderText("Notes...")
    notes_input.setMaximumHeight(40)
    notes_input.setMaximumWidth(120)
    notes_input.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_TABLE}px;")
    totals_layout.addRow("Notes:", notes_input)

    zone3_layout.addLayout(totals_layout)
    zone3_layout.addSpacing(SPACING_LG)

    # ---- Right: Action buttons ----
    action_layout = QVBoxLayout()
    action_layout.setSpacing(SPACING_SM)
    action_layout.setContentsMargins(0, 0, 0, 0)

    save_btn = EnterpriseButton(text="Save Invoice", variant=ButtonVariant.PRIMARY,
                                size=ButtonSize.MEDIUM)
    action_layout.addWidget(save_btn)

    confirm_label = "Confirm & Dispatch" if entity_type == "customer" else "Confirm & Receive"
    confirm_btn = EnterpriseButton(text=confirm_label, variant=ButtonVariant.SUCCESS,
                                   size=ButtonSize.MEDIUM)
    action_layout.addWidget(confirm_btn)

    more_btn = EnterpriseButton(text="More ▾", variant=ButtonVariant.SECONDARY,
                                size=ButtonSize.MEDIUM)
    more_menu = QMenu(parent)
    if on_print:
        more_menu.addAction("Print Invoice (Ctrl+P)", on_print)
    if on_save:
        more_menu.addAction("Save as Draft", on_save)
    if on_clear:
        more_menu.addAction("Clear Form (Ctrl+L)", on_clear)
        more_menu.addAction("New Invoice (Ctrl+N)", on_clear)
    more_btn.setMenu(more_menu)
    action_layout.addWidget(more_btn)

    return_btn = EnterpriseButton(text="Create Return", variant=ButtonVariant.WARNING,
                                  size=ButtonSize.MEDIUM)
    return_btn.setVisible(False)
    action_layout.addWidget(return_btn)

    # Workflow buttons (hidden by default)
    submit_wf_btn = EnterpriseButton(text="Submit for Approval",
                                     variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    submit_wf_btn.setVisible(False)
    action_layout.addWidget(submit_wf_btn)

    approve_wf_btn = EnterpriseButton(text="Approve", variant=ButtonVariant.SUCCESS,
                                      size=ButtonSize.MEDIUM)
    approve_wf_btn.setVisible(False)
    action_layout.addWidget(approve_wf_btn)

    reject_wf_btn = EnterpriseButton(text="Reject", variant=ButtonVariant.DANGER,
                                     size=ButtonSize.MEDIUM)
    reject_wf_btn.setVisible(False)
    action_layout.addWidget(reject_wf_btn)

    post_wf_btn = EnterpriseButton(text="Post", variant=ButtonVariant.PRIMARY,
                                   size=ButtonSize.MEDIUM)
    post_wf_btn.setVisible(False)
    action_layout.addWidget(post_wf_btn)

    action_layout.addStretch()
    zone3_layout.addLayout(action_layout)

    # ---- Attach all references to parent ----
    _refs = {
        "entity_phone": entity_phone,
        "entity_address": entity_address,
        "credit_limit_label": credit_limit_label,
        "balance_label": balance_label,
        "subtotal_label": subtotal_label,
        "discount_input": discount_input,
        "tax_enabled_cb": tax_enabled_cb,
        "tax_input": tax_input,
        "tax_amount_label": tax_amount_label,
        "total_label": total_label,
        "paid_input": paid_input,
        "notes_input": notes_input,
        "save_btn": save_btn,
        "confirm_btn": confirm_btn,
        "more_btn": more_btn,
        "return_btn": return_btn,
        "submit_wf_btn": submit_wf_btn,
        "approve_wf_btn": approve_wf_btn,
        "reject_wf_btn": reject_wf_btn,
        "post_wf_btn": post_wf_btn,
    }
    for name, widget in _refs.items():
        setattr(parent, name, widget)

    # Attach the zone3 frame itself
    setattr(parent, "_zone3_frame", zone3)

    return zone3

"""ACCOUNTING DIAGNOSTICS CORRECTNESS REMEDIATION — validation.

Covers:
  Issue A — false positive on valid inventory sales (COGS debit wrongly summed).
  Issue B — gateway false-negative risk (source_module/source_document not set).

Required fixtures:
  1. clean sale without COGS
  2. clean sale with COGS
  3. tampered sale
  4. ENGINE path
  5. GATEWAY path

Verifies: no false positives, no false negatives, identical results across routes.
"""
import uuid
import inspect
from decimal import Decimal
from datetime import timedelta

import pytest
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.management.commands.seed_accounts import seed_canonical_chart_of_accounts
from sales.models import Customer, SalesInvoice
from core.accounting_registry import ACC
from core.services.financial_diagnostics import FinancialDiagnostics
from core.services import anomaly_detection as ad
from core.services.journal_gateway import JournalGateway
from core.drift_prevention.migration_registry import MigrationRegistry


def _anomaly_service():
    for name in dir(ad):
        obj = getattr(ad, name)
        if inspect.isclass(obj) and obj.__module__ == ad.__name__ and hasattr(obj, "detect_ledger_anomalies"):
            return obj
    raise AssertionError("anomaly service not found")


def _seed():
    if Account.objects.count() == 0:
        seed_canonical_chart_of_accounts()


def _customer(name="Cust"):
    return Customer.objects.create(
        name=name, code="C-" + uuid.uuid4().hex[:8], customer_type="COMPANY", company_name=name,
        business_license="L" + uuid.uuid4().hex[:6], status="ACTIVE", is_active=True,
    )


def _invoice(cust, subtotal, tax=Decimal("0.00"), discount=Decimal("0.00")):
    total = subtotal - discount + tax
    today = timezone.now().date()
    return SalesInvoice.objects.create(
        invoice_number="INV-" + uuid.uuid4().hex[:8], customer=cust,
        order_date=today, invoice_date=today, due_date=today + timedelta(days=30),
        subtotal=subtotal, discount=discount, tax=tax, total_amount=total,
        status="CONFIRMED", payment_status="UNPAID", is_active=True,
    )


def _post_sale(inv, with_cogs=False, cogs=Decimal("0.00"), route="ENGINE"):
    """Post a sales JE the way production does, via ENGINE or GATEWAY route.

    ENGINE: build the entry directly with source_module/source_document set
            (mirrors MigrationRouter -> JournalEngine engine branch).
    GATEWAY: route through JournalGateway.create_entry with entity_type/entity_id
             only (the realistic gateway call); the gateway must derive the
             source fields itself (Issue B fix).
    """
    revenue = inv.subtotal - inv.discount
    lines = [
        {"account_code": ACC["ar"], "debit": inv.total_amount, "credit": Decimal("0.00"),
         "description": "AR"},
    ]
    if with_cogs and cogs > 0:
        lines.append({"account_code": ACC["sales_cogs"], "debit": cogs, "credit": Decimal("0.00"),
                      "description": "COGS"})
    lines.append({"account_code": ACC["sales_revenue"], "debit": Decimal("0.00"), "credit": revenue,
                  "description": "Revenue"})
    if inv.tax > 0:
        lines.append({"account_code": ACC["tax_payable"], "debit": Decimal("0.00"), "credit": inv.tax,
                      "description": "Tax"})
    if with_cogs and cogs > 0:
        lines.append({"account_code": ACC["inventory"], "debit": Decimal("0.00"), "credit": cogs,
                      "description": "Inventory"})

    if route == "GATEWAY":
        result = JournalGateway.create_entry(
            entry_type="SALE", description=f"Sale {inv.invoice_number}", lines=lines,
            entry_date=inv.invoice_date, reference=inv.invoice_number, auto_post=True,
            entity_type="SalesInvoice", entity_id=str(inv.id),
        )
        entry_id = result["entry_id"]
    else:  # ENGINE
        from accounting.services.journal_engine import JournalEngine
        result = JournalEngine.create_entry(
            entry_type="SALE", description=f"Sale {inv.invoice_number}", lines=lines,
            entry_date=inv.invoice_date, reference=inv.invoice_number, auto_post=True,
            source_module="sales", source_document=str(inv.id),
        )
        entry_id = result["entry_id"]

    inv.journal_entry_id = entry_id
    inv.save(update_fields=["journal_entry_id"])
    return JournalEntry.objects.get(id=entry_id)


def _ledger_hits():
    """Return set of invoice ids flagged by detect_ledger_anomalies."""
    svc = _anomaly_service()
    return {a["entity_id"] for a in svc.detect_ledger_anomalies()
            if a.get("anomaly_type") == "LEDGER_INVOICE_MISMATCH"}


def _integrity_mismatch_invoices():
    """Return set of invoice_numbers flagged INVOICE_JOURNAL_MISMATCH by check_ledger_integrity."""
    res = FinancialDiagnostics.check_ledger_integrity()
    out = set()
    for i in res["issues"]:
        if i["type"] == "INVOICE_JOURNAL_MISMATCH":
            out.add(i["entity"])
    return out


# ════════════════════════════════════════════════════════════════════
# ISSUE A — false positives / negatives, ENGINE route
# ════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_A1_clean_sale_without_cogs_no_false_positive():
    _seed()
    inv = _invoice(_customer("NoCOGS"), subtotal=Decimal("1000.00"))
    _post_sale(inv, with_cogs=False)
    assert str(inv.id) not in _ledger_hits()
    assert not any(inv.invoice_number in e for e in _integrity_mismatch_invoices())


@pytest.mark.django_db
def test_A2_clean_sale_WITH_cogs_no_false_positive():
    """THE regression case: valid Dr AR + Dr COGS / Cr Rev + Cr Inventory."""
    _seed()
    inv = _invoice(_customer("WithCOGS"), subtotal=Decimal("1000.00"))
    je = _post_sale(inv, with_cogs=True, cogs=Decimal("600.00"))
    # Sanity: entry balances; AR debit == total; sum(all debit) != total (1600)
    assert je.total_debit == je.total_credit == Decimal("1600.00")
    assert str(inv.id) not in _ledger_hits(), "COGS sale must NOT be flagged (Issue A)"
    assert not any(inv.invoice_number in e for e in _integrity_mismatch_invoices()), \
        "COGS sale must NOT be flagged by check_ledger_integrity (Issue A)"


@pytest.mark.django_db
def test_A3_tampered_sale_is_detected_with_cogs_present():
    """A real anomaly (AR debit != total) is still detected even with COGS lines."""
    _seed()
    inv = _invoice(_customer("Tampered"), subtotal=Decimal("1000.00"))
    je = _post_sale(inv, with_cogs=True, cogs=Decimal("600.00"))
    # Corrupt the AR line so AR debit (1000) -> 1300 (no longer == total 1000)
    ar = JournalEntryLine.objects.filter(entry=je, account__code=ACC["ar"]).first()
    ar.debit = ar.debit + Decimal("300.00")
    ar.save(update_fields=["debit"])

    assert str(inv.id) in _ledger_hits(), "tampered AR must be detected (no false negative)"
    assert any(inv.invoice_number in e for e in _integrity_mismatch_invoices())


@pytest.mark.django_db
def test_A4_missing_AR_line_is_detected():
    """If the AR line is entirely missing, AR-debit sum = 0 != total -> detected."""
    _seed()
    inv = _invoice(_customer("NoAR"), subtotal=Decimal("500.00"))
    je = _post_sale(inv, with_cogs=False)
    JournalEntryLine.objects.filter(entry=je, account__code=ACC["ar"]).delete()
    assert str(inv.id) in _ledger_hits(), "missing AR line must be detected"


# ════════════════════════════════════════════════════════════════════
# ISSUE B — GATEWAY route populates source fields; identical results
# ════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_B1_gateway_populates_source_module_and_document():
    _seed()
    inv = _invoice(_customer("GW"), subtotal=Decimal("1000.00"))
    je = _post_sale(inv, with_cogs=True, cogs=Decimal("400.00"), route="GATEWAY")
    assert je.source_module == "sales", f"GATEWAY must set source_module='sales', got {je.source_module!r}"
    assert je.source_document == str(inv.id), \
        f"GATEWAY must set source_document=str(id), got {je.source_document!r}"


@pytest.mark.django_db
def test_B2_gateway_clean_cogs_sale_no_false_positive():
    _seed()
    inv = _invoice(_customer("GWclean"), subtotal=Decimal("1000.00"))
    _post_sale(inv, with_cogs=True, cogs=Decimal("600.00"), route="GATEWAY")
    assert str(inv.id) not in _ledger_hits()


@pytest.mark.django_db
def test_B3_gateway_tampered_sale_is_detected():
    _seed()
    inv = _invoice(_customer("GWbad"), subtotal=Decimal("1000.00"))
    je = _post_sale(inv, with_cogs=True, cogs=Decimal("600.00"), route="GATEWAY")
    ar = JournalEntryLine.objects.filter(entry=je, account__code=ACC["ar"]).first()
    ar.debit = ar.debit + Decimal("250.00")
    ar.save(update_fields=["debit"])
    assert str(inv.id) in _ledger_hits(), "tampered GATEWAY sale must be detected (no false negative)"


@pytest.mark.django_db
def test_B4_identical_results_across_engine_and_gateway():
    """Same scenario posted via each route must yield the same diagnostic outcome."""
    _seed()
    # clean COGS sale via ENGINE and via GATEWAY -> both clean
    e_clean = _invoice(_customer("E1"), subtotal=Decimal("1000.00"))
    g_clean = _invoice(_customer("G1"), subtotal=Decimal("1000.00"))
    _post_sale(e_clean, with_cogs=True, cogs=Decimal("600.00"), route="ENGINE")
    _post_sale(g_clean, with_cogs=True, cogs=Decimal("600.00"), route="GATEWAY")

    # tampered COGS sale via ENGINE and via GATEWAY -> both flagged
    e_bad = _invoice(_customer("E2"), subtotal=Decimal("1000.00"))
    g_bad = _invoice(_customer("G2"), subtotal=Decimal("1000.00"))
    je_e = _post_sale(e_bad, with_cogs=True, cogs=Decimal("600.00"), route="ENGINE")
    je_g = _post_sale(g_bad, with_cogs=True, cogs=Decimal("600.00"), route="GATEWAY")
    for je in (je_e, je_g):
        ar = JournalEntryLine.objects.filter(entry=je, account__code=ACC["ar"]).first()
        ar.debit = ar.debit + Decimal("250.00")
        ar.save(update_fields=["debit"])

    hits = _ledger_hits()
    # clean ones (both routes) NOT flagged; bad ones (both routes) flagged -> identical behaviour
    assert str(e_clean.id) not in hits and str(g_clean.id) not in hits, "clean: identical (both clean)"
    assert str(e_bad.id) in hits and str(g_bad.id) in hits, "tampered: identical (both flagged)"
    # And the routing truly differed: confirm gateway entries carry the same source tags as engine
    assert JournalEntry.objects.get(id=g_clean.journal_entry_id).source_module == \
           JournalEntry.objects.get(id=e_clean.journal_entry_id).source_module == "sales"

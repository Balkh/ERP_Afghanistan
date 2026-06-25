"""FINANCIAL DIAGNOSTICS ACCURACY AUDIT.

Verifies CORRECTNESS (not just execution) of:
  - financial_diagnostics.FinancialDiagnostics.check_ledger_integrity
  - anomaly_detection.*.detect_ledger_anomalies

after the JournalLine->JournalEntryLine and source_type/source_id ->
source_module/source_document remediation.

Strategy:
  * Build controlled accounting fixtures via the REAL production posting path
    (SalesAccountingService.create_sales_journal_entry -> MigrationRouter ->
    JournalEngine), so source_module/source_document are written exactly as a
    real confirmed invoice would write them.
  * Clean data  -> expect ZERO ledger anomalies (false-positive guard).
  * Known anomaly (journal sum tampered to NOT match invoice total) -> expect
    the mismatch to be detected, with the right entity and amounts.
  * Compare expected vs actual.
"""
import uuid
from decimal import Decimal
from datetime import timedelta

import pytest
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.management.commands.seed_accounts import seed_canonical_chart_of_accounts
from sales.models import Customer, SalesInvoice
from sales.views import SalesAccountingService
from core.services.financial_diagnostics import FinancialDiagnostics
from core.services import anomaly_detection as ad


def _anomaly_service():
    """Return the class exposing detect_ledger_anomalies."""
    import inspect
    for name in dir(ad):
        obj = getattr(ad, name)
        if inspect.isclass(obj) and obj.__module__ == ad.__name__ and hasattr(obj, "detect_ledger_anomalies"):
            return obj
    raise AssertionError("No anomaly-detection class with detect_ledger_anomalies found")


def _seed_accounts():
    if Account.objects.count() == 0:
        seed_canonical_chart_of_accounts()


def _make_customer(name="Acme Pharma"):
    return Customer.objects.create(
        name=name,
        customer_type="COMPANY",
        company_name=name,
        business_license="LIC-" + uuid.uuid4().hex[:6],
        status="ACTIVE",
        is_active=True,
    )


def _make_invoice(customer, subtotal, tax=Decimal("0.00"), discount=Decimal("0.00")):
    """Create a confirmed, balanced sales invoice (no COGS)."""
    total = subtotal - discount + tax
    today = timezone.now().date()
    return SalesInvoice.objects.create(
        invoice_number="INV-" + uuid.uuid4().hex[:8],
        customer=customer,
        order_date=today,
        invoice_date=today,
        due_date=today + timedelta(days=30),
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total_amount=total,
        status="CONFIRMED",
        payment_status="UNPAID",
        is_active=True,
    )


def _post(invoice):
    """Post via the REAL production accounting service. Returns the JournalEntry."""
    result = SalesAccountingService.create_sales_journal_entry(invoice)
    assert result.get("success"), f"posting failed: {result}"
    invoice.refresh_from_db()
    je = JournalEntry.objects.get(id=invoice.journal_entry_id)
    return je


# ───────────────────────────────────────────────────────────────────
# PRE-FLIGHT: confirm the production posting writes the fields the
# diagnostics query on. If this fails, every diagnostic is a false
# negative on real data.
# ───────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_production_posting_tags_source_module_and_document_correctly():
    _seed_accounts()
    cust = _make_customer()
    inv = _make_invoice(cust, subtotal=Decimal("1000.00"))
    je = _post(inv)
    assert je.source_module == "sales", (
        f"EXPECTED source_module='sales', GOT {je.source_module!r} -- "
        "diagnostics filter on source_module='sales' would miss this entry"
    )
    assert je.source_document == str(inv.id), (
        f"EXPECTED source_document={str(inv.id)!r}, GOT {je.source_document!r} -- "
        "diagnostics match invoices by source_document==str(invoice.id)"
    )


# ───────────────────────────────────────────────────────────────────
# FALSE-POSITIVE GUARD: clean, balanced, correctly-posted invoice
# (no COGS) must produce NO ledger mismatch in either diagnostic.
# ───────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_clean_data_no_ledger_anomalies():
    _seed_accounts()
    cust = _make_customer()
    inv = _make_invoice(cust, subtotal=Decimal("1000.00"), tax=Decimal("0.00"))
    je = _post(inv)

    # Sanity: JE balances and AR debit == total_amount
    assert je.total_debit == je.total_credit, "posted JE must balance"
    assert je.total_debit == inv.total_amount

    integrity = FinancialDiagnostics.check_ledger_integrity()
    mismatches = [i for i in integrity["issues"]
                  if i["type"] in ("INVOICE_JOURNAL_MISMATCH", "UNBALANCED_JOURNAL")
                  and inv.invoice_number in i["entity"]]
    assert mismatches == [], f"FALSE POSITIVE in check_ledger_integrity: {mismatches}"

    svc = _anomaly_service()
    anomalies = svc.detect_ledger_anomalies()
    ledger_mismatches = [a for a in anomalies
                         if a.get("anomaly_type") == "LEDGER_INVOICE_MISMATCH"
                         and a.get("entity_id") == str(inv.id)]
    assert ledger_mismatches == [], f"FALSE POSITIVE in detect_ledger_anomalies: {ledger_mismatches}"


# ───────────────────────────────────────────────────────────────────
# TRUE-POSITIVE: tamper the journal so its debit sum no longer matches
# the invoice total. Both diagnostics must DETECT it.
# ───────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_known_anomaly_is_detected():
    _seed_accounts()
    cust = _make_customer("Tampered Co")
    inv = _make_invoice(cust, subtotal=Decimal("1000.00"))
    je = _post(inv)

    # Inject a KNOWN corruption: bump the AR (debit) line by 250.00 so the
    # ledger no longer reconciles to the invoice total (1000 -> 1250).
    ar_line = JournalEntryLine.objects.filter(entry=je, debit__gt=0).order_by("-debit").first()
    assert ar_line is not None
    original = ar_line.debit
    ar_line.debit = original + Decimal("250.00")
    ar_line.save(update_fields=["debit"])

    expected_je_debit_sum = original + Decimal("250.00")  # only AR is a debit (no COGS)

    # 1) detect_ledger_anomalies must flag LEDGER_INVOICE_MISMATCH for this invoice
    svc = _anomaly_service()
    anomalies = svc.detect_ledger_anomalies()
    hit = [a for a in anomalies
           if a.get("anomaly_type") == "LEDGER_INVOICE_MISMATCH"
           and a.get("entity_id") == str(inv.id)]
    assert len(hit) == 1, f"EXPECTED 1 ledger mismatch for {inv.id}, GOT {len(hit)}: {anomalies}"
    assert hit[0]["amount"] == str(inv.total_amount)
    # The explanation reports the tampered journal sum; compare numerically
    # (Decimal string formatting may omit trailing zeros, e.g. '1250' vs '1250.00').
    import re
    nums = re.findall(r"sum \(([0-9.]+)\)", hit[0]["explanation"])
    assert nums, f"explanation missing journal sum: {hit[0]['explanation']}"
    assert Decimal(nums[0]) == expected_je_debit_sum, (
        f"explanation should report tampered sum {expected_je_debit_sum}, "
        f"got {nums[0]} in: {hit[0]['explanation']}"
    )

    # 2) check_ledger_integrity must flag INVOICE_JOURNAL_MISMATCH (and the now-unbalanced JE)
    integrity = FinancialDiagnostics.check_ledger_integrity()
    inv_mismatch = [i for i in integrity["issues"]
                    if i["type"] == "INVOICE_JOURNAL_MISMATCH" and inv.invoice_number in i["entity"]]
    unbalanced = [i for i in integrity["issues"]
                  if i["type"] == "UNBALANCED_JOURNAL" and inv.invoice_number in i["entity"]]
    assert len(inv_mismatch) == 1, f"EXPECTED INVOICE_JOURNAL_MISMATCH, issues={integrity['issues']}"
    assert len(unbalanced) == 1, f"EXPECTED UNBALANCED_JOURNAL (debit now != credit), issues={integrity['issues']}"
    assert integrity["status"] == "DEGRADED"


# ───────────────────────────────────────────────────────────────────
# DISCRIMINATION: one clean + one tampered invoice -> exactly one
# detected, and it is the tampered one (no cross-contamination).
# ───────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_detector_discriminates_clean_from_tampered():
    _seed_accounts()
    cust = _make_customer("Mixed Co")
    clean = _make_invoice(cust, subtotal=Decimal("500.00"))
    bad = _make_invoice(cust, subtotal=Decimal("800.00"))
    _post(clean)
    je_bad = _post(bad)

    line = JournalEntryLine.objects.filter(entry=je_bad, debit__gt=0).order_by("-debit").first()
    line.debit = line.debit + Decimal("123.45")
    line.save(update_fields=["debit"])

    svc = _anomaly_service()
    ledger_hits = {a["entity_id"] for a in svc.detect_ledger_anomalies()
                   if a.get("anomaly_type") == "LEDGER_INVOICE_MISMATCH"}
    assert str(bad.id) in ledger_hits, "tampered invoice must be detected"
    assert str(clean.id) not in ledger_hits, "clean invoice must NOT be detected (no false positive)"

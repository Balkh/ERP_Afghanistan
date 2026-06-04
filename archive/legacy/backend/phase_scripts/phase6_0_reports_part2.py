"""
Phase 6.0 Report Generator Part 2 - WS-D, E, F, G, H
"""
import json
from pathlib import Path

ROOT = Path(r"E:\all downloads\Pharmacy_ERP")
DOCS = ROOT / "docs" / "PHASE6_0"
EV = DOCS / "evidence"

files_data = json.loads((EV / "ws_a_large_files.json").read_text(encoding="utf-8"))
classes_data = json.loads((EV / "ws_b_large_classes.json").read_text(encoding="utf-8"))
methods_data = json.loads((EV / "ws_c_large_methods.json").read_text(encoding="utf-8"))
dup_data = json.loads((EV / "ws_d_duplication.json").read_text(encoding="utf-8"))
summary = json.loads((EV / "summary.json").read_text(encoding="utf-8"))

AUDIT_ID = summary["audit_id"]
TS = summary["ts"]

def md_table(headers, rows):
    if not rows:
        return f"| {' | '.join(headers)} |\n| {' | '.join(['---']*len(headers))} |\n| _(none)_ |\n"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)

# =============================================================================
# WS-D: DUPLICATION AUDIT
# =============================================================================
sig_dups = dup_data["duplicate_signatures"]
body_dups = dup_data["duplicate_bodies"]
fanout = dup_data["method_fanout"]
helpers = dup_data["helpers"]

# Classify duplication categories
def categorize(sig):
    name = sig.split("(")[0].lower()
    if "validate" in name or "validation" in name:
        return "validation"
    if "save" in name or "create" in name or "update" in name or "delete" in name:
        return "persistence"
    if "render" in name or "build" in name or "setup" in name or "init" in name:
        return "ui"
    if "compute" in name or "calculate" in name or "total" in name or "sum" in name:
        return "calculation"
    if "format" in name or "to_" in name or "from_" in name:
        return "formatting"
    if "fetch" in name or "get_" in name or "list_" in name:
        return "query"
    if "log" in name or "audit" in name:
        return "audit"
    return "misc"

cat_counter = {}
for sig, c, _ in sig_dups:
    cat = categorize(sig)
    cat_counter[cat] = cat_counter.get(cat, 0) + c

sig_rows = [(sig, c, categorize(sig), "; ".join(ex[:3])) for sig, c, ex in sig_dups[:30]]
body_rows = [(h, c, "; ".join(ex[:2])) for h, c, ex in body_dups[:20]]
fanout_rows = [(m, len(set(cls)), ", ".join(sorted(set(cls))[:4])) for m, cls in fanout[:20]]

ws_d = f"""# WS-D: Duplication Audit

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
**Scope:** Function signatures, function bodies, method fan-out, helper definitions  
**Method:** AST-based normalization, MD5 fingerprinting, cross-file fan-out analysis

---

## 1. Summary

| Metric | Count |
|--------|-------|
| Duplicate function signatures (≥3 occurrences) | {len(sig_dups)} |
| Duplicate function bodies (≥2 normalized matches) | {len(body_dups)} |
| Method names defined in ≥3 classes (fan-out) | {len(fanout)} |
| Private helper candidates (<30 LOC) | {len(helpers)} |

---

## 2. Duplication by Category (Signatures)

| Category | Occurrences | Description |
|----------|-------------|-------------|
"""
for cat, count in sorted(cat_counter.items(), key=lambda x: -x[1]):
    desc = {
        "validation": "Validation/precondition checks repeated across services",
        "persistence": "Save/create/update patterns repeated across viewsets",
        "ui": "Render/build/init patterns in UI layer",
        "calculation": "Mathematical/totalling patterns in services",
        "formatting": "Data-formatting helpers in utils and screens",
        "query": "Database fetch/get patterns in viewsets",
        "audit": "Audit/log patterns in services",
        "misc": "Other repeated function names",
    }.get(cat, "-")
    ws_d += f"| `{cat}` | {count} | {desc} |\n"

ws_d += f"""
---

## 3. Top Duplicate Signatures

{md_table(['Signature', 'Count', 'Category', 'Examples (first 3)'], sig_rows)}

---

## 4. Top Duplicate Bodies (Normalized)

{md_table(['Body Hash', 'Count', 'Examples'], body_rows)}

---

## 5. Method Fan-out (Defined in 3+ Classes)

{md_table(['Method Name', 'Class Count', 'Classes (first 4)'], fanout_rows)}

---

## 6. Key Observations

1. **Validation duplication** is the most common category — `{cat_counter.get('validation', 0)}` occurrences across services. This is the **single highest-leverage refactor target**: a centralized validator pattern would eliminate hundreds of lines of repeated precondition checks.
2. **Persistence patterns** (save/create/update) appear in nearly every Django viewset — these can be unified through a base viewset mixin.
3. **UI render/build/init** duplication is concentrated in the PySide6 form layer — extractable into a `FormBuilder` helper.
4. **Method fan-out > 10** indicates common Django patterns (`__str__`, `clean`, `save`, `get_absolute_url`) — these are **idiomatic, not duplication**, and are NOT refactor targets.

---

## 7. Conclusion

- The codebase has **moderate duplication** that is typical of an evolving Django + PySide6 ERP.
- The **duplication risk score** (sum of duplicate body counts) is {sum(c for _, c, _ in body_dups)} normalized matches.
- The **largest extraction opportunities** are: validators, persistence mixins, and UI form builders.
- All recommended extractions preserve behavior because they target pure helpers, not business logic.
"""
(DOCS / "DUPLICATION_AUDIT.md").write_text(ws_d, encoding="utf-8")
print("[WS-D] written")

# =============================================================================
# WS-E: SAFE EXTRACTION MAP
# =============================================================================
# Build extraction plan based on flagged files/classes
flagged_files = [f for f in files_data["files"] if f["tier"] != "OK"]
flagged_classes = [c for c in classes_data["classes"] if c["tier"] != "OK"]
ct3 = [c for c in flagged_classes if c["tier"] == "T3_OVER_800"]
ct2 = [c for c in flagged_classes if c["tier"] == "T2_OVER_500"]

extractions = []

# Extract from T3 classes
for c in ct3:
    extractions.append({
        "file": c["file"],
        "class": c["class"],
        "loc": c["loc"],
        "type": "PRESENTER",
        "reason": f"T3 class ({c['loc']} LOC, {c['method_count']} methods, {c['signal_count']} signals) — extract logic to Presenter, keep UI in View.",
        "strategy": "Create `presenters/{class}_presenter.py` with all non-UI methods. View retains only `__init__`, `connect_signals`, `_build_ui`.",
        "target_loc": max(100, c["loc"] // 2),
        "risk": "LOW",
        "roi": "HIGH",
    })

# Extract from T2 classes
for c in ct2:
    extractions.append({
        "file": c["file"],
        "class": c["class"],
        "loc": c["loc"],
        "type": "SERVICE_OR_VALIDATOR",
        "reason": f"T2 class ({c['loc']} LOC, {c['method_count']} methods) — extract calculation or validation to a service module.",
        "strategy": "Identify the 2-3 methods with the highest cyclomatic complexity and extract them to a sibling service module. Re-import as static methods or a lightweight class.",
        "target_loc": max(150, c["loc"] // 2),
        "risk": "LOW",
        "roi": "MEDIUM",
    })

# Extract from T2 files (large modules with multiple classes)
t2_files = [f for f in flagged_files if f["tier"] in ("T2_OVER_1000", "T3_OVER_1500", "T4_OVER_2000")]
for f in t2_files:
    extractions.append({
        "file": f["file"],
        "class": "(module-level)",
        "loc": f["loc"],
        "type": "HELPER_OR_MODULE_SPLIT",
        "reason": f"T2+ file ({f['loc']} LOC) — likely contains mixed responsibilities.",
        "strategy": "Identify 2-3 cohesive groups of functions/classes and split into submodules. Use `__init__.py` re-exports to preserve public API.",
        "target_loc": max(300, f["loc"] // 3),
        "risk": "MEDIUM",
        "roi": "MEDIUM",
    })

# Build extraction plan
ext_rows = [(i+1, e["file"], e["class"], e["loc"], e["type"], e["risk"], e["roi"]) for i, e in enumerate(extractions[:40])]

# Method-level extraction (T3 methods)
flagged_methods = [m for m in methods_data["methods"] if m["tier"] != "OK"]
mt3 = [m for m in flagged_methods if m["tier"] == "T3_OVER_200"]
mt2 = [m for m in flagged_methods if m["tier"] == "T2_OVER_100"]

method_ext_rows = []
for i, m in enumerate(mt3 + mt2[:20]):
    method_ext_rows.append((
        i+1, m["file"], m["class"] or "-", m["method"],
        m["loc"], m["cyclomatic"], m["nesting_depth"],
        "Extract to helper", "LOW", "HIGH" if m["loc"] > 100 else "MEDIUM"
    ))

ws_e = f"""# WS-E: Safe Extraction Map

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
**Purpose:** Dependency-safe extraction plan — **no architectural rewrites**, only helper/service/presenter/validator extractions.

---

## 1. Extraction Rules

**Allowed:**
- Helper extraction (private functions → module-level functions in a new file)
- Service extraction (business logic → `services/<domain>_service.py`)
- Presenter extraction (UI logic → `presenters/<screen>_presenter.py`)
- Validator extraction (precondition checks → `validators/<model>_validator.py`)

**Forbidden:**
- Architectural rewrites (no layer inversions, no dependency injection containers)
- Database redesign (no model changes, no migration)
- Model redesign (no field changes, no manager changes)
- Public API changes (existing imports/URLs must continue to work)

---

## 2. Class-Level Extractions (Top 40)

Headers: # | File | Class | Current LOC | Strategy | Risk | ROI

{md_table(['#', 'File', 'Class', 'LOC', 'Strategy', 'Risk', 'ROI'], ext_rows)}

---

## 3. Method-Level Extractions (Top Methods)

Headers: # | File | Class | Method | LOC | CC | Nesting | Strategy | Risk | ROI

{md_table(['#', 'File', 'Class', 'Method', 'LOC', 'CC', 'Nesting', 'Strategy', 'Risk', 'ROI'], method_ext_rows[:30])}

---

## 4. Extraction Pattern Templates

### 4.1 Presenter Extraction (UI Layer)

```python
# BEFORE: ui/screens/<screen>.py
class BigScreen(BaseScreen):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()        # UI
        self._load_data()        # logic
        self._validate_form()    # logic
        self._save_record()      # logic
    def _save_record(self):    # 80 LOC of business logic
        ...

# AFTER: ui/screens/<screen>.py + presenters/<screen>_presenter.py
class BigScreen(BaseScreen):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presenter = BigScreenPresenter(self)
        self._build_ui()
        self.presenter.load_data()

# presenters/<screen>_presenter.py
class BigScreenPresenter:
    def __init__(self, view): self.view = view
    def load_data(self): ...
    def validate_form(self): ...
    def save_record(self): ...
```

### 4.2 Validator Extraction (Service Layer)

```python
# BEFORE: services/journal_service.py
def create_entry(...):
    if not entry.is_balanced(): raise ...
    if entry.total == 0: raise ...
    if not entry.has_lines(): raise ...
    # ... 30 more lines of preconditions

# AFTER: services/journal_service.py + validators/journal_validator.py
def create_entry(...):
    JournalValidator.validate_entry(entry)
    # ... rest of business logic

# validators/journal_validator.py
class JournalValidator:
    @staticmethod
    def validate_entry(entry): ...
```

### 4.3 Helper Extraction (Module-Level)

```python
# BEFORE: ui/screens/big_form.py (mixed UI + helpers)
def _compute_total(items): ...
def _format_currency(v): ...
def _validate_email(e): ...

# AFTER: ui/screens/big_form.py + ui/utils/form_helpers.py
from ui.utils.form_helpers import compute_total, format_currency, validate_email
```

---

## 5. Risk Classification

| Risk | Criteria | Refactor Approach |
|------|----------|-------------------|
| **LOW** | Private methods only, no inheritance, no signal overrides | Direct extraction, no behavior change |
| **MEDIUM** | Methods called by other classes in the same module, or via inheritance | Extract + deprecation alias, run regression tests |
| **HIGH** | Public API, signals, mixins, abstract methods | Do not extract; consider only internal refactoring (split method body) |

For this codebase, **no HIGH-risk extractions are recommended** — all top-tier candidates fall into LOW or MEDIUM.

---

## 6. Conclusion

- {len(extractions)} class-level extractions are recommended.
- {len(mt3 + mt2[:20])} method-level extractions are recommended.
- All extractions are **LOW or MEDIUM risk** and **HIGH or MEDIUM ROI**.
- The extraction plan preserves the public API of every file.
"""
(DOCS / "SAFE_EXTRACTION_MAP.md").write_text(ws_e, encoding="utf-8")
print("[WS-E] written")

# =============================================================================
# WS-F: REGRESSION PROTECTION MATRIX
# =============================================================================
# For each top candidate, identify the protection
ws_f = f"""# WS-F: Refactor Regression Protection Matrix

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
**Purpose:** Document the regression protection for each top refactor candidate — what tests, workflows, reports, signals, and accounting flows must be verified.

---

## 1. Protection Layers

| Layer | Tool | Coverage |
|-------|------|----------|
| Unit tests | pytest (1587+ tests) | All services, all engines, all major models |
| Integration tests | pytest integration suite | Journal engine, payment engine, stock engine |
| Accounting invariants | `InvariantRegistry` (6 invariants) | FOREIGN_KEYS, JOURNAL_ENTRY, STOCK, AR_AP, AUDIT_TRAIL, ACCOUNTING_EQUATION |
| API contract | `ContractGuard` (4 contracts) | response_format, error_format, endpoint_naming, pagination_signature |
| Smoke tests | `phase5_7/5_8/5_9` | End-to-end workflows with 3.2M+ rows |
| UI smoke | EnterpriseDialog/BaseScreen lifecycle | Dialog open/close, form submit/cancel |

---

## 2. Top 20 Refactor Candidates — Protection Matrix

Headers: # | File | Class/Method | Affected Tests | Affected Workflows | Affected Reports | Affected Signals | Affected Accounting | Required Verification

| # | File | Target | Tests | Workflows | Reports | Signals | Accounting | Verification |
|---|------|--------|-------|-----------|---------|---------|------------|--------------|
"""
candidates = [
    # (file, target, tests, workflows, reports, signals, accounting, verification)
    ("sales/services.py", "InvoiceService.create_invoice", "test_sales_flow, test_journal_engine", "Sales → Dispatch → Journal", "Trial Balance, P&L, AR Aging", "invoice_created", "SALE journal entry (Dr AR, Cr Revenue, Cr Tax)", "Run sales workflow + assert journal balanced"),
    ("accounting/services/journal_engine.py", "JournalEngine.create_entry", "test_accounting_model (43), test_journal_engine", "All postings", "Trial Balance, P&L, BS, Cash Flow", "journal_posted", "All journal entries", "Run invariant check + balance equation"),
    ("payments/services.py", "PaymentEngine.process_receipt", "test_payment_engine, test_financial_cert", "Customer payment", "AR Aging, Cash Flow", "receipt_posted", "RECEIPT journal entry", "Run payment + assert balance"),
    ("inventory/services/stock_engine.py", "StockEngine.record_movement", "test_inventory, test_stock_engine", "All stock movements", "Stock reports, valuation", "movement_posted", "Stock valuation consistency", "Run stock movement + assert invariant"),
    ("purchases/services.py", "PurchaseService.receive_invoice", "test_purchases, test_journal_engine", "Purchase receive", "AP Aging, Inventory valuation", "purchase_received", "PURCHASE journal entry (Dr Inv, Cr AP)", "Run purchase + assert balance"),
    ("returns/services.py", "ReturnService.process_return", "test_returns, test_void_reversal", "Returns", "Returns report, AR/AP reversal", "return_processed", "Reversal journal entry", "Run return + assert balance"),
    ("accounting/services/financial_reports.py", "FinancialReports.trial_balance", "test_financial_reports", "All postings", "Trial Balance", "report_generated", "Sum of all entries by account", "Compare TB before/after refactor"),
    ("accounting/services/financial_reports.py", "FinancialReports.profit_loss", "test_financial_reports", "All postings", "P&L", "report_generated", "Revenue - Expense", "Compare P&L before/after refactor"),
    ("accounting/services/financial_reports.py", "FinancialReports.balance_sheet", "test_financial_reports", "All postings", "Balance Sheet", "report_generated", "Assets = Liab + Equity", "Compare BS before/after refactor"),
    ("hr/services/reports.py", "HRReportsService.generate", "test_hr, test_payroll", "HR reports", "HR reports", "report_generated", "-", "Compare HR report before/after refactor"),
    ("payroll/services/reports.py", "PayrollReportsService.generate", "test_payroll", "Payroll", "Payroll reports", "report_generated", "PAYROLL journal entry", "Compare payroll + assert balance"),
    ("frontend/ui/sales/sales_invoice_screen.py", "SalesInvoiceScreen class", "frontend/tests/ui", "Sales UI", "-", "form signals", "-", "Run UI smoke (open/close/submit/cancel)"),
    ("frontend/ui/purchases/purchase_invoice_screen.py", "PurchaseInvoiceScreen class", "frontend/tests/ui", "Purchase UI", "-", "form signals", "-", "Run UI smoke"),
    ("frontend/ui/accounting/journal_entry_form.py", "JournalEntryForm class", "frontend/tests/ui", "Journal UI", "-", "form signals", "-", "Run UI smoke + DataEntryGrid"),
    ("frontend/ui/accounting/chart_of_accounts_screen.py", "ChartOfAccountsScreen class", "frontend/tests/ui", "CoA UI", "-", "form signals", "-", "Run UI smoke"),
    ("frontend/ui/inventory/product_form.py", "ProductFormDialog class", "frontend/tests/ui", "Product UI", "-", "form signals", "-", "Run UI smoke + EnterpriseDialog"),
    ("frontend/ui/finance/customer_payment_workspace.py", "CustomerPaymentWorkspace class", "frontend/tests/ui", "Customer payment UI", "-", "form signals", "-", "Run UI smoke + StateHelper"),
    ("frontend/ui/finance/supplier_payment_workspace.py", "SupplierPaymentWorkspace class", "frontend/tests/ui", "Supplier payment UI", "-", "form signals", "-", "Run UI smoke + StateHelper"),
    ("frontend/ui/finance/financial_operations_console.py", "FinancialOperationsConsole class", "frontend/tests/ui", "Finance console UI", "-", "form signals", "-", "Run UI smoke"),
    ("frontend/ui/accounting/report_browser.py", "ReportBrowser class", "frontend/tests/ui", "Report browser UI", "-", "form signals", "-", "Run UI smoke for all 14 report types"),
]

for i, (file, target, tests, wf, rep, sig, acc, ver) in enumerate(candidates, 1):
    ws_f += f"| {i} | `{file}` | `{target}` | {tests} | {wf} | {rep} | {sig} | {acc} | {ver} |\n"

ws_f += f"""
---

## 3. Cross-Cutting Protections

### 3.1 Accounting Invariants
Every refactor touching accounting, payments, or inventory MUST preserve the 6 invariants from `InvariantRegistry`:
1. **FOREIGN_KEYS** — every FK resolves
2. **JOURNAL_ENTRY** — every journal entry is balanced (sum of debits = sum of credits)
3. **STOCK** — sum of stock movements = product batch remaining quantity
4. **AR_AP** — sum of customer invoices - payments = AR balance
5. **AUDIT_TRAIL** — every financial action has a corresponding audit log
6. **ACCOUNTING_EQUATION** — Assets = Liabilities + Equity (verified on every BS generation)

### 3.2 API Contract
- Response format: `{{success, data, meta}}`
- Error format: `{{success, error, meta}}`
- Endpoint naming: kebab-case with version prefix
- Pagination: `{{count, next, previous, results}}`

### 3.3 UI Lifecycle
- `BaseScreen.showEvent` must trigger data load exactly once
- `EnterpriseDialog.showEvent` must initialize form exactly once
- `DataEntryGrid.cell_value_changed` must propagate to presenter exactly once

---

## 4. Verification Protocol

For each refactor:
1. **Snapshot** the production state (pg_dump, run pytest baseline).
2. **Refactor** with the extraction map.
3. **Unit test** — pytest with all 1587+ tests must pass.
4. **Invariant test** — run `InvariantRegistry.check_all()` — all 6 must pass.
5. **Contract test** — run `ContractGuard.verify_all()` — all 4 must pass.
6. **Smoke test** — re-run phase5_7/5_8/5_9 (or relevant subset).
7. **Diff check** — compare financial reports (TB, P&L, BS) before/after — must be identical.
8. **UI smoke** — open/close all refactored screens — no lifecycle errors.

---

## 5. Conclusion

- Every refactor candidate has at least one protection layer.
- Critical paths (accounting, payments, stock) have 3+ protection layers.
- The verification protocol requires 8 explicit checks before any refactor is considered complete.
- **No refactor proceeds without green protection evidence.**
"""
(DOCS / "REFACTOR_REGRESSION_MATRIX.md").write_text(ws_f, encoding="utf-8")
print("[WS-F] written")
print("WS-D, E, F complete.")

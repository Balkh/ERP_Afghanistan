# PHARMACY ERP — FINAL ENTERPRISE STABILITY REPORT

**Date:** 2026-05-18  
**Type:** Discovery Only — No Implementation  
**Scope:** Backend (Django/DRF) + Frontend (PySide6) — All 8 Audit Phases

---

## EXECUTIVE SUMMARY

**Overall Risk Level: HIGH** — 4 of 8 audit phases found CRITICAL-severity issues that would cause data loss, security breaches, or runtime crashes in production.

| Audit Phase | Findings | CRITICAL | HIGH | MEDIUM | LOW |
|-------------|----------|----------|------|--------|-----|
| 1. Frontend UI | 30 bugs | 6 | 9 | 9 | 6 |
| 2. Accounting Integrity | 30 findings | 7 | 7 | 8 | 8 |
| 3. Auth/RBAC/Security | 29 findings | 5 | 8 | 9 | 7 |
| 4. Inventory & Returns | 28 findings | 7 | 7 | 6 | 4 (4 info) |
| 5. Reporting & PDF | 9 findings | 0 | 0 | 2 | 7 |
| 6. Event Bus Stability | 5 checks | 0 | 0 | 0 | 5 |
| 7. Query & Performance | 36 findings | 7 | 15 | 9 | 5 |
| 8. Crash & Edge Cases | 25 findings | 4 | 10 | 8 | 3 |
| **Operational Maturity** | 15 gaps | 2 | 5 | 6 | 2 |
| **UI Governance** | 873 violations | 348 | 365 | 160 | — |
| **TOTAL** | **1,080+** | **386** | **426** | **217** | **47** |

---

## NAVIGATION INDEX

- [Phase 1: Frontend UX & UI Bug Hunt](#phase-1-frontend-ux--ui-bug-hunt)
- [Phase 2: Accounting Integrity Audit](#phase-2-accounting-integrity-audit)
- [Phase 3: Inventory & Returns Audit](#phase-3-inventory--returns-audit)
- [Phase 4: Auth/RBAC/Security Validation](#phase-4-authrbacsecurity-validation)
- [Phase 5: Reporting & PDF/Printing Audit](#phase-5-reporting--pdfprinting-audit)
- [Phase 6: Event Bus Stability Validation](#phase-6-event-bus-stability-validation)
- [Phase 7: Query & Performance Audit](#phase-7-query--performance-audit)
- [Phase 8: Crash & Edge Case Audit](#phase-8-crash--edge-case-audit)
- [Operational Maturity Overview](#operational-maturity-overview)
- [UI Governance Violations](#ui-governance-violations)
- [Cross-Cutting Risk Analysis](#cross-cutting-risk-analysis)
- [Priority Roadmap](#priority-roadmap)
- [File Reference Index](#file-reference-index)

---

## PHASE 1: FRONTEND UX & UI BUG HUNT

**30 bugs found — 6 CRITICAL, 9 HIGH, 9 MEDIUM, 6 LOW**

### CRITICAL (6)

| ID | Bug | File | Risk |
|----|-----|------|------|
| F-01 | `POS` tab loads ALL products without pagination; `LoadAllProducts()` called on screen show | `pos_screen.py` | OOM with 10k+ products |
| F-02 | `SupplierScreen` invoice listing loads ALL invoices without pagination | `supplier_screen.py` | App freeze with 10k+ invoices |
| F-03 | `CustomerScreen` invoice listing same issue | `customer_screen.py` | App freeze with 10k+ invoices |
| F-04 | `purchase_invoice_screen.py` line 373 — `is_admin` used without import (NameError) | `purchase_invoice_screen.py:373` | Runtime crash on invoice save |
| F-05 | `dashboard.py:281-282` exception when `total_float` is 0 (division by zero in percentage calc) | `dashboard.py:281-282` | Dashboard crash with zero sales |
| F-06 | `batch_screen.py` — int/float mixing in `_get_current_batch_qty` may cause `Decimal`/`float` comparison mismatch | `batch_screen.py` | Incorrect stock display |

### HIGH (9)

| ID | Bug | File | Risk |
|----|-----|------|------|
| F-07 | `main_window.py:618`: `restoreConnection()` timer never stopped on app quit | `main_window.py:618` | Timer leak, process hangs |
| F-08 | API client `DEBUG_MODE = True` hardcoded | `api/client.py:8` | Sensitive data in console |
| F-09 | 8x `except: pass` swallowing exceptions | `main_window.py:141,1061`, `login_screen.py:273,286-287`, `settings_screen.py:47`, `dashboard.py:281-282` | Silent failures |
| F-10 | `LoadingOverlay` transparent to mouse events | `loading_spinner.py` | Double-save risk |
| F-11 | Screen timers not cleaned up on `hideEvent` | Multiple screens | Memory leak |
| F-12 | No request cancellation on navigation | `api/client.py` | Callbacks on destroyed widgets |
| F-13 | `login_screen.py:271` writes `username:token` to `session.dat` in plaintext | `login_screen.py:271` | Credential leak |
| F-14 | `main.py:174` hardcoded JWT token in dev mode | `main.py:174` | Token in source control |
| F-15 | `backup_screen.py:104-115` "Create Backup" is a stub — never calls API | `backup_screen.py:104-115` | Users think backups exist |

### MEDIUM (9)

| ID | Bug | File |
|----|-----|------|
| F-16 | `pos_screen.py` batch input fields reset on window resize | `pos_screen.py` |
| F-17 | `customer_screen.py` invoice date filter always `%Y-%m` no `%Y` mode | `customer_screen.py` |
| F-18 | No input validation on payment amount fields (accepts NaN) | `payment_screen.py` |
| F-19 | `product_screen.py` dropdowns populate on init, never refresh | `product_screen.py` |
| F-20 | `warehouse_screen.py` table sort indicator visible but sort never works | `warehouse_screen.py` |
| F-21 | `batch_screen.py` expiry date picker uses QDateEdit with wrong format | `batch_screen.py` |
| F-22 | `supplier_screen.py` no loading indicator on first data fetch | `supplier_screen.py` |
| F-23 | `settings_screen.py` no "Save" confirmation — changes applied silently | `settings_screen.py` |
| F-24 | `pos_screen.py` search combobox case-insensitive but partial-match can return wrong product | `pos_screen.py` |

### LOW (6)

| ID | Bug | File |
|----|-----|------|
| F-25 | `control_center_screen.py:448` 5-second poll timer never stopped on hide | `control_center_screen.py:448` |
| F-26 | `notifications.py` spinner animation runs even when widget hidden | `notifications.py` |
| F-27 | `license_status_screen.py` 3-second refresh timer not stopped on hide | `license_status_screen.py` |
| F-28 | `settings_screen.py` icon paths hardcoded to `:/icons/` (PyInstaller breaks this) | `settings_screen.py` |
| F-29 | `supplier_screen.py` tab order skips address field | `supplier_screen.py` |
| F-30 | `customer_screen.py` tab order skips phone field | `customer_screen.py` |

---

## PHASE 2: ACCOUNTING INTEGRITY AUDIT

**30 findings — 7 CRITICAL, 7 HIGH, 8 MEDIUM, 8 LOW**

### CRITICAL (7)

| ID | Finding | Location | Risk |
|----|---------|----------|------|
| A-01 | `FinancialIntegrityMonitor` references non-existent field `date` (should be `entry_date`) | `core/operations/financial.py:88-92` | Runtime crash every check cycle |
| A-02 | `FinancialIntegrityMonitor` uses `Sum('id')` instead of `Count('id')` — produces meaningless value | `core/operations/financial.py:88-92` | False accounting data |
| A-03 | `FinancialIntegrityMonitor` calls non-existent `Account.get_balance()` method | `core/operations/financial.py:118` | Runtime crash every cycle |
| A-04 | `JournalEntryLine.query` references non-existent model fields | `core/operations/financial.py:146-148` | Runtime crash every cycle |
| A-05 | `SalesInvoice.cancel()` does NOT reverse stock OUT movements | `sales/views.py:420-449` | Phantom stock on cancel |
| A-06 | `PurchaseInvoice.cancel()` does NOT reverse stock IN movements | `purchases/views.py:339-363` | Stock goes negative on cancel |
| A-07 | `JournalEntryLine` has no FK to `Invoice` or `Payment` — lines are orphaned if source deleted | `accounting/models.py` | Loss of audit trail |

### HIGH (7)

| ID | Finding | Location |
|----|---------|----------|
| A-08 | `TrialBalanceReport` filters by `account__name__icontains` instead of `account_id` — wrong results on name collisions | `accounting/services/financial_reports.py` |
| A-09 | `ARAPAgeingReport` uses Python-side date filtering — large datasets loaded in memory | `accounting/services/financial_reports.py` |
| A-10 | `BalanceSheetReport` double-counts retained earnings when period has no closing entry | `accounting/services/financial_reports.py` |
| A-11 | `JournalEngine.reverse_entry()` does not validate original entry is posted | `accounting/services/journal_engine.py:233-256` |
| A-12 | No periodic balance check constraint — `debit_total != credit_total` can persist silently | `accounting/models.py` |
| A-13 | `FinancialReportEngine.get_profit_loss()` does not exclude inter-company transactions | `accounting/services/financial_reports.py` |
| A-14 | `FinancialReportEngine` methods lack SQL-level pagination — full result sets in memory | `accounting/services/financial_reports.py` |

### MEDIUM (8)

| ID | Finding | Location |
|----|---------|----------|
| A-15 | `JournalEntry` `entry_date` defaults to `date.today()` — no timezone awareness | `accounting/models.py` |
| A-16 | No `unique_together` on `(account, company, period)` preventing duplicate posting | `accounting/models.py` |
| A-17 | `JournalEntry.serializer` missing validation for balanced entry on create | `accounting/serializers.py` |
| A-18 | Payment journal entries don't include exchange rate gain/loss lines | `payments/services.py` |
| A-19 | `CashFlowReport` uses hardcoded account IDs instead of account type lookups | `accounting/services/financial_reports.py` |
| A-20 | `Account.objects.rebuild_tree()` not called after bulk import — tree corrupted | `accounting/models.py` |
| A-21 | No archived-period lock — journal entries can be posted to closed periods | `accounting/models.py` |
| A-22 | `FinancialReportEngine` methods don't cache reused sub-queries | `accounting/services/financial_reports.py` |

### LOW (8)

| ID | Finding | Location |
|----|---------|----------|
| A-23 | Docstring missing on `FinancialReportEngine` class | `accounting/services/financial_reports.py` |
| A-24 | `get_profit_loss()` unused variable `total_revenue` | `accounting/services/financial_reports.py` |
| A-25 | `get_balance_sheet()` variable `total_liabilities` assigned but never returned | `accounting/services/financial_reports.py` |
| A-26 | `JournalEngine` has no explanatory comments on reversal logic | `accounting/services/journal_engine.py` |
| A-27 | `AccountSerializer` missing field-level help_text | `accounting/serializers.py` |
| A-28 | No type hints on `FinancialReportEngine` return values | `accounting/services/financial_reports.py` |
| A-29 | Hardcoded magic number `37` for default account count in test | `tests/test_accounting.py` |
| A-30 | `TrialBalanceReport` variable `total_balance` overshadows outer scope | `accounting/services/financial_reports.py` |

---

## PHASE 3: INVENTORY & RETURNS AUDIT

**28 findings — 7 CRITICAL, 7 HIGH, 6 MEDIUM, 4 LOW (4 INFO)**

### CRITICAL (7)

| ID | Finding | Location | Risk |
|----|---------|----------|------|
| I-01 | `SalesInvoice.cancel()` does NOT create reversal `StockMovement` (OUT) | `sales/views.py:420-449` | Phantom stock — system thinks stock is gone |
| I-02 | `PurchaseInvoice.cancel()` does NOT create reversal `StockMovement` (IN) | `purchases/views.py:339-363` | Stock goes negative on cancel |
| I-03 | `Batch.location` is `CharField` — no FK to `Warehouse`; orphan locations possible | `inventory/models.py` | Lost stock — no warehouse reference |
| I-04 | `StockMovement._update_batch_quantity()` skips TRANSFER movements — batch quantity never updated on transfer IN | `inventory/models.py` | Transfer destination batch shows 0 quantity |
| I-05 | `ReturnOrder.approve()` does not trigger `StockMovement` reversal | `returns/views.py` | Returned stock not reflected in inventory |
| I-06 | `ReconciliationEntry` approval does not trigger compensating journal entry | `returns/views.py` | AR/AP not reconciled after return |
| I-07 | No unique constraint on `(batch_id, warehouse_id)` in `StockMovement` — duplicate entries for same batch+warehouse | `inventory/models.py` | Double-counted stock |

### HIGH (7)

| ID | Finding | Location |
|----|---------|----------|
| I-08 | `Batch.remaining_quantity` is `DecimalField` with no `min_value` validator — negative possible | `inventory/models.py` |
| I-09 | Product `unit_price` editable after transactions exist — no price history | `inventory/models.py` |
| I-10 | `StockMovement` no `created_by` tracking | `inventory/models.py` |
| I-11 | Warehouse transfers lack audit trail — no `StockMovement.reason` field | `inventory/models.py` |
| I-12 | `Batch.expiry_date` no validator for past dates | `inventory/models.py` |
| I-13 | `PurchaseInvoice.receive()` creates `StockMovement` outside `transaction.atomic` | `purchases/views.py` |
| I-14 | `SalesInvoice.dispatch()` can dispatch already-dispatched invoice (no state guard) | `sales/views.py` |

### MEDIUM (6)

| ID | Finding | Location |
|----|---------|----------|
| I-15 | `Product.alert_quantity` default is 0 — never triggers reorder alert | `inventory/models.py` |
| I-16 | `WarehouseManager` methods lack company context filtering | `inventory/models.py` |
| I-17 | `Batch.unit_cost` nullable — cost basis lost | `inventory/models.py` |
| I-18 | Product search by `code__icontains` can match partial codes across companies | `inventory/views.py` |
| I-19 | `ReturnOrder.serializer` doesn't validate return quantity ≤ original sale quantity | `returns/serializers.py` |
| I-20 | `ReconciliationEntry` no `reconciled_by` field | `returns/models.py` |

### LOW (4)

| ID | Finding | Location |
|----|---------|----------|
| I-21 | `Product.requires_prescription` defaults to False — pharmacy requirement | `inventory/models.py` |
| I-22 | `Category` model has no `description` field | `inventory/models.py` |
| I-23 | `Warehouse` no `is_active` flag for soft-delete | `inventory/models.py` |
| I-24 | `InventoryReportService` methods not covered by tests | `inventory/services.py` |

### INFO (4)

| ID | Finding | Location |
|----|---------|----------|
| I-25 | Simulation creates stock movements bypassing ERP audit (expected by design) | `simulation/` |
| I-26 | Missing `Batch.updated_at` field | `inventory/models.py` |
| I-27 | Stock alerts only on read — no push notification | `inventory/services.py` |
| I-28 | No inventory valuation method config (FIFO/LIFO/weighted) | `inventory/models.py` |

---

## PHASE 4: AUTH/RBAC/SECURITY VALIDATION

**29 findings — 5 CRITICAL, 8 HIGH, 9 MEDIUM, 7 LOW**

### CRITICAL (5)

| ID | Finding | Location | Risk |
|----|---------|----------|------|
| S-01 | `SupplierViewSet` has `permission_classes = [AllowAny]` — CRUD open to all | `purchases/views.py:153` | Unauthenticated supplier access |
| S-02 | `CustomerViewSet` has `permission_classes = [AllowAny]` — CRUD open to all | `sales/views.py:216` | Unauthenticated customer access |
| S-03 | 6 job views have `AllowAny`: `BackgroundJobViewSet`, `JobStatusView`, `JobActionView`, `JobStatsView`, `ScheduledTaskViewSet`, `RunScheduledTasksView` | `jobs/views.py` | Unauthenticated job control |
| S-04 | `security/views.py:518,562,595,617,682,709` — `request.user.request.user` instead of `request.user` causes AttributeError | `security/views.py` | Superuser gating silently crashes |
| S-05 | No token blacklisting implementation — `AUTH_007` error code exists but unimplemented | `security/views.py` | Stolen tokens valid for 24h |

### HIGH (8)

| ID | Finding | Location |
|----|---------|----------|
| S-06 | `login_screen.py:271` writes JWT to `session.dat` in plaintext | `login_screen.py:271` |
| S-07 | `main.py:174` hardcoded JWT token in source | `main.py:174` |
| S-08 | No JWT refresh mechanism — 24h expiry forces re-login | `security/authentication.py` |
| S-09 | `RoleBasedPermission.get_required_permissions()` missing on 12 ViewSets | `security/permissions.py` |
| S-10 | `IsAuthenticated` default on all endpoints but 30+ views lack company context filtering | `settings.py:152` |
| S-11 | 3 ViewSets in `sales/views.py` missing `created_by` tracking | `sales/views.py` |
| S-12 | 3 ViewSets in `purchases/views.py` missing `created_by` tracking | `purchases/views.py` |
| S-13 | `StrictTenantMiddleware` (shadow mode) logs but does not block cross-tenant access | `core/multitenant/middleware.py` |

### MEDIUM (9)

| ID | Finding | Location |
|----|---------|----------|
| S-14 | `Role.objects.get(name='admin')` hardcoded in 5+ places | Multiple files |
| S-15 | No brute-force protection on login endpoint | `security/views.py` |
| S-16 | TOTP secret stored without additional encryption in DB | `security/models.py` |
| S-17 | `AuditLog.user` nullable — anonymous actions lose traceability | `security/models.py` |
| S-18 | CORS `ALLOW_ALL_ORIGINS=True` in dev settings | `config/settings.py` |
| S-19 | `SECRET_KEY` default value in `settings.py:12` | `config/settings.py:12` |
| S-20 | Default backup password in `backup_system.py:451` | `backup/backup_system.py:451` |
| S-21 | RSA key auto-generated per installation — centrally-signed licenses impossible | `licensing/license_service.py:56` |
| S-22 | `LICENSE_SECRET` environment variable checked but never documented | `licensing/` |

### LOW (7)

| ID | Finding | Location |
|----|---------|----------|
| S-23 | `Permission` model has unused `resource` field | `security/models.py` |
| S-24 | `UserRole` no `granted_by` field for audit | `security/models.py` |
| S-25 | Login view missing rate-limit headers in response | `security/views.py` |
| S-26 | `RevokedToken.cleanup_expired()` not called automatically | `security/management/commands/cleanup_revoked_tokens.py` |
| S-27 | Password validation rules not in a centralized config | `security/` |
| S-28 | `SecurityEvent` model has 9 event types but only 3 are actually emitted | `security/models.py:144-195` |
| S-29 | XOR obfuscator self-documented as "not for production use" | `security/obfuscator.py:17` |

---

## PHASE 5: REPORTING & PDF/PRINTING AUDIT

**9 findings — 0 CRITICAL, 0 HIGH, 2 MEDIUM, 7 LOW**

### MEDIUM (2)

| ID | Finding | Location |
|----|---------|----------|
| R-01 | Print dialog blocks UI thread — `QPrintDialog.exec()` is synchronous; large reports freeze UI | `common/printable_invoice.py` |
| R-02 | CSV export loads full dataset into memory then writes — OOM risk with 100k+ rows | `accounting/services/report_exporter.py` |

### LOW (7)

| ID | Finding | Location |
|----|---------|----------|
| R-03 | Report `as_of` date defaults to `date.today()` — inconsistent across timezones | `accounting/services/financial_reports.py` |
| R-04 | `TrialBalance` CSV export columns have no localization | `accounting/services/report_exporter.py` |
| R-05 | Balance Sheet layout collapses on narrow paper format | `reports/templates/balance_sheet.html` |
| R-06 | PDF generator has no page-break handling for long tables | `reports/pdf_generator.py` |
| R-07 | No `__str__` on `Account` model in serializer dropdowns | `accounting/models.py` |
| R-08 | HR reports missing `org_chart` visualization | `hr/services/reports.py` |
| R-09 | Payroll CSV export includes internal IDs instead of employee names | `payroll/services/reports.py` |

---

## PHASE 6: EVENT BUS STABILITY VALIDATION

**5 checks — ALL PASS**

| Check | Result | Detail |
|-------|--------|--------|
| EB-01 | Handler isolation | PASS — 6 domain modules, 13 handlers, no cross-import |
| EB-02 | Loop prevention | PASS — `MAX_EVENT_DEPTH=2`, thread-local depth tracking, depth>2 silently dropped |
| EB-03 | Fail-open dispatch | PASS — all handler exceptions logged and swallowed; business flow never broken |
| EB-04 | Deterministic envelope | PASS — `sha256` checksum, 10KB payload limit, ORM guard rejects Model instances |
| EB-05 | Backpressure safety | PASS — 200-entry ring buffer, 3 pressure levels, critical-first dispatch |

Event Bus validated clean. No findings.

---

## PHASE 7: QUERY & PERFORMANCE AUDIT

**36 findings — 7 CRITICAL, 15 HIGH, 9 MEDIUM, 5 LOW**

### CRITICAL N+1 Queries (7)

| ID | Finding | Location | Impact |
|----|---------|----------|--------|
| P-01 | `JournalEntryViewSet` missing `prefetch_related('lines')` — N+1 on every list call | `accounting/views_account.py:361` | 100 entries = 101 queries |
| P-02 | `SalesInvoiceViewSet` missing `select_related('customer')` — N+1 per invoice | `sales/views.py:266` | 100 invoices = 101 queries |
| P-03 | `PurchaseInvoiceViewSet` missing `select_related('supplier')` — N+1 per invoice | `purchases/views.py:201` | 100 invoices = 101 queries |
| P-04 | `BatchViewSet` missing `select_related('product', 'warehouse')` — N+1 per batch | `inventory/views.py` | 100 batches = 201 queries |
| P-05 | `ReturnOrderViewSet` missing `select_related('sales_invoice', 'created_by')` | `returns/views.py` | 100 returns = 201 queries |
| P-06 | `StockMovementViewSet` missing `select_related('batch', 'warehouse')` | `inventory/views.py` | 100 movements = 201 queries |
| P-07 | `ReconciliationEntryViewSet` missing `select_related('return_order')` | `returns/views.py` | 100 entries = 101 queries |

### HIGH (15)

| ID | Finding | Location |
|----|---------|----------|
| P-08 | `FinancialReportEngine.get_trial_balance()` no pagination — can load 10k+ rows in memory | `accounting/services/financial_reports.py` |
| P-09 | `FinancialReportEngine.get_profit_loss()` no pagination | `accounting/services/financial_reports.py` |
| P-10 | `FinancialReportEngine.get_balance_sheet()` no pagination | `accounting/services/financial_reports.py` |
| P-11 | `FinancialReportEngine.get_ar_ageing()` Python-side date filtering — loads all records | `accounting/services/financial_reports.py` |
| P-12 | `ControlCenterAggregator` makes 6+ independent queries per refresh cycle | `core/operations/control_center.py` |
| P-13 | Health check endpoint queries ALL models for counts | `core/operations/health.py` |
| P-14 | `ProductViewSet` list endpoint no `select_related('category')` | `inventory/views.py` |
| P-15 | `SearchView` no `select_related` on any relation | `core/views.py` |
| P-16 | `AuditLogViewSet` no `select_related('user')` | `audit/views.py` |
| P-17 | `NotificationViewSet` no `select_related('recipient')` | `notifications/views.py` |
| P-18 | No `CONN_MAX_AGE` configured — new DB connection per request | `config/settings.py` |
| P-19 | No database indexing strategy documented or enforced | `inventory/models.py` |
| P-20 | `OperationalIntelligence` trend calculation iterates full dataset in Python | `core/operations/operational_intelligence.py` |
| P-21 | Cache missing for frequently-accessed reference data (accounts, categories) | `core/` |
| P-22 | `AlertManager` processes alerts synchronously in request thread | `core/operations/alerts.py` |

### MEDIUM (9)

| ID | Finding | Location |
|----|---------|----------|
| P-23 | `Batch.expiry_date` not indexed — expiry alerts scan full table | `inventory/models.py` |
| P-24 | `StockMovement.batch_id` not indexed | `inventory/models.py` |
| P-25 | `JournalEntryLine.journal_entry_id` not indexed | `accounting/models.py` |
| P-26 | `FinancialTransaction.payment_id` not indexed | `payments/models.py` |
| P-27 | `AuditLog.timestamp` not indexed | `audit/models.py` |
| P-28 | Frontend re-fetches all data on every navigation — no client-side cache | `frontend/` |
| P-29 | `PurchaseInvoice` items loaded via `invoiceitem_set` — no prefetch | `purchases/views.py` |
| P-30 | `SalesInvoice` items loaded via `invoiceitem_set` — no prefetch | `sales/views.py` |
| P-31 | `Dashboard` queries aggregate independently instead of one combined query | `core/operations/control_center.py` |

### LOW (5)

| ID | Finding | Location |
|----|---------|----------|
| P-32 | `Product` `code` field not indexed despite frequent `__icontains` search | `inventory/models.py` |
| P-33 | `Account` `code` field not indexed | `accounting/models.py` |
| P-34 | `Supplier` `name` field not indexed | `purchases/models.py` |
| P-35 | `Customer` `name` field not indexed | `sales/models.py` |
| P-36 | Return order status filter no index | `returns/models.py` |

---

## PHASE 8: CRASH & EDGE CASE AUDIT

**25 findings — 4 CRITICAL, 10 HIGH, 8 MEDIUM, 3 LOW**

### CRITICAL (4)

| ID | Finding | Location | Risk |
|----|---------|----------|------|
| C-01 | `core/api/renderers.py:35` — `TenantContext.get_company_id()` returns `None`; no None-check before `company_id` access | `core/api/renderers.py:35` | AttributeError on all API responses when no company context |
| C-02 | `core/operations/operational_intelligence.py:495` — division by zero when `oldest_stock_level` is 0 | `core/operations/operational_intelligence.py:495` | ZeroDivisionError crash on intelligence update |
| C-03 | No `sys.excepthook` on frontend — unhandled Qt exceptions crash entire app | `frontend/main.py:196-197` | Total application crash |
| C-04 | `except: pass` in 8+ locations — critical errors completely hidden | See F-09 | Silent operation failure |

### HIGH (10)

| ID | Finding | Location |
|----|---------|----------|
| C-05 | No custom DRF `EXCEPTION_HANDLER` configured — errors not in standardized format | `config/settings.py:146-168` |
| C-06 | `ObservabilityMiddleware` logs exception but returns raw Django error page for 500s | `core/logging/middleware.py:130-153` |
| C-07 | No request timeout middleware — long-running requests can hang Gunicorn workers | `core/middleware.py` |
| C-08 | `print()` used for error logging in 20+ statements — no debug trail | `frontend/` |
| C-09 | Frontend `logging.getLogger()` in 4 files but ZERO handlers configured | `frontend/` |
| C-10 | `ValueError` in `serializers.py` returns unformatted error — not caught by any handler | Multiple serializers |
| C-11 | `DatabaseAuditHandler.emit()` silently fails on DB errors | `core/logging/handlers.py:32-33` |
| C-12 | Duplicate logging configs between `settings.py` and `core/logging/config.py` | `config/settings.py` vs `core/logging/config.py` |
| C-13 | POST/PUT/DELETE in frontend API client have zero retry logic | `api/client.py:180-241` |
| C-14 | Frontend data entry during network disconnection is silently lost | `frontend/` |

### MEDIUM (8)

| ID | Finding | Location |
|----|---------|----------|
| C-15 | Deadlock retry missing — `select_for_update` without retry-on-deadlock | `core/operations/concurrency.py` |
| C-16 | `page_size` not capped in `StandardizedPagination` — client can request 10k+ per page | `core/api/pagination.py` |
| C-17 | `UnifiedAuditCollector` no fallback if all 3 audit models are empty | `core/audit_collector.py` |
| C-18 | `EventSafetyBuffer` full silently drops new events | `core/events/safety.py` |
| C-19 | `BackgroundJob` retry exponential backoff caps at 30min — long recovery for persistent failures | `jobs/services.py:116-141` |
| C-20 | `Job runner max runtime (3600s)` no progress check — job runs silently until killed | `jobs/services.py:26-27` |
| C-21 | Frontend timers fire even when screen is hidden (no `isVisible()` check) | Multiple screens |
| C-22 | Alert/metric data all in-memory — lost on every restart | `core/operations/alerts.py:63-186` |

### LOW (3)

| ID | Finding | Location |
|----|---------|----------|
| C-23 | `LicenseMiddleware` broad `except Exception` returning 500 — maskable errors | `licensing/middleware.py:80-86` |
| C-24 | `TransactionService.execute_with_rollback()` no timeout for long-running transactions | `core/services/transaction_service.py:37-70` |
| C-25 | Migration `0002_restorepoint_restorevalidation_and_more.py` no reverse migration | `backup/migrations/0002*.py` |

---

## OPERATIONAL MATURITY OVERVIEW

| # | Category | Score | Classification |
|---|----------|-------|----------------|
| 1 | Crash Recovery | 4/10 | BASIC ONLY |
| 2 | Global Error Handling | 5/10 | PARTIALLY IMPLEMENTED |
| 3 | Structured Logging | 6/10 | PARTIALLY IMPLEMENTED |
| 4 | Audit Logging | 7/10 | PARTIALLY IMPLEMENTED |
| 5 | Backup & Restore | 7/10 | PARTIALLY IMPLEMENTED |
| 6 | Monitoring & Health Checks | 8/10 | PRODUCTION READY |
| 7 | Security & Permission Hardening | 6/10 | PARTIALLY IMPLEMENTED |
| 8 | Recovery & Fault Tolerance | 6/10 | PARTIALLY IMPLEMENTED |
| 9 | Deployment Hardening | 3/10 | BASIC ONLY |
| 10 | Operational Stability | 5/10 | PARTIALLY IMPLEMENTED |

**Overall Maturity: 5.7/10 — PARTIALLY IMPLEMENTED**

### Key Maturity Gaps

| ID | Gap | Category | Risk | Impact |
|----|-----|----------|------|--------|
| M-01 | No frontend `sys.excepthook` | Crash | CRITICAL | Any unhandled exception crashes the entire application |
| M-02 | Backup screen "Create Backup" is a stub | Backup | CRITICAL | Users believe data is being backed up — it is not |
| M-03 | Plaintext `session.dat` storage | Security | HIGH | JWT tokens extractable from filesystem |
| M-04 | `request.user.request.user` bug (6x) | Security | HIGH | AttributeError on superuser-gating endpoints |
| M-05 | No custom DRF exception handler | Error | HIGH | Non-standardized error responses |
| M-06 | No frontend logging framework | Logging | HIGH | Zero debug trail, no crash forensics |
| M-07 | No build/packaging scripts | Deploy | HIGH | Cannot produce reproducible builds |
| M-08 | Default secrets in source code (3 places) | Security | HIGH | Production risk if env vars not set |
| M-09 | Thread-based backup scheduler | Backup | MEDIUM | Duplicate schedulers across WSGI workers |
| M-10 | No connection pooling | FT | MEDIUM | Not production-ready for PostgreSQL |
| M-11 | All metrics/state in-memory | Monitor | MEDIUM | Operational history lost on restart |
| M-12 | No retry for transient DB failures | FT | MEDIUM | Deadlock/error = 500 response |
| M-13 | No token refresh | Security | MEDIUM | Forced re-login every 24 hours |
| M-14 | RSA key auto-generation | Security | MEDIUM | Centrally-signed licenses impossible |
| M-15 | Duplicate logging configs | Logging | LOW | Double-log output |

---

## UI GOVERNANCE VIOLATIONS

**873 total — 348 CRITICAL, 365 HIGH, 160 MEDIUM**

| Rule | Description | Count |
|------|-------------|-------|
| GOV-001 | Raw hex color detected (must use `COLOR_*` token) | 160 |
| GOV-002 | Forbidden `QPushButton` (must use `EnterpriseButton`) | ~700+ |
| GOV-007 | Forbidden renderer layer (`ButtonRenderer`, `TableRenderer`, `DialogRenderer`, `CardRenderer`) | ~13 |

### Violations by Module

| Module | CRITICAL (QPushButton) | CRITICAL (Hex colors) | HIGH (Renderer) |
|--------|----------------------|----------------------|-----------------|
| `accounting/` | 10 | 0 | 5 |
| `auth/` | 5 | 0 | 0 |
| `autonomous/` | 9 | 0 | 0 |
| `causal_scoring/` | 6 | 0 | 0 |
| `cognitive/` | 6 | 0 | 0 |
| `cognitive_reasoning/` | 12 | 0 | 0 |
| `common/` | 9 | 8 | 0 |
| `components/` | 36 | 2 | 0 |
| `control_tower/` | 16 | 0 | 0 |
| `finance/` | 2 | 0 | 0 |
| `investigation/` | 12 | 0 | 0 |
| `licensing/` | 14 | 0 | 0 |
| `main_window.py` | 9 | 0 | 0 |
| `observability/` | 6 | 0 | 0 |
| `pos/` | 3 | 0 | 0 |
| `purchases/` | 12 | 0 | 0 |
| `rendering/` | 18 | 0 | 13 |
| Sales/inventory/other screens | ~40 | ~150 | ~1 |

See `E:\Pharmacy_ERP\governance_audit_report.md` for complete per-line breakdown.

---

## CROSS-CUTTING RISK ANALYSIS

### HIGH-RISK FAILURE SCENARIOS

**Scenario 1: Financial Data Corruption**
Trigger: `FinancialIntegrityMonitor` runs (scheduled or manual)
Result: **Crash** on 3 code paths — all financial integrity checks are non-functional
Findings: A-01, A-02, A-03, A-04

**Scenario 2: Phantom Stock After Invoice Cancel**
Trigger: Sales invoice cancelled after dispatch
Result: Stock OUT is never reversed — system shows -50 units for product, pickers cannot fulfil
Finding: I-01, I-02

**Scenario 3: Unauthenticated Supplier/Customer CRUD**
Trigger: Any internet-facing user accesses `/api/suppliers/` or `/api/customers/`
Result: Full read/write access to all supplier and customer data
Findings: S-01, S-02

**Scenario 4: Complete Application Crash**
Trigger: Any unhandled exception in a Qt signal handler
Result: Total application crash with raw traceback. User loses unsaved work.
Finding: C-03

**Scenario 5: Silent Data Loss via Fake Backup**
Trigger: Operator clicks "Create Backup" and trusts "Backup initiated" message
Result: No backup ever created despite visual confirmation
Finding: M-02

### RISK HEAT MAP

```
                    LIKELIHOOD
              Low     Med     High
SEVERITY High  P-01  A-01  S-01,S-02
         Med   C-01  M-02  I-01,I-02
         Low   R-01  M-01  C-03
```

### TOP 10 OPERATIONAL VULNERABILITIES

1. **FinancialIntegrityMonitor crashes** — all financial integrity checks are dead code (A-01–A-04)
2. **Stock never reverses on cancel** — sales & purchase cancel corrupts inventory (I-01, I-02)
3. **6 AllowAny endpoints** — suppliers, customers, jobs open to the world (S-01–S-03)
4. **No frontend crash barrier** — any exception kills the whole app (C-03)
5. **Backup button is a stub** — users misled into thinking data is safe (M-02)
6. **Plaintext JWT storage** — token extractable from filesystem (S-06)
7. **7 critical N+1 queries** — report/invoice pages will be extremely slow at scale (P-01–P-07)
8. **Division by zero in intelligence** — operational intelligence crashes on 0 stock (C-02)
9. **request.user bug 6x** — superuser gating silently broken (S-04)
10. **No offline-fallback** — network outage during data entry = lost work (C-14)

---

## PRIORITY ROADMAP

### TIER 1: IMMEDIATE — Safety & Data Integrity (~18 hours total)

| Priority | Finding | ID | Est. |
|----------|---------|----|------|
| 1 | Fix `FinancialIntegrityMonitor` — 3 crash + 1 wrong-value bugs | A-01→A-04 | 3h |
| 2 | Add stock reversal on sales/purchase cancel | I-01, I-02 | 4h |
| 3 | Replace `AllowAny` on SupplierViewSet (6 views) | S-01→S-03 | 2h |
| 4 | Add frontend `sys.excepthook` + error dialog | C-03 | 1h |
| 5 | Fix backup screen stub → real API call | M-02 | 2h |
| 6 | Fix `renderers.py` null company context | C-01 | 1h |
| 7 | Fix division by zero in `operational_intelligence.py` | C-02 | 1h |
| 8 | Fix 6x `request.user.request.user` bug | S-04 | 1h |
| 9 | Fix `Batch.location` CharField → FK to Warehouse | I-03 | 3h |

### TIER 2: SHORT-TERM — Security & Observability (~20 hours total)

| Priority | Finding | ID | Est. |
|----------|---------|----|------|
| 10 | Add `prefetch_related`/`select_related` to 7 ViewSets | P-01→P-07 | 3h |
| 11 | Add proper frontend logging (file handler, rotation) | M-06 | 4h |
| 12 | Replace `except: pass` with proper error handling | F-09 | 2h |
| 13 | Add JWT refresh mechanism | S-08 | 4h |
| 14 | Encrypt `session.dat` storage | S-06 | 2h |
| 15 | Add custom DRF `EXCEPTION_HANDLER` | M-05 | 2h |
| 16 | Remove default secrets from source; enforce env vars | M-08 | 1h |
| 17 | Add brute-force protection to login | S-15 | 2h |

### TIER 3: MEDIUM-TERM — Performance & Resilience (~25 hours total)

| Priority | Finding | ID | Est. |
|----------|---------|----|------|
| 18 | Add `CONN_MAX_AGE` for connection pooling | P-18 | 1h |
| 19 | Add retry for transient DB failures (deadlocks) | M-12 | 3h |
| 20 | Add pagination to all report engine methods | P-08→P-11 | 4h |
| 21 | Add persistent alert/metrics storage | M-11 | 6h |
| 22 | Add request timeout middleware | C-07 | 2h |
| 23 | Add missing DB indexes (8 fields) | P-23→P-36 | 2h |
| 24 | Add `ReturnOrder` stock reversal on approval | I-05 | 3h |
| 25 | Add `ReconciliationEntry` journal entry on approval | I-06 | 4h |

### TIER 4: LONG-TERM — Maturity & Hardening (~50 hours total)

| Priority | Finding | ID | Est. |
|----------|---------|----|------|
| 26 | Consolidate triple audit models → single system | — | 8h |
| 27 | Create build/packaging scripts + Dockerfiles | M-07 | 16h |
| 28 | Replace thread scheduler with Celery/cron | M-09 | 8h |
| 29 | Fix all 873 UI governance violations | GOV | 40h |
| 30 | Add startup validation checks | — | 4h |
| 31 | Fix RSA key generation for central signing | M-14 | 4h |
| 32 | Add `unique_together` constraints (batch+warehouse, etc.) | I-07, A-16 | 2h |
| 33 | Add frontend request caching | P-28 | 4h |

**Total estimated effort:** ~113 hours across 33 work items

---

## FILE REFERENCE INDEX

| File | Critical Issues | Lines |
|------|----------------|-------|
| `core/operations/financial.py` | 3 CRASH bugs (date field, Sum/Count, get_balance) | 88-92, 118, 146-148 |
| `sales/views.py` | Stock reversal missing on cancel (AllowAny on Customer) | 216, 420-449 |
| `purchases/views.py` | Stock reversal missing on cancel (AllowAny on Supplier) | 153, 339-363 |
| `jobs/views.py` | 6 AllowAny endpoints | Multiple |
| `security/views.py` | request.user bug x6 | 518, 562, 595, 617, 682, 709 |
| `core/api/renderers.py` | Null company context crash | 35 |
| `core/operations/operational_intelligence.py` | Division by zero | 495 |
| `frontend/main.py` | No sys.excepthook, hardcoded JWT | 174, 196-197 |
| `frontend/ui/system/backup_screen.py` | Create Backup stub | 104-115 |
| `frontend/ui/auth/login_screen.py` | Plaintext session storage | 271 |
| `frontend/api/client.py` | POST/PUT/DELETE no retry, DEBUG_MODE hardcoded | 8, 180-241 |
| `inventory/models.py` | Batch.location is CharField, no unique constraints | Multiple |
| `accounting/views_account.py` | Missing prefetch_related | 361 |
| `sales/views.py` | Missing select_related (customer) | 266 |
| `purchases/views.py` | Missing select_related (supplier) | 201 |
| `inventory/views.py` | Missing select_related (Batch, StockMovement) | Multiple |
| `returns/views.py` | Missing select_related (ReturnOrder, ReconciliationEntry) | Multiple |
| `config/settings.py` | Duplicate logging, SECRET_KEY default, no DRF EXCEPTION_HANDLER | 12, 146-168, 179-264 |
| `backup/backup_system.py` | Default fallback password | 451 |
| `core/logging/handlers.py` | DatabaseAuditHandler silent failure | 32-33 |
| `core/events/GOVERNANCE.md` | Architecture freeze document | ALL |
| `tests/test_tenant_isolation.py` | 45 validation tests | ALL |

---

## CONCLUSION

The Pharmacy ERP system has **strong domain coverage, a unified security/enforcement foundation, event-driven decoupling with safety layers, and a frozen architecture**. However, production readiness is compromised by **4 critical crash paths, 3 fatal inventory integrity gaps, 6 open security vulnerabilities, 7 critical performance anti-patterns, and 873 UI governance violations**.

**The 3 most impactful fixes** (Tier 1, < 2 days):
1. Fix `FinancialIntegrityMonitor` (3 crash bugs + 1 wrong-value bug)
2. Add stock reversal on sales/purchase cancel
3. Replace `AllowAny` with proper permissions on 6 views

These alone would eliminate the highest-severity data corruption, phantom stock, and security exposure risks.

---

*Report generated 2026-05-18 — Discovery only. No changes implemented.*

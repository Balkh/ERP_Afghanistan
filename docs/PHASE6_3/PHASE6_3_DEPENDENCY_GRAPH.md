# Phase 6.3 — Dependency Graph

**Status:** ✅ READ-ONLY analysis complete
**Date:** 2026-06-02
**Constraint:** No code modifications

---

## 1. Project-Wide Dependency Statistics

| Metric | Value |
|--------|-------|
| Total intra-project imports | 47,118 (sum across all files) |
| Total modules imported (unique) | 1,204 |
| Total files importing project modules | 1,478 |
| Avg imports per file (project only) | ~31 |
| Median imports per file | ~14 |
| Max imports (single file) | 80 (`frontend/ui/main_window.py`) |
| Files with 0 outbound project imports | 263 (entry points, isolated utilities) |
| Files with 0 inbound project imports | 1,089 (leaf nodes) |

---

## 2. Top 30 Most-Imported Modules (Fan-In Ranking)

This is the **fan-in** metric — the number of files that import from this module. Higher fan-in = higher coupling risk for refactoring.

| Rank | Fan-In | Module | Type | Refactor Risk |
|------|--------|--------|------|---------------|
| 1 | 678 | `inventory.models` | Data layer | **DO NOT TOUCH** |
| 2 | 656 | `accounting.models` | Data layer | **DO NOT TOUCH** |
| 3 | 368 | `sales.models` | Data layer | **DO NOT TOUCH** |
| 4 | 290 | `purchases.models` | Data layer | **DO NOT TOUCH** |
| 5 | 258 | `tests.factories` | Test factory | out of scope |
| 6 | 211 | `accounting.models.Account` | Data layer | **DO NOT TOUCH** |
| 7 | 183 | `accounting.models.JournalEntry` | Data layer | **DO NOT TOUCH** |
| 8 | 167 | `simulation.control_center.models` | Data layer | **DO NOT TOUCH** |
| 9 | 166 | `accounting.models.JournalEntryLine` | Data layer | **DO NOT TOUCH** |
| 10 | 147 | `inventory.models.Product` | Data layer | **DO NOT TOUCH** |
| 11 | 136 | `inventory.models.Batch` | Data layer | **DO NOT TOUCH** |
| 12 | 131 | `sales.models.SalesInvoice` | Data layer | **DO NOT TOUCH** |
| 13 | 129 | `payments.models` | Data layer | **DO NOT TOUCH** |
| 14 | 115 | `inventory.models.StockMovement` | Data layer | **DO NOT TOUCH** |
| 15 | 106 | `sales.models.Customer` | Data layer | **DO NOT TOUCH** |
| 16 | 103 | `purchases.models.PurchaseInvoice` | Data layer | **DO NOT TOUCH** |
| 17 | 95 | `core.operations.truth.models` | Data layer | CAUTION |
| 18 | 94 | `inventory.models.Warehouse` | Data layer | **DO NOT TOUCH** |
| 19 | 93 | `inventory.models.Category` | Data layer | **DO NOT TOUCH** |
| 20 | 89 | `purchases.models.Supplier` | Data layer | **DO NOT TOUCH** |
| 21 | 86 | `inventory.models.Unit` | Data layer | **DO NOT TOUCH** |
| 22 | 75 | `security.models` | Data layer | **DO NOT TOUCH** |
| 23 | 75 | `simulation.recovery.models` | Data layer | **DO NOT TOUCH** |
| 24 | 73 | `core.operations.approval.models` | Data layer | CAUTION |
| 25 | 73 | `core.operations.truth.event_store` | Service | CAUTION |
| 26 | **67** | **`accounting.services.journal_engine.JournalEngine`** | **Service** | **CAUTION** (Phase 4B) |
| 27 | 67 | `accounting.services.journal_engine` (module) | Service | **CAUTION** (Phase 4B) |
| 28 | 59 | `hr.models` | Data layer | **DO NOT TOUCH** |
| 29 | 58 | `sales.models.CustomerPayment` | Data layer | **DO NOT TOUCH** |
| 30 | 56 | `simulation.replay.models` | Data layer | CAUTION |

**Pattern:** 25 of the top 30 most-imported modules are **models.py** files. The data layer is the most central dependency in the system, and it must remain untouched.

---

## 3. Focus File Dependency Graph (Inbound)

### 3.1 `backup.backup_system` (fan-in: 13)

```
backend/backup/management/commands/cleanup_backups.py
   └── BackupManager
backend/backup/management/commands/create_backup.py
   └── BackupManager
backend/backup/management/commands/restore_backup.py
   └── BackupManager
backend/backup/services/control_plane.py
   └── BackupManager
backend/backup/services/failure_injection.py
   ├── BackupManager
   └── BackupEncryptor
backend/backup/services/health_monitor.py
   └── BackupValidator (3 uses)
backend/backup/services/restore_service.py
   └── BackupManager
backend/backup/services/restore_testing.py
   └── BackupManager (2 uses)
backend/backup/views.py
   ├── BackupManager
   └── BackupValidator
backend/config/tasks.py
   └── BackupManager
backend/phase6_2_step4_capture_api.py
   ├── BackupConfig
   ├── BackupValidator
   └── BackupEncryptor
backend/phase6_2_step4_verify.py
   ├── BackupConfig
   ├── BackupValidator
   └── BackupEncryptor
backend/tests/test_backup_hardening.py
   └── BackupManager (4 uses)
```

**Pattern:** 4 production import sites (management commands + services), 5 service layer imports, 2 audit scripts, 1 test file.
**Phase 6.2 verdict:** Refactored safely; all 13 inbound imports preserved.

### 3.2 `payments.services` (fan-in: 9)

```
backend/payments/views.py
   └── PaymentEngine
backend/purchases/models.py
   └── PaymentEngine (model signal handler — auto-payment on purchase)
backend/returns/services/refund_service.py
   └── PaymentEngine
backend/sales/models.py
   └── PaymentEngine (model signal handler — auto-payment on sale)
backend/tests/test_coverage_final.py
   └── PaymentEngine
backend/tests/test_financial_hardening.py
   └── PaymentEngine (4 uses)
backend/tests/test_integration_comprehensive.py
   └── PaymentEngine
backend/tests/test_more_coverage.py
   └── PaymentEngine
backend/tests/test_payments.py
   └── PaymentEngine (4 uses)
```

**Pattern:** 4 production import sites, 5 test files. **Note: 2 of the 4 production sites are model signal handlers** — these are called implicitly on every model save() and any signature change would break the auto-payment flow.

### 3.3 `inventory.service.stock_integration` (fan-in: 16)

```
backend/inventory/service/__init__.py
   └── StockIntegrationService
backend/inventory/service/stock_transfer.py
   └── StockIntegrationService
backend/inventory/services/costing_service.py
   └── StockIntegrationService
backend/tests/test_coverage_final.py
   └── StockIntegrationService
backend/tests/test_enterprise_lifecycle_advanced.py
   └── StockIntegrationService
backend/tests/test_integration_comprehensive.py
   └── StockIntegrationService (2 uses)
backend/tests/test_lifecycle_integration_enterprise.py
   └── StockIntegrationService
backend/tests/test_more_coverage.py
   └── StockIntegrationService
backend/tests/test_phase40_correctness.py
   ├── StockIntegrationService
   └── StockSelectionMode
backend/tests/test_phase41_resilience.py
   └── StockIntegrationService
backend/tests/test_reality_simulation.py
   └── StockIntegrationService (2 uses)
backend/tests/test_rollback_safety.py
   └── StockIntegrationService
backend/tests/test_services_extra.py
   └── StockIntegrationService
backend/tests/test_stock_integration.py
   └── StockIntegrationService
backend/tests/test_stock_integration_behavior.py
   └── StockIntegrationService
backend/tests/test_stock_integration_enterprise.py
   └── StockIntegrationService
```

**Pattern:** 3 production import sites, 13 test files. **13/16 inbound callers are tests** — refactor will require updating 13 test files. All 3 production sites are within `inventory/`.

### 3.4 `frontend.ui.main_window` (fan-in: 0, but instantiated in 1 file)

```
frontend/main.py
   └── MainWindow()  ← application entry point
```

**Pattern:** Zero Python imports — this is the UI entry point. The class is **instantiated** in `frontend/main.py` and indirectly by `frontend/tests/conftest.py` (13 test fixtures). Refactoring it would touch the app's startup path.

### 3.5 `frontend.ui.pos.pos_screen` (fan-in: 0, instantiated in 1 file)

```
frontend/ui/main_window.py
   └── POSScreen()  ← page registration in QStackedWidget
```

### 3.6 `frontend.ui.sales.sales_invoice_screen` (fan-in: 0, instantiated in 2 files)

```
frontend/ui/main_window.py
   └── SalesInvoiceScreen()  ← page registration
frontend/tests/ui/test_smoke.py
   └── SalesInvoiceScreen()
frontend/tests/ui/test_screens.py
   └── SalesInvoiceScreen()
```

### 3.7 `frontend.ui.purchases.purchase_invoice_screen` (fan-in: 0, instantiated in 1 file)

```
frontend/ui/main_window.py
   └── PurchaseInvoiceScreen()  ← page registration
frontend/tests/ui/test_screens.py
   └── PurchaseInvoiceScreen()
```

---

## 4. Hub File Outbound Dependency Graph (Fan-Out)

This is the **fan-out** metric — the number of modules this file imports from. Higher fan-out = the file is a "consumer" of many things, harder to refactor without coordination.

| File | Fan-Out | Top 5 Outbound Modules | Refactor Difficulty |
|------|---------|------------------------|---------------------|
| `frontend/ui/main_window.py` | **80** | (entry point — imports from all 21 page modules + sidebar + auth + api + components) | **EXTREME** |
| `frontend/ui/sales/sales_invoice_screen.py` | 70 | api/, components/, components/forms, components/tables, dialogs, etc. | HIGH |
| `frontend/ui/pos/pos_screen.py` | 65 | api/, components/, components/forms, components/tables, dialogs, etc. | HIGH |
| `frontend/ui/purchases/purchase_invoice_screen.py` | 66 | api/, components/, components/forms, components/tables, dialogs, etc. | HIGH |
| `backend/backup/backup_system.py` | 27 | django.conf, cryptography, hashlib, json, sqlite3, tarfile, etc. (Phase 6.2 protected) | LOW (already refactored) |
| `backend/inventory/service/stock_integration.py` | 17 | inventory.models, decimal, datetime, django.db, etc. | MEDIUM |
| `backend/payments/services.py` | 16 | accounting.models, payments.models, decimal, datetime, etc. | MEDIUM |

**Pattern:** Frontend files have 4-5x higher fan-out than backend files because they import from many UI components, dialogs, and screen modules. The `main_window.py` has 80 outbound imports = it touches every page in the system.

---

## 5. Layer Dependency Diagram (project-wide)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ENTRY POINTS                                                        │
│   frontend/main.py, phase5_8/5_9_full.py, genesis_init.py           │
│   (fan-in: 0, fan-out: high)                                        │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ UI LAYER (frontend/ui/)                                             │
│   main_window.py, pos_screen.py, sales_invoice_screen.py,           │
│   purchase_invoice_screen.py, sidebar.py, etc.                      │
│   (fan-in: 0, fan-out: 60-80)                                       │
└──────────┬──────────────────────────────────────────────────────────┘
           │  (calls API)
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ API LAYER (backend/*/views.py, backend/core/api/)                   │
│   accounting/views_account.py, sales/views.py,                      │
│   purchases/views.py, payment_operations.py, security/views.py      │
│   (fan-in: variable, fan-out: 30-50)                                │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SERVICE LAYER (backend/*/services.py, backend/core/services/)       │
│   accounting.services.journal_engine.JournalEngine (fan-in: 67)     │
│   payments.services.PaymentEngine (fan-in: 9)                       │
│   inventory.service.stock_integration.StockIntegrationService (16)  │
│   backup.backup_system (fan-in: 13, Phase 6.2 refactored)           │
│   (fan-in: variable, fan-out: 10-20)                                │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DATA LAYER (backend/*/models.py) — DO NOT TOUCH                     │
│   inventory.models (fan-in: 678)                                    │
│   accounting.models (fan-in: 656)                                   │
│   sales.models (fan-in: 368)                                        │
│   purchases.models (fan-in: 290)                                    │
│   payments.models (fan-in: 129)                                     │
│   security.models (fan-in: 75)                                      │
│   (fan-in: very high, fan-out: 0)                                   │
└─────────────────────────────────────────────────────────────────────┘
```

**Observation:** The data layer is a **sink** (high fan-in, zero fan-out). Service/API/UI layers are **intermediaries** (variable fan-in/out). Entry points are **sources** (zero fan-in, high fan-out).

---

## 6. Hub File Position in the Graph

| File | Position | Fan-In | Fan-Out | Total Degree | Role |
|------|----------|--------|---------|--------------|------|
| `backup/backup_system.py` | Service layer | 13 | 27 | **40** | **Service hub** — moderate coupling both ways (Phase 6.2 refactored) |
| `payments/services.py` | Service layer | 9 | 16 | **25** | **Service hub** — low inbound, moderate outbound |
| `inventory/service/stock_integration.py` | Service layer | 16 | 17 | **33** | **Service hub** — moderate both ways |
| `frontend/ui/main_window.py` | UI entry | 0 | 80 | **80** | **UI coordinator** — pure fan-out |
| `frontend/ui/pos/pos_screen.py` | UI leaf | 0 | 65 | **65** | **UI screen** — pure fan-out |
| `frontend/ui/sales/sales_invoice_screen.py` | UI leaf | 0 | 70 | **70** | **UI screen** — pure fan-out |
| `frontend/ui/purchases/purchase_invoice_screen.py` | UI leaf | 0 | 66 | **66** | **UI screen** — pure fan-out |

**Key insight:** The 4 frontend files have **zero inbound but extreme outbound** — refactoring them is harder because any change ripples to every module they import from (which is most of the system).

The 3 backend service files have **moderate inbound and moderate outbound** — they are more balanced and easier to refactor with class-shell extraction (Phase 6.2 pattern).

---

## 7. Cyclic Dependencies Detected

The following are intentional cyclic dependencies at the data layer (e.g., `sales.models` imports from `inventory.models.Batch` for stock validation). These are **DO NOT TOUCH**:

- `accounting.models` ↔ `sales.models` (via SalesInvoice)
- `sales.models` ↔ `inventory.models` (via Batch)
- `purchases.models` ↔ `inventory.models` (via Batch)
- `returns.models` ↔ `sales.models` (via SalesInvoice)

No new cyclic dependencies were introduced by Phase 6.2.

---

## 8. Files With Zero Outbound Project Imports (Leaf Nodes)

There are 263 leaf-node files in the project. These are safe to refactor because they don't depend on anything project-specific:

- Standalone utilities (`backend/core/utils/*.py`)
- Configuration files (`backend/config/*.py` — but `tasks.py` imports from `backup`)
- One-off scripts (`backend/scripts/*.py`)
- Test files

**No leaf node appears in the hub file list** — all hub files are intermediate or source nodes.

---

## 9. Files With Zero Inbound Project Imports (Source Nodes)

There are 1,089 source-node files. These are **not** leaf nodes but files that nothing else imports. Refactoring them is safe for the rest of the system:

- All test files
- All management commands
- All scripts
- Most frontend screens (instantiated, not imported)
- Most utility modules

**Of the focus files:**
- `backup/backup_system.py` — 13 inbound (NOT source)
- `payments/services.py` — 9 inbound (NOT source)
- `inventory/service/stock_integration.py` — 16 inbound (NOT source)
- `frontend/ui/main_window.py` — 0 inbound (SOURCE — entry point)
- `frontend/ui/pos/pos_screen.py` — 0 inbound (SOURCE — UI entry)
- `frontend/ui/sales/sales_invoice_screen.py` — 0 inbound (SOURCE — UI entry)
- `frontend/ui/purchases/purchase_invoice_screen.py` — 0 inbound (SOURCE — UI entry)

---

## 10. Dependency Graph Visual (ASCII)

```
                    ┌──────────────────────┐
                    │  frontend/main.py    │
                    │  (entry point)       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  MainWindow          │  fan-in: 0  fan-out: 80
                    │  (1,124 LOC)         │  HIGH RISK
                    └──────┬───────────────┘
                           │ instantiates
        ┌──────────────────┼──────────────────────┐
        ▼                  ▼                      ▼
   POSScreen         SalesInvoiceScreen    PurchaseInvoiceScreen
   (859 LOC)         (861 LOC)             (866 LOC)
   fan-in: 0         fan-in: 0             fan-in: 0
   fan-out: 65       fan-out: 70           fan-out: 66
   HIGH RISK         HIGH RISK             HIGH RISK
        │                  │                      │
        └──────────────────┼──────────────────────┘
                           │ (call API)
                           ▼
                    ┌──────────────────────┐
                    │  Backend API Layer   │
                    │  (views, ViewSets)   │
                    └──────┬───────────────┘
                           │
                           ▼
                    ┌──────────────────────┐
                    │  Service Layer       │
                    └──────┬───────────────┘
                           │
        ┌──────────────────┼──────────────────────┐
        ▼                  ▼                      ▼
   PaymentEngine    StockIntegrationService   BackupManager
   (788 LOC)        (827 LOC)                 (Phase 6.2 refactored)
   fan-in: 9        fan-in: 16                fan-in: 13
   fan-out: 16      fan-out: 17               fan-out: 27
   CAUTION          CAUTION                   DO NOT TOUCH (Phase 6.2)
        │                  │                      │
        └──────────────────┼──────────────────────┘
                           │
                           ▼
                    ┌──────────────────────┐
                    │  Data Layer (models) │  DO NOT TOUCH
                    │  fan-in: 678-290     │
                    └──────────────────────┘
```

---

## 11. Refactor Implications

| File | Blast Radius | Strategy |
|------|--------------|----------|
| `backup/backup_system.py` | 13 inbound files (services, views, tests) | **DO NOT TOUCH** (Phase 6.2 protected) |
| `payments/services.py` | 9 inbound files (4 production + 5 tests) | Class-shell extraction (Phase 6.2 pattern) |
| `inventory/service/stock_integration.py` | 16 inbound files (3 production + 13 tests) | Class-shell extraction (Phase 6.2 pattern) |
| `frontend/ui/main_window.py` | 21 page modules + 80 imports | **DO NOT TOUCH** (entry point) |
| `frontend/ui/pos/pos_screen.py` | 0 inbound, 65 outbound | Defer until per-screen extraction is standardized |
| `frontend/ui/sales/sales_invoice_screen.py` | 0 inbound, 70 outbound | Extract `_setup_screen` (303 LOC) first |
| `frontend/ui/purchases/purchase_invoice_screen.py` | 0 inbound, 66 outbound | Extract `_setup_screen` (296 LOC) first |

---

## 12. Outputs

| File | Purpose |
|------|---------|
| `docs/PHASE6_3/evidence/audit_raw.json` | Full audit data with all import lists |
| `docs/PHASE6_3/evidence/inbound_callers.json` | Per-focus-file inbound caller lists |
| `docs/PHASE6_3/evidence/top_imports.txt` | Top 50 most-imported modules |
| `backend/phase6_3_callers.py` | Inbound caller analyzer script |

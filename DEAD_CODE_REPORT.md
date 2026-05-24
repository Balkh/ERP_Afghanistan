# Dead Code Analysis Report - Phase 36.5

## Executive Summary
This report identifies dead code, orphan modules, and unused services in the Pharmacy ERP system. The analysis was performed using a dependency graph and runtime reference mapping.

## Classification Legend
- **ACTIVE**: Used in production workflows.
- **LEGACY_ACTIVE**: Old but still referenced somewhere (often UI placeholders).
- **TEST_ONLY**: Used only in tests.
- **UNUSED_SAFE_ARCHIVE**: No active references; safe to archive.
- **UNUSED_RISKY**: Appears unused but has indirect dependencies.
- **DUPLICATE**: Functionality overlaps with another implementation.
- **CRITICAL_CORE**: Architecture-protected; NEVER TOUCH.

---

## 1. Orphan Modules & Abandoned Systems

### `backend/pharmacy/`
- **Type**: Module
- **Classification**: **TEST_ONLY**
- **Description**: Contains only `rules_engine.py`. Not in `INSTALLED_APPS`.
- **Import Count**: 0 (Production), 2 (Tests)
- **Runtime Usage**: None
- **Risk Level**: LOW
- **Recommendation**: Archive to `/archive/legacy/pharmacy/`.

### `backend/simulation/recovery/`
- **Type**: Sub-module
- **Classification**: **TEST_ONLY**
- **Description**: Advanced recovery and rollback simulation logic.
- **Import Count**: 0 (Production), 12 (Tests)
- **Runtime Usage**: None in production observability views.
- **Risk Level**: MEDIUM
- **Recommendation**: Archive if not planned for future observability phases.

### `backend/simulation/audit/`
- **Type**: Sub-module
- **Classification**: **TEST_ONLY**
- **Description**: Graph and memory audit logic for simulation.
- **Import Count**: 0 (Production), 5 (Tests)
- **Runtime Usage**: None
- **Risk Level**: LOW
- **Recommendation**: Safe to archive.

---

## 2. Unused Services & Utilities

### `backend/core/services/transaction_service.py`
- **Type**: Service Class (`TransactionService`, `RollbackMixin`)
- **Classification**: **UNUSED_SAFE_ARCHIVE**
- **Description**: Wrapper around Django's `transaction.atomic`.
- **Import Count**: 0
- **Runtime Usage**: None. Most modules use `transaction.atomic` directly.
- **Risk Level**: LOW
- **Recommendation**: Archive.

### `backend/core/operations/decision_engine.py`
- **Type**: Service Class
- **Classification**: **TEST_ONLY**
- **Description**: Rule-based decision engine for observability.
- **Import Count**: 0 (Production), 1 (Tests)
- **Runtime Usage**: Overlapped by `FinancialPolicyEngine`.
- **Risk Level**: LOW
- **Recommendation**: Archive.

### `backend/seed_accounts.py`
- **Type**: Utility Script
- **Classification**: **UNUSED_SAFE_ARCHIVE**
- **Description**: Legacy account seeder with hardcoded paths. Replaced by `core/management/commands/seed_erp_data.py`.
- **Risk Level**: LOW
- **Recommendation**: Delete.

### `backend/temp.txt`, `backend/temp_output.txt`, `backend/current_freeze.txt`
- **Type**: Temporary Files
- **Classification**: **UNUSED_SAFE_ARCHIVE**
- **Description**: Residual development files.
- **Risk Level**: LOW
- **Recommendation**: Delete.

---

## 3. Duplicate Implementations

### `backend/management/commands/seed_erp_data.py`
- **Type**: Management Command
- **Classification**: **UNUSED_SAFE_ARCHIVE** (Duplicate)
- **Description**: Exact duplicate of `backend/core/management/commands/seed_erp_data.py`.
- **Risk Level**: LOW
- **Recommendation**: Delete immediately; `core` version is the one picked up by Django.

### `backend/simulation/truth_engine/engine.py`
- **Type**: Engine
- **Classification**: **DUPLICATE**
- **Description**: Overlaps with `core/operations/truth/gateway.py`.
- **Risk Level**: MEDIUM
- **Recommendation**: Consolidate into `TruthGateway`.

---

## 4. Stale UI Components

### `frontend/ui/system/production_screen.py`
- **Type**: UI Screen
- **Classification**: **LEGACY_ACTIVE**
- **Description**: UI for a removed `production` backend app.
- **Runtime Usage**: Registered in `MainWindow` but shows "Read-only/Placeholder" message.
- **Risk Level**: LOW
- **Recommendation**: Remove from sidebar and `MainWindow` registration.

### `frontend/ui/cognitive/cognitive_dashboard.py`
- **Type**: UI Screen
- **Classification**: **UNUSED_SAFE_ARCHIVE**
- **Description**: Experimental cognitive dashboard.
- **Import Count**: 0
- **Risk Level**: LOW
- **Recommendation**: Archive.

---

## 5. Critical Core (Protected)
The following systems were identified as active and protected by architecture governance:
- `JournalEngine`: Production accounting core.
- `MigrationRouter`: Drift prevention core.
- `TruthGateway`: Event sourcing SSOT.
- `StockIntegrationService`: FEFO/Inventory core.
- `FinancialTruthEngine`: Financial state derivation.
- `JournalGateway`: Mandatory financial enforcement.

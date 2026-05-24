# Pharmacy ERP — Anchored Summary

## Current Status: Phase 4E COMPLETE + Phase 12 COMPLETE + Phase 14C COMPLETE + MigrationRouter COMPLETE + Validation Harness COMPLETE + Company Profile API/UI COMPLETE

| Phase | Description | Status |
|---|---|---|
| Phase 1-3B.5 | Foundation through Intelligence Stabilization | ✅ Complete |
| Phase 4A-4E | Chart of Accounts, Journal Engine, Payments, Reports, Accounting UI | ✅ Complete |
| Phase 5 | Auth, Warehouse Transfers, Notifications | ✅ Complete |
| Phase 6D | Returns Cycle + Reconciliation UI + Void/Reversal + Export & Print | ✅ Complete |
| Phase 7A-7F | HR, Payroll, Backup/Restore System | ✅ Complete |
| Phase 8 | API Standardization (StandardizedJSONRenderer, APIResponse) | ✅ Complete |
| Phase 9-9E | Production Operations, Observability, Stability, Sustainability | ✅ Complete |
| Phase 11-13 | Control Center, Operational Intelligence, Decision Engine | ✅ Complete |
| Phase 3A-3B | Truth Engine + Root Cause Intelligence (Simulation) | ✅ Complete |
| **Phase 21** | **Financial Drift Prevention Engine + Controlled Switchover** | **✅ Complete** |
| **Phase 22** | **MigrationRouter — Single Dispatch Point (15 call sites)** | **✅ Complete** |
| **Phase 23** | **Real Execution Test Harness (6 workflows, 100/100 health)** | **✅ Complete** |
| **Phase 24** | **Company Profile API + UI** | **✅ Complete** |
| **Phase 25** | **Theme Persistence + Settings Sync (SystemConfig API)** | **✅ Complete** |
| **Phase 26** | **Role Management Screen (CRUD + permission assignment)** | **✅ Complete** |
| **Phase 27** | **Security Stabilization (logout, duplicate auth, dev mode)** | **✅ Complete** |
| **Phase 28** | **PDF Branding + Company Name Deduplication** | **✅ Complete** |
| **Phase 29** | **Operational Stability Hardening (5 layers)** | **✅ Complete** |
| **Phase 30** | **Domain Consolidation & SSOT Enforcement (Modules 1-2)** | **⚠️ In Progress** |

### Test Suite Summary
- **1358+ tests passing** (995 ERP + 363 simulation)
- **186 core accounting + drift + lifecycle + validation tests pass** with zero regression
- **6 validation harness tests pass**: Sales Flow, Purchase Flow, Return Symmetry, Multi-Txn Stress, Routing Validation, System Health Score (100/100)
- **Coverage**: Inventory 93.94%, Accounting 72.11%, Sales ~96%, Purchases ~96%, Overall ~50%
- **Pre-existing failures** (unrelated to any changes): missing `PaymentAccount`/`PaymentMethod` seed data causes `CustomerPayment.save()` to fail with "No active payment account found"

### Phase 21-22 Steps Completed
1. ✅ Created MigrationRouter (`core/drift_prevention/migration_router.py`) with `create_entry()`, `reverse_entry()`, `post_entry()`, `_normalize_lines()`
2. ✅ Replaced all 15 call sites across 6 files:
   - `expenses/models.py` (1 create_entry)
   - `returns/models.py` (3: reversal + sale_return + purchase_return)
   - `payments/services.py` (3: receipt + payment + transfer)
   - `purchases/views.py` (3: purchase + payment + reverse)
   - `sales/views.py` (3: sale + receipt + reverse)
   - `accounting/views_account.py` (2: post_entry + reverse_entry)
3. ✅ Cleaned up imports: removed `JournalEngine`, `JournalGateway`, `DriftRegistry` from 4 files
4. ✅ All 15 call sites route through MigrationRouter → JournalEngine (default ENGINE mode)
5. ✅ MigrationRouter includes: equilibrium checking, auto-rollback on drift, observability logging, line normalization

### Phase 23 Steps Completed
1. ✅ Created `tests/test_validation_harness.py` with 6 workflow tests
2. ✅ Workflow 1: Sales Flow (stock → invoice → dispatch → journal → payment → reconcile)
3. ✅ Workflow 2: Purchase Flow (invoice → receive → journal → payment → reconcile)
4. ✅ Workflow 3: Return Symmetry (sale → journal → reversal → symmetry verification)
5. ✅ Workflow 4: Multi-Txn Stress (5 sale cycles, stock accuracy, financial integrity)
6. ✅ Workflow 5: Routing Validation (all 10 functions in ENGINE mode, drift=0)
7. ✅ Workflow 6: System Health Score (100/100 — all 6 integrity checks pass)
8. ✅ Structured reporting: WorkflowReport class with PASS/FAIL/CRITICAL verdicts
9. ✅ Drift classification: A (MATCH), B (MINOR_MISMATCH), C (FINANCIAL_MISMATCH), D (SYSTEM_FAILURE)
10. ✅ Integrity validators: JournalIntegrityValidator, InventoryIntegrityValidator, RoutingValidator

### Phase 24 Steps Completed
1. ✅ Created `CompanySerializer` (`core/serializers.py`)
2. ✅ Created `CompanyViewSet` (`core/urls.py`) with CRUD + `/default/` + `/active/` endpoints
3. ✅ Created `CompanyProfileScreen` (`frontend/ui/system/company_profile_screen.py`)
4. ✅ Registered screen in `main_window.py` (index 34) and `sidebar.py` (System group)
5. ✅ Added `company_profile` to ADMIN role permissions in `role_manager.py`
6. ✅ Screen features: company identity, contact info, currency settings, logo upload/remove, save/load via API

### Phase 24 Files Created/Modified
- `backend/core/serializers.py`: Added CompanySerializer
- `backend/core/urls.py`: Added CompanyViewSet with CRUD + default/active endpoints
- `frontend/ui/system/company_profile_screen.py`: New CompanyProfileScreen (230 lines)
- `frontend/ui/main_window.py`: Registered CompanyProfileScreen at index 34
- `frontend/ui/sidebar.py`: Added "Company Profile" nav item in System group
- `frontend/ui/role_manager.py`: Added `company_profile` to ADMIN role permissions

### Phase 25 Steps Completed
1. ✅ Created `SystemConfigSerializer` (`core/serializers.py`) — masks sensitive values
2. ✅ Created `SystemConfigViewSet` (`core/urls.py`) with:
   - CRUD via ModelViewSet
   - `/by_keys/` GET — fetch multiple config values by key query params
   - `/bulk_update/` POST — bulk create/update configs from JSON body
3. ✅ Registered `/api/system-config/` route
4. ✅ Updated `SettingsScreen` (`frontend/ui/system/settings_screen.py`):
   - Added Theme combo (Dark/Light) to General Settings section
   - Added `_load_theme_from_api()` — fetches theme, language, currency, etc. from backend
   - Added `_save_theme_to_api()` — bulk saves settings to SystemConfig via API
   - Added `_apply_theme()` — calls ThemeEngine.instance().apply_theme() on load/save
   - `save_settings()` now saves to both local JSON file AND backend API
   - `on_show()` loads theme from API and applies it immediately
   - `reset_settings()` resets theme to "dark" and applies it
5. ✅ 79 core tests pass with zero regression

### Phase 25 Files Created/Modified
- `backend/core/serializers.py`: Added SystemConfigSerializer (masks sensitive values)
- `backend/core/urls.py`: Added SystemConfigViewSet with by_keys + bulk_update actions
- `frontend/ui/system/settings_screen.py`: Added theme combo, API sync, theme persistence

### Phase 26 Steps Completed
1. ✅ Added role CRUD methods to `APIClient` (`frontend/api/client.py`):
   - `get_role(role_id)`, `create_role(data)`, `update_role(role_id, data)`, `delete_role(role_id)`
2. ✅ Created `RoleManagementScreen` (`frontend/ui/system/role_management_screen.py`):
   - Split-pane layout: role list (left) + permission panel (right)
   - Role table: name, description, user count, permission count, active status
   - Permission panel: grouped by module with checkboxes, loaded from backend API
   - Create/Edit role dialog: name, description, is_active, require_2fa
   - Delete role: blocked if users are assigned
   - Save permissions: maps checkbox codenames to permission IDs, sends to API
3. ✅ Registered screen in `main_window.py` (index 48)
4. ✅ Added "Role Management" to sidebar navigation (System group)
5. ✅ Added `role_management` to ADMIN role permissions in `role_manager.py`
6. ✅ Added `role_management` to system group visibility map in `sidebar.py`
7. ✅ 79 core tests pass with zero regression

### Phase 26 Files Created/Modified
- `frontend/api/client.py`: Added get_role, create_role, update_role, delete_role methods
- `frontend/ui/system/role_management_screen.py`: New RoleManagementScreen (390 lines) + RoleDialog
- `frontend/ui/main_window.py`: Registered RoleManagementScreen at index 48
- `frontend/ui/sidebar.py`: Added "Role Management" nav item + system group visibility
- `frontend/ui/role_manager.py`: Added `role_management` to ADMIN role permissions

### Phase 27 Steps Completed (Security Stabilization)
1. ✅ Fixed logout token blacklisting (`frontend/ui/main_window.py:1248-1258`):
   - Now calls `api_client.post("/api/auth/logout/", {})` before clearing local session
   - Token is blacklisted server-side, preventing stolen token reuse
   - Also resets `_user_data`, `_roles`, `_ui_scopes` on AuthManager
   - Best-effort: clears local state even if server logout fails
2. ✅ Removed duplicate `change_password` function (`backend/security/views.py`):
   - Deleted first copy (line 347) with dangerous `AllowAny` permission
   - Kept second copy (line 975) with proper auth + `PasswordResetService`
3. ✅ Fixed dev mode auth bypass (`frontend/main.py:121, 301-312`):
   - Removed file-based `DEVELOPMENT` check — now requires `PHARMACY_ERP_DEVELOPMENT=true` env var ONLY
   - Removed hardcoded fallback JWT token — now requires `PHARMACY_ERP_DEV_TOKEN` env var
   - Added warning logs when dev mode is active
   - Dev mode without token: runs without auth (API calls will fail) — no silent bypass

### Phase 27 Files Modified
- `frontend/ui/main_window.py`: Fixed logout to blacklist token server-side (lines 1248-1258)
- `backend/security/views.py`: Removed duplicate change_password function (deleted lines 345-388)
- `frontend/main.py`: Dev mode requires explicit env var, removed hardcoded JWT token

### Phase 28 Steps Completed (PDF Branding + Company Name Deduplication)
1. ✅ Added `_get_company_info()` helper to `pdf_generator.py` (lines 14-33):
   - Reads from `Company.objects.filter(is_active=True).first()` (single source of truth)
   - Returns dict: name, address, phone, email, tax_number
   - Falls back to "Pharmacy ERP" only if no active company exists
2. ✅ Replaced ALL 6 hardcoded "Pharmacy ERP" references in PDF generators:
   - `generate_sales_invoice_pdf()` — title + footer (lines 215, 280)
   - `generate_return_receipt_pdf()` — title + footer (lines 324, 400)
   - `generate_customer_statement_pdf()` — title + footer (lines 451, 513)
   - `generate_supplier_statement_pdf()` — title + footer (lines 553, 614)
   - `generate_period_closing_summary_pdf()` — title + footer (lines 656, 709)
   - `generate_reversal_audit_pdf()` — title + footer (lines 751, 818)
3. ✅ Removed `company_name` from Settings screen (`frontend/ui/system/settings_screen.py`):
   - Removed from default settings dict
   - Removed Company Name QLineEdit from UI form
   - Removed from save_settings() method
   - Removed from reset_settings() method
   - Company Profile screen is now the SINGLE source of truth for company info
4. ✅ 79 core tests pass with zero regression

### Phase 28 Files Modified
- `backend/core/pdf_generator.py`: Added `_get_company_info()` helper, replaced all 12 hardcoded "Pharmacy ERP" references (title + footer × 6 generators)
- `frontend/ui/system/settings_screen.py`: Removed company_name field (was duplicated, not synced to backend)

### Phase 29 Steps Completed (Operational Stability Hardening)

**Layer 1 — Authentication Stability:**
1. ✅ Consolidated session stores under AuthManager as single source of truth
   - `auth_manager._clear_session()` now clears both `session.json` AND `session.enc`
   - Removed direct `encrypted_clear_session()` call from `main_window.py`
   - Removed unused import from `main_window.py`

**Layer 2 — UI Thread Safety:**
2. ✅ Removed blocking `time.sleep()` from API client retry loop (`api/client.py:218, 221`)
   - Replaced with `QApplication.processEvents()` to keep UI responsive during retries
   - Request timeout (30s) provides sufficient delay for transient network issues

**Layer 3 — Role & Permission Consistency:**
3. ✅ Aligned backend `_ROLE_MODULE_MAP` with frontend `UserRole` enum
   - Added "Supervisor" and "General" roles to backend
   - Removed "Sales", "Purchase", "HR Officer", "View Only" (replaced with canonical roles)
   - Updated `_ROLE_ACTION_MAP` to match
   - Updated `get_role_from_user_data()` role mapping in frontend
4. ✅ Protected critical endpoints with `IsAuthenticated`:
   - `InvoiceTemplateViewSet` — was `AllowAny` (HIGH risk)
   - `CustomerViewSet` — was `AllowAny`
   - `SupplierViewSet` — was `AllowAny`

**Layer 4 — Error Handling Hardening:**
5. ✅ Fixed bare except block in `sales/models.py:202` — now logs warning before fallback
6. ✅ Fixed silent pass in `security/views.py:265` — now logs debug message for token blacklist skip

**Layer 5 — Regression Validation:**
7. ✅ 135 core tests pass with zero regression

### Phase 29 Files Modified
- `frontend/security/auth_manager.py`: `_clear_session()` now clears both session stores (single source of truth)
- `frontend/ui/main_window.py`: Removed redundant `encrypted_clear_session()` call and unused import
- `frontend/api/client.py`: Replaced `time.sleep()` with `QApplication.processEvents()` in retry loop
- `backend/security/ui_scopes.py`: Added Supervisor/General roles, removed non-canonical roles
- `frontend/ui/role_manager.py`: Updated role mapping for canonical roles
- `backend/core/views_template.py`: InvoiceTemplateViewSet now requires `IsAuthenticated`
- `backend/sales/views.py`: CustomerViewSet now requires `IsAuthenticated`
- `backend/purchases/views.py`: SupplierViewSet now requires `IsAuthenticated`
- `backend/sales/models.py`: Fixed bare except → logs warning before fallback
- `backend/security/views.py`: Fixed silent pass → logs debug message

### Phase 30 Steps Completed (Domain Consolidation & SSOT Enforcement)

**Module 1 — Company Identity Consolidation:**
1. ✅ Verified frontend hardcoded "Pharmacy ERP" references — most are product branding (app title, login, about dialog), not business identity
2. ✅ Audited `installer/first_run_setup.py` — stores `company_name` in local config.json but backend never reads it (dead data, not active duplication)
3. ✅ Verified `entities/models.py` — Entity model is for multi-branch operations (headquarters, pharmacy branches, warehouses), NOT a Company duplicate. Different purpose: Company = legal identity, Entity = operational location
4. ✅ Backend PDF generators use Company model (Phase 28) — single source of truth for branding

**Module 2 — Role & Permission Unification:**
5. ✅ Canonical roles enforced: Admin, Manager, Accountant, Pharmacist, Cashier, Supervisor, Warehouse, HR, General
6. ✅ Protected critical endpoints with `IsAuthenticated`:
   - `financial_control_tower.py` — all 4 endpoints (credit exposure, risk distribution, decisions)
   - `core/operations/views.py` — all 22 endpoints (financial integrity, inventory integrity, alerts, observability, scalability, data integrity, decisions)
   - Previously protected: InvoiceTemplate, Customer, Supplier ViewSets

**Module 3-5 — Pending:**
- SystemConfig consolidation
- Cross-layer contract validation
- Remaining AllowAny endpoints (~100+ in ficl_views, observability, governance, backup, workflows, inventory, expenses, payroll, payments, hr)

### Phase 30 Files Modified
- `backend/core/api/v1/financial_control_tower.py`: All 4 endpoints now require `IsAuthenticated`
- `backend/core/operations/views.py`: All 22 endpoints now require `IsAuthenticated` (health checks included for defense-in-depth)

### Phase 22-23 Files Created/Modified
- `backend/core/drift_prevention/migration_router.py`: MigrationRouter with dual-engine dispatch
- `backend/expenses/models.py`: Replaced JournalEngine + shadow → MigrationRouter.create_entry()
- `backend/returns/models.py`: Replaced 3 JournalEngine + shadow → MigrationRouter.create_entry()/reverse_entry()
- `backend/payments/services.py`: Replaced 3 JournalEngine + shadow → MigrationRouter.create_entry()
- `backend/purchases/views.py`: Replaced 3 JournalEngine + shadow → MigrationRouter.create_entry()/reverse_entry()
- `backend/sales/views.py`: Replaced 3 JournalEngine + shadow → MigrationRouter.create_entry()/reverse_entry()
- `backend/accounting/views_account.py`: Replaced 2 JournalEngine + shadow → MigrationRouter.post_entry()/reverse_entry()
- `backend/tests/test_validation_harness.py`: Real execution test harness (6 workflows, drift classification, health scoring)

### Key Decisions
- MigrationRouter replaces both JournalEngine calls AND shadow blocks: single dispatch point per financial operation
- MigrationRouter._normalize_lines() converts `account_id` → `account_code` for Gateway path (handles mixed line formats across modules)
- Test harness uses `TransactionTestCase` for real DB behavior, creates payment infrastructure to avoid pre-existing test failures
- Test harness uses `dispatch.allocations` from `StockIntegrationService.process_sale()` result (no `select_stock` method exists)
- Test harness uses `errors` (list) not `error` on `StockOperationResult`
- Drift classification: A = OK, B = warning (minor mismatch), C = critical failure (financial mismatch), D = system failure (exception)
- System health scoring: 0–100, deductions for journal imbalance, system delta ≠ 0, account balance violations, batch quantity violations, orphan entries, bad routing states
- Company Profile API reuses existing `Company` model (no new model created)
- Company Profile UI uses existing BaseScreen, EnterpriseButton, color tokens, and API client patterns

### Next Steps
1. **Module 3: Configuration Source Unification** — Consolidate SystemConfig / JSON settings overlap
2. **Module 4: Cross-Layer Contract Validation** — Role/permission schema alignment audit
3. **Module 5: Full regression test suite** — Final validation before Phase 30 completion
4. **Remaining AllowAny endpoints** — Review and protect ficl_views, observability, governance, backup, workflows, inventory, expenses, payroll, payments, hr endpoints (~100+ remaining)
5. **Currency default consumption** — Wire `Company.default_currency` to application defaults
6. **Invoice branding integration** — Wire company address, phone, tax_number into PDF headers/footers

### Critical Context
- Migration Router architecture: non-migrated functions → JournalEngine only; migrated functions → JournalGateway with pre-simulation, equilibrium check, and rollback
- All state is database-persisted (MigrationConfig, DriftRecord, ModuleDriftState, MigrationLog) — survives restarts
- Phase 22 is NOT a single cutover — each function migrates individually through the 5-layer pipeline
- System health scoring: 100−30*blocked_modules−20*Class_C−30*Class_D−5*CD_events
- Pre-existing risk: BalanceSyncService directly mutates customer/supplier balance fields (acceptable, audited)
- Pre-existing risk: UI computes invoice totals locally for display (acceptable, backend re-validates all amounts)
- All LSP errors are pre-existing Django/Pyright type inference issues — not runtime bugs
- Company model already exists with all needed fields (name, code, address, phone, email, tax_number, logo, currencies)
- JWT auth, RBAC, theme system all exist and are functional — only need stabilization and UI gaps filled
- **Security fixes applied (Phase 27)**:
  - Logout now blacklists token server-side before clearing local session
  - Duplicate `change_password` removed (was crashing on anonymous access)
  - Dev mode requires explicit `PHARMACY_ERP_DEVELOPMENT=true` env var (file-based bypass removed)
  - Hardcoded JWT dev token removed — requires `PHARMACY_ERP_DEV_TOKEN` env var
- **Stability hardening applied (Phase 29)**:
  - AuthManager is single source of truth for session management (both stores cleared together)
  - API client retry loop no longer blocks UI thread (`time.sleep()` → `processEvents()`)
  - Canonical roles aligned: Admin, Manager, Accountant, Pharmacist, Cashier, Supervisor, Warehouse, HR, General
  - Critical endpoints protected: InvoiceTemplate, Customer, Supplier ViewSets now require `IsAuthenticated`
  - Bare except blocks and silent passes fixed in critical flows (sales, security)
- **Domain consolidation applied (Phase 30)**:
  - Company identity verified as single source of truth (PDF generators, installer audit, Entity model distinction)
  - Financial Control Tower endpoints protected (4 endpoints, exposes credit exposure/risk data)
  - Operations endpoints protected (22 endpoints, exposes financial/inventory integrity, alerts, observability)
  - Entity model confirmed as multi-branch architecture (NOT a Company duplicate)

### Relevant Files
- `backend/core/drift_prevention/migration_router.py`: Central Engine/Gateway dispatch with _normalize_lines()
- `backend/core/drift_prevention/migration_registry.py`: MigrationRegistry — per-function state machine
- `backend/core/drift_prevention/equilibrium_checker.py`: EquilibriumChecker — post-switch verification
- `backend/core/drift_prevention/rollback_manager.py`: RollbackManager — function/module rollback
- `backend/core/drift_prevention/observability.py`: Observability — execution_hash + financial_signature logging
- `backend/core/services/journal_gateway.py`: Gateway with period-lock, entity tracking, audit logging
- `backend/core/models/system.py`: Company model (name, code, address, phone, email, tax_number, logo, currencies)
- `backend/core/serializers.py`: CompanySerializer
- `backend/core/urls.py`: CompanyViewSet with CRUD + default/active endpoints
- `frontend/ui/system/company_profile_screen.py`: CompanyProfileScreen (230 lines)
- `frontend/ui/system/settings_screen.py`: Existing SettingsScreen (local JSON, needs API sync)
- `frontend/theme/theme_engine.py`: ThemeEngine singleton (apply_theme, toggle, theme_changed signal)
- `frontend/ui/role_manager.py`: Role permissions mapping, AuthorizationResolver
- `frontend/security/auth_manager.py`: AuthManager (login, logout, session, ui_scopes)
- `frontend/api/client.py`: APIClient (Bearer token, auto refresh on 401)
- `backend/tests/test_validation_harness.py`: Real execution test harness (6 workflows)
- `backend/tests/base.py`: BaseTestCase, TransactionBaseTestCase (test fixtures)
- `backend/tests/factories.py`: 20+ factory classes for test data creation

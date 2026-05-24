# ARCHITECTURE DECISIONS
## Pharmacy ERP — Append-Only Architecture Decision Record

**Generated:** May 21, 2026
**Status:** PHASE 35 — INITIAL SEED
**Type:** Append-Only Living Document

This document records all significant architecture decisions made during the Pharmacy ERP project. Each ADR is immutable once finalized. Future phases MAY add new ADRs but MUST NOT modify existing ones.

---

## ADR-001: Modular Monolith Architecture

**Context:** The system needed to support 24+ business domains (inventory, sales, purchases, accounting, HR, payroll, payments, returns, fixed assets, insurance, expenses, workflows, etc.) with strong separation while maintaining deployment simplicity. Microservices were considered but rejected due to operational overhead for a desktop ERP.

**Decision:** Use Django modular monolith — separate Django apps within a single process, communicating through function calls, signals, and an event bus.

**Consequences:**
- ✅ Strong domain boundaries via Django app isolation
- ✅ Simple deployment (single process)
- ✅ Shared database transactions across domains (ACID guarantees)
- ❌ Can't scale domains independently
- ❌ Single process limits to vertical scaling
- ❌ Migration changes can affect all apps simultaneously

**Status:** ACCEPTED — architecture freeze in effect

---

## ADR-002: Double-Entry Accounting Engine

**Context:** Financial integrity requires atomic, irreversible journal entries with debit/credit balancing. Manual SQL operations risk introducing orphaned entries or unbalanced transactions.

**Decision:** Implement JournalEngine as the sole path for creating, posting, reversing journal entries. All financial transactions must go through this engine.

**Consequences:**
- ✅ Guaranteed balanced entries (debits == credits)
- ✅ Atomic creation within transaction.atomic()
- ✅ select_for_update prevents concurrent posting conflicts
- ❌ All financial code must route through JournalEngine
- ❌ Tenancy scoping adds complexity (CompanyScopedViewSetMixin)

**Status:** ACCEPTED — core financial pillar

---

## ADR-003: FEFO Stock Selection Algorithm

**Context:** Pharmacy inventory requires strict expiry management — products expiring soonest must be sold first. FIFO (First In First Out) is insufficient for pharmaceutical compliance.

**Decision:** Implement FEFO (First Expiry First Out) as default stock selection mode with FIFO as fallback option.

**Consequences:**
- ✅ Compliant with pharmaceutical stock rotation requirements
- ✅ Reduces expired inventory write-offs
- ✅ Configurable per warehouse via StockSelectionMode enum
- ❌ Requires accurate expiry date tracking on all batches
- ❌ Performance overhead from sorting by expiry_date

**Status:** ACCEPTED — implemented in Inventory Service

---

## ADR-004: API Standardization (Phase 8)

**Context:** Inconsistent API response formats across 30+ endpoints made frontend error handling complex and development slow.

**Decision:** Implement a centralized API response layer with StandardizedJSONRenderer, APIResponse class, StandardizedPagination, and StandardizedResponseMixin.

**Consequences:**
- ✅ Consistent JSON response format across all endpoints
- ✅ Automatic company context injection
- ✅ Standardized error codes (40+ codes: AUTH_*, FIN_*, INV_*, etc.)
- ❌ All existing endpoints needed migration
- ❌ Added middleware overhead for response rendering

**Status:** ACCEPTED — fully deployed

---

## ADR-005: Simulation Isolation (Phase 3A-3B)

**Context:** Simulation/testing layer risked leaking into production code. Engineers might accidentally import simulation modules from production views.

**Decision:** Enforce strict layer isolation — simulation code can import production code but production code MUST NOT import simulation code. Verified by drift_check.py scanner.

**Consequences:**
- ✅ Production code has zero simulation dependencies
- ✅ Explicit ALLOWED_BRIDGE_FILES for legitimate bridges
- ✅ Automated detection via dependency scanner
- ❌ Cannot run simulations from production context
- ❌ Duplicated helper types needed in both layers

**Status:** ACCEPTED — enforced by CI

---

## ADR-006: Read-Only Truth Engine

**Context:** The Truth Engine detects drifts between expected vs actual system state. If it could write corrections, it risked masking root causes and creating an infinite correction loop.

**Decision:** Truth Engine is strictly read-only — it collects, compares, scores, reports, and snapshots. It NEVER writes to the ERP database. All mismatches are logged but NOT auto-corrected.

**Consequences:**
- ✅ Cannot mask root causes with auto-corrections
- ✅ Safe to run in production alongside live operations
- ✅ All mismatches explicitly documented for human review
- ❌ Can't prevent drift in real-time
- ❌ Requires human intervention for all corrections

**Status:** ACCEPTED — fundamental design constraint

---

## ADR-007: UI Component Standardization (Phase 4E/14)

**Context:** UI screens were built with raw QWidget/QPushButton/QTableWidget, causing inconsistent styling, duplicated code, and maintenance burden.

**Decision:** Mandate a strict component hierarchy: BaseScreen → BaseFormScreen/BaseListScreen. Use only EnterpriseButton, EnterpriseTable, DataEntryGrid, FormSection, ScreenStateHelper. Forbidden to use raw QPushButton/QTableWidget/QGroupBox directly.

**Consequences:**
- ✅ Consistent look and feel across 25+ screens
- ✅ Centralized style control via COLOR_* tokens
- ✅ Standardized loading/error/empty states
- ❌ All new screens require more boilerplate setup
- ❌ Migration of legacy screens is ongoing

**Status:** ACCEPTED — partially migrated (Phase 14+)

---

## ADR-008: Financial Period Closing with SOFT_CLOSED

**Context:** Traditional hard close (LOCKED) prevents any modifications, but sometimes need to reverse entries in a closed period with proper audit trail.

**Decision:** Introduce SOFT_CLOSED status between OPEN and CLOSED. SOFT_CLOSED prevents new postings but allows controlled reversals with full audit logging via FiscalPeriodCloseLog.

**Consequences:**
- ✅ Controlled reversals possible in closed periods
- ✅ Full audit trail for every close/reopen action
- ✅ Graceful escalation: OPEN → SOFT_CLOSED → CLOSED → LOCKED
- ❌ More states to validate in financial workflows
- ❌ Requires careful permission control for period mutations

**Status:** ACCEPTED — implemented in FiscalPeriod model

---

## ADR-009: Payment Engine with Multi-Method Support

**Context:** Afghan market requires diverse payment methods — cash, bank transfers, mobile money (M-Paisa), and Hawala (informal value transfer system).

**Decision:** Implement PaymentEngine supporting 6 payment methods (Cash, Bank, Mobile, Hawala, Cheque, Credit Card) with auto FinancialTransaction creation and double-entry journal generation.

**Consequences:**
- ✅ All major Afghan payment methods supported
- ✅ Automatic journal entries for every financial transaction
- ✅ Audit trail via FinancialTransaction model
- ❌ Hawala reconciliation is manual (no central ledger)
- ❌ Integration with actual mobile money APIs is future work

**Status:** ACCEPTED — all 6 methods implemented

---

## ADR-010: Concurrency Control with select_for_update

**Context:** Concurrent operations on inventory batches, journal entries, and payment allocations could cause race conditions — double-selling the same stock or creating unbalanced journal entries.

**Decision:** Use PostgreSQL select_for_update within transaction.atomic() for all critical write operations. Implement optimistic concurrency patterns for high-read, low-write operations.

**Consequences:**
- ✅ Prevents concurrent stock overselling
- ✅ Prevents concurrent journal entry double-posting
- ✅ Prevents concurrent payment allocation races
- ❌ Row-level locking reduces concurrent throughput
- ❌ Deadlock risk if lock ordering isn't consistent

**Status:** ACCEPTED — implemented across financial, inventory, and payment services

---

## ADR-011: Event Bus for Cross-Domain Communication

**Context:** Domains need to react to events in other domains (e.g., sales dispatch → inventory reduction → accounting entry). Direct imports create tight coupling.

**Decision:** Use Django signals and an in-process event bus for cross-domain communication. Workflow Orchestrator maps events to workflow definitions.

**Consequences:**
- ✅ Loose coupling between domains
- ✅ Extensible — new listeners can be added without modifying producers
- ✅ All cross-domain flows are explicit and traceable
- ❌ Debugging event chains is harder than direct calls
- ❌ Signal ordering non-deterministic in some cases

**Status:** ACCEPTED — refined in Phase 12.1 with SignalCoordinator

---

## ADR-012: Governed Intelligence Layer (No AI/ML)

**Context:** The operational intelligence layer (anomaly detection, trending, forecasting, SLA monitoring) needed to be deterministic and auditable, not a black box.

**Decision:** All intelligence is rule-based, deterministic, and stateless. Zero AI/ML. All rules are registered in RuleRegistry. Anomaly detection uses 8 static rules with configurable thresholds. Forecasting uses linear extrapolation and moving averages only.

**Consequences:**
- ✅ Fully deterministic and auditable
- ✅ No training data or model drift concerns
- ✅ All alerts have explicit, explainable triggers
- ❌ Cannot detect novel patterns outside defined rules
- ❌ Threshold tuning requires manual calibration

**Status:** ACCEPTED — deployed in Phase 12

---

## ADR-013: Role-Based Permission System

**Context:** Different users (admin, accountant, warehouse, pharmacist, manager) need different access levels. Flat Django permissions proved insufficient for granular control.

**Decision:** Implement RoleBasedPermission with seeded roles (20+ roles) and granular permission checks at viewset level. Default REST framework permission class remains IsAuthenticated.

**Consequences:**
- ✅ Granular per-viewset permission control
- ✅ Seeded roles for quick deployment
- ✅ Audit trail for permission checks
- ❌ Role management requires admin UI (not yet built)
- ❌ Permission checking adds latency to every API call

**Status:** ACCEPTED — most views use RoleBasedPermission

---

## ADR-014: Returns Cycle with Approval Workflow

**Context:** Return orders must go through approval before reconciliation. Direct reversal of sales/purchase invoices risks inventory and financial integrity.

**Decision:** Implement Returns cycle with 4 stages: Created → Approved → Reconciled → Voided. Each stage transition requires explicit action with select_for_update locking to prevent race conditions.

**Consequences:**
- ✅ Full audit trail for each return lifecycle
- ✅ No accidental inventory/accounting modifications
- ✅ select_for_update prevents double-approval
- ❌ Adds latency to return processing
- ❌ Requires multi-step UI for processing returns

**Status:** ACCEPTED — implemented in Returns module

---

## ADR-015: Desktop-First with PySide6

**Context:** The target market (Afghan pharmacies) has unreliable internet connectivity. A web app would be unusable during outages.

**Decision:** Build desktop application with PySide6 (Qt for Python) as the primary interface. Django backend runs locally. API client communicates with localhost.

**Consequences:**
- ✅ Works offline (Django runs locally)
- ✅ Rich desktop UI with native look and feel
- ✅ Printer/barcode scanner integration via system APIs
- ❌ Requires local installation (installer provided)
- ❌ Updates must be manually installed
- ❌ No centralized data (each installation has own database)

**Status:** ACCEPTED — fundamental deployment model

---

## ADR-016: Company Multi-Tenancy via Scoped Mixins

**Context:** The system may serve multi-branch pharmacy chains. Data isolation between companies is critical.

**Decision:** Implement CompanyScopedMixin pattern — every data-bearing model inherits from CompanyScopedMixin. ViewSets use CompanyScopedViewSetMixin to auto-filter by company. All API responses inject company context.

**Consequences:**
- ✅ Strong data isolation between companies
- ✅ Automatic filtering reduces query bugs
- ✅ Company context flows through all API layers
- ❌ Every query includes company filter (minor overhead)
- ❌ Cross-company reporting requires explicit UNION queries

**Status:** ACCEPTED — core data architecture pattern

---

## ADR-017: Cash Flow Categorization

**Context:** Cash flow reporting requires categorizing every transaction as Operating, Investing, or Financing activity. Manual categorization is error-prone.

**Decision:** Implement CashFlowEngine with rule-based categorization using account codes. Accounts 1xxx-5xxx are operating, 6xxx are investing, 7xxx-8xxx are financing. Support manual override with audit trail.

**Consequences:**
- ✅ Automated categorization based on chart of accounts
- ✅ Consistent cash flow reporting
- ✅ Manual overrides supported with audit trail
- ❌ New account creation may require cash flow rule update
- ❌ Complex transactions may span multiple categories

**Status:** ACCEPTED — implemented in CashFlow app

---

## ADR-018: Export Engine with Graceful Degradation

**Context:** Financial reports need Excel (.xlsx) export for accountant use, but openpyxl may not be installed. CSV fallback required.

**Decision:** Implement ExcelExporter as primary export format with automatic fallback to CSV if openpyxl is unavailable. All export formatting centralized in BaseExporter.

**Consequences:**
- ✅ Excel export with proper formatting when available
- ✅ Automatic CSV fallback ensures zero failures
- ✅ Centralized number formatting (AFN/USD support)
- ❌ Excel features (charts, pivot tables) not supported
- ❌ Large exports may timeout under default limits

**Status:** ACCEPTED — deployed in Phase 14C

---

## ADR-019: Invoice Generation via Template Engine

**Context:** Sales and purchase invoices need professional PDF generation with company branding, QR codes, and thermal printer support.

**Decision:** Use InvoiceTemplateEngine for PDF generation with configurable templates, QR code embedding, and thermal printer output via ThermalPrinter service.

**Consequences:**
- ✅ Professional invoice PDFs with company branding
- ✅ QR code for quick verification
- ✅ Thermal printer support for retail receipts
- ❌ Template customization requires code changes
- ❌ PDF generation isn't real-time for high throughput

**Status:** ACCEPTED — implemented in Phase 14C/15

---

## ADR-020: Bounded Memory for Simulation Components

**Context:** Simulation components (drift memory, event history, causal graphs) could grow unbounded, causing memory leaks in long sessions.

**Decision:** All simulation data structures use bounded collections (deque with maxlen, list caps at 5000 items). MemoryBoundaryValidator enforces limits across all structures.

**Consequences:**
- ✅ Guaranteed bounded memory growth
- ✅ No simulation memory leak in long sessions
- ✅ Automated auditing via MemoryBoundaryValidator
- ❌ Old data is evicted when limits are reached
- ❌ Maximum history window is capped

**Status:** ACCEPTED — enforced by Phase 3B.5 audit layer

---

*This document is append-only. New ADRs MUST be appended to the end. Existing ADRs MUST NOT be modified or deleted.*

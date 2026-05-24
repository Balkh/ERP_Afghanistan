# Engine Authority Matrix - Phase 37

## Authority Level Definitions
- **AUTHORITATIVE (SSOT)**: Single source of truth. Mandatory for all related operations.
- **OPERATIONAL**: Primary engine for production workflows.
- **OBSERVABILITY**: Read-only engine for monitoring and analysis.
- **DEPRECATED**: To be removed or consolidated.

---

## 1. Financial & Accounting Engines

### `JournalEngine`
- **Purpose**: Core double-entry accounting logic (creation, validation, posting).
- **Consumers**: `JournalGateway`, `ReturnOrder`, `SalesInvoice`.
- **Authority Level**: **OPERATIONAL**
- **Side Effects**: DB Writes (JournalEntry, Account Balance).
- **Production Usage**: ACTIVE (All financial modules).
- **Overlap Risks**: None. Core system.

### `JournalGateway`
- **Purpose**: Mandatory enforcement layer for all financial operations.
- **Consumers**: All modules requiring financial state changes.
- **Authority Level**: **AUTHORITATIVE (SSOT)**
- **Side Effects**: Atomic transaction management, audit logging.
- **Production Usage**: ACTIVE (Mandatory wrapper).

### `FinancialTruthEngine`
- **Purpose**: Derives current financial state from transactional data (Invoices - Payments).
- **Consumers**: `FinancialPolicyEngine`, Dashboards.
- **Authority Level**: **AUTHORITATIVE (Read-Only)**
- **Side Effects**: None.
- **Production Usage**: ACTIVE (Balance derivation).

---

## 2. Inventory & Stock Engines

### `StockIntegrationService`
- **Purpose**: Core inventory integration (FEFO/FIFO allocation, stock deduction).
- **Consumers**: `SalesInvoice`, `PurchaseInvoice`, `WarehouseTransfer`.
- **Authority Level**: **OPERATIONAL**
- **Side Effects**: DB Writes (StockMovement, Batch quantity).
- **Production Usage**: ACTIVE (Core inventory logic).

---

## 3. Observability & Truth Verification

### `TruthGateway`
- **Purpose**: Verifies system truth by comparing Event Store projections with DB state.
- **Consumers**: Observability Console, Governance API.
- **Authority Level**: **AUTHORITATIVE (SSOT for Verification)**
- **Side Effects**: None.
- **Production Usage**: ACTIVE (Integrated into v1 API).

### `TruthEngine` (Simulation)
- **Purpose**: Passive observation orchestrator for simulation.
- **Consumers**: Simulation engine, Digital Twin.
- **Authority Level**: **OBSERVABILITY (Analysis-Only)**
- **Side Effects**: None.
- **Overlap Risks**: High overlap with `TruthGateway`.
- **Governance Plan**: Convert to analysis-only mode. Use `TruthGateway` for actual verification logic.

---

## 4. Decision & Policy Engines

### `FinancialPolicyEngine`
- **Purpose**: Deterministic business policy evaluation (Blocks/Warnings).
- **Consumers**: `SalesInvoice`, `CustomerPayment`.
- **Authority Level**: **OPERATIONAL**
- **Side Effects**: DecisionRecord logging.
- **Production Usage**: ACTIVE.

### `DecisionEngine` (Observability)
- **Purpose**: Converts correlated observability signals into recommended actions.
- **Consumers**: Control Center Dashboard.
- **Authority Level**: **OBSERVABILITY**
- **Side Effects**: None.
- **Production Usage**: ACTIVE (Monitoring only).

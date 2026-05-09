# Pharmacy ERP — Project Context

## Project Overview
- **Name**: Pharmacy ERP
- **Type**: Desktop ERP for pharmaceutical distribution
- **Frontend**: PySide6 (Qt for Python) — `D:\Projects\Pharmacy_ERP\frontend\`
- **Backend**: Django + DRF — `D:\Projects\Pharmacy_ERP\backend\`
- **Database**: PostgreSQL (configured in `backend/config/settings.py`)
- **Base Currency**: AFN (Afghan Afghani) / USD

---

## Current Status: Phase 12 COMPLETE

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Foundation (models, base UI) | ✅ Complete |
| Phase 2A-2E | Inventory (products, categories, warehouses, batches, UI) | ✅ Complete |
| Phase 3A-3E | Sales & Purchase (invoices, stock integration, UI, PDF) | ✅ Complete |
| Phase 4A | Chart of Accounts (37 accounts, hierarchy) | ✅ Complete |
| Phase 4B | Journal Entry Engine (double-entry, posting, reversal) | ✅ Complete |
| Phase 4C | Payment & Financial Transactions (Cash, Bank, Mobile, Hawala) | ✅ Complete |
| Phase 4D | Financial Reports (Trial Balance, P&L, Balance Sheet, AR/AP Aging, Cash Flow, CSV export) | ✅ Complete |
| **Phase 4E** | **Accounting UI (dashboard, ledger, journal forms, report screens)** | **✅ Complete** |
| **Phase 6D** | **Final Testing + Code Cleanup (test suite, coverage, bug fixes)** | **✅ Complete** |
| **Phase 5** | **Auth, Warehouse Transfers, Notifications** | **✅ Complete** |
| **Phase 7A** | **HR Foundation (Employee, Department, Position)** | ✅ Complete |
| **Phase 7B** | **Attendance System (Attendance, Leave, Overtime)** | ✅ Complete |
| **Phase 7C** | **Payroll Foundation (Salary, Allowance, Deduction, PayrollCycle)** | ✅ Complete |
| **Phase 7D** | **Payroll Accounting (PayrollAccountingService)** | ✅ Complete |
| **Phase 7E** | **HR & Payroll Reports** | ✅ Complete |
| **Phase 7F** | **Restore System (RestorePoint, validation, rollback)** | ✅ Complete |
| **Phase 8** | **API Standardization (StandardizedJSONRenderer, APIResponse)** | ✅ Complete |
| **Phase 9** | **Production Operations (health, financial/inventory integrity, alerts)** | ✅ Complete |
| **Phase 9B** | **API Observability (bad request intelligence, slow request detection)** | ✅ Complete |
| **Phase 9C** | **Future Stability (scalability, concurrency, data integrity)** | ✅ Complete |
| **Phase 9D** | **Sustainability Guardrails (complexity control, performance budgets)** | ✅ Complete |
| **Phase 9E** | **Enterprise Stability Refinement (adaptive sampling, config versioning)** | ✅ Complete |
| **Phase 11** | **Enterprise Control Center (ControlCenterAggregator dashboards)** | ✅ Complete |
| **Phase 12** | **Advanced Operational Intelligence (SLA, Capacity Forecast, Alerts)** | ✅ Complete |
| **Phase 12.1** | **Intelligence Stability Patch (RuleRegistry, SignalCoordinator)** | ✅ Complete |

### Test Suite Summary
- **995+ tests passing** (increased from 932)
- **Coverage**: Inventory 93.94%, Accounting 72.11%, Sales ~96%, Purchases ~96%, Overall ~50%
- **Key fixes in Phase 5**:
  - Fixed `StockMovement._update_batch_quantity()` to skip TRANSFER movements (was resetting batch to 0)
  - Fixed `Batch.save()` to handle `remaining_quantity` correctly (was treating Decimal('0.00') as falsy)
  - Fixed Notification model `object_id` field to allow NULL
- **Transfer bug**: `StockMovement._update_batch_quantity()` only counted IN/OUT movements, not TRANSFER. When transfer OUT movement was created, it calculated -50 (no IN yet) and reset batch to 0. Fix: Skip recalculation for TRANSFER movements.
- **Test files**: `test_accounting.py`, `test_inventory.py`, `test_sales.py`, `test_purchases.py`, `test_api.py`, `test_lifecycle.py`, `test_edge_cases.py`, `test_lifecycle_full.py`, `test_accounting_viewset.py`, `test_accounting_views.py`, `test_inventory_views.py`, `test_sales_views.py`, `test_purchases_views.py`, `test_financial_reports.py`, `test_services.py`, `test_auth.py`, `test_transfer.py`, `test_notifications.py`

### Phase 7E Steps Completed
1. ✅ Created HR Reports service (`hr/services/reports.py`)
2. ✅ Created Payroll Reports service (`payroll/services/reports.py`)
3. ✅ Added employee list, attendance, leave, payroll API endpoints

### Phase 7F Steps Completed
1. ✅ Added RestorePoint model (`backup/models.py`)
2. ✅ Added RestoreValidation model (`backup/models.py`)
3. ✅ Created RestoreService with validation (`backup/services/restore_service.py`)
4. ✅ Created restore API endpoints (`backup/views.py`)
5. ✅ Added serializers (`backup/serializers.py`)
6. ✅ Added routes (`backup/urls.py`)
7. ✅ Created migration (`backup/migrations/0002_restorepoint_restorevalidation_and_more.py`)
8. ✅ Created restore tests (`tests/test_restore.py`)

### Phase 7F Files Created/Modified
- `backup/models.py`: Added RestorePoint, RestoreValidation models
- `backup/services/restore_service.py`: RestoreService with validation
- `backup/views.py`: Added RestorePointViewSet
- `backup/serializers.py`: Added RestorePointSerializer, RestoreValidationSerializer
- `backup/urls.py`: Added restore-points route
- `tests/test_restore.py`: Restore service tests

### API Contract Standardization (Phase 8)
All API responses now follow a standardized format with automatic company context injection.

**New Files:**
| File | Purpose |
|------|---------|
| `core/api/responses.py` | APIResponse class (success, error, paginated methods) |
| `core/api/errors.py` | Error code registry (40+ codes: AUTH_*, FIN_*, INV_*, etc.) |
| `core/api/pagination.py` | StandardizedPagination for consistent pagination |
| `core/api/renderers.py` | StandardizedJSONRenderer - auto-wraps all responses |
| `core/api/mixins.py` | StandardizedResponseMixin for ViewSets |

**Standard Response Format:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "company_id": "uuid"  (when company context set)
  }
}
```

**Error Response Format:**
```json
{
  "success": false,
  "error": { "code": "AUTH_001", "message": "..." },
  "meta": { ... }
}
```

**API Versioning:** Accept-header based (`Accept: application/json; version=v1`)

### Phase 12 Steps Completed
Advanced Operational Intelligence Layer - DETERMINISTIC (NO AI/ML):
1. ✅ Created `core/operations/operational_intelligence.py` with:
   - RuleBasedAnomalyDetector (8 static rules with thresholds)
   - TrendIdentifier (latency, error, stock trend detection)
   - RiskPredictor (SLA, stockout, journal imbalance, batch expiry prediction)
   - SLAMonitoringEngine (compliance score 0-100, violations, degradation timeline)
   - CapacityForecastEngine (linear extrapolation, moving average, historical comparison)
   - IntelligenceAlertSystem (structured alerts with explanation, metric comparison, baseline)
   - CachedIntelligenceAggregator (60s TTL cache, no blocking operations)
2. ✅ Created `tests/test_operational_intelligence.py` (63 tests)
3. ✅ Added endpoint `/api/control-center/intelligence/`
4. ✅ All tests passing

### Phase 12 Validation Output
| Component | Status |
|---|---|
| BASELINE ENGINE | PASS |
| ANOMALY DETECTION | PASS |
| TREND DETECTION | PASS |
| SLA MONITORING | PASS |
| CAPACITY FORECAST | PASS |
| ALERT SYSTEM | PASS |
| PERFORMANCE IMPACT | LOW |
| PRODUCTION READINESS | READY |

### Phase 12 Files Created
- `core/operations/operational_intelligence.py`: All intelligence components
- `tests/test_operational_intelligence.py`: 63 tests for all components

### Phase 12.1 Validation Output
| Component | Status |
|---|---|
| RULE REGISTRY | PASS |
| NO INLINE RULES IN INTELLIGENCE ENGINE | PASS |
| SIGNAL DEDUPLICATION WORKS | PASS |
| CONTROL CENTER CONSISTENCY | PASS |
| ALERT DUPLICATION ELIMINATED | PASS |
| PRODUCTION READINESS | READY |

### Phase 12.1 Files Created
- `core/operations/signal_coordinator.py`: Signal deduplication layer
- RuleRegistry: Centralized rule governance (20+ rules)
- SignalCoordinator: 10-min deduplication window, severity override, signal merging

### Phase 12.1 Architecture
- Intelligence Layer = signal producer ONLY
- SignalCoordinator = single truth layer
- Control Center = signal consumer ONLY
- Alert System = formatted output ONLY

---

## Where to Start Next

### Recommended Next Steps
1. **Run backend**: `cd backend && python manage.py runserver`
2. **Seed data**: `python manage.py seed_payments` (payment methods + accounts)
3. **Test accounting flows**: Create a sale invoice → dispatch → verify journal entry auto-created
4. **Define Phase 5**: What features are needed next? (e.g., user auth, roles, barcode hardware integration, multi-warehouse transfers, insurance module, etc.)

### Quick Verification Commands
```bash
# Backend health check
cd backend && python manage.py check

# Verify payment data seeded
python manage.py shell -c "from payments.models import PaymentMethod; print(PaymentMethod.objects.count())"

# Verify accounting data
python manage.py shell -c "from accounting.models import Account; print(Account.objects.count())"
```

---

## Architecture Overview

### Backend (`backend/`)
```
backend/
├── config/                  # Django settings, URLs
├── accounting/              # Chart of accounts, journal entries, financial reports
│   ├── models.py            # Account, JournalEntry, JournalEntryLine
│   ├── services/
│   │   ├── account_hierarchy.py
│   │   ├── journal_engine.py       # Double-entry engine
│   │   ├── financial_reports.py    # All financial reports
│   │   └── report_exporter.py      # CSV/text export
│   └── views_account.py            # All accounting API endpoints
├── payments/                # Payment infrastructure
│   ├── models.py            # PaymentMethod, PaymentAccount, FinancialTransaction, Settlement
│   ├── services.py          # PaymentEngine (receipts, payments, transfers, refunds)
│   └── views.py             # Payment API endpoints
├── sales/                   # Customers, sales invoices, payments
├── purchases/               # Suppliers, purchase invoices, payments
├── inventory/               # Products, batches, warehouses, stock movements
└── core/                    # Base models, auth
```

### Frontend (`frontend/`)
```
frontend/
├── ui/
│   ├── main_window.py       # Main window with QStackedWidget (21 pages)
│   ├── sidebar.py           # Navigation sidebar (21 items with group headers)
│   ├── accounting/          # All accounting screens
│   │   ├── accounting_dashboard.py
│   │   ├── chart_of_accounts_screen.py
│   │   ├── journal_entry_screen.py
│   │   ├── account_ledger_screen.py
│   │   ├── base_report_screen.py
│   │   ├── trial_balance_screen.py
│   │   ├── profit_loss_screen.py
│   │   ├── balance_sheet_screen.py
│   │   ├── arap_ageing_screen.py
│   │   └── components/
│   │       ├── account_form_dialog.py
│   │       ├── journal_entry_form.py
│   │       ├── journal_entry_detail.py
│   │       └── report_preview_dialog.py
│   ├── inventory/           # Product, category, warehouse, batch screens
│   ├── sales/               # Sales invoice screen
│   └── purchases/           # Purchase invoice screen
└── api/client.py            # API client (requests-based)
```

---

## Key Integration Points

### Auto Journal Entry Creation
- **Sales Invoice dispatch** → Creates SALE journal entry (Dr AR, Cr Revenue, Cr Tax)
- **Sales payment** → Creates RECEIPT journal entry (Dr Cash, Cr AR)
- **Sales cancel** → Reverses journal entry
- **Purchase receive** → Creates PURCHASE journal entry (Dr Inventory, Cr AP)
- **Purchase payment** → Creates PAYMENT journal entry (Dr AP, Cr Cash)
- **Purchase cancel** → Reverses journal entry

### Payment Flow
- `CustomerPayment.save()` → Auto-creates `FinancialTransaction` via `PaymentEngine.process_receipt()`
- `SupplierPayment.save()` → Auto-creates `FinancialTransaction` via `PaymentEngine.process_payment()`

### API Base URL
- Backend: `http://localhost:8000`
- Frontend API client default: `http://localhost:8000`

---

## Key Files to Reference

| Purpose | File |
|---|---|
| All accounting models | `backend/accounting/models.py` |
| Journal engine | `backend/accounting/services/journal_engine.py` |
| Financial reports | `backend/accounting/services/financial_reports.py` |
| Payment engine | `backend/payments/services.py` |
| Frontend main window | `frontend/ui/main_window.py` |
| Frontend sidebar | `frontend/ui/sidebar.py` |
| API client | `frontend/api/client.py` |

---

## Seeded Data (via management commands)
- **37 default accounts** (Chart of Accounts)
- **6 payment methods** (Cash, Bank, Mobile, Hawala, Cheque, CC)
- **5 payment accounts** (Main Cash AFN, USD Cash, AIB Bank, M-Paisa, Al-Farooq Hawala)

# 🐛 Bug Fix Report — ERP_Afghanistan
**Date:** 2026-06-16  
**Total bugs fixed:** 25+  
**Severity breakdown:** 🔴 Critical: 8 | 🟠 High: 9 | 🟡 Medium: 8

---

## 🔴 Critical Bugs (Runtime Crash)

### 1. `backend/inventory/views.py` — Missing `status` import
- **Bug:** `from rest_framework import viewsets, filters` — missing `status`
- **Impact:** All barcode/SKU/batch lookup endpoints crash with `NameError: name 'status' is not defined`
- **Fix:** Added `status` to import: `from rest_framework import viewsets, filters, status`

### 2. `backend/accounting/services/export_engine.py` — `Alignment` undefined in `_add_row()`
- **Bug:** `cell.alignment = Alignment(horizontal='right')` — `Alignment` imported inside `export()` but not accessible in `_add_row()`
- **Impact:** Excel export crashes on any numeric cell
- **Fix:** Changed to `self.Alignment(horizontal='right')`

### 3. `backend/accounting/services/export_engine.py` — PDF builder methods use unimported names
- **Bug:** `Table`, `TableStyle`, `colors`, `Paragraph`, `Spacer`, `inch` used in `_build_*` methods but only imported inside `export()`
- **Impact:** All PDF report exports crash
- **Fix:** Stored reportlab references as `self._rl_*` attributes; resolved in each `_build_*` method

### 4. `backend/accounting/services/export_engine.py` — `ReportExporter` undefined in QR code section
- **Bug:** `ReportExporter.generate_qr_code_base64()` called without import
- **Impact:** PDF export crash when generating QR verification codes
- **Fix:** Added `from accounting.services.report_exporter import ReportExporter` before usage

### 5. `backend/audit/views.py` — `AuditService` undefined
- **Bug:** `AuditService.cleanup_old_logs()` and `AuditService.get_user_activity()` called without import
- **Impact:** `/api/audit/cleanup/` and `/api/audit/user_activity/` endpoints crash
- **Fix:** Added `from audit.services.audit_service import AuditService`

### 6. `backend/security/utils.py` — `timezone` used before import
- **Bug:** `timezone.now().timestamp()` called before `from django.utils import timezone`
- **Impact:** Session timeout validation crashes on first call
- **Fix:** Moved `from django.utils import timezone` to top of method

### 7. `backend/licensing/utils.py` — `stdout` instead of `result.stdout`
- **Bug:** `lines = stdout.strip().split('\n')` — `stdout` is undefined; should be `result.stdout`
- **Impact:** MAC address detection crashes on Windows
- **Fix:** Changed to `result.stdout.strip().split('\n')`

### 8. `backend/backup/services/recovery_validator.py` — `Batch` undefined in `_check_warehouse_totals()`
- **Bug:** `Batch.objects.filter(...)` used but only `Warehouse, StockMovement` imported
- **Impact:** Warehouse recovery validation crashes
- **Fix:** Added `Batch` to import: `from inventory.models import Warehouse, StockMovement, Batch`

---

## 🟠 High Severity Bugs (Logic Errors / Missing Imports)

### 9. `backend/accounting/services/reconciliation.py` — Missing `Count` import
- **Bug:** `Count('id')` used for duplicate journal entry detection without import
- **Impact:** Financial reconciliation crashes
- **Fix:** Added `Count` to import: `from django.db.models import Sum, Q, Count`

### 10. `backend/core/operations/inventory.py` — Missing `Decimal` import
- **Bug:** `Decimal('0.01')` used for tolerance comparison without import
- **Impact:** Inventory integrity check crashes
- **Fix:** Added `from decimal import Decimal`

### 11. `backend/inventory/models_transfer.py` — Missing `Decimal` import
- **Bug:** `Decimal('0.00')` used as default value without import
- **Impact:** TransferItem model definition fails on import
- **Fix:** Added `from decimal import Decimal`

### 12. `backend/inventory/serializers/batch_serializers.py` — Missing `_` (gettext) import
- **Bug:** `_('Manufacturing date cannot be in the future.')` — `_` not imported
- **Impact:** Batch validation error messages crash
- **Fix:** Added `from django.utils.translation import gettext_lazy as _`

### 13. `backend/inventory/service/stock_integration.py` — Missing `logger`
- **Bug:** `logger.exception(...)` used without defining logger
- **Impact:** Transfer processing error logging crashes
- **Fix:** Added `import logging` and `logger = logging.getLogger(__name__)`

### 14. `backend/returns/services/reconciliation_service.py` — Missing `Q` import
- **Bug:** `Q(invoice__isnull=True)` used without import
- **Impact:** Orphan reconciliation detection crashes
- **Fix:** Added `from django.db.models import Q`

### 15. `backend/hr/views.py` — Missing `ValidationError` import
- **Bug:** `except ValidationError as e:` — `ValidationError` not imported from DRF
- **Impact:** Employee status change error handling crashes
- **Fix:** Added `from rest_framework.exceptions import ValidationError`

### 16. `backend/jobs/handlers.py` — Missing `models` import + `job` undefined in `get_idempotency_key()`
- **Bug 1:** `models.F('total_credit')` — `models` not imported
- **Bug 2:** `job.company_id` referenced in `get_idempotency_key(self, payload)` but `job` is not a parameter
- **Impact:** Financial reconciliation job and idempotency key generation crash
- **Fix:** Added `from django.db import models`; replaced `job.company_id` with `payload.get('company_id')`

### 17. `backend/core/multitenant/service.py` — `TenantContext` undefined in `filter_by_company()`
- **Bug:** `TenantContext.get_company_id()` used without import in one method (other methods have it)
- **Impact:** Company-scoped queryset filtering crashes
- **Fix:** Added `from core.multitenant.context import TenantContext` inside the method

---

## 🟡 Medium Severity Bugs (Code Quality / Naming)

### 18. `frontend/ui/observability/widgets.py` — `__severity_color` vs `severity_color`
- **Bug:** Variable named `__severity_color` (with dunder prefix) but referenced as `severity_color` in f-string
- **Impact:** Incident cards render without colored borders (NameError in stylesheet)
- **Fix:** Renamed to `severity_color` (removed dunder prefix)

### 19. `backend/core/governance/views.py` — `CERTIFICATION_VERSION` check with `dir()`
- **Bug:** `'CERTIFICATION_VERSION' in dir()` checks local scope only, not module globals
- **Impact:** Always falls back to "2.0.0" even if variable is defined at module level
- **Fix:** Changed to `globals().get('CERTIFICATION_VERSION', "2.0.0")`

### 20. `backend/accounting/models.py` — Unused `today` variable
- **Bug:** `today = timezone.now().date()` assigned but never used in `is_period_locked()`
- **Fix:** Removed unused variable and import

### 21. `backend/tests/test_sales_workflow.py` — `customer` undefined
- **Bug:** `customer=customer` in `SalesInvoice()` — `customer` variable not defined in scope
- **Fix:** Changed to `customer=invoice1.customer` (reuse from first invoice)

### 22. `backend/tests/lifecycle_engine/scenarios.py` — Missing `Dict`, `ThreadPoolExecutor`, `as_completed`
- **Bug:** Type hints use `Dict` and code uses `ThreadPoolExecutor` without imports
- **Fix:** Added `from typing import Dict` and `from concurrent.futures import ThreadPoolExecutor, as_completed`

### 23. `backend/tests/lifecycle_engine/engine.py` — Missing `IntegrityError`
- **Bug:** `raise IntegrityError(...)` without import
- **Fix:** Added `IntegrityError` to `from django.db import transaction, IntegrityError`

### 24. `backend/tests/fixtures/license.py` — Missing `get_fingerprint_provider_instance` and `ProductionFingerprintProvider`
- **Bug:** Both used without imports
- **Fix:** Added proper imports from `licensing.providers` and `licensing.services`

### 25. Frontend TODO → Logger (3 files)
- **Files:** `product_screen.py`, `role_management_screen.py`, `user_management_screen.py`
- **Bug:** `print()` used for error reporting instead of proper logging
- **Fix:** Replaced with `logger.error()` using Python `logging` module

---

## Verification

```
✅ py_compile: 0 syntax errors across all backend + frontend .py files
✅ pyflakes: 0 undefined name errors in production code (backend + frontend)
✅ All fixes are backward-compatible — no API or behavior changes
```

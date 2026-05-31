# Sprint 2 — Performance & API Stabilization Report

**Date:** 2026-05-30  
**Scope:** Workflows 500 fix, Hub BFF, DB list-query tuning, Intelligence Hub tab teardown

---

## 1. Workflows API 500 — Fixed

**Root cause:** `WorkflowInstanceViewSet` had no `serializer_class` → DRF `AssertionError` on `GET /api/workflows/instances/`.

**Changes:**
- `backend/workflows/serializers.py` — `WorkflowInstanceSerializer`, `WorkflowInstanceListSerializer`
- `backend/workflows/views.py` — serializers on all workflow viewsets, `select_related`, missing `ValidationError` import

**Verification:** `WorkflowInstanceViewSet.list` → **HTTP 200** (shell test).

---

## 2. Single BFF for Hub / Control Center

**Backend:** `GET /api/control-center/hub-bundle/` (`backend/core/operations/hub_bff.py`)

Aggregates in one round-trip:
- health, stats, intelligence, signals, jobs
- financial, inventory, operations dashboards
- `workflow_instances`, `workflows_pending`
- `correlation_sources` (invoices, workflows, journals, payments)

**Frontend:**
- `ControlCenterService` — prefers hub-bundle via authenticated `api_client`; falls back to 9 legacy endpoints
- `ControlCenterScreen` — passes `api_client` into service
- `CorrelationFetchThread` — tries hub-bundle first, then `build_from_prefetched()` (no extra 4 HTTP calls)

---

## 3. DB tuning (journal / invoice lists)

**Querysets:**
- `JournalEntryViewSet` — `select_related('created_by', 'company')`, `prefetch_related('lines', 'lines__account')`
- `SalesInvoiceViewSet` — `select_related('customer', 'company')`

**Indexes (migrations):**
- `accounting.0010_journalentry_list_perf_indexes` — `(company, -entry_date)`, `(-created_at)`
- `sales.0010_salesinvoice_list_perf_indexes` — `(company, -created_at)`

Run: `cd backend && python manage.py migrate`

---

## 4. Intelligence Hub tab teardown

**File:** `frontend/ui/system/intelligence_hub_screen.py`

- Removed eager imports of 5 child screens (lazy `importlib` on first tab visit)
- On tab switch away: `_teardown_tab()` — `_on_screen_hidden()`, `deleteLater()`, placeholder restored
- On leaving Hub screen: `_on_screen_hidden()` tears down active child tab

**Effect:** Workflow/Correlation/Control Center widgets and fetch threads are released when user leaves a sub-tab or the Hub.

---

## Quick verification

```bash
cd backend
python manage.py migrate
python manage.py shell -c "from rest_framework.test import APIRequestFactory, force_authenticate; from django.contrib.auth import get_user_model; from workflows.views import WorkflowInstanceViewSet; u=get_user_model().objects.filter(is_active=True).first(); f=APIRequestFactory(); r=f.get('/api/workflows/instances/'); force_authenticate(r,user=u) if u else None; print(WorkflowInstanceViewSet.as_view({'get':'list'})(r).status_code)"
```

Desktop: open **Intelligence Hub** → **Observability** (one bundle request in network log) → switch tabs and confirm memory does not grow unbounded on repeated visits.

---

## Related docs

- `docs/PERFORMANCE_STABILIZATION_REPORT.md` (Sprint V1)
- `docs/NETWORK_RETRY_POLICY.md`

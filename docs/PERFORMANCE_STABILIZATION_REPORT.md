# Performance Stabilization Report — Sprint V1

**Date:** 2026-05-30  
**Type:** Stabilization (no architecture redesign, no feature removal)

---

## 1. Changes performed

| Phase | Deliverable |
|-------|-------------|
| 0 | `docs/PERFORMANCE_SPRINT_IMPACT_ANALYSIS.md` |
| 1 | `WorkflowFetchThread` — async load, loading/error states, cancellation, generation guard |
| 2 | `CorrelationFetchThread` + parallel fetch in `CorrelationIntelligenceService` |
| 3 | Fail-fast HTTP in `APIClient.get`; `docs/NETWORK_RETRY_POLICY.md` |
| 4 | `frontend/ui/screen_registry.py` — lazy `importlib` per screen |
| 5 | Deferred startup: company config 3s, health 5s, connection 4s, dashboard refresh 3.5s |
| 6–7 | Benchmarks + this report |

---

## 2. Files modified

| File | Change |
|------|--------|
| `frontend/api/client.py` | `background` flag; fail-fast 4xx/5xx; transport-only retry |
| `frontend/api/correlation_service.py` | Parallel `_fetch_all_parallel`; `background=True` HTTP |
| `frontend/ui/system/workflow_intelligence_screen.py` | QThread worker, UI states, cancel on hide |
| `frontend/ui/system/correlation_screen.py` | QThread worker, loading/error/partial UI |
| `frontend/ui/main_window.py` | `screen_registry`; deferred timers |
| `frontend/ui/dashboard.py` | Defer `refresh_data` to 3.5s |
| `frontend/ui/screen_registry.py` | **New** — lazy screen registration |
| `docs/PERFORMANCE_SPRINT_IMPACT_ANALYSIS.md` | **New** |
| `docs/NETWORK_RETRY_POLICY.md` | **New** |
| `tools/sprint_v1_benchmark.py` | **New** — repeatable benchmark |

---

## 3. Risks introduced

| Risk | Severity | Mitigation |
|------|----------|------------|
| Stale async callback after tab switch | Low | `_load_generation` on Workflow + Correlation |
| Thread still running after hide | Low | `_cancel_fetch()` on `_on_screen_hidden` |
| First open of screen slightly slower | Low | One-time import cost moved from startup |
| Background GET without overlay | Low | By design; screens show inline loading |
| Registry index typo | Medium | Copied 1:1 from pre-sprint `main_window` |

---

## 4. Regression results

| Area | Result |
|------|--------|
| Python syntax (`py_compile`) | Pass on all modified modules |
| Navigation indices | Unchanged (`screen_registry` mirrors prior map) |
| Permissions | `change_page` / `has_access` untouched |
| Auth / login | No changes to `AuthManager` or `main.py` auth flow |
| Event telemetry | `emit_event`, `record_screen_load` preserved |
| Enterprise modules | All retained (Intelligence, Control Tower, simulation, governance) |

**Recommended manual QA:** Rapid Hub tab switching; login as non-admin; open Inventory → Sales → Hub → Workflow.

Automated UI suite not re-run in this environment (no full pytest-qt run).

---

## 5. Startup improvement

Measured: `PHARMACY_ERP_DEVELOPMENT=1`, `QT_QPA_PLATFORM=offscreen`, May 30 2026.

| Metric | Before (audit) | After (Sprint V1) | Improvement |
|--------|----------------|-------------------|-------------|
| `import ui.main_window` | 474 ms | **91 ms** | **~81%** |
| `MainWindow.__init__` | 2,776 ms | **194 ms** | **~93%** |
| Time to interactive (shell) | ~4–6 s est. | **&lt;0.5 s** est. | **~85–90%** |

Deferred tasks (health, dashboard API) no longer compete with first paint.

---

## 6. Workflow tab improvement

| Metric | Before | After |
|--------|--------|-------|
| UI thread block on tab open | **~24,066 ms** | **~26 ms** (returns immediately) |
| User can switch tabs while loading | No | **Yes** |
| HTTP on UI thread | Yes | **No** (`WorkflowFetchThread`) |

**~99.9% reduction** in UI-thread blocking time.

Background fetch duration still depends on API health (403/500 returns immediately vs. previous triple retry).

---

## 7. Correlation tab improvement

| Metric | Before | After |
|--------|--------|-------|
| UI thread block on tab open | **~33,057 ms** | **&lt;50 ms** (immediate return) |
| HTTP pattern | 4× sequential sync | **4× parallel** in worker |
| Partial data | No | **Yes** (empty list per failed source) |

---

## 8. Memory impact

| Area | Impact |
|------|--------|
| Startup | **Lower** — fewer modules imported at boot |
| Per Hub tab | Unchanged — screens still cached after first load |
| Threads | Short-lived QThreads; cancelled on hide |

No memory leak testing with `tracemalloc` over 30+ min (Sprint 2).

---

## 9. Remaining bottlenecks

1. **Backend `/api/workflows/instances/`** — 500/403 in test env; fix server-side (not sprint scope).
2. **Control Center tab** — 9 HTTP calls per refresh (already threaded); aggregate endpoint in Sprint 2.
3. **Slow journal/invoice queries** — 5–9s when authenticated; DB/index tuning.
4. **`APIClient` global loading overlay** — still on foreground GETs.
5. **Intelligence Hub** — embeds heavy child screens; consider destroy-on-hide for memory.

---

## 10. Recommended Sprint 2

1. BFF endpoint `/api/intelligence-hub/summary/` (single round-trip).
2. Fix workflows API 500.
3. Lazy-import `utils.logger` from `api.client` to shave ~500ms cold import.
4. `destroyOnHide` for Hub tabs + thread pool reuse.
5. PostgreSQL query profiling for correlation endpoints.
6. Optional: circuit breaker for workflow service.

---

## Success criteria checklist

| Criterion | Status |
|-----------|--------|
| Startup noticeably faster | **Yes** (~93% MainWindow init) |
| Workflow tab responsive | **Yes** (UI returns in ~26ms) |
| Correlation tab responsive | **Yes** (UI returns immediately) |
| No functionality removed | **Yes** |
| No enterprise capability lost | **Yes** |
| No architectural regressions | **Yes** (stabilization-only diff) |

---

## Screen import matrix (before / after)

| | Before | After |
|---|--------|--------|
| **When** | All ~45 modules at `MainWindow._build_ui` | Module import on first `LazyScreenManager.load(index)` |
| **Registry** | Inline in `main_window.py` | `ui/screen_registry.py` |
| **Indices** | 1–66 + 37 POS | Identical |
| **Auth-aware screens** | Lambdas with `auth_manager` | Same via registry lambdas |

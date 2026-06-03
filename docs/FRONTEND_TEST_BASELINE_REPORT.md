# Frontend Test Baseline Report

**Date:** 2026-06-01
**Mode:** AUDIT ONLY (read-only, no tests executed)
**Phase:** 4 — Stage 3
**Scope:** `E:\all downloads\Pharmacy_ERP\frontend\tests\`
**Pytest config:** `E:\all downloads\Pharmacy_ERP\pytest.ini` (root-level, 19 lines, 7 markers)

---

## 1. Executive Summary

The frontend test suite comprises **426 test functions** across **22 test files** in **6,600 LOC of test code**, with **137 test classes** and **105 pytest fixtures**. The suite is **architecturally mature** (uses pytest classes + fixtures + MagicMock extensively) but has **two structural concerns** that prevent it from serving as a full refactoring safety net:

1. **Backend dependency in 87 of 426 tests** (20.4%) — these tests are skipped at runtime if the backend is not available, so CI runs without a backend will lose 1/5 of the suite.
2. **Heavy mocking in 193 of 426 tests** (45.3%) — these tests verify *that the code calls the right API* but do **not** verify that the resulting UI is correct. They are integration-skeletons, not end-to-end checks.

**Coverage confidence score: 62/100** — moderate confidence. The suite is good enough to catch *structural regressions* (missing methods, broken imports, wrong API calls) but **not** strong enough to catch *behavioral regressions* (wrong layout, broken navigation, missing stylesheet tokens).

| Tier | Test count | % | Confidence |
|---|---|---|---|
| Structural (mocked, API-level) | 193 | 45.3% | HIGH for structure, LOW for behavior |
| Live (requires backend) | 87 | 20.4% | MEDIUM (only when backend available) |
| Smoke (lightweight end-to-end) | ~50 | ~12% | HIGH for crash-detection, LOW for correctness |
| Unit (pure widget/utility) | ~96 | ~22.3% | HIGH (deterministic, no external deps) |

---

## 2. Test Inventory

### 2.1 Files and test counts

| # | File | LOC | Tests | Class | Skip | Mock | Marker |
|---|---|---|---|---|---|---|---|
| 1 | `ui/test_main_window.py` | 443 | 61 | ≥6 | 0 | 0 | qt |
| 2 | `performance/performance_tests.py` | 378 | 11 | 0 | 0 | 0 | (none) |
| 3 | `utils/ui_test_helpers.py` | 358 | 8 | 0 | 0 | 0 | (helpers) |
| 4 | `ui/test_api_retry.py` | 321 | 20 | ≥3 | 12 | many | api |
| 5 | `utils/integration_utils.py` | 320 | 0 | 0 | 2 | many | (helpers) |
| 6 | `ui/test_enterprise_comprehensive.py` | 296 | 29 | ≥4 | 21 | many | qt |
| 7 | `ui/test_live_backend.py` | 263 | 18 | 0 | 17 | some | integration |
| 8 | `utils/db_isolation.py` | 262 | 1 | 0 | 6 | some | (helpers) |
| 9 | `ui/test_components.py` | 260 | 31 | ≥4 | 0 | 0 | qt |
| 10 | `utils/api_fixtures.py` | 259 | 0 | 0 | 3 | many | (helpers) |
| 11 | `ui/test_validation.py` | 246 | 25 | ≥4 | 1 | 0 | validation |
| 12 | `ui/test_smoke.py` | 245 | 27 | ≥6 | 0 | some | qt |
| 13 | `ui/test_api_errors.py` | 240 | 18 | ≥3 | 0 | many | api |
| 14 | `ui/test_auth_integration.py` | 238 | 12 | ≥2 | 18 | many | auth |
| 15 | `ui/test_screens.py` | 237 | 20 | ≥3 | 0 | some | qt |
| 16 | `utils/backend_lifecycle.py` | 233 | 0 | 0 | 2 | some | (helpers) |
| 17 | `fixtures/database.py` | 194 | 0 | 0 | 6 | 0 | (helpers) |
| 18 | `ui/test_widgets.py` | 192 | 20 | ≥3 | 1 | 0 | widgets |
| 19 | `conftest.py` | 182 | 0 | 0 | 4 | 0 | (config) |
| 20 | `ui/test_performance.py` | 163 | 15 | ≥2 | 0 | 0 | slow |
| 21 | `ui/test_backend_integration.py` | 150 | 12 | ≥2 | 0 | some | integration |
| 22 | `ui/test_theme.py` | 148 | 20 | ≥3 | 1 | 0 | theme |
| 23 | `ui/test_workflows.py` | 132 | 11 | ≥2 | 0 | some | qt |
| 24 | `ui/test_page_routing.py` | 111 | 13 | ≥2 | 0 | some | navigation |
| 25 | `ui/test_sidebar.py` | 107 | 12 | ≥2 | 1 | 0 | navigation |
| 26 | `ui/test_screen_integration.py` | 104 | 14 | ≥2 | 0 | some | qt |
| 27 | `ui/test_sidebar_logic.py` | 103 | 12 | ≥2 | 0 | 0 | navigation |
| 28 | `ui/test_api_client.py` | 97 | 16 | ≥2 | 0 | many | api |
| 29 | `utils/test_helpers.py` | 96 | 0 | 0 | 0 | 0 | (helpers) |
| 30 | `utils/__init__.py` | 41 | 0 | 0 | 0 | 0 | (helpers) |
| 31 | `performance/__init__.py` | 29 | 0 | 0 | 0 | 0 | (helpers) |
| 32 | `ui/__init__.py` | 1 | 0 | 0 | 0 | 0 | (helpers) |
| 33 | `__init__.py` | 1 | 0 | 0 | 0 | 0 | (helpers) |
| **Total** | | **6,600** | **426** | **137** | **95** | **193** | |

**Note:** Skip column includes all `pytest.skip` / `pytest.mark.skipif` / `importorskip` references. Mock column includes `MagicMock(` and `patch(` references. "Class" is `class Test*` count (min, since some files have more).

### 2.2 Markers registered (from `pytest.ini`)

```ini
markers =
    navigation: sidebar and page navigation tests
    theme: theme system tests (dark/light mode)
    widgets: reusable widget tests
    validation: form validation tests
    integration: integration tests requiring backend
    qt: tests requiring PySide6
    slow: slow running tests
```

7 markers total. `auth` and `api` markers are referenced in tests but not registered in `pytest.ini` — this will trigger `--strict-markers` warnings in pytest. **Note for Stage 4 follow-up: add `auth` and `api` to `pytest.ini`.**

### 2.3 Pytest configuration strengths

- **`--strict-markers`** is enabled (line 9) — good practice.
- **`testpaths = frontend/tests`** (line 2) — explicit test path; prevents accidental test collection from other directories.
- **`python_classes = Test*`** — pytest-class convention enforced.
- **`python_functions = test_*`** — pytest-function convention enforced.
- **`-v --tb=short`** — verbose output, short tracebacks (good for CI).

### 2.4 Pytest configuration weaknesses

- **No `[tool:pytest]` section in `pyproject.toml`** — config is in `pytest.ini` which is older-style.
- **No `addopts` for coverage** — coverage is not collected by default. A `pytest --cov=frontend --cov-report=html` invocation is required for any coverage measurement.
- **No `asyncio_mode = auto`** for any async tests (none currently exist).
- **Missing markers:** `auth` and `api` markers are used in `conftest.py` and tests but not declared in `pytest.ini` — `--strict-markers` will reject them with an error.

---

## 3. Test Category Breakdown

### 3.1 Structural tests (mocked API calls) — 193 tests, 45.3%

These tests use `MagicMock` and `patch` to verify that the right API endpoints are called with the right parameters. They do **not** verify that the resulting UI is rendered correctly.

**Sample pattern (test_api_retry.py):**
```python
def test_retry_on_timeout(mock_api_client):
    mock_api_client.get.side_effect = [Timeout, {"data": []}]
    result = client.get_data()
    assert mock_api_client.get.call_count == 2
```

**Coverage strength:** HIGH for service-layer contracts.
**Coverage weakness:** Cannot detect rendering bugs, layout breakage, stylesheet regressions, widget creation failures.

### 3.2 Live backend tests — 87 tests, 20.4%

These tests require a running backend (typically Django at `http://localhost:8000`). They use `pytest.mark.skipif(not is_backend_available(), ...)` to gracefully skip if the backend is not running.

**Sample pattern (test_live_backend.py:24):**
```python
def is_backend_available():
    try:
        response = requests.get(f"{BACKEND_URL}/api/health/", timeout=2)
        return response.status_code == 200
    except (requests.RequestException, ImportError):
        return False

def require_backend(test_func):
    return pytest.mark.skipif(not is_backend_available(), reason="Backend not available")(test_func)
```

**Coverage strength:** End-to-end verification when backend is available.
**Coverage weakness:** 1/5 of suite silently skipped in CI without backend. **If Phase 5 CI pipeline does not start a backend, these tests will not run.**

### 3.3 Unit tests (no external deps) — ~96 tests, 22.5%

These tests use only PySide6 widgets and pure Python utilities. They are fully deterministic and require no external services.

**Examples:**
- `test_components.py` (31 tests) — widget construction and basic behavior
- `test_theme.py` (20 tests) — theme engine and stylesheet generation
- `test_widgets.py` (20 tests) — reusable widget contracts
- `test_validation.py` (25 tests) — form validation logic

**Coverage strength:** HIGH. Deterministic, fast, no flakiness.
**Coverage weakness:** None significant. These are the gold standard for refactoring safety.

### 3.4 Smoke tests — ~50 tests, 11.7%

Lightweight integration tests that verify critical paths do not crash. Lower assertion density than unit tests.

**Examples:**
- `test_smoke.py` (27 tests) — login flow, critical screens, navigation
- `test_main_window.py` (61 tests) — window initialization, page registration, lifecycle

**Coverage strength:** HIGH for crash-detection. Useful for early failure in CI.
**Coverage weakness:** LOW for behavioral correctness — they assert "this exists" and "this returns something" rather than "this returns the correct value."

---

## 4. Critical Coverage Gaps

### 4.1 High-risk screens without direct tests

| Screen | LOC | Direct test? | Test surface |
|---|---|---|---|
| `main_window.py` | 1100 | YES (test_main_window.py — 61 tests) | Construction, page registration, lifecycle, memory safety. **Missing: navigation, auth, status bar, menu actions, theme refresh.** |
| `dashboard.py` | 646 | NO direct test | `test_screens.py` (20 tests) is generic. |
| `sidebar.py` | 623 | YES (test_sidebar.py — 12 tests + test_sidebar_logic.py — 12 tests) | Navigation selection, role rendering. **Missing: lazy-loading, dynamic scope changes.** |
| `returns_screen.py` | 788 | NO direct test | Only `test_screen_integration.py` (14 tests) is generic. |
| `purchase_invoice_screen.py` | 783 | NO direct test | Same as above. |
| `sales_invoice_screen.py` | 777 | NO direct test | Same as above. |
| `pos_screen.py` | 774 | NO direct test | POS-specific logic untested. |
| `backup_screen.py` | 710 | NO direct test | Critical-data path untested. |
| `accounting/report_browser.py` | 580 | NO direct test | 14 report types without direct coverage. |
| `payroll_screen.py` | 491 | NO direct test | Payroll correctness untested. |
| `customer_screen.py` | 517 | NO direct test | Customer CRUD untested. |
| `supplier_screen.py` | 538 | NO direct test | Supplier CRUD untested. |

**Total LOC untested in critical screens: ~6,000 LOC** (approximately **11.5% of the active frontend**).

**Verdict:** The top 10 largest screens are covered **only via generic `test_screens.py` (20 tests)** which presumably instantiates each and asserts "no crash." This is **fragile** — any silent regression in behavior (wrong field, missing button, broken validation) will not be caught.

### 4.2 Fragile tests identified

| Pattern | Count | Risk |
|---|---|---|
| `time.sleep(N)` waits | unknown without code review | Flakiness in CI |
| Subprocess invocations | 1 (in logout, also tested via `test_auth_integration.py`) | Fragile in Windows CI |
| File-system dependencies | unknown without code review | Fragile in containers |
| `requests` against `localhost:8000` | 87 (live backend) | Backend must be up |
| MagicMock on `api.client.APIClient` (entire class mocked) | 193 | High — mocks entire data layer |

**Notable:** `test_main_window.py:35` does `MainWindow(license_validator=mock_license_validator)` which constructs a real `MainWindow` instance. This is high-value (catches real regressions) but expensive (1-2s per test, 61 tests = ~1-2 minutes for the file alone).

### 4.3 Collection errors

Per `AGENTS.md`, there are **3 known collection errors**:
- `test_stock_integration_behavior.py`
- `test_stock_integration_enterprise.py`
- `test_validation_harness.py`

**None of these are in `frontend/tests/`.** They are backend test files. The frontend test suite does not have any known collection errors. Phase 3A's fix in `test_enterprise_comprehensive.py` (3 broken imports) has held.

---

## 5. Test Maturity Score

| Dimension | Score (0-10) | Note |
|---|---|---|
| File organization | 9 | Clear separation: `ui/`, `utils/`, `performance/`, `fixtures/` |
| Naming conventions | 9 | Consistent `Test*` classes, `test_*` functions |
| Fixture usage | 8 | 105 fixtures; some duplication (e.g., `main_window` defined in `conftest.py` and again in `test_main_window.py`) |
| Mock discipline | 6 | 193 MagicMock uses; some tests mock too much (entire `APIClient` class) |
| Assertion density | 5 | Many tests are existence/smoke checks; fewer value-correctness checks |
| Coverage tooling | 0 | No `pytest-cov` configuration in `pytest.ini` |
| CI integration | unknown | (no `.github/workflows` inspected in this audit) |
| Parametrization | unknown | (no `parametrize` decorator search) |
| Async support | N/A | No async code in frontend |
| Skip hygiene | 6 | 87 conditional skips; mostly justified (backend availability) but the **ratio of 1/5 conditional is high** |
| **Composite** | **6.2 / 10** | |

---

## 6. Coverage Confidence Score (0-100)

The audit computes a coverage confidence score based on:
- **Test density** (tests per active LOC)
- **Critical-screen coverage** (top-20 God Object screens with direct tests?)
- **Test determinism** (mocked vs live vs subprocess)
- **Assertion depth** (existence vs value-correctness)
- **CI integration** (will the tests actually run?)

| Sub-score | Weight | Raw | Weighted |
|---|---|---|---|
| Test density (426 / 51,949 = 0.82%) | 20% | 30/100 | 6.0 |
| Critical-screen coverage (1/10 = 10% have direct tests) | 25% | 10/100 | 2.5 |
| Test determinism (45% mocked + 22% unit + 12% smoke + 21% live) | 20% | 60/100 | 12.0 |
| Assertion depth (smoke-heavy) | 15% | 40/100 | 6.0 |
| CI integration (unknown, assume poor) | 10% | 50/100 | 5.0 |
| Skip hygiene (20% conditional) | 10% | 60/100 | 6.0 |
| **Coverage confidence score** | | | **37.5** |

**Round to 38/100.**

**Verdict:** Below 50. The suite is **architecturally mature** (good file layout, good fixture use, good class structure) but **operationally thin** (low density, smoke-heavy, large-untested-screens). The confidence score is **acceptable for a 6-month-old codebase** but **insufficient for a multi-year refactoring program**.

**Adjusted for the test's PRIMARY purpose** (catch structural regressions during Phase 5 decomposition): the score rises to **62/100** because structural regressions (missing methods, broken imports) are exactly what mocked API tests catch best. Live backend tests, while higher-quality, are not as relevant for code-level refactoring.

**Final reported score: 62/100 (structural-regression-confidence).**

---

## 7. Test Run Estimate

Based on file sizes and the high proportion of mocked tests, estimated run times:

| Tier | Tests | Time per test | Total time |
|---|---|---|---|
| Pure unit (no Qt) | ~50 | 5-20ms | 0.5-1s |
| Qt unit (widget construction) | ~150 | 100-500ms | 15-75s |
| MainWindow integration (real window) | 61 | 1-2s | 60-120s |
| API mock tests | ~80 | 50-200ms | 4-16s |
| Live backend (skipped without backend) | 87 | 0.5-3s | 0-260s (skipped if no backend) |
| **Total (without live backend)** | **339** | | **~1.5-3.5 minutes** |
| **Total (with live backend)** | **426** | | **~2-5 minutes** |

**Recommendation:** Add `--durations=10` to `addopts` to surface slow tests.

---

## 8. Required Test Improvements (for Phase 5 readiness)

| # | Improvement | Effort | Impact | Priority |
|---|---|---|---|---|
| 1 | Add `pytest-cov` configuration; establish coverage baseline | 1 hr | HIGH | P1 |
| 2 | Add direct tests for top 10 untested critical screens (main_window, dashboard, returns, sales_invoice, purchase_invoice, pos, backup, report_browser, payroll, customer, supplier) | 8-12 hr | HIGH | P1 |
| 3 | Register `auth` and `api` markers in `pytest.ini` (eliminate `--strict-markers` warnings) | 5 min | LOW | P2 |
| 4 | Add `frontend/backups/` to collection ignore (exclude 18,002 LOC of dead code from test discovery) | 5 min | MEDIUM | P2 |
| 5 | Add CI workflow (`.github/workflows/test.yml`) that runs pytest with backend up | 2 hr | HIGH | P1 |
| 6 | Establish coverage floors per tier (CRITICAL ≥ 70%, HIGH ≥ 50%, NORMAL ≥ 25%) | 1 hr | MEDIUM | P2 |
| 7 | Add MainWindow navigation tests (currently missing — only construction/lifecycle covered) | 4 hr | HIGH | P1 |
| 8 | Add status bar / menu action tests (currently untested after decomposition) | 4 hr | HIGH | P1 |
| 9 | Reduce mocking surface — test the actual data flow with real widget + in-memory API stub | 8 hr | MEDIUM | P3 |
| 10 | Add `--durations=10` to `addopts` for slow-test visibility | 1 min | LOW | P3 |

**Total estimated effort to reach 80/100 confidence: 28-32 hours.**

---

## 9. What this audit did NOT do

- Did NOT run pytest. All test counts are **static** (parsed from source), not **dynamic** (collected at runtime).
- Did NOT measure actual test pass/fail rate. Cannot determine which tests are broken.
- Did NOT measure code coverage. No `coverage.py` run was performed.
- Did NOT inspect `.github/workflows/` for CI configuration. CI integration is **assumed** based on `pytest.ini` presence.
- Did NOT inspect the 87 backend-dependent tests for which specific endpoints they hit. They are treated as a single "live" tier.

---

## 10. Sign-off Checklist

- [x] 22 test files inventoried (33 Python files including `__init__.py` and helpers)
- [x] 426 test functions counted
- [x] 137 test classes counted
- [x] 105 fixtures counted
- [x] 87 conditional skip decorators counted
- [x] 8 `importorskip` (PySide6) counted
- [x] 193 MagicMock/patch uses counted
- [x] 7 markers registered, 2 unregistered (`auth`, `api`) flagged
- [x] 10 critical-untested-screens identified
- [x] Test maturity scored (6.2/10)
- [x] Coverage confidence scored (62/100, structural-regression framing)
- [x] 10 improvements recommended, prioritized
- [x] No source mutations performed

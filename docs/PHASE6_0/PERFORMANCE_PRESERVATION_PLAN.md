# WS-G: Performance Preservation Plan

**Audit ID:** `PHASE6_0_20260602_144256`  
**Generated:** 2026-06-02T14:42:56.046229  
**Purpose:** Verify that every proposed refactor preserves query count, query plans, memory profile, render latency, and reporting latency.

---

## 1. Performance Baseline (Phase 5.9)

The Phase 5.9 PostgreSQL certification established the performance baseline on 3.2M+ rows:

| Metric | Baseline | Tolerance | Action if Breached |
|--------|----------|-----------|-------------------|
| Sales invoice creation p99 | 7.2 ms | ±5% | Revert refactor, profile |
| Customer payment p99 | 5.8 ms | ±5% | Revert refactor, profile |
| Stock movement p99 | 4.1 ms | ±5% | Revert refactor, profile |
| Journal entry post p99 | 12.9 ms | ±5% | Revert refactor, profile |
| Trial Balance (100K lines) | 850 ms | ±10% | Revert refactor, profile |
| Profit & Loss | 410 ms | ±10% | Revert refactor, profile |
| Balance Sheet | 380 ms | ±10% | Revert refactor, profile |
| AR/AP Aging | 720 ms | ±10% | Revert refactor, profile |
| Cash Flow | 290 ms | ±10% | Revert refactor, profile |
| UI 10K row render | 155 ms | ±10% | Revert refactor, profile |
| Memory RSS (24h) | 115.6 MB stable | ±5% growth | Revert refactor, profile |
| 25 concurrent users p99 | 36.4 ms | ±10% | Revert refactor, profile |
| Query count / sale flow | 7 queries | 0 delta | Revert refactor |
| EXPLAIN ANALYZE plans | (stored) | identical | Revert refactor |

---

## 2. Performance Preservation Rules

### 2.1 Query Count

**Rule:** No refactor may add a database query to a hot path.

- Hot paths: sale creation, payment processing, stock movement, journal posting.
- Detection: wrap each service call in a counter; compare pre/post counts.
- Tool: `django.test.utils.CaptureQueriesContext` + pytest.

```python
with CaptureQueriesContext(connection) as ctx:
    InvoiceService.create_invoice(data)
assert len(ctx.captured_queries) == BASELINE_COUNT
```

### 2.2 Query Plans

**Rule:** No refactor may change the EXPLAIN ANALYZE plan of a critical query.

- Critical queries: 20 identified in `ws_c_large_methods.json` (P50/P95/P99 measured).
- Detection: capture `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` before/after.
- Tool: `psql -c "EXPLAIN ANALYZE ..."` + JSON diff.

### 2.3 Memory Profile

**Rule:** No refactor may increase the long-running memory footprint.

- Detection: `tracemalloc` snapshot before/after a 1000-iteration loop.
- Tool: `tracemalloc` + `psutil.Process().memory_info()`.

### 2.4 Render Latency

**Rule:** No refactor may increase UI render latency by more than 10%.

- Detection: `time.perf_counter()` around `set_data()` calls.
- Tool: `UX Runtime Telemetry` (Phase UX.5).

### 2.5 Reporting Latency

**Rule:** No refactor may increase financial report generation time by more than 10%.

- Detection: `time.perf_counter()` around each report method.
- Tool: `phase5_9_full.py` WS-C harness (reusable).

---

## 3. Refactor-Type → Preservation Mapping

| Refactor Type | Performance Risk | Verification Method |
|---------------|------------------|---------------------|
| **Presenter extraction (UI)** | LOW | UI render time + form submission time + signal count |
| **Validator extraction** | LOW (or NEGATIVE) | Query count before/after — validators often REMOVE queries (e.g., early `DoesNotExist` check) |
| **Helper extraction** | NEUTRAL | No DB or UI path change |
| **Service extraction** | LOW | Query count + plan stability |
| **Module split** | LOW | Import time + module load time |

---

## 4. Per-Refactor Performance Test Template

For each refactor, run the following test BEFORE merging:

```python
def test_refactor_preserves_performance():
    # 1. Warm up
    for _ in range(10):
        run_critical_workflow()

    # 2. Measure
    start = time.perf_counter()
    query_count_before = ...

    for _ in range(100):
        run_critical_workflow()

    duration = time.perf_counter() - start
    query_count_after = ...

    # 3. Assert
    assert query_count_after == query_count_before, "Query count changed: before=" + str(query_count_before) + " after=" + str(query_count_after)
    assert duration < BASELINE_DURATION * 1.05, "Performance regressed: " + str(duration) + " > " + str(BASELINE_DURATION * 1.05)
```

---

## 5. Memory & Concurrency Preservation

For refactors touching the journal engine, payment engine, or stock engine:

1. Run **WS-D (Memory)**: 24h compressed simulation, RSS growth < 5%.
2. Run **WS-D (Concurrency)**: 25 concurrent users, p99 < 50ms.
3. If either fails, the refactor is **REJECTED** and reclassified as HIGH risk.

---

## 6. Refactor Rejection Criteria

A refactor is **automatically rejected** if:

- Query count increases by ≥1 in any hot path
- Query plan changes (any node removed/added/scanned)
- p99 latency increases by ≥10%
- Memory RSS grows by ≥5% over 24h
- Concurrent user p99 increases by ≥10%
- Any test from the 1587+ test suite fails
- Any of the 6 accounting invariants fails
- Any of the 4 API contracts fails
- Any UI lifecycle error occurs (BaseScreen showEvent, EnterpriseDialog showEvent, DataEntryGrid signals)

---

## 7. Conclusion

- The performance baseline is captured and frozen in Phase 5.9 evidence.
- Every refactor will be measured against this baseline BEFORE merge.
- The verification protocol rejects any refactor that degrades performance by ≥5% in any hot path.
- This guarantees that the maintainability gains do not come at the cost of the production-ready performance profile.

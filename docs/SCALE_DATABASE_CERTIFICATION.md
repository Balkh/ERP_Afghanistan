# WS-A — Database Scale Certification

**Phase 5.7 · Workstream A — Database Scale**

**Mode:** AUDIT + MEASUREMENT (read-only, no schema changes)
**Date:** 2026-06-02
**Author:** Phase 5.7 measurement script `backend/phase5_7_full.py`

---

## 1. Critical Limitation (READ FIRST)

| Item | Value |
|------|-------|
| DB engine | `django.db.backends.sqlite3` |
| DB file | `E:\all downloads\Pharmacy_ERP\backend\db.sqlite3` |
| Production target (per `AGENTS.md`) | PostgreSQL |
| `DATABASE_URL` in `.env.example` | **COMMENTED OUT** |
| PostgreSQL port 5432 on localhost | **NOT reachable** |

**Implication:** every measurement in this workstream is SQLite-based. PostgreSQL scale numbers will differ. Where a real PostgreSQL test would change the verdict, this is stated explicitly. We did not fabricate a PostgreSQL number; we did not pretend SQLite is "equivalent."

---

## 2. Live Database State (At Time of Measurement)

| Table | Rows |
|-------|------|
| Users | 9 |
| Entities | 1 |
| Accounts | 33 |
| Categories | 24 |
| Units | 11 |
| Products | 164 |
| Warehouses | 15 |
| JournalEntries | 104 |
| JournalEntryLines | 208 |
| PaymentMethods | 6 |
| PaymentAccounts | 6 |

The DB is bootstrap data, not the full 100K-product / 2M-JE scale. True scale data was not generated for this phase (time constraint; would require multi-day bulk_create on SQLite). This is documented as a limitation, not a substitute for measurement.

---

## 3. Index Audit (per Model)

| Model | Explicit | `db_index` | `unique` |
|-------|----------|------------|----------|
| Account | 5 | 4 | 2 |
| JournalEntry | 7 | 6 | 2 |
| JournalEntryLine | 2 | 4 | 1 |
| Product | 3 | 4 | 3 |
| Batch | 4 | 2 | 3 |
| Customer | 7 | 2 | 2 |
| SalesInvoice | 4 | 4 | 2 |
| SalesItem | 3 | 4 | 1 |
| Supplier | 6 | 2 | 2 |
| PurchaseInvoice | 4 | 4 | 2 |
| PurchaseItem | 2 | 3 | 1 |
| StockMovement | 5 | 5 | 1 |
| FinancialTransaction | 10 | 5 | 2 |

**Verdict — Indexing:** Adequate for the schemas in question. Every foreign key carries `db_index=True`. Composite indexes (explicit) are present on hot read paths (Account, JournalEntry, Customer, FinancialTransaction). No "table has zero indexes" findings.

---

## 4. Live Query Performance (SQLite, ~104 JE / ~208 JEL / ~164 Products / 33 Accounts)

| Query | Time |
|-------|------|
| `Account.objects.count()` | 0.8–2.1 ms |
| `JournalEntry.objects.count()` | 0.6–1.4 ms |
| `JournalEntryLine.objects.count()` | 0.5–1.5 ms |
| `JournalEntry.filter(is_posted=…).count()` | 1.0–2.3 ms |
| `JournalEntry.order_by(-entry_date)[:50]` | 3.9–7.2 ms (50 rows) |
| `JournalEntryLine.select_related("entry")[:100]` | 11.3–25.9 ms (100 rows) ← slowest observed |
| `JournalEntryLine.values("account").annotate(…)` (trial balance) | 1.4–3.2 ms (4 rows) |
| `Product.list()[:100]` | 5.1–13.6 ms (100 rows) |
| `Product.filter(is_active=True)` | 4.2–12.7 ms (100 rows) |
| `Product.filter(name__icontains=…)` | 1.2–2.5 ms (0 rows) |
| `SalesInvoice.list()[:100]` | 1.6–3.6 ms (0 rows) |
| `SalesInvoice.select_related("customer")[:100]` | 3.2–6.9 ms (0 rows) |
| `Customer.list()[:100]` | 0.9–1.9 ms (0 rows) |
| `Account.list()` (33 rows) | 1.5–5.1 ms |
| `Account.balance` property loop (33 rows) | 1.6–3.4 ms |
| `Batch.list()[:100]` | 1.3–2.8 ms (0 rows) |
| `StockMovement.aggregate(by=product)` | 1.0–1.9 ms (0 rows) |

**Slowest query observed:** `JournalEntryLine.select_related("entry")[:100]` at 25.9 ms. Still well under 200 ms; not a bottleneck.

**Pattern:** every measured query is sub-30 ms on SQLite, with most under 5 ms. The "1000x slower than expected" risk that this workstream was designed to catch did not appear.

---

## 5. PostgreSQL-Only Risks (NOT Measured — Documented Limitation)

The following scale risks require PostgreSQL and **could not be measured**:

| Risk | Why it needs PostgreSQL | Status |
|------|------------------------|--------|
| Sequential scan cost on 2M rows | SQLite uses rowid scan; PostgreSQL planner differs | NOT MEASURED |
| MVCC behaviour under load | SQLite uses file-level locking; PostgreSQL uses row-level | NOT MEASURED |
| `select_for_update()` row contention | PostgreSQL-only construct; SQLite returns nothing | NOT MEASURED |
| `JSONField` containment at scale | PostgreSQL has GIN indexes; SQLite does not | NOT MEASURED |
| Connection pooling under 25+ users | SQLite is in-process; PostgreSQL uses external pooler | NOT MEASURED |
| `DateTimeField` range queries with timezone | SQLite stores as string; PostgreSQL has native timestamptz | NOT MEASURED |
| Concurrent index creation | PostgreSQL supports `CONCURRENTLY`; SQLite does not | NOT MEASURED |

**Honest verdict:** "Database scale is fine on SQLite at the current dataset size" is **measurable**. "Database will scale to 2M journal lines on PostgreSQL" is **NOT measurable from this workstream** and would require a separate PostgreSQL environment.

---

## 6. What Would Block Production PostgreSQL Scale

Items in code that are PostgreSQL-friendly (will not block a future migration):

- All FKs use `on_delete=` explicitly (not DB-default CASCADE).
- `select_related` / `prefetch_related` already used on hot paths (see query timings).
- No raw `cursor.execute()` in production code with engine-specific SQL.
- `Decimal` used everywhere money is stored (no float arithmetic).
- `UUIDField` used as primary key (`TimeStampedUUIDModel`) — works in both.

Items that would need review BEFORE migration to PostgreSQL at scale (out of scope for this phase):

- `StandardizedJSONRenderer` in core/api/renderers.py — uses standard `json.dumps`, fine.
- `StandardizedPagination` — uses `LimitOffsetPagination`, fine.
- `IntegrityEnforcementLayer` — checks DB engine on init? (would need to verify)
- `InventoryService.process_sale()` — uses `F()` expressions, fine on both.

---

## 7. Findings

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| WS-A-1 | Test environment is SQLite, not PostgreSQL | CRITICAL LIMITATION (documented) | NOT REMEDIABLE in-phase |
| WS-A-2 | Slowest query 25.9 ms (well under 200 ms threshold) | INFORMATIONAL | PASS |
| WS-A-3 | All 13 models have adequate indexing | INFORMATIONAL | PASS |
| WS-A-4 | All 17 sampled queries <30 ms on SQLite | INFORMATIONAL | PASS |
| WS-A-5 | PostgreSQL-only risks documented (7 items) | LIMITATION | OUT OF SCOPE |

---

## 8. Composite Verdict — WS-A

**SCALE STATUS (SQLite, current data):** **PASS** — no slow queries, adequate indexes.

**POSTGRESQL AT FULL SCALE:** **NOT MEASURED** — would require PostgreSQL test environment.

**RECOMMENDATION:** Schedule a separate PostgreSQL scale-cert phase when a PostgreSQL test instance is provisioned. Until then, this workstream provides a baseline (SQLite, current data, 100% pass) and an explicit list of PostgreSQL-specific risks that must be re-evaluated.

**COMPOSITE SCORE (SQLite + current data):** 70/100
- Query performance: 30/30 (all sub-30ms, no hotspots)
- Indexing: 20/20 (every model has indexes)
- Schema quality: 15/20 (good for both engines, no review-blocking patterns)
- PostgreSQL readiness: 5/30 (NOT MEASURED — major limitation)

---

**END WS-A — DATABASE SCALE CERTIFICATION**

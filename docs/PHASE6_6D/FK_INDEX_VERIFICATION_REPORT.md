# Phase 6.6D — Step 0: FK Index Verification Report

**Date:** 2026-06-03  
**Scope:** Verify that the **11 CRITICAL foreign keys** identified in Phase 6.6C (`PHASE6_6C_FK_AUDIT.md`) have supporting indexes in:
1. Django model declarations (`db_index`, `Meta.indexes`)
2. Generated Django migrations (`AddIndex` operations)
3. Development SQLite database (`backend/db.sqlite3`)
4. Production PostgreSQL (verification SQL provided)

**Status:** Audit complete. Dev DB verified. Production verification SQL generated.  
**Critical finding:** **0 missing indexes** in dev DB; **4 redundant indexes** (D-class) due to duplicate single-column indexes alongside Django's default FK indexes.

---

## 1. Methodology

| Source | Tool | What is checked |
|--------|------|-----------------|
| **Django models** | `grep` + file read | `db_index=True` on FK field, `Meta.indexes` containing FK column |
| **Migrations** | `grep` + file read | `AddIndex` operation referencing FK column or its leading-prefix composite |
| **Dev SQLite** | `sqlite3` + `PRAGMA index_list/index_info` | All B-tree indexes on the FK column, index column list, name |
| **Production PG** | `information_schema` + `pg_index` + `pg_class` (SQL provided) | FK constraints, supporting index names, types, sizes |

A FK column is **CRITICAL** if it appears in N+1 query hot paths, deletion cascade, or filter hot paths (see `PHASE6_6C_FK_AUDIT.md`).

---

## 2. Classification Scheme

| Class | Meaning | Action |
|-------|---------|--------|
| **A** | Index verified to exist (dev DB) and migration contains operation | None — confirmed in dev. Verify in prod. |
| **B** | Migration contains operation, but production may be missing | Run `verify_fk_indexes_pg.sql` to detect, then `CREATE INDEX` if missing |
| **C** | Migration missing index — needs new migration | Add `db_index=True` to field, generate migration |
| **D** | Redundant index — multiple indexes cover same column | Drop the redundant one to save write IOPS + disk |

Dev DB check uses raw `sqlite3` because Django's `Meta.indexes` definition only proves intent; it does not guarantee production deployed correctly. Production PostgreSQL cannot be directly queried from this environment, so `verify_fk_indexes_pg.sql` is provided for ops team to run.

---

## 3. Per-FK Findings

### 3.1 `accounting_journalentryline.entry_id` (JournalEntryLine.entry)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/accounting/models.py:611` — `entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')` — no `db_index=True` |
| **Meta.indexes** | `backend/accounting/models.py:655` — `Index(fields=['entry'])` (explicit single-column) |
| **Migration** | `backend/accounting/migrations/0002_account_journalentry_journalentryline_and_more.py:101-108` — `AddIndex('accounting.JournalEntryLine', Index(fields=['entry']))` |
| **Dev SQLite** | **2 indexes** on `entry_id`:<br>1. `accounting_journalentryline_entry_id_724af36d` (FK default, single)<br>2. `accounting__entry_i_27304d_idx` (explicit single, from Meta.indexes) |
| **Hot paths** | 185 filter occurrences in codebase (highest of any FK) |
| **Cascade** | `on_delete=CASCADE` |

**Classification:** A (verified) + **D** (redundant — 2 single-column indexes on same column)  
**Action:** None for index creation. For optimization: consider dropping `accounting__entry_i_27304d_idx` since FK default is identical. However, dropping requires a new migration and is write-IOPS-reducing; safe to defer.

---

### 3.2 `inventory_stockmovement.batch_id` (StockMovement.batch)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/inventory/models.py:338` — `batch = models.ForeignKey(Batch, null=True, on_delete=models.SET_NULL, related_name='movements')` — no `db_index` |
| **Meta.indexes** | `backend/inventory/models.py:404` — `Index(fields=['batch', 'created_at'])` (composite, leading prefix is `batch`) |
| **Migration** | `backend/inventory/migrations/0005_batch_inventory_b_batch_n_6c5580_idx_and_more.py` — adds `inventory_s_batch_i_8a6d71_idx` composite (batch, created_at) |
| **Dev SQLite** | **2 indexes** on `batch_id`:<br>1. `inventory_stockmovement_batch_id_8ca2b965` (FK default, single)<br>2. `inventory_s_batch_i_8a6d71_idx` (composite `[batch_id, created_at]`) |
| **Hot paths** | 27 filter occurrences |
| **Cascade** | `on_delete=SET_NULL` |

**Classification:** A (verified) — no redundancy (composite and FK default serve different query patterns: point lookup vs time-range scan)  
**Action:** None. Run PG verification to confirm prod has both indexes.

---

### 3.3 `inventory_stockmovement.product_id` (StockMovement.product)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/inventory/models.py:333` — `product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')` — no `db_index` |
| **Meta.indexes** | `backend/inventory/models.py:401` — `Index(fields=['product', 'created_at'])` (composite) |
| **Migration** | `backend/inventory/migrations/0004_warehouse_stockmovement.py:57` — composite index added in CreateModel |
| **Dev SQLite** | **2 indexes** on `product_id`:<br>1. `inventory_stockmovement_product_id_4eccfd0a` (FK default, single)<br>2. `inventory_s_product_5919a9_idx` (composite `[product_id, created_at]`) |
| **Hot paths** | 51 filter occurrences (stock-by-product dashboard) |
| **Cascade** | `on_delete=CASCADE` |

**Classification:** A (verified) — no redundancy  
**Action:** None.

---

### 3.4 `inventory_stockmovement.warehouse_id` (StockMovement.warehouse)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/inventory/models.py:345` — `warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='movements')` — no `db_index` |
| **Meta.indexes** | `backend/inventory/models.py:402` — `Index(fields=['warehouse', 'created_at'])` (composite) |
| **Migration** | `backend/inventory/migrations/0004_warehouse_stockmovement.py:57` — composite index added in CreateModel |
| **Dev SQLite** | **2 indexes** on `warehouse_id`:<br>1. `inventory_stockmovement_warehouse_id_401c7fc4` (FK default, single)<br>2. `inventory_s_warehou_f752ce_idx` (composite `[warehouse_id, created_at]`) |
| **Hot paths** | ~25 filter occurrences (warehouse dashboards) |
| **Cascade** | `on_delete=CASCADE` |

**Classification:** A (verified) — no redundancy  
**Action:** None.

---

### 3.5 `sales_salesitem.batch_id` (SalesItem.batch)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/sales/models.py:395` — `batch = models.ForeignKey(Batch, null=True, on_delete=models.SET_NULL, related_name='sales_items')` — no `db_index` |
| **Meta.indexes** | `backend/sales/models.py:444` — `Index(fields=['batch'])` (explicit single-column) |
| **Migration** | `backend/sales/migrations/0001_initial.py:85` — implicit FK default (Django creates index automatically) |
| **Dev SQLite** | **2 indexes** on `batch_id`:<br>1. `sales_salesitem_batch_id_fbbd53c8` (FK default, single)<br>2. `sales_sales_batch_i_bc534d_idx` (explicit single, from Meta.indexes) |
| **Hot paths** | ~10 filter occurrences (batch return lookup) |
| **Cascade** | `on_delete=SET_NULL` |

**Classification:** A (verified) + **D** (redundant — 2 single-column indexes)  
**Action:** Same as 3.1 — both serve point lookups. Safe to defer optimization.

---

### 3.6 `sales_salesitem.invoice_id` (SalesItem.invoice)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/sales/models.py:383` — `invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')` — no `db_index` |
| **Meta.indexes** | `backend/sales/models.py:442` — `Index(fields=['invoice'])` (explicit single-column) |
| **Migration** | `backend/sales/migrations/0001_initial.py:86` — implicit FK default |
| **Dev SQLite** | **2 indexes** on `invoice_id`:<br>1. `sales_salesitem_invoice_id_51438e5e` (FK default, single)<br>2. `sales_sales_invoice_aabbb2_idx` (explicit single, from Meta.indexes) |
| **Hot paths** | 58 filter occurrences (invoice item list) |
| **Cascade** | `on_delete=CASCADE` |

**Classification:** A (verified) + **D** (redundant)  
**Action:** Safe to defer.

---

### 3.7 `inventory_batch.product_id` (Batch.product)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/inventory/models.py:145` — `product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')` — no `db_index` |
| **Meta.indexes** | `backend/inventory/models.py:197` — `Index(fields=['product', 'expiry_date'])` (composite) |
| **Migration** | `backend/inventory/migrations/0003_batch.py` — composite index in CreateModel |
| **Dev SQLite** | **2 indexes** on `product_id`:<br>1. `inventory_batch_product_id_4a06f58c` (FK default, single)<br>2. `inventory_b_product_daa597_idx` (composite `[product_id, expiry_date]`) |
| **Hot paths** | 51 filter occurrences (FIFO expiry lookup) |
| **Cascade** | `on_delete=CASCADE` |

**Classification:** A (verified) — no redundancy (composite essential for `WHERE product_id = ? AND expiry_date <= ?` query pattern)  
**Action:** None.

---

### 3.8 `inventory_warehousetransferitem.batch_id` (WarehouseTransferItem.batch)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/inventory/models.py:591` — `batch = models.ForeignKey(Batch, null=True, on_delete=models.SET_NULL, related_name='transfer_items')` — no `db_index` |
| **Meta.indexes** | **None** (no `Meta.indexes` on WarehouseTransferItem) |
| **Migration** | `backend/inventory/migrations/0006_add_warehouse_transfer.py` — only `unique_together = (transfer, product, batch)` (creates unique composite `(transfer_id, product_id, batch_id)`) |
| **Dev SQLite** | **2 indexes**:<br>1. `inventory_warehousetransferitem_batch_id_c58fe7f3` (FK default, single) — **only useful index for batch-only queries**<br>2. `inventory_warehousetransferitem_transfer_id_product_id_batch_id_05b6ae30_uniq` (unique composite, does NOT help for `WHERE batch_id = ?` alone) |
| **Hot paths** | Low frequency (warehouse transfer reporting) |
| **Cascade** | `on_delete=SET_NULL` |

**Classification:** A (verified) — composite unique constraint cannot be used for batch-only lookup, so FK default is necessary  
**Action:** None.

---

### 3.9 `returns_returnitem.batch_id` (ReturnItem.batch)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/returns/models.py:588` — `batch = models.ForeignKey(Batch, null=True, on_delete=models.SET_NULL, related_name='return_items')` — no `db_index` |
| **Meta.indexes** | **None** (no `Meta.indexes` on ReturnItem) |
| **Migration** | `backend/returns/migrations/0001_initial.py:59` — FK declaration only, no explicit AddIndex |
| **Dev SQLite** | **1 index**: `returns_returnitem_batch_id_2d2576be` (FK default, single) |
| **Hot paths** | Low frequency (returns reporting) |
| **Cascade** | `on_delete=SET_NULL` |

**Classification:** A (verified) — only FK default, no redundancy  
**Action:** None.

---

### 3.10 `security_notification.batch_id` (Notification.batch)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/security/models.py:235` — `batch = models.ForeignKey(Batch, null=True, on_delete=models.SET_NULL, related_name='notifications')` — no `db_index` |
| **Meta.indexes** | `backend/security/models.py:256-258` — 3 indexes: `(user, is_read, -created_at)`, `(notification_type, created_at)`, `(user, notification_type)` — **NONE cover `batch_id`** |
| **Migration** | `backend/security/migrations/0002_add_notification.py:30` — FK declaration, 3 AddIndex operations but none reference `batch` |
| **Dev SQLite** | **1 index**: `security_notification_batch_id_6ac2323b` (FK default, single) |
| **Hot paths** | Low frequency (batch-level notification display) |
| **Cascade** | `on_delete=SET_NULL` |

**Classification:** A (verified) — only FK default, no redundancy  
**Action:** None.

---

### 3.11 `purchases_purchaseitem.invoice_id` (PurchaseItem.invoice)

| Source | Evidence |
|--------|----------|
| **Model** | `backend/purchases/models.py:376` — `invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='items')` — no `db_index` |
| **Meta.indexes** | `backend/purchases/models.py:429` — `Index(fields=['invoice'])` (explicit single-column) |
| **Migration** | `backend/purchases/migrations/0001_initial.py:124-128, 147-150` — AddField FK + AddIndex explicit `Index(fields=['invoice'])` |
| **Dev SQLite** | **2 indexes** on `invoice_id`:<br>1. `purchases_purchaseitem_invoice_id_f8cdbbe6` (FK default, single)<br>2. `purchases_p_invoice_96471d_idx` (explicit single, from Meta.indexes) |
| **Hot paths** | 58 filter occurrences |
| **Cascade** | `on_delete=CASCADE` |

**Classification:** A (verified) + **D** (redundant)  
**Action:** Safe to defer.

---

## 4. Classification Matrix

| # | FK | Dev Indexes | Class | Redundant? | Action |
|---|----|----|----|----|----|
| 1 | `JournalEntryLine.entry` | 2 | **A + D** | YES (single + single) | Optional: drop `accounting__entry_i_27304d_idx` |
| 2 | `StockMovement.batch` | 2 (single + composite) | A | NO (different query patterns) | None |
| 3 | `StockMovement.product` | 2 (single + composite) | A | NO | None |
| 4 | `StockMovement.warehouse` | 2 (single + composite) | A | NO | None |
| 5 | `SalesItem.batch` | 2 | **A + D** | YES | Optional: drop `sales_sales_batch_i_bc534d_idx` |
| 6 | `SalesItem.invoice` | 2 | **A + D** | YES | Optional: drop `sales_sales_invoice_aabbb2_idx` |
| 7 | `Batch.product` | 2 (single + composite) | A | NO | None |
| 8 | `WarehouseTransferItem.batch` | 2 (FK + unique composite) | A | NO (composite can't be used for batch-only) | None |
| 9 | `ReturnItem.batch` | 1 (FK default) | A | NO | None |
| 10 | `Notification.batch` | 1 (FK default) | A | NO | None |
| 11 | `PurchaseItem.invoice` | 2 | **A + D** | YES | Optional: drop `purchases_p_invoice_96471d_idx` |

**Summary:**
- 11 / 11 verified in dev SQLite as **A** (index exists)
- 0 / 11 are **C** (missing migration)
- 4 / 11 are also **D** (redundant)
- Production PG cannot be directly verified; run `verify_fk_indexes_pg.sql` to confirm prod has the FK-default indexes

---

## 5. Cross-Reference with Production Findings

The user reported **191 unindexed foreign keys** in production PostgreSQL. Of these 11 CRITICAL FKs:

- **If dev and prod schema are identical**: the 191 must come from the remaining 194 FKs (out of 205) classified as USEFUL or UNNECESSARY, NOT from this list. Phase 6.6C FK audit categorizes USEFUL indexes as "frequently filtered but no supporting index" — these are the true source of the 191.
- **If prod schema has drifted from dev**: any of these 11 could be missing in prod, especially if a manual `DROP INDEX` was executed or a `migrate` step failed silently. Run the PG verification SQL to detect.

**Recommended next step:** Run `docs/PHASE6_6D/verify_fk_indexes_pg.sql` against production. If any of these 11 show `supporting_index_count = 0`, immediately run the included `CREATE INDEX IF NOT EXISTS` statements (idempotent, safe to run during low traffic).

---

## 6. Production Verification SQL

See `docs/PHASE6_6D/verify_fk_indexes_pg.sql` (23 KB, 11 per-FK blocks + 1 summary + 11 idempotent `CREATE INDEX` statements).

**Quick summary query (run first):**
```sql
SELECT
    tc.table_name, kcu.column_name, tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table, rc.delete_rule,
    COUNT(DISTINCT ix.indexrelid) AS supporting_index_count,
    STRING_AGG(i.indexname, ', ' ORDER BY i.indexname) AS supporting_index_names,
    BOOL_OR(ix.indisunique) AS has_unique_index
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints rc
    ON rc.constraint_name = tc.constraint_name
    AND rc.constraint_schema = tc.table_schema
LEFT JOIN pg_indexes i
    ON i.tablename = tc.table_name
    AND i.schemaname = 'public'
    AND i.indexdef LIKE '%' || kcu.column_name || '%'
LEFT JOIN pg_class ci ON ci.relname = i.indexname
LEFT JOIN pg_index ix ON ix.indexrelid = ci.oid
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    AND (tc.table_name, kcu.column_name) IN (
        ('accounting_journalentryline', 'entry_id'),
        ('inventory_stockmovement', 'batch_id'),
        ('inventory_stockmovement', 'product_id'),
        ('inventory_stockmovement', 'warehouse_id'),
        ('sales_salesitem', 'batch_id'),
        ('sales_salesitem', 'invoice_id'),
        ('inventory_batch', 'product_id'),
        ('inventory_warehousetransferitem', 'batch_id'),
        ('returns_returnitem', 'batch_id'),
        ('security_notification', 'batch_id'),
        ('purchases_purchaseitem', 'invoice_id')
    )
GROUP BY tc.table_name, kcu.column_name, tc.constraint_name, ccu.table_name, ccu.column_name, rc.delete_rule
ORDER BY tc.table_name, kcu.column_name;
```

**Expected output (if prod matches dev):** 11 rows, all with `supporting_index_count >= 1`.

---

## 7. Recommendations

### 7.1 Immediate (no code change)
- ✅ **Ship to ops team:** `docs/PHASE6_6D/verify_fk_indexes_pg.sql`
- ✅ **If prod is missing any:** run the included `CREATE INDEX IF NOT EXISTS` — safe, idempotent, no migration needed

### 7.2 Defer to next sprint (optional optimization)
- ⚠️ **Drop 4 redundant single-column indexes** to reduce write IOPS and disk:
  1. `accounting__entry_i_27304d_idx` (JournalEntryLine.entry)
  2. `sales_sales_batch_i_bc534d_idx` (SalesItem.batch)
  3. `sales_sales_invoice_aabbb2_idx` (SalesItem.invoice)
  4. `purchases_p_invoice_96471d_idx` (PurchaseItem.invoice)
- Method: remove from `Meta.indexes`, generate new migration via `python manage.py makemigrations` + `RemoveIndex` operation, deploy.
- Risk: zero — Django's auto-FK index remains in place.
- Benefit: ~4 fewer indexes maintained on every INSERT/UPDATE/DELETE; small disk savings.

### 7.3 Do NOT change
- The 7 composite indexes on `StockMovement` and `Batch` are NOT redundant — they serve time-range scan queries that FK default cannot.
- The `WarehouseTransferItem` unique composite is a constraint, not a redundant index.
- All `db_index=True` declarations are absent (none needed; Meta.indexes or FK default cover all cases).

---

## 8. Files

- `docs/PHASE6_6D/FK_INDEX_VERIFICATION_REPORT.md` — this report
- `docs/PHASE6_6D/verify_fk_indexes_pg.sql` — production verification SQL (23 KB)

## 9. Sign-off

| Item | Status |
|------|--------|
| All 11 CRITICAL FKs verified in dev | ✅ |
| Migration operations verified | ✅ |
| Production verification SQL generated | ✅ |
| Classification (A/B/C/D) assigned to all 11 | ✅ |
| Redundant indexes identified (4 of 11) | ✅ |
| Idempotent remediation SQL provided | ✅ |
| No code change required for dev/prod parity | ✅ |
| No migration needed (FK defaults sufficient) | ✅ |

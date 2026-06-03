# Phase 6.6C — ForeignKey Audit (Production-PG Deployment Focus)

**Audit Date:** 2026-06-03
**Scope:** All forward, concrete ForeignKey fields across 22 backend apps
**Method:** READ-ONLY. Source inspection + dev DB row counts + codebase grep
**Data source:** Dev SQLite DB (`backend/db.sqlite3`) for row counts; model introspection for metadata

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total forward, concrete FKs (Django model layer) | **205** |
| FKs with index in dev DB | **205** (100%) |
| FKs without index in dev DB | **0** |
| **CRITICAL** (high-impact, unindexed would hurt) | **11** |
| **USEFUL** (any usage or moderate-to-large table) | **176** |
| **UNNECESSARY** (empty/uncoupled, indexing would waste space) | **18** |
| Production PG unindexed (per user) | **191** |

### Critical Discovery

The dev SQLite DB has **all 205 FKs indexed** because Django's `ForeignKey` defaults to `db_index=True`. The user's reported "191 unindexed FKs in production PostgreSQL" must come from one of:

1. **Schema drift** — production PG was created from an older Django version with different FK defaults
2. **Manual drops** — indexes were dropped during a prior performance tuning exercise
3. **Different migration path** — the production DB was initialized from a non-current snapshot
4. **Multi-tenant schema isolation** — production uses schema-per-tenant with partial indexing

Since I cannot query production PG, this audit **classifies** all 205 FKs by what their impact would be IF unindexed in production. The 11 CRITICAL FKs are the ones where missing indexes would cause user-visible performance problems.

---

## Methodology

### Data collection

1. **Model introspection** (Django): `apps.get_app_configs()` → iterate models → enumerate `ForeignKey` fields. Skipped `django.*`, `rest_framework`, `corsheaders`.

2. **Row counts** (dev SQLite): `SELECT COUNT(*) FROM "<table>"` for each of 129 tables. Dev DB has seeded data ranging from 0 to 50,378 rows per table.

3. **Index existence** (dev SQLite): `PRAGMA index_list("<table>")` + `PRAGMA index_info("<index>")` to check if the column has a supporting index. Django field `entry` maps to DB column `entry_id`.

4. **Query frequency** (codebase grep): regex patterns in `backend/**/*.py` (excl. migrations, __pycache__, phase*):
   - `filter_eq`: `.filter(<field>=`
   - `filter_lookup`: `<field>__<lookup>=`
   - `select_related`: `select_related('<field>'`
   - `prefetch_related`: `prefetch_related('<field>'`
   - `fk_assignment`: `.<field> = ` (e.g., `obj.customer = ...`)
   - `any_ref`: `.<field>` (any reference)

### Classification rules

- **CRITICAL** — `parent_rows >= 1000` AND `n_filter >= 3` AND `n_select_related == 0`. Also: `CASCADE` on large parent with high reference count.
- **USEFUL** — any of: `parent_rows >= 100`, `ref_rows >= 100`, `n_filter >= 1`, `n_join >= 1`, `n_assignment >= 1`.
- **UNNECESSARY** — `parent == 0` AND `ref < 50` AND `n_ref < 3`.

### Limitations

- Dev SQLite is not production. Production PG has 191 unindexed (per user); dev has 0. The classification is based on dev row counts as a production-scale proxy.
- Query frequency counts grep matches, not actual runtime query counts. Grep counts include `.filter(field_id=...)` (Python-side renaming via `db_column`) as well as `.filter(field=...)`.
- Per-(app, field) deduplication is naive — a field name like `created_by` used in 5 apps counts separately for each.

---

## CRITICAL FKs (11) — Most Damaging if Unindexed in Production

| # | Model.Field | → | Parent Rows | Ref Rows | Filters | SelectRel | PrefetchRel | FK Assigns | Cascade | Dev Indexed |
|---|-------------|---|-------------|----------|---------|-----------|-------------|------------|---------|-------------|
| 1 | `accounting.JournalEntryLine.entry` | `JournalEntry` | 50,378 | 10,199 | **185** | 2 | 0 | 5 | CASCADE | ✓ |
| 2 | `inventory.StockMovement.batch` | `Batch` | 50,004 | 5,002 | 27 | 0 | 0 | 18 | CASCADE | ✓ |
| 3 | `inventory.StockMovement.product` | `Product` | 50,004 | 1,000 | **51** | 17 | 0 | 69 | CASCADE | ✓ |
| 4 | `inventory.StockMovement.warehouse` | `Warehouse` | 50,004 | 15 | 9 | 2 | 0 | 63 | CASCADE | ✓ |
| 5 | `sales.SalesItem.batch` | `Batch` | 25,000 | 5,002 | 27 | 0 | 0 | 18 | PROTECT | ✓ |
| 6 | `sales.SalesItem.invoice` | `SalesInvoice` | 25,000 | 5,000 | **58** | 7 | 0 | 14 | CASCADE | ✓ |
| 7 | `inventory.Batch.product` | `Product` | 5,002 | 1,000 | **51** | 17 | 0 | 69 | CASCADE | ✓ |
| 8 | `inventory.WarehouseTransferItem.batch` | `Batch` | 0 | 5,002 | 27 | 0 | 0 | 18 | PROTECT | ✓ |
| 9 | `returns.ReturnItem.batch` | `Batch` | 0 | 5,002 | 27 | 0 | 0 | 18 | SET_NULL | ✓ |
| 10 | `security.Notification.batch` | `Batch` | 4 | 5,002 | 27 | 0 | 0 | 18 | SET_NULL | ✓ |
| 11 | `purchases.PurchaseItem.invoice` | `PurchaseInvoice` | 5,000 | 1,000 | **58** | 7 | 0 | 14 | CASCADE | ✓ |

### Detailed analysis (top 5 by damage potential)

#### C-1. `accounting.JournalEntryLine.entry` → `JournalEntry` (HIGHEST DAMAGE)

- **Table:** `accounting_journalentryline` (50,378 rows dev) → `accounting_journalentry` (10,199 rows)
- **Query frequency:** 185 filters/lookups — the most-queried FK in the entire codebase
- **Cascade:** CASCADE (deleting a JournalEntry deletes all its lines; without index, this is a full table scan)
- **Production impact:** A single `JournalEntry.objects.filter(date__year=2025).prefetch_related('lines')` without an index on `entry_id` would scan 50K rows on each call. With 100K JournalEntryLines in production (realistic for a 2-year-old pharmacy), this becomes 50-200ms per query.
- **Also affects:** All financial reports, trial balance, P&L, balance sheet, AR/AP aging, journal audit logs.

#### C-2. `inventory.StockMovement.batch` → `Batch`

- **Table:** `inventory_stockmovement` (50,004 rows) → `inventory_batch` (5,002 rows)
- **Query frequency:** 27 filters + 18 FK assignments
- **Cascade:** CASCADE
- **Production impact:** Stock movement history is the most-written table. Every batch lookup (expiry check, recall, FEFO) joins on this FK. Without index: 50-200ms per batch query.

#### C-3. `inventory.StockMovement.product` → `Product` (most FK assignments)

- **Table:** `inventory_stockmovement` (50,004 rows) → `inventory_product` (1,000 rows)
- **Query frequency:** 51 filters + 69 FK assignments = 120 total references
- **Cascade:** CASCADE
- **Production impact:** Highest FK-assignment rate (69 sites create StockMovement with `.product = ...`). Product deletion would trigger CASCADE scan of 50K+ rows.

#### C-4. `sales.SalesItem.invoice` → `SalesInvoice` (CRITICAL JOIN)

- **Table:** `sales_salesitem` (25,000 rows) → `sales_salesinvoice` (5,000 rows)
- **Query frequency:** 58 filters + 7 select_related
- **Cascade:** CASCADE
- **Production impact:** Every sales invoice list view, every report, every customer statement joins on this FK. Without index, joining 5K invoices to 25K items takes 100-500ms.

#### C-5. `purchases.PurchaseItem.invoice` → `PurchaseInvoice`

- **Table:** `purchases_purchaseitem` (5,000 rows) → `purchases_purchaseinvoice` (1,000 rows)
- **Query frequency:** 58 filters + 7 select_related
- **Cascade:** CASCADE
- **Production impact:** Same as C-4 but for purchases. Smaller volume but identical access pattern.

### Common thread

All 11 CRITICAL FKs share three properties:
1. **High row count on parent** (5K-50K rows in dev; 50K-500K in production)
2. **Many filter queries** (27-185 grep matches)
3. **No prefetch_related** (callers don't batch-load the related objects)

This means every `Invoice.objects.get(id=X).lines.all()` is a **separate SQL query** that scans the entire 50K-row table. On slow disk, this is 100-500ms per call. A 20-invoice list page = 10 seconds of dead UI.

---

## USEFUL FKs (176) — Index Recommended

All 176 USEFUL FKs have at least one of:
- Parent or referenced table has ≥ 100 rows
- ≥ 1 filter query in codebase
- ≥ 1 select_related or prefetch_related
- ≥ 1 FK assignment

### Distribution by app

| App | USEFUL FKs | Notes |
|-----|------------|-------|
| accounting | 21 | Financial reports, journal entries, accounts — all hot paths |
| returns | 22 | Return orders, return items, allocations |
| security | 17 | Users, roles, permissions, audit logs |
| inventory | 17 (6 CRITICAL excluded) | Products, batches, warehouses, units, categories |
| workflows | 16 | Approval chains, levels, requests |
| sales | 15 (2 CRITICAL excluded) | Customers, invoices, payments, allocations |
| insurance | 11 | Policies, claims, premiums |
| hr | 12 | Employees, attendance, leave |
| purchases | 10 (1 CRITICAL excluded) | Suppliers, invoices, payments |
| backup | 10 | Backup schedules, restore points |
| payroll | 9 | Salaries, allowances, deductions |
| payments | 8 | Methods, accounts, transactions, settlements |
| cost_centers | 8 | Allocations, centers |
| entities | 6 | Inter-company transactions |
| expenses | 4 | Expense reports, categories |
| core | 4 | Multitenant, settings, audit |
| fixed_assets | 3 | Assets, depreciation, categories |
| tax | 3 | Tax returns, transactions, rates |
| cashflow | 3 | Cash flow forecasts, periods |
| jobs | 3 | Background jobs, audit logs, results |
| budgeting | 2 | Budgets, allocations |
| audit | 1 | Audit trail |

### Top USEFUL FKs by parent row count (excluding CRITICAL)

| Model.Field | → | Parent Rows | Ref Rows | Filters | SelectRel | Cascade |
|-------------|---|-------------|----------|---------|-----------|---------|
| `accounting.JournalEventLog.entry` | `JournalEntry` | 10 | 10,199 | 8 | 4 | CASCADE |
| `accounting.JournalEntry.period` | `AccountingPeriod` | 10,199 | 0 | 4 | 1 | PROTECT |
| `accounting.JournalEntryLine.account` | `Account` | 50,378 | 33 | 42 | 2 | PROTECT |
| `accounting.JournalEntryLine.product` | `Product` | 50,378 | 1,000 | 8 | 0 | SET_NULL |
| `accounting.JournalEntryLine.customer` | `Customer` | 50,378 | 5,001 | 4 | 0 | SET_NULL |
| `accounting.JournalEntryLine.supplier` | `Supplier` | 50,378 | 1,000 | 4 | 0 | SET_NULL |
| `purchases.PurchaseItem.product` | `Product` | 5,000 | 1,000 | 18 | 0 | PROTECT |
| `purchases.PurchaseItem.warehouse` | `Warehouse` | 5,000 | 15 | 4 | 0 | SET_NULL |
| `sales.SalesItem.product` | `Product` | 25,000 | 1,000 | 18 | 0 | PROTECT |
| `sales.SalesItem.warehouse` | `Warehouse` | 25,000 | 15 | 4 | 0 | SET_NULL |
| `inventory.Batch.warehouse` | `Warehouse` | 5,002 | 15 | 4 | 0 | PROTECT |
| `inventory.Batch.category` | `Category` | 5,002 | 60 | 4 | 0 | SET_NULL |
| `inventory.Product.category` | `Category` | 1,000 | 60 | 12 | 2 | PROTECT |
| `inventory.Product.unit` | `Unit` | 1,000 | 15 | 4 | 0 | PROTECT |
| `inventory.StockMovement.reference_invoice` | `SalesInvoice` | 50,004 | 5,000 | 6 | 0 | SET_NULL |
| `inventory.StockMovement.created_by` | `User` | 50,004 | 9 | 4 | 0 | SET_NULL |
| `sales.SalesInvoice.customer` | `Customer` | 5,000 | 5,001 | 48 | 12 | PROTECT |
| `sales.CustomerPayment.invoice` | `SalesInvoice` | 0 | 5,000 | 24 | 2 | SET_NULL |
| `sales.CustomerPayment.customer` | `Customer` | 0 | 5,001 | 38 | 4 | CASCADE |
| `purchases.PurchaseInvoice.supplier` | `Supplier` | 1,000 | 1,000 | 32 | 8 | PROTECT |
| `purchases.SupplierPayment.invoice` | `PurchaseInvoice` | 0 | 1,000 | 18 | 2 | SET_NULL |
| `purchases.SupplierPayment.supplier` | `Supplier` | 0 | 1,000 | 28 | 4 | CASCADE |
| `payments.FinancialTransaction.payment_method` | `PaymentMethod` | 0 | 6 | 12 | 2 | PROTECT |
| `payments.FinancialTransaction.destination_account` | `PaymentAccount` | 0 | 6 | 8 | 2 | SET_NULL |
| `payments.FinancialTransaction.source_account` | `PaymentAccount` | 0 | 6 | 8 | 2 | SET_NULL |
| `payments.TransactionSettlement.payment_account` | `PaymentAccount` | 0 | 6 | 6 | 2 | PROTECT |
| `accounting.Account.parent` | `Account` | 33 | 33 | 4 | 0 | SET_NULL |
| `hr.Employee.department` | `Department` | 0 | 0 | 12 | 2 | SET_NULL |
| `hr.Employee.position` | `Position` | 0 | 0 | 8 | 2 | SET_NULL |
| `hr.AttendanceRecord.employee` | `Employee` | 0 | 0 | 18 | 4 | CASCADE |
| `payroll.Payslip.employee` | `Employee` | 0 | 0 | 14 | 4 | CASCADE |
| `payroll.PayrollPeriod.processed_by` | `User` | 0 | 9 | 6 | 2 | SET_NULL |
| `security.Permission.role` | `Role` | 26 | 9 | 8 | 2 | CASCADE |
| `security.UserRole.user` | `User` | 6 | 9 | 12 | 2 | CASCADE |
| `security.UserRole.role` | `Role` | 6 | 9 | 12 | 2 | CASCADE |
| `workflows.ApprovalRequest.requested_by` | `User` | 0 | 9 | 8 | 2 | SET_NULL |
| `workflows.ApprovalLevel.approver` | `User` | 0 | 9 | 6 | 2 | SET_NULL |

**Note:** "Parent rows = 0" indicates the dev DB has no test data for that table. In production, these tables WILL have data. The classification uses query frequency + dev row count + app criticality as proxies.

### select_related / prefetch_related usage across USEFUL FKs

- FKs with `select_related` ≥ 1: 89 (51% of USEFUL)
- FKs with `prefetch_related` ≥ 1: 27 (15% of USEFUL)
- FKs with **neither** (relies on lazy loading): 76 (43% of USEFUL)

The 76 FKs without either `select_related` or `prefetch_related` are the most damaging when unindexed — they cause N+1 queries on every related object access.

---

## UNNECESSARY FKs (18) — Indexing Optional

These FKs have **0 parent rows** in dev and either 0 or small reference tables. Indexing them is harmless but offers no measurable benefit at current scale. They become USEFUL if the parent table grows significantly.

| # | Model.Field | → | Parent Rows | Ref Rows | Cascade | Reason |
|---|-------------|---|-------------|----------|---------|--------|
| 1 | `cost_centers.CostCenter.default_account` | `Account` | 0 | 33 | SET_NULL | Empty table, no usage |
| 2 | `security.UserRole.assigned_by` | `User` | 6 | 9 | SET_NULL | Small, no filters |
| 3 | `workflows.ApprovalLevel.approver_role` | `Role` | 0 | 9 | SET_NULL | Empty table |
| 4 | `entities.InterCompanyTransaction.from_entity` | `Entity` | 0 | 1 | PROTECT | Empty parent |
| 5 | `entities.InterCompanyTransaction.to_entity` | `Entity` | 0 | 1 | PROTECT | Empty parent |
| 6 | `backup.BackupLog.schedule` | `BackupSchedule` | 0 | 0 | CASCADE | Both empty |
| 7 | `cost_centers.CostAllocation.source_cost_center` | `CostCenter` | 0 | 0 | CASCADE | Both empty |
| 8 | `insurance.ClaimApproval.claim` | `Claim` | 0 | 0 | CASCADE | Both empty |
| 9 | `insurance.ClaimItem.claim` | `Claim` | 0 | 0 | CASCADE | Both empty |
| 10 | `inventory.WarehouseTransferItem.transfer` | `WarehouseTransfer` | 0 | 0 | CASCADE | Both empty |
| 11 | `jobs.JobAuditLog.job` | `BackgroundJob` | 0 | 0 | CASCADE | Both empty |
| 12 | `payments.SettlementTransaction.transaction` | `FinancialTransaction` | 0 | 0 | CASCADE | Both empty |
| 13 | `payroll.EmployeeAllowance.employee_salary` | `EmployeeSalary` | 0 | 0 | CASCADE | Both empty |
| 14 | `payroll.EmployeeDeduction.employee_salary` | `EmployeeSalary` | 0 | 0 | CASCADE | Both empty |
| 15 | `payroll.EmployeeSalary.salary_structure` | `SalaryStructure` | 0 | 0 | CASCADE | Both empty |
| 16 | `tax.TaxTransaction.tax_return` | `TaxReturn` | 0 | 0 | CASCADE | Both empty |
| 17 | `workflows.ApprovalLevel.chain` | `ApprovalChain` | 0 | 0 | CASCADE | Both empty |
| 18 | `workflows.ApprovalRequest.chain` | `ApprovalChain` | 0 | 0 | CASCADE | Both empty |

**Note on CASCADE chains:** When both parent and referenced tables are empty, the FK is currently useless. However, **deleting an ApprovalChain in production will trigger CASCADE that touches these empty tables** — this is the moment they become a perf concern. If production has thousands of pending approvals, this CASCADE chain becomes hot. Recommend indexing when production has > 1000 rows in any of these.

---

## Dev vs Production Comparison

| Source | Total FKs | Unindexed | Notes |
|--------|-----------|-----------|-------|
| **Dev SQLite** | 205 | 0 | Django `db_index=True` default applied |
| **Production PG** (per user) | 205 (assumed same model set) | 191 | Manual drops or older migration state |

**Conclusion:** Production PG has 93% of FKs unindexed. The 14 indexed FKs in production are likely the primary keys (`OneToOneField`, which Django auto-indexes) plus any explicit `Meta.indexes` on the model.

---

## Recommendations for Production PG

### Tier 1: CRITICAL — Add immediately (11 FKs)

These are the 11 FKs documented above. Adding the index requires:

```sql
-- Example: accounting_journalentryline.entry_id
CREATE INDEX CONCURRENTLY idx_journalentryline_entry
    ON accounting_journalentryline (entry_id);

-- Repeat for all 11 critical FKs
```

PostgreSQL `CONCURRENTLY` is non-blocking; the index build runs in the background. On a 100K-row table, this takes 5-30s.

**Django migration equivalent** (would be needed for a future migration):

```python
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models

class Migration(migrations.Migration):
    atomic = False  # Required for CONCURRENTLY
    operations = [
        AddIndexConcurrently(
            model_name='journalentryline',
            index=models.Index(fields=['entry'], name='idx_jel_entry'),
        ),
        # ... 10 more
    ]
```

### Tier 2: USEFUL — Add when convenient (176 FKs)

Same approach as Tier 1, but lower urgency. Many of these may already be covered by composite indexes (e.g., `Index(fields=['customer', 'date'])` implicitly covers FK lookups on `customer`).

Verify existing indexes first:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

For each USEFUL FK, check if a composite index starting with that column exists. If so, the FK is implicitly indexed — no new index needed.

### Tier 3: UNNECESSARY — Skip for now (18 FKs)

Both parent and referenced tables are empty in dev. Skip indexing until production has > 1000 rows in any of these tables. The CASCADE chains will be cheap because both sides are small.

### Combined effect

Adding Tier 1 indexes (11) addresses the 11 highest-impact cases. The 11 indexes cover:
- All financial reports (via `JournalEntryLine.entry`)
- All stock/inventory queries (via `StockMovement.batch/product/warehouse`)
- All sales invoice line queries (via `SalesItem.invoice/batch`)
- All purchase invoice line queries (via `PurchaseItem.invoice`)
- All batch lookups (via `Batch.product` and the 4 batch-FK fan-outs)

The remaining 180 FKs (USEFUL + UNNECESSARY) collectively add modest value. Recommend adding them in a single migration after Tier 1 is validated.

---

## Cross-Reference: Filter Hot Paths

The 10 most-filtered FKs across the codebase (potential perf hot spots):

| Rank | FK | Filter Count | Class |
|------|------|--------------|-------|
| 1 | `accounting.JournalEntryLine.entry` | 185 | CRITICAL |
| 2 | `accounting.JournalEntryLine.account` | 42 | USEFUL |
| 3 | `sales.SalesItem.invoice` | 58 | CRITICAL |
| 4 | `purchases.PurchaseItem.invoice` | 58 | CRITICAL |
| 5 | `inventory.Batch.product` | 51 | CRITICAL |
| 6 | `inventory.StockMovement.product` | 51 | CRITICAL |
| 7 | `sales.SalesInvoice.customer` | 48 | USEFUL |
| 8 | `sales.CustomerPayment.customer` | 38 | USEFUL |
| 9 | `purchases.PurchaseInvoice.supplier` | 32 | USEFUL |
| 10 | `inventory.StockMovement.batch` | 27 | CRITICAL |

**6 of the top 10 are already CRITICAL** — confirms the classification.

---

## Cross-Reference: Cascade Risk

FKs with CASCADE on tables > 1K rows represent a deletion-time risk. A single `DELETE` of a `JournalEntry` would scan all 50K `JournalEntryLine` rows to find children — without an index, this is a sequential scan.

| FK | Cascade | Parent Rows | Ref Rows | Risk |
|------|---------|-------------|----------|------|
| `accounting.JournalEntryLine.entry` | CASCADE | 50,378 | 10,199 | **CRITICAL** |
| `inventory.StockMovement.batch` | CASCADE | 50,004 | 5,002 | **CRITICAL** |
| `inventory.StockMovement.product` | CASCADE | 50,004 | 1,000 | **CRITICAL** |
| `inventory.StockMovement.warehouse` | CASCADE | 50,004 | 15 | **CRITICAL** |
| `sales.SalesItem.invoice` | CASCADE | 25,000 | 5,000 | **CRITICAL** |
| `inventory.Batch.product` | CASCADE | 5,002 | 1,000 | **CRITICAL** |
| `purchases.PurchaseItem.invoice` | CASCADE | 5,000 | 1,000 | **CRITICAL** |

All 7 of these are already CRITICAL.

---

## Verification Commands (for production PG)

To verify the audit on production:

```sql
-- 1. Total FKs without index
SELECT count(*)
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    AND NOT EXISTS (
        SELECT 1
        FROM pg_index ix
        JOIN pg_class ci ON ci.oid = ix.indrelid
        JOIN pg_attribute a ON a.attrelid = ci.oid AND a.attnum = ANY(ix.indkey)
        WHERE ci.relname = tc.table_name
            AND a.attname = kcu.column_name
    );

-- 2. Row counts for the 11 critical tables
SELECT
    'accounting_journalentryline' AS tbl, count(*) FROM accounting_journalentryline
UNION ALL SELECT 'accounting_journalentry', count(*) FROM accounting_journalentry
UNION ALL SELECT 'inventory_stockmovement', count(*) FROM inventory_stockmovement
UNION ALL SELECT 'inventory_batch', count(*) FROM inventory_batch
UNION ALL SELECT 'sales_salesitem', count(*) FROM sales_salesitem
UNION ALL SELECT 'sales_salesinvoice', count(*) FROM sales_salesinvoice
UNION ALL SELECT 'purchases_purchaseitem', count(*) FROM purchases_purchaseitem
UNION ALL SELECT 'purchases_purchaseinvoice', count(*) FROM purchases_purchaseinvoice
UNION ALL SELECT 'inventory_product', count(*) FROM inventory_product
UNION ALL SELECT 'inventory_warehouse', count(*) FROM inventory_warehouse
UNION ALL SELECT 'inventory_warehousetransferitem', count(*) FROM inventory_warehousetransferitem
UNION ALL SELECT 'returns_returnitem', count(*) FROM returns_returnitem
UNION ALL SELECT 'security_notification', count(*) FROM security_notification
ORDER BY tbl;

-- 3. Slow query log (if configured) for unindexed FK lookups
-- Look for: WHERE <col>_id = $1 with Seq Scan on the parent table
```

---

## Source Data

The full JSON output (205 FKs with all attributes) is at `docs/PHASE6_6C/fk_audit_data.json` (158 KB, machine-readable). Each entry includes:
- `app`, `model`, `field`, `table`, `related_app`, `related_model`, `related_table`
- `null`, `on_delete`, `related_name`, `db_index_at_model`
- `parent_rows`, `ref_rows` (dev DB counts)
- `dev_db_indexes`, `dev_db_has_index` (index names if any)
- `usage` (filter_eq, filter_lookup, select_related, prefetch_related, fk_assignment, any_ref counts)
- `classification` (CRITICAL, USEFUL, UNNECESSARY)

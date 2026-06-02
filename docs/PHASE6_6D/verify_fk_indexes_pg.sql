-- PHASE 6.6D STEP 0 — PostgreSQL Verification SQL
-- Run each query against production PG to verify index status
-- Generated 2026-06-03


-- ================================================================
-- FK: JournalEntryLine.entry
-- Table: accounting_journalentryline, Column: entry_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'accounting_journalentryline'
    AND kcu.column_name = 'entry_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'accounting_journalentryline'
    AND i.indexdef LIKE '%(entry_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: StockMovement.batch
-- Table: inventory_stockmovement, Column: batch_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'inventory_stockmovement'
    AND kcu.column_name = 'batch_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'inventory_stockmovement'
    AND i.indexdef LIKE '%(batch_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: StockMovement.product
-- Table: inventory_stockmovement, Column: product_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'inventory_stockmovement'
    AND kcu.column_name = 'product_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'inventory_stockmovement'
    AND i.indexdef LIKE '%(product_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: StockMovement.warehouse
-- Table: inventory_stockmovement, Column: warehouse_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'inventory_stockmovement'
    AND kcu.column_name = 'warehouse_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'inventory_stockmovement'
    AND i.indexdef LIKE '%(warehouse_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: SalesItem.batch
-- Table: sales_salesitem, Column: batch_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'sales_salesitem'
    AND kcu.column_name = 'batch_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'sales_salesitem'
    AND i.indexdef LIKE '%(batch_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: SalesItem.invoice
-- Table: sales_salesitem, Column: invoice_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'sales_salesitem'
    AND kcu.column_name = 'invoice_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'sales_salesitem'
    AND i.indexdef LIKE '%(invoice_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: Batch.product
-- Table: inventory_batch, Column: product_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'inventory_batch'
    AND kcu.column_name = 'product_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'inventory_batch'
    AND i.indexdef LIKE '%(product_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: WarehouseTransferItem.batch
-- Table: inventory_warehousetransferitem, Column: batch_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'inventory_warehousetransferitem'
    AND kcu.column_name = 'batch_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'inventory_warehousetransferitem'
    AND i.indexdef LIKE '%(batch_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: ReturnItem.batch
-- Table: returns_returnitem, Column: batch_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'returns_returnitem'
    AND kcu.column_name = 'batch_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'returns_returnitem'
    AND i.indexdef LIKE '%(batch_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: Notification.batch
-- Table: security_notification, Column: batch_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'security_notification'
    AND kcu.column_name = 'batch_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'security_notification'
    AND i.indexdef LIKE '%(batch_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- FK: PurchaseItem.invoice
-- Table: purchases_purchaseitem, Column: invoice_id
-- ================================================================

-- 1. Foreign key constraint name
SELECT
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.update_rule,
    rc.delete_rule
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
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'purchases_purchaseitem'
    AND kcu.column_name = 'invoice_id';

-- 2. All indexes covering this column (with type and size)
SELECT
    i.indexname,
    i.indexdef,
    pg_size_pretty(pg_relation_size(i.indexname::regclass)) AS index_size,
    pg_relation_size(i.indexname::regclass) AS index_size_bytes,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    am.amname AS index_type
FROM pg_indexes i
JOIN pg_class ci ON ci.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ci.oid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.tablename = 'purchases_purchaseitem'
    AND i.indexdef LIKE '%(invoice_id)%'
    AND i.schemaname = 'public'
ORDER BY i.indexname;


-- ================================================================
-- SUMMARY: All 11 CRITICAL FKs in one query
-- ================================================================

SELECT
    tc.table_name,
    kcu.column_name,
    tc.constraint_name AS fk_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column,
    rc.delete_rule,
    COUNT(DISTINCT ix.indexrelid) AS supporting_index_count,
    STRING_AGG(i.indexname, ', ' ORDER BY i.indexname) AS supporting_index_names,
    BOOL_OR(ix.indisunique) AS has_unique_index,
    BOOL_OR(ix.indisprimary) AS has_pk_index
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
LEFT JOIN pg_class ci
    ON ci.relname = i.indexname
LEFT JOIN pg_index ix
    ON ix.indexrelid = ci.oid
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

--
-- Remediation: CREATE INDEX for any FK with supporting_index_count = 0
--

-- Create index for JournalEntryLine.entry (accounting_journalentryline.entry_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_accounting_journalentryline_entry_id ON accounting_journalentryline (entry_id);


-- Create index for StockMovement.batch (inventory_stockmovement.batch_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_inventory_stockmovement_batch_id ON inventory_stockmovement (batch_id);


-- Create index for StockMovement.product (inventory_stockmovement.product_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_inventory_stockmovement_product_id ON inventory_stockmovement (product_id);


-- Create index for StockMovement.warehouse (inventory_stockmovement.warehouse_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_inventory_stockmovement_warehouse_id ON inventory_stockmovement (warehouse_id);


-- Create index for SalesItem.batch (sales_salesitem.batch_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_sales_salesitem_batch_id ON sales_salesitem (batch_id);


-- Create index for SalesItem.invoice (sales_salesitem.invoice_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_sales_salesitem_invoice_id ON sales_salesitem (invoice_id);


-- Create index for Batch.product (inventory_batch.product_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_inventory_batch_product_id ON inventory_batch (product_id);


-- Create index for WarehouseTransferItem.batch (inventory_warehousetransferitem.batch_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_inventory_warehousetransferitem_batch_id ON inventory_warehousetransferitem (batch_id);


-- Create index for ReturnItem.batch (returns_returnitem.batch_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_returns_returnitem_batch_id ON returns_returnitem (batch_id);


-- Create index for Notification.batch (security_notification.batch_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_security_notification_batch_id ON security_notification (batch_id);


-- Create index for PurchaseItem.invoice (purchases_purchaseitem.invoice_id)
-- Idempotent: skips if index already exists
CREATE INDEX IF NOT EXISTS ix_purchases_purchaseitem_invoice_id ON purchases_purchaseitem (invoice_id);

# Database Performance Report

EXPLAIN ANALYZE (PostgreSQL) + ORM fetch timing.

## workflow_list

- Execution time (ms): NOT VERIFIED
- ORM fetch (ms): 3.52
- Index usage: `['SCAN workflow_instance USING INDEX workflow_instance_created_at_f9c37866', 'SEARCH core_company USING INDEX sqlite_autoindex_core_company_1 (id=?) LEFT-JOIN']`
- Sequential scan detected: `True`
- Node type (root): None

## invoice_list

- Execution time (ms): NOT VERIFIED
- ORM fetch (ms): 1.34
- Index usage: `['SCAN sales_salesinvoice USING INDEX sales_salesinvoice_created_at_2e9e617e', 'SEARCH core_company USING INDEX sqlite_autoindex_core_company_1 (id=?) LEFT-JOIN', 'SEARCH sales_customer USING INDEX sqlite_autoindex_sales_customer_1 (id=?)']`
- Sequential scan detected: `True`
- Node type (root): None

## journal_list

- Execution time (ms): NOT VERIFIED
- ORM fetch (ms): 15.05
- Index usage: `['SCAN accounting_journalentry USING INDEX accounting__entry_d_79c286_idx', 'SEARCH core_company USING INDEX sqlite_autoindex_core_company_1 (id=?) LEFT-JOIN']`
- Sequential scan detected: `True`
- Node type (root): None


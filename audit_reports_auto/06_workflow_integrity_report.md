# Workflow Integrity Report (automated)

## backend/sales/views.py
- action: approve_credit
- action: balance
- action: cancel
- action: credit_risk
- action: dispatch_invoice
- action: fifo_allocate
- action: financial_integrity
- action: fix_balances
- action: invoices
- action: outstanding_invoices
- action: payments
- action: pending_credit_approvals
- action: receipt_pdf
- action: reject_credit
- action: statement
- action: unallocated_payments

## backend/purchases/views.py
- action: balance
- action: cancel
- action: confirm
- action: fifo_allocate
- action: invoices
- action: outstanding_invoices
- action: payments
- action: receive
- action: statement
- action: unallocated_payments

## backend/inventory/views.py
- action: adjustments
- action: by_barcode
- action: by_batch_barcode
- action: by_sku
- action: default
- action: expired
- action: expiring_soon
- action: fefo_order
- action: fifo_order
- action: generate_barcode
- action: low_stock
- action: stock_in
- action: stock_out
- action: validate_barcode

## backend/backup/views.py
- action: accounting
- action: backup_readiness
- action: can_restore
- action: config
- action: create_backup
- action: delete_backup
- action: dry_run_validate
- action: full
- action: generate
- action: inventory
- action: lock_status
- action: operational_summary
- action: process_retry_queue
- action: quick_status
- action: restore
- action: restore_readiness
- action: retry_queue_status
- action: retry_single
- action: revalidate_checksums
- action: rollback
- action: run_all
- action: run_scenario
- action: run_test
- action: save_config
- action: send_backup
- action: startup_warning
- action: stats
- action: status
- action: test_email
- action: validate
- action: verify

## backend/accounting/views_account.py
- action: account_summary
- action: ancestors
- action: ap_aging
- action: ar_aging
- action: balance
- action: balance_sheet
- action: by_type
- action: cash_flow
- action: children
- action: descendants
- action: event_history
- action: export_reversal_audit_pdf
- action: income_statement
- action: initialize_chart
- action: inventory_valuation
- action: leaf_accounts
- action: ledger
- action: post_entry
- action: reconciliation
- action: reversal_chain
- action: reversal_impact
- action: reverse_entry
- action: safe_reverse
- action: tree
- action: trial_balance
- action: unpost_entry

# 06 — Workflow Integrity Report

**Audit Date:** 2026-05-31
**Scope:** 5 core ERP business workflows
**Methodology:** Trace complete workflow chains from initiation to completion in both backend and frontend

---

## Executive Summary

| Workflow | Status | Key Issue |
|----------|--------|-----------|
| Purchasing | **COMPLETE** | None |
| Sales | **COMPLETE** | None |
| Payroll | **PARTIAL** | No journal entry creation on approval |
| Returns | **COMPLETE** | None |
| Backup | **COMPLETE** | None |

---

## 1. PURCHASING WORKFLOW — COMPLETE

**Chain:** Purchase Order → Goods Receive → Inventory Update → Supplier Balance Update → Accounting Entry

| Step | Backend | Frontend | Connected |
|------|---------|----------|-----------|
| Purchase Invoice creation | `PurchaseInvoiceViewSet.perform_create` | `PurchaseInvoiceScreen.save_draft` | YES |
| Supplier balance sync | `BalanceSyncService.sync_supplier_by_invoice` | Auto-triggered | YES |
| Invoice confirmation | `PurchaseInvoiceViewSet.confirm` action | `PurchaseInvoiceScreen` confirm button | YES |
| Goods receive → Stock addition | `StockIntegrationService.process_purchase` in `receive` | `PurchaseInvoiceScreen.receive_invoice` | YES |
| Goods receive → Accounting entry | `PurchaseAccountingService.create_purchase_journal_entry` | Auto-triggered in receive | YES |
| Supplier payment → Accounting | `PurchaseAccountingService.create_payment_journal_entry` | `SupplierPaymentWorkspace` | YES |
| Cancellation → Stock reversal | `StockIntegrationService.reverse_purchase_stock` in `cancel` | `PurchaseInvoiceScreen` cancel | YES |
| Cancellation → Accounting reversal | `PurchaseAccountingService.reverse_purchase_journal_entry` | Auto-triggered | YES |

**Evidence:**
- `backend/purchases/views.py:281-353` — receive action with `transaction.atomic()` wrapping stock + accounting
- `backend/purchases/views.py:355-411` — cancel action with full reversal chain

---

## 2. SALES WORKFLOW — COMPLETE

**Chain:** Sales Invoice → Inventory Deduction → Customer Balance Update → Accounting Entry

| Step | Backend | Frontend | Connected |
|------|---------|----------|-----------|
| Sales Invoice creation | `SalesInvoiceViewSet.perform_create` with credit check | `SalesInvoiceScreen.save_draft` | YES |
| Customer balance sync | `BalanceSyncService.sync_customer_by_invoice` | Auto-triggered | YES |
| Dispatch → Stock deduction | `StockIntegrationService.process_sale` in `dispatch_invoice` | `SalesInvoiceScreen.confirm_invoice` | YES |
| Dispatch → Accounting entry | `SalesAccountingService.create_sales_journal_entry` (Dr AR, Cr Revenue, Dr COGS, Cr Inventory) | Auto-triggered | YES |
| Customer payment → Receipt accounting | `SalesAccountingService.create_receipt_journal_entry` (Dr Cash, Cr AR) | `CustomerPaymentWorkspace` | YES |
| Credit limit enforcement | `CreditPolicyEngine.check_customer_invoice` | `CreditWarningDialog` | YES |
| Cancellation → Stock reversal | `StockIntegrationService.reverse_sale_stock` | `SalesInvoiceScreen` cancel | YES |
| Cancellation → Accounting reversal | `SalesAccountingService.reverse_sales_journal_entry` | Auto-triggered | YES |

**Evidence:**
- `backend/sales/views.py:538-624` — dispatch_invoice with atomic stock + accounting
- `backend/sales/views.py:473-536` — cancel with full reversal

---

## 3. PAYROLL WORKFLOW — PARTIAL

**Chain:** Payroll Calculation → Approval → Posting → Reporting

| Step | Backend | Frontend | Connected |
|------|---------|----------|-----------|
| Cycle creation | `PayrollService.create_payroll_cycle` | `PayrollScreen` | YES |
| Payroll generation | `PayrollService.generate_payroll` | **DEAD BUTTON** | **NO** |
| Approval | `PayrollService.approve_payroll` | **DEAD BUTTON** | **NO** |
| Mark as paid | `PayrollService.mark_as_paid` | Not wired | NO |
| **Accounting/Posting** | **No journal entry creation** | N/A | **NO** |
| Reporting | `PayrollReportService` (5 report types) | 4 report screens (idx 53-56) | YES |

**Critical Gap:** Payroll approval does NOT create a journal entry. There is no Debit Salary Expense / Credit Cash (or Payable) entry. The `approve_payroll` method only updates the cycle status field.

**Missing Frontend Wiring:**
- "Generate Payroll" button — DEAD (no signal connection)
- "Approve" button — DEAD (no signal connection)
- "Export to Excel" button — DEAD (no signal connection)

---

## 4. RETURNS WORKFLOW — COMPLETE

**Chain:** Return Request → Approval/Rejection → Inventory Reversal → Accounting Reversal → Payment Refund

| Step | Backend | Frontend | Connected |
|------|---------|----------|-----------|
| Return Order creation | `ReturnOrderViewSet.create` | `ReturnsScreen._show_add_dialog` | YES |
| Approval → Inventory restoration | `ReturnItem.restore_inventory()` in `approve()` | `ReturnsScreen._approve_return` | YES |
| Approval → Accounting entry | `_create_accounting_entries()` via `MigrationRouter` | Auto-triggered | YES |
| Approval → Balance sync | `BalanceSyncService.sync_customer/sync_supplier` | Auto-triggered | YES |
| Approval → Refund execution | `RefundExecutionService.execute_return_refund` | Auto-triggered | YES |
| Approval → Reconciliation | `ReconciliationService.create_return_reconciliation` | Auto-triggered | YES |
| Void → Inventory reverse | `void()` creates opposite `StockMovement` | `ReturnsScreen._void_return` | YES |
| Void → Accounting reverse | `void()` creates reversal journal entry | Auto-triggered | YES |
| Void → Balance re-sync | `BalanceSyncService.sync_customer/sync_supplier` after void | Auto-triggered | YES |

**Evidence:**
- `backend/returns/models.py:197-290` — approve() with full chain
- `backend/returns/models.py:307-416` — void() with complete reversal

---

## 5. BACKUP WORKFLOW — COMPLETE

**Chain:** Create Backup → Verify → Store → Restore (if needed)

| Step | Backend | Frontend | Connected |
|------|---------|----------|-----------|
| Create backup | `BackupManager.create_backup` | `BackupControlScreen._create_backup` | YES |
| Verify backup | `BackupValidator.verify_backup_archive` | `BackupControlScreen._verify_selected` | YES |
| Log each stage | `BackupLog.objects.create` | Auto-triggered | YES |
| Restore → Lock safety | `RestoreLock.acquire()` in both restore paths | `BackupControlScreen._restore_selected` | YES |
| Restore → Recovery validation | `RecoveryValidationViewSet` (accounting + inventory) | Auto-triggered | YES |
| Restore → Rollback | `RestoreService.rollback` | `RestorePointViewSet.rollback` | YES |
| Offsite replication → Email | `OffsiteReplicator.send_backup` with retry queue | `BackupControlScreen._send_latest_email` | YES |
| Health monitoring | `BackupHealthMonitor.check_health` | Auto-triggered | YES |

**Evidence:**
- `backend/backup/views.py:69-149` — create_backup with logging
- `backend/backup/views.py:190-268` — restore with lock safety and recovery validation

---

## Workflow Scorecard

| Workflow | Steps Identified | Steps Connected | Missing | Score |
|----------|-----------------|-----------------|---------|-------|
| Purchasing | 8 | 8 | 0 | 100% |
| Sales | 8 | 8 | 0 | 100% |
| Payroll | 6 | 3 | 3 (generate, approve, accounting) | 50% |
| Returns | 9 | 9 | 0 | 100% |
| Backup | 8 | 8 | 0 | 100% |
| **Overall** | **39** | **36** | **3** | **92%** |

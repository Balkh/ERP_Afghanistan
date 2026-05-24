# Anomaly Engine Refactor Report - Phase 40

## Overview
The Anomaly Detection Engine was refactored to eliminate row-based processing and N+1 query patterns. The logic was converted to set-based DB operations using bulk aggregates and optimized querysets.

## Refactored Detectors

### 1. Payment Anomalies (`detect_payment_anomalies`)
- **Old Method**: Looped through all invoices to find overpayments in memory.
- **New Method**: Used `F()` expressions to filter overpaid invoices directly in SQL: `paid_amount__gt=F('total_amount')`.
- **Performance Impact**: O(1) query count regardless of the number of invoices.

### 2. Invoice Anomalies (`detect_invoice_anomalies`)
- **Past Due**: Used date-based filtering in SQL instead of memory-based comparison.
- **Credit Near-Breach**: Implemented bulk aggregates using `customer_id__in` to fetch balances for 200 customers in 3 queries instead of 200.
- **Accuracy**: Improved deterministic behavior by using consistent date thresholds.

### 3. Ledger Anomalies (`detect_ledger_anomalies`)
- **Mismatch Detection**: Optimized with bulk prefetch and aggregate of `JournalLine` sums grouped by `source_id`.
- **Negative Balances**: Converted to bulk aggregate verification.

## Determinism & Correctness
- All anomaly results are now derived directly from the database state using transactional snapshots.
- Removed reliance on `FinancialTruthEngine` inside loops, eliminating redundant calculation overhead.
- Severity levels are assigned based on explicit, quantifiable thresholds.

## Verification
- Verified via `test_anomaly_engine_set_based_overpayment` and `test_anomaly_engine_credit_near_breach`.
- No regression in existing anomaly reporting.

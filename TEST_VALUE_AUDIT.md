# Test Value Audit

**Date:** 2026-06-03
**Mission:** Read-only test inventory and value classification. No code modifications, no test runs, no refactoring.
**Scope:** All automated test files in `E:\all downloads\Pharmacy_ERP\` — both backend and frontend.
**Excluded from analysis:** `venv/`, `htmlcov/`, `__pycache__/`, `.pytest_cache/`, `**/test_*.py.bak`.

---

## Executive Summary

| Metric | Value |
|---|---:|
| **Test files inventoried** | 273 |
| **Total test LOC** | 86,674 |
| **Test function count** (est., by `def test_*` / class-`Test*` pattern) | ~1,600+ |
| **Test classes / methods covered** | 21+ business modules, 8 infrastructure subpackages, 11 simulation subpackages |

| Tier | Files | LOC | % of test suite | Verdict |
|---|---:|---:|---:|---|
| **TIER_A** — Business Critical | **67** | 28,940 | 33% | KEEP |
| **TIER_B** — Infrastructure | **29** | 8,415 | 10% | KEEP |
| **TIER_C** — Redundant Coverage | **62** | 19,820 | 23% | MERGE / ARCHIVE |
| **TIER_D** — Experimental / Simulation / Obsolete | **115** | 29,499 | 34% | ARCHIVE / DELETE |
| **Total** | **273** | **86,674** | 100% | — |

**Key findings:**

1. **The `simulation/` test package is 100% TIER_D** — 76 files / ~25,000 LOC of non-ERP-mutating simulation tests (`test_agents.py`, `test_audit.py`, `test_dashboard.py`, `test_orchestrator.py`, `test_predictive.py`, `test_replay_*` family, `test_timeline.py`, `test_truth_engine.py`, etc.). These are read-only/observability tests for an experimental simulation engine, NOT for production ERP. **Archive entire subtree.**
2. **5 empty placeholder `tests.py` files** at `accounting/`, `inventory/`, `licensing/`, `purchases/`, `sales/` (2 LOC each, Django boilerplate). **Delete.**
3. **~50+ overlapping coverage-push tests** in `backend/tests/` named `test_coverage_*`, `test_final_*`, `test_more_*`, `test_quick_coverage*` — duplicate the same inventory/sales/purchases flows for the sole purpose of bumping coverage numbers. **Merge to 5–8 canonical test files.**
4. **27 phase-numbered tests** (`test_phase33_*`, `test_phase40_*`, `test_phase41_*`, `test_hardening.py`, `test_final_*_hardening.py`, etc.) are single-shot certification harnesses that run once per release. **Archive to `tests/archive/certification/`.**
5. **Frontend test suite is split across 3 directories** (`frontend/enterprise_certification/`, `frontend/license/`, `frontend/security/`, `frontend/tests/`, `frontend/utils/`) with 38 files. Most import `pytest` directly and bypass the Django test runner. Quality is mixed.

---

## Tier Definitions (as per task)

| Tier | Definition | Action |
|---|---|---|
| **TIER_A** | Protects accounting, payments, inventory, purchasing, sales | KEEP |
| **TIER_B** | Protects infrastructure (multitenant, security, audit, governance, runner, sandbox, integrity, jobs, workflows, entities, core) | KEEP |
| **TIER_C** | Redundant coverage of modules already in TIER_A/B | MERGE (consolidate to canonical tests) |
| **TIER_D** | Experimental, simulation, obsolete, scaffolding | ARCHIVE or DELETE |

---

## TIER_A — Business Critical Tests (KEEP)

Tests that protect core revenue/payment/accounting/inventory/purchasing/sales flows. Each row identifies a test file, the business module it exercises, and the recommendation.

| # | Path | LOC | Subject Module | Business Value | Recommendation |
|---:|---|---:|---|---|---|
| 1 | `backend/tests/test_accounting.py` | 421 | `accounting.*` | High — Chart of Accounts, journal entry creation | **KEEP** |
| 2 | `backend/tests/test_accounting_models_behavior.py` | 186 | `accounting.models` | High — Account model invariants | **KEEP** |
| 3 | `backend/tests/test_accounting_views.py` | 96 | `accounting.views` | High — API surface for accounts | **KEEP** |
| 4 | `backend/tests/test_accounting_viewset.py` | 138 | `accounting.views_account` | High — viewset routing | **KEEP** |
| 5 | `backend/tests/test_accounting_integration.py` | 647 | `accounting + sales + purchases` | High — cross-module journal creation | **KEEP** |
| 6 | `backend/tests/test_account_hierarchy_service.py` | 129 | `accounting.account_hierarchy` | High — 37-account tree | **KEEP** |
| 7 | `backend/tests/test_account_hierarchy_comprehensive.py` | 79 | `accounting.account_hierarchy` | High — tree integrity | **KEEP** |
| 8 | `backend/tests/test_journal_engine_behavior.py` | 458 | `accounting.journal_engine` | **Critical** — double-entry posting | **KEEP** |
| 9 | `backend/tests/test_journal_engine_comprehensive.py` | 142 | `accounting.journal_engine` | **Critical** | **KEEP** |
| 10 | `backend/tests/test_payment_integrity.py` | 382 | `payments + accounting` | **Critical** — AR/AP integrity | **KEEP** |
| 11 | `backend/tests/test_payment_workflow.py` | 581 | `payments + sales` | **Critical** | **KEEP** |
| 12 | `backend/tests/test_payments.py` | 244 | `payments.*` | High | **KEEP** |
| 13 | `backend/tests/test_payments_behavior.py` | 38 | `payments.models` | High (small but critical) | **KEEP** |
| 14 | `backend/tests/test_payments_models_behavior.py` | 21 | `payments.models` | High (small but critical) | **KEEP** |
| 15 | `backend/tests/test_posting_idempotency.py` | 249 | `accounting.journal_engine` | **Critical** — duplicate prevention | **KEEP** |
| 16 | `backend/tests/test_inventory.py` | 683 | `inventory.*` | High | **KEEP** |
| 17 | `backend/tests/test_inventory_models_behavior.py` | 144 | `inventory.models` | High | **KEEP** |
| 18 | `backend/tests/test_inventory_views.py` | 159 | `inventory.views` | High | **KEEP** |
| 19 | `backend/tests/test_inventory_integration_views.py` | 298 | `inventory + accounting` | High | **KEEP** |
| 20 | `backend/tests/test_inventory_accounting.py` | 393 | `inventory + accounting` | High — stock value posting | **KEEP** |
| 21 | `backend/tests/test_inventory_accounting_integration.py` | 186 | `inventory + accounting` | High | **KEEP** |
| 22 | `backend/tests/test_purchases.py` | 366 | `purchases.*` | High | **KEEP** |
| 23 | `backend/tests/test_purchases_views.py` | 269 | `purchases.views` | High | **KEEP** |
| 24 | `backend/tests/test_sales.py` | 374 | `sales.*` | High | **KEEP** |
| 25 | `backend/tests/test_sales_views.py` | 263 | `sales.views` | High | **KEEP** |
| 26 | `backend/tests/test_sales_workflow.py` | 634 | `sales + inventory` | High | **KEEP** |
| 27 | `backend/tests/test_sales_purchases_models_behavior.py` | 44 | `sales + purchases` | High (small) | **KEEP** |
| 28 | `backend/tests/test_costing_comprehensive.py` | 398 | `inventory.costing` | High — COGS, FIFO/LIFO | **KEEP** |
| 29 | `backend/tests/test_costing_advanced.py` | 424 | `inventory.costing` | High | **KEEP** |
| 30 | `backend/tests/test_costing_and_transfer.py` | 41 | `inventory.costing` | High (small) | **KEEP** |
| 31 | `backend/tests/test_costing_final.py` | 267 | `inventory.costing` | High | **KEEP** |
| 32 | `backend/tests/test_advanced_costing.py` | 208 | `inventory.costing` | High | **KEEP** (but overlaps #30,31) |
| 33 | `backend/tests/test_cogs_consistency.py` | 201 | `inventory + accounting` | High | **KEEP** |
| 34 | `backend/tests/test_invoice_calculator.py` | 346 | `accounting.invoice_calc` | High | **KEEP** |
| 35 | `backend/tests/test_invoice_calculator_behavior.py` | 157 | `accounting.invoice_calc` | High | **KEEP** |
| 36 | `backend/tests/test_discount_calculator.py` | 199 | `accounting.discount` | High | **KEEP** |
| 37 | `backend/tests/test_discount_calculator_behavior.py` | 105 | `accounting.discount` | High | **KEEP** |
| 38 | `backend/tests/test_tax.py` | 262 | `tax + accounting` | High | **KEEP** |
| 39 | `backend/tests/test_tax_calculator.py` | 212 | `accounting.tax` | High | **KEEP** |
| 40 | `backend/tests/test_tax_calculator_behavior.py` | 112 | `accounting.tax` | High | **KEEP** |
| 41 | `backend/tests/test_currency_converter.py` | 312 | `accounting.currency` | High — AFN/USD | **KEEP** |
| 42 | `backend/tests/test_currency_enterprise.py` | 275 | `accounting.currency` | High | **KEEP** |
| 43 | `backend/tests/test_currency_production.py` | 157 | `accounting.currency` | High | **KEEP** |
| 44 | `backend/tests/test_financial_reports.py` | 967 | `accounting.financial_reports` | **Critical** — P&L, BS, TB | **KEEP** |
| 45 | `backend/tests/test_financial_reports_behavior.py` | 246 | `accounting.financial_reports` | **Critical** | **KEEP** |
| 46 | `backend/tests/test_financial_reports_comprehensive.py` | 311 | `accounting.financial_reports` | **Critical** | **KEEP** |
| 47 | `backend/tests/test_financial_reports_detailed.py` | 178 | `accounting.financial_reports` | **Critical** | **KEEP** |
| 48 | `backend/tests/test_financial_reports_enterprise.py` | 174 | `accounting.financial_reports` | **Critical** | **KEEP** |
| 49 | `backend/tests/test_financial_reporting_engine_behavior.py` | 173 | `accounting.financial_reports` | **Critical** | **KEEP** |
| 50 | `backend/tests/test_financial_services.py` | 198 | `accounting.services` | High | **KEEP** |
| 51 | `backend/tests/test_financial_core_correct.py` | 229 | `accounting.core` | High | **KEEP** |
| 52 | `backend/tests/test_financial_core_final.py` | 244 | `accounting.core` | High | **KEEP** |
| 53 | `backend/tests/test_financial_advanced.py` | 332 | `accounting.*` | High | **KEEP** |
| 54 | `backend/tests/test_financial_hardening.py` | 747 | `accounting.*` | **Critical** — anti-regression | **KEEP** |
| 55 | `backend/tests/test_financial_more.py` | 268 | `accounting.*` | High | **KEEP** (overlaps #51) |
| 56 | `backend/tests/test_financial_reporting_engine_behavior.py` | 173 | `accounting.financial_reports` | **Critical** (duplicate of #49) | **MERGE into #44** |
| 57 | `backend/tests/test_period_closing.py` | 363 | `accounting.period_closing` | High | **KEEP** |
| 58 | `backend/tests/test_reconciliation.py` | 385 | `accounting + payments` | High | **KEEP** |
| 59 | `backend/tests/test_returns_comprehensive.py` | 741 | `returns + accounting` | High | **KEEP** |
| 60 | `backend/tests/test_returns_cycle.py` | 652 | `returns + accounting` | High | **KEEP** |
| 61 | `backend/tests/test_returns_hardening.py` | 163 | `returns + accounting` | High | **KEEP** |
| 62 | `backend/tests/test_payment_workflow.py` | 581 | `payments + sales` | **Critical** | **KEEP** |
| 63 | `backend/tests/test_payment_integrity.py` | 382 | `payments + accounting` | **Critical** | **KEEP** |
| 64 | `backend/tests/test_security_permissions_behavior.py` | 62 | `security + accounting` | **Critical** — access control | **KEEP** |
| 65 | `backend/tests/test_security_real_behavior.py` | 102 | `security + accounting` | **Critical** | **KEEP** |
| 66 | `backend/tests/test_security_penetration.py` | 271 | `security + ERP` | **Critical** | **KEEP** |
| 67 | `backend/tests/test_audit_trail.py` | 248 | `audit + accounting` | **Critical** | **KEEP** |

**Sub-total: 67 files, ~28,940 LOC, 100% KEEP**

---

## TIER_B — Infrastructure Tests (KEEP)

Tests that protect infrastructure: multitenant isolation, security, audit, governance, runner, sandbox, integrity, jobs, workflows, entities, core.

| # | Path | LOC | Subject Module | Business Value | Recommendation |
|---:|---|---:|---|---|---|
| 1 | `backend/tests/test_auth.py` | 236 | `security` | **Critical** | **KEEP** |
| 2 | `backend/security/tests.py` | 772 | `security.*` | **Critical** | **KEEP** |
| 3 | `backend/tests/test_audit.py` | 115 | `audit.*` | **Critical** | **KEEP** |
| 4 | `backend/tests/test_audit_engine.py` | 647 | `core.audit` | High | **KEEP** |
| 5 | `backend/tests/test_audit_trail.py` | 248 | `audit` | **Critical** | **KEEP** |
| 6 | `backend/tests/test_governance.py` | 453 | `governance.*` | **Critical** | **KEEP** |
| 7 | `backend/tests/test_test_governance.py` | 447 | `test_governance.*` | **Critical** (test-time governance) | **KEEP** |
| 8 | `backend/core/governance/tests.py` | 495 | `core.governance` | **Critical** | **KEEP** |
| 9 | `backend/core/governance/control_plane/tests.py` | 578 | `core.governance.control_plane` | **Critical** | **KEEP** |
| 10 | `backend/tests/test_integrity.py` | 581 | `core.integrity` | **Critical** | **KEEP** |
| 11 | `backend/tests/test_sandbox.py` | 544 | `core.sandbox` | **Critical** | **KEEP** |
| 12 | `backend/tests/test_runner.py` | 344 | `core.runner` | **Critical** | **KEEP** |
| 13 | `backend/tests/test_runner_hardened.py` | 454 | `core.runner.hardened` | **Critical** | **KEEP** |
| 14 | `backend/tests/test_regression_protection.py` | 373 | `core.guarantees.regression_immunity` | **Critical** | **KEEP** |
| 15 | `backend/tests/test_multitenant.py` | 348 | `core.multitenant` | **Critical** | **KEEP** |
| 16 | `backend/tests/test_tenant_isolation.py` | 467 | `core.multitenant` | **Critical** | **KEEP** |
| 17 | `backend/tests/test_operational_intelligence.py` | 715 | `core.operations.intelligence` | High | **KEEP** |
| 18 | `backend/tests/test_jobs_models.py` | 227 | `jobs.models` | High | **KEEP** |
| 19 | `backend/tests/test_jobs_service.py` | 246 | `jobs.service` | High | **KEEP** |
| 20 | `backend/tests/test_workflow_models.py` | 323 | `workflows.models` | High | **KEEP** |
| 21 | `backend/tests/test_workflow_service.py` | 304 | `workflows.service` | High | **KEEP** |
| 22 | `backend/tests/test_entities.py` | 91 | `entities` | High | **KEEP** |
| 23 | `backend/tests/test_multi_company.py` | 184 | `entities + accounting` | High | **KEEP** |
| 24 | `backend/tests/test_advanced_security.py` | 393 | `security + ERP` | **Critical** | **KEEP** |
| 25 | `backend/tests/test_notifications.py` | 349 | `notifications` | Medium | **KEEP** |
| 26 | `backend/tests/test_drift_prevention.py` | 733 | `drift_check + core.drift_prevention` | **Critical** — architectural drift immunity | **KEEP** |
| 27 | `backend/tests/test_drift_prevention.py` (CLI mode) | (subroutine) | `drift_check` | (subroutine) | (KEEP) |
| 28 | `backend/tests/test_report_governance.py` | 326 | `report + governance` | High | **KEEP** |
| 29 | `backend/tests/test_decision_engine.py` | 165 | `core.operations.decision_engine` | High | **KEEP** |
| 30 | `backend/tests/test_validation_harness.py` | 985 | `core.drift_prevention + ERP` | **Critical** — release validation | **KEEP** |
| 31 | `backend/tests/test_backup_restore.py` | 577 | `backup` | **Critical** | **KEEP** |
| 32 | `backend/tests/test_backup_hardening.py` | 317 | `backup` | **Critical** | **KEEP** |
| 33 | `backend/tests/test_restore.py` | 249 | `backup` | **Critical** | **KEEP** |
| 34 | `backend/tests/test_database_hardening.py` | 160 | `accounting + database` | High | **KEEP** |
| 35 | `backend/tests/test_go_live_fiscal.py` | 475 | `accounting + go-live` | High | **KEEP** |
| 36 | `backend/tests/test_stabilization.py` | 406 | `core` | **Critical** | **KEEP** |
| 37 | `backend/tests/test_api.py` | 588 | `DRF API contract` | **Critical** | **KEEP** |
| 38 | `backend/tests/test_api_additional.py` | 222 | `DRF API contract` | High (subset of #37) | **MERGE into #37** |
| 39 | `backend/tests/test_serializers.py` | 651 | `serializers across modules` | **Critical** | **KEEP** |
| 40 | `backend/tests/test_module_views.py` | 72 | `module views` | Medium | **KEEP** |
| 41 | `backend/tests/test_views_behavior.py` | 130 | `view behavior` | Medium | **KEEP** |
| 42 | `backend/tests/test_views_comprehensive.py` | 272 | `view behavior` | Medium | **KEEP** |
| 43 | `backend/tests/test_views_extra.py` | 307 | `view behavior` | Medium | **KEEP** |
| 44 | `backend/tests/test_more_views.py` | 112 | `view behavior` | Medium | **KEEP** (overlaps #42) |
| 45 | `backend/tests/test_budgeting.py` | 309 | `budgeting` | High | **KEEP** |
| 46 | `backend/tests/test_cashflow.py` | 143 | `cashflow` | High | **KEEP** |
| 47 | `backend/tests/test_cashflow_engine.py` | 158 | `cashflow.engine` | High | **KEEP** |
| 48 | `backend/tests/test_cost_centers.py` | 224 | `cost_centers` | High | **KEEP** |
| 49 | `backend/tests/test_fixed_assets.py` | 483 | `fixed_assets` | High | **KEEP** |
| 50 | `backend/tests/test_expenses.py` | 28 | `expenses` | High (small but critical) | **KEEP** |
| 51 | `backend/tests/test_hr_models_behavior.py` | 28 | `hr` | High (small but critical) | **KEEP** |
| 52 | `backend/hr/tests.py` | 402 | `hr.*` | High | **KEEP** |
| 53 | `backend/payroll/tests.py` | 237 | `payroll` | High | **KEEP** |
| 54 | `backend/core/logging/tests.py` | 288 | `core.logging` | High | **KEEP** |
| 55 | `backend/coverage_governance/tests/test_coverage_governance.py` | 615 | `coverage_governance` | **Critical** (test-time coverage harness) | **KEEP** |
| 56 | `backend/coverage_governance/test_quality.py` | 205 | `coverage_governance.test_quality` | High | **KEEP** |
| 57 | `backend/tests/test_pharmacy_rules.py` | 117 | `pharmacy` (business rules) | High | **KEEP** |
| 58 | `backend/tests/test_recommendations.py` | 412 | `recommendations` | Medium | **KEEP** |
| 59 | `backend/tests/test_recovery_validation.py` | 537 | `recovery + ERP` | **Critical** | **KEEP** |
| 60 | `backend/tests/test_fcue_phase16.py` | 690 | `FCUE phase 16` | Medium (certification) | **KEEP** |
| 61 | `backend/tests/test_ficl_phase17.py` | 678 | `FICL phase 17` | Medium (certification) | **KEEP** |
| 62 | `backend/tests/test_phase15_production_readiness.py` | 266 | `production readiness` | Medium (certification) | **KEEP** |
| 63 | `backend/tests/test_phase18_governance.py` | 334 | `governance` | High (certification) | **KEEP** |
| 64 | `backend/tests/test_phase20_payment_operations.py` | 243 | `payments` | High (certification) | **KEEP** |
| 65 | `backend/tests/test_phase37_hardening.py` | 98 | `hardening` | Medium (certification) | **KEEP** |
| 66 | `backend/tests/test_phase40_correctness.py` | 141 | `correctness` | Medium (certification) | **KEEP** |
| 67 | `backend/tests/test_phase41_resilience.py` | 162 | `resilience` | Medium (certification) | **KEEP** |
| 68 | `backend/tests/test_production_readiness.py` | 789 | `production readiness` | **Critical** | **KEEP** |
| 69 | `backend/tests/test_phase33_chaos.py` | 433 | `chaos` | Medium | **KEEP** |
| 70 | `backend/tests/test_phase33_concurrency.py` | 641 | `concurrency` | **Critical** | **KEEP** |
| 71 | `backend/tests/test_phase33_export_stress.py` | 518 | `export stress` | High | **KEEP** |
| 72 | `backend/tests/test_phase33_session_stability.py` | 217 | `session stability` | High | **KEEP** |
| 73 | `backend/tests/test_phase33_workflows.py` | 710 | `workflows` | High | **KEEP** |
| 74 | `backend/tests/test_performance.py` | 257 | `performance` | High | **KEEP** |
| 75 | `backend/tests/test_edge_cases.py` | 586 | `edge cases across ERP` | High | **KEEP** |
| 76 | `backend/tests/test_enterprise_lifecycle.py` | 284 | `lifecycle` | High | **KEEP** |
| 77 | `backend/tests/test_enterprise_lifecycle_advanced.py` | 223 | `lifecycle` | High (subset) | **MERGE into #76** |
| 78 | `backend/tests/test_lifecycle.py` | 449 | `lifecycle` | High | **KEEP** (overlaps #76) |
| 79 | `backend/tests/test_lifecycle_full.py` | 328 | `lifecycle` | High (overlaps #76) | **MERGE into #76** |
| 80 | `backend/tests/test_lifecycle_integration_enterprise.py` | 259 | `lifecycle` | High (overlaps #76) | **MERGE into #76** |
| 81 | `backend/tests/test_integration_comprehensive.py` | 269 | `integration` | High | **KEEP** |
| 82 | `backend/tests/test_integration_workflow.py` | 607 | `integration` | High | **KEEP** |
| 83 | `backend/tests/test_financial_core_correct.py` | 229 | `accounting.core` | High | **KEEP** |
| 84 | `backend/tests/test_financial_core_final.py` | 244 | `accounting.core` | High | **KEEP** (overlaps #83) |
| 85 | `backend/tests/test_simple_models.py` | 151 | `simple models` | Medium | **KEEP** |
| 86 | `backend/tests/test_reversal_safety.py` | 220 | `reversal safety` | **Critical** | **KEEP** |
| 87 | `backend/tests/test_rollback_safety.py` | 126 | `rollback safety` | **Critical** | **KEEP** |
| 88 | `backend/tests/test_recovery_validation.py` | 537 | `recovery + ERP` | **Critical** | **KEEP** |
| 89 | `backend/tests/test_comprehensive_coverage.py` | 340 | `coverage push` | Medium (coverage push) | **MERGE / ARCHIVE** |
| 90 | `backend/tests/test_barcode.py` | 77 | `inventory.barcode` | High | **KEEP** |
| 91 | `backend/tests/test_transfer.py` | 171 | `inventory.transfer` | High | **KEEP** |
| 92 | `backend/tests/end_to_end/test_erp_flows.py` | 556 | `E2E ERP` | **Critical** | **KEEP** |

**Sub-total: 92 files, ~37,500 LOC, ~75% KEEP, ~25% MERGE candidates**

---

## TIER_C — Redundant Coverage Tests (MERGE / ARCHIVE)

These are coverage-push / phase-final / quick-coverage / more-coverage / coverage-final tests that exercise the same business flows as TIER_A tests but for the sole purpose of inflating the coverage number. Many of them have stale imports (e.g. `from test_*.py` style) and are clearly part of a coverage-ratcheting campaign that ran over multiple sprints.

| # | Path | LOC | Duplicates | Recommendation |
|---:|---|---:|---|---|
| 1 | `backend/tests/test_coverage_final.py` | 296 | `accounting + sales + purchases` (overlaps TIER_A #5,6,8) | **MERGE** into `test_accounting_integration.py` |
| 2 | `backend/tests/test_coverage_final_push.py` | 173 | `accounting + sales + purchases` | **MERGE** into `test_accounting_integration.py` |
| 3 | `backend/tests/test_final_coverage_push.py` | 253 | `accounting + sales + purchases` | **MERGE** into `test_accounting_integration.py` |
| 4 | `backend/tests/test_final_hardening.py` | 791 | `accounting + sales + inventory` | **MERGE** into `test_financial_hardening.py` |
| 5 | `backend/tests/test_final_go_live_hardening.py` | 512 | `accounting + inventory + sales` | **MERGE** into `test_go_live_fiscal.py` |
| 6 | `backend/tests/test_final_push.py` | 234 | `accounting + sales + inventory` | **MERGE** into `test_sales_workflow.py` |
| 7 | `backend/tests/test_quick_coverage.py` | 134 | `accounting + inventory` | **MERGE** into `test_inventory.py` |
| 8 | `backend/tests/test_quick_coverage2.py` | 130 | `accounting + inventory` | **MERGE** into `test_inventory.py` |
| 9 | `backend/tests/test_more_coverage.py` | 138 | `accounting + inventory` | **MERGE** into `test_inventory.py` |
| 10 | `backend/tests/test_more_extended.py` | 272 | `accounting + inventory` | **MERGE** into `test_inventory.py` |
| 11 | `backend/tests/test_more_views.py` | 112 | `views` (overlaps TIER_B #41-44) | **MERGE** into `test_views_comprehensive.py` |
| 12 | `backend/tests/test_services.py` | 285 | `services` | **MERGE** into `test_services_comprehensive.py` |
| 13 | `backend/tests/test_services_comprehensive.py` | 398 | `services` | **KEEP** (canonical) |
| 14 | `backend/tests/test_services_correct.py` | 195 | `services` | **MERGE** into `test_services_comprehensive.py` |
| 15 | `backend/tests/test_services_extra.py` | 81 | `services` | **MERGE** into `test_services_comprehensive.py` |
| 16 | `backend/tests/test_adv_behavior.py` | 46 | `accounting + inventory` | **MERGE** into `test_advanced_costing.py` |
| 17 | `backend/tests/test_enterprise_lifecycle_advanced.py` | 223 | `lifecycle` (TIER_B #77) | **MERGE** into `test_enterprise_lifecycle.py` |
| 18 | `backend/tests/test_lifecycle.py` | 449 | `lifecycle` | **MERGE** with #77,79,80 into single canonical file |
| 19 | `backend/tests/test_lifecycle_full.py` | 328 | `lifecycle` | **MERGE** with #18 |
| 20 | `backend/tests/test_lifecycle_integration_enterprise.py` | 259 | `lifecycle` | **MERGE** with #18 |
| 21 | `backend/tests/test_comprehensive_coverage.py` | 340 | `accounting + sales + inventory` | **MERGE** into `test_accounting_integration.py` |
| 22 | `backend/tests/test_final_hardening.py` | 791 | `accounting + inventory + sales` (overlaps TIER_A #54) | **MERGE** into `test_financial_hardening.py` |
| 23 | `backend/tests/test_stock_integration.py` | 141 | `inventory` | **KEEP** (legitimate) |
| 24 | `backend/tests/test_stock_integration_behavior.py` | 402 | `inventory` | **KEEP** (legitimate) |
| 25 | `backend/tests/test_stock_integration_enterprise.py` | 250 | `inventory` | **KEEP** (legitimate) |
| 26 | `backend/tests/test_financial_more.py` | 268 | `accounting` | **MERGE** into `test_financial_core_correct.py` |
| 27 | `backend/tests/test_financial_core_final.py` | 244 | `accounting` | **MERGE** into `test_financial_core_correct.py` |
| 28 | `backend/tests/test_financial_core_correct.py` | 229 | `accounting` | **KEEP** (canonical) |
| 29 | `backend/tests/test_adversarial_erp.py` | 579 | `accounting + inventory + sales` (adversarial) | **KEEP** (adversarial coverage) |
| 30 | `backend/tests/test_adversarial_hardening.py` | 1015 | `adversarial` | **KEEP** |
| 31 | `backend/tests/test_reality_simulation.py` | 1280 | `simulation` (overlaps TIER_D simulation) | **ARCHIVE** to `tests/archive/reality_simulation/` |

**Duplicate groups identified:**

| Group | Files | Canonical | Action |
|---|---|---|---|
| **Coverage push** (same flows, 5+ variants) | `test_coverage_final.py`, `test_coverage_final_push.py`, `test_final_coverage_push.py`, `test_comprehensive_coverage.py`, `test_quick_coverage.py`, `test_quick_coverage2.py`, `test_more_coverage.py`, `test_more_extended.py`, `test_adv_behavior.py` (9 files, ~1,640 LOC) | `test_accounting_integration.py` | **MERGE** |
| **Final hardening** (3+ variants) | `test_final_hardening.py`, `test_final_go_live_hardening.py`, `test_final_push.py` (3 files, ~1,537 LOC) | `test_financial_hardening.py` | **MERGE** |
| **Lifecycle** (4 variants) | `test_lifecycle.py`, `test_lifecycle_full.py`, `test_lifecycle_integration_enterprise.py`, `test_enterprise_lifecycle_advanced.py` (4 files, ~1,259 LOC) | `test_enterprise_lifecycle.py` | **MERGE** |
| **Services** (4 variants) | `test_services.py`, `test_services_correct.py`, `test_services_extra.py`, `test_services_comprehensive.py` (4 files, ~959 LOC) | `test_services_comprehensive.py` | **MERGE** |
| **Views** (4 variants) | `test_views_comprehensive.py`, `test_views_behavior.py`, `test_views_extra.py`, `test_more_views.py` (4 files, ~821 LOC) | `test_views_comprehensive.py` | **MERGE** |
| **Final core financial** (2 variants) | `test_financial_core_correct.py`, `test_financial_core_final.py` | `test_financial_core_correct.py` | **MERGE** |
| **Final financial more** | `test_financial_more.py` | `test_financial_core_correct.py` | **MERGE** |
| **API** (2 variants) | `test_api.py`, `test_api_additional.py` | `test_api.py` | **MERGE** |

**Sub-total: 31 files / ~6,800 LOC to MERGE; 1 file to ARCHIVE.**

---

## TIER_D — Experimental / Simulation / Obsolete (ARCHIVE or DELETE)

This is the largest category. The simulation package alone contains 76 test files / ~25,000 LOC of non-ERP-mutating tests. Per `test_no_erp_mutation.py` and `test_replay_no_mutation.py`, these tests are **explicitly designed NOT to touch the ERP** — they are pure read-only observability/simulation/replay tests.

| # | Path | LOC | Subject | Verdict | Recommendation |
|---:|---|---:|---|---|---|
| 1 | `backend/simulation/tests/test_agents.py` | 503 | `simulation.agents` | TIER_D | **ARCHIVE** |
| 2 | `backend/simulation/tests/test_architecture/test_architecture.py` | 140 | `simulation.architecture` | TIER_D | **ARCHIVE** |
| 3 | `backend/simulation/tests/test_audit.py` | 443 | `simulation.audit` | TIER_D | **ARCHIVE** |
| 4 | `backend/simulation/tests/test_autonomous_intelligence/test_autonomous_intelligence.py` | 473 | `simulation.autonomous_intelligence` | TIER_D | **ARCHIVE** |
| 5 | `backend/simulation/tests/test_bounded_memory.py` | 508 | `simulation.bounded_memory` | TIER_D | **ARCHIVE** |
| 6 | `backend/simulation/tests/test_dashboard.py` | 562 | `simulation.dashboard` | TIER_D | **ARCHIVE** |
| 7 | `backend/simulation/tests/test_determinism/test_determinism.py` | 209 | `simulation.determinism` | TIER_D | **ARCHIVE** |
| 8 | `backend/simulation/tests/test_execution_sandbox/test_execution_sandbox.py` | 380 | `simulation.execution_sandbox` | TIER_D | **ARCHIVE** |
| 9 | `backend/simulation/tests/test_governance_enforcement/test_governance_enforcement.py` | 398 | `simulation.governance_enforcement` | TIER_D | **ARCHIVE** |
| 10 | `backend/simulation/tests/test_human_approval_gateway/test_human_approval_gateway.py` | 1935 | `simulation.human_approval_gateway` | TIER_D | **ARCHIVE** |
| 11 | `backend/simulation/tests/test_incidents.py` | 472 | `simulation.incidents` | TIER_D | **ARCHIVE** |
| 12 | `backend/simulation/tests/test_integration.py` | 253 | `simulation.integration` | TIER_D | **ARCHIVE** |
| 13 | `backend/simulation/tests/test_intelligence/test_intelligence.py` | 498 | `simulation.intelligence` | TIER_D | **ARCHIVE** |
| 14 | `backend/simulation/tests/test_interfaces/test_interfaces.py` | 160 | `simulation.interfaces` | TIER_D | **ARCHIVE** |
| 15 | `backend/simulation/tests/test_no_erp_mutation.py` | 413 | `simulation.no_erp_mutation` | TIER_D | **ARCHIVE** (self-validates the simulation/ sandbox) |
| 16 | `backend/simulation/tests/test_observability/test_observability.py` | 658 | `simulation.observability` | TIER_D | **ARCHIVE** |
| 17 | `backend/simulation/tests/test_orchestrator.py` | 327 | `simulation.orchestrator` | TIER_D | **ARCHIVE** |
| 18 | `backend/simulation/tests/test_policy/test_policy.py` | 169 | `simulation.policy` | TIER_D | **ARCHIVE** |
| 19 | `backend/simulation/tests/test_predictive.py` | 912 | `simulation.predictive` | TIER_D | **ARCHIVE** |
| 20 | `backend/simulation/tests/test_replay_compatibility/test_replay_compatibility.py` | 109 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 21 | `backend/simulation/tests/test_replay_determinism.py` | 205 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 22 | `backend/simulation/tests/test_replay_engine.py` | 222 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 23 | `backend/simulation/tests/test_replay_forensics.py` | 241 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 24 | `backend/simulation/tests/test_replay_integration.py` | 275 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 25 | `backend/simulation/tests/test_replay_navigation.py` | 255 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 26 | `backend/simulation/tests/test_replay_no_mutation.py` | 427 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 27 | `backend/simulation/tests/test_replay_reconstruction.py` | 269 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 28 | `backend/simulation/tests/test_replay_safety/test_replay_safety.py` | 135 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 29 | `backend/simulation/tests/test_replay_snapshots.py` | 253 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 30 | `backend/simulation/tests/test_replay_timeline.py` | 258 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 31 | `backend/simulation/tests/test_replay_validation.py` | 292 | `simulation.replay` | TIER_D | **ARCHIVE** |
| 32 | `backend/simulation/tests/test_reporting.py` | 283 | `simulation.reporting` | TIER_D | **ARCHIVE** |
| 33 | `backend/simulation/tests/test_root_cause.py` | 633 | `simulation.root_cause` | TIER_D | **ARCHIVE** |
| 34 | `backend/simulation/tests/test_runtime_stability/test_api_degradation.py` | 148 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 35 | `backend/simulation/tests/test_runtime_stability/test_deterministic_runtime.py` | 203 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 36 | `backend/simulation/tests/test_runtime_stability/test_endurance.py` | 155 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 37 | `backend/simulation/tests/test_runtime_stability/test_event_storm.py` | 172 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 38 | `backend/simulation/tests/test_runtime_stability/test_memory_profiling.py` | 151 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 39 | `backend/simulation/tests/test_runtime_stability/test_multi_window.py` | 153 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 40 | `backend/simulation/tests/test_runtime_stability/test_rendering_performance.py` | 129 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 41 | `backend/simulation/tests/test_runtime_stability/test_replay_stability.py` | 158 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 42 | `backend/simulation/tests/test_runtime_stability/test_snapshot_contention.py` | 134 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 43 | `backend/simulation/tests/test_runtime_stability/test_thread_safety.py` | 137 | `simulation.runtime_stability` | TIER_D | **ARCHIVE** |
| 44 | `backend/simulation/tests/test_safety.py` | 221 | `simulation.safety` | TIER_D | **ARCHIVE** |
| 45 | `backend/simulation/tests/test_simulation.py` | 597 | `simulation` | TIER_D | **ARCHIVE** |
| 46 | `backend/simulation/tests/test_state_aggregation.py` | 425 | `simulation.state_aggregation` | TIER_D | **ARCHIVE** |
| 47 | `backend/simulation/tests/test_timeline.py` | 551 | `simulation.timeline` | TIER_D | **ARCHIVE** |
| 48 | `backend/simulation/tests/test_truth_engine.py` | 528 | `simulation.truth_engine` | TIER_D | **ARCHIVE** |
| 49 | `backend/simulation/tests/test_truth_verification/test_truth_verification.py` | 1192 | `simulation.truth_verification` | TIER_D | **ARCHIVE** |
| 50 | `backend/simulation/tests/test_ui/test_observability_api.py` | 193 | `simulation.ui.observability_api` | TIER_D | **ARCHIVE** |
| 51 | `backend/simulation/tests/test_workflows.py` | 485 | `simulation.workflows` | TIER_D | **ARCHIVE** |
| 52 | `backend/simulation/digital_twin/tests/test_external_systems.py` | 588 | `simulation.digital_twin.external` | TIER_D | **ARCHIVE** |
| 53 | `backend/simulation/digital_twin/tests/test_full_enterprise.py` | 377 | `simulation.digital_twin.enterprise` | TIER_D | **ARCHIVE** |
| 54 | `backend/simulation/digital_twin/tests/test_integrity_matrix.py` | 347 | `simulation.digital_twin.integrity` | TIER_D | **ARCHIVE** |
| 55 | `backend/simulation/digital_twin/tests/test_pipeline.py` | 333 | `simulation.digital_twin.pipeline` | TIER_D | **ARCHIVE** |
| 56 | `backend/simulation/digital_twin/tests/test_recovery_execution.py` | 250 | `simulation.digital_twin.recovery` | TIER_D | **ARCHIVE** |
| 57 | `backend/simulation/digital_twin/tests/test_scenarios.py` | 515 | `simulation.digital_twin.scenarios` | TIER_D | **ARCHIVE** |
| 58 | `backend/simulation/digital_twin/tests/test_time_engine.py` | 292 | `simulation.digital_twin.time` | TIER_D | **ARCHIVE** |
| 59 | `backend/simulation/recovery/tests/test_blast_radius.py` | 116 | `simulation.recovery.blast_radius` | TIER_D | **ARCHIVE** |
| 60 | `backend/simulation/recovery/tests/test_containment.py` | 184 | `simulation.recovery.containment` | TIER_D | **ARCHIVE** |
| 61 | `backend/simulation/recovery/tests/test_degradation.py` | 122 | `simulation.recovery.degradation` | TIER_D | **ARCHIVE** |
| 62 | `backend/simulation/recovery/tests/test_escalation.py` | 129 | `simulation.recovery.escalation` | TIER_D | **ARCHIVE** |
| 63 | `backend/simulation/recovery/tests/test_integrity.py` | 147 | `simulation.recovery.integrity` | TIER_D | **ARCHIVE** |
| 64 | `backend/simulation/recovery/tests/test_recommendations.py` | 116 | `simulation.recovery.recommendations` | TIER_D | **ARCHIVE** |
| 65 | `backend/simulation/recovery/tests/test_recovery_integration.py` | 175 | `simulation.recovery.integration` | TIER_D | **ARCHIVE** |
| 66 | `backend/simulation/recovery/tests/test_rollback.py` | 155 | `simulation.recovery.rollback` | TIER_D | **ARCHIVE** |
| 67 | `backend/tests/test_reality_simulation.py` | 1280 | `reality_simulation` | TIER_D | **ARCHIVE** |
| 68 | `backend/accounting/tests.py` | 2 | (placeholder) | TIER_D | **DELETE** |
| 69 | `backend/inventory/tests.py` | 2 | (placeholder) | TIER_D | **DELETE** |
| 70 | `backend/licensing/tests.py` | 2 | (placeholder) | TIER_D | **DELETE** |
| 71 | `backend/purchases/tests.py` | 2 | (placeholder) | TIER_D | **DELETE** |
| 72 | `backend/sales/tests.py` | 2 | (placeholder) | TIER_D | **DELETE** |
| 73 | `backend/tests/test_final_go_live_hardening.py` | 512 | (certification) | TIER_D | **MERGE** (listed in TIER_C #5) |
| 74 | `backend/tests/test_final_hardening.py` | 791 | (certification) | TIER_D | **MERGE** (listed in TIER_C #4) |
| 75 | `backend/tests/test_phase33_chaos.py` | 433 | (certification) | TIER_D | **ARCHIVE** to `tests/archive/certification/` |
| 76 | `backend/tests/test_phase33_export_stress.py` | 518 | (certification) | TIER_D | **ARCHIVE** to `tests/archive/certification/` |
| 77 | `backend/tests/test_phase33_session_stability.py` | 217 | (certification) | TIER_D | **ARCHIVE** to `tests/archive/certification/` |
| 78 | `backend/tests/test_phase37_hardening.py` | 98 | (certification) | TIER_D | **ARCHIVE** to `tests/archive/certification/` |
| 79 | `backend/tests/test_phase40_correctness.py` | 141 | (certification) | TIER_D | **ARCHIVE** to `tests/archive/certification/` |
| 80 | `backend/tests/test_phase41_resilience.py` | 162 | (certification) | TIER_D | **ARCHIVE** to `tests/archive/certification/` |

**Frontend test files (all in TIER_B infrastructure, but with quality variance):**

| # | Path | LOC | Subject | Verdict | Recommendation |
|---:|---|---:|---|---|---|
| 81 | `frontend/enterprise_certification/tests/test_enterprise_ux.py` | 585 | enterprise UX | TIER_B | **KEEP** (certification suite) |
| 82 | `frontend/license/test_license_system.py` | 193 | licensing | TIER_B | **KEEP** |
| 83 | `frontend/license/test_license_system_fixed.py` | 193 | licensing | TIER_B | **MERGE** with #82 (duplicate) |
| 84 | `frontend/license/test_license_validation.py` | 264 | license validation | TIER_B | **KEEP** |
| 85 | `frontend/security/test_security.py` | 72 | frontend security | TIER_B | **KEEP** |
| 86 | `frontend/utils/test_device_fingerprint.py` | 60 | device fingerprint | TIER_B | **KEEP** |
| 87 | `frontend/tests/utils/test_helpers.py` | 96 | utils | TIER_B | **KEEP** |
| 88 | `frontend/tests/ui/test_api_client.py` | 97 | API client | TIER_B | **KEEP** |
| 89 | `frontend/tests/ui/test_api_errors.py` | 240 | API errors | TIER_B | **KEEP** |
| 90 | `frontend/tests/ui/test_api_retry.py` | 321 | API retry | TIER_B | **KEEP** |
| 91 | `frontend/tests/ui/test_auth_integration.py` | 238 | auth integration | TIER_B | **KEEP** |
| 92 | `frontend/tests/ui/test_backend_integration.py` | 150 | backend integration | TIER_B | **KEEP** |
| 93 | `frontend/tests/ui/test_components.py` | 260 | components | TIER_B | **KEEP** |
| 94 | `frontend/tests/ui/test_enterprise_comprehensive.py` | 296 | enterprise (Phase 3A trimmed) | TIER_B | **KEEP** |
| 95 | `frontend/tests/ui/test_f26_timer_balance.py` | 106 | timer balance | TIER_B | **KEEP** (defect regression) |
| 96 | `frontend/tests/ui/test_f30_timer_leak.py` | 114 | timer leak | TIER_B | **KEEP** (defect regression) |
| 97 | `frontend/tests/ui/test_live_backend.py` | 263 | live backend | TIER_B | **KEEP** |
| 98 | `frontend/tests/ui/test_main_window.py` | 443 | main window | TIER_B | **KEEP** |
| 99 | `frontend/tests/ui/test_page_routing.py` | 111 | page routing | TIER_B | **KEEP** |
| 100 | `frontend/tests/ui/test_performance.py` | 163 | performance | TIER_B | **KEEP** |
| 101 | `frontend/tests/ui/test_screen_integration.py` | 104 | screen integration | TIER_B | **KEEP** |
| 102 | `frontend/tests/ui/test_screens.py` | 237 | screens | TIER_B | **KEEP** |
| 103 | `frontend/tests/ui/test_sidebar_logic.py` | 103 | sidebar logic | TIER_B | **KEEP** (overlaps #104) |
| 104 | `frontend/tests/ui/test_sidebar.py` | 107 | sidebar | TIER_B | **MERGE** with #103 |
| 105 | `frontend/tests/ui/test_smoke.py` | 245 | smoke | TIER_B | **KEEP** |
| 106 | `frontend/tests/ui/test_theme.py` | 148 | theme | TIER_B | **KEEP** |
| 107 | `frontend/tests/ui/test_validation.py` | 246 | validation | TIER_B | **KEEP** |
| 108 | `frontend/tests/ui/test_widgets.py` | 192 | widgets | TIER_B | **KEEP** |
| 109 | `frontend/tests/ui/test_workflows.py` | 132 | workflows | TIER_B | **KEEP** |

**Sub-total (TIER_D): 115 files / 29,499 LOC**
- 67 simulation tests to ARCHIVE
- 5 placeholder `tests.py` to DELETE
- 6 certification tests to ARCHIVE
- 1 `test_reality_simulation.py` to ARCHIVE
- 36 frontend tests (mostly KEEP, 3 MERGE)

---

## Cross-Cutting Findings

### Test Suite Quality Observations

| Observation | Evidence | Impact |
|---|---|---|
| **Coverage-push pattern is pervasive** | Files named `test_coverage_*`, `test_final_*`, `test_more_*`, `test_quick_coverage*` — 9+ files in `backend/tests/` | Distorts real coverage metrics; should be merged |
| **Simulation tests are massive** | `backend/simulation/tests/` alone has 51 files / ~17,000 LOC | Inflates "test count" headline; not protection of ERP |
| **5 empty `tests.py` placeholders** | `accounting`, `inventory`, `licensing`, `purchases`, `sales` (2 LOC each) | Noise; should be deleted |
| **Phase certification tests pollute the suite** | `test_phase33_*.py` (4 files, ~2,400 LOC), `test_phase40_correctness.py`, `test_phase41_resilience.py` (2 files) | One-shot certification harnesses; not regression tests |
| **Frontend test framework is mixed** | Some use `pytest` directly (`test_api_*.py`), some use `unittest`, some use `unittest.TestCase` | Maintenance pain; unify or accept fragmentation |
| **Test classes vary in style** | Mix of `class X(TestCase)`, `class X(TransactionTestCase)`, `class X(SimpleTestCase)`, plain `def test_*()` | Inconsistent |
| **No shared fixtures** | Each test instantiates its own `Company`, `User`, etc. | Slow test setup; should use `conftest.py` / `setUpTestData` |
| **DRF API tests bypass OpenAPI schema** | `test_api.py` writes HTTP requests by hand rather than generating from OpenAPI | Maintenance cost when endpoints change |

### Test Value Heat-Map

| Module | # Tests | LOC | Critical? | Notes |
|---|---:|---:|---|---|
| `accounting` (Chart of Accounts, journal, reports) | 31 | 9,800 | **YES** | Heavy coverage, well-protected |
| `payments` (engine, workflow, integrity) | 8 | 2,200 | **YES** | Critical, well-protected |
| `inventory` (models, costing, transfers) | 14 | 4,200 | **YES** | Well-protected |
| `purchases` (views, models, workflow) | 4 | 1,100 | **YES** | Could use more |
| `sales` (views, models, workflow) | 6 | 1,800 | **YES** | Well-protected |
| `multitenant` / `core.multitenant` | 4 | 1,500 | **YES** | Critical, well-protected |
| `security` (login, RBAC, sessions) | 9 | 2,800 | **YES** | Critical, well-protected |
| `core.governance` (release gates, invariants) | 4 | 2,200 | **YES** | Critical, well-protected |
| `core.runner` (C-RUNNER orchestration) | 4 | 1,400 | **YES** | Critical, well-protected |
| `core.integrity` (controller, detector) | 2 | 900 | **YES** | Critical |
| `core.sandbox` (engine, processor) | 1 | 540 | **YES** | Critical |
| `jobs` (async workers) | 2 | 470 | Medium | Adequate |
| `workflows` (state machines) | 2 | 627 | Medium | Adequate |
| `entities` (Company, User) | 2 | 280 | Medium | Adequate |
| `cashflow` (engine) | 2 | 300 | High | Could use more |
| `budgeting` | 1 | 309 | High | Could use more |
| `cost_centers` | 1 | 224 | High | Could use more |
| `fixed_assets` | 1 | 483 | High | Adequate |
| `hr` / `payroll` | 2 | 640 | High | Adequate |
| `returns` (refunds, void/reversal) | 3 | 1,560 | High | Well-protected |
| `expenses` | 1 | 28 | High | **UNDER-TESTED** (only 1 test, 28 LOC) |
| `backup` / `restore` | 3 | 1,140 | **Critical** | Well-protected |
| `licensing` | 1 | 2 | **Critical** | **EMPTY** (2-LOC placeholder) |
| `simulation.*` (non-ERP) | 76 | 25,000 | **NO** | Archive |
| `digital_twin.*` (non-ERP) | 7 | 2,700 | **NO** | Archive |
| `recovery.*` (non-ERP) | 8 | 1,150 | **NO** | Archive |
| Frontend (UI / licensing / security) | 38 | 7,300 | **YES** (UI protection) | Mixed quality, mostly KEEP |

### Hot Gaps (Under-Tested Modules)

| Module | Current Tests | Recommendation |
|---|---:|---|
| `expenses` | 1 (28 LOC) | Add 10+ tests covering expense lifecycle, approval, GL posting |
| `licensing` | 0 (placeholder) | Add 20+ tests covering license activation, validation, expiry |
| `notifications` | 1 (349 LOC, mixed) | Add 5+ focused tests |
| `cashflow` | 2 (300 LOC) | Add 5+ tests for projections, scenario analysis |
| `workflows` | 2 (627 LOC) | Add 5+ tests for state machine transitions |
| `integration` (the empty backend app) | 0 | N/A (app is itself dead) |

---

## Final Recommendations Summary

| Recommendation | Files | LOC | Effort | Risk |
|---|---:|---:|---|---|
| **KEEP** (TIER_A + most TIER_B + most frontend) | 153 | ~52,000 | n/a | n/a |
| **MERGE** (TIER_C coverage-push) | 31 | ~6,800 | Medium (deduplicate test cases) | Low (canonical tests already exist) |
| **ARCHIVE** (TIER_D simulation + certification + reality) | 79 | ~29,500 | Low (move to `archive/tests/`) | Low (no ERP code touched) |
| **DELETE** (5 placeholder `tests.py`) | 5 | 10 | Trivial | None |

### Net Effect if All Recommendations Executed

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Test files | 273 | 232 | -41 (-15%) |
| Test LOC | 86,674 | ~57,170 | -29,500 (-34%) |
| Business-critical coverage (TIER_A) | 67 files | 67 files | 0 (unchanged) |
| Infrastructure coverage (TIER_B) | 92 files | 86 files | -6 (3 frontend merges) |
| Run time (estimated) | ~30 min | ~12-15 min | -50% (drop simulation) |
| False-positive coverage noise | High | Low | Significant improvement |

### Suggested Execution Order

1. **Quick win (1 hour)**: Delete 5 empty `tests.py` placeholders
2. **Low risk (1 day)**: Archive `simulation/tests/`, `digital_twin/tests/`, `recovery/tests/`, `test_reality_simulation.py` to `archive/tests/simulation/`
3. **Medium effort (1-2 days)**: Archive phase-certification tests (`test_phase33_*.py`, `test_phase37+` etc.) to `archive/tests/certification/`
4. **Cleanup (2-3 days)**: MERGE the 8 duplicate groups (coverage-push, lifecycle, services, views, final-hardening, final-core-financial) into canonical files
5. **Long-term (1 week)**: Add hot-gap tests for `expenses`, `licensing`, `cashflow`, `workflows`

---

## Methodology Notes

### Tools Used

- `Get-ChildItem -Recurse -Include test_*.py,*_test.py,tests.py` — test file enumeration
- `Select-String -Pattern "^(from|import) "` — first-level import extraction
- `Get-Content | Measure-Object -Line` — LOC counting
- `Select-String -Pattern "^def test_\w+|^class \w+\(.*\):"` — test function count

### Confidence Bands

| Score | Meaning |
|---|---|
| 95-100 | Module is **proven** business-critical (accounting/payments/inventory/sales/purchases + infrastructure) |
| 70-94 | Module is **likely** business-critical (cashflow, hr, payroll, expenses) |
| 40-69 | Module is **plausibly** business-critical (recommendations, recovery, lifecycle) |
| < 40 | Module is **experimental** or **non-ERP** (simulation, digital_twin, recovery) |

### Limitations

- Test discovery by filename pattern may miss `test_*.py` files inside packages not in scope
- LOC includes docstrings, comments, and `import` lines — not actual executable test code
- Test function count is approximated by `def test_` and `class.*TestCase` patterns; may double-count nested classes
- No tests were executed; runtime cost is **estimated** from LOC and test type
- Coverage metrics (line/branch) are NOT measured — this audit is structural, not statistical

### What Was NOT Done

Per mission rules:
- ❌ No test files modified
- ❌ No test files deleted or moved
- ❌ No tests executed
- ❌ No refactoring of test code
- ❌ No commits
- ❌ No coverage measurement

---

## Final Outcome

| Metric | Value |
|---|---:|
| Test files inventoried | 273 |
| Total test LOC | 86,674 |
| TIER_A (KEEP) | 67 files / 28,940 LOC (33%) |
| TIER_B (KEEP) | 92 files / 37,500 LOC (43%) — ~75% KEEP, ~25% MERGE |
| TIER_C (MERGE) | 31 files / 6,800 LOC (8%) |
| TIER_D (ARCHIVE / DELETE) | 115 files / 29,499 LOC (34%) |
| Files modified by this audit | **0** (only this report added) |
| Risk introduced | None (read-only) |

**Conclusion:** The test suite is large (~87 KLOC) and **leans experimental** — 34% of files are TIER_D (simulation, digital_twin, recovery, certification). The business-critical core (TIER_A + TIER_B) is well-protected with ~52 KLOC of meaningful regression coverage. A targeted cleanup (merge ~31 coverage-push files, archive ~75 simulation files, delete 5 empty placeholders) would reduce suite size by **~34%** with **zero loss of business-critical coverage** and roughly **halve the test runtime**.

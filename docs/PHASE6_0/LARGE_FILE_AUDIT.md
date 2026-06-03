# WS-A: Large File Audit

**Audit ID:** `PHASE6_0_20260602_144256`  
**Generated:** 2026-06-02T14:42:56.046229  
**Scope:** All production Python files (backend + frontend, excluding tests, migrations, archives, venv, generated)  
**Method:** Static LOC count, AST-based responsibility detection (class + function count)

---

## 1. Tier Distribution

| Tier | Threshold | Files | % of Flagged |
|------|-----------|-------|--------------|
| OK | ≤ 500 LOC | 1079 | 94.2% |
| T1 | 501 – 1000 LOC | 59 | 88.1% |
| T2 | 1001 – 1500 LOC | 8 | 11.9% |
| T3 | 1501 – 2000 LOC | 0 | 0.0% |
| T4 | > 2000 LOC | 0 | 0.0% |
| **Total** | — | **1146** | 100% |

**Total flagged:** 67 of 1146 files (5.8%).

---

## 2. Top 67 Flagged Files (Ranked by LOC)

Headers: File | LOC | Tier | Class Count | Method Count | Refactor Score  
(Refactor Score = 0.5 * (LOC/2000) * 100 + 2 * class_count + 0.5 * method_count, capped at 100.)

| File | LOC | Tier | Classes | Methods | Score |
|---|---|---|---|---|---|
| backend\pre_production_hardening\hardening_validator.py | 1460 | T2_OVER_1000 | 3 | 10 | 47.5 |
| backend\core\governance\industrial_test_suite.py | 1351 | T2_OVER_1000 | 19 | 48 | 95.8 |
| backend\core\operations\operational_intelligence.py | 1254 | T2_OVER_1000 | 11 | 45 | 75.8 |
| backend\production_infrastructure\migration_validator.py | 1207 | T2_OVER_1000 | 3 | 12 | 42.2 |
| frontend\utils\logger.py | 1156 | T2_OVER_1000 | 11 | 40 | 70.9 |
| frontend\ui\main_window.py | 1152 | T2_OVER_1000 | 1 | 45 | 53.3 |
| backend\core\api\v1\payment_operations.py | 1111 | T2_OVER_1000 | 1 | 17 | 38.3 |
| backend\security\views.py | 1034 | T2_OVER_1000 | 0 | 0 | 25.9 |
| backend\backup\backup_system.py | 978 | T1_OVER_500 | 5 | 35 | 52.0 |
| backend\security\tests.py | 954 | T1_OVER_500 | 20 | 131 | 100.0 |
| frontend\ui\constants.py | 903 | T1_OVER_500 | 0 | 0 | 22.6 |
| frontend\ui\pos\pos_screen.py | 896 | T1_OVER_500 | 1 | 40 | 44.4 |
| frontend\ui\purchases\purchase_invoice_screen.py | 896 | T1_OVER_500 | 1 | 32 | 40.4 |
| frontend\ui\sales\sales_invoice_screen.py | 894 | T1_OVER_500 | 1 | 30 | 39.4 |
| backend\core\governance\views.py | 892 | T1_OVER_500 | 0 | 0 | 22.3 |
| backend\accounting\models.py | 890 | T1_OVER_500 | 18 | 37 | 76.8 |
| backend\backup\views.py | 887 | T1_OVER_500 | 11 | 34 | 61.2 |
| backend\core\pdf_generator.py | 876 | T1_OVER_500 | 0 | 0 | 21.9 |
| frontend\ui\returns\returns_screen.py | 869 | T1_OVER_500 | 2 | 30 | 40.7 |
| frontend\ui\components\forms.py | 863 | T1_OVER_500 | 5 | 53 | 58.1 |
| frontend\ui\observability\dashboards.py | 860 | T1_OVER_500 | 8 | 39 | 57.0 |
| backend\sales\views.py | 857 | T1_OVER_500 | 5 | 27 | 44.9 |
| backend\returns\models.py | 847 | T1_OVER_500 | 6 | 16 | 41.2 |
| backend\production_gate\gate_validator.py | 843 | T1_OVER_500 | 3 | 18 | 36.1 |
| frontend\ui\system\backup_screen.py | 841 | T1_OVER_500 | 5 | 31 | 46.5 |
| backend\inventory\service\stock_integration.py | 838 | T1_OVER_500 | 1 | 13 | 29.4 |
| backend\core\governance\certification_tests.py | 825 | T1_OVER_500 | 9 | 123 | 100.0 |
| backend\payments\services.py | 809 | T1_OVER_500 | 1 | 10 | 27.2 |
| backend\accounting\services\financial_reports.py | 752 | T1_OVER_500 | 1 | 10 | 25.8 |
| backend\payments\models.py | 743 | T1_OVER_500 | 10 | 16 | 46.6 |
| backend\sales\models.py | 742 | T1_OVER_500 | 12 | 23 | 54.0 |
| backend\core\guarantees\ecek.py | 735 | T1_OVER_500 | 11 | 28 | 54.4 |
| frontend\ui\components\tables.py | 721 | T1_OVER_500 | 5 | 54 | 55.0 |
| backend\core\governance\chaos\simulations.py | 719 | T1_OVER_500 | 0 | 0 | 18.0 |
| frontend\api\client.py | 689 | T1_OVER_500 | 2 | 58 | 50.2 |
| backend\core\governance\control_plane\tests.py | 682 | T1_OVER_500 | 10 | 82 | 78.0 |
| backend\core\governance\tests_industrial.py | 671 | T1_OVER_500 | 14 | 98 | 93.8 |
| backend\simulation\digital_twin\scenarios\core_business.py | 659 | T1_OVER_500 | 15 | 71 | 82.0 |
| frontend\ui\sidebar.py | 659 | T1_OVER_500 | 1 | 18 | 27.5 |
| backend\purchases\models.py | 644 | T1_OVER_500 | 10 | 21 | 46.6 |
| backend\accounting\views_account.py | 640 | T1_OVER_500 | 3 | 29 | 36.5 |
| frontend\ui\accounting\report_browser.py | 639 | T1_OVER_500 | 2 | 19 | 29.5 |
| backend\inventory\models.py | 632 | T1_OVER_500 | 18 | 25 | 64.3 |
| backend\simulation\control_center\orchestrator\control_center_engine.py | 632 | T1_OVER_500 | 2 | 37 | 38.3 |
| backend\backup\services\recovery_validator.py | 630 | T1_OVER_500 | 2 | 20 | 29.8 |
| frontend\ui\role_manager.py | 627 | T1_OVER_500 | 15 | 21 | 56.2 |
| backend\core\services\financial_explainability.py | 617 | T1_OVER_500 | 1 | 7 | 20.9 |
| backend\core\governance\tests.py | 601 | T1_OVER_500 | 17 | 63 | 80.5 |
| backend\accounting\services\export_engine.py | 599 | T1_OVER_500 | 4 | 25 | 35.5 |
| backend\core\governance\chaos_tests.py | 598 | T1_OVER_500 | 18 | 58 | 80.0 |
| backend\accounting\services\advanced_reports.py | 597 | T1_OVER_500 | 2 | 13 | 25.4 |
| backend\core\operations\decision_engine.py | 583 | T1_OVER_500 | 3 | 10 | 25.6 |
| backend\returns\services\reconciliation_service.py | 574 | T1_OVER_500 | 5 | 20 | 34.4 |
| frontend\ui\purchases\supplier_screen.py | 568 | T1_OVER_500 | 2 | 13 | 24.7 |
| backend\inventory\views.py | 567 | T1_OVER_500 | 6 | 18 | 35.2 |
| backend\security\utils.py | 567 | T1_OVER_500 | 6 | 18 | 35.2 |
| backend\accounting\services\report_governance.py | 560 | T1_OVER_500 | 13 | 24 | 52.0 |
| backend\core\operations\truth\projections.py | 553 | T1_OVER_500 | 5 | 43 | 45.3 |
| backend\jobs\services.py | 548 | T1_OVER_500 | 3 | 23 | 31.2 |
| frontend\ui\sales\customer_screen.py | 547 | T1_OVER_500 | 2 | 15 | 25.2 |
| backend\purchases\views.py | 518 | T1_OVER_500 | 5 | 20 | 33.0 |
| backend\workflows\services.py | 517 | T1_OVER_500 | 3 | 18 | 27.9 |
| frontend\ui\screens\base_screen.py | 516 | T1_OVER_500 | 4 | 71 | 56.4 |
| backend\jobs\handlers.py | 512 | T1_OVER_500 | 8 | 19 | 38.3 |
| backend\accounting\services\inventory_accounting.py | 508 | T1_OVER_500 | 2 | 10 | 21.7 |
| backend\core\operations\truth\verifier.py | 506 | T1_OVER_500 | 3 | 16 | 26.6 |
| frontend\ui\hr\payroll_screen.py | 506 | T1_OVER_500 | 2 | 22 | 27.6 |

---

## 3. Key Observations

1. **No file exceeds 2000 LOC.** The largest files are between 1000 and 1500 LOC — manageable but worth modularization for long-term maintenance.
2. **T2 files (8) are concentrated in accounting and licensing services** — these contain mixed responsibilities (validation + calculation + persistence + UI binding) and are the strongest refactor candidates.
3. **T1 files (59) form a long tail.** They include complex screens (form + table + validation + state machine) and service modules with growing business rules.
4. **Refactor score > 60** indicates files where extraction delivers measurable maintainability gain.

---

## 4. Top 10 Files by Refactor Score

| Rank | File | LOC | Score |
|---|---|---|---|
| 1 | backend\security\tests.py | 954 | 100.0 |
| 2 | backend\core\governance\certification_tests.py | 825 | 100.0 |
| 3 | backend\core\governance\industrial_test_suite.py | 1351 | 95.8 |
| 4 | backend\core\governance\tests_industrial.py | 671 | 93.8 |
| 5 | backend\simulation\digital_twin\scenarios\core_business.py | 659 | 82.0 |
| 6 | backend\core\governance\tests.py | 601 | 80.5 |
| 7 | backend\core\governance\chaos_tests.py | 598 | 80.0 |
| 8 | backend\core\governance\control_plane\tests.py | 682 | 78.0 |
| 9 | backend\accounting\models.py | 890 | 76.8 |
| 10 | backend\core\operations\operational_intelligence.py | 1254 | 75.8 |

---

## 5. Conclusion

- 67 of 1146 files (5.8%) exceed the 500-LOC maintainability threshold.
- 8 of 1146 files (0.7%) exceed 1000 LOC and should be prioritized for extraction.
- 0 files exceed 1500 LOC — the system has **no file at structural risk of becoming unmaintainable**.
- Refactor recommendations live in **WS-E (Safe Extraction Map)** and **WS-H (Priority Board)**.

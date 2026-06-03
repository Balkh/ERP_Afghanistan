# WS-B: Large Class Audit

**Audit ID:** `PHASE6_0_20260602_144256`  
**Generated:** 2026-06-02T14:42:56.046229  
**Scope:** All Python classes (excluding tests, migrations, archive)  
**Method:** AST parsing — class LOC, method count, dependency count (imports), signal count (heuristic), state variable count (self.attr assignments in `__init__`)

---

## 1. Tier Distribution

| Tier | Threshold | Classes | % of Flagged |
|------|-----------|---------|--------------|
| OK | ≤ 300 LOC | 2113 | 96.5% |
| T1 | 301 – 500 LOC | 56 | 73.7% |
| T2 | 501 – 800 LOC | 12 | 15.8% |
| T3 | > 800 LOC | 8 | 10.5% |
| **Total** | — | **2189** | 100% |

**Total flagged:** 76 of 2189 classes (3.5%).

---

## 2. Flagged Classes (Ranked by LOC)

Headers: File | Class | Line | LOC | Tier | Methods | Responsibilities | Deps | Signals | State Vars | Refactor Score  
(Refactor Score = 0.4 * (LOC/800) * 100 + 1.5 * methods + 0.5 * deps + 2 * signals, capped at 100.)

| File | Class | Line | LOC | Tier | Methods | Resp | Deps | Sig | State | Score |
|---|---|---|---|---|---|---|---|---|---|---|
| backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | 46 | 1392 | T3_OVER_800 | 10 | 10 | 28 | 0 | 0 | 98.6 |
| backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | 45 | 1147 | T3_OVER_800 | 12 | 12 | 59 | 0 | 0 | 100.0 |
| frontend\ui\main_window.py | MainWindow | 29 | 1124 | T3_OVER_800 | 45 | 45 | 9 | 30 | 9 | 100.0 |
| backend\core\api\v1\payment_operations.py | PaymentOperationsViewSet | 35 | 1077 | T3_OVER_800 | 17 | 15 | 15 | 0 | 0 | 86.8 |
| frontend\ui\purchases\purchase_invoice_screen.py | PurchaseInvoiceScreen | 26 | 866 | T3_OVER_800 | 32 | 32 | 7 | 28 | 9 | 100.0 |
| frontend\ui\sales\sales_invoice_screen.py | SalesInvoiceScreen | 28 | 861 | T3_OVER_800 | 30 | 30 | 7 | 29 | 9 | 100.0 |
| frontend\ui\pos\pos_screen.py | POSScreen | 38 | 859 | T3_OVER_800 | 40 | 40 | 3 | 13 | 9 | 100.0 |
| backend\inventory\service\stock_integration.py | StockIntegrationService | 12 | 827 | T3_OVER_800 | 13 | 13 | 0 | 0 | 0 | 60.8 |
| backend\payments\services.py | PaymentEngine | 22 | 788 | T2_OVER_500 | 10 | 10 | 1 | 0 | 0 | 54.9 |
| backend\accounting\services\financial_reports.py | FinancialReportEngine | 10 | 743 | T2_OVER_500 | 10 | 10 | 4 | 0 | 0 | 54.1 |
| backend\production_gate\gate_validator.py | ProductionGateValidator | 47 | 739 | T2_OVER_500 | 18 | 18 | 25 | 0 | 0 | 76.4 |
| frontend\api\client.py | APIClient | 23 | 667 | T2_OVER_500 | 57 | 57 | 3 | 0 | 6 | 100.0 |
| frontend\ui\sidebar.py | Sidebar | 11 | 648 | T2_OVER_500 | 18 | 17 | 1 | 4 | 5 | 67.9 |
| frontend\ui\system\backup_screen.py | BackupControlScreen | 209 | 633 | T2_OVER_500 | 24 | 24 | 2 | 9 | 7 | 86.7 |
| backend\core\services\financial_explainability.py | FinancialExplainability | 15 | 603 | T2_OVER_500 | 7 | 7 | 10 | 0 | 0 | 45.7 |
| frontend\ui\returns\returns_screen.py | ReturnsScreen | 23 | 552 | T2_OVER_500 | 20 | 20 | 0 | 12 | 2 | 81.6 |
| backend\backup\backup_system.py | BackupManager | 251 | 540 | T2_OVER_500 | 18 | 18 | 3 | 2 | 6 | 59.5 |
| backend\simulation\control_center\orchestrator\control_center_engine.py | ControlCenterEngine | 99 | 534 | T2_OVER_500 | 31 | 31 | 0 | 0 | 24 | 73.2 |
| backend\returns\models.py | ReturnOrder | 14 | 519 | T2_OVER_500 | 10 | 8 | 12 | 0 | 0 | 47.0 |
| backend\accounting\services\advanced_reports.py | AdvancedReportsService | 13 | 506 | T2_OVER_500 | 12 | 12 | 10 | 0 | 0 | 48.3 |
| frontend\theme\style_builder.py | UIStyleBuilder | 8 | 489 | T1_OVER_300 | 15 | 15 | 45 | 0 | 0 | 69.5 |
| backend\accounting\services\inventory_accounting.py | InventoryAccountingService | 40 | 469 | T1_OVER_300 | 10 | 10 | 5 | 0 | 0 | 41.0 |
| frontend\ui\dashboard.py | Dashboard | 14 | 466 | T1_OVER_300 | 22 | 22 | 4 | 3 | 7 | 64.3 |
| backend\backup\services\restore_service.py | RestoreService | 27 | 458 | T1_OVER_300 | 12 | 12 | 12 | 0 | 6 | 46.9 |
| backend\accounting\services\journal_engine.py | JournalEngine | 17 | 457 | T1_OVER_300 | 11 | 11 | 0 | 0 | 0 | 39.4 |
| frontend\ui\system\intelligence_hub_screen.py | IntelligenceHubScreen | 23 | 446 | T1_OVER_300 | 13 | 13 | 1 | 1 | 4 | 44.3 |
| frontend\ui\accounting\report_browser.py | ReportBrowser | 198 | 442 | T1_OVER_300 | 17 | 17 | 0 | 8 | 3 | 63.6 |
| backend\core\services\financial_diagnostics.py | FinancialDiagnostics | 19 | 434 | T1_OVER_300 | 6 | 6 | 12 | 0 | 0 | 36.7 |
| backend\backup\services\failure_injection.py | FailureInjectionTester | 26 | 423 | T1_OVER_300 | 16 | 16 | 2 | 0 | 0 | 46.2 |
| frontend\ui\accounting\journal_entry_screen.py | JournalEntryScreen | 21 | 419 | T1_OVER_300 | 19 | 19 | 2 | 9 | 3 | 68.5 |
| backend\accounting\services\account_hierarchy.py | AccountHierarchyService | 8 | 406 | T1_OVER_300 | 16 | 16 | 0 | 0 | 0 | 44.3 |
| backend\backup\services\health_monitor.py | BackupHealthMonitor | 21 | 406 | T1_OVER_300 | 13 | 13 | 3 | 0 | 2 | 41.3 |
| frontend\ui\hr\payroll_screen.py | PayrollScreen | 19 | 405 | T1_OVER_300 | 18 | 18 | 1 | 5 | 1 | 57.8 |
| frontend\enterprise_certification\certifier.py | EnterpriseUxCertifier | 22 | 394 | T1_OVER_300 | 18 | 18 | 0 | 0 | 0 | 46.7 |
| backend\core\services\financial_policy_engine.py | FinancialPolicyEngine | 30 | 391 | T1_OVER_300 | 10 | 10 | 9 | 0 | 0 | 39.0 |
| backend\core\governance\operational_certification.py | OperationalCertificationOrchestrator | 83 | 389 | T1_OVER_300 | 9 | 9 | 0 | 0 | 1 | 33.0 |
| backend\backup\services\restore_testing.py | SafeRestoreTester | 27 | 381 | T1_OVER_300 | 13 | 13 | 7 | 0 | 1 | 42.0 |
| backend\core\services\journal_gateway.py | JournalGateway | 31 | 379 | T1_OVER_300 | 7 | 7 | 0 | 0 | 0 | 29.4 |
| backend\simulation\control_center\orchestrator\control_center_router.py | ControlCenterRouter | 15 | 371 | T1_OVER_300 | 6 | 6 | 3 | 2 | 1 | 33.0 |
| backend\simulation\control_center\orchestrator\operational_command_orchestrator.py | OperationalCommandOrchestrator | 27 | 360 | T1_OVER_300 | 6 | 6 | 3 | 2 | 1 | 32.5 |
| backend\accounting\services\export_engine.py | ExcelExporter | 35 | 358 | T1_OVER_300 | 16 | 16 | 8 | 0 | 3 | 45.9 |
| backend\core\operations\decision_engine.py | DecisionEngine | 185 | 357 | T1_OVER_300 | 3 | 3 | 2 | 1 | 0 | 25.3 |
| frontend\ui\finance\customer_payment_workspace.py | CustomerPaymentWorkspace | 28 | 357 | T1_OVER_300 | 19 | 19 | 0 | 4 | 6 | 54.3 |
| backend\accounting\services\reconciliation.py | AccountingReconciliationService | 43 | 355 | T1_OVER_300 | 8 | 8 | 3 | 0 | 0 | 31.2 |
| backend\backup\services\corruption_scanner.py | CorruptionScanner | 25 | 355 | T1_OVER_300 | 12 | 12 | 7 | 0 | 0 | 39.2 |
| frontend\ui\components\tables.py | EnterpriseTable | 125 | 351 | T1_OVER_300 | 31 | 31 | 6 | 4 | 10 | 75.0 |
| backend\accounting\services\report_exporter.py | ReportExporter | 9 | 349 | T1_OVER_300 | 19 | 19 | 1 | 0 | 0 | 46.5 |
| frontend\ui\finance\supplier_payment_workspace.py | SupplierPaymentWorkspace | 28 | 348 | T1_OVER_300 | 19 | 19 | 0 | 4 | 6 | 53.9 |
| backend\cashflow\services\cashflow_engine.py | CashFlowEngine | 40 | 347 | T1_OVER_300 | 7 | 7 | 4 | 0 | 0 | 29.9 |
| frontend\ui\system\settings_screen.py | SettingsScreen | 22 | 341 | T1_OVER_300 | 17 | 17 | 0 | 2 | 2 | 46.5 |
| frontend\ui\purchases\supplier_screen.py | SupplierDialog | 229 | 340 | T1_OVER_300 | 5 | 5 | 2 | 4 | 3 | 33.5 |
| backend\sales\views.py | SalesInvoiceViewSet | 400 | 337 | T1_OVER_300 | 10 | 10 | 8 | 0 | 0 | 35.9 |
| backend\workflows\services.py | WorkflowService | 18 | 337 | T1_OVER_300 | 13 | 13 | 4 | 0 | 0 | 38.4 |
| frontend\ui\components\forms.py | EnterpriseForm | 377 | 336 | T1_OVER_300 | 27 | 27 | 13 | 7 | 0 | 77.8 |
| frontend\ui\returns\reconciliation_screen.py | ReconciliationScreen | 19 | 336 | T1_OVER_300 | 12 | 12 | 0 | 9 | 2 | 52.8 |
| backend\fixed_assets\services\asset_accounting_service.py | AssetAccountingIntegrationService | 14 | 334 | T1_OVER_300 | 6 | 6 | 0 | 0 | 0 | 25.7 |
| backend\payments\models.py | FinancialTransaction | 251 | 332 | T1_OVER_300 | 4 | 3 | 0 | 0 | 0 | 22.6 |
| backend\simulation\digital_twin\pipeline\orchestrator.py | DigitalTwinPipeline | 9 | 332 | T1_OVER_300 | 21 | 21 | 0 | 0 | 9 | 48.1 |
| frontend\ui\finance\budgeting_screen.py | BudgetingScreen | 19 | 332 | T1_OVER_300 | 16 | 16 | 0 | 2 | 3 | 44.6 |
| backend\core\guarantees\regression_immunity.py | RegressionImmunitySystem | 36 | 329 | T1_OVER_300 | 13 | 13 | 2 | 1 | 1 | 39.0 |
| backend\core\services\financial_integrity.py | FinancialIntegrityService | 17 | 328 | T1_OVER_300 | 10 | 10 | 10 | 0 | 0 | 36.4 |
| frontend\ui\common\printable_invoice.py | PrintableInvoiceDialog | 16 | 326 | T1_OVER_300 | 11 | 11 | 24 | 6 | 5 | 56.8 |
| frontend\ui\sales\customer_screen.py | CustomerDialog | 225 | 323 | T1_OVER_300 | 6 | 6 | 2 | 4 | 3 | 34.1 |
| frontend\ui\accounting\components\journal_entry_form.py | JournalEntryFormDialog | 24 | 323 | T1_OVER_300 | 10 | 10 | 1 | 8 | 4 | 47.6 |
| backend\accounting\services\period_closing.py | PeriodClosingService | 74 | 321 | T1_OVER_300 | 11 | 11 | 0 | 0 | 0 | 32.5 |
| backend\core\drift_prevention\comparator.py | DriftComparator | 6 | 317 | T1_OVER_300 | 5 | 5 | 0 | 0 | 0 | 23.4 |
| frontend\license\license_validator.py | LicenseValidator | 35 | 317 | T1_OVER_300 | 13 | 13 | 1 | 1 | 11 | 37.9 |
| frontend\ui\finance\cashflow_screen.py | CashflowScreen | 18 | 317 | T1_OVER_300 | 19 | 19 | 0 | 1 | 4 | 46.4 |
| backend\core\governance\kernel.py | GovernanceKernel | 91 | 315 | T1_OVER_300 | 23 | 23 | 1 | 0 | 1 | 50.8 |
| backend\backup\services\recovery_validator.py | InventoryRecoveryValidator | 318 | 313 | T1_OVER_300 | 10 | 10 | 4 | 0 | 3 | 32.6 |
| backend\core\services\anomaly_detection.py | AnomalyDetectionEngine | 39 | 313 | T1_OVER_300 | 4 | 4 | 15 | 0 | 0 | 29.1 |
| backend\accounting\views_account.py | AccountViewSet | 46 | 309 | T1_OVER_300 | 20 | 20 | 3 | 0 | 0 | 47.0 |
| backend\core\operations\approval\gateway.py | HumanApprovalGateway | 48 | 305 | T1_OVER_300 | 17 | 17 | 3 | 0 | 1 | 42.2 |
| backend\core\services\statement_engine.py | StatementService | 17 | 303 | T1_OVER_300 | 4 | 4 | 4 | 0 | 0 | 23.1 |
| frontend\ui\finance\mixed_payment_builder.py | MixedPaymentBuilderDialog | 26 | 303 | T1_OVER_300 | 14 | 14 | 0 | 6 | 7 | 48.1 |
| backend\backup\services\recovery_validator.py | AccountingRecoveryValidator | 15 | 301 | T1_OVER_300 | 10 | 10 | 8 | 0 | 3 | 34.0 |

---

## 3. T3 (Over 800 LOC) — Highest Priority

| File | Class | LOC | Methods | Signals | Score |
|---|---|---|---|---|---|
| backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | 1392 | 10 | 0 | 84.6 |
| backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | 1147 | 12 | 0 | 75.3 |
| backend\core\api\v1\payment_operations.py | PaymentOperationsViewSet | 1077 | 17 | 0 | 79.3 |
| backend\inventory\service\stock_integration.py | StockIntegrationService | 827 | 13 | 0 | 60.8 |
| frontend\ui\main_window.py | MainWindow | 1124 | 45 | 30 | 100.0 |
| frontend\ui\pos\pos_screen.py | POSScreen | 859 | 40 | 13 | 100.0 |
| frontend\ui\purchases\purchase_invoice_screen.py | PurchaseInvoiceScreen | 866 | 32 | 28 | 100.0 |
| frontend\ui\sales\sales_invoice_screen.py | SalesInvoiceScreen | 861 | 30 | 29 | 100.0 |

---

## 4. Key Observations

1. **T3 classes (8)** are concentrated in the **PySide6 UI layer** (screens, dialogs, form widgets). They are the strongest refactor candidates — extracted presenters/services will reduce cognitive load without changing UX.
2. **T2 classes (12)** include Django viewsets, signals handlers, and complex service classes. Most can be split into a thin orchestration layer + extracted calculation helpers.
3. **Signal count > 5** is a strong indicator of UI/state coupling — these classes are doing event plumbing in addition to business logic.
4. **Responsibility count > 20** indicates mixed concerns: form rendering, validation, persistence, and reporting are likely bundled together.

---

## 5. Refactor Strategy

- **For T3 UI classes** → extract **presenter** (logic) and **view builder** (UI construction).
- **For T2 service classes** → extract **validator** and **calculation engine** as separate modules.
- **For high-signal classes** → consolidate signal connections into a single `connect_signals()` method, then extract.

---

## 6. Conclusion

- 76 of 2189 classes (3.5%) exceed 300 LOC.
- 20 of 2189 classes (0.9%) exceed 500 LOC.
- 8 of 2189 classes (0.4%) exceed 800 LOC — these are the **highest-leverage refactor targets**.
- No class exceeds 1500 LOC.

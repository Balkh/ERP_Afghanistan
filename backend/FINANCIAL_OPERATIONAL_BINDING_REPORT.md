# Pharmacy ERP - Frontend to Backend Consistency Audit Report

**Date:** 2026-05-21
**Scope:** All backend API endpoints vs. all frontend screens
**Purpose:** Identify gaps, dead code, duplicated workflows, and safety risks for Phase 21 planning

---

## 1. Backend API Endpoint Inventory

### 1.1 Core Health and Operations (24 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/health/ | GET | Health check |
| /api/health/db/ | GET | Database health |
| /api/health/system/ | GET | System health |
| /api/ops/health/ | GET | Operations health |
| /api/ops/financial-integrity/ | GET | Financial integrity check |
| /api/ops/inventory-integrity/ | GET | Inventory integrity check |
| /api/ops/alerts/ | GET | Alert list |
| /api/ops/alerts/clear/ | POST | Clear alerts |
| /api/ops/postgres-readiness/ | GET | PostgreSQL readiness |
| /api/ops/summary/ | GET | Observability summary |
| /api/ops/bad-requests/ | GET | Bad request intelligence |
| /api/ops/slow-requests/ | GET | Slow request detection |
| /api/ops/api-detail/ | GET | API observability detail |
| /api/ops/scalability/ | GET | Scalability audit |
| /api/ops/db-records/ | GET | Database record counts |
| /api/ops/concurrency/ | GET | Concurrency safety |
| /api/ops/integrity/ | GET | Data integrity check |
| /api/ops/integrity-summary/ | GET | Data integrity summary |
| /api/ops/dashboard/ | GET | Observability dashboard |
| /api/ops/trends/ | GET | Performance trends |
| /api/ops/anomalies/ | GET | Anomaly clusters |
| /api/ops/guardrails/ | GET | Guardrail status |
| /api/ops/sampling/ | GET | Sampling status |
| /api/ops/stability/ | GET | Stability status |

### 1.2 Control Center (15 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/control-center/ | GET | Full dashboard data |
| /api/control-center/stats/ | GET | Quick KPI stats |
| /api/control-center/health/ | GET | Health live |
| /api/control-center/financial/ | GET | Financial summary |
| /api/control-center/inventory/ | GET | Inventory summary |
| /api/control-center/operations/ | GET | Operations summary |
| /api/control-center/hr/ | GET | HR summary |
| /api/control-center/intelligence/ | GET | Operational intelligence |
| /api/control-center/signals/ | GET | Signal summary |
| /api/control-center/signals/active/ | GET | Active signals |
| /api/control-center/signals/register/ | POST | Register signal |
| /api/control-center/decisions/ | GET | Decisions list |
| /api/control-center/decisions/detail/ | GET | Decision detail |
| /api/control-center/decisions/evaluate/ | POST | Evaluate event |
| /api/control-center/jobs/ | GET | Jobs dashboard |

### 1.3 Inventory (12 endpoints + 6 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/inventory/categories/ | CRUD | Product categories |
| /api/inventory/units/ | CRUD | Units of measure |
| /api/inventory/products/ | CRUD | Products |
| /api/inventory/batches/ | CRUD | Batches |
| /api/inventory/warehouses/ | CRUD | Warehouses |
| /api/inventory/stock-movements/ | CRUD | Stock movements |
| /api/inventory/stock/allocate/ | POST | Allocate stock |
| /api/inventory/stock/process-sale/ | POST | Process sale stock |
| /api/inventory/stock/process-purchase/ | POST | Process purchase stock |
| /api/inventory/stock/check-availability/ | GET | Check stock availability |
| /api/inventory/stock/levels/ | GET | Stock levels |
| /api/inventory/stock/products/{id}/available-batches/ | GET | Available batches |

### 1.4 Sales (9 endpoints + 4 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/sales/customers/ | CRUD | Customers |
| /api/sales/invoices/ | CRUD | Sales invoices |
| /api/sales/items/ | CRUD | Sales line items |
| /api/sales/payments/ | CRUD | Customer payments |
| /api/sales/payments/fifo_allocate/ | POST | FIFO allocation |
| /api/sales/payments/unallocated_payments/ | GET | Unallocated payments |
| /api/sales/payments/outstanding_invoices/ | GET | Outstanding invoices |
| /api/sales/payments/financial_integrity/ | GET | Financial integrity |
| /api/sales/payments/fix_balances/ | POST | Fix balances |

### 1.5 Purchases (4 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/purchases/suppliers/ | CRUD | Suppliers |
| /api/purchases/invoices/ | CRUD | Purchase invoices |
| /api/purchases/items/ | CRUD | Purchase line items |
| /api/purchases/payments/ | CRUD | Supplier payments |

### 1.6 Returns (2 ViewSets + custom actions)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/returns/return-orders/ | CRUD | Return orders |
| /api/returns/return-orders/summary/ | GET | Returns summary |
| /api/returns/return-orders/export_csv/ | GET | Export CSV |
| /api/returns/return-orders/{id}/receipt_pdf/ | GET | Receipt PDF |
| /api/returns/reconciliation/ | CRUD | Reconciliation entries |
| /api/returns/reconciliation/export_csv/ | GET | Export CSV |

### 1.7 Accounting (17 endpoints + 5 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/accounting/accounts/ | CRUD | Chart of accounts |
| /api/accounting/journal-entries/ | CRUD | Journal entries |
| /api/accounting/journal-entries/{id}/post_entry/ | POST | Post entry |
| /api/accounting/journal-entries/{id}/unpost_entry/ | POST | Unpost entry |
| /api/accounting/journal-events/ | CRUD | Journal event log |
| /api/accounting/fiscal-periods/ | CRUD | Fiscal periods |
| /api/accounting/fiscal-period-logs/ | GET | Fiscal period close logs |
| /api/accounting/calculate-invoice/ | POST | Calculate invoice |
| /api/accounting/convert-currency/ | POST | Currency conversion |
| /api/accounting/currencies/ | GET | Currency list |
| /api/accounting/exchange-rates/ | GET | Exchange rates |
| /api/accounting/calculate-mixed-payment/ | POST | Calculate mixed payment |
| /api/accounting/calculate-discount/ | POST | Calculate discount |
| /api/accounting/calculate-tax/ | POST | Calculate tax |
| /api/accounting/export/ | POST | Export report |
| /api/accounting/reports/ | POST | Advanced reports |
| /api/accounting/report-options/ | GET | Report options |

### 1.8 Payments (5 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/payments/methods/ | CRUD | Payment methods |
| /api/payments/accounts/ | CRUD | Payment accounts |
| /api/payments/transactions/ | CRUD | Financial transactions |
| /api/payments/settlements/ | CRUD | Settlements |
| /api/payments/dashboard/ | CRUD | Payment dashboard |

### 1.9 Auth and Security (17 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/auth/login/ | POST | Login |
| /api/auth/logout/ | POST | Logout |
| /api/auth/token/refresh/ | POST | Token refresh |
| /api/auth/profile/ | GET | User profile |
| /api/auth/change-password/ | POST | Change password |
| /api/auth/notifications/ | GET | Notifications list |
| /api/auth/notifications/read/ | POST | Mark read |
| /api/auth/notifications/unread-count/ | GET | Unread count |
| /api/auth/users/ | GET/POST | User list/create |
| /api/auth/users/{id}/ | GET/PUT/DELETE | User detail/update/delete |
| /api/auth/roles/ | GET | Roles list |
| /api/auth/roles/{id}/ | GET | Role detail |
| /api/auth/permissions/ | GET | Permissions list |
| /api/auth/totp/setup/ | POST | TOTP setup |
| /api/auth/totp/verify/ | POST | TOTP verify |
| /api/auth/totp/disable/ | POST | TOTP disable |
| /api/auth/totp/status/ | GET | TOTP status |

### 1.10 HR (11 endpoints + 3 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/hr/departments/ | CRUD | Departments |
| /api/hr/positions/ | CRUD | Positions |
| /api/hr/employees/ | CRUD | Employees |
| /api/hr/update-status/ | POST | Update employee status |
| /api/hr/department-tree/ | GET | Department tree |
| /api/hr/active-employees/ | GET | Active employees |
| /api/hr/reports/employee-summary/ | GET | Employee summary |
| /api/hr/reports/department-summary/ | GET | Department summary |
| /api/hr/reports/attendance-summary/ | GET | Attendance summary |
| /api/hr/reports/leave-summary/ | GET | Leave summary |
| /api/hr/reports/overtime-summary/ | GET | Overtime summary |

### 1.11 Payroll (12 endpoints + 4 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/payroll/cycles/ | CRUD | Payroll cycles |
| /api/payroll/records/ | CRUD | Payroll records |
| /api/payroll/allowances/ | CRUD | Allowances |
| /api/payroll/deductions/ | CRUD | Deductions |
| /api/payroll/generate/ | POST | Generate payroll |
| /api/payroll/approve/ | POST | Approve payroll |
| /api/payroll/summary/ | GET | Payroll summary |
| /api/payroll/reports/yearly-summary/ | GET | Yearly summary |
| /api/payroll/reports/monthly-detail/ | GET | Monthly detail |
| /api/payroll/reports/department-cost/ | GET | Department cost |
| /api/payroll/reports/employee-history/ | GET | Employee history |
| /api/payroll/reports/trend/ | GET | Payroll trend |

### 1.12 Finance Domain (14 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/expenses/ | CRUD | Expenses |
| /api/budgets/budgets/ | CRUD | Budgets |
| /api/budgets/lines/ | CRUD | Budget lines |
| /api/tax/categories/ | CRUD | Tax categories |
| /api/tax/rates/ | CRUD | Tax rates |
| /api/tax/jurisdictions/ | CRUD | Tax jurisdictions |
| /api/tax/returns/ | CRUD | Tax returns |
| /api/tax/transactions/ | CRUD | Tax transactions |
| /api/cost-centers/centers/ | CRUD | Cost centers |
| /api/cost-centers/allocations/ | CRUD | Cost allocations |
| /api/cost-centers/transactions/ | CRUD | Cost transactions |
| /api/cashflow/forecasts/ | CRUD | Cash flow forecasts |
| /api/cashflow/items/ | CRUD | Cash flow items |
| /api/cashflow/scenarios/ | CRUD | Cash flow scenarios |

### 1.13 Fixed Assets (4 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/assets/categories/ | CRUD | Asset categories |
| /api/assets/assets/ | CRUD | Fixed assets |
| /api/assets/depreciations/ | CRUD | Asset depreciations |
| /api/assets/disposals/ | CRUD | Asset disposals |

### 1.14 Backup and Restore (12 ViewSets + custom actions)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/backup/records/ | GET | Backup records |
| /api/backup/records/create_backup/ | POST | Create backup |
| /api/backup/records/{id}/verify/ | POST | Verify backup |
| /api/backup/records/{id}/delete_backup/ | DELETE | Delete backup |
| /api/backup/schedules/ | CRUD | Backup schedules |
| /api/backup/logs/ | GET | Backup logs |
| /api/backup/restore-points/ | GET | Restore points |
| /api/backup/restore-points/{id}/validate/ | POST | Validate restore point |
| /api/backup/restore-points/{id}/restore/ | POST | Restore from point |
| /api/backup/health/ | ViewSet | Backup health checks |
| /api/backup/offsite/ | ViewSet | Offsite replication |
| /api/backup/recovery/ | ViewSet | Recovery validation |
| /api/backup/certification/ | ViewSet | Certification |
| /api/backup/failure-injection/ | ViewSet | Failure injection tests |
| /api/backup/safe-restore-test/ | ViewSet | Safe restore testing |
| /api/backup/control-plane/ | ViewSet | Control plane |

### 1.15 Workflows (7 endpoints + 3 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/workflows/instances/ | CRUD | Workflow instances |
| /api/workflows/chains/ | CRUD | Approval chains |
| /api/workflows/requests/ | CRUD | Approval requests |
| /api/workflows/status/{type}/{id}/ | GET | Workflow status |
| /api/workflows/action/{id}/ | POST | Workflow action |
| /api/workflows/my-pending/ | GET | My pending approvals |
| /api/workflows/request/{id}/action/ | POST | Approval request action |

### 1.16 Jobs (6 endpoints + 2 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/jobs/jobs/ | CRUD | Background jobs |
| /api/jobs/scheduled/ | CRUD | Scheduled tasks |
| /api/jobs/job/{id}/ | GET | Job status |
| /api/jobs/job/{id}/action/ | POST | Job action |
| /api/jobs/stats/ | GET | Job stats |
| /api/jobs/run-scheduled/ | POST | Run scheduled tasks |

### 1.17 Core (4 endpoints + 1 ViewSet)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/core/invoice-templates/ | CRUD | Invoice templates |
| /api/core/import/{type}/dry-run/ | POST | Import dry run |
| /api/core/import/{type}/execute/ | POST | Import execute |

### 1.18 Entities (3 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/entities/entities/ | CRUD | Business entities |
| /api/entities/entity-accounts/ | CRUD | Entity accounts |
| /api/entities/inter-company/ | CRUD | Inter-company transactions |

### 1.19 Audit (2 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/audit/logs/ | GET | Audit trail logs |
| /api/audit/policies/ | CRUD | Audit retention policies |

### 1.20 Licensing (3 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/licensing/info/ | GET | License info |
| /api/licensing/validate/ | POST | Validate license |
| /api/licensing/create/ | POST | Create license |

### 1.21 Insurance (3 ViewSets)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/insurance/providers/ | CRUD | Insurance providers |
| /api/insurance/policies/ | CRUD | Insurance policies |
| /api/insurance/claims/ | CRUD | Insurance claims |

### 1.22 API v1 - Governance (11 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/v1/governance/intercept/ | POST | Governance intercept |
| /api/v1/governance/evaluate/ | POST | Governance evaluate |
| /api/v1/governance/action-types/ | GET | Action types |
| /api/v1/governance/simulate/ | POST | Simulation |
| /api/v1/governance/workflows/ | GET | Workflows list |
| /api/v1/governance/workflows/create/ | POST | Create workflow |
| /api/v1/governance/workflows/{id}/ | GET | Workflow detail |
| /api/v1/governance/workflows/{id}/sign/ | POST | Sign workflow |
| /api/v1/governance/workflows/{id}/escalate/ | POST | Escalate workflow |
| /api/v1/governance/workflows/{id}/cancel/ | POST | Cancel workflow |
| /api/v1/governance/status/ | GET | Gateway status |

### 1.23 API v1 - Truth Engine (14 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/v1/truth/events/ | GET | Event list |
| /api/v1/truth/events/emit/ | POST | Emit event |
| /api/v1/truth/events/{id}/ | GET | Event detail |
| /api/v1/truth/events/{id}/exists/ | GET | Event exists |
| /api/v1/truth/verify/ | POST | Verify claim |
| /api/v1/truth/verify/{domain}/{id}/ | GET | Verify aggregate |
| /api/v1/truth/projections/{domain}/rebuild/ | POST | Rebuild projection |
| /api/v1/truth/reports/stock-levels/ | GET | Stock levels report |
| /api/v1/truth/reports/ledger/ | GET | Ledger report |
| /api/v1/truth/reports/trial-balance/ | GET | Trial balance report |
| /api/v1/truth/reports/employees/ | GET | Employees report |
| /api/v1/truth/reports/orders/ | GET | Orders report |
| /api/v1/truth/summary/ | GET | Store summary |
| /api/v1/truth/consistency/ | GET | Consistency check |

### 1.24 API v1 - Observability (17 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/v1/observability/trace/{domain}/{id}/ | GET | Trace aggregate |
| /api/v1/observability/trace/event/{id}/ | GET | Trace by event |
| /api/v1/observability/trace/{id}/causation/ | GET | Causation graph |
| /api/v1/observability/timeline/ | GET | Timeline |
| /api/v1/observability/timeline/{domain}/{id}/ | GET | Timeline aggregate |
| /api/v1/observability/correlation/{id}/ | GET | Event correlation |
| /api/v1/observability/correlation/{a}/{b}/ | GET | Domain correlation |
| /api/v1/observability/correlation/dependencies/ | GET | Domain dependencies |
| /api/v1/observability/integrity/ | GET | Integrity check |
| /api/v1/observability/integrity/{domain}/ | GET | Domain integrity |
| /api/v1/observability/replay/ | POST | Replay state |
| /api/v1/observability/replay/render/{seq}/ | GET | Replay render |
| /api/v1/observability/replay/hash/ | POST | Replay hash |
| /api/v1/observability/dashboard/{type}/ | GET | Dashboard |
| /api/v1/observability/snapshot/ | GET | Snapshot |
| /api/v1/observability/status/ | GET | Status |
| /api/v1/observability/stream/ | GET | Stream metrics |

### 1.25 API v1 - Intelligence (13 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/v1/intelligence/drift/baseline/{domain}/ | GET | Drift baseline |
| /api/v1/intelligence/drift/{domain}/{id}/ | GET | Drift aggregate |
| /api/v1/intelligence/drift/{domain}/ | GET | Drift all |
| /api/v1/intelligence/patterns/{domain}/ | GET | Patterns |
| /api/v1/intelligence/patterns/{domain}/rare/ | GET | Rare events |
| /api/v1/intelligence/patterns/{domain}/bursts/ | GET | Bursts |
| /api/v1/intelligence/anomalies/{domain}/ | GET | Anomaly graph |
| /api/v1/intelligence/anomalies/cross-domain/ | GET | Cross-domain anomaly |
| /api/v1/intelligence/temporal/{domain}/ | GET | Temporal drift |
| /api/v1/intelligence/consistency/ | GET | Consistency |
| /api/v1/intelligence/consistency/compare/ | POST | Consistency compare |
| /api/v1/intelligence/snapshot/ | GET | Snapshot |
| /api/v1/intelligence/status/ | GET | Status |

### 1.26 API v1 - Autonomous (8 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/v1/autonomous/insights/ | GET | Insights |
| /api/v1/autonomous/risk-summary/ | GET | Risk summary |
| /api/v1/autonomous/decision-options/ | GET | Decision options |
| /api/v1/autonomous/forecast/ | GET | Forecast |
| /api/v1/autonomous/anomaly-warnings/ | GET | Anomaly warnings |
| /api/v1/autonomous/report/ | GET | Full report |
| /api/v1/autonomous/recommendations/ | GET | Recommendations |
| /api/v1/autonomous/status/ | GET | Status |

### 1.27 API v1 - Financial Intelligence FICL (24 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/v1/financial-intelligence/anomalies/ | GET | All anomalies |
| /api/v1/financial-intelligence/anomalies/payments/ | GET | Payment anomalies |
| /api/v1/financial-intelligence/anomalies/invoices/ | GET | Invoice anomalies |
| /api/v1/financial-intelligence/anomalies/ledger/ | GET | Ledger anomalies |
| /api/v1/financial-intelligence/reconciliation/suggest/customer/{id}/ | GET | Reconciliation suggest customer |
| /api/v1/financial-intelligence/reconciliation/suggest/supplier/{id}/ | GET | Reconciliation suggest supplier |
| /api/v1/financial-intelligence/reconciliation/unresolved/ | GET | Unresolved recs |
| /api/v1/financial-intelligence/credit-risk/assess/{id}/ | GET | Credit risk assess |
| /api/v1/financial-intelligence/credit-risk/high-risk/ | GET | High risk customers |
| /api/v1/financial-intelligence/credit-risk/predict/{id}/ | GET | Credit risk predict |
| /api/v1/financial-intelligence/cashflow/ | GET | Cashflow summary |
| /api/v1/financial-intelligence/cashflow/liquidity/ | GET | Liquidity snapshot |
| /api/v1/financial-intelligence/cashflow/exposure/ | GET | Outstanding exposure |
| /api/v1/financial-intelligence/explain/customer/{id}/ | GET | Explain customer |
| /api/v1/financial-intelligence/explain/supplier/{id}/ | GET | Explain supplier |
| /api/v1/financial-intelligence/trace/invoice/{model}/{id}/ | GET | Trace invoice |
| /api/v1/financial-intelligence/trace/payment/{model}/{id}/ | GET | Trace payment |
| /api/v1/financial-intelligence/health/ | GET | Financial health |
| /api/v1/financial-intelligence/health/ssot/ | GET | SSOT health |
| /api/v1/financial-intelligence/health/ledger/ | GET | Ledger health |
| /api/v1/financial-intelligence/health/fifo/ | GET | FIFO health |
| /api/v1/financial-intelligence/health/credit/ | GET | Credit health |
| /api/v1/financial-intelligence/health/reconciliation/ | GET | Reconciliation health |

### 1.28 Financial Control Tower (4 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/financial/control-tower/summary/ | GET | Control tower summary |
| /api/financial/control-tower/alerts/ | GET | Active alerts |
| /api/financial/control-tower/decisions/ | GET | Decisions |
| /api/financial/control-tower/re-evaluate/ | POST | Re-evaluate |

### 1.29 API v1 - Payment Operations (12 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/v1/payment-operations/customers/{id}/payment-workspace/ | GET | Customer workspace |
| /api/v1/payment-operations/customers/{id}/payment-trace/ | GET | Payment trace |
| /api/v1/payment-operations/customers/{id}/unallocated-payments/ | GET | Unallocated payments |
| /api/v1/payment-operations/customers/{id}/fifo-allocate/ | POST | FIFO allocate |
| /api/v1/payment-operations/customers/{id}/payment/ | POST | Create payment |
| /api/v1/payment-operations/suppliers/{id}/payment-workspace/ | GET | Supplier workspace |
| /api/v1/payment-operations/suppliers/{id}/payment-trace/ | GET | Payment trace |
| /api/v1/payment-operations/suppliers/{id}/unallocated-payments/ | GET | Unallocated payments |
| /api/v1/payment-operations/suppliers/{id}/fifo-allocate/ | POST | FIFO allocate |
| /api/v1/payment-operations/suppliers/{id}/payment/ | POST | Create payment |
| /api/v1/payment-operations/payment-methods/ | GET | Payment methods |
| /api/v1/payment-operations/payment-accounts/ | GET | Payment accounts |

### 1.30 Observability Console (12 endpoints)
| Endpoint | Method | Purpose |
|---|---|---|
| /api/observability/v1/health/ | GET | Observability health |
| /api/observability/v1/state/ | GET | Observability state |
| /api/observability/v1/summary/ | GET | Frontend summary |
| /api/observability/v1/timeline/ | GET | Timeline |
| /api/observability/v1/incidents/ | GET | Incidents |
| /api/observability/v1/dashboard/ | GET | Dashboard |
| /api/observability/v1/drift/ | GET | Drift |
| /api/observability/v1/telemetry/ | GET | Telemetry |
| /api/observability/v1/replay/sessions/ | GET | Replay sessions |
| /api/observability/v1/replay/sessions/{id}/ | GET | Session detail |
| /api/observability/v1/digital-twin/ | GET | Digital twin |
| /api/observability/v1/safety/ | GET | Safety |

---

## 2. Frontend Screen Inventory

### 2.1 Dashboard
- Dashboard (ui/dashboard.py) - Index 0

### 2.2 Inventory Screens
| Screen | File | Index |
|---|---|---|
| Products | ui/inventory/product_screen.py | 1 |
| Categories | ui/inventory/category_screen.py | 2 |
| Warehouses | ui/inventory/warehouse_screen.py | 3 |
| Batches | ui/inventory/batch_screen.py | 4 |

### 2.3 Sales Screens
| Screen | File | Index |
|---|---|---|
| Sales Invoice | ui/sales/sales_invoice_screen.py | 5 |
| POS Terminal | ui/pos/pos_screen.py | 10 |
| Customers | ui/sales/customer_screen.py | 7 |

### 2.4 Purchases Screens
| Screen | File | Index |
|---|---|---|
| Purchase Invoice | ui/purchases/purchase_invoice_screen.py | 6 |
| Suppliers | ui/purchases/supplier_screen.py | 8 |

### 2.5 Returns Screens
| Screen | File | Index |
|---|---|---|
| Return Orders | ui/returns/returns_screen.py | 9 |
| Reconciliation | ui/returns/reconciliation_screen.py | 57 |

### 2.6 Accounting Screens
| Screen | File | Index |
|---|---|---|
| Chart of Accounts | ui/accounting/chart_of_accounts_screen.py | 10 |
| Journal Entries | ui/accounting/journal_entry_screen.py | 11 |
| Account Ledger | ui/accounting/account_ledger_screen.py | 12 |
| Financial Integrity | ui/accounting/financial_integrity_screen.py | 58 |
| Financial Audit Log | ui/accounting/financial_audit_log_screen.py | 59 |

### 2.7 Report Screens (via ReportBrowser)
| Screen | Index | Screen | Index |
|---|---|---|---|
| Trial Balance | 13 | Cash Flow | 48 |
| Profit and Loss | 14 | Employee Summary | 49 |
| Balance Sheet | 15 | Attendance Report | 50 |
| AR Ageing | 16 | Leave Report | 51 |
| AP Ageing | 17 | Overtime Report | 52 |
| | | Payroll Summary | 53 |
| | | Payroll Trend | 54 |
| | | Payroll Dept Cost | 55 |
| | | Payroll Emp History | 56 |

### 2.8 Finance Screens
| Screen | File | Index |
|---|---|---|
| Payments | ui/finance/payment_screen.py | 18 |
| Budgeting | ui/finance/budgeting_screen.py | 19 |
| Tax | ui/finance/tax_screen.py | 20 |
| Cost Centers | ui/finance/cost_centers_screen.py | 21 |
| Cash Flow | ui/finance/cashflow_screen.py | 22 |
| Expenses | ui/finance/expense_screen.py | 34 |
| Customer Payments | ui/finance/customer_payment_workspace.py | 60 |
| Supplier Payments | ui/finance/supplier_payment_workspace.py | 61 |
| Allocation Explorer | ui/finance/payment_allocation_explorer.py | 62 |
| Returns Explainability | ui/finance/returns_explainability.py | 63 |
| Journal Reversals | ui/finance/journal_reversal_explorer.py | 64 |
| Operations Console | ui/finance/financial_operations_console.py | 65 |
| Mixed Payment Builder | ui/finance/mixed_payment_builder.py | dialog |

### 2.9 HR Screens
| Screen | File | Index |
|---|---|---|
| Employees | ui/hr/employee_screen.py | 23 |
| Attendance | ui/hr/attendance_screen.py | 24 |
| Leave | ui/hr/leave_screen.py | 25 |
| Payroll | ui/hr/payroll_screen.py | 26 |

### 2.10 System Screens
| Screen | File | Index |
|---|---|---|
| Backup and Restore | ui/system/backup_screen.py | 27 |
| Settings | ui/system/settings_screen.py | 28 |
| Fixed Assets | ui/system/fixed_assets_screen.py | 29 |
| Audit Log | ui/system/audit_screen.py | 30 |
| User Management | ui/system/user_management_screen.py | 31 |
| Intelligence Hub | ui/system/intelligence_hub_screen.py | 32 |
| Invoice Templates | ui/system/invoice_template_manager.py | 33 |
| Business Entities | ui/system/entity_management_screen.py | 35 |
| Licensing | ui/system/licensing_screen.py | 36 |
| Production | ui/system/production_screen.py | 37 |
| Control Center | ui/control_tower/operations_dashboard.py | 38 |
| Observability Console | ui/observability/observability_console.py | 39 |
| Decision Support | ui/causal_scoring/decision_workspace.py | 47 |
| Analytics Workspace | ui/system/analytics_workspace.py | 40-42 |

### 2.11 Auth Screens
- Login (ui/auth/login_screen.py)
- TOTP Setup (ui/auth/totp_setup_dialog.py)

### 2.12 Dialogs and Components
- FIFO Allocation Dialog, Credit Warning Dialog, Email Config Dialog
- Journal Entry Form/Detail, Account Form Dialog, Report Preview Dialog
- Product Form, Category/Warehouse/Batch Form Dialogs
- Printable Invoice

---

## 3. Endpoint to UI Mapping

### 3.1 Fully Covered APIs
| API Prefix | UI Screens | Coverage |
|---|---|---|
| /api/inventory/products/ | ProductScreen, BatchForm, SalesInvoice | FULL |
| /api/inventory/categories/ | CategoryScreen, ProductForm | FULL |
| /api/inventory/warehouses/ | WarehouseScreen, BatchForm | FULL |
| /api/inventory/batches/ | BatchScreen, BatchForm | FULL |
| /api/sales/customers/ | CustomerScreen, CustomerPaymentWorkspace, SalesInvoice | FULL |
| /api/sales/invoices/ | SalesInvoiceScreen, FIFOAllocationDialog | FULL |
| /api/sales/payments/ | CustomerPaymentWorkspace, FinancialIntegrityScreen, FIFOAllocationDialog | FULL |
| /api/purchases/suppliers/ | SupplierScreen, SupplierPaymentWorkspace | FULL |
| /api/purchases/invoices/ | PurchaseInvoiceScreen | FULL |
| /api/purchases/payments/ | SupplierPaymentWorkspace | FULL |
| /api/returns/return-orders/ | ReturnsScreen, ReturnsExplainability | FULL |
| /api/returns/reconciliation/ | ReconciliationScreen | FULL |
| /api/accounting/accounts/ | ChartOfAccountsScreen, JournalEntryScreen | FULL |
| /api/accounting/journal-entries/ | JournalEntryScreen, JournalReversalExplorer, FinancialOperationsConsole | FULL |
| /api/accounting/export/ | APIClient.export_report() | FULL |
| /api/accounting/reports/ | ReportBrowser | FULL |
| /api/payments/methods/ | MixedPaymentBuilder | FULL |
| /api/payments/accounts/ | MixedPaymentBuilder | FULL |
| /api/auth/users/ | UserManagementScreen | FULL |
| /api/auth/login/ | LoginScreen | FULL |
| /api/auth/logout/ | MainWindow | FULL |
| /api/auth/totp/* | TOTPSetupDialog | FULL |
| /api/licensing/info/ | LicensingScreen | FULL |
| /api/licensing/validate/ | LicensingScreen | FULL |
| /api/backup/records/ | BackupScreen | FULL |
| /api/backup/restore-points/ | BackupScreen | FULL |
| /api/backup/offsite/* | BackupScreen, EmailConfigDialog | FULL |
| /api/backup/control-plane/ | BackupScreen | FULL |
| /api/control-center/ | Dashboard, OperationsDashboard | FULL |
| /api/control-center/financial/ | Dashboard | FULL |
| /api/control-center/inventory/ | Dashboard | FULL |
| /api/control-center/hr/ | Dashboard | FULL |
| /api/control-center/health/ | Dashboard | FULL |
| /api/v1/payment-operations/customers/*/payment-workspace/ | CustomerPaymentWorkspace | FULL |
| /api/v1/payment-operations/suppliers/*/payment-workspace/ | SupplierPaymentWorkspace | FULL |
| /api/v1/payment-operations/*/payment-trace/ | PaymentAllocationExplorer | FULL |
| /api/v1/payment-operations/payment-methods/ | MixedPaymentBuilder | FULL |
| /api/v1/payment-operations/payment-accounts/ | MixedPaymentBuilder | FULL |
| /api/core/invoice-templates/ | InvoiceTemplateManager, PrintableInvoice | FULL |
| /api/entities/entities/ | EntityManagementScreen | FULL |
| /api/hr/employees/ | EmployeeScreen | FULL |
| /api/expenses/ | ExpenseScreen | FULL |
| /api/audit/logs/ | AuditScreen, FinancialAuditLogScreen | FULL |
| /api/health/ | MainWindow health check | FULL |

### 3.2 Partially Covered APIs
| API Prefix | UI Screen | Missing Coverage |
|---|---|---|
| /api/inventory/stock/levels/ | None | No UI shows stock levels directly |
| /api/sales/payments/outstanding_invoices/ | None | No direct UI |
| /api/accounting/convert-currency/ | None | No UI |
| /api/accounting/currencies/ | None | No UI |
| /api/accounting/exchange-rates/ | None | No UI |
| /api/accounting/fiscal-periods/ | None | No UI for fiscal period management |
| /api/accounting/fiscal-period-logs/ | None | No UI |
| /api/accounting/journal-events/ | None | No UI for journal event log |
| /api/payments/settlements/ | None | No UI |
| /api/payments/dashboard/ | None | No UI |
| /api/hr/department-tree/ | None | No UI |
| /api/insurance/* | None | Entire module has no UI |

---

## 4. Missing UI Coverage

### 4.1 High Priority
| Endpoint | Purpose | Recommendation |
|---|---|---|
| /api/accounting/fiscal-periods/ | Fiscal period management | CRITICAL: Add fiscal period UI for period lock management |
| /api/accounting/fiscal-period-logs/ | Fiscal period close audit trail | Add to Financial Audit Log screen |
| /api/accounting/journal-events/ | Journal event log | Add to Financial Audit Log screen |
| /api/accounting/convert-currency/ | Currency conversion | Add to Accounting toolbar |
| /api/accounting/currencies/ | Currency list | Add to Settings |
| /api/accounting/exchange-rates/ | Exchange rate management | Add to Settings |
| /api/payments/settlements/ | Settlement management | Add to Finance module |
| /api/payments/dashboard/ | Payment dashboard KPIs | Consolidate into FinancialOperationsConsole |
| /api/inventory/stock/levels/ | Stock level overview | Add to Inventory module |
| /api/hr/department-tree/ | Department hierarchy | Add to HR module |
| /api/insurance/* | Insurance module | No UI - module incomplete |

### 4.2 Medium Priority - Intelligence APIs
| Endpoint | Purpose | Recommendation |
|---|---|---|
| /api/v1/financial-intelligence/anomalies/* | Financial anomaly detection | Add to FinancialOperationsConsole |
| /api/v1/financial-intelligence/reconciliation/* | Reconciliation assistance | Add to ReconciliationScreen |
| /api/v1/financial-intelligence/credit-risk/* | Credit risk intelligence | Add to CustomerPaymentWorkspace |
| /api/v1/financial-intelligence/cashflow/* | Cashflow observability | Add to CashflowScreen |
| /api/v1/financial-intelligence/explain/* | Financial explainability | Add to ReturnsExplainability |
| /api/v1/financial-intelligence/trace/* | Invoice/payment trace | Add to FinancialOperationsConsole |
| /api/v1/financial-intelligence/health/* | Financial diagnostics | Add to FinancialIntegrityScreen |
| /api/financial/control-tower/* | Control tower | Add to FinancialOperationsConsole |

### 4.3 Low Priority - Admin/Internal
| Endpoint | Purpose | Recommendation |
|---|---|---|
| /api/backup/health/ | Backup health checks | Add to BackupScreen |
| /api/backup/recovery/ | Recovery validation | Add to BackupScreen |
| /api/backup/certification/ | Backup certification | Add to BackupScreen |
| /api/backup/failure-injection/ | Failure injection tests | Dev-only |
| /api/backup/safe-restore-test/ | Safe restore testing | Dev-only |
| /api/ops/* (24 endpoints) | Operations observability | Partially covered by ProductionScreen |
| /api/core/import/* | Import dry-run/execute | Add to entity screens |
| /api/entities/entity-accounts/ | Entity account mapping | Add to EntityManagementScreen |
| /api/entities/inter-company/ | Inter-company transactions | Add to EntityManagementScreen |
| /api/audit/policies/ | Audit retention policies | Add to AuditScreen |
| /api/licensing/create/ | License creation | Add to LicensingScreen |
| /api/tax/categories/ | Tax categories | Add to TaxScreen |
| /api/tax/jurisdictions/ | Tax jurisdictions | Add to TaxScreen |
| /api/inventory/units/ | Units of measure | Add to Settings |
| /api/inventory/stock-movements/ | Stock movements | Add to Inventory module |

---

## 5. Dead APIs (No UI Calls Them)

| Endpoint | Purpose | Risk |
|---|---|---|
| /api/accounting/fiscal-periods/ | Fiscal period open/close | HIGH - Period locking critical for financial integrity |
| /api/accounting/fiscal-period-logs/ | Period close audit log | MEDIUM |
| /api/accounting/journal-events/ | Journal event log | MEDIUM |
| /api/accounting/convert-currency/ | Currency conversion | LOW |
| /api/accounting/currencies/ | Currency list | LOW |
| /api/accounting/exchange-rates/ | Exchange rates | LOW |
| /api/payments/settlements/ | Settlement management | MEDIUM |
| /api/payments/dashboard/ | Payment dashboard | LOW |
| /api/inventory/stock/levels/ | Stock levels | MEDIUM |
| /api/hr/department-tree/ | Department tree | LOW |
| /api/insurance/* (3 ViewSets) | Insurance module | HIGH - Entire module has no UI |
| /api/v1/financial-intelligence/* (24 endpoints) | Financial intelligence | MEDIUM - All read-only |
| /api/financial/control-tower/* (4 endpoints) | Financial control tower | MEDIUM |
| /api/v1/governance/workflows/create/ | Create governance workflow | LOW |
| /api/v1/governance/workflows/*/sign/ | Sign workflow | LOW |
| /api/v1/governance/workflows/*/escalate/ | Escalate workflow | LOW |
| /api/v1/governance/workflows/*/cancel/ | Cancel workflow | LOW |
| /api/v1/truth/events/emit/ | Emit truth event | LOW |
| /api/v1/truth/projections/*/rebuild/ | Rebuild projection | LOW |
| /api/v1/truth/reports/* | Truth reports | LOW |
| /api/v1/observability/replay/* | Replay state | LOW |
| /api/v1/intelligence/consistency/compare/ | Consistency compare | LOW |
| /api/core/import/*/dry-run/ | Import dry run | MEDIUM |
| /api/core/import/*/execute/ | Import execute | MEDIUM |
| /api/entities/entity-accounts/ | Entity accounts | LOW |
| /api/entities/inter-company/ | Inter-company transactions | LOW |
| /api/audit/policies/ | Audit retention policies | LOW |
| /api/licensing/create/ | License creation | LOW |
| /api/tax/categories/ | Tax categories | LOW |
| /api/tax/jurisdictions/ | Tax jurisdictions | LOW |
| /api/inventory/units/ | Units of measure | LOW |
| /api/inventory/stock-movements/stock_valuation/ | Stock valuation | MEDIUM |
| /api/backup/health/ | Backup health | LOW |
| /api/backup/recovery/ | Recovery validation | LOW |
| /api/backup/certification/ | Certification | LOW |
| /api/backup/failure-injection/ | Failure injection | LOW |
| /api/backup/safe-restore-test/ | Safe restore test | LOW |
| /api/jobs/run-scheduled/ | Run scheduled tasks | LOW |
| /api/auth/roles/{id}/ | Role detail | LOW |
| /api/auth/permissions/ | Permissions list | LOW |

---

## 6. Dead Screens (Not Registered in main_window.py)

| Screen | File | Issue |
|---|---|---|
| Drift Intelligence Screen | ui/system/drift_intelligence_screen.py | NOT registered - dead code |
| Correlation Screen | ui/system/correlation_screen.py | NOT registered - dead code |
| Control Center Screen | ui/system/control_center_screen.py | NOT registered - dead code |
| Workflow Intelligence Screen | ui/system/workflow_intelligence_screen.py | NOT registered - dead code |
| Integrity Screen | ui/system/integrity_screen.py | NOT registered - dead code |
| Event Store Screen | ui/truth/event_store_screen.py | NOT registered - dead code |
| Master Dashboard | ui/autonomous/master_dashboard.py | NOT registered - dead code |
| Decision Options Screen | ui/autonomous/decision_options_screen.py | NOT registered - dead code |
| Anomaly Warning Center | ui/autonomous/anomaly_warning_center.py | NOT registered - dead code |
| Forecast Dashboard | ui/autonomous/forecast_dashboard.py | NOT registered - dead code |
| HR Report Screens | ui/hr/report_screens.py | Reports served via ReportBrowser |
| Base Report Screen | ui/accounting/base_report_screen.py | Superseded by ReportBrowser |
| Trial Balance Screen | ui/accounting/trial_balance_screen.py | Superseded by ReportBrowser |
| Profit Loss Screen | ui/accounting/profit_loss_screen.py | Superseded by ReportBrowser |
| Balance Sheet Screen | ui/accounting/balance_sheet_screen.py | Superseded by ReportBrowser |
| AR/AP Ageing Screen | ui/accounting/arap_ageing_screen.py | Superseded by ReportBrowser |
| Cash Flow Screen (accounting) | ui/accounting/cash_flow_screen.py | Superseded by ReportBrowser |
| Analytics Workspace | ui/system/analytics_workspace.py | Indices 40-42 all point to same screen |

---

## 7. Duplicated Workflows

### 7.1 Report Browser Consolidation (6 duplicate files)
| Old Screen | New Screen | Status |
|---|---|---|
| trial_balance_screen.py | report_browser.py (trial_balance) | Superseded |
| profit_loss_screen.py | report_browser.py (profit_loss) | Superseded |
| balance_sheet_screen.py | report_browser.py (balance_sheet) | Superseded |
| arap_ageing_screen.py | report_browser.py (ar_aging/ap_aging) | Superseded |
| cash_flow_screen.py (accounting) | report_browser.py (cash_flow) | Superseded |
| base_report_screen.py | report_browser.py | Superseded |

**Impact:** 6 duplicate screen files consuming maintenance overhead.

### 7.2 Intelligence Screen Consolidation (6 dead files)
| Old Screen | New Screen | Status |
|---|---|---|
| drift_intelligence_screen.py | intelligence_hub_screen.py | Dead code |
| correlation_screen.py | intelligence_hub_screen.py | Dead code |
| control_center_screen.py | operations_dashboard.py | Dead code |
| workflow_intelligence_screen.py | operations_dashboard.py | Dead code |
| integrity_screen.py | production_screen.py | Dead code |
| event_store_screen.py | intelligence_hub_screen.py | Dead code |

**Impact:** 6 dead screen files.

### 7.3 Dashboard Consolidation (4 dead files)
| Old Screen | New Screen | Status |
|---|---|---|
| master_dashboard.py | dashboard.py | Dead code |
| decision_options_screen.py | decision_workspace.py | Dead code |
| anomaly_warning_center.py | Cognitive bar + decision_workspace.py | Dead code |
| forecast_dashboard.py | analytics_workspace.py | Dead code |

**Impact:** 4 dead screen files.

### 7.4 Payment Workflow Duplication
| Workflow | Screen 1 | Screen 2 | Issue |
|---|---|---|---|
| Customer payment entry | customer_payment_workspace.py | payment_screen.py | Overlap |
| Supplier payment entry | supplier_payment_workspace.py | payment_screen.py | Overlap |
| FIFO allocation | fifo_allocation_dialog.py | customer_payment_workspace.py | Both available |
| Financial integrity | financial_integrity_screen.py | financial_operations_console.py | Both show health metrics |

---

## 8. Unsafe Flows

### 8.1 Period Lock Bypass Risks
| Risk | Description | Severity |
|---|---|---|
| No fiscal period UI | FiscalPeriodViewSet exists but no UI. Users can post to closed periods. | CRITICAL |
| No period validation in journal entry form | JournalEntryScreen does not check fiscal period status. | CRITICAL |
| No period validation in sales/purchase | SalesInvoiceScreen and PurchaseInvoiceScreen do not check period status. | HIGH |
| No period validation in returns | ReturnsScreen does not check period status. | HIGH |

### 8.2 Reversal Safety Gaps
| Risk | Description | Severity |
|---|---|---|
| Journal reversal without period check | Entries can be reversed without checking if reversal date is in open period. | HIGH |
| Return reversal without approval workflow | Returns can be reversed without mandatory approval chain. | MEDIUM |
| No reversal audit trail UI | JournalEventLogViewSet exists but no UI to view reversal audit trail. | MEDIUM |
| Invoice cancel without FIFO unwind | SalesInvoice cancel reverses journal entry but does not unwind FIFO allocations. | HIGH |

### 8.3 Concurrency Risks
| Risk | Description | Severity |
|---|---|---|
| CustomerPayment concurrent safety | select_for_update() used but UI does not show locking status. | LOW |
| SalesInvoice concurrent safety | select_for_update() used - safe. | LOW |
| No optimistic locking in UI | UI screens do not show version/etag for concurrent edit detection. | MEDIUM |

### 8.4 Data Integrity Risks
| Risk | Description | Severity |
|---|---|---|
| BalanceSyncService not visible in UI | BalanceSyncService called in model save() but UI does not show derived vs stored balance. | MEDIUM |
| FinancialTruthEngine not exposed in UI | Derived balances shown in PaymentWorkspace but not in CustomerScreen/SupplierScreen. | MEDIUM |
| No SSOT consistency UI | SSOT consistency checks exist but no UI shows mismatches. | MEDIUM |

---

## 9. Recommendations for Phase 21

### 9.1 Critical (Must Do)
| # | Recommendation | Effort | Impact |
|---|---|---|---|
| 1 | Add Fiscal Period Management UI - Create screen to open/close periods with lock enforcement in all posting screens | Medium | Critical |
| 2 | Add period validation to all posting screens - Journal entries, invoices, returns, payments must check period status | Medium | Critical |
| 3 | Clean up dead screen files - Remove 16 dead screen files not registered in main_window.py | Low | High |
| 4 | Add FIFO unwind on invoice cancel - Ensure SalesInvoice cancel properly unwinds FIFO allocations | Medium | High |

### 9.2 High Priority
| # | Recommendation | Effort | Impact |
|---|---|---|---|
| 5 | Add Financial Intelligence UI - Wire FICL endpoints into FinancialOperationsConsole | Medium | High |
| 6 | Add Financial Control Tower UI - Wire control tower endpoints into FinancialOperationsConsole | Low | High |
| 7 | Add Stock Levels UI - Create stock levels overview in Inventory module | Low | Medium |
| 8 | Add Settlement Management UI - Create settlements screen in Finance module | Medium | Medium |
| 9 | Add reversal audit trail UI - Wire JournalEventLogViewSet into FinancialAuditLogScreen | Low | Medium |
| 10 | Add SSOT consistency indicator - Show derived vs stored balance in CustomerScreen and SupplierScreen | Low | Medium |

### 9.3 Medium Priority
| # | Recommendation | Effort | Impact |
|---|---|---|
| 11 | Add optimistic locking to UI - Show version/etag on edit forms | Medium | Medium |
| 12 | Add currency/exchange rate management UI - Create currency management screen | Low | Medium |
| 13 | Add import UI - Create import dialogs with dry-run preview | Medium | Medium |
| 14 | Add insurance module UI - Create screens for providers, policies, claims | High | Low |
| 15 | Consolidate payment workflows - Merge PaymentScreen into CustomerPaymentWorkspace/SupplierPaymentWorkspace | Medium | Medium |

### 9.4 Low Priority
| # | Recommendation | Effort | Impact |
|---|---|---|
| 16 | Add department tree visualization - Create department hierarchy view in HR | Low | Low |
| 17 | Add units of measure management UI - Create units management screen in Settings | Low | Low |
| 18 | Add stock movement history UI - Create stock movement log in Inventory | Low | Low |
| 19 | Add audit retention policy UI - Create policy management screen in AuditScreen | Low | Low |
| 20 | Add entity account mapping UI - Create entity account mapping in EntityManagementScreen | Low | Low |

---

## 10. Summary Statistics

| Metric | Count |
|---|---|
| Total Backend API Endpoints | ~280+ (including ViewSet CRUD actions) |
| Total Frontend Screens | 55+ (including dialogs) |
| Fully Covered APIs | ~70 endpoints |
| Partially Covered APIs | ~40 endpoints |
| Dead APIs (no UI consumer) | ~50 endpoints |
| Dead Screens (not registered) | 16 screens |
| Duplicated Workflows | 4 areas |
| Critical Safety Gaps | 4 issues |
| High Safety Gaps | 3 issues |

---

*Report generated by comprehensive frontend-backend consistency audit on 2026-05-21.*
*All findings based on static analysis of URL routing, ViewSet definitions, and frontend API client calls.*

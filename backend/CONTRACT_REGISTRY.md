# API Contract Registry — v1 Stable Baseline

## Active Endpoints (119) — DO NOT CHANGE WITHOUT COMPATIBILITY LAYER

### Health & Operations
| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/api/health/` | GET | ✅ STABLE | |
| `/api/health/db/` | GET | ✅ STABLE | |
| `/api/health/system/` | GET | ✅ STABLE | |
| `/api/control-center/` | GET | ✅ STABLE | |
| `/api/control-center/stats/` | GET | ✅ STABLE | |
| `/api/control-center/health/` | GET | ✅ STABLE | |
| `/api/control-center/financial/` | GET | ✅ STABLE | |
| `/api/control-center/inventory/` | GET | ✅ STABLE | |
| `/api/control-center/operations/` | GET | ✅ STABLE | |
| `/api/control-center/hr/` | GET | ✅ STABLE | |
| `/api/control-center/intelligence/` | GET | ✅ STABLE | |
| `/api/control-center/signals/` | GET | ✅ STABLE | |
| `/api/control-center/jobs/` | GET | ✅ STABLE | |

### Auth
| Endpoint | Method | Status |
|---|---|---|
| `/api/auth/login/` | POST | ✅ STABLE |
| `/api/auth/logout/` | POST | ✅ STABLE |
| `/api/auth/token/refresh/` | POST | ✅ STABLE |
| `/api/auth/profile/` | GET | ✅ STABLE |
| `/api/auth/change-password/` | POST | ✅ STABLE |
| `/api/auth/notifications/` | GET | ✅ STABLE |
| `/api/auth/notifications/unread-count/` | GET | ✅ STABLE |
| `/api/auth/users/` | GET,POST | ✅ STABLE |
| `/api/auth/users/{id}/` | GET,PUT,DELETE | ✅ STABLE |
| `/api/auth/roles/` | GET | ✅ STABLE |
| `/api/auth/permissions/` | GET | ✅ STABLE |

### Inventory
| Endpoint | Method | Status |
|---|---|---|
| `/api/inventory/categories/` | GET,POST | ✅ STABLE |
| `/api/inventory/categories/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/inventory/products/` | GET,POST | ✅ STABLE |
| `/api/inventory/products/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/inventory/products/by_barcode/` | GET | ✅ STABLE |
| `/api/inventory/products/by_sku/` | GET | ✅ STABLE |
| `/api/inventory/batches/` | GET,POST | ✅ STABLE |
| `/api/inventory/batches/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/inventory/warehouses/` | GET,POST | ✅ STABLE |
| `/api/inventory/warehouses/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/inventory/stock-movements/` | GET,POST | ✅ STABLE |

### Sales
| Endpoint | Method | Status |
|---|---|---|
| `/api/sales/customers/` | GET,POST | ✅ STABLE |
| `/api/sales/customers/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/sales/customers/{id}/balance/` | GET | ✅ STABLE |
| `/api/sales/invoices/` | GET,POST | ✅ STABLE |
| `/api/sales/invoices/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/sales/items/` | GET,POST | ✅ STABLE |
| `/api/sales/payments/` | GET,POST | ✅ STABLE |

### Purchases
| Endpoint | Method | Status |
|---|---|---|
| `/api/purchases/suppliers/` | GET,POST | ✅ STABLE |
| `/api/purchases/suppliers/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/purchases/suppliers/{id}/balance/` | GET | ✅ STABLE |
| `/api/purchases/invoices/` | GET,POST | ✅ STABLE |
| `/api/purchases/invoices/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/purchases/items/` | GET,POST | ✅ STABLE |
| `/api/purchases/payments/` | GET,POST | ✅ STABLE |

### Accounting
| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/api/accounting/accounts/` | GET,POST | ✅ STABLE | |
| `/api/accounting/accounts/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE | |
| `/api/accounting/accounts/leaf_accounts/` | GET | ✅ STABLE | |
| `/api/accounting/accounts/trial_balance/` | GET | ✅ STABLE | |
| `/api/accounting/accounts/balance_sheet/` | GET | ✅ STABLE | |
| `/api/accounting/accounts/profit_loss/` | GET | ✅ STABLE | Alias for income_statement |
| `/api/accounting/accounts/income_statement/` | GET | ✅ STABLE | Canonical name |
| `/api/accounting/accounts/ledger/` | GET | ✅ STABLE | |
| `/api/accounting/accounts/ar_aging/` | GET | ✅ STABLE | |
| `/api/accounting/accounts/ap_aging/` | GET | ✅ STABLE | |
| `/api/accounting/accounts/account_summary/` | GET | ✅ STABLE | |
| `/api/accounting/accounts/reconciliation/` | GET | ✅ STABLE | |
| `/api/accounting/journal-entries/` | GET,POST | ✅ STABLE | |
| `/api/accounting/journal-entries/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE | |
| `/api/accounting/journal-entries/{id}/post_entry/` | POST | ✅ STABLE | |
| `/api/accounting/journal-entries/{id}/unpost_entry/` | POST | ✅ STABLE | |
| `/api/accounting/journal-entries/{id}/reverse_entry/` | POST | ✅ STABLE | |
| `/api/accounting/export/` | POST | ✅ STABLE | |
| `/api/accounting/reports/` | POST | ✅ STABLE | |
| `/api/accounting/report-options/` | GET | ✅ STABLE | |

### Payments
| Endpoint | Method | Status |
|---|---|---|
| `/api/payments/methods/` | GET,POST | ✅ STABLE |
| `/api/payments/accounts/` | GET,POST | ✅ STABLE |
| `/api/payments/transactions/` | GET,POST | ✅ STABLE |
| `/api/payments/settlements/` | GET,POST | ✅ STABLE |

### HR
| Endpoint | Method | Status |
|---|---|---|
| `/api/hr/departments/` | GET,POST | ✅ STABLE |
| `/api/hr/positions/` | GET,POST | ✅ STABLE |
| `/api/hr/employees/` | GET,POST | ✅ STABLE |
| `/api/hr/reports/employee-summary/` | GET | ✅ STABLE |
| `/api/hr/reports/attendance-summary/` | GET | ✅ STABLE |
| `/api/hr/reports/leave-summary/` | GET | ✅ STABLE |
| `/api/hr/reports/overtime-summary/` | GET | ✅ STABLE |

### Payroll
| Endpoint | Method | Status |
|---|---|---|
| `/api/payroll/cycles/` | GET,POST | ✅ STABLE |
| `/api/payroll/records/` | GET,POST | ✅ STABLE |
| `/api/payroll/allowances/` | GET,POST | ✅ STABLE |
| `/api/payroll/deductions/` | GET,POST | ✅ STABLE |
| `/api/payroll/reports/yearly-summary/` | GET | ✅ STABLE |
| `/api/payroll/reports/department-cost/` | GET | ✅ STABLE |
| `/api/payroll/reports/employee-history/` | GET | ✅ STABLE |
| `/api/payroll/reports/trend/` | GET | ✅ STABLE |

### Tax
| Endpoint | Method | Status |
|---|---|---|
| `/api/tax/categories/` | GET,POST | ✅ STABLE |
| `/api/tax/rates/` | GET,POST | ✅ STABLE |
| `/api/tax/returns/` | GET,POST | ✅ STABLE |
| `/api/tax/transactions/` | GET,POST | ✅ STABLE |

### Budgeting
| Endpoint | Method | Status |
|---|---|---|
| `/api/budgets/budgets/` | GET,POST | ✅ STABLE |
| `/api/budgets/lines/` | GET,POST | ✅ STABLE |

### Cashflow
| Endpoint | Method | Status |
|---|---|---|
| `/api/cashflow/forecasts/` | GET,POST | ✅ STABLE |
| `/api/cashflow/items/` | GET,POST | ✅ STABLE |
| `/api/cashflow/scenarios/` | GET,POST | ✅ STABLE |

### Fixed Assets
| Endpoint | Method | Status |
|---|---|---|
| `/api/assets/categories/` | GET,POST | ✅ STABLE |
| `/api/assets/assets/` | GET,POST | ✅ STABLE |
| `/api/assets/depreciations/` | GET,POST | ✅ STABLE |

### Other
| Endpoint | Method | Status |
|---|---|---|
| `/api/backup/records/` | GET,POST | ✅ STABLE |
| `/api/backup/restore-points/` | GET | ✅ STABLE |
| `/api/audit/logs/` | GET | ✅ STABLE |
| `/api/licensing/info/` | GET | ✅ STABLE |
| `/api/licensing/validate/` | POST | ✅ STABLE |
| `/api/entities/entities/` | GET,POST | ✅ STABLE |
| `/api/expenses/` | GET,POST | ✅ STABLE |
| `/api/returns/return-orders/` | GET,POST | ✅ STABLE |
| `/api/returns/return-orders/{id}/` | GET,PUT,PATCH,DELETE | ✅ STABLE |
| `/api/returns/return-orders/{id}/approve/` | POST | ✅ STABLE |
| `/api/returns/return-orders/{id}/reject/` | POST | ✅ STABLE |
| `/api/returns/reconciliation/` | GET,POST | ✅ STABLE |
| `/api/workflows/instances/` | GET,POST | ✅ STABLE |
| `/api/workflows/chains/` | GET,POST | ✅ STABLE |
| `/api/workflows/status/{entity_type}/{entity_id}/` | GET | ✅ STABLE |
| `/api/workflows/action/{workflow_id}/` | POST | ✅ STABLE |
| `/api/workflows/my-pending/` | GET | ✅ STABLE |
| `/api/workflows/request/{request_id}/action/` | POST | ✅ STABLE |
| `/api/core/invoice-templates/` | GET | ✅ STABLE |

## Contract Notes
- All responses wrapped in `StandardizedJSONRenderer` (success/data/meta format)
- All list endpoints use DRF `PageNumberPagination` with `PAGE_SIZE=20`
- Error responses: `{"success": false, "error": {...}, "meta": {...}}`
- Auth: JWT token via `Authorization: Bearer <token>` header
- Versioning: Accept-header based (`Accept: application/json; version=v1`)

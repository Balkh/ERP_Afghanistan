# EnterpriseDialog Migration Map — Phase UX.3 Layer 1

**Generated:** 2026-05-24

---

## Current State

| Category | Count | Details |
|----------|-------|---------|
| EnterpriseDialog subclasses | 3 | ConfirmDialog, AlertDialog, LoadingDialog |
| Standalone QDialog subclasses | 30 | See below |
| Dialog-like QWidget | 1 | LicenseDetailsDialog |

## Migration Targets

### BATCH 1 — LOW RISK (simple dialogs, no complex form logic)
| Priority | Dialog | File | Risk |
|----------|--------|------|------|
| 1 | EmailConfigDialog | `ui/system/email_config_dialog.py` | LOW |
| 2 | BatchFormDialog | `ui/inventory/components/batch_form_dialog.py` | LOW |
| 3 | CategoryFormDialog | `ui/inventory/components/category_form_dialog.py` | LOW |
| 4 | WarehouseFormDialog | `ui/inventory/components/warehouse_form_dialog.py` | LOW |
| 5 | ProductFormDialog | `ui/inventory/components/product_form.py` | LOW |
| 6 | CreditWarningDialog | `ui/sales/credit_warning_dialog.py` | LOW |
| 7 | AccountFormDialog | `ui/accounting/components/account_form_dialog.py` | LOW |

### BATCH 2 — MEDIUM RISK (moderate dialog logic)
| Priority | Dialog | File | Risk |
|----------|--------|------|------|
| 8 | CustomerDialog | `ui/sales/customer_screen.py` | MEDIUM |
| 9 | SupplierDialog | `ui/purchases/supplier_screen.py` | MEDIUM |
| 10 | EmployeeDialog | `ui/hr/employee_screen.py` | MEDIUM |
| 11 | UserDialog | `ui/system/user_management_screen.py` | MEDIUM |
| 12 | RoleDialog | `ui/system/role_management_screen.py` | MEDIUM |
| 13 | AssetDialog | `ui/system/fixed_assets_screen.py` | MEDIUM |
| 14 | CostCenterDialog | `ui/finance/cost_centers_screen.py` | MEDIUM |
| 15 | AddExpenseDialog | `ui/finance/expense_screen.py` | MEDIUM |
| 16 | RestoreConfirmDialog | `ui/system/backup_screen.py` | MEDIUM |
| 17 | ReportPreviewDialog | `ui/accounting/components/report_preview_dialog.py` | MEDIUM |

### BATCH 3 — HIGH RISK (complex form dialogs)
| Priority | Dialog | File | Risk |
|----------|--------|------|------|
| 18 | LoginDialog | `ui/auth/login_screen.py` | HIGH |
| 19 | TOTPSetupDialog | `ui/auth/totp_setup_dialog.py` | HIGH |
| 20 | BatchSelectionDialog | `ui/common/batch_selection.py` | HIGH |
| 21 | ProductSelectionDialog | `ui/common/product_selection_dialog.py` | HIGH |
| 22 | PrintableInvoiceDialog | `ui/common/printable_invoice.py` | HIGH |
| 23 | DocumentActionDialog | `ui/components/document_action_dialog.py` | HIGH |
| 24 | SalaryStructureDialog | `ui/hr/payroll_screen.py` | HIGH |
| 25 | FIFOAllocationDialog | `ui/sales/fifo_allocation_dialog.py` | HIGH |
| 26 | ReturnOrderDialog | `ui/returns/returns_screen.py` | HIGH |
| 27 | MixedPaymentBuilderDialog | `ui/finance/mixed_payment_builder.py` | HIGH |
| 28 | JournalEntryFormDialog | `ui/accounting/components/journal_entry_form.py` | HIGH |
| 29 | JournalEntryDetailDialog | `ui/accounting/components/journal_entry_detail.py` | HIGH |
| 30 | LicenseManagerDialog | `ui/licensing/license_manager_dialog.py` | HIGH |
| 31 | LicenseDetailsDialog (QWidget) | `ui/licensing/license_status_screen.py` | HIGH |

## Migration Pattern

### FROM (current pattern):
```python
class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("...")
        self.setMinimumWidth(500)
        self.setStyleSheet("...")
        # inline layout, buttons, etc.
```

### TO (EnterpriseDialog pattern):
```python
class MyDialog(EnterpriseDialog):
    def __init__(self, parent=None):
        super().__init__(title="...", dialog_type=DialogType.CUSTOM, parent=parent)
        content = self._build_content()
        self.set_content(content)
    
    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # ... form fields ...
        return widget
```

## FORBIDDEN in migrated dialogs
- Hardcoded dialog sizes (use EnterpriseDialog width governance)
- Inline setStyleSheet with raw hex colors
- Manual save/cancel button rows (EnterpriseDialog provides them)
- Nested QDialog.exec() calls (blocking modal chains)

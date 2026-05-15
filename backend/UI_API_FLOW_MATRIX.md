# UI ↔ API Flow Matrix

## Sales Invoice Lifecycle
| UI Action | API Endpoint | Before Fix | After Fix |
|---|---|---|---|
| Save Draft | `POST /api/sales/invoices/` | ✅ REAL | ✅ REAL (now stores invoice ID) |
| Confirm Invoice | `POST /api/sales/invoices/{id}/confirm/` | ❌ STUB (UI only) | ✅ REAL |
| Dispatch Invoice | `POST /api/sales/invoices/{id}/dispatch_invoice/` | ❌ STUB (UI only) | ✅ REAL |
| Print Invoice | `PrintableInvoiceDialog` | ✅ REAL | ✅ REAL |
| Cancel Invoice | `POST /api/sales/invoices/{id}/cancel/` | ❌ STUB (not implemented) | ❌ STUB (not implemented) |

## Purchase Invoice Lifecycle
| UI Action | API Endpoint | Before Fix | After Fix |
|---|---|---|---|
| Save Draft | `POST /api/purchases/invoices/` | ✅ REAL | ✅ REAL (now stores invoice ID) |
| Confirm Invoice | `POST /api/purchases/invoices/{id}/confirm/` | ❌ STUB (UI only) | ✅ REAL |
| Receive Invoice | `POST /api/purchases/invoices/{id}/receive/` | ❌ STUB (UI only) | ✅ REAL |
| Print Invoice | `PrintableInvoiceDialog` | ✅ REAL | ✅ REAL |

## Accounting Journal Entry Lifecycle
| UI Action | API Endpoint | Status |
|---|---|---|
| Create Entry | `POST /api/accounting/journal-entries/` | ✅ REAL |
| Post Entry | `POST /api/accounting/journal-entries/{id}/post_entry/` | ✅ REAL |
| Unpost Entry | `POST /api/accounting/journal-entries/{id}/unpost_entry/` | ✅ REAL |
| Reverse Entry | `POST /api/accounting/journal-entries/{id}/reverse_entry/` | ✅ REAL |

## Remaining Stubs (Not Fixed)
| UI Action | Expected Backend | Status | Reason |
|---|---|---|---|
| Sales Invoice Cancel | `POST /api/sales/invoices/{id}/cancel/` | ❌ STUB | No cancel button exists in UI |
| Purchase Invoice Cancel | `POST /api/purchases/invoices/{id}/cancel/` | ❌ STUB | No cancel button exists in UI |

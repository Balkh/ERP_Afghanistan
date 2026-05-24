# Changelog

## v1.0.0 (Current) — Enterprise Gold Standard

### Licensing System
- 4-state offline license validation (dev/trial/limited/licensed)
- RSA-2048 PSS/SHA256 signed `.lic` file format
- 5-factor device fingerprint engine (CPU, disk, MAC, OS ID, installation UUID)
- Offline activation flow via `activation_request.json`
- Vendor license generator console (standalone Tkinter GUI + CLI)
- Emergency bypass via `PHARMACY_ERP_LICENSE_BYPASS=true`

### Accounting
- Chart of Accounts (37 accounts, hierarchical)
- Double-entry journal engine with validated posting and reversal
- Payment infrastructure (Cash, Bank, Mobile, Hawala, Cheque, CC)
- Financial reports: Trial Balance, P&L, Balance Sheet, AR/AP Aging, Cash Flow
- Fiscal period governance and period closing
- Reversal safety validation

### Inventory
- Product, category, warehouse, batch management
- FIFO allocation engine
- Stock movement tracking (IN/OUT/TRANSFER)
- Batch expiry tracking

### Sales & Purchases
- Invoice creation with auto-journal posting
- Customer/supplier management with credit limits
- Payment allocation and reconciliation
- Returns cycle with approval workflow

### HR & Payroll
- Employee, department, position management
- Attendance, leave, overtime tracking
- Payroll cycles with allowances and deductions
- Payroll accounting integration

### UI & UX
- BaseScreen and EnterpriseDialog governance
- Token-based design system with ThemeEngine
- Deferred rendering and skeleton loaders
- UX telemetry and observability
- Workflow intelligence and navigation accelerators

### Security
- JWT authentication with refresh tokens
- TOTP multi-factor authentication
- Role-based access control
- API versioning via Accept-header
- Standardized JSON responses with error codes

### Infrastructure
- Drift prevention system with migration registry
- Backup/restore with validation
- Health monitoring and operational intelligence
- Capacity forecasting and SLA monitoring
- Production stability hardening

## v0.9.0 — Pre-Licensing Foundation

- All business logic features implemented
- 1350+ tests passing
- Multi-phase completion (Phase 1-14, UX.1-UX.5)
- Dead UI cleanup and component consolidation
- API standardization (Phase 8)
- Enterprise stability refinement (Phase 9A-9E)

# Pharmacy ERP

Enterprise pharmaceutical distribution management system. Offline-first, desktop-based, with full accounting, inventory, sales, purchasing, HR/payroll, and licensing.

## Core Philosophy

- **Offline-first**: No cloud dependency. All operations function without internet. Licensing uses an offline activation flow with RSA-signed license files.
- **Deterministic**: No AI/ML in business logic. All rule engines are static threshold-based, auditable, and predictable.
- **Single-tenant**: Designed for one pharmacy/peri-clinic per deployment. Multi-branch support via configurable `max_branches`.
- **Double-entry accounting**: All financial transactions post through a validated journal engine. No silent imbalances.
- **Graceful degradation**: License validation NEVER blocks system access. Expired licenses restrict business writes but preserve export, backup, and data access.

## Architecture

| Layer | Technology | Location |
|---|---|---|
| Frontend | PySide6 (Qt for Python) | `frontend/` |
| Backend API | Django + DRF | `backend/` |
| Database | PostgreSQL | Config in `backend/config/settings.py` |
| License validation | RSA-2048 PSS/SHA256 | `backend/licensing/` |
| Vendor licensing tool | Standalone Python (Tkinter + CLI) | `vendor_tools/` |

```
frontend/  ──HTTP──>  backend/  ──ORM──>  PostgreSQL
                          │
                    licensing/  (RSA signature verification, device fingerprint)
```

## Licensing Model

Four-state offline system — no activation server required:

| Mode | Description |
|---|---|
| **dev** | Bypasses all checks. Activated by `settings.DEBUG`, `ENV=DEV`, or `PHARMACY_ERP_LICENSE_BYPASS=true` |
| **trial** | 10-day auto-trial. Created deterministically from device fingerprint. No registration required. |
| **limited** | Trial expired. Business writes blocked (invoices, inventory edits, financial posting). Data export preserved. |
| **licensed** | Full access. Activated by importing a vendor-signed `.lic` file. No internet needed after activation. |

Private RSA keys are held exclusively by the vendor. Customers verify signatures using the bundled public key.

## Technology Stack

- **Backend**: Python 3.12, Django 4.2, DRF 3.17, PostgreSQL
- **Frontend**: PySide6 (Qt 6), custom theme engine with token-based design system
- **Security**: JWT authentication, TOTP 2FA, RSA-signed license files, role-based access control
- **Payments**: Multi-method (Cash, Bank, Mobile, Hawala, Cheque, Credit Card) with auto-journal posting
- **Reporting**: Trial Balance, P&L, Balance Sheet, AR/AP Aging, Cash Flow, CSV export

## Installation

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend
cd frontend
pip install -r ../requirements.txt
python main.py
```

## Development Setup

```bash
# Enable dev mode (bypasses all license checks)
$env:PHARMACY_ERP_LICENSE_BYPASS = "true"

# Seed demo data
python manage.py seed_payments
python manage.py seed_operational_demo
```

## Security Model

| Concern | Mechanism |
|---|---|
| Authentication | JWT (access + refresh tokens) |
| Multi-factor | TOTP (time-based one-time password) |
| Authorization | Role-based (granular permissions per endpoint) |
| License integrity | RSA-2048 signatures (PSS/SHA256) |
| Device binding | 5-factor fingerprint (CPU, disk, MAC, OS ID, installation UUID) |
| API versioning | Accept-header based (`Accept: application/json; version=v1`) |

## Repository Structure

```
├── backend/           Django API server
├── frontend/          PySide6 desktop client
├── vendor_tools/      License generation tools (vendor only)
├── docs/              Documentation
│   ├── architecture/  System design and decisions
│   ├── governance/    Governance scorecards and policies
│   ├── security/      Security audits and reports
│   ├── ux/           UX/UI reports and standards
│   ├── deployment/    Deployment guides and runbooks
│   ├── api/          API contracts and flow matrices
│   ├── licensing/     License architecture
│   ├── phases/        Phase completion reports (archived)
│   └── archive/       Legacy snapshots
├── installer/         Build and packaging
├── runner/            Startup and health scripts
└── scripts/           Utility scripts
```

## Roadmap

- **v1.0.0 (LTS)**: Current — full accounting, inventory, sales, purchasing, HR/payroll, licensing, multi-currency (AFN/USD)
- **v1.1.0**: Advanced reporting, BI dashboards, enhanced audit trails
- **v2.0.0**: Multi-company, consolidated reporting, supply chain integration

## License

Proprietary. This software is distributed under a per-device license agreement. See `docs/licensing/LICENSE_ARCHITECTURE.md` for the licensing model. Unauthorized distribution or modification is prohibited.
